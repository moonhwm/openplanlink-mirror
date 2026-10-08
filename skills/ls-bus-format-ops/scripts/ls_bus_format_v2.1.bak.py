#!/usr/bin/env python3
"""ls-bus-format-ops 核心脚本 v2（梯度读取补丁版，原体 /app/.user/skills 只读不动）。

v1 卡死定谳：scan 对目标目录全部文件逐一全量 sha256（6133 件 / 156MB，
其中 20 件 >1MB 计 133MB，node_modules 二进制为主），且无目录排除、无大小分档、
无进度输出——大目录下 I/O 风暴致表象"卡死"。

v2 梯度读取三档：
  档一 stat 档   全量仅 os.stat（瞬时）；
  档二 全量哈希  ≤ FULL_HASH_MAX（默认 4MB）全量 sha256；
  档三 采样哈希  > FULL_HASH_MAX 取头 1MB + 尾 1MB + size 合成指纹，
                 manifest 逐件标注 hash_mode: full|sampled。
目录排除：默认跳过 .git / node_modules / __pycache__（目录本身作条目入册，
不递归；--no-prune-dirs 关闭）。进度：每 PROGRESS_EVERY 件 stderr 报点。
--max-files 保险丝：超限即拒（防误指巨目录）。

三段式与三重安全闸同 v1，execute 漂移比对按 hash_mode 各自复核。
"""
import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

ALLOWED_ROOT = os.path.realpath("/mnt/agents/output")
RUNS_DIRNAME = "_ls_bus_format_runs"

KEEP_PATTERNS = [
    "persona", "人设", "周嘤鸣", "授名", "署名", "身份锚点", "锚点",
    "handoff", "genealogy", "engine_r", "自我设定", "本席设定", "席位",
    "seat-naming", "naming", RUNS_DIRNAME,
]

# v2 梯度参数
FULL_HASH_MAX = 4 << 20          # ≤4MB 全量哈希
SAMPLE_BLOCK = 1 << 20           # 采样头尾各 1MB
PRUNE_DIRNAMES = {".git", "node_modules", "__pycache__"}
PROGRESS_EVERY = 500
MAX_FILES_DEFAULT = 20000
JOBS_DEFAULT = 16                # FUSE 挂载 per-open 延迟并发摊销


def sha256_of(path, block=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(block)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def fingerprint(path, size):
    """梯度指纹：小文件全量；大文件头尾采样。返回 (hexdigest, mode)。"""
    if size <= FULL_HASH_MAX:
        return sha256_of(path), "full"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(SAMPLE_BLOCK))
        if size > SAMPLE_BLOCK:
            f.seek(max(SAMPLE_BLOCK, size - SAMPLE_BLOCK))
            h.update(f.read(SAMPLE_BLOCK))
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


def scan(target, extra_patterns, prune_dirs=True, max_files=MAX_FILES_DEFAULT,
         jobs=JOBS_DEFAULT):
    entries, pruned, todos = [], [], []
    for dirpath, dirnames, filenames in os.walk(target, followlinks=False):
        dirnames.sort()
        if prune_dirs:
            skip = [d for d in list(dirnames) if d in PRUNE_DIRNAMES]
            for d in skip:
                dirnames.remove(d)
                rel = os.path.relpath(os.path.join(dirpath, d), target)
                pruned.append(rel)
                entries.append({"rel": rel + "/", "size": 0, "sha256": None,
                                "hash_mode": "pruned-dir", "class": "keep"})
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                continue
            rel = os.path.relpath(full, target)
            st = os.stat(full)                       # 档一：stat（walk 内联）
            todos.append((rel, full, st.st_size))
            if len(todos) > max_files:
                raise SystemExit(f"REFUSE: 文件数超保险丝 {max_files}，请缩目录或 --max-files")
    # 档二/档三：并发指纹（FUSE per-open 延迟摊销；GIL 让位于 I/O）
    n = 0
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(fingerprint, full, size): (rel, size)
                for rel, full, size in todos}
        for fut in futs:
            rel, size = futs[fut]
            fp, mode = fut.result()
            entries.append({"rel": rel, "size": size, "sha256": fp,
                            "hash_mode": mode,
                            "class": "keep" if is_keep(rel, extra_patterns) else "purge"})
            n += 1
            if n % PROGRESS_EVERY == 0:
                print(f"[scan] {n}/{len(todos)} files…", file=sys.stderr)
    entries.sort(key=lambda e: e["rel"])
    return entries, pruned


