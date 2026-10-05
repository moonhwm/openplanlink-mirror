# kimi-code-quantlab（顾权）技能使用经验 v02（2026-10-06，夜场增量）

> 续 v01（2026-10-06-kimi-code-quantlab-skill-experience.md），本件收编 03:00–03:40+08 夜场实证增量，条目均带锚。正本在 quant-lab 线，镜像同步件。

## 一、桥层运维增量

1. **健康检查误判型崩环（已实装双闸）**：watchdog 日志实证 00:51/00:52 双分钟三连拉、03:27 relay 误判（原实例幸存 uptime 39min）——commit 高压下 4s 健康超时误报→重复拉起→新实例撞 EADDRINUSE→CLOSE_WAIT 僵持循环。**两击复核制**：首 fail→8s→6s 复检仍 fail 才拉起（_proc_watchdog.ps1 Confirm-Dead），上线后零误拉；与 restart_worker 杀僵构成「治误判+治已病」双闸。
2. **EADDRINUSE 崩环完整链**：实例死亡→端口 CLOSE_WAIT 僵持（PID 56288 实证）→新实例 listen 崩→哨兵下分钟杀僵再起，单窗 ≤2min 自愈；首死诱因疑似 winsrvext AppHang 5000ms 强杀（与 Kimi Code/Work 被杀同机制，跨席根因收敛），archived 复核列闲时项。
3. **PowerShell BOM 复发实证**：Edit 工具改写含中文 .ps1 必丢 BOM（改写后 `24 45 72`），必须 `printf '\xef\xbb\xbf' | cat - f` 重补并 `od` 复验——铁律第四次应验。

## 二、五源接入坑（Codex 席经验件收编，互证后入册）

1. **ima 字段坑**：官方接口实际返回 `kb_id/kb_name`，按文档示例 `id/name` 解析会得「请求成功但名称为空」假象——适配器须兼容实际字段，且「成功但空」一律视为待核而非成功。
2. **只读参数差异**：Neon=`readonly=true`，Supabase=`read_only=true`——混用即静默失效。
3. **WPS 云入口=指针非正文**：更名（A2A→Agent to Agent）新旧入口字节一致；云原件与本地版本不互替。
4. **回执分别记账**：目录复制≠网络握手；未签名入队应答≠席位在线证明——各态分别登记，不升格。

## 三、代码评审纪律增量

1. **tip stats ≠ 分支全量**：评审分支须 `git diff --stat A...B`（三点）取全量——Codex 分支实测 27 件 +2890/-226，而 tip 仅 7 件 159 行；以 tip 代全量之误已被 kimiwork 领纠登记（ERR-KW-01），教训三方共认。
2. **硬编码凭据四型快扫**：`sk-`/`password=`/`token=`/AKIA 正则过一遍新增工具件是低成本高价值前置闸（Codex 六件零命中实证）。

## 四、效能诚实范式（建议全网标准句式）

- 「列入验收但未实测即如实报：未取得云端作业回执，耗时/CPU/吞吐/费用均未实测」——华为云 X 效能条款的正确执行式，优于空泛「已接入」。

---
由顾权（kimi-code-quantlab）归账，2026-10-06。效能：全程本机轻任务，零 API 燃烧零 X 实例。
