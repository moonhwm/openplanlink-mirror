---
name: license-match
description: 开源协议条款匹配与声明一致性预检——识别仓库声明面（根 LICENSE / NOTICE / SBOM）与文件面（各级 LICENSE、SPDX 头），判定「一致 / 冲突 / 未声明 / 不适格」，输出一页纸报告。补 doc-triad-check 未覆盖的许可面。
kind: compliance-skill
version: 1.0.0
owner: A2A新席_石敢当Cairn
---

# license-match · 开源协议条款匹配技能

## 何时使用

- 上仓前预检（与 CI 的 `compliance_check.py`、`supply_chain.py` 形成三层）；
- 许可变更后（如 MIT → AGPL-3.0 升级）复核全仓一致性；
- 接收外部件前评估许可兼容性。

## 用法

```powershell
python license_match.py --repo <仓库路径> --out <报告.md>
```

无 `--out` 时打印标准输出。退出码恒为 0（**报告型工具**，不阻断流水线；需要门禁时读其「不适格/冲突」计数）。

## 判据口径（政策表在脚本内，可审可改）

- **允许**：AGPL-3.0、SSPL-1.0、CC-BY-SA-4.0、ODbL-1.0、MIT、Apache-2.0、BSD-3-Clause
- **不适格**：GPL-3.0（缺 AGPL §13 网络交互条款）
- **注意**：AGPL-3.0 正文内含 "GNU General Public License" 字样，脚本按指纹**顺序**先判 AGPL 再判 GPL，避免误报（本技能首跑即验证此点）

## 输出结构（四节）

1. 声明面：根 LICENSE 身份（含指纹证据）、NOTICE/SBOM 在位、SBOM 组件许可表
2. 文件面：LICENSE* 计数与识别分布、扫描源文件数、SPDX 头命中数
3. 匹配结论：不适格清单 / 声明冲突表 / 未识别清单 / 缺口
4. 处置建议：只提请不代改

## 纪律

1. **只读**：不改动任何许可文件、不写台账、不动仓库。
2. **只提请**：发现冲突只登记与建议，**不擅自改写他席文件**（与他席档案不代署同纪律）。
3. **可复算**：所有计数现场扫描所得，附指纹证据。

## 首跑实测（openplanlink-mirror，2026-10-06）

- 根 LICENSE = **AGPL-3.0**；不适格 **0**
- LICENSE* 文件 96：MIT×79、Apache-2.0×7、AGPL-3.0×2、CC-BY-SA-4.0×1、未识别×7
- 扫描源文件 1683，**SPDX 头 0**
- **声明冲突 85 处**：SBOM 声明 `skills/` = AGPL-3.0，而各技能自带 LICENSE 为 MIT/Apache-2.0
  → 已登记 `DF-LIC-20261006-CAIRN-01` 候裁定（以声明面为准则须统一，或显式登记为「历史 MIT 副本·仅存证」）
