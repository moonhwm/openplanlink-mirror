# Codex 席主张独立核验报告

- 档号：`DF-VERIFY-2026-1005-BURN-01`
- 核验席：burn（独立核验席，不修改任何被核验文件）
- 核验时点：2026-10-05（北京时间）
- 被核验对象：《OpenPlanLink_A2A核查与逐件批注_20261005.md》（档号 `DF-REVIEW-2026-1005-CODEX-01`，v0.1.0，16,982 字节）
- 核验结论摘要：**5 项核验中 3 项成立、1 项部分成立、1 项主理人前提需纠正**；另发现 4 项此前未被发现的实证缺陷。

---

## 〇、核验方法与证据来源

### 0.1 方法

本席采取「只读独立核验」：不复用 Codex 席任何自述作为结论，仅将其自述作为**待验证命题**，然后用文件系统、Git、哈希、Python AST、正则与公开权威原文直接对撞。所有结论均给出可复现命令或可核对的文件字节偏移。

### 0.2 证据来源清单

| 类别 | 具体证据 |
|---|---|
| 被核验报告 | `A:\OPL_A2A\codex-review\20261005-120443-997956-source-review\OpenPlanLink_A2A核查与逐件批注_20261005.md`（16,982 B）；桌面副本 `C:\Users\欧阳宏俊\OneDrive\桌面\` 同名件（SHA-256 与 A 盘件**完全一致**：`7c3f8a1b5edf06b6…`，见 §5.4） |
| SDD 基座 | `A:\OPL_A2A\selfevo-sdd\`（Git 仓库，3 次提交，最新 `026854b6`）；`specs/`、`src/selfevo/`、`tests/unit/`、`.specify/memory/constitution.md`（6,364 B） |
| Codex 侧运行目录 | `A:\OPL_A2A\codex-review\` 下 **5 个**运行目录：`20261005-115159-789968` / `-120443-997956` / `-122623-984067` / `-132146-644377` / `-135227-166611` |
| Codex 自证件 | `a2a_notification.json`、`endpoint_probe.json`、`verification.json`、`manifest.json`、`response_nonces.sqlite3`、`skill_install_and_execution.json`、`逐件批注.json`、`核查事实索引.json` |
| 源件与抽取件 | `openplanlink-docx\_extract_tmp.txt`（35,799 B，136 个非空段落，与报告「136 个非空段落」自述**吻合**） |
| 外部权威 | OSI 官方博客（2021-01-19）、Git 官方 `githooks` 文档、GNU AGPL-3.0 官方全文、MongoDB SSPL FAQ |

### 0.3 执行纪律遵守

本席全程遵守：单命令单 Bash 调用（无 `&&`/`;` 串联）、不执行临时 `.py` 脚本（仅 `python -c` 内联单行）、不删文件、写文件仅用 Write 工具并在写后回读、凭据只登记「位置 + 类型 + 掩码前 4 字符」。

---

## 一、核验 1：规格编号冲突

### 1.1 结论

> **主理人前提需纠正**：`001-source-refresh` **既非笔误、也非 `002-ooxml-meta-traceability` 的旧名或别名，而是一套真实存在但落在错误位置的独立规格**。同时，**`002-ooxml-meta-traceability` 并非 Codex 席产出**，而是 hy4 席产出。因此「编号冲突」的本质不是「同一件东西两个名字」，而是 **Codex 席在运行证据目录内自建了一整套与 SDD 基座平行、编号同名但内容无关的 `001`~`005` 规格序列**。

### 1.2 实证

**(a) `selfevo-sdd/specs/` 下确无 `001-source-refresh`**

```
$ ls -la A:/OPL_A2A/selfevo-sdd/specs/
drwxr-xr-x  001-self-evolving-a2a      (Oct 5 12:59)
drwxr-xr-x  002-ooxml-meta-traceability (Oct 5 15:13)
```

**(b) 但 `001-source-refresh` 确实存在于 Codex 运行目录内**——共 1 份，含 4 个文件：

```
codex-review/20261005-120443-997956-source-review/implementation/specs/001-source-refresh/
├── spec.md            (1,236 B)
├── plan.md
├── tasks.md
└── verification.md
```

其 `spec.md` 首行标题为「**SDD 规格：源件刷新与可核验批注**」，正文第 6 条为「本功能落实用户要求的每轮刷新、重读与批注……」，末段引用「沿用既有 SDD 目录的规格、计划、任务及验证记录口径」。**主题为「源件刷新」，与 OOXML 元数据溯源门禁无关**——故它**不是** `002-ooxml-meta-traceability` 的前身或别名。

**(c) 该规格编号未与基座发生「删除/改名」，而是「从未写入基座」**

`selfevo-sdd` 的 Git 历史仅 3 次提交（`d65d176` / `53c0947` / `026854b`），`git status --porcelain` 显示 `?? specs/002-ooxml-meta-traceability/`（未跟踪新增），而 `specs/001-source-refresh` **在提交记录与工作区中均无任何痕迹**。故不存在「曾存在又被改名/删除」的历史。

**(d) 真正的编号冲突：两套平行编号序列**

| 序列 | 载体 | 001 | 002 | 003 | 004 | 005 |
|---|---|---|---|---|---|---|
| SDD 基座 | `A:\OPL_A2A\selfevo-sdd\specs\` | `001-self-evolving-a2a`（黏菌检索，SPEC-20261005-SELFVO-01，62 任务） | `002-ooxml-meta-traceability`（OOXML 溯源，SPEC-20261005-SELFVO-02，9 任务） | — | — | — |
| Codex 侧 | `codex-review\<run>\implementation\specs\` | `001-source-refresh`（源件刷新） | `002-alignment-cycle`（持续对齐与额度停止点） | `003-audit-ledger`（追加式审计台账） | `004-idempotent-consumer` | `005-deadletter-retry` |

两套序列在 `002` 处**编号相同、主题完全不同**。这是真实的编号空间冲突。

**(e) 002 号规格档号核验（不冲突）**

| 件 | 档号 | 状态 |
|---|---|---|
| `specs/002-.../spec.md:3` | `SPEC-20261005-SELFVO-02` | 与 001 的 `SPEC-20261005-SELFVO-01` **构成正确递增序列，无冲突** |
| `specs/002-.../plan.md:3` | `PLAN-20261005-SELFVO-02` | 同上 |
| `specs/002-.../tasks.md:3` | `TASKS-20261005-SELFVO-02` | 同上 |
| `constitution.md:3` | `CONST-20261005-SELFVO-01` | 宪法档号独立，无冲突 |

**结论：002 档号体系完备、无冲突。** 冲突只发生在「目录编号」层（两套 `001`~`005` 并行），不在档号层。

**(f) 关键纠正：002 的作者不是 Codex 席**

- `spec.md:4` 自称「本切片由**本席**推进 Specify → Plan → Tasks → Implement → Converge 全阶段」；
- `spec.md:53` 明确区分「**Codex 席**与**本席**各自产出一份 10 件勘查快照」——即 002 的作者把 Codex 席视为**对账的另一方**；
- `git log` 三次提交作者均为 `workbuddy-hy4`；
- 002 的证据件落在 `evidence/20261005-1540-hy4-increment/DF-INCR-2026-1005-HY4-01_自进化源件刷新与A2A通告_本轮增量.md`。

**故：`002-ooxml-meta-traceability` 由 hy4 席产出，Codex 席只是其对账方。** 主理人前提中的「002 由 Codex 席产出」有误。

---

## 二、核验 2：工具位置与可复用性

### 2.1 结论

> **成立，且比主理人判断的更严重**：工具**完全不在** SDD 基座内，全盘仅 2 份副本，**均位于 Codex 每次运行的证据目录内**，且 `A:\OPL_A2A\codex-review\` 与 `A:\OPL_A2A\` **均无 `.git`**——即该工具**既不在版本控制中、也不在任何可复用位置**。Copies 是「每次运行复制一份」的副产物，不是「一份工具多处引用」。

### 2.2 实证

**(a) 全盘定位（深度 6）**

```
$ find A:/OPL_A2A -maxdepth 6 -name "review_sources.py" -type f
A:/OPL_A2A/codex-review/20261005-120443-997956-source-review/implementation/tools/review_sources.py
A:/OPL_A2A/codex-review/20261005-122623-984067-source-review/implementation/tools/review_sources.py
```

同一命令在 `C:/Users/欧阳宏俊/.zcode/workspace/default`（深度 6）下**零命中**——即工具**未**写入 C 盘真身工作区。`ls -d A:/OPL_A2A/selfevo-sdd/tools` → `No such file or directory`。

**(b) 两处副本字节数与 SHA-256 完全一致**

| 副本 | 字节数 | SHA-256 |
|---|---|---|
| `…-120443-997956…/implementation/tools/review_sources.py` | 9,600 | `caf4456d71707424e7a15c2ba0ad70f31b250cef26f1250fd60da5a9cb094d2f` |
| `…-122623-984067…/implementation/tools/review_sources.py` | 9,600 | `caf4456d71707424e7a15c2ba0ad70f31b250cef26f1250fd60da5a9cb094d2f` |

**两副本逐字节相同**（哈希一致）。故 Codex 席不存在「两个版本工具并存」的技术风险。

**(c) 语法可解析（非死文件）**

```
$ python -c "import ast;ast.parse(open(r'…review_sources.py',encoding='utf-8').read());print('SYNTAX_OK')"
SYNTAX_OK
```

（同批产出的 `notify_a2a.py` 在 `-122623` 目录中另有演化版 5,003 B → 6,433 B，`check_quota.py`、`export_wps_sources.py` 为 `-122623` 轮新增——说明工具确有迭代，但**未沉淀到基座**。）

**(d) 版本控制状态**

```
$ ls -d A:/OPL_A2A/codex-review/.git   → No such file or directory
$ ls -d A:/OPL_A2A/.git                → No such file or directory
```

**整个 `codex-review/` 树不在任何 Git 仓库内。** 对比 SDD 基座有完整 3 次提交历史与 `pre-commit`/`pre-push` 双钩子门禁。

### 2.3 对「工具可复用性」的影响（四项实证缺陷）

| # | 缺陷 | 实证 |
|---|---|---|
| R-1 | **工具无版本控制**：无 Git、无 SHA 登记簿（与 SDD 基座的 HMAC-SHA3-512 台账纪律不一致）。工具被篡改无法追溯 | `ls -d …/.git` 双双失败 |
| R-2 | **路径硬编码到单机**：第 18 行 `SOURCE_ROOT = Path(r"C:\Users\欧阳宏俊\WPSDrive\…\Plasma游乐场")`，第 19-30 行硬编码 10 个具体文件名。宪法附加约束要求「跨席协作统一走 A 盘地址」，工具却走 C 盘真身 | `review_sources.py:18-30` |
| R-3 | **副本随运行增殖**：5 个运行目录中只有 2 个含 `tools/`，同一文件被复制而非引用。后续运行（`-132146`、`-135227`）的工具目录已消失，**无法从最新运行追溯工具版本** | `find` 只命中 2 处；`-132146/-135227` 无 `implementation/tools/` |
| R-4 | **与基座门禁脱钩**：宪法第一条（凭据零字面量）与门禁 2（双钩子）的扫描器 `src/selfevo/secretscan/scan.py` 只在 `selfevo-sdd` 生效，对 `codex-review/` 内文件**无覆盖**。R-1 缺失叠加此条，等于 Codex 工具完全在宪法门禁视野之外 | `.git/hooks/pre-commit` 仅存在于 `selfevo-sdd/.git/hooks/` |

**综合评价**：工具的**功能**是真实且可用的（标准库实现、10 件实测、两轮比对、凭据遮蔽降级测试），但其**工程安置**违反宪法附加约束「映射纪律」与「跨席协作统一走 A 盘地址」，亦违反 SDD 基座「工具应在仓内、可被门禁扫描」的基本要求。可复用性评级：**低（一次性证据脚本级，非基座资产级）**。

---

## 三、核验 3：002 号规格内容质量评估

### 3.1 总体判断

> **内容质量在「判据严谨性」维度上是本轮两份规格中较高的一份，缺陷集中在「流程合规」与「文档自洽」两处**。宪法 7 条核心原则**无违反项**，但 SDD 工作流门禁（`/speckit.analyze`）缺失、plan.md 缺 3 个模板章节、spec.md 与自身 FR 及实测结果存在 3 处自相矛盾。

### 3.2 完备性检查

| 项 | 结论 | 实证 |
|---|---|---|
| 档号 | ✅ 完备 | spec/plan/tasks 三件均带档号（`-02`），格式与 001 同构 |
| 目标 | ✅ 清晰 | `spec.md:11-19` 列出 3 类实测缺陷（时序自相矛盾 / 时区标记造假 / 比对器静默回落），均带具体实证值（17 小时、8.0 小时、10/10 假 DRIFT vs 0 漂移） |
| 用户场景 | ✅ 完备 | US-1/US-2/US-3，覆盖出档门禁、跨席对账、审计复现三种角色 |
| 成功标准可验证性 | ✅ **强** | AC-1~AC-10 全部给出**可判定**判据，含具体级别（BLOCK/WARN/info）、具名错误码、期望值。AC-4 更设**负对照**（负对照为一等公民），AC-7 区分「字节域/时间域」——判据设计水平高于 001 |
| FR 编号体系 | ✅ 完备 | FR-1.1~FR-1.4 / FR-2.1~FR-2.3 / FR-3.1~FR-3.4 / FR-4.1~FR-4.5 / FR-5.1~FR-5.3，**19 条子项，无断号** |
| AC→FR→测试三向映射 | ✅ 完备 | `spec.md:95-108` 验收映射表，10 行全覆盖 |
| 判据冻结机制 | ✅ 强 | `GATE_VERSION="1.0.0"` 冻结注释（`ooxml_meta.py:19-21`，**已实测第 19/20/21 行内容与 tasks.md T009 登记一致**）；R2 将 2 项新发现登记为 `1.1.0` 候选而**不就地扩权** |

### 3.3 tasks.md 任务粒度与依赖统计

| 指标 | 数值 | 实证 |
|---|---|---|
| 任务总数 | **9**（T001~T009），**全部标记 `[x]` 已完成** | `grep -cE "^\- \[[ x]\] \*\*T[0-9]{3}\*\*"` → `9` |
| 显式依赖标注 | **9 / 9（100%）** | `grep -cE "依赖\*\*："` → `9` |
| 标注阻塞的任务 | **0 个** | 无任何 `阻塞` 标记；`spec.md:110` 明示「开放问题（不阻塞本切片）」 |
| 标注 `[P]` 可并行的任务 | **0 个** | 但 T004 依赖栏写「无（与 T001~T003 可并行）」——**标注不一致：正文声明可并行却未打 `[P]`**（轻微缺陷） |
| 每任务绑定 FR + AC + 测试名 | **9 / 9 全部绑定** | 例如 T002 绑定 FR-2.1~2.3 + AC-1/2/9/10 + 5 个具名测试函数 |
| 对照 001 | 62 任务 / 29,699 B | 002 规模小一个数量级，与「单模块切片」定位相符 |

**粒度评估**：
- T001~T005（实现）粒度**合适**，每个任务产出一个可独立测试的入口（`extract` / 判据集 / `gate` / `compare_snapshots` / `run`），且绑定具名测试函数；
- **T006 粒度偏粗**：把「新增单测全绿 + 4 个既有单测 + 1 个 contract 测试无回归」打包为单一任务；
- **T007 粒度偏粗**：把「10 件真实语料跑门禁 + 与勘查结论逐条比对 + 产出两份产物」打包为单一任务，其中还包含一次**验收订正**（原预写「2 件 docx = BLOCK」订正为「1 BLOCK + 1 WARN」）——验收基线变更与执行混在同一任务里，削弱了「任务完成 = 验收通过」的确定性。

### 3.4 与 001 号规格的边界

> **结论：无耦合冲突，边界清晰。**

| 检验项 | 结果 | 实证 |
|---|---|---|
| 001 是否涉及 OOXML / 溯源 / 门禁 | **零命中** | `grep -niE "ooxml\|docx\|溯源\|门禁" specs/001-.../spec.md` → 无输出 |
| 002 是否涉及黏菌 / 自进化检索 | **零命中** | `grep -nE "001\|黏菌\|self-evolving"` 于 002 三件 → 仅命中宪法依据 `SELFVO-01` 与分支名，无技术耦合 |
| 文件级重叠 | **无** | 001 相关产物：`hashing.py` / `ledger.py` / `idempotency.py` / `deadletter.py` / `policy.py` / `busadapter.py` / `envelope.py` / `creds.py` / `identity_sha3.py`；002 产物：`ooxml_meta.py`（22,197 B）——文件集完全不交集 |
| 交叉引用 | **无** | 002 三件不引用 001 的 FR/T 编号；001 亦不引用 002 |

**唯一的边界越界**：002 的 R4 修改了 `src/selfevo/secretscan/scan.py`（属 T010「SDD 自进化骨架 + SC-6 密钥扫描门禁」切片①的产物）。虽已在 R4 显式登记（「由 T008 触发」「跨切片」），但仍是**跨切片改动**，且改动落在被别的切片声明所有的文件上。已声明 ≠ 无风险，建议补交叉引用。

### 3.5 plan.md 是否偏薄

> **结论：偏薄，且薄在有明确模板依据的三处缺口。**

字节数对比：**plan.md 4,099 B vs spec.md 11,544 B（比例 0.35）**；对照 001：plan.md 26,478 B vs spec.md 7,866 B（比例 3.37）。002 的 plan 相对自身 spec **异常薄**。

按 `.specify/templates/plan-template.md` 逐节比对：

| 模板必需章节 | 002 plan | 001 plan |
|---|---|---|
| `## Summary` | ✅ 有 | ✅ |
| `## Technical Context`（语言/版本/依赖/存储/性能约束） | ❌ **缺失** | ✅ 有 |
| `## Constitution Check`（宪法合规门禁） | ❌ **缺失** | ✅ 有 |
| `## Project Structure` | ✅ 有（「目录结构」，含树图 + 路径口径说明） | ✅ |
| `## Complexity Tracking` | ❌ **缺失** | ✅ |

