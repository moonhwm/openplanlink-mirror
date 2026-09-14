# CHANGELOG —— harmony-app 交接簿

> 规矩（见 AGENTS.md §三）：每个 AI 会话干完活在此**追加**条目，动手前先读最后一条。

## 2026-09-14 10:00 · 白秉烛（Kimi Work 桌面席）· 骨架首建

- 建 Stage 工程 23 文件：EntryAbility / Index 卡片流 / PushService 占位 / AlertPoller 轮询兜底 / AudioPlayer / AlertItem 契约 / 图标 / README / .gitignore。
- 基调：适老化大字卡、点卡即听、Push 未实装时首屏示例卡兜底。
- 遗留：FEED_URL 待 X 服务器；PushService 待 AGC；云构建走 CodeArts Build。

## 2026-09-14 10:55 · 白秉烛 · 共治契约建立

- 新增 AGENTS.md（分区主权/硬约束/串行纪律/架构基调）+ 本交接簿 + git 版本锁。
- 起因：码道 IDE 与 Kimi Code 同日开工，防多 AI 架构互踩。
- 遗留：quant-lab 侧服务端产出须对齐 AlertFeed 契约（已管道通告顾权席）。

## 2026-09-14 11:00 · 白秉烛 · 信号松绑（机主裁）

- AGENTS.md §二.2 修订：允许自家策略信号卡（kind="signal"），保留三禁（收益承诺/催促强指令/对外公开收费）。
- AlertItem 契约加可选字段 kind（缺省 fact，向后兼容）；Index.ets 实装「自家信号」金字角标。
- 已管道通报顾权席（契约变更）。
