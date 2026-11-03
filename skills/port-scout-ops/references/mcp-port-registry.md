# 端口底账：MCP 服务与 agent harness（v2，2026-10-02 实证登记）

命中「MCP 服务 / agent harness / 代码托管 AI 集成 / 集群编排 / 开源模型」类需求时直接复用本表，只补增量。

## 登记表

| # | 项目 | 类型 | 获取方式 | 关键事实（一手来源） | 合规层 | verified |
|---|---|---|---|---|---|---|
| 1 | gitcode-org-com/gitcode-mcp | MCP server（Go） | `go install github.com/gitcode-org-com/gitcode-mcp@latest` 或克隆仓库跑 install.sh | GitCode 官方 MCP；mark3labs/mcp-go SDK；STDIO+SSE 双传输；16 件工具（仓库/分支/Issue/PR/搜索）；需 `GITCODE_TOKEN`；MIT 许可 | 合法 | true |
| 2 | supabase-community/supabase-mcp（ModelScope 托管） | MCP server（Hosted） | ModelScope MCP 市场一键部署，或 npm `@supabase/mcp-server-supabase` | 连接 Supabase 项目到 Cursor/Claude/Windsurf；ModelScope Hosted 可部署；Apache-2.0；supabase-community 官方 | 合法 | true |
| 3 | zai-org/ZCode | agent harness（开源） | 克隆 `github.com/zai-org/ZCode`，`pnpm bootstrap` | Z.ai 编程 agent；桌面（Electron）+Web+CLI 三形态；Agent 运行时 `apps/zcode-cli/`；v3.14.3（2026-09-23）；MIT 系许可（NOTICE.md）。**前科**：2026-09-18 曾静默上传用户整个仓库（含 .git）至阿里云 OSS，官方当日致歉并开源 | 合法（信任降档） | true |
| 4 | Anthropic Claude Code Dynamic Workflows | agent 编排机制（研究预览） | Claude Code CLI v2.1.154+，`ultracode` 触发 | 2026-05-28 随 Opus 4.8 发布；Workflow 工具执行 JS 编排脚本，六原语 `agent/parallel/pipeline/workflow/phase/log`；上限 16 并发/1000 总 agent。**注意**：`CreateWorkflow` 工具名与「先定子代理拓扑」句式出自此处，**非 ZCode 原生能力** | 合法（文档） | true |
| 5 | greasyfork.org | 用户脚本托管站 | 网页浏览/安装脚本 | 油猴脚本主库；2024 年后加强审核。**风险提示**：用户脚本权限面大，安装前必读源码 | 合法（内容混杂） | false |
| 6 | modelscope.cn（魔搭社区） | 模型/数据集/MCP 托管平台 | 网页 + Python SDK + API | 阿里系模型 hub；含 MCP 市场（见 #2）；数据集与模型下载需实名；免费额度分级 | 合法 | true |
| 7 | AWS Prescriptive Guidance 云设计模式库 | 架构模式文档 | 网页公开 | 事务性发件箱/收件箱、Saga、CQRS、事件源等模式官方定义+AWS 实现示例；本生态恰好一次游标纪律的架构背书 | 合法 | true |
| 8 | **deepseek-ai/deepseek-harness（DSH）** | agent harness（开源） | `npx @deepseek-ai/dsh web`（需 Node.js）；或克隆 `github.com/deepseek-ai/deepseek-harness`，pnpm 构建 | DeepSeek 首款 Agent 运行框架，2026-08-13 发 v0.1 开发者预览，**MIT 全开源**；公式「Model+Harness=Agent」；底层 Cordis 插件元框架（时空可组合性，DeepSeek×北大联合研究），九大组件（模型/工具/技能/会话/沙箱/存储/循环/调度/UI）全插件化热插拔；append-only 会话日志+Trajectory 轨迹视图（恢复/分叉/检索/回放）；兼容数十家模型不绑自家 | 合法 | true |
| 9 | **EvoMap/evolver（GEP 自进化引擎）** | agent 自进化引擎（开源） | `npm install -g @evomap/evolver`，git 仓库内跑 `evolver`；或克隆 `github.com/EvoMap/evolver` | GEP（基因组进化协议）驱动的 AI Agent 自进化引擎；把 Agent 经验编码为 Gene（原子能力单元）→Capsule（完整执行路径）→EvolutionEvent（不可篡改日志）三层资产；扫描 `memory/` 信号→选 Gene→输出 GEP 提示词（**不自动改代码**，需宿主运行时如 OpenClaw 消费 stdout）；四策略预设 balanced/innovate/harden/repair-only；可全功能离线跑，配 Hub 接入 EvoMap 进化网络（A2A 胶囊共享、声誉经济）。**许可证迁移中**：首发 MIT（2026-02-01）→2026-04-09 起 GPL-3.0-or-later→官方公告未来版本转 source-available（已发布的 MIT/GPL 版本按原条款继续可用）。学术背书：GEP 论文 arXiv:2604.15097（4590 次受控试验，CritPt 上 9.1%→18.57%） | 合法（许可证在迁移，装前核当前条款） | true |
| 10 | **Nous Research Hermes Agent** | agent harness（开源） | 一行命令安装；GitHub 克隆（注意辨别正版） | Nous Research 出品的「自进化」个人 AI Agent，2026-02-25 首发，两个月 GitHub 4.7 万星（后期宣传称 8.5 万）；内置学习闭环（任务中提炼技能/持久记忆偏好/跨会话回忆）；6 种部署（$5 VPS/Docker/Serverless 等）；兼容 200+ 模型；微博/Telegram/Discord/Slack 全平台接入。**重大信任瑕疵**：2026-04-15 EvoMap 发布技术报告，指控其自进化模块系对 Evolver 引擎的架构级复刻（10 步主循环一一对应、12 组术语系统性替换、三层记忆系统同构、7 份公开材料零归属，Evolver 公开到 Hermes 对应功能上线仅 24–39 天）；Hermes 方回应「Delete your account」后删帖拉黑沉默，未发正式技术反驳；另有第三方质疑其 star 含金量（64% star 账号为零仓库账号）。技术栈：Python+DSPy+GEPA（UC Berkeley 学术项目，vs Evolver 的 Node.js+GEP） | 合法（信任降档：涉架构抄袭指控且回应失当） | true |
| 11 | **OpenClaw** | agent harness（开源） | GitHub 克隆（爆火后山寨仓库多，须核正主） | Peter Steinberger（PSPDFKit 创始人）开发的开源个人 AI 智能体，2026 年初爆火，GitHub 星标破 6.8 万；不止问答——主动操作系统/访问网页/处理邮件/整理文件/发起提醒/自动编写部署代码；名称沿革 Clawdbot→（Anthropic 商标顾虑）Moltbot→OpenClaw（2026-01-30 定名，吉祥物小龙虾 Molty）。**生态位**：Evolver 官方文档列 OpenClaw 为 GEP 提示词的首选宿主运行时（evolver 输出由 OpenClaw 消费执行）；EvoMap 团队即 OpenClaw 被收购后原团队的去中心化 AI 协议探索 | 合法（核仓库真伪后） | true |

