#!/usr/bin/env python3
"""Fick-Gravity 空间流动/渗透分析器（纯标准库）。

理论渗透通量（引力-扩散形式）：
    flux_i = A_i / (C_i * d_i^2)
  A_i = 源对目的地 i 的引力强度（如岗位吸引力、薪资差、市场规模）
  C_i = 摩擦/成本系数（默认 1；可并入行政、语言、交通成本）
  d_i = 距离（地理/通勤时间/制度距离，须保持全表单位一致）

理论渗透份额 = flux_i / sum(flux)。
若提供 actual（实际渗透量/人数），计算：
    ratio_i       = 实际份额 / 理论份额
    barrier_i     = 1 - ratio_i   （壁垒系数，截断到 >=0）
ratio_i > 1 时该目的地补 "overshoot": true 与 "overshoot_ratio"，
表示实际超理论渗透；此时 barrier=0 是截断结果，禁止误读为零壁垒。
显式传入的 total_actual 小于各 actual 之和时口径矛盾：
输出 {"error": ...} 并 exit 1。

防偏硬条款（本脚本强制输出）：
  壁垒系数由"理论 vs 实际差值"推出，在未经独立数据验证前一律标注
  verification_status="unverified_hypothesis（待验证假设）"，禁止在报告中
  当作已证实结论直接引用；必须先收集独立证据（问卷、行政壁垒清单、
  政策文本等）验证差值确实由壁垒造成，而非模型设定误差。

输入：stdin JSON：
{
  "unit": "km",                       // 距离单位说明（可选，透传）
  "destinations": [
    {"name": "城市B", "A": 120.0, "C": 1.0, "d": 50, "actual": 800},
    {"name": "城市C", "A":  80.0, "C": 1.2, "d": 120, "actual": 150}
  ],
  "total_actual": 950                 // 可选；缺省时用各 actual 之和
}
输出：stdout JSON，含每目的地理论通量/份额/比值/壁垒系数及整体壁垒系数。
"""

import argparse
import json
import os
import subprocess
import sys

UNVERIFIED = "unverified_hypothesis（待验证假设）"


def _run_self(payload):
    """子进程实跑本脚本（stdin JSON→stdout JSON），返回 (exit_code, 输出dict或None)。"""
    r = subprocess.run([sys.executable, os.path.abspath(__file__)],
                       input=json.dumps(payload, ensure_ascii=False),
                       capture_output=True, encoding="utf-8", timeout=60)
    try:
        out = json.loads(r.stdout) if r.stdout.strip() else None
    except json.JSONDecodeError:
        out = None
    return r.returncode, out


