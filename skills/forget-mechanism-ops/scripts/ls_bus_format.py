#!/usr/bin/env python3
"""ls-bus-format-ops 核心脚本 v2.0：ls 清单 → 上传总线留痕（SQL 底稿）→ 本地格式化。

三段式：
  scan     递归列出 target_dir，按自我设定规则分类 keep/purge，输出清单（JSON+MD+sha256）
  bussql   由 scan 清单生成总线 INSERT SQL 底稿（脚本生成，禁人工转录；执行须另经批准）
  execute  删除 purge 清单内文件（须 --approve=<manifest_sha256 前16> 且清单未变）

硬闸（不可覆盖）：
  * target_dir 必须位于 /mnt/agents/output 之内（含其本身）
  * KEEP 识别双保险：分类时一次、删除前逐文件再一次
  * 永不跟随符号链接；永不删除 KEEP 命中项；runs 留痕目录强制保留

v2.0 梯度读取（修 v1 卡死）：
  * 指纹分级：≤SAMPLE_THRESHOLD 全文 sha256；超过则 head/tail 各 64KB + size + mtime_ns 采样指纹
  * --full 恢复 v1 全文哈希（慢挂载慎用）
  * 遍历分批并输出进度（--quiet 关闭）；--max-files 总量护栏
  * scan/execute 共用同一指纹函数，漂移判定对称
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

ALLOWED_ROOT = os.path.realpath("/mnt/agents/output")
RUNS_DIRNAME = "_ls_bus_format_runs"
SAMPLE_THRESHOLD = 1 << 20      # 1MB：以下全文哈希，以上采样指纹
SAMPLE_BLOCK = 1 << 16          # 采样头尾各 64KB
PROGRESS_EVERY = 200            # 每 200 件报一次进度

# 自我设定（身份/人设/席位设定区块）默认识别模式——命中即保留
KEEP_PATTERNS = [
    "persona", "人设", "周嘤鸣", "授名", "署名", "身份锚点", "锚点",
    "handoff", "genealogy", "engine_r", "自我设定", "本席设定", "席位",
    "seat-naming", "naming", RUNS_DIRNAME,
]


def fingerprint(path, size, mtime_ns, full=False):
    """文件指纹：小文件全文 sha256；大文件采样指纹（head+tail+size+mtime_ns）。
    返回 (hexdigest, mode)。mode ∈ full|sampled。"""
    h = hashlib.sha256()
    if full or size <= SAMPLE_THRESHOLD:
        with open(path, "rb") as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                h.update(b)
        return h.hexdigest(), "full"
    with open(path, "rb") as f:
        head = f.read(SAMPLE_BLOCK)
        f.seek(max(0, size - SAMPLE_BLOCK))
        tail = f.read(SAMPLE_BLOCK)
    h.update(head)
    h.update(tail)
    h.update(str(size).encode())
    h.update(str(mtime_ns).encode())
    return h.hexdigest(), "sampled"


def is_keep(relpath, extra_patterns):
    pats = KEEP_PATTERNS + (extra_patterns or [])
    low = relpath.lower()
    return any(p.lower() in low for p in pats)


def resolve_target(raw):
    t = os.path.realpath(raw)
    if t != ALLOWED_ROOT and not t.startswith(ALLOWED_ROOT + os.sep):
        raise SystemExit(f"REFUSE: target_dir 须在 {ALLOWED_ROOT} 之内，收到: {t}")
    if not os.path.isdir(t):
        raise SystemExit(f"REFUSE: 目录不存在: {t}")
    return t


def load_extra_patterns(keep_file):
    if not keep_file:
        return []
    with open(keep_file, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]


def _listdir_retry(dirpath, retries=3, base_sleep=0.5):
    """scandir 物化 + EAGAIN 退避重试（fuse 挂载抖动抛 Resource temporarily unavailable）。"""
    import time as _time
    for k in range(retries):
        try:
            with os.scandir(dirpath) as it:
                return list(it)
        except BlockingIOError:
            if k == retries - 1:
                raise
            _time.sleep(base_sleep * (2 ** k))
        except OSError:
            raise
    return []


def scan(target, extra_patterns, full=False, quiet=False, max_files=0):
    """梯度遍历：os.scandir 逐层物化（EAGAIN 退避重试），分批进度输出；指纹分级。"""
    entries = []
    n = 0
    stack = [target]
    while stack:
        dirpath = stack.pop()
        try:
            dirents = _listdir_retry(dirpath)
        except OSError as e:
            print(f"WARN: 无法进入 {dirpath}: {e}", file=sys.stderr)
            continue
        if True:
            subs = []
            for de in dirents:
                try:
                    if de.is_symlink():
                        continue
                    if de.is_dir(follow_symlinks=False):
                        subs.append(de.path)
                        continue
                    if not de.is_file(follow_symlinks=False):
                        continue
                    st = de.stat(follow_symlinks=False)
                    rel = os.path.relpath(de.path, target)
                    digest, mode = fingerprint(de.path, st.st_size, st.st_mtime_ns, full=full)
                    entries.append({
                        "rel": rel,
                        "size": st.st_size,
                        "mtime_ns": st.st_mtime_ns,
                        "sha256": digest,
                        "hash_mode": mode,
                        "class": "keep" if is_keep(rel, extra_patterns) else "purge",
                    })
                    n += 1
                    if max_files and n > max_files:
                        raise SystemExit(f"REFUSE: 文件数超 --max-files={max_files} 护栏，已列 {n} 件")
                    if not quiet and n % PROGRESS_EVERY == 0:
                        print(f"...scan 进度 {n} 件（当前 {rel}）", file=sys.stderr)
                except OSError as e:
                    print(f"WARN: 跳过 {de.path}: {e}", file=sys.stderr)
            stack.extend(sorted(subs))
    entries.sort(key=lambda e: e["rel"])
    return entries


def cmd_scan(args):
    target = resolve_target(args.target_dir)
    extra = load_extra_patterns(args.keep_file)
    entries = scan(target, extra, full=args.full, quiet=args.quiet,
                   max_files=args.max_files)
    keep = [e for e in entries if e["class"] == "keep"]
    purge = [e for e in entries if e["class"] == "purge"]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest = {
        "tool": "ls-bus-format-ops",
        "tool_version": "2.0",
        "ts_utc": ts,
        "target_dir": target,
        "keep_patterns": KEEP_PATTERNS + extra,
        "hash_full": bool(args.full),
        "counts": {"total": len(entries), "keep": len(keep), "purge": len(purge)},
        "keep": keep,
        "purge": purge,
    }
    mtext = json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True)
    mhash = hashlib.sha256(mtext.encode()).hexdigest()
    manifest["manifest_sha256"] = mhash
    runs = os.path.join(target, RUNS_DIRNAME)
    os.makedirs(runs, exist_ok=True)
    # v2.1 并发侦测：runs 内有非本席时间戳 manifest（60s 内异席扫描）→ 警告并发，不抢删
    concurrent = []
    try:
        import time as _t
        now_epoch = _t.time()
        for fn in os.listdir(runs):
            if fn.startswith("manifest_") and fn.endswith(".json") and ts not in fn:
                fp2 = os.path.join(runs, fn)
                if abs(now_epoch - os.path.getmtime(fp2)) < 3600:
                    concurrent.append(fn)
    except OSError:
        pass
    if concurrent:
        print(f"CONCURRENT-WARN: 近 1h 内异席 manifest 在案 {concurrent[:3]} —— execute 前必核漂移，不抢删不重复删", file=sys.stderr)
    mpath = os.path.join(runs, f"manifest_{ts}.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1, sort_keys=True)
    # v2.1 KEEP 件入备份包（血泪教训：KEEP 未入包+异席删除=台账原件丢失）
    keep_arc = os.path.join(runs, f"keep_archive_{ts}.tar.gz")
    try:
        import tarfile
        with tarfile.open(keep_arc, "w:gz") as tf:
            for e in keep:
                fp3 = os.path.join(target, e["rel"])
                if os.path.isfile(fp3):
                    tf.add(fp3, arcname=e["rel"])
        print(f"keep_archive: {keep_arc}（{len(keep)} 件 KEEP 已入包）")
    except Exception as ex:
        print(f"WARN: keep 归档失败 {ex}（不阻断 scan）", file=sys.stderr)
        keep_arc = None
    md = [f"# ls 清单 {ts}", f"target={target} total={len(entries)} keep={len(keep)} purge={len(purge)}",
          f"manifest_sha256={mhash}", "", "## purge（待格式化）"]
    md += [f"- {e['rel']} ({e['size']}B, sha256:{e['sha256'][:12]}…, {e['hash_mode']})" for e in purge]
    md += ["", "## keep（自我设定，保留）"]
    md += [f"- {e['rel']} ({e['size']}B)" for e in keep]
    mdpath = os.path.join(runs, f"manifest_{ts}.md")
    with open(mdpath, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(json.dumps({"manifest": mpath, "manifest_md": mdpath,
                      "manifest_sha256": mhash, "counts": manifest["counts"]},
                     ensure_ascii=False, indent=1))
    print("DRY-RUN：未删除任何文件。格式化须先 bussql 留痕，再 execute --approve=" + mhash[:16])


def cmd_bussql(args):
    with open(args.manifest, encoding="utf-8") as f:
        m = json.load(f)
    mhash = m.get("manifest_sha256", "")
    c = m["counts"]
    if args.digest:
        import collections
        top = collections.Counter(e["rel"].split("/")[0] for e in m["purge"])
        lines = [f"【ls-bus-format 留痕·摘要】target={m['target_dir']} total={c['total']} keep={c['keep']} purge={c['purge']}",
                 f"manifest_sha256={mhash}",
                 f"manifest_local={args.manifest}（全量清单含逐件指纹，runs 留痕目录强制保留）",
                 "", "## purge 顶层目录分布（件数）"]
        lines += [f"- {k}: {v}" for k, v in top.most_common(30)]
    else:
        lines = [f"【ls-bus-format 留痕】target={m['target_dir']} total={c['total']} keep={c['keep']} purge={c['purge']}",
                 f"manifest_sha256={mhash}", "", "## purge 清单（sha256 前12）"]
        lines += [f"- {e['rel']} ({e['size']}B, {e['sha256'][:12]})" for e in m["purge"]]
        lines += ["", "## keep 清单（自我设定保留）", ]
        lines += [f"- {e['rel']}" for e in m["keep"]]
    payload = "\n".join(lines) + "\n"
    phash = hashlib.sha256(payload.encode()).hexdigest()
    esc = payload.replace("'", "''")
    seat = args.seat or "k3-govdoc-seat"
    sql = ("INSERT INTO public.cross_mode_channel (from_mode, to_mode, kind, payload_md, status, msg_hash)\n"
           f"VALUES ('{seat}', 'all', 'notice', '{esc}', 'sent', '{phash}')\n"
           "RETURNING id, from_mode, kind, status, msg_hash, length(payload_md) AS plen;\n")
    out = args.out or args.manifest.replace(".json", ".bus.sql")
    with open(out, "w", encoding="utf-8") as f:
        f.write(sql)
    print(json.dumps({"sql": out, "payload_sha256": phash, "plen": len(payload)},
                     ensure_ascii=False, indent=1))
    print("SQL 底稿已生成（脚本生成禁人工转录）。执行属写类动作，须当轮批准后经 execute_sql 落线并回读核验。")


def cmd_execute(args):
    with open(args.manifest, encoding="utf-8") as f:
        m = json.load(f)
    mhash = m.get("manifest_sha256", "")
    if not args.approve or args.approve != mhash[:16]:
        raise SystemExit(f"REFUSE: --approve 令牌须等于 manifest_sha256 前16（{mhash[:16]}）")
    target = resolve_target(m["target_dir"])
    extra = m.get("keep_patterns", [])[len(KEEP_PATTERNS):]
    hash_full = bool(m.get("hash_full", False))
    current = scan(target, extra, full=hash_full, quiet=args.quiet)
    cur_map = {e["rel"]: (e["sha256"], e["size"], e["mtime_ns"]) for e in current}
    plan_map = {e["rel"]: (e["sha256"], e["size"], e["mtime_ns"]) for e in m["purge"]}
    drift = [r for r in plan_map if cur_map.get(r) != plan_map[r]]
    if drift:
        raise SystemExit("REFUSE: 清单漂移（文件已变动），须重新 scan：" + "; ".join(drift[:5]))
    deleted, kept_blocked = [], []
    for i, e in enumerate(m["purge"], 1):
        rel = e["rel"]
        if is_keep(rel, extra):  # 双保险
            kept_blocked.append(rel)
            continue
        full = os.path.join(target, rel)
        if os.path.isfile(full) and not os.path.islink(full):
            os.remove(full)
            deleted.append(rel)
        if not args.quiet and i % PROGRESS_EVERY == 0:
            print(f"...execute 进度 {i}/{len(m['purge'])}", file=sys.stderr)
    pruned = 0
    if args.prune_empty_dirs:
        for dirpath, dirnames, filenames in os.walk(target, topdown=False):
            if os.path.basename(dirpath) == RUNS_DIRNAME:
                continue
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
                pruned += 1
    print(json.dumps({"deleted": len(deleted), "blocked_by_keep_doublecheck": kept_blocked,
                      "pruned_empty_dirs": pruned,
                      "verify": "deleted files gone: " +
                      str(all(not os.path.exists(os.path.join(target, r)) for r in deleted))},
                     ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser(prog="ls_bus_format.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("scan")
    p1.add_argument("--target-dir", default="/mnt/agents/output")
    p1.add_argument("--keep-file", default=None, help="追加自我设定模式白名单（每行一个子串）")
    p1.add_argument("--full", action="store_true",
                    help="全文 sha256（v1 行为；慢挂载/大目录慎用，可能极慢）")
    p1.add_argument("--quiet", action="store_true", help="关闭进度输出")
    p1.add_argument("--max-files", type=int, default=0, help="文件数护栏，超限拒绝（0=不限）")
    p2 = sub.add_parser("bussql")
    p2.add_argument("--manifest", required=True)
    p2.add_argument("--seat", default="k3-govdoc-seat")
    p2.add_argument("--out", default=None)
    p2.add_argument("--digest", action="store_true",
                    help="摘要模式：总线只载计数+哈希绑定+顶层分布（全量清单留 runs 留痕目录）")
    p3 = sub.add_parser("execute")
    p3.add_argument("--manifest", required=True)
    p3.add_argument("--approve", required=True, help="manifest_sha256 前16")
    p3.add_argument("--prune-empty-dirs", action="store_true")
    p3.add_argument("--quiet", action="store_true", help="关闭进度输出")
    args = ap.parse_args()
    {"scan": cmd_scan, "bussql": cmd_bussql, "execute": cmd_execute}[args.cmd](args)


if __name__ == "__main__":
    main()