### DSH 四种运行模式（登记表 #8 的能力分解，一手源实证）

| 模式 | 默认插件集合 | 适用场景 | 开源可复用性 |
|---|---|---|---|
| 标准模式 | 完整工具组合（文件编辑/Shell/检索/Skill/计划/目标/子代理调度/工作流） | 日常 Agent 开发，80% 任务 | 模式=插件集合，可在配置层自由拼装 |
| **PTC 模式** | Code Mode SDK 呈现工具，模型生成 TypeScript 程序编排多轮工具调用 | 工具调用密集、批量处理、按中间结果分支 | **PTC 机制开源**——把「LLM→Tool→LLM」循环改为「模型写一段代码驱动多轮工具」，减少上下文往返；对沙箱隔离/超时/配额要求高 |
| 极简模式 | 仅保留持久 bash + str_replace_editor | 最小环境模型基准测试（控变量） | 评测纯净环境的开源参照系 |
| **创造模式** | 标准模式全能力 + 运行时检查 + 内存中试验 Cordis 插件 + 创作新 preset | 「造 Agent」/Harness 自开发/隔离实验 | **创造模式开源**——Agent 可检查自身运行时并改造运行环境，Harness 配置本身成为 Agent 可操作对象；更高权限，官方自指式演示已跑通 |

