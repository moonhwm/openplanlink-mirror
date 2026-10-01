#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skill_audit.py — 非显式 .skill 包入口审计：十探针合一。

用法:
  python3 skill_audit.py <pkg.skill|目录> [--installed-names a,b,c] [--bomb-ratio 100] [--json out.json]

探针（2026-09-11 实证校准）:
  A1 结构: 扁平/包裹（扁平不判罪，登记防串件）
  A2 zip slip 意图: 条目含 ../、绝对路径、盘符 → FAIL（stdlib 消毒≠意图清白）
  A3 符号链接条目（unix mode S_ISLNK）→ FAIL
  A4 压缩炸弹: 解压总字节/包字节 > --bomb-ratio（默认100）或解压总量 >200MB → FAIL
  A5 名称遮蔽: frontmatter name 与既有安装名录冲突 → FAIL（优先级 Project>User>Built-in）
  A6 description 劫持面: >1024 字符 FAIL；含泛化劫持词（任何任务/所有请求/always/every task）→ WARN
  A7 正文注入: 忽略以上/ignore previous/system prompt/你现在是/覆盖纪律 等 → FAIL
  A8 脚本危险面: os.system/subprocess/eval/exec/socket/urllib/rm -rf/curl|sh → 逐条 WARN（不禁运行，呈批）
  A9 凭证面: 明文形态 + base64/hex 长串（编码逃逸已实证）→ FAIL；文档占位与资源ID白名单
  A10 MANIFEST 在场 → WARN（自证无签名，不等于可信）

