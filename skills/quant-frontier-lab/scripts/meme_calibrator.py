#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meme_calibrator.py — meme_strength 真实热度校准器。

严肃等级: L1（教学级原型）。合规与诚实纪律（写入 docstring 即为纪律）：
  - 本脚本【不爬取任何登录墙/需授权内容】，不绕过反爬，不伪造 UA 批量抓取。
  - 仅消费【合规公开信号】：调用方通过 web_search 获得的搜索结果计数、
    公开指数页（如公开趋势页）由人工录入的数值。信号一律由调用方提供，
    脚本只做校准计算，不自行联网。
  - 校准结果一律标注 conf="估算"：它是信号加权的启发式修正，非官方统计。
  - 每条输入信号必须带采样记录（来源类型/查询词/采样时间），输出附采样记录表。

校准模型（透明启发式，非黑盒）：
  calibrated = base × (1 + Σ w_i × norm_i)
    norm_search = log1p(search_count) / log1p(NORM_SEARCH_REF)
    norm_index  = index_value / NORM_INDEX_REF
  权重默认 w_search=0.15, w_index=0.20，可由输入覆盖。
  修正幅度截断到 ±50%，防止单一信号主导（防炒作信号过冲）。

输入（stdin JSON）:
{
  "entries": [
    {"school": "示例中学", "base_score": 72.0,
     "signals": [
        {"type": "search_count", "query": "示例中学 中考", "count": 185000,
         "sampled_at": "2026-08-24"},
        {"type": "public_index", "source": "公开趋势页(人工录入)", "value": 3200,
         "sampled_at": "2026-08-24"}
     ]}, ...
  ],
  "weights": {"search_count": 0.15, "public_index": 0.20}   # 可选覆盖
}

输出（stdout JSON）:
  每校：base_score、各信号归一化贡献、calibrated_score、conf="估算"；
  全局：sampling_log 采样记录表 + honesty 等级 + 合规纪律复述。

