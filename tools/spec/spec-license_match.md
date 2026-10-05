# spec-license_match

## 目的
开源协议条款匹配与声明一致性预检：比对仓库「声明面」（根 LICENSE／NOTICE／SBOM）与「文件面」（各级 LICENSE*／SPDX 头），判定一致、冲突、未识别、不适格。

## 输入/输出
- 输入：`--repo`、可选 `--out`（Markdown 报告）、`--json`（机器可读摘要）、`--fail-on-deny`
- 输出：四节报告（声明面／文件面／匹配结论／处置建议）＋ 摘要计数
- 退出码：默认 0（报告型）；`--fail-on-deny` 且存在不适格许可时 3

## 不变量
- **只读**：不改动任何许可文件、不写仓库、不写台账
- 指纹判定**顺序敏感**：先 AGPL 后 GPL（AGPL 正文含 "GNU General Public License" 字样，避免误报）
- 政策表：允许 {AGPL-3.0, SSPL-1.0, CC-BY-SA-4.0, ODbL-1.0, MIT, Apache-2.0, BSD-3-Clause}；**不适格 {GPL-3.0}**
- 发现声明冲突只登记与建议，**不擅自改写他席文件**

## 失败模式
- 仓库路径不存在 → 退出码 2
- 许可文本无法识别 → 计入「未识别」清单，不猜测
- SBOM 表格格式变异 → 容错解析，解析不到的组件不入声明面

## 关键函数
- identify
- declared_from_sbom
- main

## 验收断言
- 根 LICENSE 为 AGPL-3.0 的仓库不得被识别为 GPL-3.0
- `conflict_count` 等于「声明面有、文件面不同」的件数
- 无不适格时 `--fail-on-deny` 退出码为 0