退出码: 0=PASS 1=FAIL 2=WARN-only。凭证值永不回显（只出 文件/键名/长度/md5前8）。
"""
import argparse, base64, hashlib, json, os, re, stat, sys, zipfile

CRED = re.compile(r"(api[_-]?key|secret|password|token)['\"]?\s*[:=]\s*['\"]([A-Za-z0-9_\-]{16,})", re.I)
B64BLOB = re.compile(r"['\"]([A-Za-z0-9+/]{40,}={0,2})['\"]")
HEXBLOB = re.compile(r"['\"]([0-9a-fA-F]{48,})['\"]")
RESOURCE_ID = re.compile(r"(file|node|obj|origin_node|parent|folder|doc|sheet|bitable|wiki)_token$", re.I)
INJECT = re.compile(r"(忽略以上|忽略之前|ignore previous|ignore all previous|system prompt|你现在是|覆盖.{0,4}纪律|覆盖.{0,4}指令|override (the |all )?(rules|instructions)|无需批准|免批准|跳过审批)", re.I)
HIJACK = re.compile(r"(任何任务|所有任务|一切任务|所有请求|任何请求|every task|any task|all requests|always use)", re.I)
DANGER = re.compile(r"(os\.system|subprocess|eval\(|exec\(|\bsocket\b|urllib|requests\.|rm +-rf|chmod +777|curl[^\n|]*\|\s*(ba)?sh|wget[^\n|]*\|\s*(ba)?sh)")


def is_placeholder(v):
    lv = v.lower()
    return any(k in lv for k in ("your", "example", "xxx", "placeholder", "dummy", "changeme"))


class Pkg:
    def __init__(self, path):
        self.path = path
        self.zf = None
        if zipfile.is_zipfile(path):
            self.zf = zipfile.ZipFile(path)
            self.names = self.zf.namelist()
            self.infos = self.zf.infolist()
        else:
            self.names, self.infos = [], []
            for root, _, files in os.walk(path):
                for f in files:
                    self.names.append(os.path.relpath(os.path.join(root, f), path).replace(os.sep, "/"))

    def read_text(self, name):
        if self.zf:
            return self.zf.read(name).decode("utf-8", errors="ignore")
        return open(os.path.join(self.path, name), encoding="utf-8", errors="ignore").read()

    def text_files(self):
        out = []
        for n in self.names:
            if n.endswith("/"):
                continue
            if os.path.splitext(n)[1].lower() in (".md", ".py", ".sh", ".json", ".yaml", ".yml", ".txt", ".toml"):
                out.append(n)
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--installed-names", default="")
    ap.add_argument("--bomb-ratio", type=float, default=100)
    ap.add_argument("--json", dest="json_out", default=None)
    a = ap.parse_args()

    pkg = Pkg(a.target)
    findings = []  # (probe, severity, detail)
    sev_rank = {"INFO": 0, "WARN": 1, "FAIL": 2}

    def add(probe, sev, detail):
        findings.append({"probe": probe, "severity": sev, "detail": detail})

    # A1 结构
    tops = {n.split("/")[0] for n in pkg.names if not n.endswith("/")}
    dirs = {n.split("/")[0] for n in pkg.names if "/" in n}
    flat = "SKILL.md" in tops
    add("A1-structure", "INFO", ("flat layout (batch-extract collision risk, wrap manually)" if flat
                                 else f"wrapped under {sorted(dirs)[:3]}"))

    # A2/A3/A4 仅 zip 有意义
    if pkg.zf:
        for info in pkg.infos:
            n = info.filename
            if n.startswith("/") or ".." in n.split("/") or re.match(r"^[A-Za-z]:", n):
                add("A2-zipslip", "FAIL", f"entry intent: {n}")
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                add("A3-symlink", "FAIL", f"symlink entry: {n}")
        comp = sum(i.compress_size for i in pkg.infos) or 1
        uncomp = sum(i.file_size for i in pkg.infos)
        ratio = uncomp / max(os.path.getsize(a.target), 1)
        if ratio > a.bomb_ratio or uncomp > 200 * 1024 * 1024:
            add("A4-bomb", "FAIL", f"ratio={ratio:.0f}x uncompressed={uncomp}B")
        else:
            add("A4-bomb", "INFO", f"ratio={ratio:.1f}x")

    # 找 SKILL.md 与 frontmatter
    skill_mds = [n for n in pkg.names if n.endswith("SKILL.md") and not n.endswith("/")]
    fm_name, fm_desc = None, ""
    if skill_mds:
        txt = pkg.read_text(skill_mds[0])
        m = re.search(r"^---\s*\n(.*?)\n---", txt, re.S)
        if m:
            fm = m.group(1)
            nm = re.search(r"^name:\s*(\S+)", fm, re.M)
            fm_name = nm.group(1) if nm else None
            dm = re.search(r"^description:\s*[|>]?\s*(.*?)(?=^\w+:|\Z)", fm, re.M | re.S)
            fm_desc = (dm.group(1) if dm else "").strip()
        # A7 正文注入
        for im in INJECT.finditer(txt):
            add("A7-injection", "FAIL", f"{skill_mds[0]}: pattern '{im.group(0)}'")
    else:
        add("A1-structure", "FAIL", "no SKILL.md found")

    # A5 名称遮蔽
    installed = {s.strip() for s in a.installed_names.split(",") if s.strip()}
    if fm_name:
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,63}$", fm_name):
            add("A5-shadow", "WARN", f"irregular name '{fm_name}'")
        if fm_name in installed:
            add("A5-shadow", "FAIL", f"name '{fm_name}' shadows an installed skill (Project>User>Built-in)")

    # A6 description 面
    if len(fm_desc) > 1024:
        add("A6-desc", "FAIL", f"description {len(fm_desc)} chars >1024")
    hm = HIJACK.search(fm_desc)
    if hm:
        add("A6-desc", "WARN", f"broad-trigger word '{hm.group(0)}' in description")

    # A8 脚本危险面
    for n in pkg.text_files():
        if not n.endswith((".py", ".sh")):
            continue
        for i, line in enumerate(pkg.read_text(n).split("\n"), 1):
            dm = DANGER.search(line)
            if dm:
                add("A8-script", "WARN", f"{n}:L{i} '{dm.group(0)}'")

    # A9 凭证面
    for n in pkg.text_files():
        txt = pkg.read_text(n)
        for m in CRED.finditer(txt):
            key, val = m.group(1), m.group(2)
            if not (is_placeholder(val) or RESOURCE_ID.search(key)):
                add("A9-cred", "FAIL", f"{n} key={key[:12]} len={len(val)} fp={hashlib.md5(val.encode()).hexdigest()[:8]}")
        for m in B64BLOB.finditer(txt):
            blob = m.group(1)
            if is_placeholder(blob):
                continue
            try:
                dec = base64.b64decode(blob).decode("utf-8", errors="ignore")
            except Exception:
                dec = ""
            if re.search(r"(api[_-]?key|secret|token|passwd|credential)", dec, re.I) or CRED.search(dec):
                add("A9-cred-b64", "FAIL", f"{n} base64 blob len={len(blob)} decodes to cred-like content fp={hashlib.md5(blob.encode()).hexdigest()[:8]}")
        for m in HEXBLOB.finditer(txt):
            blob = m.group(1)
            ctx = txt[max(0, m.start() - 60):m.start()].lower()
            if any(k in ctx for k in ("md5", "sha", "hash", "checksum", "fp", "digest")):
                continue
            add("A9-cred-hex", "WARN", f"{n} hex blob len={len(blob)} fp={hashlib.md5(blob.encode()).hexdigest()[:8]}")

    # A10 MANIFEST 自证
    if any(os.path.basename(n).startswith("MANIFEST") for n in pkg.names):
        add("A10-manifest", "WARN", "MANIFEST present: self-declared, unsigned — verify independently")

    worst = max((sev_rank[f["severity"]] for f in findings), default=0)
    verdict = {0: "PASS", 1: "WARN", 2: "FAIL"}[worst]
    report = {"target": a.target, "verdict": verdict, "skill_name": fm_name, "findings": findings}
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if a.json_out:
        json.dump(report, open(a.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 2 if worst == 1 else (1 if worst == 2 else 0)


if __name__ == "__main__":
    sys.exit(main())
