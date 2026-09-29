#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""delta_inventory.py — 增量盘点：某目录在截止日期后变更的文件清单（含排除表）。

用法:
  python3 delta_inventory.py <source_dir> --since 2026-09-04 [--exclude a.json --exclude b.py]
                           [--maxdepth 1] [--json out.json]

输出: stdout 打印摘要；--json 给路径时落盘逐件清单(relpath/size/md5/mtime)。
红线: 默认排除任何路径含 vault 的件；--exclude 逐名追加（只匹配 basename）。
"""
import argparse, hashlib, json, os, sys, datetime


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source_dir")
    ap.add_argument("--since", required=True, help="截止日期 YYYY-MM-DD（含当日零点起算）")
    ap.add_argument("--exclude", action="append", default=[], help="按 basename 排除，可多次")
    ap.add_argument("--maxdepth", type=int, default=1, help="相对 source_dir 的目录深度，默认1")
    ap.add_argument("--json", dest="json_out", default=None)
    a = ap.parse_args()

    since = datetime.datetime.strptime(a.since, "%Y-%m-%d").timestamp()
    base = os.path.abspath(a.source_dir)
    excl = set(a.exclude)
    items, skipped = [], []

    for root, dirs, files in os.walk(base):
        rel_root = os.path.relpath(root, base)
        depth = 0 if rel_root == "." else rel_root.count(os.sep) + 1
        if depth >= a.maxdepth:
            dirs[:] = []
        if "vault" in rel_root.split(os.sep):
            dirs[:] = []
            continue
        for fn in files:
            if fn in excl:
                skipped.append(fn)
                continue
            p = os.path.join(root, fn)
            st = os.stat(p)
            if st.st_mtime < since:
                continue
            rel = os.path.relpath(p, base)
            items.append({"relpath": rel.replace(os.sep, "/"), "size": st.st_size,
                          "md5": md5f(p),
                          "mtime": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")})

    items.sort(key=lambda x: x["relpath"])
    total = sum(i["size"] for i in items)
    print(f"source={base}")
    print(f"since={a.since}  files={len(items)}  bytes={total}  excluded={sorted(excl)}  skipped_excluded={skipped}")
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump({"source": base, "since": a.since, "count": len(items),
                       "bytes": total, "excluded": sorted(excl), "items": items},
                      f, ensure_ascii=False, indent=1)
        print(f"json={a.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
