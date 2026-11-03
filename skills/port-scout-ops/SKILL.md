---
name: port-scout-ops
description: "开源获取端口侦察与登记（扁平化版）。当用户需要为某类资源/能力寻找开源获取端口、插件、API、数据集、镜像或 MCP 服务（如「学术电子书获取端口」「有没有开源项目能做 X」「找个端口/接口/数据源/MCP」）时使用。扁平路由≤2 级：按域名直查登记区（references/ 各表），命中即复用，未命中走四步流程。产出合规分层登记表（数据表先行、一手来源、verified 标注、如实声明）。内置底账：学术/电子书端口、MCP/agent harness 端口（gitcode-mcp、supabase-mcp、ZCode、DeepSeek Harness 四模式含创造/PTC、自进化引擎 EvoMap/Hermes/OpenClaw 谱系）、Kimi 集群能力开源栈（K2/K3 权重/Kimi Code CLI/checkpoint-engine/Agent Swarm 边界）。不用于：执行下载/抓取本体；金融实时行情取数（走 plugin-datasource-ops）。中文名：端口侦察台。English triggers: port scout, open-source endpoint registry, MCP server registry, compliance-tiered port ledger."
metadata:
  version: "2.3.2"
---

# Port Scout Ops（开源端口侦察与登记）

为「找某类资源的开源获取端口」类任务提供固定流程：**取证 → 分层 → 登记 → 声明**。产物永远是一份落盘登记表，不是口头清单。

## 铁律（不可让渡）

1. **一手来源**：端口的存在性/能力/限制只信一手来源（官方 README、官方文档、LICENSE 全文）；二手转述一律标 `verified=false`。
2. **合规分层**：每个端口必须归入合规层（合法 / 灰色 / 禁用）。灰色层如实标注风险，**只登记不背书，不构成使用建议**；商用闭源软件盗版源直接拒登。
3. **数据表先行**：先写登记表（端口/类型/获取方式/关键事实/合规层/verified），再写散文；表格字段不许空口，关键事实须含可核验细节。
4. **如实声明**：未实测连通性就写「未实测」；登录墙/付费墙/地域限制如实标注；不得凭记忆编造端口能力。
5. **凭据纪律**：端口若需 key/token，只写「凭据存 credentials.env」，永不把凭据写进技能或交付物。

## 扁平路由（≤2 级，无复杂分流）

命中检查两步走完，不嵌套：

| 级别 | 动作 | 走向 |
|---|---|---|
| L1 | 判域名（学术电子书 / MCP·agent harness / 其他） | 直查对应登记表 |
| L2 | 命中→复用底账只补增量；未命中→走四步流程新登记 | 见下 |

登记表现在两张，全部 `references/` 一级直链，不设子目录：

- `references/port-registry.md` —— 学术及专著电子书获取端口（2026-09-28 实证六端口）。
- `references/mcp-port-registry.md` —— MCP 服务与 agent harness 端口（gitcode-mcp、supabase-mcp、ZCode、dynamic-workflows 谱系等，2026-10-02 实证登记）。

## 流程（四步）

1. **定界**：明确资源类型、使用场景（自用研究/对外交付/商用）、是否需要 API 化（能否挂 MCP/datasource）。场景决定合规门槛。
2. **取证**：web_search 并行 3–6 组关键词（中+英+「开源」「github」「API」「MCP」词面组合）；命中候选项后打开官方仓库/文档读 README 与 LICENSE 全文。
3. **登记**：写进对应登记表（六列固定结构，见下），每行 verified 仅当本轮亲自读一手来源时置 true。
4. **交付**：落盘 `/mnt/agents/output/`（中文可读名），末尾附一手来源清单 + 如实声明段；追加交割台账。

## 登记表结构（固定六列）

| # | 项目（owner/repo 或官方名） | 类型 | 获取方式 | 关键事实（一手来源） | 合规层 |