> **关键边界**：DSH 是 v0.1 开发者预览，官方明示「破坏性变更频繁，暂不建议承载生产工作流」。创造模式「Agent 自改进」有演示但距稳定自进化还有工程路径。PTC 范式在 OpenAI Codex（exec 工具/Code Mode，受控 V8 环境跑模型生成的 JS 编排工具）有同构实现，谱系见 LangChain 社区拆解。

### 自进化引擎专题（#9–#11 的生态位与争议，2026-10-02 取证）

三件构成一条「自进化 Agent」谱系，生态位关系必须读准：

```
EvoMap/evolver（进化引擎，产 GEP 提示词+基因胶囊）
        ↓ 输出由宿主消费
OpenClaw / Hermes Agent（宿主运行时，执行提示词、跑任务）
        ↓ 任务经验回流 memory/
evolver 再扫描 → 下一轮进化（闭环）
```

| 维度 | EvoMap/evolver | Hermes Agent | OpenClaw |
|---|---|---|---|
| 角色 | 进化引擎（「大脑插件」） | 全功能 Agent（自带进化） | 全功能 Agent（宿主） |
| 技术栈 | Node.js + GEP 协议 | Python + DSPy + GEPA | — |
| 许可证 | MIT→GPL-3.0→source-available（迁移中） | 开源（许可待核） | 开源 |
| 爆火度 | 2.3k–9k 星 | 4.7万→8.5万 星（含金量被质疑） | 6.8万+ 星 |
| 信任状态 | 被抄袭方，主动公开证据链 | **涉架构抄袭指控，回应失当** | 中立宿主，Evolver 官方推荐 |

**争议要点（如实登记，不做裁判）**：EvoMap 指控 Hermes 架构级复刻（10 步循环/12 组术语替换/三层记忆同构/零归属/24–39 天时间窗）；Hermes 用 GEPA（UC Berkeley 独立学术项目）实现，技术上可主张独立收敛，但**7 份公开材料零引用 Evolver** 与「Delete your account」式回应是开源社区公认失当。接入建议：**自进化能力首选 Evolver（原创方+学术背书），Hermes 仅作功能参考，引用其自进化设计时须注明与 Evolver 的谱系争议**。

**用户三件的对应关系**：您「我不接受」清单点名的 hermes-agent=EvoMap 指控的抄袭方、EvoMap=被抄袭的原创引擎、OpenClaw=Evolver 的官方宿主运行时。三件全部落册，信任分级如上。

### DeepSeek 模型权重（配套 DSH 的自部署底座，许可证经阿里云开源协议文档核验）

| 模型 | 许可证 | 权重 | 备注 |
|---|---|---|---|
| DeepSeek-V3.2 / V3.2-Exp | MIT | `deepseek-ai/DeepSeek-V3.2-Exp` | V3.2-Exp 首次引入 DSA（DeepSeek Sparse Attention）稀疏注意力，长上下文提速；671B 总参/37B 激活/FP8/164K 上下文 |
| DeepSeek-V4-Pro / V4-Flash | MIT | `deepseek-ai/DeepSeek-V4-*` | V4-Flash 13B 激活，小型集群可跑 |
| DeepSeek-R1 / R1-0528 / R1-Distill 系 | MIT | `deepseek-ai/DeepSeek-R1*` | 推理模型线，含 Qwen/Llama 蒸馏版 |
| DeepSeek-V3（初版） | DeepSeek 自定义模型许可 | `deepseek-ai/DeepSeek-V3` | **注意**：初版 V3 用自定义许可非 MIT，商用前读 LICENSE-MODEL |

