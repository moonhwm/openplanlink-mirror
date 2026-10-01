#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lineage_intake.py — 传人收件：合规压缩包 → 归一化解包 → 内容盘点 → intake 报告。

用法:
  python3 lineage_intake.py <pkg.zip|pkg.skill> <work_dir> [--audit-script path/to/skill_audit.py]

行为:
  1. 安检: --audit-script 在场则调用之（只读，退码!=0 即拒收）；缺席声明降级。
  2. 归一化解包进 <work_dir>/inbox/<pkg名>/：单一顶层目录用之，扁平包按包名包壳
     （钉 backup-delta-ops 已钉 bug：扁平串件互盖）。
  3. 盘点: 逐件 relpath/size/类型；文本件抽前 400 字符作预览（供女娲吸收拍定位素材）。
  4. 落 intake_report.json + stdout 摘要。
红线: vault 字样路径拒收；凭证值永不回显。
"""
import argparse, json, os, shutil, subprocess, sys, zipfile

TEXT_EXT = (".md", ".py", ".sh", ".json", ".yaml", ".yml", ".txt", ".toml", ".csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pkg")
    ap.add_argument("work_dir")
    ap.add_argument("--audit-script", default=None)
    a = ap.parse_args()

    # 1 安检
    audit = "skipped(no audit script)"
    if a.audit_script:
        r = subprocess.run([sys.executable, a.audit_script, a.pkg], capture_output=True, text=True)
        audit = f"exit={r.returncode}"
        if r.returncode == 1:
            print(f"REJECT: audit FAIL ({a.pkg})"); print(r.stdout[-2000:])
            return 1

    name = os.path.basename(a.pkg)
    for suf in (".skill", ".zip"):
        if name.endswith(suf):
            name = name[: -len(suf)]
    inbox = os.path.join(a.work_dir, "inbox")
    os.makedirs(inbox, exist_ok=True)
    tmp = os.path.join(inbox, ".__tmp__")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)

    # 2 归一化解包
    if zipfile.is_zipfile(a.pkg):
        with zipfile.ZipFile(a.pkg) as z:
            for i in z.infolist():  # 穿越/符号链意图在审计拍已拒；此处双保险
                n = i.filename
                if n.startswith("/") or ".." in n.split("/"):
                    print(f"REJECT: unsafe entry {n}")
                    return 1
            z.extractall(tmp)
    else:
        shutil.copy2(a.pkg, os.path.join(tmp, os.path.basename(a.pkg)))
    entries = sorted(os.listdir(tmp))
    if len(entries) == 1 and os.path.isdir(os.path.join(tmp, entries[0])):
        shutil.move(os.path.join(tmp, entries[0]), os.path.join(inbox, name))
    else:
        dst = os.path.join(inbox, name)
        shutil.rmtree(dst, ignore_errors=True)
        os.makedirs(dst)
        for e in entries:
            shutil.move(os.path.join(tmp, e), os.path.join(dst, e))
    shutil.rmtree(tmp, ignore_errors=True)

    # 3 盘点
    root = os.path.join(inbox, name)
    items, n_text = [], 0
    for r_, _, files in os.walk(root):
        for fn in files:
            p = os.path.join(r_, fn)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            if "vault" in rel.split("/"):
                print(f"REJECT: vault-like path {rel}")
                return 1
            ext = os.path.splitext(fn)[1].lower()
            it = {"relpath": rel, "size": os.path.getsize(p), "ext": ext}
            if ext in TEXT_EXT and it["size"] <= 2 * 1024 * 1024:
                it["preview"] = open(p, encoding="utf-8", errors="ignore").read(400)
                n_text += 1
            items.append(it)
    items.sort(key=lambda x: x["relpath"])

    # 4 报告
    rep = {"pkg": a.pkg, "inbox": root, "audit": audit, "files": len(items),
           "text_files": n_text, "bytes": sum(i["size"] for i in items), "items": items}
    out = os.path.join(a.work_dir, "intake_report.json")
    json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"INTAKE OK: {name} files={len(items)} text={n_text} bytes={rep['bytes']} audit={audit}")
    print(f"report={out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
