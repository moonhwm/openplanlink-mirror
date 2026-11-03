# OTL 格式事实卡

> 本卡是 otl-format-ops 的事实底座：只收录已核实的格式事实与生态对策，不收录操作参数（参数以 kdocs 插件 skill 的 `references/otl/*.md` 为准）。

## 目录

- 是什么
- 操作面（kdocs-cli otl）
- 内容模型
- 封闭性风险与双轨对策
- 同名异物辨析

## 是什么

| 事实 | 内容 |
|------|------|
| 全称定位 | WPS 365 智能文档（Smart Document），WPS 云原生的在线协作文档格式 |
| 后缀 / 类型码 | `.otl`；WebOffice 预览编辑服务中 type 值为 `o` |
| 打开方式 | WPS 新版客户端、金山文档网页端；旧版 WPS 与第三方办公套件均不能原生打开 |
| 内容特性 | 块结构文档（title/heading/paragraph/table/codeBlock/highLightBlock 等节点），官方写入接口接受 Markdown/HTML 并自动转块 |
| AI 覆盖 | WPS AI 写作能力覆盖最完整的组件之一（帮我写/帮我改/全文总结/文档问答/划词） |
| 上下游 | 可作为 WPS 灵犀读文档、AIPPT 大纲生成等能力的输入格式 |

## 操作面（kdocs-cli otl）

| 工具 | 用途 | 幂等 |
|------|------|------|
| `otl.insert_content` | Markdown/HTML 写入：prepend / append / replace | 否（重复调用会重复插入） |
| `otl.block_query` | 读块结构与内容（`blockIds:["doc"]` 取全文） | 是 |
| `otl.block_insert` | 指定父块下按 index 插入块 | 否 |
| `otl.block_update` | 块内容/属性更新、表格行列与单元格操作（operation 族） | 是 |
| `otl.block_delete` | 删块（不可逆，须用户确认） | — |
| `otl.convert` | Markdown/HTML → 块结构（只转换，不落文档） | 是 |

三条已核实的硬约束：

1. **title 规则**：写入新建/空白文档时必须把开头一级标题的文字提取为 `title` 参数并从 `content` 删除；否则标题空缺、H1 误入正文。doc 首子节点必须是 title 且全局唯一。
2. **CommonMark 子集**：`content` 不是全量 Markdown；Unicode 制表图落在普通段落会错位，必须整段入围栏代码块。
3. **InvalidArgument 不原样重试**：先重构 content 或改用 block_delete + block_insert 精准操作；非幂等写入失败后先 block_query 确认现状再决定重试。

## 内容模型

Markdown 元素 → OTL 节点的映射细则见 `markdown-subset.md`。块节点全表（类型、可容纳子节点、属性）以 kdocs skill `references/otl/node.md` 为唯一准——本件不复制。

## 封闭性风险与双轨对策

| 风险 | 实证 | 对策（本标准立法） |
|------|------|------|
| 生态封闭 | 仅 WPS 新版客户端/网页端可读写，第三方套件与旧版 WPS 均不支持 | 唯一真源在本地 Markdown 主文档；云端 .otl 仅为发布态 |
| 离线不可用 | 云原生格式，断网无法打开/预览，本地缓存亦然 | 主文档即离线副本与灾难恢复基线 |
| 导出受限 | 社区长期反馈不支持导出 Markdown/HTML | 不依赖「从 otl 导出」路径；回写方向恒为 主文档 → otl |
| 协作漂移 | 他人在云端直接改，主文档过期 | 发现云端与主文档不一致：以云端为准重灌主文档一次、登记差异、此后仍只从主文档发布 |

## 同名异物辨析

`.otl` 另有 NoteTab Outline File（Fookes Software 的 Windows 文本编辑器大纲格式）等历史用途，与 WPS 智能文档**毫无关系**。生态内说 OTL 一律指 WPS 智能文档；遇到外部 `.otl` 文件先确认来源，不套用本标准。
