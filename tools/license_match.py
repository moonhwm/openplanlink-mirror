#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""license_match.py —— 开源协议条款匹配与声明一致性预检

用途（对应主权人令「开源协议条款匹配」「格式合规性预检」）：
  1. 识别仓库**声明面**：根 LICENSE 身份、NOTICE 沿革、SBOM 组件许可表；
  2. 扫描**文件面**：各级 LICENSE* 文件的实际许可类型、SPDX 头命中数；
  3. **匹配**：文件面 vs 声明面 → 判定「一致 / 冲突 / 未声明 / 不适格」；
  4. 输出一页纸报告（Markdown），并在发现不适格或冲突时给出处置建议。

判据口径（承守藏席 DF-EFF-20261006-SHOUCANG-01 §五 与本仓 NOTICE/SBOM）：
  - 本仓软件：AGPL-3.0（2026-10-03 由 MIT 升级，原 MIT 副本权利不受影响）
  - 服务栈敏感：SSPL-1.0；文档：CC BY-SA 4.0；数据集：ODbL-1.0
  - **GPL-3.0 不适格**（缺 AGPL §13 网络交互条款）

纪律：只读扫描；不改动任何许可文件；发现冲突只登记与建议，不擅自改写。

用法:
  python license_match.py --repo <仓库路径> --out <报告.md>
