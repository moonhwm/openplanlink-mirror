#!/usr/bin/env python3
"""manifest_diff.py — 比对两份文件清单（期望基线 vs 实际抓取），产出四分类差异报告。

用法:
    python3 manifest_diff.py --expected expected.{json,csv,txt} --actual actual.{json,csv,txt} --out <报告目录>

输入格式（按扩展名自动识别）:
    .json — manifest JSON: {"files": [{"path": "...", "size": 字节或null}, ...]}
            也接受裸列表 [{"path": ..., "size": ...}, ...]
    .csv  — 表头 path,size（size 可空）
    .txt  — 每行 "大小<TAB>路径" 或仅路径

输出（写入 --out 目录）:
    diff_report.md   — 人类可读台账
    diff_report.json — 机器可读结果（summary + 四分类明细）

退出码: 0=一致或无基线外错误, 1=存在差异, 2=输入错误
"""
import argparse
import csv
import json
import os
import sys
import unicodedata


def norm_path(p: str) -> str:
    """路径归一化：NFC、统一分隔符、去前导斜杠、trim。"""
    p = unicodedata.normalize("NFC", str(p)).strip().replace("\\", "/")
    return p.lstrip("/")


def norm_size(v):
    """大小归一化：空/未知 -> None；数字字符串 -> int。"""
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.lower() in ("null", "none", "-", "unknown"):
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def load_manifest(fp: str):
    """加载任意支持格式，返回 {path: size_or_None}（重复路径后者覆盖前者并告警）。"""
    ext = os.path.splitext(fp)[1].lower()
    entries = []
    if ext == ".json":
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        files = data.get("files", data) if isinstance(data, dict) else data
        for it in files:
            entries.append((it.get("path", ""), it.get("size")))
    elif ext == ".csv":
        with open(fp, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                entries.append((row.get("path", ""), row.get("size")))
    elif ext == ".txt":
        with open(fp, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line.strip():
                    continue
                if "\t" in line:
                    size_s, path = line.split("\t", 1)
                    entries.append((path, size_s))
                else:
                    entries.append((line, None))
    else:
        raise ValueError(f"不支持的格式: {fp}（仅 .json/.csv/.txt）")

    out, dup = {}, []
    for path, size in entries:
        p = norm_path(path)
        if not p:
            continue
        if p in out:
            dup.append(p)
        out[p] = norm_size(size)
    if dup:
        print(f"[warn] {fp} 含 {len(dup)} 条重复路径，已按后者覆盖: {dup[:5]}", file=sys.stderr)
    return out


def diff(expected: dict, actual: dict):
    missing, extra, size_mismatch, unverifiable, matched = [], [], [], [], []
    for p, esz in expected.items():
        if p not in actual:
            missing.append({"path": p, "expected_size": esz})
        else:
            asz = actual[p]
            if esz is not None and asz is not None and esz != asz:
                size_mismatch.append({"path": p, "expected_size": esz, "actual_size": asz})
            elif esz is None or asz is None:
                unverifiable.append({"path": p, "expected_size": esz, "actual_size": asz})
            else:
                matched.append({"path": p, "size": esz})
    for p, asz in actual.items():
        if p not in expected:
            extra.append({"path": p, "actual_size": asz})
    return {
        "summary": {
            "expected_total": len(expected),
            "actual_total": len(actual),
            "matched": len(matched),
            "missing": len(missing),
            "extra": len(extra),
            "size_mismatch": len(size_mismatch),
            "unverifiable": len(unverifiable),
        },
        "missing": sorted(missing, key=lambda x: x["path"]),
        "extra": sorted(extra, key=lambda x: x["path"]),
        "size_mismatch": sorted(size_mismatch, key=lambda x: x["path"]),
        "unverifiable": sorted(unverifiable, key=lambda x: x["path"]),
    }


def fmt_size(v):
    return "未知" if v is None else str(v)


def render_md(result: dict, expected_fp: str, actual_fp: str) -> str:
    s = result["summary"]
    lines = [
        "# 文件清单比对台账",
        "",
        f"- 基线: `{expected_fp}`（{s['expected_total']} 条）",
        f"- 实际: `{actual_fp}`（{s['actual_total']} 条）",
        f"- 结论: ✅ 一致 {s['matched']} / ❌ 缺失 {s['missing']} / ➕ 多余 {s['extra']} / ⚠️ 大小不符 {s['size_mismatch']} / ❓ 不可核验 {s['unverifiable']}",
        "",
    ]
    def section(title, rows, header, row_fn):
        if not rows:
            return
        lines.extend([f"## {title}（{len(rows)}）", "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)])
        for r in rows:
            lines.append("| " + " | ".join(row_fn(r)) + " |")
        lines.append("")
    section("❌ 缺失（基线有、实际无）", result["missing"], ["路径", "期望大小(字节)"],
            lambda r: [r["path"], fmt_size(r["expected_size"])])
    section("➕ 多余（实际有、基线无）", result["extra"], ["路径", "实际大小(字节)"],
            lambda r: [r["path"], fmt_size(r["actual_size"])])
    section("⚠️ 大小不符", result["size_mismatch"], ["路径", "期望", "实际"],
            lambda r: [r["path"], fmt_size(r["expected_size"]), fmt_size(r["actual_size"])])
    section("❓ 不可核验（一侧大小未知）", result["unverifiable"], ["路径", "期望", "实际"],
            lambda r: [r["path"], fmt_size(r["expected_size"]), fmt_size(r["actual_size"])])
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected", required=True)
    ap.add_argument("--actual", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    try:
        expected = load_manifest(args.expected)
        actual = load_manifest(args.actual)
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(f"[error] 输入读取失败: {e}", file=sys.stderr)
        sys.exit(2)

    result = diff(expected, actual)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "diff_report.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "diff_report.md"), "w", encoding="utf-8") as f:
        f.write(render_md(result, args.expected, args.actual))

    s = result["summary"]
    print(json.dumps(s, ensure_ascii=False))
    sys.exit(1 if (s["missing"] or s["extra"] or s["size_mismatch"]) else 0)


if __name__ == "__main__":
    main()
