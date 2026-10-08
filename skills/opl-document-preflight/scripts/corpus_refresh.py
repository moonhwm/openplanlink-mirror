#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""活体语料跨轮漂移监测驱动（opl-document-preflight 监测层，参数化版）。

用法：
  python scripts/corpus_refresh.py --corpus-dir <语料目录> --evidence-dir <证据目录> --run runN [--prev runM]

纪律：只读被检件（唯一 I/O 是 read_bytes）；结论自绑定被检件哈希；
      比对缺字段判 INCOMPARABLE，禁静默跨异名字段回落；
      P6 掩码基线逐轮自动捕获（探针失败仅 WARN 留痕，不阻塞主流程）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ooxml_meta as G  # noqa: E402

# 内容键集：只有这些字段变动才算 DRIFT。时戳键（mtime/fs_mtime_utc/created_*/modified_*）
# 变动归 TOUCH——云客户端会触碰 mtime 而不改字节，混计即假阳性。
CONTENT_KEYS = {"sha3_512", "sha3_512_16", "sha256", "bytes", "zip_crc",
                "nonempty_paras_wt"}

# 默认观测名单（声明语料文件名）；可用 --names-file 覆盖（每行一个文件名）。
DEFAULT_NAMES = [
    "2026-9-25-OpenPlanLink 润色-1 (3).docx",
    "A2A网络全面优化整合架构方案.otl.wpsonline",
    "A2A项目四件套完整文字记录_上.otl.wpsonline",
    "A2A项目四件套完整文字记录_下.otl.wpsonline",
    "A2A项目四件套完整文字记录_中.otl.wpsonline",
    "ima与A2A约束下开源协议补充论证.docx",
    "OpenPlanLink蓝图OTL主文档_党组学术视角.otl",
    "OpenPlanLink全局声明与Agent-to-Agent网络建设纲要.otl.wpsonline",
    "跨生态A2A协作网络体系建设方案_党组学术视角.otl",
    "认证流程章节_MFA与GitHook与编码校验_党组学术视角.otl",
]

# P6 掩码基线默认目标：名单中的真容器 docx（首件）。
DEFAULT_P6_TARGET = DEFAULT_NAMES[0]