def cmd_scan(args):
    target = resolve_target(args.target_dir)
    extra = load_extra_patterns(args.keep_file)
    entries, pruned = scan(target, extra,
                           prune_dirs=not args.no_prune_dirs,
                           max_files=args.max_files, jobs=args.jobs)
    keep = [e for e in entries if e["class"] == "keep"]
    purge = [e for e in entries if e["class"] == "purge"]
    sampled = sum(1 for e in entries if e.get("hash_mode") == "sampled")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest = {
        "tool": "ls-bus-format-ops", "tool_version": "v2-gradient",
        "ts_utc": ts, "target_dir": target,
        "keep_patterns": KEEP_PATTERNS + extra,
        "gradient": {"full_hash_max": FULL_HASH_MAX, "sample_block": SAMPLE_BLOCK,
                     "prune_dirnames": sorted(PRUNE_DIRNAMES),
                     "pruned_dirs": pruned, "sampled_files": sampled},
        "counts": {"total": len(entries), "keep": len(keep), "purge": len(purge)},
        "keep": keep, "purge": purge,
    }
    mtext = json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True)
    mhash = hashlib.sha256(mtext.encode()).hexdigest()
    manifest["manifest_sha256"] = mhash
    runs = os.path.join(target, RUNS_DIRNAME)
    os.makedirs(runs, exist_ok=True)
    mpath = os.path.join(runs, f"manifest_{ts}.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1, sort_keys=True)
    md = [f"# ls 清单 {ts}（v2 梯度）",
          f"target={target} total={len(entries)} keep={len(keep)} purge={len(purge)} "
          f"sampled={sampled} pruned_dirs={len(pruned)}",
          f"manifest_sha256={mhash}", "", "## purge（待格式化）"]
    shown = purge[: args.md_max_rows]
    md += [f"- {e['rel']} ({e['size']}B, {e['hash_mode']}:{e['sha256'][:12]}…)" for e in shown]
    if len(purge) > len(shown):
        md.append(f"- …余 {len(purge) - len(shown)} 件见 manifest.json")
    md += ["", "## keep（自我设定，保留）"]
    md += [f"- {e['rel']} ({e['size']}B)" for e in keep[: args.md_max_rows]]
    mdpath = os.path.join(runs, f"manifest_{ts}.md")
    with open(mdpath, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(json.dumps({"manifest": mpath, "manifest_md": mdpath,
                      "manifest_sha256": mhash, "counts": manifest["counts"],
                      "gradient": manifest["gradient"]},
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
                 f"manifest_local={args.manifest}（全量清单含逐件 sha256，runs 留痕目录强制保留）",
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
    current, _ = scan(target, extra,
                      prune_dirs=not args.no_prune_dirs,
                      max_files=args.max_files, jobs=args.jobs)
    cur_map = {e["rel"]: (e["sha256"], e.get("hash_mode")) for e in current}
    plan_map = {e["rel"]: (e["sha256"], e.get("hash_mode")) for e in m["purge"]}
    drift = [r for r in plan_map if cur_map.get(r) != plan_map[r]]
    if drift:
        raise SystemExit("REFUSE: 清单漂移（文件已变动），须重新 scan：" + "; ".join(drift[:5]))
    deleted, kept_blocked = [], []
    for e in m["purge"]:
        rel = e["rel"]
        if is_keep(rel, extra):  # 双保险
            kept_blocked.append(rel)
            continue
        full = os.path.join(target, rel)
        if os.path.isfile(full) and not os.path.islink(full):
            os.remove(full)
            deleted.append(rel)
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
    p1.add_argument("--no-prune-dirs", action="store_true",
                    help="关闭 .git/node_modules/__pycache__ 目录排除")
    p1.add_argument("--max-files", type=int, default=MAX_FILES_DEFAULT)
    p1.add_argument("--md-max-rows", type=int, default=2000, help="manifest.md 每段最大行数")
    p1.add_argument("--jobs", type=int, default=JOBS_DEFAULT, help="指纹并发线程数")
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
    p3.add_argument("--no-prune-dirs", action="store_true")
    p3.add_argument("--max-files", type=int, default=MAX_FILES_DEFAULT)
    p3.add_argument("--jobs", type=int, default=JOBS_DEFAULT)
    args = ap.parse_args()
    {"scan": cmd_scan, "bussql": cmd_bussql, "execute": cmd_execute}[args.cmd](args)


if __name__ == "__main__":
    main()
