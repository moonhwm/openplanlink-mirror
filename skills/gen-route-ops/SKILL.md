---
name: gen-route-ops
description: "生成智路由署——3D 建模/AI 生图/AI 视频/DCC 场景/算力全车道统一入口与决策大模型智慧路由：车道注册表（Tripo 系、302 系、V2Fun、Rodin、image/video_generation 插件、HappyHorse、Remotion、MiniMax H3、CompShare、Maya DCC、CAD 预留位等 17 条）+ 确定性探针 + 决策大模型（百炼/DeepSeek/火山方舟/OpenRouter 自动链）选车道出带 sha256 的决策卡。内置反抽卡教义：gacha_risk 三级（low 机器直办/medium 锚定制导/high 纯 prompt 抽卡），身份一致性/精度敏感/批量一致任务禁 high 裸跑，走 anchor-first 剧本（references/control-doctrine.md）。触发（满足任一）：①用户要给图片/文字做 3D 建模、生图、生成视频且未指名车道，或问「用哪个平台/模型生成」「哪条车道便宜/快/好」；②多车道可用需选型比价时；③提到 HappyHorse、v2fun、Rodin、Tripo、302、Remotion、MiniMax H3、CompShare、Maya 等车道名需调度时；④车道状态/余额/可用性盘点时；⑤人像写真重构、身份一致性生成等反抽卡场景路由时。不覆盖：各车道具体生成执行（路由后交车道本体技能——tripo-3d 插件、v2fun-ops、hyper3d-rodin-mcp、dcc-mcp-umbrella、remotion-video-forge、compshare-cli、image_generation、video_generation 或 references/happyhorse.md 五拍）；GLB 观展页注造（归 glb-observatory-ops）。中文名：生成智路由署。English triggers: generation lane router, anti-gacha anchor-first routing."
metadata:
  version: "1.1.2"
---

# 生成智路由署（gen-route-ops）

> 立法锚：**「选车道交给注册表+探针+决策大模型；执行归车道本体；费用逐次批准、笔笔回填。」**
> 立法锚二（v1.1.0，主权人 2026-10-10）：**「编译后干预，拒绝抽卡——能机器直办不裸摇，要生成先锚定。」**
> 溯源：2026-10-08 主权人令「整合当前所有 3D 建模、生图模型等，用决策大模型决定智慧路由，整合安装 HappyHorse CLI」锻造 v1.0.0；2026-10-10 主权人令「再次智能路由构建整合并锻造」+ MyTan 2024 反抽卡考量升 v1.1.0。周嘤鸣（字乔木）｜k3-govdoc-seat 谨制。
> v1.1.0 增量：车道 12→17（+remotion/minimax_h3/compshare_gpu/maya_dcc/cad_engineering）；全车道 gacha_risk 三级标注；决策卡增 control_surface/intervention_points；反抽卡教义入决策 prompt；kind 增 dcc/compute；smoke 8→13 断言。
> v1.1.1（2026-10-10，注册表 1.1.1）：主权人口径「Tripo 走的也是 Studio」落册——当时误记为「同账户同钱包」，经主权人当轮纠正（v1.1.2 勘正）。
> v1.1.2（2026-10-10，注册表 1.1.2）：**勘正**——Tripo 官方与 Tripo Studio 同账户、**不同钱包**（API 钱包与 Studio 钱包分立），Studio 端有折扣，钱包可否划转未证 ⚠️；tripo302/tripo_mcp/tripo_env 增 quality_note「主权人观感：目前 Tripo 效果一般」，决策简报与决策卡同步呈报该口径。

## 定位与边界

本件是**路由层**：探可用性 → 决策大模型选车道 → 出决策卡 → 交车道本体执行。不替代任何车道本体技能，不亲手生成内容。

- 3D 执行：tripo-3d 插件技能（MCP 车道）、v2fun-ops、hyper3d-rodin-mcp、302.AI 契约（lanes.json `executor` 字段）
- 生图执行：image_generation / video_generation 插件技能、302.AI 目录
- 视频执行：references/happyhorse.md 五拍、video_generation 插件、**remotion-video-forge（代码直办，零抽卡首选）**
- DCC 执行：dcc-mcp-umbrella（Maya 等场景操作；工程域预留位不拿网格域冒充）
- 算力执行：compshare-cli（GPU 实例+MiniMax H3；dry-run→批准→--yes）
- GLB 观展页：归 glb-observatory-ops

## 反抽卡教义（速览；全文 references/control-doctrine.md）

| 级 | 定义 | 姿态 |
|---|---|---|
| low | 机器直办：代码/参数/直接操纵，可复现 | 首选——能工程化就落 low |
| medium | 锚定制导：参考图/首尾帧/多视图/幂等键 | 生成类标准姿态，锚件先行人工闸 |
| high | 纯 prompt 抽卡 | 仅创意探索；身份/精度/批量一致任务禁用 |

**立法案例（MyTan 2024，主权人亲历口径）**：500 元 / 约 500w token / 单张约 1w，
ChatGPT-image（或未到 2.5）裸 prompt 重构人像西服写真未竟——**纯抽卡对身份锁定任务无效**。
正解=anchor-first 剧本 A（参考锚→人工闸→锚定生成，教义全文 §三）。

## 五条铁律

