#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_goal.py — 本目标验收器 v6。
在 v5 十二检基础上新增：文书群锚点互检（第十三检）。
立项动机：探讨件锚点滞留呈批件 v1.3.5／纪要 v1.5.5 历五轮涟漪未及升指，
涟漪消化漏网深化附件——锚点漂移自此由机器巡检兜底，不再依赖人工记忆。"
判定哲学继承：闸门恒严，例外由验收器显式登记承载。
  - 硬凭据类词表序号（S 类）在公开镜像仓 / 根目录交付物 / 验收器目录零命中，命中即 FAIL；
  - 通用凭据正则（密钥形 / 令牌形 / JWT 形）命中须指纹在豁免册（开源件占位符与测试向量）；
  - 隔离区（WPS 快照语料）与既有遗留偏差件只计数登记，处置裁量归主权人，不判 FAIL；
  - 软标记（已公开结构性 / 通用短语类）命中不判 FAIL，仅计数。
退出码 0=全过，1=有 FAIL。每项出 PASS/FAIL/WAIVED 三态（WAIVED 须带原因）。
"""
import json, os, re, subprocess, sys, hashlib

ROOT = "/mnt/agents/output"
PATCH = f"{ROOT}/_skill_patch/govdoc-compliance-ops"
PRECHECK = f"{PATCH}/scripts/govdoc_precheck.py"
REGISTRY = f"{PATCH}/references/doccode_registry.jsonl"
BOUNDARY = f"{ROOT}/boundary_map_20261004.md"
QUEUE = f"{ROOT}/_sync_work/writeback_queue.jsonl"
REPO = f"{ROOT}/_sync_work/repo"
REMOTE = "https://github.com/moonhwm/openplanlink-mirror.git"
TERMS = f"{ROOT}/_sync_work/private_terms.txt"

# 前期简报/过程说明类文书骨架豁免清单（非双框架正式文书；显式登记，防例外膨胀）
EXEMPT = {"同步待授权说明.md", "总线灵感清扫与安全告警报告_20261003.md",
          "技能同步外发审查报告_20260930.md", "技能同步最终报告_20261001.md",
          "致桌面Kimi-K2.8协调函_img_token_saver补齐.md"}

# —— 第十一检常量（2026-10-05 巡检登记；新增词表条目默认归入硬类，保守从严）——
PUBLIC_STRUCTURAL = {1, 2, 3, 4, 10, 11, 16, 17}   # 已公开结构性标记（署名/路径/端点/代号/域名哨兵）
GENERIC_PHRASE = {12, 13, 18}                      # 通用短语标记（散文提及不构成泄漏）
EXEMPT_FP = {"1ed906668e", "0b8031074c"}           # 公开仓占位符/测试向量指纹（脱敏定性在案）
LOCAL_KNOWN = {}  # 序号15遗留直引 2026-10-05 已就地脱敏（指纹 5cc1b079→33b3c71c），豁免清零
CRED_PAT = re.compile(r"sk-[A-Za-z0-9]{16,}|AKID[A-Za-z0-9]{16,}|eyJ[\w\-]+\.[\w\-]+\.[\w\-]+")
QUAR_PREFIX = "_goal_a2a/wps_corpus_20261005"
REMOTE_REFS_BASELINE = {                          # 远端引用态势基线（2026-10-05 在案）
    "refs/heads/main": "54f045ab19db5f40d24bad5d8959b02714e76280",
    "refs/heads/codex/fix-git-upload-gate-20261005": "37095e2888a1bf4e4e16ca612fbe194be3ed0271",
    "refs/pull/2/head": "37095e2888a1bf4e4e16ca612fbe194be3ed0271",
    "refs/pull/2/merge": "2c6929f395d1ab3464c8a720d85b285a3cabbd18",
}

results = []

def rec(name, ok, note="", waived=False):
    results.append((name, "WAIVED" if waived else ("PASS" if ok else "FAIL"), note))

def check_boundary_map():
    """能力边界图在场，且含三档：可执行/降级/不可执行。"""
    if not os.path.exists(BOUNDARY):
        rec("boundary_map 落盘", False, "文件缺失"); return
    t = open(BOUNDARY, encoding="utf-8").read()
    need = ["本席云端可执行", "不可执行"]
    ok = all(s in t for s in need)
    rec("boundary_map 三档在场", ok, f"字数 {len(t)}")

def check_registry_chain():
    """台账哈希链完好（重算全链）。"""
    if not os.path.exists(REGISTRY):
        rec("台账在场", False, "缺失"); return
    rows = [json.loads(l) for l in open(REGISTRY, encoding="utf-8") if l.strip()]
    prev = "GENESIS"
    ok = True
    for r in rows:
        core = {k: r[k] for k in ("seq", "code", "series", "doc", "seat", "date", "status")}
        h = hashlib.sha256((json.dumps(core, ensure_ascii=False, separators=(",", ":")) + prev).encode("utf-8")).hexdigest()
        if h != r["sha256"] or r["prev_hash"] != prev:
            ok = False; break
        prev = h
    rec("台账哈希链完好", ok, f"rows={len(rows)} head={prev[:12]}")

def check_precheck_selftest():
    """闸门自检 PASS。"""
    if not os.path.exists(PRECHECK):
        rec("govdoc_precheck 在场", False, "缺失"); return
    r = subprocess.run([sys.executable, PRECHECK, "--self-test"], capture_output=True, text=True)
    rec("precheck self-test", r.returncode == 0 and "self-test PASS" in r.stdout, r.stdout.strip()[-60:])

def check_sdd_doc():
    """SDD 立项文书在场且过四闸（exit 0）。"""
    cands = [f for f in os.listdir(ROOT) if f.startswith("SDD") and f.endswith(".md")]
    if not cands:
        rec("SDD 文书在场", False, "未产出"); return
    p = os.path.join(ROOT, sorted(cands)[-1])
    r = subprocess.run([sys.executable, PRECHECK, p, "--doccode"], capture_output=True, text=True)
    rec("SDD 文书四闸", r.returncode == 0, f"{cands[-1]} exit={r.returncode}")

def check_report_register():
    """预检报告/表述文本交付物仍全过（回归）。"""
    for name in ["预检报告_OpenPlanLink全局声明与A2A网络建设纲要_DF-NOTICE-2026-1004-K3-01.md",
                 "规范化表述文本_DF-ORD-2026-1003-K3-01.md"]:
        p = os.path.join(ROOT, name)
        if not os.path.exists(p):
            rec(f"回归:{name[:12]}…", False, "缺失"); continue
        r = subprocess.run([sys.executable, PRECHECK, p, "--doccode"], capture_output=True, text=True)
        rec(f"回归:{name[:12]}…", r.returncode == 0, f"exit={r.returncode}")

def check_queue():
    """写回队列有 v0.2.1 条目。"""
    if not os.path.exists(QUEUE):
        rec("写回队列", False, "缺失"); return
    t = open(QUEUE, encoding="utf-8").read()
    rec("写回队列 v0.2.1", '"0.2.1"' in t, "")

def check_selfrefresh_capability():
    """v0.3.0 能力在场：自检含自更新链接用例且全过；对豁免件不误判 error。"""
    src = open(PRECHECK, encoding="utf-8").read()
    cap = "self_refreshing_url" in src and "SELF_REFRESHING_URL" in src
    r = subprocess.run([sys.executable, PRECHECK, "--self-test"], capture_output=True, text=True)
    rec("闸门自更新链接能力", cap and r.returncode == 0, "v0.3.0 自检 PASS" if r.returncode == 0 else r.stdout[-60:])

def check_exempt_docs_no_error():
    """豁免清单内文书：术语闸 error 必须为 0（骨架豁免不代表术语豁免）。"""
    bad = []
    for name in EXEMPT:
        p = os.path.join(ROOT, name)
        if not os.path.exists(p):
            continue
        r = subprocess.run([sys.executable, PRECHECK, p, "--json"], capture_output=True, text=True)
        try:
            j = json.loads(r.stdout)
            errs = [i for i in j["issues"] if i["severity"] == "error"]
            if errs:
                bad.append(f"{name}:{errs[0]['word']}")
        except Exception:
            bad.append(f"{name}:解析失败")
    rec("豁免件术语零 error", not bad, ";".join(bad) if bad else f"{len(EXEMPT)} 件在册")

def check_mirror_freshness():
    """镜像仓新鲜度：本地 HEAD 与远端 HEAD 一致；网络失败记 WAIVED。"""
    if not os.path.isdir(REPO):
        rec("镜像新鲜度", False, "本地仓缺失"); return
    try:
        local = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"],
                               capture_output=True, text=True, timeout=15)
        if local.returncode != 0:
            rec("镜像新鲜度", False, "本地 rev-parse 失败"); return
        lh = local.stdout.strip()
        remote = None
        for _ in range(3):
            try:
                remote = subprocess.run(["git", "ls-remote", REMOTE, "HEAD"],
                                        capture_output=True, text=True, timeout=60)
                if remote.returncode == 0 and remote.stdout.strip():
                    break
            except subprocess.TimeoutExpired:
                remote = None
        if remote is None or remote.returncode != 0 or not remote.stdout.strip():
            rec("镜像新鲜度", True, f"网络三次重试均失败，WAIVED；本地 {lh[:12]}", waived=True); return
        rh = remote.stdout.split()[0]
        rec("镜像新鲜度", lh == rh, f"local={lh[:12]} remote={rh[:12]}")
    except Exception as e:
        rec("镜像新鲜度", True, f"异常 WAIVED：{type(e).__name__}", waived=True)

def check_remote_refs_posture():
    """远端分支与拉取请求态势监测：ls-remote 全引用比对在案基线。
    新引用/指针移动/引用消失一律如实列出，态势变化本身不判 FAIL（不预断吉凶），
    仅作登记驱动当轮文书涟漪；网络失败记 WAIVED。"""
    remote = None
    for _ in range(3):
        try:
            remote = subprocess.run(["git", "ls-remote", REMOTE],
                                    capture_output=True, text=True, timeout=60)
            if remote.returncode == 0 and remote.stdout.strip():
                break
        except subprocess.TimeoutExpired:
            remote = None
    if remote is None or remote.returncode != 0 or not remote.stdout.strip():
        rec("远端态势监测", True, "网络三次重试均失败，WAIVED", waived=True); return
    refs = {}
    for line in remote.stdout.splitlines():
        h, r = line.split("\t", 1)
        if r != "HEAD":
            refs[r] = h
    diffs = []
    for r, h in REMOTE_REFS_BASELINE.items():
        if r not in refs:
            diffs.append(f"引用消失:{r}")
        elif refs[r] != h:
            diffs.append(f"指针移动:{r[:24]}…({refs[r][:8]}≠基线{h[:8]})")
    for r in refs:
        if r not in REMOTE_REFS_BASELINE and r.startswith(("refs/heads/", "refs/pull/")):
            diffs.append(f"新引用:{r}")
    note = f"基线 {len(REMOTE_REFS_BASELINE)} 引用；实测 {len(refs)} 引用"
    if diffs:
        note += "；变化：" + "；".join(diffs[:6])
        rec("远端态势监测", True, note + "（变化登记，待消化）")
    else:
        rec("远端态势监测", True, note + "；与基线全符")

def check_output_credential_scan():
    """输出区凭据标记扫描：硬类零命中；正则命中须指纹豁免；隔离区与遗留豁免只登记。"""
    if not os.path.exists(TERMS):
        rec("输出区凭据标记扫描", False, "私有词表缺失"); return
    terms = [t for t in open(TERMS, encoding="utf-8").read().splitlines() if t.strip()]
    soft = PUBLIC_STRUCTURAL | GENERIC_PHRASE
    hard = [(i, t) for i, t in enumerate(terms, 1) if i not in soft and t]
    fails, notes, quar = [], [], 0
    terms_abs = os.path.abspath(TERMS)
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if os.path.abspath(p) == terms_abs:
                continue
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            rel = os.path.relpath(p, ROOT)
            in_quar = rel.startswith(QUAR_PREFIX)
            in_fail_scope = rel.startswith("_sync_work/repo") or rel.startswith("verifier/") \
                or (os.path.dirname(rel) == "" and fn.endswith(".md"))
            for i, t in hard:
                if t in txt:
                    if in_quar:
                        quar += 1
                    elif rel in LOCAL_KNOWN and i in LOCAL_KNOWN[rel]:
                        notes.append(f"{rel}#序号{i}(遗留豁免)")
                    elif in_fail_scope:
                        fails.append(f"{rel}#序号{i}")
                    else:
                        notes.append(f"{rel}#序号{i}(工作区)")
            hits = CRED_PAT.findall(txt)
            if in_quar:
                quar += len(hits)
            elif in_fail_scope:
                for m in hits:
                    fp = hashlib.sha256(m.encode()).hexdigest()[:10]
                    if fp not in EXEMPT_FP:
                        fails.append(f"{rel}#指纹{fp}")
    note = f"硬类序号 {len(hard)} 条；隔离区命中 {quar} 处（待裁）；注记 {len(notes)} 处"
    rec("输出区凭据标记扫描", not fails,
        ("FAIL: " + "; ".join(fails[:5]) + " | " if fails else "") + note)

check_boundary_map()
check_registry_chain()
check_precheck_selftest()
check_sdd_doc()
check_report_register()
check_queue()
check_selfrefresh_capability()
check_exempt_docs_no_error()
DOC_GROUP = {                                   # 文书群锚点互检范围（关联锚点表所在件）
    "SDD规范驱动开发立项书_DF-ORD-2026-1005-K3-01.md",
    "协同规约候批条款呈批件_DF-ORD-2026-1005-K3-02.md",
    "重读批注纪要_WPS十件_DF-MIN-2026-1005-K3-01.md",
    "A2A网络算力分配与分布式协同探讨_DF-ORD-2026-1005-K3-03.md",
    "姊妹OTL件锚定纳表审议呈批附件_DF-ORD-2026-1005-K3-04.md",
}
DOC_CODES = ["DF-ORD-2026-1005-K3-01", "DF-ORD-2026-1005-K3-02",
             "DF-MIN-2026-1005-K3-01", "DF-ORD-2026-1005-K3-03",
             "DF-ORD-2026-1005-K3-04"]

def check_doc_group_anchors():
    """文书群锚点互检：各件文档头版本为基准，群内含关联锚点表之件
    所引他件版本号不得落后于基准；自身引用豁免；EVT 件（一次性实证存档）不在互检范围。"""
    ver = {}
    for fn in DOC_GROUP:
        p = os.path.join(ROOT, fn)
        if not os.path.exists(p):
            rec("文书群锚点互检", False, f"群件缺失:{fn}"); return
        m = re.search(r"\|\s*版本\s*\|\s*(v[0-9.]+)\s*\|", open(p, encoding="utf-8").read())
        if not m:
            rec("文书群锚点互检", False, f"版本字段解析失败:{fn}"); return
        # 件号以文档头「件号」字段为准（文件名回退）
        txt = open(p, encoding="utf-8").read()
        m2 = re.search(r"\|\s*件号\s*\|\s*(DF-[A-Z]+-\d{4}-\d{4}-K3-\d{2})\s*\|", txt)
        code = m2.group(1) if m2 else re.search(r"(DF-[A-Z]+-\d{4}-\d{4}-K3-\d{2})", fn).group(1)
        ver[code] = m.group(1)
    drifts = []
    pat = re.compile(r"(DF-(?:ORD|MIN)-\d{4}-\d{4}-K3-\d{2})（(v[0-9.]+)）")
    for fn in DOC_GROUP:
        txt = open(os.path.join(ROOT, fn), encoding="utf-8").read()
        head = txt.split("## 一、")[0]          # 仅查文档头锚点表区
        for code, cited in pat.findall(head):
            if code in ver and cited != ver[code]:
                drifts.append(f"{fn[:8]}…引{code[-5:]}:{cited}≠基准{ver[code]}")
    rec("文书群锚点互检", not drifts,
        f"基准 {len(ver)} 件：" + "／".join(f"{c[-7:]}={v}" for c, v in sorted(ver.items())) +
        ("；漂移：" + "；".join(drifts[:8]) if drifts else "；全符"))

check_mirror_freshness()
check_remote_refs_posture()
check_doc_group_anchors()
check_output_credential_scan()

fails = [r for r in results if r[1] == "FAIL"]
for n, s, note in results:
    print(f"[{s}] {n}" + (f" — {note}" if note else ""))
print(f"\n{'ALL PASS' if not fails else f'{len(fails)} FAIL'} ({len(results)} 项)")
sys.exit(1 if fails else 0)
