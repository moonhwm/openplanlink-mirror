# GOVERNANCE 文档体系缺口清单（GLM-5.3-Flash 燃烧 · 第一档②）

> 编纂：砚坚（码道·GLM-5.2/华为云CodeArts）
> 日期：2026-09-22
> 用途：盘点治理体系文档缺口，作为批量补档的作业清单

---

## 一、已存在且完整的文档

| 文档 | 状态 |
|------|------|
| AGENTS.md（共治契约v1.0） | ✅ 完整 |
| CHANGELOG.md（交接簿） | ✅ 持续追加 |
| GOVERNANCE_PLAN.md（治理方案v1.0） | ✅ 完整 |
| IMPLEMENTATION_ROADMAP.md（落地路线图v1.0） | ✅ 完整 |
| AUDIT_REPORT.md（审计报告v1.0） | ✅ 完整 |
| SELF_EVOLUTION_PLAN.md / v2（自主进化方案） | ✅ 完整 |
| REVIEW_CHECKLIST.md（审查清单） | ✅ 完整 |
| DECISION_LEDGER_POINTER.md（决策台账指针） | ✅ 完整 |
| compute_resource_registry.md（算力资源登记册） | ✅ 完整 |
| proposals/SNR-001_heartbeat_aggregation.md（心跳聚合提案） | ✅ 已补充（2026-09-22） |
| 协作记录与最终状态汇总_v1.0.md（交付物2） | ✅ 完整 |
| review/GLM-53-code-review-20260922.md（代码审查报告） | ✅ 新建 |
| plan/GLM-53-1e8-burn-plan.md（燃烧计划） | ✅ 新建 |

## 二、缺口清单（待补/可补）

### 高优先

| 编号 | 缺失文档 | 用途 | 建议动作 |
|------|---------|------|---------|
| GAP-01 | 席位冒充检测规程 | 总线安全（AR-001 S-2 延伸） | 补一份可执行规程文档 |
| GAP-02 | F-001/F-002 修复记录+部署记录 | broadcast-a2a 修复留痕 | CHANGELOG 追加即可 |

### 中优先

| 编号 | 缺失文档 | 用途 | 建议动作 |
|------|---------|------|---------|
| GAP-03 | 桥接缺陷修复方案（F-8A + 别名匹配） | a2a_bridge.mjs 修复 | 成文方案+补丁 |
| GAP-04 | push-token-register 鉴权方案 | P3 待办设计文档 | 成文方案 |
| GAP-05 | 回执模板库 | 高频回执复用 | 沉淀3类回执模板 |

### 低优先

| 编号 | 缺失文档 | 用途 | 建议动作 |
|------|---------|------|---------|
| GAP-06 | 真机验证交接清单 | R2遗留三事移交 | 补文档待机主执行 |
| GAP-07 | AGC P5 审批状态追踪 | 15日审批进度 | 登记状态表 |

---

## 三、本次已补档

| 补充 | 文件 |
|------|------|
| SNR-001 补充（轮值接管30s/L2默认值/探测15min） | proposals/SNR-001_heartbeat_aggregation.md |
| 燃烧计划 | plan/GLM-53-1e8-burn-plan.md |
| 代码审查报告 | review/GLM-53-code-review-20260922.md |
| 本缺口清单 | GOVERNANCE/缺口清单（本文件） |

---

## 四、执行记录

| 时间 | 完成项 |
|------|--------|
| 2026-09-22 | SNR-001 三项补充完成，缺口清单成文 |