1. **凭据零落盘零回显**：一律环境变量（AI302_API_KEY/TRIPO_API_KEY/V2FUN_API_KEY/BAILIAN_API_KEY/DEEPSEEK_API_KEY/ARK_API_KEY/OPENROUTER_API_KEY/AIMLAPI_KEY/MODELSCOPE_TOKEN/COMPSHARE_PUBLIC_KEY/COMPSHARE_PRIVATE_KEY/COMPSHARE_MINIMAX_API_KEY）；probe 只报 present/absent；Rodin/HappyHorse 登录永不索取凭据、全程浏览器。
2. **付费逐次批准**：决策卡 `needs_user_confirmation` 恒真；烧前查钱包/登录态，烧绑 artifact，烧后费用回填留痕。
3. **决策留痕**：每次 decide 出决策卡（含 card_sha256、control_surface、intervention_points），append 入台账；`degraded=true`（规则降级）必须如实标注，禁冒充 LLM 决策。
4. **不重复提交**：任何车道 SUBMIT_OUTCOME_UNKNOWN/超时——凭 taskId/uuid 续查（HappyHorse `task-recent`、V2Fun `--task-uuid`、302 `task/{id}`、compshare 幂等键），重复提交=重复扣费。
5. **诚实状态**：车道状态以 probe 实测为准；注册表快照含 unverified/unknown/pending 者调用前复测；⚠️ 标注不得抹掉。

## 工作流（四拍）

1. **探**：`python3 scripts/route_decide.py probe`（零网络零燃烧）——env 凭据、CLI 在轨一目了然；MCP/插件车道标 `agent_confirm`，由你从当前工具表确认。
2. **决**：`python3 scripts/route_decide.py decide "<用户需求原文>" [--kind image|model_3d|video|dcc|compute] [--json]`——决策大模型出决策卡（chosen_lane 过注册表校验防幻觉；全灭自动规则降级并标注；decide 前须 `set -a; . /mnt/agents/upload/credentials.env`）。首选决策位可用环境变量 `GEN_ROUTE_DECIDER` 指定；琐事且需求明确时可直接引用规则降级路径省决策额度。
3. **批**：决策卡呈用户——车道、控制面等级、人工闸点、费用口径、前置条件（充值/登录/key）明示；获批再执行。
4. **行**：交车道本体（executor 指向的技能/契约）；产物落盘、费用回填台账、决策卡 sha 引用入录。

## 车道速查（2026-10-10 快照；全量见 `python3 scripts/route_decide.py lanes`）

| 类目 | 立即可用 | 候条件 |
|---|---|---|
| 3D 建模 | tripo302（30 credits/图生实测，risk=medium 可 multiview 锚） | tripo_mcp（充值；与 Studio 同账户不同钱包，Studio 端有折扣）、tripo_env（验余额，API 钱包独立）、v2fun（注 key）、rodin（OAuth，401 漂移在案）；⚠️ 主权人观感：Tripo 效果目前一般，质量敏感任务呈报替代项 |
| 生图 | image_generation 插件（high，锚定制导降级用法见教义） | ai302_image、modelscope/aimlapi/openrouter（验余额） |
| 视频 | remotion（low 代码直办）、video_generation 插件 | happyhorse（已装 0.1.9，候 login）、minimax_h3（候 COMPSHARE 三 key） |
| DCC 场景 | —（maya_dcc 断连在案） | maya_dcc（MCP 修复）、cad_engineering（预留位未接入） |
| 算力 | — | compshare_gpu（cli 0.5.3 已装，候公私钥） |

## 失败模式（if-then）

| 触发 | 处置 |
|---|---|
| decide 报 NO_KEY 链全灭 | 自动规则降级出卡（degraded=true）+ 如实报告；候凭据注入 |
| LLM 返回注册表外车道 | 该车次记 HALLUCINATED_LANE 并自动换下一家决策模型；禁采用幻觉车道 |
| 车道 probe 全 pending | 如实呈「无立即可用车道」+ 各前置条件清单，不伪造可用 |
| HappyHorse 未登录 | 呈 `happyhorse login --region cn` 指引；浏览器授权后 whoami 复核再烧 |
| 提交后断线/超时 | 铁律 4：续查不重复提交 |
| 身份一致性任务被路由到 high 裸车道 | 违反教义——重路由：medium 锚定车道+intervention_points，或明确向用户告示方差风险并获批 |
| Maya/DCC MCP 断连 | 如实报修复路径（dcc-mcp-umbrella 排错），不拿生成线冒充场景操作 |
| 工程域任务（尺寸/公差/装配） | cad_engineering 预留位 not_integrated——如实声明，不拿网格域凑合（B-rep≠三角网格） |

## 资源

- `scripts/lanes.json` — 车道注册表单一真源（端点/凭据变量/费用口径/gacha_risk/状态/证据/executor；状态变更先改此表并升 registry_version）
- `scripts/route_decide.py` — probe/decide/lanes/smoke 四命令；stdlib 零依赖；`smoke` 离线自检 13 断言
- `references/control-doctrine.md` — 反抽卡/编译后干预教义全文：MyTan 案例、控制面三级、anchor-first 剧本三件
- `references/happyhorse.md` — HappyHorse CLI 五拍与安全契约全文（走该车道前必读）

## 诚实边界

- 决策卡是「当前注册表+当前探针」的相对结论；车道状态漂移后须重新 probe。
- 决策大模型只选型、不担保质量；模型质量归生成侧，验收归用户。
- 教义管路由姿态不管产物达标——锚定≠必成，产物验收归各车道本体质量闸。
- 本件 v1.1.0 快照日 2026-10-10；注册表内 ⚠️ 项均为未独立核实口径，引用必带标。