**plan.md 缺失的其他内容**（对照用户关注的四类）：
- **测试策略**：无独立章节。测试策略散落在 tasks.md 每任务的「验收」列——**实践上更严格**（每任务直接给测试函数名），但 plan 层无「测试分层/覆盖率口径/回归基线」的总体声明；
- **风险与缓解**：**完全缺失**。002 有三处已识别风险（云存根不可自动降级、被检语料为活体、外部扫描器 `secrun` 与仓内 `scan.py` 口径冲突），R3/R4 均已处置，但 plan 层无风险登记册，属「事后补记」而非「事前规划」；
- **数据结构**：部分缺失。有 `compare_snapshots(a_items, b_items, key, name_field="name")` 签名与判据四元组 `(code, level, reason, evidence)`，但**无 schema 定义**（`reports[]` 单项的字段表、JSON Schema、版本兼容策略）。对照 `T007_real_corpus_gate.json` 实际有 `schema` / `gate_version` / `generated_at` / `count` / `tally` / `finding_codes` / `reports[]` 7 个顶层键——**实现比 plan 更完整**。

**薄的程度评价**：属「可执行但缺治理层」的薄——技术路线表（7 行决策 + 理由）质量高、5 条「关键设计取向」判断准确（尤其第 2 条 `NOT_APPLICABLE` 与 `PASS` 严格分离、第 3 条负对照为一等公民），但缺**流程合规章（Constitution Check）与风险章**。

