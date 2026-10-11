# 产学研协同 A2A 节点发现与接入规范

本规范按委托方指定的党组学术技术工作语境记录技术事实与实施建议。供应商授权、参与单位身份、机构审批和共同体决议以对应回执为准。

## 问题与本轮成果

现有本地节点已返回可验证的自定义 HMAC 应答，五个席位返回未签名的入队状态。Agent Card 声明协议版本 0.3.0，但声明、认证、标准方法互操作及独立席位签收是不同证据。本轮最小实现用于生成有时间和来源的发现记录，避免将网页 active、数据库活动或未验证声明直接用于任务分派。

## 需求与验收

- D1：默认仅访问已知回环地址的 `/.well-known/agent-card.json` 和 `/health`。不扫描网段、启动进程或改动路由。
- D2：远端只接受显式列入允许清单的 HTTPS origin；拒绝用户名、密码、查询参数、片段及非根路径。发现时不跟随卡片中的地址或 HTTP 重定向。
- D3：每次请求有限时、大小上限和严格 JSON 解析；拒绝重复字段、非有限数值及非对象响应。失败记录只保存状态与错误类别，不保存原始错误正文、凭据或描述文本。
- D4：记录卡片基本字段的存在与类型、声明的有限版本值及能力数量。这只是基本字段检查，不等于完整 schema 验证、签名验证或标准方法调用验收。
- D5：发现记录包含观测时刻、发现阶段和失效时刻。`authenticated_node_verified`、`standard_methods_verified`、`independent_peer_acknowledged` 和 `eligible_for_task_dispatch` 默认 false，不由卡片、健康页或版本声明提升。
- D6：输出保存为新的 UTF-8 JSON 文件；已有结果不得覆写。实际运行证据保存在受控目录，公开仓库只发布工具、规范、测试及事实摘要。
- D7：`/health` 是本项目约定的探测扩展，不宣称为 A2A 标准路径。共享 HMAC 证明信任域持有密钥，不单独证明某机构身份或席位不可否认签名。

## 产学研协同接入关系

需求提出方提供任务目标、数据范围和成果验收标准；学术技术验证方提供方法、可复现实验及限制；实施方提供环境、运行回执和反馈。上述任务关系是方案设计，不等同已登记的参与单位。各方的节点需分别取得身份绑定、可验证能力、授权范围、可达端点与有效期，随后通过标准 `message/send`、`tasks/get` 及失败路径验证，再进入任务分派。

项目与资料链接通过受控 catalog 登记。一个共享中转节点应答不能替代五个独立节点的证明。现有数据库可提供登记、租约、广播和语义锚点的结构参考，本轮不创建或修改生产表。

## 云端执行和华为云 X 效能

云端验收绑定 GitHub 已发布提交、规范 ID、输入摘要、环境与输出摘要。Claude Code 云会话与华为云 X 实例的执行位置分别记录；未验证实例 ID 和运行回执时，不把供应商托管云会话计入华为云 X 作业。

真实计算任务先做单作业基线，再比较增加并发后的有效吞吐量、CPU 利用率、峰值内存、排队时间、P95 延迟、失败率和费用。仅在有待处理任务且观测值支持时扩并发；IO 等待采用有界预取和批处理。为正常协同服务及 VPN 留出资源并记录影响。无任务时的空闲及未知指标如实保留，不以无效计算或占满内存替代生产效能。

华为云执行前需实例 ID、区域、已授权配置引用和实际任务清单。当前这些定位尚未齐备，作业与效能保持“未实测”，该阶段不宣称云端调度已实施。

## 验收证据层级

configured → card_observed → transport_observed → authenticated_node_verified → standard_methods_verified → independent_peer_acknowledged → task_dispatch_eligible。

这些阶段需要各自证据，前一阶段通过不自动使后一阶段成立。观测过期后必须重新核查，不以监控已启用推断连续在线。

## 规范来源

- [A2A 0.3.0 官方规范](https://a2a-protocol.org/v0.3.0/specification/)：版本固定为现有节点声明，用于后续兼容验收；不声明其为全局最新版本。
- [Claude Code 云端官方文档](https://code.claude.com/docs/zh-CN/claude-code-on-the-web)：云会话、GitHub 连接和环境设置分别核验。
- [John's Blog SDD 原文](https://johng.cn/ai/sdd-spec-driven-development)：据其规范驱动思想设置需求、计划、任务、实施与反馈记录；文中效率案例不作为本项目实测。
- [IBM CI/CD 说明](https://www.ibm.com/cn-zh/think/topics/ci-cd)、[Atlassian MVP 说明](https://www.atlassian.com/zh/agile/product-management/minimum-viable-product)：本轮小范围发现工具与可复核门禁对应最小实现。
- [Hugging Face Spaces 官方说明](https://huggingface.co/docs/hub/spaces-overview)：可作为公开演示的候选载体，尚未部署；其算力不计入华为云 X。
