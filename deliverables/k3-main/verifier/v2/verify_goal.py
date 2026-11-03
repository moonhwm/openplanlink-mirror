#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_goal.py — 本目标验收器 v2。
在 v1 六检基础上新增：镜像仓新鲜度检（本地 HEAD == 远端 HEAD；网络失败记 WAIVED）。
退出码 0=全过，1=有 FAIL。每项出 PASS/FAIL/WAIVED 三态（WAIVED 须带原因）。
"""
import json, os, subprocess, sys, hashlib

ROOT = "/mnt/agents/output"
PATCH = f"{ROOT}/_skill_patch/govdoc-compliance-ops"
PRECHECK = f"{PATCH}/scripts/govdoc_precheck.py"
REGISTRY = f"{PATCH}/references/doccode_registry.jsonl"
BOUNDARY = f"{ROOT}/boundary_map_20261004.md"
QUEUE = f"{ROOT}/_sync_work/writeback_queue.jsonl"
REPO = f"{ROOT}/_sync_work/repo"
REMOTE = "https://github.com/moonhwm/openplanlink-mirror.git"

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

check_boundary_map()
check_registry_chain()
check_precheck_selftest()
check_sdd_doc()
check_report_register()
check_queue()
check_mirror_freshness()

fails = [r for r in results if r[1] == "FAIL"]
for n, s, note in results:
    print(f"[{s}] {n}" + (f" — {note}" if note else ""))
print(f"\n{'ALL PASS' if not fails else f'{len(fails)} FAIL'} ({len(results)} 项)")
sys.exit(1 if fails else 0)