### 3.6 宪法 CONST-20261005-SELFVO-01 逐条对照表

| 宪法条款 | 要求 | 002 三件符合情况 | 判定 |
|---|---|---|---|
| **第零条** 永久性自指订正 | 引用须可追溯，不得改写来源 | 002 未触及此段内容，无改写 | ✅ 符合 |
| **一** 凭据零字面量（NON-NEGOTIABLE） | 无明文密钥；只写键名；出档前扫描 PASS | 三件 grep `sk-` / `AKID` / `AKIA` / `q-ak=` / `q-signature=` / `-----BEGIN` → **exit 1，零命中**；`spec.md:42` 明列「不引入任何新凭据，不读取任何密钥」；`spec.md:29` AC-5 要求作者标识只出 SHA3-512 前 16 位指纹与长度；T008 为扫描任务；R1 登记扫描 0 命中 | ✅ **符合（且为 002 的强项）** |
| **二** 超链接不可改动 | 全部 URL 原样保留，脱敏亦禁止 | 002 三件 `grep -rnoE "https?://…"` → **零命中**，即无任何 URL 可被改动 | ✅ 符合（消极符合） |
| **三** 事件等幂消费 | 幂等键收敛；关键路径强一致 | 002 为离线只读门禁，不投递总线，故不触发。但 spec 未声明「本切片不涉总线，故不设幂等键」——**免责未声明** | ⚠️ **部分符合（缺显式免责）** |
| **四** 台账 append-only 与可复现 | 一切审计日志只增不删；每条含档号/时间戳/主体/事件类型/载荷哈希；闭环验证采用 **HMAC-SHA3-512 签名链**；对账可重跑复现 | ✅ 可复现：AC-7 字节域口径、FR-5.2 `generated_at` 为唯一变化字段、实测 `test_report_is_reproducible`；✅ append-only：Phase 6 修订记录 R1~R4 只增不改；❌ **闭环验证记录未采用 HMAC-SHA3-512 签名链**——`T007_real_corpus_gate.json` 只有裸 `sha3_512`，无 `previous_mac` / `mac` 链字段；每条记录亦无「主体标识」「事件类型」字段 | ⚠️ **部分符合** |
| **五** 撞墙即停切通道 | 额度墙码零重试、留痕 | 002 不涉及外部 API 额度 | ✅ 符合（不适用） |
| **六** 协议分层与「源可得」口径 | AGPL/SSPL 分层；**SSPL 属源可得，不得笼统称开源** | 002 三件不涉及许可议题 | ✅ 符合（不适用） |
| **七** 第三方引入三先行 | NOTICE + 密钥扫描 + SBOM | AC-8 零第三方运行时依赖；实测 `ooxml_meta.py` import 面**仅 stdlib**（`hashlib`/`json`/`struct`/`sys`/`time`/`xml.etree.ElementTree`/`zipfile`/`datetime`/`pathlib`）→ **未引入任何第三方，三先行不触发** | ✅ 符合 |
| **门禁 1** SDD 流程强制；`/speckit.analyze` 在 Tasks 之后、Implement 之前执行 | 六阶段不可跳跃；analyze 必执行 | 三件齐备（Specify→Plan→Tasks→Implement→Converge 有记录）；但 `grep -n "analyze\|converge"` 于 tasks.md → **零命中**，**无 analyze 阶段产物或记录** | ❌ **违反（流程门禁）** |
| **门禁 6** 变更留痕 | 涉编号/层级/引用关系者须在修订记录追加，不得静默改动 | ✅ R1~R4 追加式；✅ R2 拒绝就地扩权；✅ R3 AC-7 口径收紧留痕；❌ 但 spec.md 自身与实测的 3 处不一致**未在 spec 内留痕订正**（见 §3.7） | ⚠️ **部分符合** |
| **门禁 5** 未通过全量回归与门禁判定的构建不得进入生产 | — | R1 记 `144 passed, 4 skipped`；R4 记 `151 passed` + 阳性对照回滚验证 | ✅ 符合 |
| **治理尾段** 各阶段产出须逐条自检宪法符合性 | 逐条自检 | plan.md **无 Constitution Check 章节**，故 plan 阶段的宪法自检**无载体** | ❌ **违反** |

