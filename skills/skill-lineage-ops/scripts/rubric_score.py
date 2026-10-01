#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rubric_score.py — 达尔文静态 8 维打分器（dim1-7,9；dim8 实测维 23 分留判官）。

用法:
  python3 rubric_score.py <skill_dir> [--json out.json]

口径: 与全舰队 93 件大筛查同一法典（2026-09-11 缄钥定），权重
  d1=7 d2=12 d3=12 d4=6 d5=18 d6=4 d7=12 d9=6，每维 1-10，总分 /770 折百。
校准锚: munger-mind-ops 静态≈判官受评 84.4 量级互参；已知偏差在案——
  短而密件被低估（stat-verdict +18.8）、营销话术不可捕（software-testing -16.4）。
"""
import json, os, re, sys

SOFT_WORDS = ["建议", "可以考虑", "根据情况", "灵活把握", "视情况而定", "酌情", "尽量", "可能的话"]
BANNED_WORDS = ["说白了", "换句话说", "综上所述", "综上", "总的来说", "总而言之",
                "众所周知", "不难发现", "由此可见", "值得注意的是", "首先其次"]
EMPTY_TAIL = ["灵活应用", "根据情况判断", "灵活运用"]
FAIL_PAT = re.compile(r"如果[^\n]{0,40}失败|失败[^\n]{0,20}(→|->|则|时)|fallback|回退|错误恢复|异常处理|报错|处置|错误码|失败分支|出错", re.I)
CHECK_STRONG = re.compile(r"🔴|STOP|CHECKPOINT|检查点")
CHECK_SOFT = re.compile(r"候批|显式批准|逐次批准|确认后|用户确认|机主批准|呈批")
BLACK_PAT = re.compile(r"不要做|禁止|红线|禁令|反模式|不覆盖|绝不|永不|禁入|黑名单|不得")
STEP_PAT = re.compile(r"^\s*(#{1,4}\s*)?(第?\d+[.、)]|步骤\s*\d+|Step\s*\d+|阶段\s*\d+|Phase\s*\d)", re.M | re.I)
INOUT_PAT = re.compile(r"输入|输出|Input|Output", re.I)


def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, text
    fm = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"^(\w[\w.-]*):\s*(.*)$", line)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip().strip('"').strip("'")
    desc = fm.get("description", "")
    if desc in ("|", ">", "|-", ">-", ""):
        block = re.search(r"description:\s*[|>]-?\n((?:\s{2,}.*\n)+)", m.group(1))
        if block:
            desc = " ".join(l.strip() for l in block.group(1).splitlines())
    fm["description"] = desc
    return fm, text[m.end():]


def clamp(x, lo=1, hi=10):
    return max(lo, min(hi, x))


def score(skill_dir):
    path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(path):
        return None
    text = open(path, encoding="utf-8", errors="replace").read()
    fm, body = parse_frontmatter(text)
    lines = text.count("\n") + 1

    d1 = 0
    if fm:
        name = fm.get("name", "")
        if re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", name or ""):
            d1 += 2
        desc = fm.get("description", "")
        if desc:
            d1 += 2
            if len(desc) <= 1024:
                d1 += 2
            if re.search(r"做|处理|生成|管理|分析|创建|查询|蒸馏|评估|Use|used to", desc):
                d1 += 1
            if re.search(r"触发|何时|当用户|Use when|Trigger|用于当", desc):
                d1 += 1
            if any(w in desc[-30:] for w in EMPTY_TAIL):
                d1 -= 2
    d1 = clamp(d1)

    steps = len(STEP_PAT.findall(body))
    d2 = clamp(2 + steps * 1.2 + (1.5 if INOUT_PAT.search(body) else 0))

    fails = len(FAIL_PAT.findall(body))
    d3 = clamp(2 + fails * 1.6) if fails else 2

    strong = len(CHECK_STRONG.findall(body))
    soft = len(CHECK_SOFT.findall(body))
    d4 = clamp(strong * 3 + soft * 1.5) if (strong or soft) else 1

    softc = sum(body.count(w) for w in SOFT_WORDS)
    d5 = clamp(10 - 3 - (softc - 3) * 0.5) if softc >= 3 else clamp(10 - softc * 0.8)

    refs = set(re.findall(r"(?:references|scripts|assets)/[\w./-]+", body))
    d6 = clamp(round(10 * sum(1 for r in refs if os.path.exists(os.path.join(skill_dir, r))) / len(refs))) if refs else 6

    banned = sum(body.count(w) for w in BANNED_WORDS)
    d7 = clamp(10 - banned - (1 if lines > 500 else 0))

    blacks = len(BLACK_PAT.findall(body))
    d9 = clamp(2 + blacks * 1.2) if blacks else 2

    W = {"d1": 7, "d2": 12, "d3": 12, "d4": 6, "d5": 18, "d6": 4, "d7": 12, "d9": 6}
    ds = {"d1": d1, "d2": d2, "d3": d3, "d4": d4, "d5": d5, "d6": d6, "d7": d7, "d9": d9}
    total = sum(ds[k] * W[k] for k in ds)
    return {"skill": os.path.basename(skill_dir), "lines": lines,
            **{k: round(v, 1) for k, v in ds.items()},
            "soft_words": softc, "banned_hits": banned, "fail_signals": fails,
            "refs": len(refs), "steps": steps,
            "static_total": round(total, 1), "static_pct": round(total / 770 * 100, 1),
            "d8_judge_only": "dim8(实测,权重23)不在静态范围,留判官"}


def main():
    r = score(sys.argv[1])
    if r is None:
        print("FAIL: no SKILL.md")
        return 1
    print(json.dumps(r, ensure_ascii=False, indent=1))
    if len(sys.argv) > 3 and sys.argv[2] == "--json":
        json.dump(r, open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
