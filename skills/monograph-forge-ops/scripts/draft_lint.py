#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""draft_lint.py — monograph-forge-ops 写作期口径闸（纯标准库）

用法:
  python3 draft_lint.py <稿目录>            # 全项机械闸
  python3 draft_lint.py --smoke             # 自检（含负断言）

五闸:
  R1 数据表五字段（value/basis/n/src/verified；verified 必为 bool；basis 长度下限）
  R2 正文 %无N（百分比所在句须含样本量锚：N=/n=/数量词/「样本」）
  R3 自指密度（「本报告/本综述」每千字 >2 报）
  R4 工作日志句式（踩坑/一开始…抓错/下载环节/渲染脚本一度 类）
  R5 附录体量闸（附录文件字数 / 正文字数 > 10% 报）

退出码: 0=全绿 1=有 FAIL 2=用法/环境错误。SKIP 项印「跳过≠通过」。
"""
import json, os, re, sys, tempfile

VERIFIED = "verified"
BASIS_MIN = 15  # basis 一句完整口径话的启发式下限（字符）

SELF_REF = ("本报告", "本综述")
LOGLIKE = ("踩坑", "踩了个坑", "抓错", "下载环节", "渲染脚本一度", "脚本一开始", "值得一提的坑")
PCT_RE = re.compile(r"\d+(?:\.\d+)?\s*%|百分之[一二三四五六七八九十\d.]+")
N_ANCHOR = re.compile(r"[Nn]\s*[=＝≈]|约?\d[\d,]*\s*(?:家|个|人|份|名|户|次|篇|条|件|家企业)|样本")
SENT_SPLIT = re.compile(r"[。！？；!?;\n]")


def cjk_len(s):
    return sum(1 for ch in s if ch.strip())


def scan_datatable(path):
    finds = []
    try:
        rows = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return [{"rule": "R1", "sev": "FAIL", "loc": path, "msg": f"数据表不可解析: {e}"}]
    if isinstance(rows, dict):
        rows = rows.get("items") or rows.get("data") or [rows]
    if not isinstance(rows, list):
        return [{"rule": "R1", "sev": "FAIL", "loc": path, "msg": "数据表顶层不是数组"}]
    for i, r in enumerate(rows):
        rid = r.get("id", f"#{i}") if isinstance(r, dict) else f"#{i}"
        if not isinstance(r, dict):
            finds.append({"rule": "R1", "sev": "FAIL", "loc": f"{path}:{rid}", "msg": "记录不是对象"})
            continue
        for k in ("value", "basis", "n", "src", VERIFIED):
            if k not in r:
                finds.append({"rule": "R1", "sev": "FAIL", "loc": f"{path}:{rid}", "msg": f"缺字段 {k}"})
        if VERIFIED in r and not isinstance(r[VERIFIED], bool):
            finds.append({"rule": "R1", "sev": "FAIL", "loc": f"{path}:{rid}", "msg": "verified 非 bool"})
        b = r.get("basis")
        if isinstance(b, str) and cjk_len(b) < BASIS_MIN:
            finds.append({"rule": "R1", "sev": "FAIL", "loc": f"{path}:{rid}", "msg": f"basis 过短({cjk_len(b)}<{BASIS_MIN})，疑非一句完整口径话"})
    return finds


def scan_text(path, body_total):
    text = open(path, encoding="utf-8").read()
    finds = []
    body_total[0] += cjk_len(text)
    # R2 %无N
    for ln, line in enumerate(text.splitlines(), 1):
        if not PCT_RE.search(line):
            continue
        for sent in SENT_SPLIT.split(line):
            if PCT_RE.search(sent) and not N_ANCHOR.search(sent):
                finds.append({"rule": "R2", "sev": "FAIL", "loc": f"{path}:{ln}",
                              "msg": f"%无N: {sent.strip()[:40]}"})
    # R3 自指密度（以全目录汇总，见 aggregate）
    # R4 工作日志句式
    for ln, line in enumerate(text.splitlines(), 1):
        for w in LOGLIKE:
            if w in line:
                finds.append({"rule": "R4", "sev": "FAIL", "loc": f"{path}:{ln}", "msg": f"工作日志句式「{w}」"})
    return finds


def lint(root):
    report = {"root": root, "findings": [], "skips": []}
    md, appendix, datatables = [], [], []
    for dp, dns, fns in os.walk(root):
        if "upstream" in dp.split(os.sep):
            continue
        for fn in fns:
            p = os.path.join(dp, fn)
            if fn.endswith(".md"):
                (appendix if ("附录" in fn or "appendix" in fn.lower()) else md).append(p)
            elif fn in ("数据表.json", "datatable.json", "data.json"):
                datatables.append(p)
    body_total = [0]
    for p in sorted(md):
        report["findings"] += scan_text(p, body_total)
    app_total = 0
    for p in sorted(appendix):
        t = open(p, encoding="utf-8").read()
        app_total += cjk_len(t)
        report["findings"] += scan_text(p, body_total)
    if not datatables:
        report["skips"].append("R1 数据表：未找到 数据表.json —— 跳过≠通过")
    else:
        for p in sorted(datatables):
            report["findings"] += scan_datatable(p)
    # R3 自指密度（全目录聚合）
    alltext = "".join(open(p, encoding="utf-8").read() for p in sorted(md))
    total = max(body_total[0], 1)
    cnt = sum(alltext.count(w) for w in SELF_REF)
    if cnt / (total / 1000.0) > 2:
        report["findings"].append({"rule": "R3", "sev": "FAIL", "loc": "<aggregate>",
                                   "msg": f"自指密度 {cnt}/约{total}字 = {cnt * 1000.0 / total:.1f}‰ > 2‰"})
    # R5 附录体量闸
    if appendix and body_total[0] > 0:
        ratio = app_total / body_total[0]
        if ratio > 0.10:
            report["findings"].append({"rule": "R5", "sev": "FAIL", "loc": "<aggregate>",
                                       "msg": f"附录体量 {app_total}/正文 {body_total[0]} = {ratio:.0%} > 10%"})
    return report


def emit(rep):
    fails = [f for f in rep["findings"] if f["sev"] == "FAIL"]
    for s in rep["skips"]:
        print("SKIP:", s)
    for f in rep["findings"]:
        print(f'{f["sev"]} {f["rule"]} {f["loc"]} :: {f["msg"]}')
    print(f"\n== draft_lint: {len(fails)} FAIL, {len(rep['skips'])} SKIP ==")
    return 1 if fails else 0


def smoke():
    ok = True
    with tempfile.TemporaryDirectory() as td:
        good = os.path.join(td, "good"); bad = os.path.join(td, "bad")
        os.makedirs(good); os.makedirs(bad)
        json.dump([{"id": "E1", "value": "7%",
                    "basis": "951 家受访企业中跑通全自主 agent 的比例，按是否生产环境全链路无人工接管计",
                    "n": "951 家企业，2026Q2 调研", "src": "Bain, 2026", "date": "2026-08-01", "verified": True}],
                  open(os.path.join(good, "数据表.json"), "w", encoding="utf-8"), ensure_ascii=False)
        open(os.path.join(good, "正文.md"), "w", encoding="utf-8").write(
            "第一章 发现\n\n951 家企业里 7% 跑通全自主 agent（n=951）。\n机制上存在两种竞争假说。\n" * 30)
        # 坏稿：R1 缺字段+verified 非 bool+basis 过短；R2 %无N；R3 自指密；R4 日志句；R5 附录超重
        json.dump([{"id": "E1", "value": "7%", "basis": "很少", "verified": "yes"}],
                  open(os.path.join(bad, "数据表.json"), "w", encoding="utf-8"), ensure_ascii=False)
        open(os.path.join(bad, "正文.md"), "w", encoding="utf-8").write(
            "第一章\n\n多数企业（73%）正在部署 agent。本报告认为这很严重。下载环节踩坑：抓错了 5 份文件。\n" * 20)
        open(os.path.join(bad, "附录.md"), "w", encoding="utf-8").write("口径长文\n" * 2000)

        rep_g = lint(good)
        if any(f["sev"] == "FAIL" for f in rep_g["findings"]):
            ok = False; print("SMOKE-NEG 好稿误报:", rep_g["findings"][:3])
        rep_b = lint(bad)
        rules = {f["rule"] for f in rep_b["findings"] if f["sev"] == "FAIL"}
        for want in ("R1", "R2", "R4", "R5"):
            if want not in rules:
                ok = False; print(f"SMOKE-NEG 坏稿漏检 {want}")
        if emit(rep_g) != 0: ok = False; print("SMOKE-NEG 好稿 exit != 0")
        if emit(rep_b) != 1: ok = False; print("SMOKE-NEG 坏稿 exit != 1")
    print("SMOKE", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--smoke":
        sys.exit(smoke())
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        print(__doc__); sys.exit(2)
    sys.exit(emit(lint(sys.argv[1])))
