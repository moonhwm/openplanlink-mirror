#!/usr/bin/env bash
# commit_gate.sh v1.1 — 共用仓提交级互斥（M1 单一写者令牌适用域扩充·实证件）
# 缘起：2026-10-06 本机多席共用 openplanlink-mirror 工作区，staged 内容与提交归属串扰实证
#       （顾权 v02 与 Cairn DF-ATTEST 被同一 commit 扫入；git commit 撞 cannot lock ref HEAD）。
# v1.1（圆桌 DS-V4-Flash 复审后修订，独立重算后采纳）：
#   ①获锁旗标制：仅真正持锁者才释放（修 acquire 超时退场误删他人锁——原 v1 最重洞）；
#   ②owner 原子写入（tmp+mv）+ 判死回退锁目录 mtime（修 mkdir/write 竞态窗永死锁）；
#   ③判死收回前先再读 owner 比对（修 TOCTOU 误删新持有者锁）；
#   ④commit 失败回滚本次 add 的路径（修残留串扰）；
#   ⑤EPOCHSECONDS 内置时间（去 date 叉）。
# 机制：.git/opl-commit.lock 原子 mkdir 取锁；>600s 判死收回；trap EXIT 释放。
# 用法: bash tools/commit_gate.sh <seat> <commit message> [-- <git add 路径...>]
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
ACQUIRED=0

lock_ts() {
  if [ -f "$LOCK/owner" ]; then sed -n '2p' "$LOCK/owner" 2>/dev/null || echo 0
  else stat -c %Y "$LOCK" 2>/dev/null || echo 0; fi
}

acquire() {
  local i now ts tmp owner_snapshot
  for i in $(seq 1 60); do
    if mkdir "$LOCK" 2>/dev/null; then
      tmp="$LOCK/owner.tmp.$$"
      printf '%s\n%s\n' "$SEAT" "$EPOCHSECONDS" > "$tmp"
      mv "$tmp" "$LOCK/owner"
      ACQUIRED=1
      return 0
    fi
    ts=$(lock_ts)
    now=$EPOCHSECONDS
    if [ $((now - ts)) -gt "$STALE_SEC" ]; then
      owner_snapshot=$(cat "$LOCK/owner" 2>/dev/null || echo "__noowner__")
      if [ "$owner_snapshot" = "$(cat "$LOCK/owner" 2>/dev/null || echo '__noowner__')" ]; then
        echo "[commit_gate] 锁龄 $((now - ts))s 超 $STALE_SEC（owner=$(sed -n '1p' "$LOCK/owner" 2>/dev/null || echo '?')），判死收回" >&2
        rm -rf "$LOCK"
        continue
      fi
    fi
    sleep 5
  done
  echo "[commit_gate] 等锁 300s 超时，放弃（owner=$(sed -n '1p' "$LOCK/owner" 2>/dev/null || echo '?')）" >&2
  return 1
}

release() {
  if [ "$ACQUIRED" = "1" ]; then rm -rf "$LOCK" 2>/dev/null || true; fi
}
trap release EXIT

if ! acquire; then
  exit 1
fi

if [ "${#PATHS[@]}" -gt 0 ]; then
  git add -- "${PATHS[@]}"
fi
if ! git -c "user.name=$SEAT" -c "user.email=$SEAT@opl-a2a.local" commit -m "$MSG"; then
  if [ "${#PATHS[@]}" -gt 0 ]; then
    git reset -q -- "${PATHS[@]}" || true
    echo "[commit_gate] commit 失败，已回滚本次 add 路径" >&2
  fi
  exit 1
fi
echo "[commit_gate] 提交完成 owner=$SEAT"