**汇总：宪法 7 条核心原则——0 违反、2 条部分符合（三、四）。SDD 工作流门禁 1 与治理尾段——2 处违反。**

### 3.7 缺陷清单（本席新发现，含实证）

| ID | 严重度 | 缺陷 | 实证位置 |
|---|---|---|---|
| **D-1** | **高** | **spec.md US-1 与自身 FR-3.2 直接自相矛盾**：US-1 称「3 件 `.otl` 裸文本判 `PASS`」，FR-3.2 规定「非 OOXML 件判 `NOT_APPLICABLE`，**不得记 `PASS`**」；实测裁定确为 `NOT_APPLICABLE` | `spec.md:49` vs `spec.md:77`；实测 `T007_real_corpus_gate.json` tally `NOT_APPLICABLE: 3` |
| **D-2** | **高** | **spec.md US-1 与实测裁定不符且未订正**：US-1 称「对 2 件 `.docx` 判 `BLOCK`」，实测为 1 件 `BLOCK`（时序矛盾）+ 1 件 `WARN`（时区标记）。tasks.md T007 已按实测订正并留痕，**但 spec.md:49 未同步订正** | `spec.md:49` vs `tasks.md:42-43` 订正说明；实测 tally `BLOCK:6 / WARN:1`（6 = 5 云存根 + 1 docx） |
| **D-3** | 中 | **plan.md 缺 Constitution Check 章节**，plan 阶段宪法逐条自检无载体（违反宪法治理尾段） | `grep "Constitution Check" plan.md` → exit 1 |
| **D-4** | 中 | **plan.md 缺 Technical Context 与 Complexity Tracking 章节**（模板必需） | 同上 → exit 1 |
| **D-5** | 中 | **`/speckit.analyze` 阶段无任何产物或记录**（违反门禁 1） | `grep "analyze" tasks.md` → 零命中 |
| **D-6** | 中 | **闭环验证记录未采用 HMAC-SHA3-512 签名链**（违反宪法第四条），报告仅裸 `sha3_512`；且每条记录缺「主体标识」「事件类型」字段 | `T007_real_corpus_gate.json` 顶层键 `schema`/`gate_version`/`generated_at`/`count`/`tally`/`finding_codes`/`reports[]`，无 `mac`/`previous_mac` |
| **D-7** | 中 | **evidence 路径引用不精确**：三件多处引用 `evidence/OOXML-GATE-20261005.md`、`evidence/T007_*.json`（相对 002 目录），但实际证据在**仓库根** `A:\OPL_A2A\selfevo-sdd\evidence\`；`ls specs/002-ooxml-meta-traceability/evidence/` → `No such file or directory`。读者按 spec 相对路径查找会落空 | `spec.md:118,125`、`tasks.md:41,44,61,63,87,97,107,147` vs 实际路径 |
| **D-8** | 轻 | **`[P]` 标注不一致**：T004 依赖栏声明「可并行」但未打 `[P]` 标记 | `tasks.md:11`（格式说明）与 `tasks.md:30`（T004 无 `[P]`） |
| **D-9** | 轻 | **T006/T007 粒度偏粗**：验收基线变更（T007 订正）与执行打包在同一任务，削弱「任务完成 = 验收通过」的确定性 | `tasks.md:39-44` |
| **D-10** | 轻 | **跨切片改动未交叉引用**：R4 修改 `src/selfevo/secretscan/scan.py`（T010 切片①产物），已在 R4 声明但未在 001 的 tasks.md 建立反向引用 | `tasks.md:109-147` |
| **D-11** | 轻 | **spec.md 无 Version/Ratified 字段**（与 001 同缺，属基座共性问题而非 002 独有） | `spec.md:1-7` |

### 3.8 凭据零字面量专项

```
$ grep -rnoE "sk-[A-Za-z0-9]{4}|AKID[A-Za-z0-9]{4}|AKIA[A-Za-z0-9]{4}|q-ak=|q-signature=|-----BEGIN" \
    A:/OPL_A2A/selfevo-sdd/specs/002-ooxml-meta-traceability/
