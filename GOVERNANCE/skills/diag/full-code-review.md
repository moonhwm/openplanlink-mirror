---
name: full-code-review
type: diag
created: 2026-09-22
updated: 2026-09-22
version: 1.0.0
trigger: 对鸿蒙端侧或云函数做全量代码审查、合规走查、契约一致性检查
source_files: [entry/src/main/ets/, cloudfunctions/functions/, GOVERNANCE/review/GLM-53-code-review-20260922.md]
---

# 鸿蒙全量代码审查技能

## 概述
对 HarmonyOS 端侧（ArkTS）与 CloudBase 云函数（Node.js）做批量、可复现的全量审查。以工程硬约束（适老化/信号松绑/占位封装/首屏兜底/串行纪律）为准绳，输出分级发现清单与修复建议。

## 适用场景
- 新增功能合并前的全量合规走查
- 云函数/端侧契约不一致排查
- 对抗性审查（AR类）的代码侧输入
- 批量燃烧模型额度的高价值任务载体

## 执行步骤
1. glob 列出端侧 `.ets` 与云函数 `**/index.js` 全部文件，登记行数
2. 逐文件通读，对照工程硬约束逐项核验（适老化无K线、信号三禁、PushService占位、DEMO兜底、冷启动/后台拉起）
3. 云函数重点核：表名/存储路径/API端点是否与实测一致、鉴权、并发写保护、错误降级
4. 发现按 高/中/低 分级归入表格，标注 文件:行号
5. 输出审查报告到 `GOVERNANCE/review/`，含修复优先级（P1/P2/P3）
6. 高优先发现立即修复并记录

## 质量门槛
- 端侧+云函数 100% 文件覆盖（无遗漏）
- 每项发现带 文件:行号 证据
- 硬约束条目逐条核验并显式标注 通过/发现
- 修复后重新走查受影响函数

## 经验记录
- Supabase 表名必须实测确认：代码里写 `a2a_messages`，实际表是 `cross_mode_channel`，一次误写导致广播静默失败 404
- `downloadFile` 的 `fileID` 与 `cloudPath` 两种参数在不同 SDK 版本行为可能不一致，应统一
- ArkTS 端侧硬约束核验可用 "无 K线/图表组件 + 字号范围 + 状态机完整性" 三查法快速通过
- 注释错别字类低级问题单独清点，修复成本近乎为零

## 关联文档
- AGENTS.md（工程硬约束）
- GOVERNANCE/AUDIT_REPORT.md（对抗性审查基线）
- GOVERNANCE/review/GLM-53-code-review-20260922.md（本次审查报告）