"""
import argparse
import collections
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

# 许可指纹（顺序敏感：先匹配更具体的）
FINGERPRINTS = [
    ("AGPL-3.0", [r"GNU\s+AFFERO\s+GENERAL\s+PUBLIC\s+LICENSE", r"Version\s+3"]),
    ("LGPL-3.0", [r"GNU\s+LESSER\s+GENERAL\s+PUBLIC\s+LICENSE", r"Version\s+3"]),
    ("GPL-3.0", [r"GNU\s+GENERAL\s+PUBLIC\s+LICENSE", r"Version\s+3"]),  # 注意：AGPL 正文亦含此串，故置于其后
    ("SSPL-1.0", [r"Server\s+Side\s+Public\s+License"]),
    ("Apache-2.0", [r"Apache\s+License", r"Version\s+2\.0"]),
    ("CC-BY-SA-4.0", [r"Creative\s+Commons", r"(ShareAlike|BY-SA)"]),
    ("ODbL-1.0", [r"Open\s+Database\s+License|ODbL"]),
    ("BSD-3-Clause", [r"Redistribution\s+and\s+use\s+in\s+source\s+and\s+binary\s+forms",
                      r"Neither\s+the\s+name"]),
    ("MIT", [r"MIT\s+License", r"Permission\s+is\s+hereby\s+granted,\s+free\s+of\s+charge"]),
]

# 政策：允许 / 不适格 / 待复核
POLICY_ALLOW = {"AGPL-3.0", "SSPL-1.0", "CC-BY-SA-4.0", "ODbL-1.0", "MIT", "Apache-2.0", "BSD-3-Clause"}
POLICY_DENY = {"GPL-3.0": "缺 AGPL §13 网络交互条款；与本仓 AGPL-3.0 主许可不兼容（守藏席 §五 口径）"}

LICENSE_NAME_RE = re.compile(r"^(LICEN[CS]E|COPYING|NOTICE|NOTICE-LICENSE|SBOM|SIGNING)(\..*)?$", re.I)
SPDX_RE = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9.\-+]+)")
TEXT_EXT = {".py", ".mjs", ".js", ".ts", ".md", ".json", ".yml", ".yaml", ".sh", ".ps1", ".html", ".css", ".txt"}


def identify(text: str):
    """按指纹判定许可类型；返回 (类型, 命中证据) 或 (None, '')。"""
    head = text[:20000]
    for name, pats in FINGERPRINTS:
        if all(re.search(p, head, re.I) for p in pats):
            return name, pats[0]
    return None, ""


def declared_from_sbom(sbom_text: str):
    """解析 SBOM.md 组件许可表 → {路径前缀: 许可}。"""
    out = {}
    for line in sbom_text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        comp, lic = cells[0], cells[-2] if len(cells) >= 5 else cells[-1]
        lic_norm = identify(lic)[0] or lic
        if comp and lic_norm and comp not in ("组件", "---"):
            for seg in re.split(r"[/、,，\s]+", comp):
                seg = seg.strip().strip("`")
                if seg and seg not in ("等", "**"):
                    out.setdefault(seg, lic_norm)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default=None)
    ap.add_argument("--json", default=None, help="输出机器可读摘要（CI 用）")
    ap.add_argument("--fail-on-deny", action="store_true",
                    help="发现不适格许可时以退出码 3 失败（默认恒 0，供报告型使用）")
    a = ap.parse_args()

    repo = pathlib.Path(a.repo).resolve()
    if not repo.exists():
        print("★ 仓库不存在：%s" % repo)
        return 2

    # ---- 声明面 ----
    root_lic = None
    root_lic_evidence = ""
    for cand in ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE"):
        p = repo / cand
        if p.exists():
            root_lic, root_lic_evidence = identify(p.read_text(encoding="utf-8", errors="replace"))
            break
    notice = (repo / "NOTICE")
    notice_text = notice.read_text(encoding="utf-8", errors="replace") if notice.exists() else ""
    sbom = (repo / "SBOM.md")
    sbom_text = sbom.read_text(encoding="utf-8", errors="replace") if sbom.exists() else ""
    declared = declared_from_sbom(sbom_text)

    # ---- 文件面 ----
    license_files = []          # (相对目录, 文件名, 识别类型)
    spdx_counter = collections.Counter()
    spdx_files = 0
    scanned = 0
    for p in repo.rglob("*"):
        if not p.is_file() or ".git" in p.parts or "node_modules" in p.parts:
            continue
        if LICENSE_NAME_RE.match(p.name):
            rel_dir = p.parent.relative_to(repo).as_posix()
            typ, _ev = identify(p.read_text(encoding="utf-8", errors="replace"))
            license_files.append((rel_dir, p.name, typ))
        elif p.suffix.lower() in TEXT_EXT:
            scanned += 1
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                continue
            m = SPDX_RE.search(txt)
            if m:
                spdx_counter[m.group(1)] += 1
                spdx_files += 1

    # ---- 匹配 ----
    by_type = collections.Counter(t for _d, _n, t in license_files)
    conflicts = []      # 声明与文件面不一致
    for rel_dir, name, typ in license_files:
        if rel_dir == ".":
            continue
        top = rel_dir.split("/")[0]
        decl = declared.get(top) or declared.get(rel_dir) or declared.get(name)
        if decl and typ and decl != typ:
            conflicts.append((rel_dir, name, typ, decl))
    denies = [(d, n, t) for d, n, t in license_files if t in POLICY_DENY]
    unident = [(d, n) for d, n, t in license_files if t is None]

    lines = []
    lines.append("# 开源协议条款匹配报告（自动生成）")
    lines.append("")
    lines.append("- 仓库：`%s`" % repo)
    lines.append("- 生成器：`license_match.py`（只读扫描，不改动任何许可文件）")
    lines.append("- 政策口径：允许 {%s}；**不适格** {%s}" % (
        "、".join(sorted(POLICY_ALLOW)), "、".join(sorted(POLICY_DENY))))
    lines.append("")
    lines.append("## 一、声明面")
    lines.append("")
    lines.append("| 项 | 实测 |")
    lines.append("|---|---|")
    lines.append("| 根 LICENSE 身份 | **%s**（指纹命中：`%s`） |" % (root_lic or "未识别", root_lic_evidence or "—"))
    lines.append("| NOTICE 在位 | %s |" % ("是" if notice_text else "否"))
    lines.append("| SBOM.md 在位 | %s |" % ("是" if sbom_text else "否"))
    if declared:
        lines.append("| SBOM 组件许可（抽样） | %s |" % "；".join("%s→%s" % (k, v) for k, v in list(declared.items())[:6]))
    lines.append("")
    lines.append("## 二、文件面")
    lines.append("")
    lines.append("| 项 | 实测 |")
    lines.append("|---|---|")
    lines.append("| LICENSE* 文件数 | %d |" % len(license_files))
    lines.append("| 识别分布 | %s |" % ("；".join("%s×%d" % (k, v) for k, v in by_type.most_common()) or "—"))
    lines.append("| 扫描源文件数 | %d |" % scanned)
    lines.append("| 含 SPDX 头文件数 | **%d**（分布：%s） |" % (
        spdx_files, "；".join("%s×%d" % (k, v) for k, v in spdx_counter.most_common()) or "无"))
    lines.append("")
    lines.append("## 三、匹配结论")
    lines.append("")
    if denies:
        lines.append("### 3.1 不适格（须处置）")
        for d, n, t in denies:
            lines.append("- `%s/%s` → **%s**：%s" % (d, n, t, POLICY_DENY.get(t, "")))
    else:
        lines.append("- 不适格：**0**（未发现 %s）" % "、".join(POLICY_DENY))
    lines.append("")
    if conflicts:
        lines.append("### 3.2 声明冲突（文件面 ≠ 声明面）")
        lines.append("")
        lines.append("| 目录 | 文件 | 文件面许可 | 声明面许可 | 判定 |")
        lines.append("|---|---|---|---|---|")
        for d, n, t, decl in conflicts[:40]:
            lines.append("| `%s` | %s | %s | %s | **冲突** |" % (d, n, t, decl))
        if len(conflicts) > 40:
            lines.append("| … | … | … | … | 另 %d 处 |" % (len(conflicts) - 40))
    else:
        lines.append("- 声明冲突：**0**")
    lines.append("")
    if unident:
        lines.append("### 3.3 未识别许可文件")
        for d, n in unident[:20]:
            lines.append("- `%s/%s`" % (d, n))
        lines.append("")
    if spdx_files == 0:
        lines.append("### 3.4 缺口")
        lines.append("- **全仓零 SPDX-License-Identifier 头**：自动化扫描无法按文件级判定许可，"
                     "建议后续统一在源文件首行加 SPDX 标识（不改许可，仅增标识）。")
        lines.append("")
    lines.append("## 四、处置建议")
    lines.append("")
    n_tips = 0
    if conflicts:
        n_tips += 1
        lines.append("%d. 就 §3.2 冲突组织裁定：以 NOTICE/SBOM 声明面为准（本仓 2026-10-03 升级 AGPL-3.0），"
                     "则 `skills/*/LICENSE`（MIT）应统一为 AGPL-3.0 或显式登记为「历史 MIT 副本·仅存证」——"
                     "**本席只提请，不擅自改写他席文件**。" % n_tips)
    if spdx_files == 0:
        n_tips += 1
        lines.append("%d. 逐步补 SPDX 头（建议一次性脚本批量前置，逐件可回滚）。" % n_tips)
    n_tips += 1
    lines.append("%d. 每次上仓前跑本工具：`python license_match.py --repo . --out license-match.md`，"
                 "与 CI 的 `compliance_check.py` / `supply_chain.py` 形成三层预检。" % n_tips)
    lines.append("")
    lines.append("—— 自动生成；只读扫描，未改动任何许可文件。")

    text = "\n".join(lines) + "\n"
    if a.out:
        pathlib.Path(a.out).write_text(text, encoding="utf-8")
        print("已写出：%s（%d 字节）" % (a.out, len(text.encode("utf-8"))))
    else:
        print(text)
    print("★ 摘要：LICENSE 文件 %d；识别分布 %s；SPDX 头 %d 文件；不适格 %d；声明冲突 %d" % (
        len(license_files), dict(by_type), spdx_files, len(denies), len(conflicts)))

    summary = {
        "repo": str(repo),
        "root_license": root_lic,
        "license_files": len(license_files),
        "by_type": dict(by_type),
        "scanned_source_files": scanned,
        "spdx_header_files": spdx_files,
        "deny_count": len(denies),
        "conflict_count": len(conflicts),
        "unidentified_count": len(unident),
    }
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
        print("已写出摘要：%s" % a.json)
    if a.fail_on_deny and denies:
        print("★ 门禁失败：检测到不适格许可 %d 处" % len(denies))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