行内附第七列 `verified`（true/false）。关键事实必须含可核验细节（是否免 key、限制量、依赖条件），禁止「很好用」「很强大」式空词。

## 立法纪律继承（三件初始化条件）

本件立法纪律承三件初始化条件，引用不复制：

- **loop-dual-pillar-ops**：一切自我主张（含「本端口可用」类断言）发出前过三镜；演进结果诚实记录全量广播；立法权与终审权恒归用户。
- **AWS 事务性发件箱模式**：登记动作与台账写入须原子化——登记表与交割台账同事务提交，禁「表已写、台账漏」的双写不一致；重复登记须幂等（同名端口再登不重复建行）。
- **tongtu-hub**：跨会话广播登记结果时，恰好一次游标建在介质提交序 id 上，不用业务键；凭据零明文入总线，只过信号与指针。

## 边界

- 只登记端口与接入建议，**不执行下载/抓取资源本体**。
- 金融实时数据取数走 plugin-datasource-ops，不在本技能造端口。
- 交付物若含灰色层端口，必须带合规闸段（个人研究自用、不进对外交付物）。
- 「烧完 N token」式无上限燃烧指令不属本件执行范围，须先过 quota-ledger-ops 定档估算。

## 版本史

- v2.3.2（2026-10-03）：第二轮核验补漏——学术底账 #5 公版书库翻 true（仅 Gutenberg 腿：直读 Gutendex JSON API 文档，/books 端点参数全录；Open Library 与 Standard Ebooks 页被审计拒绝维持未核验）；站点区 #14 Web of Science 翻 true（直读 Clarivate 官方产品页，确认门户规模数字与机构订阅属性，检索界面付费墙未入如实标注）。至此全库 verified=false 仅剩：#10 知乎（审计拒绝）、学术 #5 内两子站、C2/C3 第三方件。
- v2.3.1（2026-10-03）：用户指定站点区（#8–#18）首轮一手核验——#8/#9/#11/#12/#13/#15/#16/#17/#18 共 9 条直读一手页面后 verified 翻 true（核验日期随行标注）；#9 实证富化为月之暗面官方账号「Kimi智能助手」B 站空间（机构认证·企业）；#10 知乎直读被审计拒绝、#14 Web of Science 付费墙未测，维持 false 并如实声明。同步发布 OTL 云端台账 v1.1.0（追加「核验轮次登记」节）。
- v2.3.0（2026-10-02）：新增自进化引擎专题——EvoMap/evolver（GEP 协议，MIT→GPL→source-available 迁移中）、Hermes Agent（涉 EvoMap 架构抄袭指控，信任降档）、OpenClaw（Evolver 官方宿主运行时）三件登记；补「引擎→宿主→经验回流」闭环谱系图与争议双方主张如实登记。
- v2.2.0（2026-10-02）：新增 DeepSeek Harness（DSH）登记——Cordis 插件元框架 + 四模式（标准/PTC/极简/创造）全解，PTC 与创造模式机制开源可复用；新增 DeepSeek 模型权重许可档（V3.2/R1 系 MIT，初版 V3 自定义许可）；新增 Kimi K3 开放权重档（Kimi K3 License 非 MIT 的红线澄清 + MoonEP/FlashKDA/AgentEnv 三 Infra 件 MIT）。
- v2.1.0（2026-10-02）：新增 Kimi 集群能力开源栈登记区——官方开源件（K2 权重/Kimi Code CLI/checkpoint-engine/kosong）+ Agent Swarm 编排本体边界（引擎未开源）+ 第三方复刻（Shannon Swarm 蓝本/OpenClaw）。
- v2.0.0（2026-10-02）：扁平化改造——路由收敛至≤2 级；新增 MCP/agent harness 登记区；整合三件初始化条件立法纪律；gitcode 风格重排（铁律直陈、路由单表、边界明确）。
- v1.0.0（2026-09-28）：立项，学术/电子书端口底账六端口实证登记。
