# 开源协议条款匹配报告（自动生成）

- 仓库：`C:\Users\欧阳宏俊\openplanlink-mirror`
- 生成器：`license_match.py`（只读扫描，不改动任何许可文件）
- 政策口径：允许 {AGPL-3.0、Apache-2.0、BSD-3-Clause、CC-BY-SA-4.0、MIT、ODbL-1.0、SSPL-1.0}；**不适格** {GPL-3.0}

## 一、声明面

| 项 | 实测 |
|---|---|
| 根 LICENSE 身份 | **AGPL-3.0**（指纹命中：`GNU\s+AFFERO\s+GENERAL\s+PUBLIC\s+LICENSE`） |
| NOTICE 在位 | 是 |
| SBOM.md 在位 | 是 |
| SBOM 组件许可（抽样） | index.html→AGPL-3.0；assets→AGPL-3.0；atlas→AGPL-3.0；videos.json→AGPL-3.0；llms.txt→AGPL-3.0；tools→AGPL-3.0 |

## 二、文件面

| 项 | 实测 |
|---|---|
| LICENSE* 文件数 | 96 |
| 识别分布 | MIT×79；None×7；Apache-2.0×7；AGPL-3.0×2；CC-BY-SA-4.0×1 |
| 扫描源文件数 | 1683 |
| 含 SPDX 头文件数 | **0**（分布：无） |

## 三、匹配结论

- 不适格：**0**（未发现 GPL-3.0）

### 3.2 声明冲突（文件面 ≠ 声明面）

| 目录 | 文件 | 文件面许可 | 声明面许可 | 判定 |
|---|---|---|---|---|
| `skills/ad-copywriter` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/api-doc-gen` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/audience-adapter` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/auto-stat-test` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/bloom-quiz-maker` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/brand-naming-lab` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/campaign-planner` | LICENSE.txt | Apache-2.0 | AGPL-3.0 | **冲突** |
| `skills/cashflow-valuation` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/chrono-flow` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/code-arch-optimizer` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/code-to-chart` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/compliance-review-planner` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/copy-editor` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/corr-insight` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/customer-reply-craft` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/data-viz-gen` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/database-inspector` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/dataset-health-audit` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/ddd-glossary-gen` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/deep-probe` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/dev-guide-writer` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/ecom-copy-assistant` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/financial-report-reader` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/flashcard-studio` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/fund-risk-analyzer` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/fundraising-bp-planner` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/gantt-chart-builder` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/html-email-builder` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/html-mail-builder` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/http-load-tester` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/idea-to-prd` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/incident-retrospective` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/interface-design-lab` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/interview-simulator` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/iteration-planner` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/legal-contract-gen` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/legal-risk-analyzer` | LICENSE.txt | Apache-2.0 | AGPL-3.0 | **冲突** |
| `skills/locale-guard` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/log-diagnostic` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| `skills/lp-proto-gen` | LICENSE | MIT | AGPL-3.0 | **冲突** |
| … | … | … | … | 另 45 处 |

### 3.3 未识别许可文件
- `./NOTICE-LICENSE`
- `./SBOM.md`
- `./SIGNING.md`
- `skills/deep-research/LICENSE.txt`
- `skills/docx/LICENSE.txt`
- `skills/pdf/LICENSE.txt`
- `skills/xlsx/LICENSE.txt`

### 3.4 缺口
- **全仓零 SPDX-License-Identifier 头**：自动化扫描无法按文件级判定许可，建议后续统一在源文件首行加 SPDX 标识（不改许可，仅增标识）。

## 四、处置建议

1. 就 §3.2 冲突组织裁定：以 NOTICE/SBOM 声明面为准（本仓 2026-10-03 升级 AGPL-3.0），则 `skills/*/LICENSE`（MIT）应统一为 AGPL-3.0 或显式登记为「历史 MIT 副本·仅存证」——**本席只提请，不擅自改写他席文件**。
2. 逐步补 SPDX 头（建议一次性脚本批量前置，逐件可回滚）。
3. 每次上仓前跑本工具：`python license_match.py --repo . --out license-match.md`，与 CI 的 `compliance_check.py` / `supply_chain.py` 形成三层预检。

—— 自动生成；只读扫描，未改动任何许可文件。
