# license-packet 逐字节核验报告（trae-audit）

**档号**：LICENSE-VERIFY-20261006-01 ｜ **核验席**：k3-main ｜ **日期**：2026-10-06
**体例**：政府职能部门党组学术技术成员视角
**核验对象**：`A:\OPL_A2A\Plasma游乐场\A2A新席_TraeAudit_20261003\license-packet\` 内 LICENSE / NOTICE
**闭环对照面**：GitHub moonhwm/openplanlink-mirror 根目录 LICENSE / NOTICE（raw 逐字节）

---

## 一、核验方法与证据

| 项 | 方法 | 证据 |
|---|---|---|
| 体量/哈希 | `wc -c` + `sha256sum` | 见下表 |
| 结构完整性 | 行数、换行格式（`file`+CR 计数）、首尾直读、关键节检索 | 见下表 |
| 镜像闭环 | raw.githubusercontent 逐字节下载对照 | 见下表 |

## 二、核验结果

| 文件 | 本地（trae-audit 包） | 镜像（GitHub 根目录） | 判定 |
|---|---|---|---|
| LICENSE | 34,523 B / 661 行 / 纯 ASCII / 零 CR / sha256 `0d96a4ff…abcb0` | 34,523 B / sha256 `0d96a4ff…abcb0`（逐字节一致） | **PASS——与 FSF  canonical AGPL-3.0（2007-11-19）文本完全相符**；§13 Remote Network Interaction 在位（540 行）；END OF TERMS AND CONDITIONS 收尾完整 |
| NOTICE | 1,701 B / 25 行 / UTF-8 / 零 CR / sha256 `08c607a7…9d1f` | 2,754 B / sha256 `a6881b75…2b34` | **DRIFT——非损坏，系版本漂移**：镜像 NOTICE 多出第 4 节「分层组合补充（2026-10-03 104 号令增补）」（AGPL-3.0/SSPL 分层组合、LICENSE.SSPL-ADDENDUM 指针、法律效力注记）；本地包内 NOTICE 为增补前版本 |

## 三、判读与处置建议

1. **LICENSE 双层一致**：本地包与镜像根目录逐字节相同，且即为 FSF canonical 文本——trae-audit 包内许可正文完整性确认，POOL-EXP-20261006-01 所标 Medium 项对 LICENSE 部分升级为 **High（本席亲验）**。
2. **NOTICE 漂移登记**：镜像侧为 104 号令后新版，trae-audit 包内旧版缺第 4 节分层组合补充。建议 trae-audit 席：以镜像 NOTICE 为准更新包内副本（其自指索引 DF-SELF-2026-1003-TRAE-LICENSE-00 主张「不改动超链接、对他席产物不产生效力」，更新属其本席件内生维护，不越权）；在更新完成前，引用该 NOTICE 时以**镜像版为有效版**。
3. **自指一致性核验**：NOTICE 所载「AGPL-3.0 因 §13 网络交互条款为服务形态最严格适用协议、SSPL 非 OSI 认可不单独采用、NC/ND 不具开源定义资格」三论断，与本席 §3 灵感台账及全局声明口径一致，且 §13 条文经逐字检索确在 LICENSE 内——**文本级自洽成立**。
4. **不构成法律意见**：本核验为技术性完整性核查，许可适用性结论以机主及法务复核为准。

## 四、如实声明

- 全部哈希与行数为一手命令输出，未凭记忆转录；
- 未改动 trae-audit 包内任何文件（他席产物，批注不越权改写）；
- 未引入凭据明文；镜像下载走公开 raw URL。
