#!/usr/bin/env python3
"""check_page.py — 观展页三检：module 脚本 node --check + 运行时外链清空 + 本地引用清点。

用法：python3 check_page.py <page.html>
退出码：0=全绿，1=任一 FAIL。
"""
import re, subprocess, sys, tempfile, os

def main():
    page = sys.argv[1]
    s = open(page, encoding="utf-8").read()
    ok = True

    # 1) module 脚本抽提 + node --check
    mods = re.findall(r'<script type="module">(.*?)</script>', s, re.S)
    if not mods:
        print("FAIL: no <script type=\"module\"> found"); ok = False
    for i, m in enumerate(mods):
        with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as f:
            f.write(m); tmp = f.name
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
        os.unlink(tmp)
        print(("PASS" if r.returncode == 0 else "FAIL") + f": module script #{i} node --check")
        if r.returncode != 0:
            print(r.stderr[:500]); ok = False

    # 2) 运行时外链清空（http(s) 引用；HTML 注释内铭文豁免）
    s_nocomment = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    links = re.findall(r"https?://[^\"' )]+", s_nocomment)
    # XML 命名空间标识符（data-URI SVG 内 www.w3.org/...）不产生网络请求，豁免
    links = [l for l in links if not l.startswith(("http://www.w3.org/", "https://www.w3.org/"))]
    if links:
        ok = False
        for l in links: print(f"FAIL: external URL in runtime scope: {l}")
    else:
        print("PASS: zero external URLs in runtime scope")

    # 3) 本地引用清点（href/src 相对路径须存在；# 锚与 mailto: 豁免）
    base = os.path.dirname(os.path.abspath(page))
    refs = re.findall(r'(?:href|src)="([^"#][^"]*)"', s)
    missing = []
    for r_ in refs:
        if r_.startswith(("mailto:", "javascript:", "data:")): continue
        if r_.startswith(("http://", "https://")): continue  # 已被第 2 检捕获
        if not os.path.exists(os.path.join(base, r_)): missing.append(r_)
    if missing:
        ok = False
        for m_ in missing: print(f"FAIL: local ref missing: {m_}")
    else:
        print(f"PASS: all {len(refs)} local refs resolve")

    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