（无输出，exit 1）
```

**002 三件零凭据字面量，判定 PASS。** 附带扫描关联证据件 `evidence/OOXML-GATE-20261005.md`：唯一命中为第 279 行**讨论** `sk-…{28,}` 形态的说明文字（`仓内扫描器按**值的形态**匹配（\bsk-…{28,} 等）`），属规则描述而非真实凭据，**不构成泄漏**。

002 的零字面量纪律有两条**超出要求**的设计：`FR-1.4` 作者字段只出 SHA3-512 前 16 位指纹 + 字符长度；`FR-3.3` 云存根只披露字段名不披露取值（`fileid`/`groupid`）。这是本轮两份规格中唯一把「零字面量」从「不写密钥」扩展到「不写可定位标识」的切片。

---

## 四、核验 4：三条技术主张的独立查证

### 主张 1 —— 「段落 62 将『调用修改后的 AGPL 模块』直接等同于全服务端源码开放，**范围过宽**」

**判定：成立（但 Codex 席的转述比原文更极端，属「纠偏方向正确、用词过强」）**

**原文核对**（`_extract_tmp.txt` 第 62 段，实测）：

> 「在A2A网络生态中，若核心框架或关键技能模块采用AGPL-3.0协议，任何通过Agent网络对外提供交互服务的节点，**只要调用了修改后的AGPL-3.0模块，就必须强制开放其服务端修改源码**，从而保障生态内核心能力的开放共享与可追溯性，防止隐性闭源分支的产生。」

**条文核对**（GNU AGPL-3.0 官方全文，第 13 条，逐字）：

> 「Notwithstanding any other provision of this License, **if you modify the Program**, your modified version must prominently offer all users interacting with it remotely through a computer network (if your version supports such interaction) an opportunity to receive **the Corresponding Source of your version** by providing access to the Corresponding Source from a network server at no charge…」

第 1 条对 "Corresponding Source" 的定义：

> 「The "Corresponding Source" for a work in object code form means **all the source code needed to generate, install, and (for an executable work) run the object code and to modify the work**… **it does not include the work's System Libraries, or general-purpose tools or generally available free programs** which are used unmodified in performing those activities but which are not part of the work.」

**核验判断**：
- AGPL 第 13 条的义务主体是「**你修改后的那个版本的 Corresponding Source**」，义务对象是「与该版本远程交互的用户」——**不是**「调用者的整个服务端」；
- Corrected Source 有明确**排除项**（System Libraries、通用工具、非作品组成部分），因此**不可能**等于「全服务端源码」；
- 故原文「开放其服务端修改源码」确实**范围含糊**，把「被修改模块的对应源码」与「调用方的服务端」混同——**Codex 席的纠偏方向正确**。

**但须指出 Codex 席的两处用词过强**：
1. 原文写的是「其服务端**修改源码**」，Codex 转述为「**全服务端源码开放**」——原文虽含糊，但字面并非「全部服务端源码」；
2. Codex 称「其他程序是否纳入**还需分析作品及组合关系**」——这句偏保守：AGPL 第 13 条第二段已**明确** combine/aggregate 边界（combine 后 covered work 部分继续适用 AGPL，combine 的另一部分继续适用 GPLv3），且第 1 条已排除 System Libraries，故「其他程序是否纳入」**不完全是开放问题**，而是有明确规则可依（须区分 combine 与 mere aggregation）。

**最终**：主张的实质判断「范围过宽」**成立**；其转述与补充论证**略有夸张与过度保守**。

### 主张 2 —— 「**OSI 明确不将 SSPL 认定为开源许可证**」

**判定：成立（证据强度最高的一条）**

**OSI 官方原文**（opensource.org/blog/the-sspl-is-not-an-open-source-license，**发布日 2021-01-19**，OSI Board of Directors 署名）：

> 「The license du jour is the Server Side Public License. This license was submitted to the Open Source Initiative for approval but later **withdrawn by the license steward** when it became clear that the license would not be approved.」

> 「Fauxpen source licenses allow a user to view the source code but **do not allow other highly important rights protected by the Open Source Definition, such as the right to make use of the program for any field of endeavor.**」

> 「What a company may not do is claim or imply that software under a license that has not been approved by the Open Source Initiative, **much less a license that does not meet the Open Source Definition, is open source software.** It's deception, plain and simple…」

**旁证**（MongoDB 官方 FAQ，供应商自认）：

> 「Are you basing the SSPL on an OSI-recognized open source license? …the SSPL has not been approved by the OSI.」
> 「The only substantive modification is section 13, which makes clear the condition to offering MongoDB as a service.」

**附带核实 Codex 引用的「SSPL 第 13 条」表述**——Codex 称「SSPL 第 13 条对向第三方提供程序功能作为服务设定了更广的服务源码要求」，其报告内链 `https://www.mongodb.com/legal/licensing/server-side-public-license`。实测 SSPL 确有第 13 条（`Service Source Code` 定义），MongoDB FAQ 直接引述了 a/b 两款全文。**该表述准确**。

**最终**：主张**成立**。OSI 不仅「未认定」，而且是**主动发表声明**（2021-01-19）并使用「fauxpen source license / deception」等强烈措辞。

### 主张 3 —— 「**Git 官方文档明确 pre-commit 可被 `--no-verify` 绕过，不能承担唯一发布门禁**」

