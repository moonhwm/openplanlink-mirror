---
name: otl-format-ops
description: "[项目技能] OTL 编写总署——生态项目文件的 WPS 智能文档（.otl）编写标准与发布管线：唯一真源 Markdown 主文档 → 静态闸 lint → kdocs otl 发布 → 写后核验 → 回写登记。触发（满足任一）：①用户说「OTL」「智能文档」「按 OTL 标准写」「otl 编写规范」「写成 otl」「发布到金山文档/WPS 云文档」或等价表述（含语音变体，不纠正用户、映射意图）；②需要把项目文件（技能文书/台账/开放计划/协调记录等）编写或改写为 OTL 智能文档时；③需要审计既有 OTL 主文档是否符合编写标准（lint）时；④需要把 Markdown 主文档发布/更新到 kdocs .otl 并回写登记 file_id 与链接时。覆盖：OTL 格式事实卡与生态定位、Markdown 主文档编写子集约束（title 规则/标题层级/围栏代码块/图片）、项目文件标准骨架（文档头六要素+变更记录）、四类文书模板、scripts/otl_source_lint.py 静态闸、发布与回写流程。不覆盖：kdocs API 调用纪律与认证本体（归 kdocs 插件 skill，引用不复制）、协调函六段式格式本体（归 coordination-letter）、.otl 的本地二进制解析（云原生格式无此路径）、与 WPS 无关的同名 .otl（NoteTab 大纲文件）。中文名：OTL 编写总署。English triggers: OTL writing standard, WPS smart document authoring, otl markdown publishing pipeline, kdocs otl standard, project file lint gate."
---

# OTL 编写总署

## 定位

生态内一切要进入 WPS 智能文档（.otl）的项目文件，编写、审改、发布、回写统一走本标准。操作层（认证、参数细节、限流处置）归 kdocs 插件 skill，本件只管「写什么、怎么写、怎么验、怎么登记」。

## 五条铁律

1. **唯一真源在 Markdown 主文档**。OTL 是云原生封闭格式（仅 WPS 新版客户端/网页可读写），不可本地解析、不可离线兜底。因此每份 OTL 文档必须有一份本地 `.md` 主文档作为可编辑真源；云端 .otl 只是主文档的发布态。**禁止**只在云端改而不回写主文档——发现即视为主文档过期，以云端为准重灌一次并登记。
2. **先过 lint 闸再发布**。任何主文档发布/更新前必跑 `python3 scripts/otl_source_lint.py <file.md>`，零 error 方可写入；error 不过即改文档，不改闸。
3. **写后必核验**。写入完成后用 `otl.block_query`（`blockIds: ["doc"]`）独立回读比对标题与关键节，不信任 `code: 0`（与 kdocs 纪律一致）。
4. **回写登记即完成**。发布/更新完成后，把 `file_id`、访问链接、发布时间、主文档 sha256 前 16 位登记回主文档文档头；未登记视为未发布。
5. **replace 全量覆盖须用户确认**。文档已有内容时，`mode=replace` 与 `block_update(doc, update_content)` 都是覆盖全文，执行前必须向用户确认；局部更新优先 append/prepend 或精准块操作。

## 格式事实速览

- OTL = WPS 365 智能文档（后缀 `.otl`，WebOffice type `o`），云原生、块结构（doc/title/heading/paragraph/table/codeBlock/highLightBlock 等节点）。
- 写入面：`kdocs-cli otl insert-content`（Markdown/HTML → 自动转块）、`block_query/insert/update/delete`、`convert`（仅转换不落文档）。
- 内容以 **CommonMark 子集**驱动：一级标题提取为 `title`、正文从二级标题起、Unicode 制表图必须围栏代码块包裹、图片仅 base64 或公网直链。
- 详细事实卡与风险对策：读 `references/otl-facts.md`。

## 编写工作流

1. **定文书类型**：技能文书 / 台账 / 开放计划 / 通用项目文书，从 `assets/templates/` 复制对应模板为主文档起点；模板即标准骨架的活样例。
2. **填骨架**：文档头六要素（文档标识/版本/状态/更新日期/责任席/关联锚点）+ 正文 + 文末「变更记录」节，缺一不可（lint 强制）。
3. **守子集**：按 `references/markdown-subset.md` 的约束写正文——H1 唯一且仅作标题、层级不跳级、制表图入围栏、图片合规。
4. **过闸**：跑 lint，error 清零、warning 逐条处置。

## 发布工作流

1. 前置：`bash <kdocs skill>/scripts/auth_restore.sh` 恢复登录（沙箱）；读 `references/publishing.md` 确认本次发布路径（新建 / 追加 / 局部更新 / 全量替换）。
2. lint 闸：零 error。
3. 写入：按 `references/publishing.md` 的调用卡执行（新建用 `create_file_with_content` 或 `create_file`+`insert-content`；title 从主文档 H1 提取并从 content 剔除）。
4. 核验：`otl.block_query` 回读，比对标题与至少一个关键节文本。
5. 回写：主文档文档头登记 file_id、链接、发布时间、sha256[:16]；向用户展示可访问链接。
6. 失败处置、限流熔断、并发冲突：一律按 kdocs skill 错误速查表执行，本件不另立法。

## 资源清单

| 资源 | 用途 | 何时读/用 |
|------|------|-----------|
| `references/otl-facts.md` | OTL 格式事实卡、封闭性风险与双轨对策 | 首次接触 OTL 或需向用户解释格式边界时 |
| `references/markdown-subset.md` | Markdown 主文档子集约束与节点映射表 | 编写/审改主文档时 |
| `references/publishing.md` | 发布路径决策、调用卡、核验与回写细则 | 每次发布/更新前 |
| `scripts/otl_source_lint.py` | 主文档静态闸（E01–E09 错误 + 警告），`--self-test` 自检，`--json` 机器输出 | 发布前必跑；审计既有主文档时 |
| `assets/templates/skill-doc.md` | 技能文书模板 | 为技能写 OTL 说明/修订文书 |
| `assets/templates/ledger.md` | 台账模板 | 登记类项目文件 |
| `assets/templates/plan.md` | 开放计划/排期书模板 | 计划类项目文件 |
| `assets/templates/general-doc.md` | 通用项目文书模板 | 其他项目文件 |

## 边界与联挂

- kdocs 插件 skill：认证、参数约束、限流熔断、写后核验纪律的本体，本件引用不复制；调用前以其 `references/otl/*.md` 为参数准。
- coordination-letter：协调函/回执的段落格式本体；函件要落成 OTL 时，骨架用本件、段落格式用彼件。
- 主文档存放：随项目落盘（技能目录、注册处或 upload 持久层），`.md` 与云端 `.otl` 一一对应，文档头互为指针。
