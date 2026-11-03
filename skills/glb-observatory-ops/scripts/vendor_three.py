#!/usr/bin/env python3
"""vendor_three.py — three.js 观展页 vendor 链一键取件 + 导入符改写（构建期联网，运行时零外链）。

用法：
  python3 vendor_three.py --rev 170 --dest <page_dir>/vendor/

产出（dest 下）：
  three.module.js            （core， pinned rev）
  GLTFLoader.js              （examples/jsm/loaders，导入符已改写）
  utils/BufferGeometryUtils.js（GLTFLoader r150+ 依赖，导入符已改写）

改写规则（精确替换 + count 断言，失败即退出非零）：
  GLTFLoader.js:            "from 'three';" -> "from './three.module.js';"
                            "from '../utils/BufferGeometryUtils.js';" -> "from './utils/BufferGeometryUtils.js';"
  utils/BufferGeometryUtils.js: "from 'three';" -> "from '../three.module.js';"
"""
import argparse, os, sys, urllib.request

CDN = "https://cdn.jsdelivr.net/npm/three@0.{rev}.0/{path}"
FILES = [
    ("build/three.module.js", "three.module.js"),
    ("examples/jsm/loaders/GLTFLoader.js", "GLTFLoader.js"),
    ("examples/jsm/utils/BufferGeometryUtils.js", "utils/BufferGeometryUtils.js"),
]
REWRITES = {
    "GLTFLoader.js": [
        ("from 'three';", "from './three.module.js';"),
        ("from '../utils/BufferGeometryUtils.js';", "from './utils/BufferGeometryUtils.js';"),
    ],
    "utils/BufferGeometryUtils.js": [
        ("from 'three';", "from '../three.module.js';"),
    ],
}

def fetch(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "wb").write(data)
    return len(data)

def rewrite(path, pairs):
    s = open(path, encoding="utf-8").read()
    for old, new in pairs:
        n = s.count(old)
        if n != 1:
            print(f"FATAL: {path}: pattern {old!r} count={n}, expect 1", file=sys.stderr)
            sys.exit(2)
        s = s.replace(old, new)
    open(path, "w", encoding="utf-8").write(s)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", required=True, help="three.js REVISION, e.g. 170")
    ap.add_argument("--dest", required=True, help="vendor dest dir, e.g. <page>/vendor/")
    a = ap.parse_args()
    for src, rel in FILES:
        url = CDN.format(rev=a.rev, path=src)
        dest = os.path.join(a.dest, rel)
        n = fetch(url, dest)
        print(f"fetched {rel} ({n} B) <- {url}")
        if rel in REWRITES:
            rewrite(dest, REWRITES[rel])
            print(f"rewrote imports in {rel}")
    core = open(os.path.join(a.dest, "three.module.js"), encoding="utf-8", errors="ignore").read(4000)
    import re
    m = re.search(r"REVISION = '(\d+)'", core)
    got = m.group(1) if m else "?"
    if got != a.rev:
        print(f"FATAL: REVISION mismatch: got {got}, want {a.rev}", file=sys.stderr)
        sys.exit(3)
    print(f"OK: vendor chain complete, REVISION={got}")

if __name__ == "__main__":
    main()
