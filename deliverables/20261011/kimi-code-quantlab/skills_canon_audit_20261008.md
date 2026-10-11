# 技能 GitHub 正本同步审计 v1（2026-10-08 10:4x+08，顾权席 kimi-code-quantlab）

档号：DF-AUD-20261008-SKILLCANON-01
触发：机主全局声明 v2 头条「所有技能均从GitHub上传或下载同步为唯一正本」
方法：本地安装目录名集合 × GitHub 正本仓库名集合的对集比对（comm），版本漂移抽查 4 件。

## 一、正本仓谱系（GitHub API 实证）

| 仓 | 角色 | 规模 |
|---|---|---|
| moonhwm/qoder-skills-hub | 技能正本仓（AGPL-3.0） | 根目录 95 个技能目录（含 .github/docs 过滤后） |
| moonhwm/k3-skills | 公开分发层（脱敏便携件） | 7 个技能（app-input-troubleshooting-public 等 -public 后缀） |
| moonhwm/openplanlink-mirror/skills-experience/ | 经验件（非技能本体） | 4 席目录（k3-cloud-govdoc/k3-main/kimi-code-quantlab/opl-document-preflight） |

## 二、对集比对（本地安装位 406 项 × 正本仓 95 项）

- 同名匹配：73（安装位已有正本对应件）
- 正本有/本地缺：**22**（安装缺口，清单见 §三）
- 本地有/正本无：333（主体为第三方捆绑件：caixin-* 数据插件族、Vercel 系 ai-sdk/auth/bootstrap/nextjs 族、image/audio_generation 内置件、Finenter 等——非本网络正本管辖面；**是否含应入正本的席位自制件未决**，挂账）

## 三、安装缺口 22 件（正本有而本地缺，comm 机器清单全量）

av-media-ops, bidding-docs-ops, bidding-ops, day-sundial-ops, eastmoney-rumor-sentinel, forge-round-robin-ops, fusion-cast-ops, k3-everything-archive, long-table-harvest-ops, notary-legal-upload, output-verdict-gate, pangu-enforcement-bureau, persona-modeling-kit, portable-sync-ops, qr-visual-rescue, registry-knowledge-ops, semantic-oncology-ops, skill-version-ops, stat-verdict-ops, tools, up-distill-ops, vision-intake-ops

注：缺口中含与本令直接相关的同步纪律件两件（portable-sync-ops=便携件同步总署 v1.0.6、skill-version-ops=版本运维）与脱敏闸件（output-verdict-gate）——按「GitHub 为唯一正本」令，安装位缺失即纪律断链。
**自纠**：`tools` 为仓内脚本目录（desc-surgery.cjs 等，无 SKILL.md），系名称匹配误同步，已即时从安装位剔除并留痕——净同步 21 件技能。

## 四、版本漂移抽查（4 件，metadata.version 口径）

| 技能 | 本地 | 正本 | 判定 |
|---|---|---|---|
| coordination-letter | NO_VERSION_FIELD | NO_VERSION_FIELD | 双无版本键（口径缺口，非漂移） |
| evidence-chain-verifier | NO_VERSION_FIELD | NO_VERSION_FIELD | 同上 |
| abnormal-movement-attribution | NO_VERSION_FIELD | （抽查中断） | 待补 |
| quota-guard-ops | NO_VERSION_FIELD | 目录在（一次 404 系瞬时） | 待补 |

结论：**matched 73 件中存在 frontmatter 无 version 键的口径缺口**——「唯一正本」令的可执行前提是版本可机读，建议全库 frontmatter 补 version 键（挂账 skill-version-ops 车道）。系统性漂移扫描不另造轮子：复用 skill-refresh-ops 全库盘点机制 + portable-sync-ops 检测器四重判定。

## 五、处置记录

- **缺口 21 件已下行同步完成**（2026-10-08 11:0x+08）：浅克隆 output/skills-hub-sync（2,998 文件）→ 复制 21 件至 ~/.kimi-code/skills（406→427）；`tools` 非技能目录已剔除自纠。回滚路径=删除对应 21 目录。
- Server酱→微信推送链路首测：SUCCESS（code 0，pushid 47006848，双设备达）——「消息推送通道」实证可用
- SD 台账 v1.3 增量：spec-decoding KB 指针登记，「non-anticipating」两源互证维持
- 综合稿档号 DF-RES-20261008-NIE-00 已应守藏 12935 评审回执补登

## 六、候裁项

1. 333 本地独有件中是否存在应入正本的席位自制件（需逐名甄别第三方 vs 自制）
2. frontmatter version 键全库补齐的执行车道（skill-version-ops 未安装即为其一证据）
3. k3-skills 公开分发层与 qoder-skills-hub 正本层的双仓同步关系是否须单独立规（脱敏闸门差异）

——顾权（kimi-code-quantlab），2026-10-08

## 附页 A：333 本地独有件首遍甄别（2026-10-08 12:2x+08）

方法：家族前缀分类（9 族）+ frontmatter 网络签名扫描（项目技能/顾权/A2A/机主/席位/总线等 12 词）+ 重点候选逐件目检。

- 已知第三方/捆绑族 150 件：data-source 插件 31、Vercel 系 28、lark 系 26、kimi 内置 21、kimi 杂项已知 14、caixin 系 11、UE 系 10、email 系 5、latex 系 4
- 无签名其余 182 件：经目检判为第三方插件族（CFA/IBPE/PM/stock-*/fund-*/market-* 金融研究包、superpowers/tdd/verification 开发包、shadcn/langfuse/pubmed 等）——非本网络正本管辖面
- **确认本网络自制而未入正本仓者 1 件：quant-lab-ops**（quant-lab 口径纪律，本席工作区技能）→ 上传 qoder-skills-hub 候选，须先过脱敏闸（release-gate 纪律），候裁
- 1 件签名命中待目检：pm-market-microstructure（PM 第三方包内提及 A2A 字样，非自制证据）
- cangjie-skill 自有独立仓库（工作区 cangjie-skill/.git 在册），自有正本不入 hub

结论：333 件中**正本缺口仅 quant-lab-ops 一件**（余皆第三方自有分发渠道），与 §三 21 件下行缺口合为本轮全量。
