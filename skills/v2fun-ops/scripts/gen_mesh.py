#!/usr/bin/env python3
"""v2fun-ops 生产调用脚本：V2Fun 3D 网格生成（文生/图生）+ 轮询 + 下载。

实测纪律内化（2026-10-02 中国区实测）：
- 中国区缺省 base = https://api.v2fun.art/api/v1（key 分区：.art 控制台 key 只能打 .art；
  api.v2fun.ai 从中国访问被阿里云 WAF 拦）。海外/自查场景用 --base-url 或 V2FUN_BASE_URL 覆盖。
- 轮询间隔 >=15s（5s 实测触发 429 RATE_LIMIT_EXCEEDED），429 指数退避。
- 断线凭 task_uuid 续查（--task-uuid），绝不重复提交（重复提交 = 重复扣积分）。
- 实测响应结构：status 大写（COMPLETED/processing）；result 是字符串化列表；
  metadata 是 list，metadata[0].downloads[] 每项含 asset_path / download_url（OSS 签名，
  约 1 小时过期）/ download_expires_at；按 asset_path 后缀挑格式。
- 凭据零接触：Key 只从环境变量 V2FUN_API_KEY 读，不打印、不落盘。

用法：
  python3 gen_mesh.py --balance                          # 查余额
  python3 gen_mesh.py --prompt "a low-poly fox" --with-texture --out fox.glb
  python3 gen_mesh.py --image portrait.png --with-texture --out model.glb
  python3 gen_mesh.py --task-uuid <uuid> --out model.glb # 断线续查
  python3 gen_mesh.py --selftest                         # 无网自检
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "https://api.v2fun.art/api/v1"
POLL_INTERVAL = 15.0        # 实测：5s 触发 429
POLL_TIMEOUT = 15 * 60      # 图生 3D+纹理实测 165s；留足余量
BACKOFF_MAX = 120.0
DONE_STATES = {"completed", "success", "succeeded", "done"}
FAIL_STATES = {"failed", "failure", "error", "canceled", "cancelled"}


class ApiError(Exception):
    pass


def _http(method, url, key, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, method=method, data=data)
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = {"_raw": raw[:500]}
        return e.code, payload
    except urllib.error.URLError as e:
        raise ApiError(f"网络错误: {e.reason}")


def _parse_status(payload):
    """实测：status 字段大小写混杂（COMPLETED / processing），统一 lower 后判断。"""
    st = str(payload.get("status") or payload.get("state") or "").lower()
    task = payload.get("task") or payload.get("data")
    if not st and isinstance(task, dict):
        st = str(task.get("status") or "").lower()
    return st, payload


def extract_downloads(payload):
    """实测结构（2026-10-02）：metadata 是 list，metadata[0].downloads[] 含
    asset_path / download_url / download_expires_at；result 是字符串化列表（仅供参考）。
    返回 [(asset_path, download_url), ...]；结构不符时抛错如实呈报，不猜测。"""
    meta = payload.get("metadata")
    if isinstance(meta, list) and meta and isinstance(meta[0], dict):
        dls = meta[0].get("downloads")
    elif isinstance(meta, dict):
        dls = meta.get("downloads")
    else:
        dls = None
    if not isinstance(dls, list):
        raise ApiError("响应中未找到 metadata[].downloads 列表；实际结构: "
                       + json.dumps({k: type(v).__name__ for k, v in payload.items()}, ensure_ascii=False))
    out = []
    for d in dls:
        if isinstance(d, dict) and d.get("download_url"):
            out.append((str(d.get("asset_path") or ""), d["download_url"]))
    if not out:
        raise ApiError("downloads 列表为空或缺 download_url 字段")
    return out


def pick_asset(downloads, want_suffix=".glb"):
    for path, url in downloads:
        if path.lower().endswith(want_suffix):
            return path, url
    return downloads[0]


def poll_until_done(base, key, task_uuid, log=print):
    """轮询任务；429 指数退避；返回终态 payload。"""
    url = f"{base}/3d_models/meshes/{task_uuid}"
    interval = POLL_INTERVAL
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        code, payload = _http("GET", url, key)
        if code == 429:
            log(f"429 限流，退避 {interval:.0f}s 后续查（task_uuid={task_uuid} 保留，不重提交）")
            time.sleep(interval)
            interval = min(interval * 2, BACKOFF_MAX)
            continue
        if code != 200:
            raise ApiError(f"轮询 HTTP {code}: {json.dumps(payload, ensure_ascii=False)[:300]}")
        interval = POLL_INTERVAL
        st, payload = _parse_status(payload)
        log(f"status={st or '?'}")
        if st in DONE_STATES:
            return payload
        if st in FAIL_STATES:
            raise ApiError(f"任务失败: {json.dumps(payload, ensure_ascii=False)[:300]}")
        time.sleep(interval)
    raise ApiError(f"轮询超时（{POLL_TIMEOUT}s）；task_uuid={task_uuid} 仍可续查，勿重新提交")


def create_mesh(base, key, prompt=None, image_path=None, model="pro", with_texture=False, log=print):
    body = {"model": model}
    if prompt:
        body["prompt"] = prompt
    elif image_path:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(image_path)[1].lstrip(".").lower() or "png"
        if ext == "jpg":
            ext = "jpeg"
        body["input_image"] = f"data:image/{ext};base64,{b64}"  # 实测内联可用
    else:
        raise ApiError("需要 --prompt 或 --image 之一")
    if with_texture:
        body["with_texture"] = True
    code, payload = _http("POST", f"{base}/3d_models/meshes", key, body)
    if code not in (200, 201):
        raise ApiError(f"创建任务 HTTP {code}: {json.dumps(payload, ensure_ascii=False)[:300]}")
    task_uuid = payload.get("task_uuid") or (payload.get("task") or {}).get("task_uuid")
    if not task_uuid:
        raise ApiError("响应缺 task_uuid: " + json.dumps(payload, ensure_ascii=False)[:300])
    log(f"任务已提交 task_uuid={task_uuid}（断线可用 --task-uuid 续查，勿重复提交）")
    if code == 200:  # 同步完成
        return task_uuid, payload
    return task_uuid, None


def download(url, out_path, log=print):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read()
    if out_path.lower().endswith(".glb"):
        if data[:4] != b"glTF":
            raise ApiError("下载件缺 glTF 魔数，非有效 GLB")
        log(f"GLB 核验通过（魔数 glTF，{len(data)} 字节）")
    with open(out_path, "wb") as f:
        f.write(data)
    log(f"已下载 -> {out_path}（{len(data)} 字节）")


def selftest():
    """无网自检：实测响应结构的解析、状态归一、挑格式。"""
    # 2026-10-02 实测响应样本（结构）
    sample = {
        "status": "COMPLETED",
        "result": "['models/xxx.glb']",
        "metadata": [{"reference_images": ["in.png"],
                       "downloads": [{"asset_path": "models/xxx.glb",
                                       "download_url": "https://oss.example/sig",
                                       "download_expires_at": "2026-10-02T01:00:00Z"}]}],
    }
    st, _ = _parse_status(sample)
    assert st in DONE_STATES, st
    dls = extract_downloads(sample)
    assert pick_asset(dls, ".glb")[0] == "models/xxx.glb"
    # 异常结构必须报错而非猜测
    try:
        extract_downloads({"status": "COMPLETED", "metadata": {"x": 1}})
        raise SystemExit("selftest FAIL: 应抛错未抛")
    except ApiError:
        pass
    st2, _ = _parse_status({"status": "processing"})
    assert st2 not in DONE_STATES and st2 not in FAIL_STATES
    print("selftest PASS（状态归一/实测结构解析/异常拒猜/格式挑选）")


def main(argv=None):
    ap = argparse.ArgumentParser(description="V2Fun 3D 网格生成（实测纪律内化）")
    ap.add_argument("--prompt")
    ap.add_argument("--image")
    ap.add_argument("--model", default="pro", choices=["pro", "flash"])
    ap.add_argument("--with-texture", action="store_true")
    ap.add_argument("--task-uuid", help="断线续查：跳过提交直接轮询既有任务")
    ap.add_argument("--out", default="model.glb")
    ap.add_argument("--balance", action="store_true")
    ap.add_argument("--base-url", default=os.environ.get("V2FUN_BASE_URL", DEFAULT_BASE))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        selftest()
        return 0

    key = os.environ.get("V2FUN_API_KEY")
    if not key:
        print("缺 V2FUN_API_KEY 环境变量（凭据零接触：请用户自行配置，勿在对话中索要明文）",
              file=sys.stderr)
        return 2
    base = args.base_url.rstrip("/")

    if args.balance:
        code, payload = _http("GET", f"{base}/balance", key)
        print(f"HTTP {code}: {json.dumps(payload, ensure_ascii=False)}")
        return 0 if code == 200 else 1

    try:
        if args.task_uuid:
            task_uuid, payload = args.task_uuid, None
            print(f"续查既有任务 task_uuid={task_uuid}（不重复提交，不重复扣积分）")
        else:
            task_uuid, payload = create_mesh(base, key, args.prompt, args.image,
                                             args.model, args.with_texture)
        if payload is None:
            payload = poll_until_done(base, key, task_uuid)
        dls = extract_downloads(payload)
        path, url = pick_asset(dls, os.path.splitext(args.out)[1] or ".glb")
        print(f"取件 {path}（共 {len(dls)} 件可下载）")
        download(url, args.out)
        return 0
    except ApiError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