**判定：成立（两个半命题均成立）**

**Git 官方 `githooks` 文档原文**（git-scm.com/docs/githooks，2.4.12 与 2.27.0 等版本**逐字一致**）：

> 「**pre-commit** — This hook is invoked by git commit, and **can be bypassed with --no-verify option.** It takes no parameter, and is invoked before obtaining the proposed commit log message and making a commit. Exiting with non-zero status from this script causes the git commit to abort.」

同文档 `commit-msg`：「This hook is invoked by git commit, and **can be bypassed with --no-verify option**.」；`pre-merge-commit` 同。

**实测本地印证**：`selfevo-sdd` 同时安装了 `.git/hooks/pre-commit`（3,569 B）与 `.git/hooks/pre-push`（3,569 B），二者均为本地客户端钩子，**在 `--no-verify` 面前可被绕过**。因此「以 pre-commit/pre-push 作为**唯一**发布门禁」在结构上不成立。

**结论**：前半（可被绕过）有 Git 官方文档逐字支撑；后半（不能承担**唯一**发布门禁，须落到接收端/受保护 CI/分支规则）是正确推论，且与本仓宪法「提交签名与分支保护双重校验为『与』关系，任一未通过即整体拦截」在方向上一致——**Codex 席的主张与宪法门禁 2 互补而非抵触**。

### 与主理人上一轮两条裁定的关系

| 主理人裁定 | Codex 主张 | 关系 |
|---|---|---|
| 「SSPL 属 source-available，不笼统称开源」 | 主张 2（OSI 不认 SSPL 为开源） | **互补且强化**。主理人裁定是**结论**，Codex 提供了**权威出处**（OSI 2021-01-19 官方声明 + MongoDB FAQ 自认未获批）。Codex 报告用的措辞是「应采用准确的『源码可用许可』表述」，与主理人裁定的「source-available」同义。**无冲突，双向加固**。建议主理人采纳其出处，使裁定可外部复核。 |
| 「不可脱敏链接内凭据」 | 主张 1、2、3 均未涉及此问题 | **无直接关联**。但本席在核验中发现一处**需要提请注意的间接张力**：Codex 的 `review_sources.py:36-38` 对含 `q-ak`/`q-signature` 的 URL 做**整链遮蔽**（替换为 `[签名或凭据链接已遮蔽]`），在派生阅读件中共 **19 处**遮蔽标记。宪法第二条明定「链接内凭据（如 COS 预签名 URL 的 q-ak/q-signature）按『不准动链接』令原样保留，**待 L1/L2/L3 裁定后统一处置**」。Codex 席选择了「原件不动、派生件遮蔽」并在报告中明确声明「派生文本中的遮蔽明确标记，不能用于原文一致性证明」——**程序上是自洽的**，但它实际上**提前行使了主理人尚未做出的 L1/L2/L3 裁定**。这不是伪造，是**越位行使裁量**。见 §6 建议档。 |

---

## 五、核验 5：Codex 席自证边界诚实性评估

### 5.1 结论

> **总体诚实、可被采信，且自证密度高于一般席级产出。** 未发现「说了没做」。发现 **1 处「做了但表述含混」**（即主理人察觉的编号问题，属措辞而非造假）与 **1 处「实质动作被自我降级为『不计入验收』」**（Kimi/握手，属诚实但需主理人另行裁定）。**A2A 通知的原始证据文件全部存在且字段层面自洽，验真通过。**

### 5.2 「说了没做」排查（逐条反查）

| Codex 自述「未做/未验证」 | 本席反查实测 | 判定 |
|---|---|---|
| 「没有部署 Kimi Chat」 | 后续运行 `-135227` 的 `skill_install_and_execution.json` 实录：`"kimi_code_actual_invocation": "unverified; kimi command not found on PATH"`、`"kimi_chat_import_and_invocation": "unverified; kimiim-cli is group chat only"`；该轮实际安装的是 `opl-document-preflight`（`script_exit_code: 0`），**不是 Kimi Chat** | ✅ **诚实**（未做且如实登记） |
| 「安装 Spec Kit CLI」未做 | `.specify/` 全套脚手架存在，但由 **hy4 席**在提交 `d65d176` 中落盘（`author: workbuddy-hy4`），非 Codex 所装 | ✅ **诚实** |
| 「更新网卡驱动」未做 | 无任何相反证据；该项无产物可查，属不可核验声明 | ✅ 无冲突 |
| 「完成大规模文件迁移」未做 | 报告第三节点名 6 个目录链接至 A 盘，明确写「当前清单不能支持『桌面已经全部迁完』或『云端全部上传完成』的结论」 | ✅ **诚实**（并主动否定了可能对自己有利的结论） |
| 「云入口不能计为已读正文」 | manifest 中 5 件 `.wpsonline` 均记 `"kind":"wps_cloud_pointer"`、`body_status` 非 extracted；报告首节写「取得 5 件可读正文，识别 5 件云入口」 | ✅ **诚实**（计数与产物一致） |
| 「本轮并未验证从 DOCX 到云大纲的图像、修订、附件和权限转换保真性」 | 全文搜索无任何「转换保真」类断言 | ✅ **诚实** |
| 「没有独立席位签名」 | `a2a_notification.json` 5 条 `queued` 记录的 `receipt_authenticated` 字段**全部为 `false`**——即证据文件本身在字段层面自证了这句话 | ✅ **诚实且自证** |

### 5.3 A2A 通知的原始证据验真（重点核查项）

**主理人要求：查 `a2a_notification.json` 是否存在，验其真伪。**

**(a) 文件存在性**：**5 个运行目录中 4 个含 `a2a_notification.json`**（`-115159` / `-120443` / `-122623` / `-132146` / `-135227` 均有）。非孤证。

**(b) `-120443` 轮（即报告 v0.1.0 所对应轮次）实测结构**：

```
schema                : "openplanlink.review-notification/1"
sender                : "codex-review-20261005"
sender_registration   : "not_asserted"          ← 主动标注「未主张已注册席位」
module_path           : …\openplanlink-mirror\tools\a2a_hmac.py
module_sha256         : 76796b37fb93ded31ae48185a9c7415e1ae258ec2840450ebee35b7a4af2b800
endpoint              : http://127.0.0.1:4173/
notice_sha256         : 0e5c58e5c3e9e26491c7693121ab3326ae83a2925598544ebc64b4837310db2e
credentials 相关字段   : 报告中明示「未携带源件凭据或设备 MAC」
results               : 6 条
```

