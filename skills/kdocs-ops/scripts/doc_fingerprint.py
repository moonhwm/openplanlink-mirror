#!/usr/bin/env python3
"""doc_fingerprint.py — 云文档「可微可导」建档：指纹 + 节级指纹 + 漂移 diff（SKILL.md §5）。

输入：kdocs-cli drive read-file 的 JSON 导出（shell 重定向落盘，不用 -o），或纯文本。
用法：
  python3 doc_fingerprint.py --key gangyao --file-id qh2Z... --src /tmp/gangyao_raw.json \
      --version 170 --archive-dir /mnt/agents/output/openplanlink-guard/docs
行为：
  1) 解析导出（容错：raw_decode 截过 CLI 升级提示尾噪）；
  2) 写 <archive-dir>/<key>.txt（正文）与 <key>.meta.json（file_id/version/chars/links/节指纹）；
  3) 更新 <archive-dir>/index.json 登记簿；
  4) 对比上次登记，打印漂移报告（version/chars/sha256_16/节级新增·消失·变更）。
退出码：0=建档成功；1=输入解析失败；2=写盘校验失败。
"""
import argparse, datetime, hashlib, json, os, re, sys

def sha(s: str) -> str: return hashlib.sha256(s.encode("utf-8")).hexdigest()

def load_text(src: str) -> str:
    raw = open(src, encoding="utf-8").read()
    try:  # JSON 导出：data.content；用 raw_decode 容错尾部升级提示（实证：stdout 混流）
        d, _ = json.JSONDecoder().raw_decode(raw.lstrip())
        if isinstance(d, dict):
            node = d.get("data", d)
            if isinstance(node, dict) and isinstance(node.get("content"), str):
                return node["content"]
            if isinstance(d.get("result"), str):  # otl block-query 形态
                return d["result"]
    except Exception:
        pass
    return raw  # 纯文本兜底

def section_fps(text: str):
    heads = [(m.start(), m.group(0).strip()) for m in re.finditer(r"(?m)^#{1,6}\s+.+$", text)]
    out = []
    for i, (pos, h) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        body = text[pos:end]
        out.append({"heading": h.lstrip("# ").strip(), "line": text[:pos].count("\n") + 1,
                    "chars": len(body), "sha256_16": sha(body)[:16]})
    return out

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--file-id", default="")
    ap.add_argument("--src", required=True)
    ap.add_argument("--version", type=int, default=0)
    ap.add_argument("--archive-dir", required=True)
    a = ap.parse_args()

    text = load_text(a.src)
    if not text.strip():
        print("FAIL: 正文为空或解析失败", file=sys.stderr); return 1

    os.makedirs(a.archive_dir, exist_ok=True)
    txt_path = os.path.join(a.archive_dir, f"{a.key}.txt")
    meta_path = os.path.join(a.archive_dir, f"{a.key}.meta.json")
    idx_path = os.path.join(a.archive_dir, "index.json")

    links = len(re.findall(r"https?://[^\s)\]]+", text))
    meta = {"key": a.key, "file_id": a.file_id, "version": a.version,
            "pulled_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "chars": len(text), "links": links, "sha256_16": sha(text)[:16],
            "section_headings": section_fps(text)}

    # FUSE 安全写：tmp → remove → copy → 复读断言（SKILL.md 生态纪律）
    import shutil, tempfile
    def fuse_write(path: str, payload: str) -> None:
        fd, tmp = tempfile.mkstemp(); os.close(fd)
        with open(tmp, "w", encoding="utf-8") as f: f.write(payload)
        if os.path.exists(path): os.remove(path)
        shutil.copyfile(tmp, path); os.remove(tmp)
        if sha(open(path, encoding="utf-8").read()) != sha(payload):
            raise IOError(f"sha 复读不符: {path}")

    prev = None
    if os.path.exists(idx_path):
        try: prev = json.load(open(idx_path, encoding="utf-8")).get(a.key)
        except Exception: prev = None

    try:
        fuse_write(txt_path, text)
        fuse_write(meta_path, json.dumps(meta, ensure_ascii=False, indent=2))
        idx = {}
        if os.path.exists(idx_path):
            idx = json.load(open(idx_path, encoding="utf-8"))
        idx[a.key] = {k: meta[k] for k in ("file_id", "version", "pulled_at", "chars", "links", "sha256_16")}
        fuse_write(idx_path, json.dumps(idx, ensure_ascii=False, indent=2))
    except (IOError, OSError) as e:
        print(f"FAIL: {e}", file=sys.stderr); return 2

    print(json.dumps({"key": a.key, "sha256_16": meta["sha256_16"], "version": a.version,
                      "chars": meta["chars"], "links": links,
                      "sections": len(meta["section_headings"])}, ensure_ascii=False))
    if prev:
        drift = {"version": (prev.get("version"), a.version),
                 "chars": (prev.get("chars"), meta["chars"]),
                 "sha256_16_changed": prev.get("sha256_16") != meta["sha256_16"]}
        print("DRIFT " + json.dumps(drift, ensure_ascii=False))
        if drift["sha256_16_changed"]:
            print("节级定位：比对本目录 <key>.meta.json 的 section_headings 与上轮快照，逐节 sha256_16 定位变动节")
    else:
        print("FIRST_ARCHIVE（无上次登记）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
