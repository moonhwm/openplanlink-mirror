#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pack_delta.py — 增量包组装：按 spec 拷贝文件层 + 技能 zip 归一化解包 + 生成 MANIFEST.md5。

用法:
  python3 pack_delta.py spec.json <pkg_dir>

spec.json 形如:
{
  "copy_layers": [{"layer": "skill-iteration-registry", "files": ["abs/p1", "abs/p2"]}],
  "skill_zips":  ["abs/a.skill", "abs/b.skill"],
  "overlay_layer": "skills-overlay",
  "dist_layer": "skill-dist-delta"
}

行为:
  1. copy_layers: 逐件拷入 <pkg_dir>/<layer>/（取 basename，重名即报错）。
  2. skill_zips: 每个 zip 拷入 dist_layer；再解包进 overlay_layer——
     ★归一化（钉 bug：扁平 zip 无顶层目录会串件互盖）：
       zip 内为单一顶层目录 → 用之；否则按 zip 文件名手工包壳。
  3. 全包逐文件 MANIFEST.md5（自身除外）。
"""
import hashlib, json, os, shutil, sys, zipfile


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_extract(zp, name, overlay_dir):
    tmp = os.path.join(overlay_dir, ".__tmp_extract__")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    with zipfile.ZipFile(zp) as z:
        bad = z.testzip()
        if bad:
            raise SystemExit(f"CORRUPT zip {zp}: first bad entry {bad}")
        z.extractall(tmp)
    entries = sorted(os.listdir(tmp))
    if len(entries) == 1 and os.path.isdir(os.path.join(tmp, entries[0])):
        real = entries[0]
        shutil.move(os.path.join(tmp, real), os.path.join(overlay_dir, real))
    else:
        real = name
        dst = os.path.join(overlay_dir, real)
        if os.path.exists(dst):
            raise SystemExit(f"COLLISION: overlay/{real} already exists (flat-zip guard)")
        os.makedirs(dst)
        for e in entries:
            shutil.move(os.path.join(tmp, e), os.path.join(dst, e))
    shutil.rmtree(tmp, ignore_errors=True)
    return real


def main():
    spec_path, pkg = sys.argv[1], sys.argv[2]
    spec = json.load(open(spec_path, encoding="utf-8"))
    os.makedirs(pkg, exist_ok=True)

    for cl in spec.get("copy_layers", []):
        dst_dir = os.path.join(pkg, cl["layer"])
        os.makedirs(dst_dir, exist_ok=True)
        seen = set()
        for f in cl["files"]:
            bn = os.path.basename(f)
            if bn in seen or os.path.exists(os.path.join(dst_dir, bn)):
                raise SystemExit(f"COLLISION in layer {cl['layer']}: {bn}")
            seen.add(bn)
            shutil.copy2(f, os.path.join(dst_dir, bn))
        print(f"layer {cl['layer']}: {len(seen)} files")

    overlay_layer = spec.get("overlay_layer", "skills-overlay")
    dist_layer = spec.get("dist_layer", "skill-dist-delta")
    zips = spec.get("skill_zips", [])
    if zips:
        ov = os.path.join(pkg, overlay_layer); os.makedirs(ov, exist_ok=True)
        dd = os.path.join(pkg, dist_layer); os.makedirs(dd, exist_ok=True)
        for zp in zips:
            name = os.path.basename(zp)
            name = name[:-6] if name.endswith(".skill") else os.path.splitext(name)[0]
            shutil.copy2(zp, os.path.join(dd, name + ".skill"))
            real = normalize_extract(zp, name, ov)
            print(f"skill {name} -> overlay/{real} + dist/{name}.skill")

    man = os.path.join(pkg, "MANIFEST.md5")
    lines = []
    for root, _, files in os.walk(pkg):
        for fn in files:
            p = os.path.join(root, fn)
            if os.path.abspath(p) == os.path.abspath(man):
                continue
            rel = os.path.relpath(p, pkg).replace(os.sep, "/")
            lines.append(f"{md5f(p)}  ./{rel}")
    lines.sort(key=lambda s: s.split("  ./", 1)[1])
    with open(man, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"MANIFEST.md5: {len(lines)} entries")
    return 0


if __name__ == "__main__":
    main()