| 收件目标 | HTTP | result | queued | request_body_sha256（前12） | receipt_authenticated |
|---|---|---|---|---|---|
| `a2a-node-local` | 200 | `authenticated_node_reply` | — | `3b12e3ed7b31` | （`hmac_verified: true`） |
| `zcode-moon` | 200 | `queued` | true | `d3673a2d5797` | **false** |
| `cairn-dsh` | 200 | `queued` | true | `7b8005061277` | **false** |
| `workbuddy-hy4` | 200 | `queued` | true | `15811f04c926` | **false** |
| `shoucang-seat` | 200 | `queued` | true | `cba32f98a707` | **false** |
| `kimi-seat` | 200 | `queued` | true | （记录截断） | **false** |

**验真判定：真。** 依据：
1. **报告表格与 JSON 逐行一致**：报告「向 5 个协作席提交核查通知」↔ 5 条 `queued:true`；报告「本地认证往返已通过」↔ `a2a-node-local` 的 `hmac_verified: true`；
2. **JSON 比报告更保守**：报告称「客户端未声称已完成席位名册注册」↔ JSON 有 `sender_registration: "not_asserted"` 字段显式登记；报告称「五个入队回执没有独立席位签名」↔ 5 条 `receipt_authenticated: false`。**JSON 字段反过来证成了报告的自我限制声明**；
3. **旁证链齐备**：`endpoint_probe.json` 记录了 `127.0.0.1:4173/health`（200，78 B，附完整 body）、`/.well-known/agent-card.json`（200，2,486 B，附完整 body 与 sha256）、公网 `120.46.86.165` 桥接（200，2,273 B，附 body）——**含哈希与原文字段，非仅布尔断言**；
4. **防重放机制有物证**：`-115159` 与 `-132146` / `-135227` 轮各含 `response_nonces.sqlite3`（12,288 B），说明 nonce 持久化真实落地；
5. **10 件两轮哈希实测吻合**：`-115159` 与 `-120443` 两份 `manifest.json` 的 `sources[]` 逐条比对，10/10 件 `bytes` 与 `sha256` **完全相同**（首件均 `2605286` / `4dc2911ece66…`）。报告「10 件 SHA-256 在两次读取间均未变化，读取期间尺寸和修改时间稳定」**属实**。

**(c) 一处需要主理人注意的时点局限（不构成不诚实）**

主 DOCX 的哈希在**报告之后**已变化：

| 时点 | bytes | sha256（前 12） | 来源 |
|---|---|---|---|
| 11:51 / 12:04（Codex 两轮） | 2,605,286 | `4dc2911ece66` | 两份 `manifest.json` |
| 14:53（002 席 T007 首跑） | 2,605,374 → 后重写为 2,605,053（−321 B） | sha3 前 16 位 `24768165cdb9989e` → `db622771d1a440c6` | `tasks.md` R3 登记 |
| 15:46（本席实测） | 2,605,114 | `cc7d92a024e6` | `sha256sum` |

**即：Codex 席的「未变化」结论在其自身两轮读取窗口（11:51→12:04）内完全成立，此后的漂移由 WPS 云客户端后台同步造成。Codex 席未预见到后续漂移，但这不是它的责任——它无法预知 12:04 之后 15:46 的云同步行为。** 反倒是 **002 席捕捉到了该漂移并写入 R3「活体语料漂移事件」**——在这一个点上，002 席比 Codex 席更敏感。这是应当向 Codex 席正向指出的事实。

### 5.4 桌面副本一致性

```
$ sha256sum "C:/Users/欧阳宏俊/OneDrive/桌面/OpenPlanLink_A2A核查与逐件批注_20261005.md" \
           "A:/OPL_A2A/codex-review/20261005-120443-997956-source-review/OpenPlanLink_A2A核查与逐件批注_20261005.md"
7c3f8a1b5edf06b6c78a830671640ad80fd06f53adc45b110b8e04471ae9cbc9  （桌面）
7c3f8a1b5edf06b6c78a830671640ad80fd06f53adc45b110b8e04471ae9cbc9  （A 盘）
```

**逐字节一致。** 报告第七节「写入后按字节哈希回读核验，登记『本地落盘已核』」的流程**确实执行了**。这是很多席级产出会含糊过去的一环，Codex 席做到了，且可被独立复核。

### 5.5 自证边界诚实性：两处需点名的瑕疵

| 类别 | 具体 | 判定 |
|---|---|---|
| **「做了但表述含混」** | 报告第五节写「本轮在**当前协作工作区**新增 `specs/001-source-refresh` 的规格、计划、任务」。`当前协作工作区` 在字面上指 `codex-review/<run>/implementation/`，**该目录确实存在此三件**——技术上未撒谎。但读者极易误解为写入 `selfevo-sdd/specs/`。**后果已经发生**：主理人因此认为该规格「不存在」，进而怀疑其真实性。这正是「以歧义表述导致下游误判」的责任，虽非造假。 | ⚠️ **表述含混，须担责** |
| **实质动作被自我降级** | `tasks.md`（Codex 侧 `001-source-refresh/tasks.md`）末段写「线上握手、Kimi Chat 技能部署、云端同步和对方签认按证据记录，**不计入本地读取验收**」。这把 4 项实质工作移出了验收范围。**程序上是诚实的**（明确声明不算），但实质上是**扩大了自身验收面的边界**。 | ⚠️ **需主理人另行裁定** |

### 5.6 诚实性总评

| 维度 | 评分 | 依据 |
|---|---|---|
| 「未做」类声明的真实性 | **5/5** | 7 项逐条反查全部属实，无一项夸大 |
| 「已做」类声明的证据密度 | **5/5** | `manifest.json` / `a2a_notification.json` / `endpoint_probe.json` / `verification.json` / `response_nonces.sqlite3` 五类原始证据齐备，含哈希、字节数、时刻、原文字段 |
| 自我限制的主动性 | **5/5** | 主动写 `sender_registration:"not_asserted"`、主动写 5× `receipt_authenticated:false`、主动指出 `pre-commit` 可被绕过（即指出自己依赖的门禁有弱点）、主动说「当前清单不能支持桌面已迁完」——**主动交代对自己不利的部分** |
| 表述精确度 | **3/5** | 「当前协作工作区」一处歧义已致下游误判 |
| 验收面划定 | **3/5** | 4 项实质工作移出验收范围，程序诚实但需外部裁定 |

**综合：可被采信。** 建议主理人在采纳其结论时，**对其「已做」部分按证据采信、对其「未做」部分无需追加核查**，仅对第五节的表述歧义提出更正要求。

---

## 六、给主理人的行动建议

### 6.1 须立即修正（4 项）

