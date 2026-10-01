#!/usr/bin/env python3
"""Verdict Register 生成/追加工具（留痕硬要求）。
v1.4 2026-09-18 修改人: 女娲delta/任有恒席锻造管线：docstring 用法示例对齐实现（补 --date/--chain≥2、删 [--note]、示 [--threshold-assumption]）；add 补 --source/--grade（对齐 schema original_source/原依据分级，list 输出含两键 .get 防御）；实装 --smoke（依 delta 工单 V1/V2/V9）
v1.3 2026-08-27 修改人: K3：补 --threshold-assumption 对齐 reference schema 双字段；list 改 .get 防御缺键老记录（依 v1.2.2 批判#7）
v1.1 2026-08-25 修改人: Orchestrator (Kimi K3)：增「维持·理由重构」+ --threshold（依 swarm 评估 issue 2/5）
用法:
  python3 verdict_register.py --file vr.json add --city 沈阳 --original 淘汰 --reason "普速24h" \
      --new 候选 --change 翻案 --chain "市直个案年到手约15万" "直飞3h9m每周103班" \
      --by "Orchestrator" --date 2026-XX-XX --evidence stages/raw/st21_shenyang.md [--threshold-assumption ...]
  python3 verdict_register.py --file vr.json list
"""
import argparse, json, os, subprocess, sys, tempfile

CHANGE_TYPES = ["维持", "维持·理由重构", "翻案", "上调", "下调", "存疑待复核"]


def smoke():
    """自检：正例 add+list 全链路（含 original_source 键断言）；负断言 翻案但 --chain 仅 1 条必非零退出。"""
    self_py = os.path.abspath(__file__)
    results = []

    def run(*argv):
        return subprocess.run(
            [sys.executable, self_py, *argv],
            capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)

    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "vr.json")
        # 1. 正例：add 全字段（翻案，chain=2 条，含 --source/--grade）
        r = run("--file", f, "add", "--city", "沈阳", "--original", "淘汰",
                "--reason", "普速24h", "--new", "候选", "--change", "翻案",
                "--chain", "市直个案年到手约15万", "直飞3h9m每周103班",
                "--by", "smoke", "--date", "2026-09-18",
                "--source", "stages/17b-xxx.md", "--grade", "B-")
        ok = r.returncode == 0
        print(f"smoke[add正例] exit={r.returncode} -> {'OK' if ok else 'NG'}")
        results.append(ok)
        # 2. add 后 JSON 含 original_source / original_grade 键
        try:
            reg = json.load(open(f, encoding="utf-8"))
            ok = ("original_source" in reg[0] and "original_grade" in reg[0]
                  and reg[0]["original_source"] == "stages/17b-xxx.md")
        except Exception:
            ok = False
        print(f"smoke[JSON含original_source/original_grade键] -> {'OK' if ok else 'NG'}")
        results.append(ok)
        # 3. 正例：list 全链路
        r = run("--file", f, "list")
        ok = r.returncode == 0 and "沈阳" in r.stdout
        print(f"smoke[list正例] exit={r.returncode} -> {'OK' if ok else 'NG'}")
        results.append(ok)
        # 4. 负断言：翻案但 --chain 仅 1 条 → 非零退出或 stderr 警示
        r = run("--file", f, "add", "--city", "贵阳", "--original", "淘汰",
                "--reason", "工资低", "--new", "观察", "--change", "翻案",
                "--chain", "仅一条孤证", "--by", "smoke", "--date", "2026-09-18")
        ok = r.returncode != 0 or "翻案须" in (r.stderr or "")
        print(f"smoke[翻案chain<2负断言] exit={r.returncode} -> {'OK' if ok else 'NG'}")
        results.append(ok)

    if all(results):
        print(f"verdict_register.py --smoke PASS ({sum(results)}/{len(results)} 用例符合预期)")
        return 0
    print(f"verdict_register.py --smoke FAIL ({sum(results)}/{len(results)} 用例符合预期)")
    return 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    sub = p.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add")
    add.add_argument("--city", required=True)
    add.add_argument("--original", required=True, help="原结论")
    add.add_argument("--reason", required=True, help="原理由原文")
    add.add_argument("--new", required=True, help="新判定")
    add.add_argument("--change", required=True, choices=CHANGE_TYPES)
    add.add_argument("--by", required=True, help="修改人（留痕）")
    add.add_argument("--date", required=True)
    add.add_argument("--evidence", nargs="*", default=[], help="证据文件路径")
    add.add_argument("--chain", nargs="*", default=[], help="证据链（翻案须≥2条）")
    add.add_argument("--flags", nargs="*", default=[], help="红旗")
    add.add_argument("--review-after", default="")
    add.add_argument("--threshold", default="", help="原理由阈值原文")
    add.add_argument("--threshold-assumption", default="", help="原阈值不可得时的假设声明（须配±敏感性）")
    add.add_argument("--source", default="", help="原理由出处（路径/描述），对齐 schema original_source")
    add.add_argument("--grade", default="", help="原依据分级（A/S/B/C/D/E，含 B- 等子档，自由文本），对齐 schema 原依据分级")
    sub.add_parser("list")
    a = p.parse_args()

    reg = []
    if os.path.exists(a.file):
        reg = json.load(open(a.file, encoding="utf-8"))
    if a.cmd == "list":
        for v in reg:
            print(f"{v.get('city','?')}: {v.get('original_verdict','?')} → {v.get('new_verdict','?')} [{v.get('change_type','?')}] by {v.get('modified_by','?')} {v.get('date','?')} | source={v.get('original_source','')} grade={v.get('original_grade','')}")
        return
    if a.change == "翻案" and len(a.chain) < 2:
        sys.exit("翻案须 evidence chain ≥2 条独立证据（--chain）")
    if not a.by:
        sys.exit("缺少修改人 --by（留痕硬要求）")
    reg.append({
        "city": a.city, "original_verdict": a.original, "original_reason": a.reason,
        "new_verdict": a.new, "change_type": a.change,
        "evidence_chain": a.chain, "red_flags": a.flags,
        "modified_by": a.by, "date": a.date,
        "evidence_files": a.evidence, "review_after": a.review_after,
        "original_threshold": a.threshold, "threshold_assumption": a.threshold_assumption,
        "original_source": a.source, "original_grade": a.grade,
    })
    json.dump(reg, open(a.file, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[OK] {a.city}: {a.original} → {a.new} [{a.change}] by {a.by}")

if __name__ == "__main__":
    if sys.argv[1:] == ["--smoke"]:
        sys.exit(smoke())
    main()
