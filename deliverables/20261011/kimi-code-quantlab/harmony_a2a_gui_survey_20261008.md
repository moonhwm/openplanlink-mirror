# HarmonyOS × A2A 内部 IM 网络 —— GUI 面参考侦察（设计输入件）

- 件别：顾权席侦察子代理参考面产出（非项目代码，仅设计输入）
- 日期：2026-10-08
- 铁律执行：每条断言附来源 URL；检不到的标「未检得」；未读凭据；未改 quant-lab 其他文件
- 本机实测环境约束（2026-10-08 实测）：RAM 16,076 MB / 已用 92.3%（free 1,241 MB），分页文件已分配 48,915 MB、当前用 10,162 MB —— 与「内存 commit 90%+」约束一致，重活（DevEco 模拟器、Docker、本地向量库）均在此约束下评级

---

## 1. HarmonyOS 7 真实性核实（S 级源结论）

**结论：HarmonyOS 7 真实存在，但截至 2026-10-08 处于「开发者 Beta」阶段，非正式商用版。**

- 2026-06-12，华为在 HDC 2026 上宣布 HarmonyOS 7 开发者 Beta 正式启动（华为官网新闻稿，S 级源）：https://www.huawei.com/cn/news/2026/6/harmonyos7-hdc
- 开发者官网已上线「HarmonyOS 7 (API 26) 新能力一览」页（S 级源，本件已抓取正文）：https://developer.huawei.com/consumer/cn/features/
- 第三方佐证：科技日报（2026-06-12，https://www.stdaily.com/web/gdxw/2026-06/12/content_531514.html ）、IT之家（2026-06-15 开发者 Beta 推送，系统包约 20GB，https://www.ithome.com/0/964/605.htm ）

**与本件直接相关的新能力面（来源：上述华为官方新闻稿 + 开发者 features 页）：**

1. **鸿蒙智能体框架升级至 2.0**：官方表述「践行"意图即服务"理念，将复杂任务成功率提升至 90% 以上……开放了超 20 项系统级 AI 能力，首次向开发者开放 GUI 操控能力」。——对本网的含义：HarmonyOS 7 原生支持 Agent 编排与 GUI 操控，ArkUI 应用可被系统级 Agent 能力调用/操控，这与「A2A 网络 + GUI 交互界面」的叙事同向。
2. **Agent 亲和系统架构**：「深度融合端云大模型，驱动应用向智能化、Agent化、Skill化演进」；features 页列出 Skill、Vibe Coding、卡片链接等入口。
3. **生态数据**（官方新闻稿）：HarmonyOS 6 终端 6,600 万台、注册开发者 1,100 万+、应用/服务 40 万+。
4. 官方新闻稿未明示 HarmonyOS 7 正式商用版的确切推送日期（有媒体转述何刚宣布正式版将面向消费者开放，具体日期未检得官方页确认——标「未检得」）。

**不得凭宣传话术写作的如实判定**：HarmonyOS 7 的 GUI 操控、Agent 框架 2.0 等能力为开发者 Beta 期能力，面向本网落地时 API 稳定性、上架审核口径、真机持有率均有不确定性；本网不应把「HarmonyOS 7 原生能力」当作已稳定可用的前提，只能作为二期增强面。

---

## 2. GitHub 开源面（全部经 GitHub API 2026-10-08 核实）

### 2.1 HarmonyOS / ArkTS / ArkUI 的 IM / 聊天 GUI 参考项目