| # | 事项 | 依据 | 建议动作 |
|---|---|---|---|
| **A-1** | **纠正 002 的归属认知**：002-ooxml-meta-traceability 由 **hy4 席**产出，非 Codex 席 | `spec.md:4,53`、Git `author: workbuddy-hy4`、`evidence/20261005-1540-hy4-increment/` | 在席位台账中登记；后续对账不得把 002 计入 Codex 席产出 |
| **A-2** | **消除两套 `001`~`005` 编号序列的并存**：Codex 侧 `001-source-refresh`~`005-deadletter-retry` 与基座 `001`/`002` 编号同名、主题无关 | §1.2(d) | 二选一：① 将 `codex-review/<run>/implementation/specs/` 改名为 `specs-codex/` 或 `runspecs/`（保持 run 内相对路径不变，零改动成本）；② 为 Codex 侧另立编号前缀（如 `X01`~`X05`）。**推荐 ①**，因改动面最小 |
| **A-3** | **修正 spec.md 的两处错误裁定（D-1、D-2）**：`spec.md:49` 的「3 件判 `PASS`」违反自身 FR-3.2；「2 件 docx 判 `BLOCK`」与实测（1 BLOCK + 1 WARN）不符。tasks.md T007 已订正留痕但 spec 未同步 | §3.7 D-1/D-2 | 在 spec.md 增补 §5.2「US-1 实测订正」，与 tasks.md T007 的订正理由互相引用，**追加式留痕，不得就地改写**（宪法门禁 6） |
| **A-4** | **补 plan.md 的 Constitution Check 章节（D-3）**：宪法治理尾段明定「各阶段产出（spec/plan/tasks）均须逐条自检本宪法符合性」，现 plan 层无载体 | §3.6、§3.7 D-3 | 补写 7 条核心原则 + 6 项门禁的逐条自检表（可引用本席 §3.6 作为初稿，但须由 002 席自行确认） |

### 6.2 建议补齐（6 项）

| # | 事项 | 依据 |
|---|---|---|
| **B-1** | **补 `/speckit.analyze` 阶段产物或记录（D-5）**：门禁 1 明定其在 Tasks 之后、Implement 之前**必须执行**；002 三件零命中 | §3.6、§3.7 D-5 |
| **B-2** | **门禁报告补 HMAC-SHA3-512 签名链（D-6）**：宪法第四条要求「闭环验证记录采用 HMAC-SHA3-512 签名链」，现报告仅裸 `sha3_512`，无 `mac`/`previous_mac`，亦无「主体标识」「事件类型」字段 | §3.6、§3.7 D-6 |
| **B-3** | **修正 evidence 路径引用（D-7）**：三件共 10 处写 `evidence/…`（相对 002 目录），实际在仓库根。读者按 spec 相对路径查找会落空 | §3.7 D-7 |
| **B-4** | **把 `review_sources.py` 沉淀进 SDD 基座并纳入门禁扫描（R-1~R-4）**：现状为证据目录内的两份无版本控制副本，路径硬编码 C 盘真身，`.git/hooks/pre-commit` 对其零覆盖 | §2.3 |
| **B-5** | **就 Codex 席派生件遮蔽签名链接一事作 L1/L2/L3 裁定**：宪法第二条定「链接内凭据原样保留，**待 L1/L2/L3 裁定后统一处置**」；Codex 席已在派生件中遮蔽 19 处，实际提前行使了尚未做出的裁定。程序自洽，但属越位 | §四末段 |
| **B-6** | **补 plan.md 的 Technical Context / Complexity Tracking 两章节（D-4）及风险登记册**：002 已识别 3 项风险（云存根不可自动降级、语料为活体、外部扫描器口径冲突）但 plan 层无风险规划章节，全靠 R3/R4 事后补记 | §3.5、§3.7 D-4 |

### 6.3 可暂缓（5 项）

| # | 事项 | 依据 |
|---|---|---|
| **C-1** | 细化 T006/T007 粒度（D-9）：把「全量回归」与「10 件实跑」各自拆为独立可验收任务 | 严重度低，当前 9/9 任务均有具名测试绑定，追溯性尚可 |
| **C-2** | 统一 `[P]` 标注（D-8）：T004 声明可并行但未打 `[P]` | 纯格式问题，不影响执行 |
| **C-3** | 补 001↔002 跨切片交叉引用（D-10）：R4 改了 T010 切片的 `scan.py` | 已声明，仅缺反向引用 |
| **C-4** | spec.md 增补 `Version` / `Ratified` 字段（D-11） | 001 同缺，属基座共性问题，宜统一处理而非单点修 |
| **C-5** | 引入数据 schema 定义（`reports[]` 字段表 / JSON Schema） | 实现已领先 plan；可在下次升 `GATE_VERSION` 时补 |

### 6.4 须向 Codex 席正向反馈的两点

1. **「SSPL 不被 OSI 认定为开源」这一纠偏应予采纳并向外扩散**：其提供的 OSI 官方声明（2021-01-19）与 MongoDB FAQ 自认未获批，使主理人「SSPL 属 source-available，不笼统称开源」的裁定从**内部裁定**升级为**有外部权威出处支撑的可复核结论**。这是本轮 Codex 席对主理人最有实质价值的贡献。
2. **关于活体语料漂移：002 席比 Codex 席更早捕捉到**。Codex 两轮（11:51/12:04）记录主 DOCX 为 `2605286` / `4dc2911ece66`，至 14:53 已被云客户端重写为 `2605053`，本席 15:46 实测为 `2605114` / `cc7d92a024e6`。002 席在 tasks.md R3 将此登记为「活体语料漂移事件」并据此**收紧** AC-7 口径为「字节域可复现，非时间域」。建议主理人将此反哺 Codex 席的 `review_sources.py`——该工具目前只做「本轮 vs 上一轮」比较，**无跨轮次基线持久化**，故无法发现 12:04 之后的漂移。

---

## 附：本席核验边界声明

1. 本席**未修改任何被核验文件**：对 `A:\OPL_A2A\` 全树只做读操作（`ls`/`find`/`grep`/`Read`/`sha256sum`/`python -c` 只读内联）。唯一写入为本报告自身。
2. 本席**未执行** `review_sources.py`、`ooxml_meta.py` 或任何被核验脚本（仅用 `ast.parse` 做语法解析验证）。
3. 本席**未运行**任何 Git 写操作（无 commit/checkout/reset/stash）。
4. 本报告中出现的一切哈希、字节数、字段值均可由本文所载命令复现。
5. 凭据：本席在 Codex 派生阅读件中确认遮蔽标记 19 处、明文凭据残留 **0** 处；未在任何位置发现可还原的密钥值，故本报告不含任何凭据字面量。
6. 本席对 Codex 席的三条技术主张**未采信其自述**，全部以 GNU / OSI / MongoDB / git-scm 官方原文为准；其中主张 1 的转述用词被本席判定为「过强」并已指出。

**报告完**
