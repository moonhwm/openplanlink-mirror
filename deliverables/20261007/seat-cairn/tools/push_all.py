# -*- coding: utf-8 -*-
"""push_all.py —— 双路径推送与三面核验（本席推送例程，固化轮11教训）

缘起（本席轮11实测）：同一时刻 `github.com` **直连不通(000)、经代理 curl 200**，
但 **git push 经代理失败(21s 超时) 而直连成功** ⇒ 通路行为**依客户端/协议而异、且随时间变**，
不得只试一路。本工具：
  1. 逐远端依次尝试 **经代理 → 直连**（谁成功记谁），失败再换路；
  2. 推送后 `ls-remote` **实查真值**并核 **三面一致**（local／origin／gitcode）；
  3. 打印**通路矩阵**（每远端 × 每路径 的成功/失败），供事后复盘；
  4. 默认**绝不 force**（仅当显式 `--force-gitcode` 且远端为其镜像位时才允许）。

用法:
  python push_all.py                 # 推 origin 与 gitcode（自动双路径）
  python push_all.py --remotes origin
  python push_all.py --dry-run       # 只打印计划与当前三面，不推送
退出码：三面一致 0；否则 3。
"""
import argparse
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

REPO = pathlib.Path(r"C:\Users\欧阳宏俊\openplanlink-mirror")
ROUTES = [("经代理", []), ("直连", ["-c", "http.proxy=", "-c", "https.proxy="])]
DEFAULT_REMOTES = ["origin", "gitcode"]


def git(args, timeout=180):
    try:
        p = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return (p.stdout or "") + (p.stderr or ""), p.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 1


def local_head():
    out, _ = git(["rev-parse", "--short", "HEAD"])
    return out.strip()


def remote_head(remote, route_args):
    out, code = git([*route_args, "ls-remote", remote, "refs/heads/main"], timeout=90)
    if code == 0 and out.strip():
        return out.split()[0][:7]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remotes", nargs="*", default=DEFAULT_REMOTES)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-gitcode", action="store_true",
                    help="仅 gitcode 镜像位允许 force（origin 永不 force）")
    a = ap.parse_args()

    head = local_head()
    print("★ 本地 HEAD = %s" % head)
    matrix = {}
    for r in a.remotes:
        for name, args in ROUTES:
            h = remote_head(r, args)
            matrix[(r, name)] = h
    print("★ 通路矩阵（ls-remote 实查）：")
    for (r, name), h in matrix.items():
        print("   %-8s %-6s → %s" % (r, name, h or "不可达"))

    if a.dry_run:
        print("★ dry-run：不推送")
        return 0

    pushed = {}
    for r in a.remotes:
        ok = False
        for name, args in ROUTES:
            cmd = [*args, "push", r, "main"]
            if r == "gitcode" and a.force_gitcode:
                cmd.insert(len(args) + 1, "--force")
            out, code = git(cmd, timeout=300)
            good = (code == 0) and (("main -> main" in out) or ("up-to-date" in out) or ("Everything up-to-date" in out))
            print("   %-8s %-6s → %s" % (r, name, "成功" if good else "失败"))
            if good:
                pushed[r] = name
                ok = True
                break
        if not ok:
            pushed[r] = None
            print("   ★ 警告：%s 两条路径均失败" % r)

    print("★ 推送路径记录：%s" % "、".join("%s=%s" % (k, v or "失败") for k, v in pushed.items()))

    local = local_head()
    heads = {}
    for r in a.remotes:
        h = None
        for name, args in ROUTES:
            h = remote_head(r, args)
            if h:
                break
        heads[r] = h
    print("★ 三面核验：local=%s ｜ %s" % (local, " ｜ ".join("%s=%s" % (k, v or "?") for k, v in heads.items())))
    aligned = all(v == local for v in heads.values()) and bool(heads)
    print("VERDICT=" + ("ALIGNED" if aligned else "MISALIGNED"))
    return 0 if aligned else 3


if __name__ == "__main__":
    sys.exit(main())
