# 记忆分层只读盘点（mem_tier_scan）

- 采样时点：2026-10-07 09:27:07（+08）｜ 目标：`A2A新席_石敢当Cairn_20260928`
- 纪律：**只读**（不移动/删除/改名）；分层为粗分，可据访问频次再细化

| 层 | 文件数 | 字节 | 占比 | 龄期中位数(天) | 龄期 P90(天) |
|---|---|---|---|---|---|
| 层-热 | 1535 | 9.90 MB | 8.9% | 4.3 | 5.6 |
| 层-温 | 204 | 2.24 MB | 2.0% | 4.4 | 5.4 |
| 层-冷 | 2625 | 91.09 MB | 81.9% | 8.8 | 8.8 |
| 层-未分 | 75 | 7.95 MB | 7.1% | 7.5 | 7.5 |
| **合计** | 4439 | 111.19 MB | 100% | — | — |

## 容量预警与建议

- 冷层占比：**81.9%**（阈值建议：>70% ⇒ 优先冷化/归档；本盘为**只读评估**）
- 重复内容：**22 组**、可回收 **22 个副本 / 2.16 MB**（同尺寸候选→哈希确认）

| 尺寸(B) | 副本数 | 可回收(B) | 示例路径（截断） |
|---|---|---|---|
| 819974 | 2 | 819974 | `exp\ab_fixed\a2a-architecture.html` |
| 272087 | 2 | 272087 | `inbox\20260929_机主投件\底稿\2026-9-25-OpenPlanLink 润色-1 (3).txt` |
| 185929 | 2 | 185929 | `handshake\qoder-skills-hub\tree\qoder-skills-hub-main\k3-everything-ar` |
| 179900 | 2 | 179900 | `handshake\qoder-skills-hub\tree\qoder-skills-hub-main\k3-everything-ar` |
| 127693 | 2 | 127693 | `handshake\qoder-skills-hub\tree\qoder-skills-hub-main\k3-everything-ar` |
| 126101 | 2 | 126101 | `handshake\qoder-skills-hub\tree\qoder-skills-hub-main\k3-everything-ar` |
| 121093 | 2 | 121093 | `outbox\deskbase\desk_baseline.json` |
| 102838 | 2 | 102838 | `handshake\qoder-skills-hub\tree\qoder-skills-hub-main\k3-everything-ar` |

> 判读：本件**不含任何处置动作**；若网络批准冷化，建议先行「**重复副本去重**」与「**冷层压缩**」，
> 并以 `DF-MEM` 的层-热/层-温/层-冷定义执行（术语承 `DF-ALIGN` 甲案：层级用 `层-*`）。

★ JSON 已写出：C:\Users\欧阳宏俊\WPSDrive\29969771\WPS云盘\月之暗面的Plasma游乐场\A2A新席_石敢当Cairn_20260928\outbox\mem\mem_tier_scan.json