冒烟：python3 meme_calibrator.py --smoke
"""
import json
import math
import os
import subprocess
import sys

NORM_SEARCH_REF = 100000   # 搜索结果计数参考量级
NORM_INDEX_REF = 5000      # 公开指数参考量级
MAX_ADJUST = 0.50          # 修正幅度上限 ±50%
DEFAULT_WEIGHTS = {"search_count": 0.15, "public_index": 0.20}

COMPLIANCE = ("合规纪律：本脚本不爬取登录墙/需授权内容，不自行联网；"
              "仅处理调用方提供的合规公开信号（web_search 结果计数、"
              "人工录入的公开指数页数值）；所有输出 conf='估算'，"
              "为启发式校准，非官方统计。")
HONESTY = {"level": "L1", "unverified": True, "conf": "估算", "note": COMPLIANCE}


def norm_signal(sig):
    """返回 (归一化值, 说明)。非法/缺字段信号返回 None 并记警告。"""
    t = sig.get("type")
    if t == "search_count":
        c = sig.get("count")
        if not isinstance(c, (int, float)) or c < 0:
            return None, "search_count 缺少非负 count"
        return math.log1p(c) / math.log1p(NORM_SEARCH_REF), f"log1p({c})/log1p({NORM_SEARCH_REF})"
    if t == "public_index":
        v = sig.get("value")
        if not isinstance(v, (int, float)) or v < 0:
            return None, "public_index 缺少非负 value"
        return v / NORM_INDEX_REF, f"{v}/{NORM_INDEX_REF}"
    return None, f"未知信号类型 {t!r}（仅支持 search_count / public_index）"


def run(payload):
    weights = dict(DEFAULT_WEIGHTS)
    weights.update(payload.get("weights") or {})
    results, sampling_log = [], []
    for entry in payload["entries"]:
        school = entry["school"]
        base = float(entry["base_score"])
        contribs, warnings = [], []
        total_adj = 0.0
        for sig in entry.get("signals", []):
            sampling_log.append({
                "school": school, "type": sig.get("type"),
                "query_or_source": sig.get("query") or sig.get("source"),
                "raw_value": sig.get("count", sig.get("value")),
                "sampled_at": sig.get("sampled_at", "未标注（建议补录）"),
            })
            norm, desc = norm_signal(sig)
            if norm is None:
                warnings.append(desc)
                continue
            w = weights.get(sig["type"], 0.0)
            contrib = w * norm
            total_adj += contrib
            contribs.append({"type": sig["type"], "norm": round(norm, 4),
                             "weight": w, "contribution": round(contrib, 4),
                             "formula": desc})
        clipped = max(-MAX_ADJUST, min(MAX_ADJUST, total_adj))
        if clipped != total_adj:
            warnings.append(f"修正幅度 {total_adj:.3f} 超 ±{MAX_ADJUST}，已截断（防信号过冲）")
        calibrated = base * (1.0 + clipped)
        results.append({
            "school": school,
            "base_score": base,
            "signal_contributions": contribs,
            "adjustment": round(clipped, 4),
            "calibrated_score": round(calibrated, 2),
            "conf": "估算",
            "warnings": warnings,
        })
    return {"results": results, "sampling_log": sampling_log,
            "weights": weights, "compliance": COMPLIANCE, "honesty": HONESTY}


SMOKE = {
    "entries": [
        {"school": "示例中学", "base_score": 72.0,
         "signals": [
             {"type": "search_count", "query": "示例中学 中考", "count": 185000,
              "sampled_at": "2026-08-24"},
             {"type": "public_index", "source": "公开趋势页(人工录入)",
              "value": 3200, "sampled_at": "2026-08-24"}]},
        {"school": "示范小学", "base_score": 65.0,
         "signals": [
             {"type": "search_count", "query": "示范小学 入学", "count": 42000,
              "sampled_at": "2026-08-24"}]},
        {"school": "无信号学校", "base_score": 50.0, "signals": []},
    ]
}


REQUIRED_FIELDS = ["entries"]
ENTRY_FIELDS = ["school", "base_score"]


def load_payload(stdin):
    """从 stdin 读 JSON payload；解析失败/非对象/缺必填字段 → stderr 友好错误 + exit 2。"""
    try:
        payload = json.load(stdin)
    except json.JSONDecodeError as e:
        print(f"输入错误：stdin 不是合法 JSON（{e}）。"
              "用法：echo '{\"entries\":[{\"school\":...,\"base_score\":...,\"signals\":[...]}]}'"
              " | python3 meme_calibrator.py", file=sys.stderr)
        sys.exit(2)
    if not isinstance(payload, dict):
        print("输入错误：stdin JSON 必须是对象 {...}", file=sys.stderr)
        sys.exit(2)
    missing = [k for k in REQUIRED_FIELDS if k not in payload]
    if missing:
        print(f"输入错误：缺必填字段 {missing}（必填：{REQUIRED_FIELDS}）", file=sys.stderr)
        sys.exit(2)
    for i, entry in enumerate(payload["entries"]):
        if not isinstance(entry, dict):
            print(f"输入错误：entries[{i}] 必须是对象 {{...}}", file=sys.stderr)
            sys.exit(2)
        miss_e = [k for k in ENTRY_FIELDS if k not in entry]
        if miss_e:
            print(f"输入错误：entries[{i}] 缺必填字段 {miss_e}（必填：{ENTRY_FIELDS}）",
                  file=sys.stderr)
            sys.exit(2)
    return payload


def _smoke_checks():
    """--smoke 断言套件：缺必填字段 stdin JSON → exit 2 + stderr 友好报错（不裸堆栈）。"""
    r = subprocess.run([sys.executable, os.path.abspath(__file__)],
                       input='{"entries": [{"base_score": 60}]}',
                       capture_output=True, text=True)
    assert r.returncode == 2, f"缺必填字段退出码 {r.returncode} != 2"
    assert "输入错误" in r.stderr, "缺必填字段未给出友好报错"
    print("[smoke] OK 缺必填字段 stdin JSON → exit 2 友好报错", file=sys.stderr)
    print("[smoke] ALL PASS meme_calibrator", file=sys.stderr)


def main():
    if "--smoke" in sys.argv:
        payload = SMOKE
        result = run(payload)
        _smoke_checks()
    else:
        payload = load_payload(sys.stdin)
        try:
            result = run(payload)
        except (ValueError, KeyError, TypeError) as e:
            print(f"输入错误：{e}", file=sys.stderr)
            sys.exit(2)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
