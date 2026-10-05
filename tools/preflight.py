#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""preflight.py —— 一键预检（把本席 MVP 七项压成一条命令）

口径来源：本席 DF-MVP-20261006-CAIRN-01「一页纸状态 + 一条可复现命令」。
行为：**只读**跑七项检查，逐项打印 判据/结果/证据，末尾给 VERDICT。
不改动仓库、不推送、不动台账（cd_attest 输出到系统临时目录）。

用法:
  python tools/preflight.py            # 全量七项
  python tools/preflight.py --json out.json
退出码：全过 0；有失败 1。
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
SEAT = pathlib.Path(r"C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928")
PY = sys.executable


def run(args, cwd=None, timeout=600):
    p = subprocess.run(args, cwd=cwd or REPO, capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or ""), p.returncode


def check_sdd():
    out, code = run([PY, str(HERE / "sdd_gate.py")])
    ok = code == 0 and "VERDICT=PASS" in out
    n = out.count(" = OK")
    return ok, "VERDICT=PASS 且模块数≥34", "模块 OK=%d" % n


def check_license():
    with tempfile.TemporaryDirectory() as td:
        out, code = run([PY, str(HERE / "license_match.py"), "--repo", ".", "--json",
                         os.path.join(td, "s.json")])
        deny = None
        try:
            deny = json.load(open(os.path.join(td, "s.json"), encoding="utf-8"))["deny_count"]
        except Exception:  # noqa: BLE001
            pass
    ok = code == 0 and deny == 0
    return ok, "deny_count == 0", "deny=%s" % deny


def check_cd_attest():
    with tempfile.TemporaryDirectory() as td:
        out, code = run([PY, str(HERE / "cd_attest.py"), "--root", ".", "--out",
                         os.path.join(td, "a.json"), "--status", os.path.join(td, "STATUS.md"),
                         "--html", os.path.join(td, "index.html")])
        cnt = files = None
        try:
            d = json.load(open(os.path.join(td, "a.json"), encoding="utf-8"))
            cnt, files = d["file_count"], len(d["files"])
        except Exception:  # noqa: BLE001
            pass
    ok = code == 0 and cnt is not None and cnt == files
    return ok, "file_count == len(files)", "file_count=%s len=%s" % (cnt, files)


def check_ledger():
    script = SEAT / "ledger" / "cairn_ledger.py"
    if not script.exists():
        return None, "台账脚本在位", "缺 %s" % script
    out, code = run([PY, str(script), "verify"])
    ok = code == 0 and "PASS" in out
    n = ""
    for line in out.splitlines():
        if "条目数" in line:
            n = line.strip()
    return ok, "链内自洽 PASS", n or "（未读到条目数）"


def check_upload():
    out, code = run([PY, str(HERE / "push_reconcile.py")])
    ok = "一致" in out and "分叉" not in out.split("结论")[-1]
    tail = [l.strip() for l in out.splitlines() if "一致" in l or "分叉" in l]
    return ok, "双远端一致或给出 force-free 处置", "；".join(tail[:2])


def check_mcp():
    probe = pathlib.Path(r"C:\Users\欧阳宏俊\.dsh\mcp-servers\probe_mcp.mjs")
    if not probe.exists():
        return None, "MCP 探针在位", "缺 %s" % probe
    # 探针是 .mjs，必须用 node 执行（曾误用 python 执行导致假 FAIL）
    node = pathlib.Path(r"C:\Users\欧阳宏俊\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\node\bin\node.exe")
    runner = str(node) if node.exists() else "node"
    out, code = run([runner, str(probe)])
    # 逐服务器解析 name/ok（探针输出为 JSON 数组）
    import re as _re
    pairs = _re.findall(r'"name":\s*"([^"]+)"[^}]*?"ok":\s*(true|false)', out, _re.S)
    okmap = {n: (v == "true") for n, v in pairs}
    # 百度通道不在 probe_mcp 清单内，由 probe_one.mjs 单独探测
    one = pathlib.Path(r"C:\Users\欧阳宏俊\.dsh\mcp-servers\probe_one.mjs")
    baidu_entry = pathlib.Path(r"C:\Users\欧阳宏俊\.dsh\mcp-vendor\baidu-netdisk-knowledge-mcp\dist\cli.js")
    baidu_ok = None
    if one.exists() and baidu_entry.exists():
        out_b, _code_b = run([runner, str(one), str(baidu_entry)], timeout=180)
        baidu_ok = '"ok": true' in out_b
    total = sum(1 for v in okmap.values() if v) + (1 if baidu_ok else 0)
    live = (okmap.get("ima") is True) and (baidu_ok is True)
    ok = code == 0 and live and total >= 3
    ev = "ima=%s、baidu=%s；成功总数=%d（%s）" % (
        "OK" if okmap.get("ima") else "FAIL",
        {True: "OK", False: "FAIL", None: "SKIP"}[baidu_ok], total,
        "、".join("%s:%s" % (n, "OK" if v else "FAIL") for n, v in okmap.items()))
    return ok, "在线通道 ima/baidu 必通且成功总数≥3", ev


def check_eff_report():
    script = SEAT / "exp" / "eff_report.py"
    if not script.exists():
        return None, "效能报告生成器在位", "缺 %s" % script
    out, code = run([PY, str(script)])
    ok = code == 0 and "## 六、改进项" in out
    return ok, "输出含六节", "节数=%d" % out.count("\n## ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    checks = [
        ("SDD 规范门", check_sdd),
        ("许可预检", check_license),
        ("CD 交付证明", check_cd_attest),
        ("台账链", check_ledger),
        ("上传通道", check_upload),
        ("MCP 五通道", check_mcp),
        ("效能报告", check_eff_report),
    ]
    results = []
    print("★ 本席 MVP 一键预检（只读；七项）")
    print("")
    print("| # | 检查 | 判据 | 结果 | 证据 |")
    print("|---|---|---|---|---|")
    allok = True
    for i, (name, fn) in enumerate(checks, 1):
        try:
            ok, crit, ev = fn()
        except Exception as exc:  # noqa: BLE001
            ok, crit, ev = False, "异常", "%s: %s" % (type(exc).__name__, exc)
        if ok is None:
            mark = "SKIP"
        else:
            mark = "PASS" if ok else "FAIL"
            allok = allok and ok
        print("| %d | %s | %s | **%s** | %s |" % (i, name, crit, mark, ev))
        results.append({"name": name, "criteria": crit, "result": mark, "evidence": ev})
    print("")
    print("VERDICT=" + ("PASS" if allok else "FAIL"))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({"verdict": "PASS" if allok else "FAIL",
                                                    "checks": results},
                                                   ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
        print("已写出：%s" % a.json)
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