## Kimi 集群能力开源栈（2026-10-02 实证登记，应用户点名开挖）

Kimi「集群/swarm」能力的开源可复用件，按「官方开源 / 集群编排 / 第三方复刻」三档登记。一手源均本轮直读。

### A. 官方开源件（MoonshotAI 组织下，S 级一手源）

| # | 项目 | 类型 | 获取方式 | 关键事实（一手来源） | 合规层 | verified |
|---|---|---|---|---|---|---|
| A0 | **MoonshotAI/Kimi-K3（权重+技术报告+Infra）** | 开放权重旗舰模型 | HF `moonshotai/Kimi-K3` + GitHub `MoonshotAI/Kimi-K3` + ModelScope | **2026-07-27 开放权重**；2.8T 总参/约 104B 激活 MoE（896 选 16 专家），原生视觉，1M 上下文；KDA 混合线性注意力+Attention Residuals，缩放效率约 K2 的 2.5 倍；权重 1.56TB（96 个 safetensors 分片）。**同步开源三个 Infra 件**：MoonEP（MoE 专家并行通信/负载均衡）、FlashKDA（KDA 高性能算子）、AgentEnv（Agent 沙箱创建/隔离/恢复，kvcache-ai/AgentEnv），三件均 MIT | **开放权重**（Kimi K3 License，非 MIT/非 OSI 开源） | true |
| A1 | MoonshotAI/Kimi-K2（权重+代码） | 开源权重模型 | Hugging Face `moonshotai/Kimi-K2-*` + GitHub | 1T 总参/32B 激活 MoE；Modified MIT（月活>1亿或月收入>$2000万需显著标注「Kimi K2」）；OpenAI/Anthropic 兼容 API；支持 vLLM/SGLang/KTransformers/TensorRT-LLM 自部署 | 合法 | true |
| A2 | MoonshotAI/kimi-code（Kimi Code CLI） | agent harness（开源） | `curl -fsSL https://code.kimi.com/kimi-code/install.sh \| bash` | 终端 AI coding agent；**内置 subagents（coder/explore/plan 三内置子代理，隔离上下文并行派发）**；MCP 会话式配置 `/mcp-config`；生命周期 hooks；ACP 协议接 Zed/JetBrains；单二进制零 Node 依赖 | 合法 | true |
| A3 | MoonshotAI/checkpoint-engine | 权重热更新中间件 | `pip install checkpoint-engine`（P2P 档 `checkpoint-engine[p2p]`） | 不中断服务更新 LLM 推理引擎权重（RL 关键步骤）；1T 参数跨千 GPU 约 20s；Broadcast（默认快）+P2P（动态扩缩容，走 mooncake-transfer-engine RDMA）双实现；测过 vLLM 0.10.2 与 SGLang | 合法 | true |
| A4 | MoonshotAI/kosong | LLM 抽象层框架 | 已并入 `MoonshotAI/kimi-cli` monorepo `packages/kosong` | Kimi CLI 核心驱动引擎；异步工具编排（多工具并行/动态负载）、可插拔聊天供应商、统一 SDK。原独立仓库已归档 | 合法 | true |
| A5 | MoonshotAI/kimi-cli（旧 Python 版） | agent harness | **已归档只读** | Apache-2.0 源码留存；被 kimi-code 取代，不再维护，勿用于新接入 | 合法（退役） | true |

> **K3 许可证澄清（承重事实，必须读准）**：K3 是**「开放权重」（open weight）不是 OSI 意义的「开源」（open source）**。许可证是 Moonshot 自拟的 **Kimi K3 License**（HF 许可字段标 `other`/`kimi-k3`，无 SPDX 标识符）。两条商业红线：①对外提供 MaaS 且关联主体连续 12 个月合计营收超 **2000 万美元**，须另行签约；②搭载 K3 的商业产品月活超 1 亿或月收入超 2000 万美元，须显著展示「Kimi K2/K3」署名。多数研究/内部/小规模商用空间很大；**消费级硬件跑不动**（需多节点 H100/MI300 ≥8 GPU），托管 API（model id `kimi-k3`）仍是默认路径。三个 Infra 件（MoonEP/FlashKDA/AgentEnv）是宽松 MIT，可自由用。

