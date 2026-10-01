# FORGE_REPORT —— webpage-forge-ops（网页注造室）

- 锻造日期：2026-09-29 ｜ 管线：skill-forge-pipeline v2.4.1（纯提示词/工作流型：无 scripts，自检=dry-run 用例集）
- 组阁闸：3 异质族 × 3 路由过闸——qwen3.8-flash@阿里百炼 / glm-4.5-flash@z.ai / minimax-m3@TokenHub 广州
- 基线快照：v1.0.0 → .bak-r1（锻造现场 /tmp/forge2/webpage-forge-ops.bak-r1）

## 票数纪事

| 轮 | 对象 | qwen | glm | minimax | 多数 |
|---|---|---|---|---|---|
| R1 首评 | v1.0.0 | REVISE（两跑同票） | KEEP | REVISE | REVISE 2/3 |
| R2 复评（嵌 R1 摘要） | v1.1.0 | REVISE | REVISE | REVISE | REVISE 3/3 |
| R3 复评（嵌 R2 摘要） | v1.2.0 | REVISE | REVISE | REVISE | REVISE 3/3 |

R3 触顶：三轮 keep 链完整（无 FAIL/worse），收敛判据不满足 → 强制出链，标 MAX_ROUNDS_REACHED，残余修复后移交机主裁量。

## 判官抓包与修复

- R1（7 项 → v1.1.0）：反模式 BrowserRouter 措辞越权改通用；新增 references/experience-card-template.md 九字段经验卡模板；production-paths 厂商名补全称实证限定；rumor-chain-verifier 切分口径；触发③工程披露阈值；URL 处置闭环；反 slop 本地最小检查清单。
- R2（7 项 → v1.2.0）：React 边界收口（脚手架归 webapp-building，本件只管交付纪律）；数字钻取锚；可钻取=页内来源铭文定义；证据不足中断分支+四路径拆解规程；自检三问机检钩子；output/app 前置 IO 兜底；dryrun 复核记录回填。
- R3（7 项 → v1.2.1，触顶残余修复）：自检钩子按产物形态分支；来源铭文一一对应；static 口径（build 后传项目根）；数字「随件不可独立复核」如实标注；账单锚真实性定断归 rumor-chain-verifier；术语统一创作者账号级；触发④阈值+灵感参考登记条形态。

## 残余与已知边界（移交机主）

1. 判官 d8（实测表现）各轮 4–10 分摆动：纯工作流型技能无 scripts，实测证据=dryrun 复核记录+判官干跑，强度低于确定性套件——属技能形态固有边界。
2. website_version_manager / musepool 为外部生态依赖，缺席处置已写入失败模式与本地清单，但其内部行为不可由本件保证。
3. production-paths 的数字为会话研究产物快照摘录，随件不可独立复核（已如实标注）；精确复核须回原仓库台账。
4. R3 三席仍判 REVISE（残余多为文档级措辞与可机检性提升），机主可裁量：交付使用 / 再开新一轮锻造。

## 验证凭证

dry-run 用例集三用例预期行为与工作流一致（references/dryrun-suite.md 复核记录四行台账）；改必验闸 verify_edit 逐处通过。
