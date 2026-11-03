#!/usr/bin/env bash
# kdocs_bootstrap.sh — kdocs-cli 沙箱启动五连（幂等）
# 序：探活→装→PATH→exec位→认证恢复→状态断言。顺序即纪律，见 SKILL.md §1。
# 用法：bash kdocs_bootstrap.sh；全绿（auth:true）exit 0，否则 exit 1。
set -u
KD="$HOME/.kimi-work/bin/kdocs-cli"
SETUP="/app/.agents/plugins/kdocs/skills/kdocs/scripts/setup.sh"
AUTH_RESTORE="/app/.agents/plugins/kdocs/skills/kdocs/scripts/auth_restore.sh"

echo "== 1/5 探活 =="
if [ ! -x "$KD" ]; then
  echo "kdocs-cli 不在，跑 setup.sh …"
  bash "$SETUP" 2>&1 | tail -2
fi
ls -la "$KD" 2>/dev/null || { echo "FAIL: 安装后仍无 $KD"; exit 1; }

echo "== 2/5 PATH（先于一切调用，auth_restore 自身也依赖）=="
case ":$PATH:" in *":$HOME/.kimi-work/bin:"*) ;; *) export PATH="$HOME/.kimi-work/bin:$PATH";; esac
command -v kdocs-cli >/dev/null || { echo "FAIL: PATH 导出后仍找不到 kdocs-cli"; exit 1; }

echo "== 3/5 exec 位（upgrade 后会丢，幂等补）=="
[ -x "$KD" ] || chmod +x "$KD"
kdocs-cli version 2>&1 | head -1

echo "== 4/5 认证恢复（token.enc 加密件，全程无明文）=="
if kdocs-cli auth status 2>/dev/null | grep -q '"authenticated"[[:space:]]*:[[:space:]]*true'; then
  echo "已登录，无需恢复"
else
  bash "$AUTH_RESTORE" 2>&1 | tail -2
fi

echo "== 5/5 状态断言 =="
if kdocs-cli auth status 2>/dev/null | grep -q '"authenticated"[[:space:]]*:[[:space:]]*true'; then
  echo "BOOTSTRAP OK (auth:true)"
  exit 0
else
  echo "FAIL: authenticated=false —— 须用户扫码授权（人身动作，不代办）"
  exit 1
fi