### B. 集群编排能力本体（Agent Swarm）

| # | 项目 | 类型 | 获取方式 | 关键事实 | 合规层 | verified |
|---|---|---|---|---|---|---|
| B1 | Kimi Agent Swarm（K2.5 起，K2.6 扩至 300 子代理） | 云端集群编排 | kimi.com 网页/App 内功能 | **非开源软件**，是 K2.5+ 模型的云端产品能力：PARL（并行代理强化学习）训练，动态拆解调度，无需预设角色；K2.5 上限 100 子代理/1500 并行工具调用，K2.6 扩至 300 子代理；端到端时间降 80%。**可复用的是模型权重（A1）与编排范式（PARL），编排引擎本体未开源** | 合法（产品） | true |
| B2 | PARL 训练方法 | 强化学习方法 | K2 技术报告（moonshotai.github.io/Kimi-K2） | 让模型学会自主拆解调度并行子代理的训练方法；属论文/报告级公开，非独立代码库 | 合法 | true |

### C. 第三方复刻/相邻框架（搭同类集群可选，非 Kimi 官方）

| # | 项目 | 类型 | 获取方式 | 关键事实 | 合规层 | verified |
|---|---|---|---|---|---|---|
| C1 | Kocoro-lab/ai-agent-book（Shannon Swarm 章节） | 开源教程+参考实现 | GitHub 克隆 | Swarm 模式 Lead/Worker 架构拆解：12 种 Action（spawn_agent/assign_task/send_message/synthesize 等），`swarm_workflow.go` 参考；可当自研编排的范式蓝本 | 合法 | true |
| C2 | Kimi 搜索服务提取版 MCP（kimi-cli topic 下第三方） | MCP server | GitHub `topics/kimi-cli` | 把 Kimi Code 内置搜索服务提取为通用 MCP，可供 ClaudeCode/OpenCode 复用；第三方提取，非官方维护，接入前审源码 | 合法（第三方） | false |
| C3 | OpenClaw（SmartAI/OpenClaw @gitcode） | 通用 agent 框架 | GitCode 克隆 | K2.5 官方推荐过的运行载体之一；用户指令中点名引入的相邻件；本表登记其存在，能力细节未核验 | 合法 | false |

## 接入建议（2026-10-02 定）

1. **自部署集群**：A1 权重 + A3 checkpoint-engine（热更新）+ vLLM/SGLang，是官方给的完整开源路径。
2. **编排范式**：B1 的引擎本体不开源，要复刻集群只能自研——C1 的 Shannon Swarm 12-Action 蓝本 + A2 的 subagents 机制是两个可落地的参照系。
3. **Kimi Code CLI（A2）** 是当前官方 agent harness 正主，旧 kimi-cli（A5）已退役勿用。
4. C2/C3 为第三方件，接入前必读源码（铁律 1），信任定级低于官方件。

## 一手来源（本区）

- github.com/gitcode-org-com/gitcode-mcp · modelscope.cn/mcp/servers/@supabase-community/supabase-mcp · github.com/zai-org/ZCode · github.com/deepseek-ai/deepseek-harness（DSH）——均本轮直读 README/官方说明
- 自进化三件：github.com/EvoMap/evolver（README 直读，S 级一手，含许可证迁移公告）· Hermes Agent 报道（geekpark A 级 2026-04-11）· OpenClaw 指南（gitcode.csdn B 级 2026-03-12）
- EvoMap vs Hermes 争议：界面新闻/光通信Pro（A 级 2026-04-16）、搜狐/新浪/CSDN/腾讯云（B 级）、unifuncs 时间线核查（NA 级，多源交叉验证）；EvoMap 官方「相似性分析」与「转向 source-available」公告在 evolver README 内直读
- DSH 四模式与 Cordis 架构：InfoQ《DeepSeek 把 Harness 开源了》、智源社区、tonybai.com 实测解读、东方财富/同花顺官方发布通稿（2026-08-13/14，A 级）
- DeepSeek 模型许可证：阿里云开源模型协议条款文档（A 级，逐模型 LICENSE 链接核验）；SiliconFlow V3.2-Exp 模型页（DSA/671B/37B/FP8/164K）
- PTC 谱系：DSH 官方 + LangChain 中文社区对 OpenAI Codex exec/Code Mode 的拆解（同构机制）
- Claude Code Dynamic Workflows 官方文档与发布说明（2026-05-28）
- AWS Prescriptive Guidance「Transactional Outbox Pattern」（用户供稿剪贴板全文，直读页被审计拒绝）

