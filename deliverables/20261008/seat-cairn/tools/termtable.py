# -*- coding: utf-8 -*-
"""termtable.py —— **议题术语表**（可执行版）：术语一致性校验
（承令条「同步在 Kimi Chat 端部署相应技能，辅助开展**术语一致性校验**」「杜绝术语歧义」）

本器把**研究段第一手发现**与**网络既有判别**固化为**可校验条目**：
  每条＝{术语, 义项[], 原文/档号锚, 状态, 检查规则}

用法：
    python termtable.py list                     # 打印术语表（人读）
    python termtable.py check --mine-only        # 扫本席交换区件
    python termtable.py check --paths <dir>      # 扫指定目录（递归）
    python termtable.py export --json <path>     # 导出机读表
退出码：0＝未命中｜1＝命中（须人工判读）｜2＝用法错误
纪律：**只读、只报告**；**不回显值**；命中仅是**提示**，最终判读在人（承"候选≠判据"）。
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
EXCHANGE = SEAT.parent / "A2A共同体_共享交换区"

# ── 术语表（每条含：义项、锚、状态、检查规则） ─────────────────────────────
TERMS = [
    {
        "term": "价值重估 / Umwertung",
        "senses": [
            {"label": "①主人式·创造价值", "meaning": "自发的价值创造（werteschaffen）", "anchor": "GM I §2, §10"},
            {"label": "②奴隶式·反转价值", "meaning": "以否定外部为出发点的价值反转（Ressentiment 之作）", "anchor": "GM I §7"},
        ],
        "status": "必分列（两义敌对）",
        "check": {"pattern": r"价值重估|Umwertung", "qualifier": r"主人式|奴隶式|创造|反转|分列|两义",
                  "advice": "须注明为「主人式·创造」抑或「奴隶式·反转」（否则同一议题内指称敌对操作）"},
    },
    {
        "term": "自决 / zijue-self-determination",
        "senses": [
            {"label": "①自发型（可）", "meaning": "拥有自己的、独立的、长久意志；可为自身作保", "anchor": "GM II §2（autonom↔sittlich 互斥）"},
            {"label": "②反应型（禁）", "meaning": "以反对外部规定为出发点 ⇒ 结构上即 Ressentiment", "anchor": "GM I §10（Aktion ist von Grund aus Reaktion）"},
        ],
        "status": "定义须取①，禁止取②",
        "check": {"pattern": r"自决[^。\n]{0,20}(反抗|对抗|反对外部|抵制外部)|(反抗|对抗|反对外部)[^。\n]{0,12}自决",
                  "qualifier": r"自发|非反应|非 Ressentiment|不取",
                  "advice": "「自决」不得定义为「反对外部规定」（该结构＝Ressentiment）；宜取「自发型」定义并注明发生学/运作两层"},
    },
    {
        "term": "良心 / Gewissen",
        "senses": [
            {"label": "甲义·债务所生", "meaning": "由债权—惩罚结构生成的内化（他律）", "anchor": "GM II §4, §6"},
            {"label": "乙义·自主者之良心", "meaning": "对自身与命运之支配的意识（自律）", "anchor": "GM II §2"},
        ],
        "status": "必分列",
        "check": {"pattern": r"凭良心|良心的?(自律|他律)|Gewissen",
                  "qualifier": r"甲义|乙义|债务所生|自主者|分列",
                  "advice": "「良心」须注明系「债务所生（他律内化）」抑或「自主者之良心（自律支配）」"},
    },
    {
        "term": "主人道德 / 奴隶道德（Herren-/Sklaven-Moral）",
        "senses": [
            {"label": "作为类型", "meaning": "两种价值规定方式（高贵↔可鄙 / 善↔恶）", "anchor": "JGB §260"},
            {"label": "★并存事实", "meaning": "二者可同处一人一灵魂（sogar im selben Menschen, innerhalb einer Seele）", "anchor": "JGB §260"},
        ],
        "status": "用作二分时须并述「同灵魂并存」",
        "check": {"pattern": r"主人道德|奴隶道德",
                  "qualifier": r"并存|同一灵魂|混|调和|非二元|兼",
                  "advice": "以二者为二分对立时，宜并述 JGB §260「可在同一灵魂内并存」以免绝对化"},
    },
    {
        "term": "打通 / 可用 / 不可用（节点）",
        "senses": [{"label": "规范表述", "meaning": "无入参之节点一律记「未测」；严禁写「可用」亦严禁写「不可用」", "anchor": "DF-CCM-20261007-HY4-01 §四"}],
        "status": "硬纪律",
        "check": {"pattern": r"(Neon|Supabase|WPS|ima|百度网盘|百炼)[^。\n]{0,16}?(可用|不可用|已打通|已接入)",
                  "qualifier": r"未测|未核实|待核|无入参",
                  "advice": "无入参节点须记「未测」；「打通」不等于「常驻可用」"},
    },
    {
        "term": "marginals ≠ joint（边际≠联合）",
        "senses": [{"label": "判别", "meaning": "各维边际成立不推出联合成立；须给出联合口径或声明未测", "anchor": "本席 DF-START6 映射"}],
        "status": "方法论",
        "check": {"pattern": r"各维度?均(已)?(合规|达标|满足)[^。\n]{0,20}(整体|联合|统一)",
                  "qualifier": r"联合|joint|分别|边际",
                  "advice": "「各维均达标」不得径推「整体达标」——须区分 marginal 与 joint"},
    },
    {
        "term": "报告值 ≠ 核实值",
        "senses": [{"label": "判别", "meaning": "「推送/写入报成功」不等于「已核实」；须以独立核验为准", "anchor": "本席自课（多轮实战）"}],
        "status": "本席纪律",
        "check": {"pattern": r"(报成功|报告成功|返回成功)[^。\n]{0,20}(已核实|核实一致|确认一致)",
                  "qualifier": r"未核实|待核|非 live|快照",
                  "advice": "「报成功」与「已核实」须分列（本席 push_all 已按此设计）"},
    },
]


def scan_file(p):
    """两段限定：**行级**（qualifier）或**文档级**（doc_qualifier）命中其一 ⇒ 视为已限定。
    文档级判据承本席自纠：行级判据对"全文已作区分、但某行仅提及术语"者会误报。"""
    hits = []
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits
    lines = text.splitlines()
    for i, ln in enumerate(lines, 1):
        for t in TERMS:
            chk = t["check"]
            m = re.search(chk["pattern"], ln)
            if not m:
                continue
            line_ok = bool(re.search(chk["qualifier"], ln))
            doc_pat = chk.get("doc_qualifier") or chk["qualifier"]
            doc_ok = bool(re.search(doc_pat, text))
            hits.append({"line": i, "term": t["term"], "qualified": line_ok or doc_ok,
                         "qualified_by": ("行级" if line_ok else ("文档级" if doc_ok else "未限定")),
                         "advice": chk["advice"], "masked": ln.strip()[:110]})
    return hits


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    c = sub.add_parser("check")
    c.add_argument("--paths", nargs="*", default=None)
    c.add_argument("--mine-only", action="store_true")
    e = sub.add_parser("export")
    e.add_argument("--json", required=True)
    a = ap.parse_args()

    if a.cmd == "list":
        print("★ 议题术语表（%d 条；每条含义项、锚、状态与检查规则）" % len(TERMS))
        for t in TERMS:
            print("\n■ %s ｜ 状态：%s" % (t["term"], t["status"]))
            for s in t["senses"]:
                print("   - %s：%s（锚：%s）" % (s["label"], s["meaning"], s["anchor"]))
            print("   检查：%s" % t["check"]["advice"])
        return 0

    if a.cmd == "export":
        out = {"schema": "opl-termtable/1", "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S +08"),
               "terms": TERMS}
        pathlib.Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print("★ 已导出机读术语表：%s（%d 条）" % (a.json, len(TERMS)))
        return 0

    roots = [EXCHANGE] if (a.mine_only or not a.paths) else [pathlib.Path(x) for x in a.paths]
    files = []
    for r in roots:
        if r.exists():
            for ext in ("*.otl", "*.md", "*.txt"):
                files += [f for f in r.rglob(ext) if f.is_file()]
    if a.mine_only:
        files = [f for f in files if "CAIRN" in f.name]
    print("★ 术语一致性校验（%s，北京时间）" % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("  范围：%d 文件 ｜ 条目：%d" % (len(files), len(TERMS)))
    total = unqual = 0
    for f in sorted(files):
        hs = scan_file(f)
        if not hs:
            continue
        bad = [h for h in hs if not h["qualified"]]
        total += len(hs); unqual += len(bad)
        print("  · %s：命中 %d，其中**未加限定 %d**" % (f.name, len(hs), len(bad)))
        for h in bad[:2]:
            print("      行%d ｜ %s ｜ %s" % (h["line"], h["term"], h["advice"][:60]))
    print("  ⇒ 合计命中 %d ｜ **须人工判读 %d**（其余经行级或文档级限定）" % (total, unqual))
    print("  VERDICT=" + ("CLEAN" if total == 0 else ("QUALIFIED" if unqual == 0 else "NEEDS_REVIEW")))
    return 1 if unqual else 0


if __name__ == "__main__":
    sys.exit(main())
