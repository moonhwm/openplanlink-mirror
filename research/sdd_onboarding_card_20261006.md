# SDD/工程化入门五题资料卡 · 2026-10-06

档号：RESEARCH-KIMI-2026-1006-01 · 幻16Kimi席调研产出
conf 声明：各条注明来源与置信度；厂商宣称数字均标注 conf=unverified。

## 1. Claude Code 云端使用（docs.anthropic.com / claude.ai/code）

- cloud session 跑在 Anthropic 云 VM（`claude --cloud` 或 claude.ai/code 入口），可克隆 GitHub 分支在云端执行，多会话并行；支持 Routines（定时云端任务）。
- 计费纳入 Pro/Max/Team 订阅；本地 plan → 云端执行的分离模式适合长任务不占本机。
- **A2A 启示**：跨席位长任务可交云端会话执行，幻16本机只做调度与验收，呼应算力分配议题。

## 2. SDD 规范驱动开发（Spec-Driven Development）

- 核心循环：spec → plan → tasks → implement，四阶段各设人工检查点；规格是唯一事实源，代码是规格的产物。
- 与 TDD 互补不替代：TDD 给函数级反馈，SDD 给系统级契约；最小 SDD 包 = spec/tasks/evidence 三文件。
- 厂商报告「3–10× 通过率提升」为供应商数据，conf=unverified。
- **A2A 启示**：本管线（漂移监测/基线/diff 定稿）已是 SDD 实证实例；节点间协议应先 spec 后码，消解跨席位语义漂移。

## 3. Hugging Face Spaces

- 免费档：2 vCPU / 16GB，闲置约 48h 休眠（社区口径，conf=unverified）；2025 后新建 Gradio/Docker Space 需付费计划，免费账号限 2 个 Gradio Space。
- **A2A 启示**：只能做对外展示面板（如 A2A 网络虚拟空间预览），不能做常驻总线；常驻服务应走华为云 X 实例。

## 4. CI/CD 原理（IBM 资料口径）

- CI=频繁合入+自动构建测试；CD 分「持续交付（人工批准闸门）」与「持续部署（全自动）」两义。
- 流水线六段：源代码→构建→测试→暂存→部署→监控。
- GitHub Actions：公共仓免费无限制；私仓 2,000 Linux 分钟/月，超额约 $0.006/min（2026-01 调价后口径）。
- **A2A 启示**：openplanlink-mirror 为公共仓，SDD evidence 推送零成本；若转私仓，超额分钟可分流到 X 实例自建 runner。

## 5. MVP 最小可行产品（Eric Ries 口径）

- 定义：最少努力获得最多「经证实的学习」；Build-Measure-Learn 循环；优先验证最高风险假设。
- **A2A 启示**：OpenPlanLink MVP 收敛为四件套——N 个席位 + 一条总线（GitHub 仓）+ 一种交接契约（HANDSHAKE 格式）+ 一个可验证的跨席位任务（本轮漂移监测定稿即实证之一）。

---
敏感面自检：不含凭据与网络标识真值。来源 URL 见调研过程记录（WebSearch 当轮返回）。