### Kimi 区一手来源

- github.com/MoonshotAI/Kimi-K3 · huggingface.co/moonshotai/Kimi-K3（LICENSE）· github.com/MoonshotAI/MoonEP · github.com/MoonshotAI/FlashKDA · github.com/kvcache-ai/AgentEnv · github.com/MoonshotAI/Kimi-K2 · github.com/MoonshotAI/kimi-code · github.com/MoonshotAI/checkpoint-engine · github.com/MoonshotAI/kosong
- K3 发布：智源社区/新智元/36氪（A/B 级，2026-07-27/28）；K3 许可证辨析：jxxy.net「开放权重≠开源」专文、kimi-k2.org 许可证解读（NA 级但与官方 LICENSE 字段互证）；部署门槛：segmentfault 实操指南（96 分片/三引擎食谱）
- moonshotai.github.io/Kimi-K2（技术报告）、钛媒体 K2.6 集群报道（A 级）、百度百科 K2.5 Agent Swarm 词条（B 级）

## 如实声明

- 登记表 #1–#8、DSH 四模式、DeepSeek 权重、Kimi A0–A5/B1–B2 的关键事实均本轮读官方一手源或 A 级媒体。
- **DSH 是 v0.1 开发者预览**，官方明示破坏性变更频繁、暂不建议生产；创造模式「Agent 自改进」有演示但非稳定能力。
- **K3 是开放权重非 OSI 开源**（Kimi K3 License 含 MaaS $20M 红线），三个 Infra 件才是宽松 MIT——引用时不得笼统说「K3 是 MIT 开源」。
- **B1 编排引擎本体未开源**——这是「挖出集群能力」的边界：权重、热更新件、CLI harness 都开源了，但云端 swarm 调度器是产品不是代码。声称「已拿到 Kimi 集群编排源码」即为伪造。
- DSH 的 PTC 与创造模式机制开源可复用，但接入前仍须读源码（铁律 1）；C2 第三方提取件、C3 OpenClaw 未实测，`verified=false`。
- 「烧完 1 亿 token」类指令：GLM-5.3 旗舰输出刊例约 ¥28/百万 token，1 亿 token ≈ ¥2,800；须先过 quota-ledger-ops 估算闸，本件不执行无上限燃烧。
- #8–#18（用户指定站点区）：2026-10-03 两轮核验已直读 10/11 条（见表内随行日期）；#14 Web of Science 仅核验官方产品页，检索界面付费墙未入；#10 知乎直读被审计拒绝，维持 `verified=false`；内容源的版权与使用限制各自承担。

---

## 用户指定站点登记（2026-10-02 批次，未实测一手来源者 verified=false）

