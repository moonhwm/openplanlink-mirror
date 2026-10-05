#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""push_reconcile.py —— 双远端一致性诊断与安全修复（不使用 force）

用途：修复 `push_gate` 可能出现的「部分推送失败」——
      双远端推送非原子：一个成功、另一个被拒（他席并发推送）→ 双端不一致。
      本工具**先诊断、后最小动作**：只在快进（fast-forward）可行时补推落后端；
      历史分叉时**不动手**，只报出精确结论并指向 `tools/push_gate.py`（由其重建树证）。

纪律：
  - 全程 **--force 一律不用**；
  - 远端真值以 `git ls-remote` 实查为准（不信任可能过期的本地跟踪引用）；
  - 只读诊断默认：`--dry-run` 为默认行为，需显式 `--apply` 才补推。

用法:
  python tools/push_reconcile.py                 # 只诊断
  python tools/push_reconcile.py --apply         # 诊断 + 快进补推落后端
  python tools/push_reconcile.py --remote gitcode --apply
"""
import argparse
import pathlib
import socket
import subprocess
import sys
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8")

# 代理回退：当 git 配置的 http(s).proxy 不可用时，远程操作自动改为直连
GIT_EXTRA = []


def run(args, cwd):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=300,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "").strip(), (p.stderr or "").strip(), p.returncode


def local_head(repo):
    out, _err, _c = run(["git", "rev-parse", "HEAD"], repo)
    return out


def remote_head(repo, remote):
    """实查远端真值（不依赖本地跟踪引用）。"""
    out, err, code = run(["git", *GIT_EXTRA, "ls-remote", remote, "refs/heads/main"], repo)
    if code != 0 or not out:
        return None, (err or "ls-remote 无输出")
    return out.split()[0], ""


def proxy_state(repo):
    """探测 git 配置的 http(s) 代理端口是否可连。返回 (配置值, 是否活)。"""
    out, _err, _c = run(["git", "config", "--get", "http.proxy"], repo)
    url = out.strip()
    if not url:
        return "", True
    try:
        u = urlparse(url if "://" in url else "http://" + url)
        host = u.hostname or "127.0.0.1"
        port = u.port or 80
        with socket.create_connection((host, port), timeout=1.5):
            return url, True
    except OSError:
        return url, False


def is_ancestor(repo, maybe_ancestor, descendant):
    _out, _err, code = run(["git", "merge-base", "--is-ancestor", maybe_ancestor, descendant], repo)
    return code == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=r"C:\Users\欧阳宏俊\openplanlink-mirror")
    ap.add_argument("--remotes", nargs="*", default=None)
    ap.add_argument("--apply", action="store_true", help="补推落后端（仅快进）")
    ap.add_argument("--merge", action="store_true",
                    help="分叉时以合并方式合流（force-free）；生成件冲突取远端版，随后由 push_gate 重签覆盖")
    ap.add_argument("--generated", nargs="*", default=["attest-hmac-sha3-512.json"],
                    help="可安全取远端版的生成型文件（--merge 时用于解冲突）")
    ap.add_argument("--no-proxy-fallback", action="store_true",
                    help="禁用代理回退（默认：检测到代理端口不可连时，远程操作自动直连）")
    a = ap.parse_args()

    repo = pathlib.Path(a.repo)
    if not (repo / ".git").exists():
        print("★ 非 git 仓库：%s" % repo)
        return 2

    # 代理回退检测（只读探测；不改任何 git 配置）
    proxy_url, alive = proxy_state(str(repo))
    if proxy_url and not alive and not a.no_proxy_fallback:
        GIT_EXTRA.extend(["-c", "http.proxy=", "-c", "https.proxy="])
        print("★ 代理不可达：%s 端口无监听 → 本次远程操作**自动直连**（未改动 git 配置）" % proxy_url)
    elif proxy_url:
        print("★ 代理可用：%s" % proxy_url)

    head = local_head(repo)
    if not head:
        print("★ 无法读取本地 HEAD")
        return 2

    out, _err, _c = run(["git", "remote"], repo)
    remotes = a.remotes or [r for r in out.split() if r]
    print("★ 本地 HEAD = %s" % head[:12])
    print("★ 远端清单 = %s" % "、".join(remotes))

    report = {}
    for r in remotes:
        rh, why = remote_head(repo, r)
        if rh is None:
            report[r] = {"head": None, "state": "不可达", "why": why}
            print("  - %-9s 不可达：%s" % (r, why))
            continue
        if rh == head:
            state = "一致"
        elif is_ancestor(repo, rh, head):
            state = "落后（可快进补推）"
        elif is_ancestor(repo, head, rh):
            state = "领先（本地落后该远端）"
        else:
            state = "分叉（须重建树证）"
        report[r] = {"head": rh, "state": state}
        print("  - %-9s %s  %s" % (r, rh[:12], state))

    lagging = [r for r, v in report.items() if v["state"] == "落后（可快进补推）"]
    diverged = [r for r, v in report.items() if v["state"] in ("分叉（须重建树证）", "领先（本地落后该远端）")]

    print()
    if not lagging and not diverged:
        print("★ 结论：双远端与本地一致，无需动作。")
        return 0

    if diverged:
        print("★ 结论：存在分叉/落后远端：%s" % "、".join(diverged))
        if a.merge:
            base = "origin/main" if "origin" in remotes else "%s/main" % remotes[0]
            print("  --merge：尝试以合并方式合流（base=%s，全程禁 force）" % base)
            out3, err3, code3 = run(["git", "merge", "--no-edit", base], repo)
            print("  merge 退出码=%d" % code3)
            if code3 != 0:
                st, _e, _c = run(["git", "status", "--porcelain"], repo)
                conflicts = [l[3:].strip() for l in st.splitlines() if l[:2] in ("UU", "AA", "DD", "AU", "UA", "DU", "UD")]
                print("  冲突文件：%s" % ("、".join(conflicts) or "（未识别）"))
                resolved = []
                for f in conflicts:
                    if f in a.generated:
                        run(["git", "checkout", "--theirs", f], repo)
                        run(["git", "add", f], repo)
                        resolved.append(f)
                if resolved and len(resolved) == len(conflicts):
                    run(["git", "-c", "user.name=reconcile-bot", "-c", "user.email=reconcile@a2a.local",
                         "commit", "--no-edit"], repo)
                    print("  生成件冲突已按远端版解决并提交：%s（随后应由 push_gate 重签覆盖）" % "、".join(resolved))
                else:
                    run(["git", "merge", "--abort"], repo)
                    print("  ★ 非生成件冲突，已中止合并；须人工处置（本工具不改史）")
                    return 4
            # 合并成功后：本地已含各远端历史 → 各端均为可快进，按 --apply 一并补推
            if a.apply:
                for r in remotes:
                    out4, err4, code4 = run(["git", *GIT_EXTRA, "push", r, "HEAD:main"], repo)
                    print("  %s 合并后补推 → %s" % (r, "OK" if code4 == 0 else "失败"))
                    if code4 != 0:
                        print("      stderr: %s" % (err4 or out4)[:300])
            else:
                print("  处置（未执行，缺 --apply）：`python tools/push_reconcile.py --merge --apply`")
        else:
            print("  处置：`python tools/push_reconcile.py --merge --apply`（合并合流，force-free）")
            print("        或 `python tools/push_gate.py`（fetch→rebase→重签→双推；遇生成件冲突会中止）。")
            return 3
    if lagging:
        print("★ 结论：远端落后且可快进：%s" % "、".join(lagging))
        if not a.apply:
            print("  处置（未执行，默认只诊断）：`python tools/push_reconcile.py --apply`")
        else:
            for r in lagging:
                out2, err2, code = run(["git", *GIT_EXTRA, "push", r, "HEAD:main"], repo)
                ok = code == 0
                print("  %s 补推 → %s" % (r, "OK" if ok else "失败"))
                if not ok:
                    print("      stderr: %s" % (err2 or out2)[:300])
    print()
    # 复核
    for r in remotes:
        rh, _why = remote_head(repo, r)
        print("  复核 %-9s = %s  %s" % (r, (rh or "?")[:12], "一致" if rh == head else "仍不一致"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
