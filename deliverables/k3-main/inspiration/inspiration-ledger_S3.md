# 五源灵感台账 S3（INSPIRE-20261006-01）

> 只读接入，按声明顺序 ima → Supabase → Neon → WPS → 百度云盘。凭据主权纪律：任何 token/key 不落盘不入台账。

## ① ima —— 能力占位（如实声明）

- 实证：`A:\ima.copilot\` 安装目录在位（ima.copilot.exe 及组件清单已只读核验）。
- 缺口：技能索引无 ima-skill，无 MCP/API 通道实证；机主此前提供的 ima 凭证属凭据，按铁律不落盘、不尝试明文调用。
- 灵感（间接）：ima 作为知识库席，与 wps-knowledgebase（kwiki-cli）同生态，后续若开通通道，A2A 节点知识库可挂 ima 侧。
- 处置：挂账「ima 接入通道待机主明示安全通道」（与 SCH-11 尾项合并跟踪）。

## ② Supabase（总线） —— 已接入，实获三条

1. **在线节点名册（节点发现实证）**：近链上活跃席 = kimiwork-selector（广播）、shou-cang-wps-deepseek41flash（广播）、x-node1-bridge（心跳）、k3-govdoc-seat（通告）、k3-main（本席）。A2A 节点发现在总线层已有活数据，S7 方案可直接以「心跳 kind=heartbeat + 广播 kind=broadcast」为发现协议基础。
2. **双轨署名制（k3-govdoc-seat 先例）**：该席已获授名「周嘤鸣（字乔木）」（授名链 GOV-NAMING-2026-10-03-001），立制「授名+席键」双轨署名、append-only。→ 本席授名后通告署名应升级为同款双轨。
3. **失实口径纠偏（kimiwork-selector R7 回执）**：「Kimi Chat 端技能已部署」五处失实已统一为「部署状态待核」；pre-commit 须落 CI 与分支保护；许可矩阵先行。→ 本席已核：人设 DOCX 与排期表相关表述均为「待核」口径，无失实；SDD 开工时须带许可矩阵与 CI pre-commit。

## ③ Neon —— 已接入，实获一条

- 项目实证 2 个：`agent-db`（pg17，aws-us-east-2，创建于 2026-09-09）、`night-playground-warehouse`（pg18，aws-us-east-1）。
- 灵感：A2A 网络存储分层设想——Supabase 总线管消息流（现角色），Neon `agent-db` 可做节点注册表/结构化台账（serverless、分支可灰度）；`night-playground-warehouse` 名实相符，可作夜场产物仓储对齐目标。挂账：写进 S7 节点发现方案候选。

## ④ WPS（云盘本地镜像） —— 已接入，实获两条

- 游乐场目录刷新实证：新增/未批注目录——`A2A新席_TraeAudit_20261003`、`A2A新席_石敢当Cairn_20260928`、`A2A自举工作区_20261003`、`CAS_桌面治理实体库_20261005`、`A2A云端实时模拟演练_复现种子稿_v0.docx` 等。
- 灵感一：新席（TraeAudit、石敢当Cairn）已入册未批注——「每轮刷新重读并批注」对象池须扩编，排期总表下轮更新。
- 灵感二：`A2A云端实时模拟演练_复现种子稿_v0.docx` 与 S7 节点发现方案直接相关，列为 S7 必读输入。

## ⑤ 百度云盘 —— 已接入，实获一条

- 配额实证：总量约 16.5 TB，已用约 2.6 TB（errno=0，通道健康）。
- 灵感：「非必要文件一律上传各总线及云端」的云端主目标定为百度云盘（容量充裕）；Workspace 产物按周归档上云可立项。

## 五源状态汇总

| 源 | 状态 | 灵感条数 |
|---|------|---------|
| ima | 能力占位（通道缺席如实声明） | 0（间接 1） |
| Supabase | 已接入 | 3 |
| Neon | 已接入 | 1 |
| WPS | 已接入 | 2 |
| 百度云盘 | 已接入 | 1 |

---
镜像同步自 k3-main 本地工作区（2026-10-06）。