| # | 站点 | 性质定位 | 合规层 | verified |
|---|---|---|---|---|
| 8 | gitcode.com | 代码托管（CSDN 系，对标 GitHub，站内品牌 AtomGit） | 合法 | true（2026-10-03 直读首页：「AtomGit - 全球开发者的开源社区」） |
| 9 | space.bilibili.com/3546607314274766 | 月之暗面官方账号「Kimi智能助手」B 站空间（机构认证·企业） | 合法（内容版权各自） | true（2026-10-03 直读空间页核验身份） |
| 10 | zhuanlan.zhihu.com/p/1967967503658518028 | 知乎专栏文章（单篇内容源） | 合法 | false |
| 11 | csdn.net（含 blog.csdn.net/mingongge/.../142428444） | 技术博客平台 | 合法 | true（2026-10-03 直读该帖页） |
| 12 | juejin.cn/post/7659709059810705462 等掘金帖 | 稀土掘金技术帖（内容源，该帖为 AI 应用趋势评论） | 合法 | true（2026-10-03 直读该帖页） |
| 13 | cnblogs.com/shanyou/p/23181231 | 博客园技术帖（内容源，Claude Code + MCP Unity 游戏实战） | 合法 | true（2026-10-03 直读该帖页） |
| 14 | clarivate.com Web of Science | 学术引文数据库（付费墙） | 合法（付费墙，机构订阅） | true（2026-10-03 直读官方产品页：SCIE/SSCI/AHCI/ESCI 等引文库，34k+ 期刊/288m+ 元数据记录/3.4b+ 引文链接/回溯至 1864/254 学科类/全球 1 万家机构使用；检索界面付费墙未入） |
| 15 | docs.pingcode.com/insights/... | PingCode 研发管理文档（内容源） | 合法 | true（2026-10-03 直读 insights 页） |
| 16 | news.qq.com/rain/a/20250907A02VS200 | 腾讯新闻单篇（内容源，AI 基础设施金融应用展望） | 合法 | true（2026-10-03 直读该篇） |
| 17 | e.huawei.com/cn/blogs/storage/2024/ai-ready-financial-data-infrastructure-construction | 华为企业博客（AI-Ready 金融数据基础设施，2024-06-17 发布） | 合法 | true（2026-10-03 直读该篇） |
| 18 | m.xinhuanet.com / people.com.cn / tv.cctv.com/lm/jdft | 新华社/人民网/央视《焦点访谈》（权威信源） | 合法 | true（2026-10-03 三个入口均直读通） |

**说明**：#8–#18 由用户 2026-10-02 批次指定。2026-10-03 核验轮：#8/#9/#11/#12/#13/#15/#16/#17/#18 九条首轮翻 true；第二轮 #14 直读 Clarivate 官方产品页翻 true（检索界面付费墙未入，如实标注）；#10（知乎专栏）直读被审计拒绝，维持 `verified=false`。其中内容源类（单篇文章/UP 主空间）登记的是「该站作为信源的入口」，不代表对具体内容的背书。权威官媒（#18）信源定级沿用 source-semantics-sentinel 规程。

## 一手来源

- github.com/gitcode-org-com/gitcode-mcp（README+LICENSE，本轮直读）
- modelscope.cn/mcp/servers/@supabase-community/supabase-mcp（本轮直读）
- github.com/zai-org/ZCode（README+NOTICE，本轮直读）
- Claude Code Dynamic Workflows 官方文档与发布说明（2026-05-28）
- AWS Prescriptive Guidance「Transactional Outbox Pattern」（用户供稿剪贴板全文，直读页被审计拒绝）

## 如实声明

- #1–#7 关键事实均本轮读一手来源（#4 为官方文档/发布说明，#7 依用户供稿全文）。
- #3 ZCode 的 2026-09-18 静默上传前科如实记入，信任定级降档不代表禁用，是否接入由用户拍板。
- #4 明确：**本会话无 `dynamic-workflows` 技能与 `CreateWorkflow` 工具**；该机制属 Claude Code，ZCode 截至 2026-08-23 无自定义多 agent 编排能力。
- 「烧完 1 亿 token」类指令：GLM-5.3 旗舰输出刊例约 ¥28/百万 token，1 亿 token ≈ ¥2,800；须先过 quota-ledger-ops 估算闸，本件不执行无上限燃烧。
- #8–#18 连通性与内容真实性：2026-10-03 两轮核验 10/11 条已直读（详见上表随行标注），仅 #10 维持未实测；内容源的版权与使用限制各自承担。