def sha16(p: pathlib.Path) -> str:
    return hashlib.sha3_512(p.read_bytes()).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser(description="活体语料跨轮漂移监测驱动")
    ap.add_argument("--corpus-dir", required=True, help="被监测语料目录")
    ap.add_argument("--evidence-dir", required=True, help="产物输出目录")
    ap.add_argument("--run", required=True, help="本轮标签，如 run15")
    ap.add_argument("--prev", help="前轮标签，给出则产比对件")
    ap.add_argument("--names-file", help="观测名单覆盖件（每行一个文件名）")
    ap.add_argument("--p6-target", default=None,
                    help="P6 掩码基线目标文件名（默认名单首件）")
    args = ap.parse_args()

    src = pathlib.Path(args.corpus_dir)
    evid = pathlib.Path(args.evidence_dir)
    evid.mkdir(parents=True, exist_ok=True)
    run, prev = args.run, args.prev

    if args.names_file:
        names = [ln.strip() for ln in
                 pathlib.Path(args.names_file).read_text(encoding="utf-8")
                 .splitlines() if ln.strip()]
    else:
        names = list(DEFAULT_NAMES)

    paths = [str(src / n) for n in names]
    missing = [p for p in paths if not pathlib.Path(p).is_file()]
    out = G.run(paths)
    out["run_label"] = run
    out["missing"] = missing
    out["in_place"] = len(paths) - len(missing)

    op = evid / f"plasma_refresh_{run}.json"
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[{run}] in_place={out['in_place']}/{len(paths)} "
          f"tally={out['tally']} gate_version={out.get('gate_version')}")
    print(f"  finding_codes={out['finding_codes']}")
    print(f"  -> {op.name}")

    # P6 掩码基线：每轮刷新自动捕获（custom/core 仅名称+值长+哈希，真值不落盘）
    p6_target = src / (args.p6_target or DEFAULT_P6_TARGET)
    p6_cur = None
    if p6_target.is_file():
        try:
            subprocess.run([sys.executable,
                            str(pathlib.Path(__file__).resolve().parent
                                / "p6_custom_probe.py"),
                            "--target", str(p6_target),
                            "--out-dir", str(evid), "--label", run],
                           check=True, capture_output=True, text=True)
            p6_cur = json.loads((evid / f"p6_custom_props_{run}.json")
                                .read_text(encoding="utf-8"))
            print(f"  P6 掩码基线 -> p6_custom_props_{run}.json "
                  f"(custom={len(p6_cur['custom'])} core={len(p6_cur['core'])})")
        except Exception as e:  # 探针失败不阻塞刷新主流程，但须留痕
            print(f"  [WARN] P6 基线捕获失败：{type(e).__name__}: {e}")
    else:
        print(f"  [WARN] P6 目标不在场：{p6_target.name}")

    if prev:
        pp = evid / f"plasma_refresh_{prev}.json"
        if not pp.is_file():
            print(f"[BLOCK] 前轮快照不存在：{pp.name}")
            return 2
        a = json.loads(pp.read_text(encoding="utf-8"))
        cmp = G.compare_snapshots(a["reports"], out["reports"],
                                  key="sha3_512", name_field="name")
        cmp["schema"] = "ooxml-meta-snapshot-compare/1"
        cmp["a_run"], cmp["b_run"] = prev, run
        cp = evid / f"plasma_refresh_{run}_vs_{prev}.json"
        cp.write_text(json.dumps(cmp, ensure_ascii=False, indent=2),
                      encoding="utf-8")

        # 第一道：compare_snapshots（按 sha3_512 为键）
        per_item = cmp.get("per_item") or []
        non_same = [r for r in per_item
                    if str(r.get("result", "")).upper() != "SAME"]
        print(f"  vs {prev}: verdict={cmp.get('verdict')} "
              f"same={cmp.get('same_count')}/{cmp.get('total')} "
              f"drift_count={cmp.get('drift_count')} 非SAME={len(non_same)}")
        for r in non_same[:12]:
            print(f"    {r.get('result')} {str(r.get('name'))[:44]}")

        # 第二道：全字段直比（compare 以单键为判据，须另证其余字段亦未动）
        A = {x["name"]: x for x in a["reports"]}
        B = {x["name"]: x for x in out["reports"]}
        shared = sorted(set(A) & set(B))
        fielddiff = {}
        for n in shared:
            ka, kb = set(A[n]), set(B[n])
            d = ([("KEYSET", sorted(ka ^ kb))] if ka != kb else [])
            d += [(k, A[n][k], B[n][k]) for k in sorted(ka & kb)
                  if A[n][k] != B[n][k]]
            if d:
                fielddiff[n] = d
        cmp["full_field_check"] = {
            "shared_names": len(shared),
            "only_in_a": sorted(set(A) - set(B)),
            "only_in_b": sorted(set(B) - set(A)),
            "files_with_field_diff": len(fielddiff),
            "detail": {k: [list(map(str, t)) for t in v]
                       for k, v in fielddiff.items()},
            "tally_equal": a.get("tally") == out.get("tally"),
            "finding_codes_equal": (a.get("finding_codes")
                                    == out.get("finding_codes")),
        }

        drift = sorted(n for n, d in fielddiff.items()
                       if {t[0] for t in d} & CONTENT_KEYS)
        touch = sorted(n for n in fielddiff if n not in drift)
        cmp["drift_touch_split"] = {
            "content_keys": sorted(CONTENT_KEYS),
            "drift": drift,
            "touch": touch,
            "drift_count": len(drift),
            "touch_count": len(touch),
            "rule": "漂移计数只认 content_keys；时戳键变动归 touch，不计入 drift_count",
        }

        # P6 对表：前轮基线在场则逐属性/字段对哈希（仅名称级归因，真值不落盘）
        p6_prev_path = evid / f"p6_custom_props_{prev}.json"
        if p6_prev_path.is_file() and p6_cur:
            pa = json.loads(p6_prev_path.read_text(encoding="utf-8"))

            def _idx(r):
                return {(c.get("name") or c.get("field")): c
                        for c in (r["custom"] + r["core"])}

            ia, ib = _idx(pa), _idx(p6_cur)
            p6_changed = sorted(k for k in set(ia) & set(ib)
                                if ia[k]["value_sha3_16"]
                                != ib[k]["value_sha3_16"])
            p6_gone = sorted(set(ia) - set(ib))
            p6_new = sorted(set(ib) - set(ia))
            cmp["p6_custom_core"] = {"changed": p6_changed, "removed": p6_gone,
                                     "added": p6_new,
                                     "note": "仅名称级归因；真值不落盘"}
            if p6_changed or p6_gone or p6_new:
                print(f"  P6 对表: 变更={p6_changed} 新增={p6_new} "
                      f"缺失={p6_gone}")

        cmp["self_anchor"] = {
            "a": {"file": pp.name, "bytes": pp.stat().st_size,
                  "sha3_512_16": sha16(pp)},
            "b": {"file": op.name, "bytes": op.stat().st_size,
                  "sha3_512_16": sha16(op)},
        }
        cp.write_text(json.dumps(cmp, ensure_ascii=False, indent=2),
                      encoding="utf-8")
        ff = cmp["full_field_check"]
        print(f"  全字段直比: 共有 {ff['shared_names']} 件 · "
              f"差异件 {ff['files_with_field_diff']} · "
              f"tally一致={ff['tally_equal']} "
              f"判据码一致={ff['finding_codes_equal']}")
        print(f"  DRIFT/TOUCH 二分: DRIFT={len(drift)} TOUCH={len(touch)}")
        for n in drift:
            print(f"    [DRIFT] {n[:48]}")
        for n in touch:
            print(f"    [TOUCH] {n[:48]}（内容键未变，不计入漂移）")
        print(f"  -> {cp.name} ({cp.stat().st_size}B {sha16(cp)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
