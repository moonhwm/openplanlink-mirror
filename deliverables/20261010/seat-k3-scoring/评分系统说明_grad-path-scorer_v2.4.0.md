# 评分系统说明 · grad-path-scorer v2.4.0（主仓对齐件）

> 席位：K3·评分系统席（k3-scoring-web）｜ 日期：2026-10-10 ｜ 件号：K3SCORING-NOTE-2026-1010-01
> 许可：CC BY-SA 4.0（deliverables 文档层，仓根 NOTICE 在案）

## 一、版本链
- v68.69 起：本地主线内部代际（panel v4 / Lane D v4 工艺）；公开仓 sleepless-flower-under-sealevel 停在 v68.78（2026-10-10 实勘），本地主线超前；回写公开仓属候批项，未自主。
- skill v2.3.7：技能包元数据旧版（滞登，metadata 未随采用决议滚动）。
- **skill v2.4.0（现行）**：2026-09-09 用户令「加进去」正式采用；2026-10-10 元数据对齐收口（frontmatter version 2.3.7→2.4.0）。本文件即对齐登记件。

## 二、数据基线
- 数据截止：2026-09-09；面板 10,893 行 / 64 单位；基准池 43 校 dense_pool。

## 三、v2.4.0 参数集（DEFAULT_CONFIG 权重）
| 维度 | 权重 | 变动 |
|---|---|---|
| phd | 0.2035 | 平 |
| city | 0.1332 | ↑ |
| funding | 0.0502 | ↓ |
| platform | 0.3995 | 平 |
| admission_risk | 0.2136 | 平（历史记录曾显 0.2137，截断差） |

- max_penalty：22 → 18
- dead_end_discount：0.4 → 0.5

## 四、验证状态
- 秩相关 ρ = 0.9236；smoke/stress 7/7 绿；43 校 dense_pool PASS（TOP2 零翻转）。

## 五、风险登记（如实）
- ⚠ mp×disc 平台期警告（v2.3.6 起在案）仍有效：v2.4.0 采用 = 用户行使对保守纪律的 override；用户保留一票恢复权（one-vote restore），触发即回滚至采用前参数。
- 证据：技能包 workspace/v240_adoption/{score43_v240.json, sens43_v240.json}（本地留档，未入仓）。

## 六、与主仓结构对接
- 技能包本体留本地（SKILL.md + scripts/ + references/ + assets/ + workspace/），不入本仓；本仓仅登记本说明与哈希锚。
- 评分可视化层（园刊第叁版）：本目录 parts/ 342 分片 + PARTS 指针 + README；git-blob sha1 `c367879da5755b6f51afd5304f2ec465e649f470`，sha256 `1670cce4…2516588`（140,511 B），还原与核验口径见 README.md。

—— K3·评分系统席（k3-scoring-web）· 对齐件 ——