def smoke():
    """--smoke 自检：SKILL.md 示例参数正例 + 判官 bug 清单负断言。

    正例：双目的地实跑，断言 barrier_coefficient 与 verification_status
    存在；构造 ratio>1 用例断言 overshoot 标记；
    负断言：total_actual=0 必败（exit!=0 且 error 字段）；
            total_actual 小于分项之和必败（口径矛盾）。
    全过打印 PASS 并返回 0，任一失败打印 FAIL 明细并返回 1。
    """
    checks = []

    # 正例：SKILL.md 步骤4 的示例参数
    code, out = _run_self({"unit": "km", "destinations": [
        {"name": "城市B", "A": 120, "d": 50, "actual": 800},
        {"name": "城市C", "A": 80, "C": 1.2, "d": 120, "actual": 150}]})
    checks.append(("正例 exit==0", code == 0))
    checks.append(("正例 各目的地含 barrier_coefficient 与 verification_status",
                   bool(out) and all(
                       "barrier_coefficient" in d and "verification_status" in d
                       for d in out["destinations"])))

    # 正例（KIMI-B2）：ratio>1 的目的地必须带 overshoot 标记
    code, out = _run_self({"destinations": [
        {"name": "B", "A": 120, "d": 50, "actual": 1000},
        {"name": "C", "A": 80, "C": 1.2, "d": 120, "actual": 10}]})
    checks.append(("超发例 exit==0", code == 0))
    checks.append(("超发例 B 标记 overshoot=true 且 barrier=0",
                   bool(out)
                   and out["destinations"][0].get("overshoot") is True
                   and out["destinations"][0]["barrier_coefficient"] == 0.0))
    checks.append(("超发例 顶层 notes 含误读警示",
                   bool(out) and "非零壁垒误读禁止" in out.get("notes", "")))

    # 负断言（判官 bug 清单）：total_actual=0 必败
    code, out = _run_self({"destinations": [
        {"name": "B", "A": 120, "d": 50, "actual": 800}],
        "total_actual": 0})
    checks.append(("负例 total_actual=0 exit!=0", code != 0))
    checks.append(("负例 total_actual=0 输出 error 字段",
                   bool(out) and "error" in out))

    # 负断言（KIMI-B4）：total_actual 小于分项之和必败（口径矛盾）
    code, out = _run_self({"destinations": [
        {"name": "B", "A": 120, "d": 50, "actual": 800},
        {"name": "C", "A": 80, "d": 120, "actual": 150}],
        "total_actual": 100})
    checks.append(("负例 total_actual<分项之和 exit==1", code == 1))
    checks.append(("负例 total_actual<分项之和 输出口径矛盾 error",
                   bool(out) and "口径矛盾" in str(out.get("error", ""))))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print("smoke[%s] %s" % (name, "OK" if ok else "NG"))
    if failed:
        print("gravity_diffusion.py --smoke FAIL (%s)" % ", ".join(failed))
        return 1
    print("gravity_diffusion.py --smoke PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Fick-Gravity 理论渗透通量与壁垒系数计算（纯标准库）。"
                    "stdin 读 JSON，stdout 写 JSON。",
        epilog="示例: echo '{\"destinations\":[{\"name\":\"B\",\"A\":120,"
               "\"d\":50,\"actual\":800}]}' | python3 gravity_diffusion.py")
    ap.add_argument("--indent", type=int, default=None,
                    help="输出 JSON 缩进空格数（默认紧凑输出）")
    ap.add_argument("--smoke", action="store_true",
                    help="自检模式：内置正负断言套件，全过打印 PASS 并 exit 0")
    args = ap.parse_args()

    if args.smoke:
        sys.exit(smoke())

    try:
        cfg = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        json.dump({"error": "stdin 不是合法 JSON: %s" % e}, sys.stdout,
                  ensure_ascii=False)
        sys.exit(2)

    dests = cfg.get("destinations")
    if not isinstance(dests, list) or not dests:
        json.dump({"error": "缺少非空 destinations 数组"}, sys.stdout,
                  ensure_ascii=False)
        sys.exit(2)

    rows, errors = [], []
    for i, dst in enumerate(dests):
        try:
            name = str(dst.get("name", "dest_%d" % i))
            A = float(dst["A"])
            C = float(dst.get("C", 1.0))
            d = float(dst["d"])
            if A < 0 or C <= 0 or d <= 0:
                raise ValueError("要求 A>=0, C>0, d>0")
            actual = dst.get("actual")
            actual = None if actual is None else float(actual)
            if actual is not None and actual < 0:
                raise ValueError("actual 不能为负")
            rows.append({"name": name, "A": A, "C": C, "d": d,
                         "actual": actual, "flux": A / (C * d * d)})
        except (KeyError, ValueError, TypeError) as e:
            errors.append("destinations[%d]: %s" % (i, e))
    if errors:
        json.dump({"error": errors}, sys.stdout, ensure_ascii=False)
        sys.exit(2)

    flux_sum = sum(r["flux"] for r in rows)
    if flux_sum <= 0:
        json.dump({"error": "理论通量总和为 0，无法归一化"}, sys.stdout,
                  ensure_ascii=False)
        sys.exit(2)

    actuals = [r["actual"] for r in rows]
    has_actual = all(a is not None for a in actuals)
    total_actual = cfg.get("total_actual")
    if has_actual:
        # D8 口径校验：显式传入的 total_actual 不得小于各分项之和
        if total_actual is not None and float(total_actual) < sum(actuals):
            json.dump({"error": "total_actual 小于分项之和，口径矛盾"},
                      sys.stdout, ensure_ascii=False)
            sys.exit(1)
        total_actual = float(total_actual) if total_actual is not None \
            else sum(actuals)
        if total_actual <= 0:
            json.dump({"error": "actual 全提供时 total_actual 必须为正"},
                      sys.stdout, ensure_ascii=False)
            sys.exit(2)

    results = []
    for r in rows:
        theo_share = r["flux"] / flux_sum
        row = {"name": r["name"],
               "theoretical_flux": round(r["flux"], 6),
               "theoretical_share": round(theo_share, 6)}
        if has_actual:
            act_share = r["actual"] / total_actual
            ratio = act_share / theo_share if theo_share > 0 else 0.0
            row.update({
                "actual": r["actual"],
                "actual_share": round(act_share, 6),
                "actual_to_theoretical_ratio": round(ratio, 6),
                "barrier_coefficient": round(max(0.0, 1.0 - ratio), 6),
                "verification_status": UNVERIFIED,
            })
            # 超发标记：ratio>1 时壁垒系数截断为 0，须显式标注防止误读
            if ratio > 1.0:
                row["overshoot"] = True
                row["overshoot_ratio"] = round(ratio, 6)
        results.append(row)

    out = {
        "model": "Fick-Gravity: flux = A / (C * d^2)",
        "distance_unit": cfg.get("unit"),
        "total_theoretical_flux": round(flux_sum, 6),
        "destinations": results,
        "barrier_coefficient_definition": "1 - 实际渗透份额/理论渗透份额（截断到 >=0）",
        "anti_bias_notice": (
            "壁垒系数由理论与实际差值推得，属循环论证高风险量；在收集独立证据"
            "（壁垒清单/问卷/政策文本）验证前，只能作为待验证假设引用，"
            "不得当作已证实结论，也不得给估算参数标实证级置信度。"),
        "notes": "barrier=0 且 overshoot=true 表示实际超理论渗透，"
                 "非零壁垒误读禁止",
    }
    if has_actual:
        theo_total_share = 1.0
        overall_ratio = 1.0  # 份额总和均为 1，整体比值恒为 1
        # 有含义的整体指标：各地壁垒系数按理论份额加权
        overall_barrier = sum(
            r["barrier_coefficient"] * r["theoretical_share"]
            for r in results)
        out["overall"] = {
            "total_actual": total_actual,
            "weighted_barrier_coefficient": round(overall_barrier, 6),
            "verification_status": UNVERIFIED,
            "note": "按理论份额加权的平均壁垒系数；individual 值更有意义",
        }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=args.indent)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
