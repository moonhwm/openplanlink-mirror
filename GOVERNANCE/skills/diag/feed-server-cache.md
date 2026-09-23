---
name: feed-server-cache
type: diag
created: 2026-09-23
updated: 2026-09-23
version: 1.0.0
trigger: 端侧异动卡片停更或显示陈旧数据、怀疑 feed-server 缓存旧数据、需要判断重启是否有效
source_files: [feed-server/server.mjs, feed-server/audio-postprocess.mjs, feed-server/manage-feed-server.ps1]
---

# diag技能：feed-server缓存旧数据诊断——缓存机制识别、重启刷新策略、时效验证

## 概述

feed-server 是 harmony-app（铃语）的 X 服务器落地前的数据源服务：端侧 Index.ets 以 5 秒前台轮询（AlertPoller 兜底）拉 FEED_URL，feed-server 每 30 秒刷新一次缓存数据（内存 cachedAlerts + CloudBase alerts.json 上游 + 本地 tts-cache），契约即 AlertFeed。"数据是旧的"在这条链路上有多个可能的滞留点，本技能提供缓存机制识别、重启刷新策略与时效验证三段诊断法。

## 适用场景

- 端侧卡片长时间不更新，或 updatedAt 停留在过去时刻。
- 新出现的异动迟迟不上卡片，旧卡片反复出现。
- 判断"该不该重启 feed-server"、重启后仍旧数据的原因分析。
- 区分"缓存故障"与"非交易时段本来就没有新数据"的正常现象。

## 执行步骤

### 步骤一：缓存机制识别——数据在哪儿停留

以 feed-server/server.mjs 真实实现为准，链路上有四个滞留点，从上游到端侧：

1. 上游行情源：Tushare（token 失效 40101 时降级东财 API），行情本身不新鲜则全链路旧。
2. CloudBase 存储 `alerts/alerts.json`：refresh 时优先尝试 CloudBase 代理拉取 feed.items，直接采用存储里的现成数据。
3. feed-server 进程内存：`cachedAlerts` 与 `lastRefreshTs` 两个模块级变量缓存全量卡片，`REFRESH_INTERVAL = 30000`（30 秒）定时 refresh 刷新；refresh 失败时保留旧缓存继续服务（日志 `[feed-server] refresh failed:`）。
4. 端侧：5 秒轮询 AlertPoller 拿到数据后的去重与渲染（以 alertId 判重，属端侧逻辑，不在本技能展开）。

另有本地 TTS 缓存 `data/tts-cache/{alertId}.wav`：refresh 检测到新 alert 后按 alertId 查本地音频，存在则直接复用，不存在则合成并经 HRTF 后处理 renameSync 落盘。它缓存的是音频不是行情，但"旧音频配新卡片"的错配感也常被报成"缓存旧数据"。

识别口诀：**先问数据停在 1~4 哪一层，再动手刷新**。每层的判别手段见步骤三。

### 步骤二：重启刷新策略

重启的确切效果（依据 server.mjs 启动序列）：进程启动即 `await refresh()` 一次，随后 `setInterval(refresh, 30000)`。因此：

- 重启**必定**清掉第 3 层内存缓存（进程级变量随进程消失）并立即触发一次刷新——内存层的所有"旧"一次重启归零。
- 重启**不一定**带来新数据：refresh 优先走 CloudBase 代理取 alerts.json，若存储里的数据本身就旧（fetch-tushare-data 定时任务未跑、token 失效未降级成功），重启后拉回的还是旧数据。**重启治内存不治上游。**
- 正确的重启姿势（manage-feed-server.ps1 提供管理入口）：
  1. 先看 /health 确认 lastRefresh 与失败日志，判断旧数据在第 2 还是第 3 层。
  2. 第 3 层（内存）→ 重启即愈。
  3. 第 2 层（存储）→ 触发一次 fetch-tushare-data 云函数刷新上游，再重启/等待 feed-server 下个 30 秒周期。
  4. 第 1 层（行情源）→ 按 tushare-token-failure 技能修复源，再依次刷新第 2、3 层。