| # | 项目 | ★ | 许可 | 最近 push | 可借鉴点 |
|---|------|---|------|-----------|----------|
| 1 | [JackJiang2011/MobileIMSDK](https://github.com/JackJiang2011/MobileIMSDK) | 6,084 | Apache-2.0 | 2026-09-28 | 全平台 IM 通信层框架，鸿蒙 NEXT 客户端为纯 ArkTS、基于 WebSocket；轻量（lib 包 50KB 级）；消息与 UI 解耦范式 |
| 2 | [JackJiang2011/harmonychat](https://github.com/JackJiang2011/harmonychat) | 43 | Apache-2.0 | 2025-08-19 | 鸿蒙 NEXT WebSocket 聊天客户端 Demo：LazyForEach 长列表性能、全局消息缓存 + DataSource 解耦、消息类型组件式扩展、人性化时间显示 |
| 3 | [TencentCloud/TIMSDK](https://github.com/TencentCloud/TIMSDK) | 2,748 | 仓库级 license 未标（部分文件自有声明） | 2026-09-21 | 商业 SDK；其 **TUIKit ArkUI 组件库**提供聊天/会话列表/联系人管理完整方案（官方文档：https://cloud.tencent.com/document/product/269/125128 ） |
| 4 | [wildfirechat/flutter-chat](https://github.com/wildfirechat/flutter-chat) | 53 | NOASSERTION | 2026-10-04 | 野火 IM Flutter 客户端，声明支持 HarmonyOS 等多端；适合评估「Flutter 跨端 → 鸿蒙」路线 |
| 5 | [wangxulove-jpg/ArkTavernSolo](https://github.com/wangxulove-jpg/ArkTavernSolo) | 3 | MIT | 2026-10-07 | 原生 ArkTS/ArkUI 的 **AI 角色聊天客户端（类 SillyTavern）**，活跃维护；可借鉴流式对话 UI、会话管理、人设卡数据模型 |
| 6 | [easemob/im_flutter_sdk_oh](https://github.com/easemob/im_flutter_sdk_oh) | 2 | MIT | 2026-08-24 | 环信 IM Flutter SDK OpenHarmony 版（SDK 厂商面，参考集成方式） |
| 7 | [juggleim/imsdk-harmony](https://github.com/juggleim/imsdk-harmony) | 2 | Apache-2.0 | 2026-06-11 | JuggleIM 鸿蒙 SDK（私聊/群聊/聊天室/富媒体，参考其 API 面设计） |

另：ChatUI（`@changwei/chatui`，ArkTS 原生聊天 UI 库，`ohpm install @changwei/chatui`）仅在 Gitee 核实（https://gitee.com/depth0/ChatUI ），其 GitHub 镜像与许可「未检得」，列为备选待复核。

OpenIM 鸿蒙 SDK（openimsdk/openim-harmonyos-sdk）：GitHub API 返回 Not Found——「未检得」，不列入。

**开源面整体判断**：鸿蒙原生 IM 开源面「通信层成熟（MobileIMSDK 10 年项目、持续活跃）、UI 层单薄（星数低、多为教学/演示级）」；本网 GUI 若走原生 ArkUI，UI 骨架大概率需自研，可组合 MobileIMSDK 范式 + ArkTavernSolo 的流式 AI 对话 UI 模式。

### 2.2 Agent 行为轨迹审计 / LLM observability 开源面（「可核验信任闭环」参照系）

全部经 GitHub API 2026-10-08 核实：

| 项目 | ★ | 许可（API 返回） | 定位 / 借鉴点 |
|------|---|------------------|----------------|
| [langfuse/langfuse](https://github.com/langfuse/langfuse) | 35,498 | NOASSERTION（含 EE 部分；核心自托管可用） | 开源 agent evals + observability；OTel 原生；轨迹(trace)+评估+用户反馈闭环；2026-01 被 ClickHouse 收购后仍开源（佐证：https://www.morphllm.com/ai-agent-observability-tools ） |
| [comet-ml/opik](https://github.com/comet-ml/opik) | 22,440 | Apache-2.0 | Debug/评估/监控 LLM 与 agentic workflow；自托管轻 |
| [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) | 11,744 | NOASSERTION（ELv2 系） | OTel 原生（OpenInference）；span 级轨迹回放 |
| [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) | 25,796 | MIT | 红队/断言测试，适合「决策依据可重放」的判分面 |
| [AgentOps-AI/agentops](https://github.com/AgentOps-AI/agentops) | 5,887 | MIT | 会话回放（session replay）——与本网「决策依据回放」诉求最直接对应 |
| [traceloop/openllmetry](https://github.com/traceloop/openllmetry) | 7,475 | Apache-2.0 | 基于 OpenTelemetry 的 GenAI 观测规范实现 |

**参照系结论**：本网「可核验信任闭环」无需自建审计内核——以 **OpenTelemetry GenAI 语义** 为轨迹 schema，自托管 Langfuse（或 Opik）做轨迹存储/回放/评估 GUI；本网自研部分仅为「轨迹 → 证据卡 → 哈希链登记」的薄映射层。对照表佐证 OTel 为 2026 年该面共识：https://www.morphllm.com/ai-agent-observability-tools

---

## 3. A2A 协议面现状（一手源核实）

- 官方站（本件已抓取）：https://a2a-protocol.org/ ——「Originally developed by Google and now donated to the Linux Foundation」。官方 SDK 列表：Python / JavaScript / **Java / C#/.NET / Golang**；**无 ArkTS/鸿蒙官方 SDK（未检得）**。
- 主仓 [a2aproject/A2A](https://github.com/a2aproject/A2A)：26,051★，Apache-2.0，2026-10-07 活跃。
- 官方 SDK/样例：[a2a-python](https://github.com/a2aproject/a2a-python)（2,185★）、[a2a-js](https://github.com/a2aproject/a2a-js)（635★）、[a2a-samples](https://github.com/a2aproject/a2a-samples)（1,792★），均 Apache-2.0 且 2026-09-30 后仍活跃。
- 版本与生态时间线（多源一致）：Google 2025-04-09 发布；2025-06-23 进入 Linux Foundation；**v1.0 于 2026-03-12 发布（新增签名 Agent Card、多租户）**，v1.1 随后；2026-04-09 超 150 家组织；2026-08-17 A2A 转入 Linux Foundation 下的 Agentic AI Foundation（AAIF）（佐证：https://www.sentra.app/articles/mcp-vs-a2a 、https://rpabotsworld.com/a2a-joins-mcp-aaif-agentic-ai-architects-guide/ 、https://aaif.io/blog/a2a-joins-aaif ）。注：以上 5 条时间线均为二手多源一致，未逐条抓取一手公告，采用时建议终审复核。
- Agent 框架适配面：LangGraph 平台自带 A2A 端点（https://7x.mintlify.app/langsmith/server-a2a ，非官方镜像，一手文档未检得）；社区有 `langgraph-a2a-server`（https://libraries.io/pypi/langgraph-a2a-server ）与 `a2a-langgraph`（https://libraries.io/pypi/a2a-langgraph ）等适配器；langchain 官方 issue 跟踪自托管 A2A 适配需求（https://github.com/langchain-ai/langchain/issues/35724 ）。
- A2A 与 MCP 关系（官方站一手）：互补标准——MCP=agent→工具，A2A=agent→agent；IBM ACP 已并入 A2A。

---

## 4. 设计输入汇总（三层栈 + 三条落地路径 + 本机约束分级）

### 4.1 三层候选技术栈

**GUI 层（ArkUI）**
- 首选：ArkTS + ArkUI 声明式 UI（官方文档入口 https://developer.huawei.com/consumer/cn/doc/ ），聊天骨架自研，参考 harmonychat / ArkTavernSolo 模式。
- 消息流组件：LazyForEach + 全局消息缓存（harmonychat 范式）。
- 二期增强：HarmonyOS 7 Agent 框架 2.0 的系统级 Skill 入口（features 页）。

**审计层（轨迹留痕 + 决策依据回放）**
- 轨迹 schema：OpenTelemetry GenAI 语义（openllmetry 实现）。
- 存储/回放 GUI：自托管 Langfuse 或 Opik（二选一，Langfuse 生态最大但部署偏重；Opik 更轻）。
- 本网特有薄层：轨迹摘要 → 证据卡（sha256）→ 登记台账；决策依据回放 = trace 级时间线 + 消息体原文锚点。

**桥接层（对接本网 Supabase 总线）**
- Supabase 侧：复用现有 cross_mode_channel 表结构（register/broadcast/read/cursor 语义，由本网总控件定义，本件不复述）。
- A2A 适配：Python 侧用官方 a2a-python SDK 包一层 A2A gateway，把本网 agent 暴露为 A2A 服务端点（Agent Card + JSON-RPC message/stream）；鸿蒙端暂无官方 SDK，用 ArkTS HTTP/WebSocket 客户端直读 Supabase 总线即可，**不必为鸿蒙端硬套 A2A SDK**。

### 4.2 三条候选落地路径（可行性分级，本机约束下）

| 路径 | 形态 | 可行性 | 理由 |
|------|------|--------|------|
| P0 仅 Web 面板 | 浏览器 GUI + Supabase 直连 + Server酱推送兜底 | **A（首选）** | 零新工具链、零重活；Windows 本机立即可做；审计 GUI 可直接用 Langfuse/Opik 自托管（Opik 更省内存）或先借 Langfuse Cloud 免费层 |
| P1 元服务（Atomic Service） | 免安装、≤2MB 轻形态（官方介绍：https://developer.huawei.com/consumer/cn/harmonyos/fa ） | **B（二期）** | 需华为开发者账号 + 审核口径；Beta 期 API 稳定性风险；但契合「IM 轻入口」叙事，开发量小 |
| P2 原生 App | DevEco Studio + ArkUI 全功能客户端 | **C（三期/谨慎）** | DevEco Studio + 鸿蒙模拟器在 16GB RAM 92% 占用机上不可行（模拟器属 5GB+ 重活禁）；需真机或外接编译机；HarmonyOS 7 Beta 真机门槛未检得公开招募口径 |
| 旁路：Flutter | flutter-chat（野火）路线 | **D（不推荐）** | 引入第二工具链；对本网「ArkUI 原生 + Agent 框架 2.0」二期目标无增益 |

### 4.3 本机硬约束（实测）

- RAM 16 GB，已用 92.3%（2026-10-08 实测）；任何 5GB+ 占用的活（DevEco 模拟器、Docker 桌面、本地大模型）禁。
- Windows 开发机：Python/Node 工具链可用；Docker 路线仅在内存富余的会话窗口审慎评估。

---

## 5. Server酱 → A2A 事件总线 接线设计要点（不复测）

前提：2026-10-08 顾权席首测 SUCCESS 已记录；Server酱官方文档面已核实（Turbo: https://sct.ftqq.com/ ；SendKey 获取/验证: https://sct.ftqq.com/docs/getting-started/sendkey/ ；FAQ/额度频率: https://sct.ftqq.com/docs/getting-started/faq/ ）。

接线要点：
1. **单向扇出，不做回环**：Server酱只做「总线事件 → 微信」的只读扇出通道；微信侧不承载控制指令回流（本网控制面只走 Supabase 总线），避免把 IM 推送通道变成未审计的控制面。
2. **事件筛选在桥接层做**：订阅 Supabase `broadcast` 的高优先级事件类（裁决/交割/告警），按 tag 路由到 SendKey；低优先级心跳不进微信，防额度/频率触顶（FAQ 页有额度与频率限制说明）。
3. **消息体即审计证据**：推送正文 = 事件哈希 + 一句话裁决 + 台账锚链；与审计层证据卡共用 sha256，使「微信里看到的话」与「台账里登记的话」同一指纹——这是「可核验」在微信侧的最小闭环。
4. **失败降级**：SendKey 失效/额度耗尽时桥接层记台账告警，不静默（首测 SUCCESS 不代表长期可用，FAQ 明示两个产品 Turbo/SC3 的额度独立）。
5. **密钥纪律**：SendKey 仅存环境变量/凭据库，任何侦察件、报告、日志不落 key 明文。

---

## 6. 最大风险 / 不确定项（如实清单）

1. **HarmonyOS 7 仍处开发者 Beta**：正式商用版时间未检得官方确认；Agent 框架 2.0 / GUI 操控的 API 在 Beta 期内可变——P1/P2 路径的时间表不可承诺。
2. **鸿蒙原生 A2A SDK 不存在**：官方 SDK 无 ArkTS；鸿蒙端只能「Supabase 总线直连 + 服务端 A2A gateway」的混合形态，本网对外宣称「A2A 网络」时，鸿蒙端实为客户端而非协议端点。
3. **审计层自托管的内存账未算清**：Langfuse v3 自托管（Postgres+ClickHouse 系）在本机 92% 内存占用下大概率不可行；Opik 轻量但成熟度次之——落地前必须先做内存实测，或先用 Langfuse Cloud 免费层过渡（数据出境合规口径本网自定）。
4. **A2A 时间线均为二手多源一致**：v1.0 日期、150+ 组织、AAIF 转入等未逐条抓取一手公告，终审前建议复核 aaif.io / linuxfoundation.org 原页。
5. **开源项目可持续性**：harmonychat（43★，最近 push 2025-08）、ArkTavernSolo（3★）均存在停更或转向风险，借鉴模式而非依赖代码。
6. **Server酱通道不可作为信任闭环的唯一承载**：推送内容经第三方（方糖服务号/SC3 App），正文指纹只能做到「台账↔微信展示一致」，做不到「微信侧可独立验证」，可核验的锚必须在台账与审计层。

（完）
