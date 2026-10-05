#!/usr/bin/env bash
# commit_gate.sh — 共用仓提交级互斥（M1 单一写者令牌适用域扩充·实证件）
# 缘起：2026-10-06 本机多席共用 openplanlink-mirror 工作区，staged 内容与提交归属串扰实证
#       （顾权 v02 与 Cairn DF-ATTEST 被同一 commit 扫入；git commit 撞 cannot lock ref HEAD）。
# 机制：.git/opl-commit.lock 原子 mkdir 取锁；锁内写 owner+时间戳；>600s 判死收回；trap EXIT 释放。
# 用法: bash tools/commit_gate.sh <seat> <commit message> [-- <git add 路径...>]
#   不带路径=调用方已自行 git add；带路径=锁内 add 再 commit（add 与 commit 同锁原子）。
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "用法: bash tools/commit_gate.sh <seat> <message> [-- <paths...>]" >&2
  exit 2
fi
SEAT="$1"; MSG="$2"; shift 2
PATHS=()
if [ "${1:-}" = "--" ]; then shift; PATHS=("$@"); fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
LOCK="$REPO_ROOT/.git/opl-commit.lock"
STALE_SEC=600

acquire() {
  local i now ts
  for i in $(seq 1 60); do
    if mkdir "$LOCK" 2>/dev/null; then
      printf '%s\n%s\n' "$SEAT" "$(date +%s)" > "$LOCK/owner"
      return 0
    fi
    if [ -f "$LOCK/owner" ]; then
      ts=$(sed -n '2p' "$LOCK/owner" 2>/dev/null || echo 0)
      now=$(date +%s)
      if [ $((now - ts)) -gt "$STALE_SEC" ]; then
        echo "[commit_gate] 锁龄 $((now - ts))s 超 $STALE_SEC（owner=$(sed -n '1p' "$LOCK/owner")），判死收回" >&2
        rm -rf "$LOCK"
        continue
      fi
    fi
    sleep 5
  done
  echo "[commit_gate] 等锁 300s 超时，放弃（owner=$(sed -n '1p' "$LOCK/owner" 2>/dev/null || echo '?')）" >&2
  return 1
}

release() { rm -rf "$LOCK" 2>/dev/null || true; }
trap release EXIT

acquire
if [ "${#PATHS[@]}" -gt 0 ]; then
  git add -- "${PATHS[@]}"
fi
git -c "user.name=$SEAT" -c "user.email=$SEAT@opl-a2a.local" commit -m "$MSG"
echo "[commit_gate] 提交完成 owner=$SEAT"