- 禁止用"循环重启"掩盖上游问题：每 30 秒本就有一次自然刷新，重启频率高于刷新间隔毫无增益。

### 步骤三：时效验证

三个口径由粗到细：

1. /health 口径（最快）：`GET <FEED_URL 根>/health`，返回 `alerts`（缓存条数）与 `lastRefresh`（ISO 时间）。判读：`now - lastRefresh ≤ 30s + 网络延迟` 为健康；超过 60 秒说明 refresh 连续失败（看 `refresh failed` 日志）；条数为 0 且端侧有卡片，说明端侧在吃演示卡 DEMO_ITEMS（服务未连通时的"永不空白"兜底），属链路断而非缓存旧。
2. updatedAt 口径（最准）：连续两次 `curl FEED_URL` 间隔 35 秒以上，比对返回 items 的 updatedAt/最新 alertId。有变化 → 链路活着；无变化 → 结合交易时段判断（见下）。
3. 端到端口径：制造一个已知新异动（或等真实异动），计时从发生到卡片出现的延迟，应 ≈ 上游检测周期 + 30 秒刷新 + 5 秒轮询。

**交易时段判别（防误诊的关键）**：异动数据源依赖行情更新，非交易时段（收盘后、周末、节假日）updatedAt 不前进、无新卡片是**正常现象**，不是缓存故障。验证前先确认当前处于交易时段；调试可选盘中或人为触发 fetch-tushare-data 造数。

时效验证还应包含音频一致性：新卡片 alertId 对应 `data/tts-cache/{alertId}.wav` 是否为新合成文件（核对文件 mtime），避免旧音频错配新文案。

### 步骤四：常见误诊清单

| 现象 | 直觉判断 | 实际原因 | 处置 |
| --- | --- | --- | --- |
| updatedAt 长期不动 | 缓存坏了 | 非交易时段 | 无需处置 |
| 卡片反复出现旧的几条 | 缓存没清 | 上游 alerts.json 未追加新数据，refresh 只能取到旧的 | 刷第 2 层 |
| 重启后仍旧 | 重启无效 | 旧数据在第 2/1 层 | 按步骤二分层刷 |
| 端侧完全无卡片 | 数据断供 | 服务未连通，端侧走演示卡 | 查 feed-server 存活与 FEED_URL |
| 播报声音内容旧 | 行情缓存旧 | tts-cache 按 alertId 命中旧音频或音频与文案错配 | 核对 alertId 与音频 mtime |

## 质量门槛

- [ ] 能说出四个滞留点及其判别手段
- [ ] 重启前已查 /health，明确旧数据在哪一层
- [ ] 时效验证至少跑通 updatedAt 口径（两次 curl 间隔 ≥35s）
- [ ] 已排除非交易时段误诊
- [ ] 音频 mtime 与新卡片 alertId 一致

## 经验记录

- 重启只清内存层；refresh 优先吃 CloudBase 现成数据，上游不新则重启白重启。
- /health 的 lastRefresh 是第一入口，30 秒阈值记牢。
- 非交易时段的"旧"是正常态，先看盘再看病。
- refresh 失败保留旧缓存是刻意的可用性取舍，别当 bug 修掉。
- tts-cache 按 alertId 键控，alertId 生成规则若含时间窗，音频错配要第一时间怀疑它。

## 关联文档

- GOVERNANCE/skills/diag/cloudbase-cache.md（alerts.json 存储层细节）
- GOVERNANCE/skills/diag/tushare-token-failure.md（第 1 层行情源故障）
- GOVERNANCE/skills/diag/tts-websocket.md（音频合成链路）

### 自我评估
- 正确性：5分 30 秒刷新、启动即 refresh、CloudBase 优先、refresh 失败保旧缓存、/health 字段均引自 feed-server/server.mjs 源码阅读（本次会话核对行 32/160/517-532/584-585/635/666-670）
- 完整性：5分 机制识别、重启策略、三口径时效验证、误诊清单齐备；端侧去重逻辑按约定未展开并已注明
- 可复用性：5分 "先分层再刷新"与三口径验证法可迁移到任何轮询型缓存服务
- 字数：约3000字
- 使用模型：GLM-5.3-Flash
