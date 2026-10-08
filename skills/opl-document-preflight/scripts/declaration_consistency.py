#!/usr/bin/env python3
"""全局声明稿内部一致性预检（cred-clean · fail-closed · 纯标准库）。

用途：对公文类长稿做「同稿内部口径一致性」机检，产出不含任何凭据真值的
结构化报告。解决的实际问题：版本合并会在同一文档内留下重复条款，而重复的
两处文本未必一致（例如目标存储节点清单一处有一处无），执行席位据此会得出
互相矛盾的操作口径。人工通读难以稳定发现，故固化为可复现门。

纪律：
  - 一切输出经 mask() 过滤，凭据形态只报规则名+计数+掩码前缀，绝不回显真值。
  - 覆盖如实披露：因长度门槛未参与比对的段对计入 skipped_short_pairs 并告警，
    不得以「无差异」冒充「已比对」（实测教训，见 skills/EXPERIENCE.md E-26）。
  - fail-closed：口径歧义（包含关系或高相似而不等）或行尾不变量破坏即判 FAIL。

用法：
  python declaration_consistency.py <声明稿路径> [--json 输出] [--threshold 0.60]
                                    [--min-segment-len 40]
退出码：0=PASS/WARN，1=FAIL，2=用法或读取错误。
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import itertools
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCHEMA = "opl-declaration-consistency/1"

SECRET_PATTERNS = (
    ("mac-address", re.compile(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}")),
    ("push-sendkey", re.compile(r"\bsctp[A-Za-z0-9_\-]{8,}")),
    ("aliyun-ak", re.compile(r"\bLTAI[A-Za-z0-9]{6,}")),
    ("openai-sk", re.compile(r"\bsk-[A-Za-z0-9]{8,}")),
    ("bearer-token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}")),
    ("pem-block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("kv-credential", re.compile(
        r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?key"
        r"|token|密码|口令|密钥)\b\s*[:=]\s*[^\s，。、；;]{4,}")),
    ("long-token", re.compile(r"\b[A-Za-z0-9_\-]{40,}\b")),
)

EMOJI = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002B00-\U00002BFF"
    "\U0000FE00-\U0000FE0F"
    "\U0001F1E6-\U0001F1FF"
    "]"
)

URL = re.compile(r"https?://[^\s、）)，。;；\"'<>]+")
CLONE = re.compile(r"git\s+clone\s+(https?://\S+?|[\w./-]+\.git)(?=[、，。\s]|$)")
ACCOUNT = re.compile(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
# 非贪婪：先捉「同一账号粘连两次」。否则 ACCOUNT 会把第二个邮箱吞进域名，
# 使这类版本合并笔误在报告里不可见。
DOUBLED_ACCOUNT = re.compile(
    r"([A-Za-z0-9_.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+?)\1")

AMBIGUITY_RATIO = 0.9
# 包含关系还须满足长度比例，否则「独立成行的短 URL 被长段落包含」会被误判
# 为同条款扩写（实测假阳性：L16 vs L25 比例 0.18、L18 vs L29 比例 0.12）。
CONTAINMENT_MIN_PROPORTION = 0.6


def mask(text: str) -> str:
    """把所有凭据形态替换为掩码，保证报告与日志零真值。"""
    out = text
    for rule, pat in SECRET_PATTERNS:
        out = pat.sub(lambda m, r=rule: f"[MASK:{r}]", out)
    return out


def sha3_16(data: bytes) -> str:
    return hashlib.sha3_512(data).hexdigest()[:16]


def masked_account(raw: str) -> str:
    local, _, domain = raw.partition("@")
    return f"{local[:2]}{'*' * max(0, len(local) - 2)}@{domain}"


def normalize(segment: str) -> str:
    """比对用归一：去零宽/标记符号/空白，统一全角冒号。不改原文。"""
    s = segment.replace("\u200b", "").replace("\U0001f4a1", "").replace("：", ":")
    return re.sub(r"\s+", "", s)


def diff_fragments(a: str, b: str, limit: int = 6) -> dict:
    """给出两处近似段的差异摘要（掩码后），供差分登记引用。"""
    only_a, only_b = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag in ("replace", "delete"):
            only_a.append(mask(a[i1:i2])[:120])
        if tag in ("replace", "insert"):
            only_b.append(mask(b[j1:j2])[:120])
    return {
        "only_in_first": only_a[:limit],
        "only_in_second": only_b[:limit],
        "truncated": len(only_a) > limit or len(only_b) > limit,
    }


def account_shapes(text: str) -> list:
    """账号形态勘查：只报掩码形与粘连重复判定，不报真值。"""
    shapes, seen = [], set()
    for m in DOUBLED_ACCOUNT.finditer(text):
        raw = m.group(1)
        if raw in seen:
            continue
        seen.add(raw)
        shapes.append({
            "masked_form": masked_account(raw),
            "local_len": len(raw.partition("@")[0]),
            "occurrences": 2,
            "concatenated_self_duplicate": True,
            "doubled_span_chars": len(m.group(0)),
        })
    residue = DOUBLED_ACCOUNT.sub(lambda m: m.group(1), text)
    for raw in dict.fromkeys(ACCOUNT.findall(residue)):
        if raw in seen:
            continue
        seen.add(raw)
        shapes.append({
            "masked_form": masked_account(raw),
            "local_len": len(raw.partition("@")[0]),
            "occurrences": residue.count(raw),
            "concatenated_self_duplicate": False,
        })
    return shapes


def inspect(path: Path, threshold: float, min_segment_len: int) -> dict:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    segments = text.split("\r\n")

    crlf = raw.count(b"\r\n")
    bare_lf = raw.count(b"\n") - crlf

    normalized = [(i, normalize(s)) for i, s in enumerate(segments, 1) if normalize(s)]
    exact, divergent, overlap = [], [], []
    skipped_short = 0
    for (i, a), (j, b) in itertools.combinations(normalized, 2):
        if min(len(a), len(b)) < min_segment_len:
            skipped_short += 1
            continue
        ratio = difflib.SequenceMatcher(None, a, b).ratio()
        # 包含关系是「同一条款一处被扩写」的最强信号，不因比率略低而降级。
        contained = a in b or b in a
        if contained and min(len(a), len(b)) / max(len(a), len(b)) < CONTAINMENT_MIN_PROPORTION:
            contained = False
        if ratio >= 1.0 and len(a) == len(b):
            exact.append({"first_line": i, "second_line": j, "norm_len": len(a)})
            continue
        if contained or ratio >= AMBIGUITY_RATIO:
            verdict = "口径歧义(包含关系)" if contained else "口径歧义"
            bucket = divergent
        elif ratio >= threshold:
            verdict, bucket = "部分重叠", overlap
        else:
            continue
        bucket.append({
            "first_line": i,
            "second_line": j,
            "ratio": round(ratio, 4),
            "len_first": len(a),
            "len_second": len(b),
            "containment": contained,
            "verdict": verdict,
            "diff": diff_fragments(a, b),
        })

    urls = URL.findall(text)
    url_counts = Counter(urls)
    clones = CLONE.findall(text)

    secret_hits = {rule: len(pat.findall(text))
                   for rule, pat in SECRET_PATTERNS if pat.findall(text)}

    report = {
        "schema": SCHEMA,
        "source": {
            "name": path.name,
            "bytes": len(raw),
            "sha3_512": hashlib.sha3_512(raw).hexdigest(),
            "sha3_512_16": sha3_16(raw),
            "crlf": crlf,
            "bare_lf": bare_lf,
            "segments": len(segments),
            "nonempty_segments": sum(1 for s in segments if s.strip()),
        },
        "duplication": {
            "exact_pairs": exact,
            "divergent_pairs": divergent,
            "overlap_pairs": overlap,
            "threshold": threshold,
            "min_segment_len": min_segment_len,
            "ambiguity_ratio": AMBIGUITY_RATIO,
            "skipped_short_pairs": skipped_short,
            "compared_segments": len(normalized),
        },
        "links": {
            "url_total": len(urls),
            "url_unique": len(url_counts),
            "url_repeated": {mask(u): c for u, c in url_counts.items() if c > 1},
            "clone_targets": [mask(c) for c in clones],
            "clone_target_count": len(clones),
        },
        "accounts": account_shapes(text),
        "secret_shapes_detected": secret_hits,
        "emoji_present": bool(EMOJI.search(text)),
        "emoji_count": len(EMOJI.findall(text)),
    }

    reasons = []
    if bare_lf != 0:
        reasons.append(f"行尾不变量破坏：bareLF={bare_lf}（应为纯 CRLF）")
    if divergent:
        reasons.append(f"同稿口径歧义：{len(divergent)} 对近似段文本不一致")

    warnings = []
    if exact:
        warnings.append(f"逐字重复条款 {len(exact)} 对（合并痕迹，宜归并或标注版本）")
    if overlap:
        warnings.append(
            f"部分重叠条款 {len(overlap)} 对（相似度介于 {threshold} 与 "
            f"{AMBIGUITY_RATIO} 之间，未达口径歧义判据，宜人工复核）")
    if skipped_short:
        warnings.append(
            f"{skipped_short} 对段因短于 {min_segment_len} 字未参与比对（覆盖缺口，"
            f"非「已比对无差异」；如需全覆盖请下调 --min-segment-len）")
    if report["emoji_present"]:
        warnings.append(f"含表情符号 {report['emoji_count']} 处（正式公文口径宜核）")
    for acc in report["accounts"]:
        if acc["concatenated_self_duplicate"]:
            warnings.append(
                f"账号标识粘连重复：{acc['masked_form']} 形态自粘贴两次"
                f"（跨 {acc['doubled_span_chars']} 字符）")
    if secret_hits:
        warnings.append(
            "稿内含凭据形态 "
            + "、".join(f"{k}×{v}" for k, v in sorted(secret_hits.items()))
            + "（真值不入本报告；出域前须脱敏）")

    report["verdict"] = "FAIL" if reasons else ("WARN" if warnings else "PASS")
    report["fail_reasons"] = reasons
    report["warnings"] = warnings
    return report


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="全局声明稿内部一致性预检（cred-clean）")
    ap.add_argument("path", help="声明稿路径（UTF-8 文本）")
    ap.add_argument("--json", help="报告输出路径（缺省仅打印）")
    ap.add_argument("--threshold", type=float, default=0.60,
                    help="部分重叠判定阈值（缺省 0.60）")
    ap.add_argument("--min-segment-len", type=int, default=40,
                    help="参与比对的最短归一段长（缺省 40；调低可扩大覆盖）")
    args = ap.parse_args(argv)

    path = Path(args.path)
    if not path.is_file():
        print(f"[FAIL] 输入不存在或不可读：{path}", file=sys.stderr)
        return 2
    try:
        report = inspect(path, args.threshold, args.min_segment_len)
    except UnicodeDecodeError as exc:
        print(f"[FAIL] 非 UTF-8 或字节损坏，拒绝猜测编码：{exc}", file=sys.stderr)
        return 2

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8", newline="\n")
        tmp.replace(out)
        print(f"[OK] 报告已落盘 {out} ({out.stat().st_size}B {sha3_16(out.read_bytes())})")

    src, dup = report["source"], report["duplication"]
    print(f"件 {src['name']} {src['bytes']}B sha3_16={src['sha3_512_16']} "
          f"段={src['nonempty_segments']}/{src['segments']} "
          f"CRLF={src['crlf']} bareLF={src['bare_lf']}")
    print(f"比对：参与段 {dup['compared_segments']} · 逐字 {len(dup['exact_pairs'])} 对 · "
          f"分歧 {len(dup['divergent_pairs'])} 对 · 重叠 {len(dup['overlap_pairs'])} 对 · "
          f"未参与(过短) {dup['skipped_short_pairs']} 对")
    for e in dup["exact_pairs"]:
        print(f"  [逐字重复] L{e['first_line']} == L{e['second_line']} "
              f"(norm_len {e['norm_len']})")
    for e in dup["divergent_pairs"] + dup["overlap_pairs"]:
        print(f"  [{e['verdict']}] L{e['first_line']} vs L{e['second_line']} "
              f"ratio={e['ratio']} len {e['len_first']}/{e['len_second']}")
        for side, key in (("仅前者", "only_in_first"), ("仅后者", "only_in_second")):
            for frag in e["diff"][key]:
                print(f"      {side}: {frag}")
    links = report["links"]
    print(f"链接：{links['url_total']} 处 / 去重 {links['url_unique']} · "
          f"clone 目标 {links['clone_target_count']} 个")
    for u, c in links["url_repeated"].items():
        print(f"  [重复链接 x{c}] {u[:96]}")
    for acc in report["accounts"]:
        print(f"  [账号形态] {acc['masked_form']} local_len={acc['local_len']} "
              f"出现{acc['occurrences']}次 粘连自重复={acc['concatenated_self_duplicate']}")
    if report["secret_shapes_detected"]:
        print(f"凭据形态（仅计数）：{report['secret_shapes_detected']}")
    print("表情符号：" + (f"有 {report['emoji_count']} 处"
                        if report["emoji_present"] else "无"))
    for r in report["fail_reasons"]:
        print(f"  FAIL: {r}")
    for w in report["warnings"]:
        print(f"  WARN: {w}")
    print(f"verdict = {report['verdict']}")
    return 1 if report["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
