#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_delta.py — 增量包验收闸：结构抽查 + MANIFEST 复算 + 凭证嗅探 + zip 完整性。

用法:
  python3 verify_delta.py <pkg_dir> [--zip path.zip] [--overlay-layer skills-overlay]

判项(全部 PASS 才退 0):
  S1 overlay 每个技能目录必含 SKILL.md（扁平包壳事故的回检闸）
  S2 MANIFEST.md5 逐行复算（缺件/改字节即 FAIL）
  S3 凭证嗅探: 疑似命中须全为文档占位/资源ID形态, 否则 FAIL（只报计数与分类, 永不回显值）
  S4 --zip 在场时 zipfile.testzip 完整性
"""
import argparse, hashlib, os, re, sys, zipfile

CRED_PAT = re.compile(r"(api[_-]?key|secret|password|token)['\"]?\s*[:=]\s*['\"]([A-Za-z0-9_\-]{16,})", re.I)
RESOURCE_ID = re.compile(r"(file|node|obj|origin_node|parent|folder|doc|sheet|bitable|wiki)_token$", re.I)


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_placeholder(v):
    lv = v.lower()
    return any(k in lv for k in ("your", "example", "xxx", "placeholder", "dummy", "changeme"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pkg_dir")
    ap.add_argument("--zip", dest="zip_path", default=None)
    ap.add_argument("--overlay-layer", default="skills-overlay")
    a = ap.parse_args()
    pkg = a.pkg_dir
    fails = []

    # S1 结构闸
    ov = os.path.join(pkg, a.overlay_layer)
    if os.path.isdir(ov):
        bad = [d for d in sorted(os.listdir(ov))
               if os.path.isdir(os.path.join(ov, d)) and not os.path.exists(os.path.join(ov, d, "SKILL.md"))]
        loose = [f for f in sorted(os.listdir(ov)) if os.path.isfile(os.path.join(ov, f))]
        if bad or loose:
            fails.append(f"S1 FAIL: dirs missing SKILL.md={bad}; loose files={loose}")
        else:
            print(f"S1 PASS: overlay {len(os.listdir(ov))} dirs all have SKILL.md")
    else:
        print("S1 SKIP: no overlay layer")

    # S2 MANIFEST 复算
    man = os.path.join(pkg, "MANIFEST.md5")
    if os.path.exists(man):
        bad = []
        for line in open(man, encoding="utf-8"):
            line = line.rstrip("\n")
            if not line:
                continue
            h, rel = line.split("  ./", 1)
            p = os.path.join(pkg, rel)
            if not os.path.exists(p) or md5f(p) != h:
                bad.append(rel)
        if bad:
            fails.append(f"S2 FAIL: {len(bad)} entries mismatch, first={bad[:3]}")
        else:
            print(f"S2 PASS: MANIFEST {sum(1 for _ in open(man))} entries all recompute")
    else:
        fails.append("S2 FAIL: MANIFEST.md5 missing")

    # S3 凭证嗅探
    total, hard = 0, []
    for root, _, files in os.walk(pkg):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for m in CRED_PAT.finditer(txt):
                total += 1
                key, val = m.group(1), m.group(2)
                if not (is_placeholder(val) or RESOURCE_ID.search(key)):
                    hard.append((os.path.relpath(p, pkg), key, len(val), hashlib.md5(val.encode()).hexdigest()[:8]))
    if hard:
        fails.append(f"S3 FAIL: {len(hard)} suspicious (file,key,len,fp)={hard[:5]}  (values never echoed)")
    else:
        print(f"S3 PASS: {total} doc-pattern hits, 0 hard secrets")

    # S4 zip 完整性
    if a.zip_path:
        with zipfile.ZipFile(a.zip_path) as z:
            bad = z.testzip()
        if bad:
            fails.append(f"S4 FAIL: zip first bad entry {bad}")
        else:
            print(f"S4 PASS: zip integrity ok ({a.zip_path})")

    if fails:
        for f_ in fails:
            print(f_)
        return 1
    print("VERDICT: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
