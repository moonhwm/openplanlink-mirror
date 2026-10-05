# 五通道依次接入计划 v0.1（草案，待各席/主权人定序）
author: a2a-node-local
date: 2026-10-06 (轮267)

## 目标
目标新增：依次接入 ima、Supabase、Neno、WPS、百度云盘。

## 现状（实测，逐条可复现）
1. Supabase —— 已接：spinal_probe.py 只读 cross_mode_channel 表正常（publishable key 在册）。
2. WPS 云盘 —— 已在用：本席全部文档在 WPSDrive/29969771 下（读写正常）。
3. ima —— 未启动：A:\ima.copilot\ima.copilot.exe 存在、进程未跑；无 API/凭据侧接入。
4. Neno —— 未识别：本席无该服务凭据与端点信息，待主权人说明所指（服务形态/账号）。
5. 百度云盘 —— 未接入：无 API 凭据（需主权人给 key，仅存本地 .env）。

## 建议顺序（提案，待拍板）
Supabase(已通) → WPS(已通) → ima(本地启动+再议API) → Neno(待认领) → 百度云盘(待凭证)。

## 阻塞
- ima/Neno/百度云盘均缺凭据或定义；未获授权前本席不做任何注册/付费动作。
