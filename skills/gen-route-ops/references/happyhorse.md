# HappyHorse CLI 事实档（gen-route-ops 车道附件）

> 事实基础：2026-10-08 实装实测——安装 0.1.9（Linux-x86_64，官方 install.sh 经 SHA256SUMS 校验+版本自检+原子落盘 ~/.happyhorse/bin），`--version`/`--help`/`agent-guide --compact --json`/`whoami` 全部实跑。安装文档源：https://happyhorse.cn/install-cli.md（官方，OSS releases 桶分发）。

## 定位

AI **视频**生成 CLI（不是 3D 建模、不是生图）：text2video / image2video / reference2video（1–9 张参考图）/ video2video / refine（成功结果再加工）/ upload（图像或视频媒体注册）。cn/global 双区账户，分区登录。

## 标准五拍（agent-guide 推荐工作流，逐步照做）

1. `happyhorse whoami --json` — 登录态核查（可自动跑）。
2. `happyhorse <生成命令> <输入> --dry-run --json` — 本地校验（可自动跑，零扣费）。
3. `happyhorse <生成命令> <输入> --yes --json` — **付费提交；`--yes` 是逐次确认旗标，每次提交前必须取得用户批准**。
4. `happyhorse task <taskId> --wait --json` — 等待/恢复；断线用 `happyhorse task-recent --json`（本地回执上限 20 条）找回，**超时任务服务端继续跑，凭 taskId 续查，绝不重复提交**（重复提交=重复扣费）。
5. `happyhorse download <taskId> --if-exists skip --json` — 落盘；`--url-only` 可取链。

## 安全契约（不可裁剪）

- 付费命令五件：text2video / image2video / reference2video / video2video / refine —— 全部 `requiresUserConfirmation`。
- `SUBMIT_OUTCOME_UNKNOWN`：服务可能已受理但无幂等重试键——**禁止自动重试**；保留 traceId，查网页任务中心。
- 永不索取/打印/落盘用户账户凭据与令牌（`neverRequestAccountCredentials`）；登录一律 `happyhorse login --region cn|global` 走浏览器授权页（`--no-browser` 变体输出 URL 供已登录 Profile 手开）。
- 输出契约：`--json` 单对象上 stdout，stderr 为 JSON-lines 指示；任务 id 为十进制字符串。
- 安装/更新：官方原生二进制默认静默跟随 stable 自动更新（`update --disable-auto` 可关）；Windows 含非 ASCII 用户目录自动落 `%ProgramData%\HappyHorse\users\<hash>`，勿手工移回。
- 会员闸：响应含 `paywall/paywallUrl/paywalls` 字段（MEMBERSHIP_AUTHORITY）——遇到即如实呈用户，不绕行。

## 当前状态（2026-10-08 快照）

已装 0.1.9；whoami 双区未登录——**生成类命令须先由主权人完成 `happyhorse login`（浏览器）**。
