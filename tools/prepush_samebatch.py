#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""prepush_samebatch.py —— 预推「同批不变式」守卫（不改共享件，独立可跑）

缘起：轮 21 本席绕过 push_gate（代理不可达时直连推送）而**跳过重签**，
      致 attest-hmac-sha3-512.json 与所推树不同批 → CI「树验证（无钥）」变红。
      本守卫把该判据前移到**推送之前**，以**提交树（blob）**为基准（与 Linux CI 检出语义一致），
      而非工作树——避免 Windows/autocrlf 的 CRLF 干扰。

判据（两自洽 + 三查）：
  L1 结构：file_count == len(files)
  L3 根自洽：由声明叶自举默克尔根 == 声明的根（纯声明值）
  漏声明  ：树里有、manifest 未声明
  声明多余：manifest 声明了、树里没有
  内容不符：树中 blob 的 SHA3-512 ≠ manifest 声明的 content_sha3_512

⚠ 首版踩坑（已修正）：`git ls-tree` 默认 `core.quotepath=true` 会**转义非 ASCII 路径**，
   导致全仓中文路径被误判为「漏声明／声明多余」（实测 257 项假不符）。必须显式
   `-c core.quotepath=false`。

用法:
  python tools/prepush_samebatch.py                 # 校验 HEAD 与 attest-hmac-sha3-512.json
  python tools/prepush_samebatch.py --rev 18c1e4a   # 校验历史提交（回归验证）
退出码：全过 0；不一致 1（并打印修复指引）。
"""
import argparse
import hashlib
import json
import pathlib
import struct
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

REPO = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = "attest-hmac-sha3-512.json"
IGNORE_EXTRA = {DEFAULT_MANIFEST}


def sha3(b: bytes) -> bytes:
    return hashlib.sha3_512(b).digest()


def root_of(leaves):
    level = [bytes.fromhex(h) for h in leaves]
    if not level:
        return ""
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            right = level[i + 1] if i + 1 < len(level) else level[i]
            nxt.append(sha3(b"\x01" + level[i] + right))
        level = nxt
    return level[0].hex()


def git(args):
    p = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, timeout=600)
    return p.stdout, p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    mp = REPO / a.manifest
    if not mp.exists():
        print("★ 未找到 %s（本仓无该证明件，跳过守卫）" % a.manifest)
        return 0
    d = json.loads(mp.read_text(encoding="utf-8"))
    files = {f["path"]: f for f in d.get("files", [])}

    out, code = git(["-c", "core.quotepath=false", "ls-tree", "-r", "--name-only", a.rev])
    if code != 0:
        print("★ 无法读取 rev=%s 的树" % a.rev)
        return 2
    tracked = [x for x in out.decode("utf-8", "replace").split("\n") if x.strip()]

    problems = {
        "extra_declared": [p for p in files if p not in tracked and p not in IGNORE_EXTRA],
        "missing_declared": [p for p in tracked if p not in files and p not in IGNORE_EXTRA],
        "content_mismatch": [],
    }
    # 批量取 blob：单进程 `git cat-file --batch`（首版逐文件调用 → 1878 次子进程，过慢量级）
    want = [p for p in tracked if p in files]
    blobs = {}
    if want:
        payload = ("\n".join("%s:%s" % (a.rev, p) for p in want) + "\n").encode("utf-8")
        proc = subprocess.run(["git", "cat-file", "--batch"], cwd=str(REPO), input=payload,
                              capture_output=True, timeout=900)
        data = proc.stdout
        i = 0
        for p in want:
            nl = data.find(b"\n", i)
            if nl < 0:
                break
            head = data[i:nl].split()
            if len(head) < 3 or head[1] != b"blob":
                break
            size = int(head[2])
            i = nl + 1
            blobs[p] = data[i:i + size]
            i += size + 1
    for p in want:
        blob = blobs.get(p)
        if blob is None:
            problems["content_mismatch"].append(p + "(读 blob 失败)")
            continue
        if sha3(blob).hex() != files[p].get("content_sha3_512"):
            problems["content_mismatch"].append(p)

    ok1 = d.get("file_count") == len(files)
    calc_root = root_of([f.get("leaf_sha3_512", "") for f in files.values()]) if files else ""
    ok_root = bool(d.get("merkle_root_sha3_512")) and calc_root == d["merkle_root_sha3_512"]
    fail = (bool(problems["extra_declared"]) or bool(problems["missing_declared"])
            or bool(problems["content_mismatch"]) or not ok1 or not ok_root)

    print("★ 预推同批守卫（rev=%s，基准=提交树 blob，非工作树）" % a.rev)
    print("")
    print("| 检查 | 结论 | 证据 |")
    print("|---|---|---|")
    print("| L1 结构 | **%s** | file_count=%s len(files)=%d |" % (
        "PASS" if ok1 else "FAIL", d.get("file_count"), len(files)))
    print("| L3 根自洽 | **%s** | 声明=%s… 重算=%s… |" % (
        "PASS" if ok_root else "FAIL",
        str(d.get("merkle_root_sha3_512"))[:16], calc_root[:16]))
    print("| 漏声明（树有而清单无） | **%s** | %d 项%s |" % (
        "PASS" if not problems["missing_declared"] else "FAIL", len(problems["missing_declared"]),
        ("：" + "、".join(problems["missing_declared"][:5])) if problems["missing_declared"] else ""))
    print("| 声明多余（清单有而树无） | **%s** | %d 项%s |" % (
        "PASS" if not problems["extra_declared"] else "FAIL", len(problems["extra_declared"]),
        ("：" + "、".join(problems["extra_declared"][:5])) if problems["extra_declared"] else ""))
    print("| 内容不符（blob 对清单） | **%s** | %d 项%s |" % (
        "PASS" if not problems["content_mismatch"] else "FAIL", len(problems["content_mismatch"]),
        ("：" + "、".join(problems["content_mismatch"][:5])) if problems["content_mismatch"] else ""))
    print("")
    print("VERDICT=" + ("FAIL" if fail else "PASS"))
    if fail:
        print("")
        print("修复指引（勿手改清单字段）：")
        print("  PS> $env:OPL_A2A_HMAC_KEY_B64=[Convert]::ToBase64String([IO.File]::ReadAllBytes($env:USERPROFILE+'\\.a2a-hmac-key.bin'))")
        print("  PS> $env:OPL_A2A_HMAC_KEY_ID='opl-a2a-2026q4'")
        print("  PS> node tools/sha3-tree.mjs build ; git add %s ; git commit -m 'push-gate: re-sign tree'" % a.manifest)
        print("  然后重跑本守卫确认 PASS 再推送。")

    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(
            {"rev": a.rev, "verdict": "FAIL" if fail else "PASS",
             "l1": ok1, "root": ok_root, "problems": problems},
            ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
