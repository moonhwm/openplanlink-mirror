#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""forge_furnace.py v1.1.0 —— 密钥考场炉执行件：探针 → 候选登记 → 双判官+爆破 → JSONL 台账。
炉规：每轮 with-join 排水；content 空则取 reasoning_content；凭据与密钥候选零明文落日志（***尾4）。
v1.1.0 = R32 外池审判必修闭环版：空座席防护、--max-tokens（默认 8192）、环境变量凭据优先、
判官回包 JSON 校验重试、判官异族运行时登记（family）。
用法：
  python forge_furnace.py --selftest [--creds <dir>]
  python forge_furnace.py [--creds <dir>] --brief <铸造卡.md> --out <ledger.jsonl> \
      --judge pool.json:model[:fallback1,fallback2] --blast pool.json:model [--blast ...]
凭据信道：环境变量优先 KEYFORGE_POOL_<大写池名>_ENDPOINT / _KEY（可选 _FAMILY）；
--creds 目录（池 JSON，可选 family 字段）为登记备选。同名池环境变量覆盖文件。
"""
import argparse, json, os, time, pathlib, datetime, urllib.request, urllib.error
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

__version__ = "1.1.0"

JUDGE_SYS = ("你是同行评审（判官）。只基于呈堂证据与专业常识裁判，不迎合作者。"
    "思考从简，直接输出严格 JSON：{\"scores\":{\"craft\":0,\"evidence\":0,\"honesty\":0},"
    "\"verdict\":\"PASS|REVISE|FAIL\",\"critiques\":[\"...\"],"
    "\"rulings\":[\"对每条自登记裂缝的裁定：是否致命及理由\"]}")
BLAST_SYS = ("你是敌意审稿人（爆破手），任务是炸毁不是表扬。输出严格 JSON："
    "{\"fatal_flaws\":[{\"claim\":\"...\",\"why_wrong\":\"...\",\"counter_evidence\":\"无反证则此条自废\"}],"
    "\"weakest_candidate\":{\"name\":\"...\",\"reason\":\"...\"},"
    "\"immunity_check\":\"作者自登记裂缝是否夸大以求免疫\"}。")

LEDGER_NOTE = "本 JSONL 为原始 transcript（content 字段存判官回包原文，重试留痕）"

def mask(s):
    s = str(s or "")
    return "***" + s[-4:] if len(s) >= 4 else "***"

def normalize_endpoint(endpoint):
    if endpoint and "chat/completions" not in endpoint and endpoint.rstrip("/").endswith(("/v1", "/v2", "/v3")):
        endpoint = endpoint.rstrip("/") + "/chat/completions"
    return endpoint

def load_pool(path):
    d = json.load(open(path, encoding="utf-8"))
    endpoint = normalize_endpoint(d.get("endpoint") or (d.get("api") or {}).get("chat", ""))
    key = d.get("api_key") or d.get("key") or d.get("token") or ""
    return {"name": pathlib.Path(path).stem, "endpoint": endpoint, "key": key,
            "family": d.get("family") or "", "via": "creds"}

def load_env_pools():
    pools = {}
    for k, v in os.environ.items():
        if k.startswith("KEYFORGE_POOL_") and k.endswith("_ENDPOINT"):
            name = k[len("KEYFORGE_POOL_"):-len("_ENDPOINT")].lower()
            up = name.upper()
            pools[name] = {"name": name, "endpoint": normalize_endpoint(v),
                           "key": os.environ.get(f"KEYFORGE_POOL_{up}_KEY", ""),
                           "family": os.environ.get(f"KEYFORGE_POOL_{up}_FAMILY", ""),
                           "via": "env"}
    return pools

def chat(endpoint, key, model, system, user, max_tokens=8192, timeout=180):
    body = {"model": model, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}]}
    req = urllib.request.Request(endpoint, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
            m = d["choices"][0]["message"]
            content = m.get("content") or m.get("reasoning_content") or ""
            return {"ok": bool(content), "http": 200, "content": content,
                    "via": "content" if m.get("content") else "reasoning_content",
                    "tokens": d.get("usage", {}).get("total_tokens"),
                    "latency_s": round(time.time() - t0, 1)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "http": e.code, "content": e.read().decode("utf-8", "replace")[:300]}
    except Exception as e:
        return {"ok": False, "http": -1, "content": f"{type(e).__name__}: {e}"}

def _try_parse(content):
    try:
        return json.loads(content)
    except Exception:
        return None

def validate_verdict(rec, pool, model, system, user, max_tokens):
    """判官回包校验：content 试 json.loads，失败原模型重试一次；仍败 parse_status=invalid。"""
    d = _try_parse(rec.get("content", ""))
    if d is None:
        r2 = chat(pool["endpoint"], pool["key"], model, system, user, max_tokens=max_tokens)
        rec["parse_retry"] = {"model": model, "http": r2["http"], "ok": r2["ok"]}
        if r2["ok"]:
            d = _try_parse(r2["content"])
            if d is not None:
                rec["content"] = r2["content"]
    rec["parse_status"] = "ok" if isinstance(d, dict) else "invalid"
    if isinstance(d, dict):
        rec["verdict"] = d.get("verdict")
        rec["scores"] = d.get("scores")
    return rec

def run_seat(seat, pool, models, system, user, max_tokens):
    chain = []
    for model in models:
        r = chat(pool["endpoint"], pool["key"], model, system, user, max_tokens=max_tokens)
        chain.append({"model": model, "http": r["http"]})
        if r["ok"]:
            rec = {**r, "seat": seat, "pool": pool["name"], "model": model,
                   "family": pool.get("family") or "",
                   "fallback_chain": chain,
                   "ts": datetime.datetime.now().isoformat(timespec="seconds")}
            return validate_verdict(rec, pool, model, system, user, max_tokens)
    return {"ok": False, "http": chain[-1]["http"] if chain else -1, "content": "all models failed",
            "seat": seat, "pool": pool["name"], "model": models[-1],
            "family": pool.get("family") or "", "fallback_chain": chain,
            "parse_status": "invalid",
            "ts": datetime.datetime.now().isoformat(timespec="seconds")}

def check_spec_syntax(spec):
    parts = spec.split(":")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(spec)
    return parts[0]

def main():
    ap = argparse.ArgumentParser(description=f"密钥考场炉执行件 v{__version__}")
    ap.add_argument("--creds", help="池凭据 JSON 目录（登记备选；环境变量 KEYFORGE_POOL_* 优先）")
    ap.add_argument("--brief", help="铸造卡+矿脉证据链 md（呈堂题面）")
    ap.add_argument("--out", help="JSONL 台账输出路径")
    ap.add_argument("--judge", action="append", default=[],
                    help="pool.json:model[:fb1,fb2]，可重复（须异族）")
    ap.add_argument("--blast", action="append", default=[], help="同 --judge")
    ap.add_argument("--max-tokens", type=int, default=8192,
                    help="判官/爆破手 max_tokens（默认 8192，推理型模型烧尽不出判词时按降级登记）")
    ap.add_argument("--selftest", action="store_true", help="无网自检：载凭据+组题面，不发包")
    a = ap.parse_args()

    # M4 凭据通道：环境变量优先，--creds 目录为登记备选
    pools = load_env_pools()
    if a.creds:
        for p in pathlib.Path(a.creds).glob("*.json"):
            if p.stem not in pools:
                pools[p.stem] = load_pool(p)
    for p in pools.values():
        p["key_masked"] = mask(p["key"])

    def parse(spec):
        f, rest = spec.split(":", 1)
        f = f[:-5] if f.endswith(".json") else f
        if f not in pools:
            ap.error(f"座席池未登记：{f}（环境变量 KEYFORGE_POOL_{f.upper()}_ENDPOINT/_KEY "
                     f"与 --creds 目录均无此池）")
        parts = rest.split(":")
        models = [parts[0]] + (parts[1].split(",") if len(parts) > 1 else [])
        return pools[f], models

    if a.selftest:
        if pools:
            print("[selftest] pools:", {n: {"endpoint": p["endpoint"][:48], "key": p["key_masked"],
                                            "family": p["family"], "via": p["via"]}
                                        for n, p in pools.items()})
            for spec in a.judge + a.blast:
                pool, models = parse(spec)
                print(f"[selftest] seat spec ok: pool={pool['name']} models={models}"
                      f" family={pool['family'] or '-'} via={pool['via']}")
        else:
            print("[selftest] 未给 --creds 且环境无 KEYFORGE_POOL_*：只验座席 spec 语法与题面组装，不解析池")
            for spec in a.judge + a.blast:
                try:
                    check_spec_syntax(spec)
                except ValueError:
                    ap.error(f"座席 spec 语法不合法：{spec}（须为 pool.json:model[:fb1,fb2]）")
                print(f"[selftest] seat spec 语法 ok: {spec}")
        if a.brief:
            print(f"[selftest] brief bytes={len(pathlib.Path(a.brief).read_bytes())}")
        print(f"[selftest] max_tokens={a.max_tokens}")
        print("[selftest] PASS（未发任何网络请求）")
        return

    # M1 空座席防护：未给任何座席，在读 brief/发任何网络请求之前友好退出（exit 2）
    if not a.judge and not a.blast:
        ap.error("至少需要一个 --judge/--blast 座席（空座席不开庭）")

    # M9 非 selftest 缺 --brief：argparse 级友好报错，不裸栈
    if not a.brief:
        ap.error("非 --selftest 开庭须给 --brief 铸造卡题面（呈堂不可无题）")

    brief = pathlib.Path(a.brief).read_text(encoding="utf-8")
    user = ("【呈堂题面：铸造卡+矿脉证据链】\n\n" + brief +
            "\n\n判官闭卷：你不见作者自辩，只据此题面与专业常识裁判。")

    tasks = []
    for spec in a.judge:
        pool, models = parse(spec)
        tasks.append(("判官-" + pool["name"], pool, models, JUDGE_SYS))
    for spec in a.blast:
        pool, models = parse(spec)
        tasks.append(("爆破手-" + pool["name"], pool, models, BLAST_SYS))

    # M9 判官异族运行时登记：同族多座席不拒绝，但台账记「同族偏倚在案」
    fam_seats = defaultdict(list)
    for seat, pool, models, system in tasks:
        if pool.get("family"):
            fam_seats[pool["family"]].append(seat)
    biased_seats = {s for seats in fam_seats.values() if len(seats) > 1 for s in seats}

    results = []
    with ThreadPoolExecutor(max_workers=min(4, len(tasks))) as ex:  # with 即 join 排水
        futs = [ex.submit(run_seat, seat, pool, models, system, user, a.max_tokens)
                for seat, pool, models, system in tasks]
        for f in futs:
            r = f.result()
            r["ledger_note"] = LEDGER_NOTE
            if r["seat"] in biased_seats:
                r["family_note"] = "同族偏倚在案"
            results.append(r)
            print(f"[{r['seat']}] http={r['http']} ok={r['ok']} parse={r.get('parse_status')}"
                  f" verdict={r.get('verdict')} tokens={r.get('tokens')} chain={r.get('fallback_chain')}"
                  + (" 同族偏倚在案" if r["seat"] in biased_seats else ""))

    if a.out:
        with open(a.out, "a", encoding="utf-8") as fo:
            for r in results:
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
        print("ledger ->", a.out)

if __name__ == "__main__":
    main()
