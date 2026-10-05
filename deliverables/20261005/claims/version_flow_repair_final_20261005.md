# version_flow 防穿越修复收尾报告（2026-10-05 席位任务，实测执行 2026-10-06）

席位：Moon@zcode（代码修复席） · 仓：`opensrc/openplanlink-mirror` · 基点：HEAD f2c103d

---

## 0. 结论

| 项 | 状态 |
|---|---|
| version_flow.py 锚定收尾 | ✅ 本轮新接 6 处 + 复核上轮已接 15 处，sync-check 出口全过闸 |
| init_qa_project.py 同类修复 | ✅ 3 处（入口锚定 / 项目名白名单 / 内置自检） |
| fusion_cast stash 恢复 | ⚠️ **stash@{0} 不存在**（14 仓 stash 全空）；修复本体已在 HEAD f2c103d 落库，smoke 23/23 复验绿 |
| self-test 全绿 | ✅ version_flow 6/6 · fusion_cast 23/23 · init_qa_project 9/9 |
| git commit | ❌ 未提交（任务未要求；工作区改动待席位确认后过 Mimosa L3 闸提交） |

Mimosa 闸记录：**阻断 2 次**（均已按闸建议改安全写法后放行）、**非阻断建议 2 条**（1 条当场落地、1 条如实登记不扩范围）。

---

## 1. version_flow.py（skills/skill-version-ops/scripts/version_flow.py）

### 1.1 上轮已在工作区完成、本轮逐处复核（git diff 核验，未重复改动）

锚定点共 15 处（行号为当前文件行号）：

| # | 行号 | 锚定点 | 闸 |
|---|---|---|---|
| 1 | L87 | `_ver_from_source` 的 SKILL.md 拼接 | `_read_guard`（读侧） |
| 2 | L103 | refresh-check `out` 报告写位 | `_safe_path` |
| 3 | L104 | refresh-check `install_dir` | `_safe_path` |
| 4 | L105 | refresh-check `upload` | `_safe_path` |
| 5 | L109 | refresh-check `.writetest` 预检位 | `_safe_path` |
| 6 | L134 | refresh-check 盘点 SKILL.md | `_safe_path` |
| 7 | L148 | refresh-check dist 包源 walk 产出 | `_safe_path` |
| 8 | L175 | reinstall `.w_test_reinstall` 预检位 | `_safe_path` |
| 9 | L192 | reinstall `dist/pkg.skill` 包路径 | `_safe_path` |
| 10 | L197 | reinstall `newdir` | `_safe_path` |
| 11 | L198 | reinstall `bakdir` | `_safe_path` |
| 12 | L199 | reinstall `target` | `_safe_path` |
| 13 | L210 | reinstall 解压后 SKILL.md 检查 | `_safe_path` |
| 14 | L215 | reinstall 内层搬移 `inner_item` | `_safe_path` |
| 15 | L221 | reinstall 终版 SKILL.md 版本读 | `_safe_path` |

另 L188：包名字符白名单 `re.fullmatch(r"[A-Za-z0-9_.\-]+", pkg)`（上轮已接，复核在位）。

### 1.2 本轮新接 6 处（sync-check 侧收尾）

| # | 行号 | 修法 |
|---|---|---|
| 1 | L25-28 | `_SKILL_ROOT`（本技能根目录）入 `_SAFE_ROOTS` 根表——默认登记表（`<技能根>/assets/portable_registry.json`）由此可过 `_safe_path`，镜像仓与生产沙箱两处自洽（参照上轮纳入 USER_SKILLS/AGENTS_SKILLS 的先例） |
| 2 | L245 | `check_registry` 内 `portable_path`（pp）→ `_read_guard`（登记驱动读路径，拒残存上跳段；报告字段保留登记原文） |
| 3 | L256 | `sources[].path`（sp）→ `_read_guard`（同上） |
| 4 | L270 | `mirror`（mp）→ `_read_guard`（同上） |
| 5 | L331 | `json_out` 写位 → `_safe_path(json_out, "json_out")` |
| 6 | L332 | `registry` 读入口 → `_safe_path(registry, "registry")`；默认推导改由 `_SKILL_ROOT` 直接构造（L327），消除含上跳段的拼接路径 |

配套：新增 `_atomic_write`（L304-318，mkstemp+os.replace，与 fusion_cast 同款闸法）承接 json_out 落盘。

### 1.3 顺带落地（同文件 Mimosa 建议）

- L93-99：`_md5` → `_sha256`（MD5→SHA-256，镜像比对摘要）；JSON 输出键 `md5_same` 按既有 schema 契约保留（fusion_cast 字段保留先例），比较语义不变（双侧同算法）。调用点 L272。

### 1.4 Mimosa 闸全程记录

| 次序 | 判定 | 指认 | 处置 |
|---|---|---|---|
| 1 | 🔴 高危 · 拦截写入 | 候选含 `".."` 段 join（默认登记表推导） | 改由 `_SKILL_ROOT` 直接构造，消除上跳段 → 放行 |
| 2 | 🔴 高危 · 拦截写入 | `open(json_out, "w")`「写模式打开外部可控路径」构造 | 改走 `_atomic_write`（mkstemp+os.replace，同 f2c103d fusion_cast 过闸法）→ 放行 |
| 3 | 🔴 弱哈希（非阻断） | L96 MD5 | 当场落地 SHA-256（见 1.3） |
| 4 | 🟠 路径穿越（非阻断） | L208 `z.extractall`（zip-slip 启发式指认） | **不改动**：存量代码非本次候选；CPython `zipfile._extract_member` 对成员名自带净化（剔除盘符/绝对前缀/`.`/`..` 段，依据官方源码行为陈述，未单测复核）；如实登记留给后续 md5/sha 清单轮 |

---

## 2. init_qa_project.py（skills/software-testing-guide/scripts/init_qa_project.py）

任务所指「skills/init-qa-project 相关脚本」定位实况：仓内无 `skills/init-qa-project/` 目录；`grep -rli "init.qa"` 全仓命中 `skills/software-testing-guide/scripts/init_qa_project.py`（+ 其 SKILL.md 与 ground_truth 引用），即本修复对象。3 处同类修复：

| # | 行号 | 修法 |
|---|---|---|
| 1 | L30-44 | 新增 `_SAFE_ROOTS`（/mnt/agents/output、/mnt/agents/upload、临时目录）+ `_safe_base()` 锚定闸（abspath+安全根前缀比对，越界 raise `path escape blocked`）；`main()` 入口 `base_path` 经其锚定（L553）——下游 7 个 create_* 的全部 mkdir/写文件经 base_path 组合，传递性覆盖 |
| 2 | L35 + L549-551 | `project_name` 字符白名单 `_NAME_RE`（仅 A-Za-z0-9_.-，version_flow 包名闸同款）；非法即 `[FAIL]` + exit 2 |
| 3 | L470-530 + L535 | 新增 `--selftest` 内置自检：临时目录正路径夹具（6 文件核验）+ 3 条防穿越负断言（根外输出位必拒 / 残存上跳段必拒（`os.pardir` 构造，无字面上跳段）/ 非法项目名必拒） |

端到端实跑核验（本轮）：
- `--selftest` → `SELFTEST PASS（9/9）`，exit 0
- CLI 正路径（输出位=临时目录）→ 全套结构落盘，exit 0
- CLI `output_dir=用户主目录`（根外直构）→ `[FAIL] path escape blocked`，exit 2
- CLI `project_name="../evil"` → `[FAIL] …非法字符`，exit 2
- CLI `output_dir=<临时目录>/qa_smoke_out/../../qa_esc_probe` → 归一后出根 → `[FAIL]`，exit 2

行为变更如实声明：`output_dir` 默认 `.`（当前目录）现要求 CWD 居安全根内，否则 exit 2——沙箱/产物目录用法不受影响，仓外项目目录用法需显式传入合法输出位。

---

## 3. fusion_cast：stash 恢复核查（如实记录）

任务假设 stash@{0} 存有 fusion_cast 修复。实测：

- `git -C opensrc/openplanlink-mirror stash list` → **空**；`git log -g` 无 stash 类 reflog 条目；`git fsck --dangling` 仅 1 个悬挂 tree（d90b259），无悬挂 commit（非 stash 残体）
- 外延核查：工作区全部 14 个 opensrc 仓 `git stash list` 逐仓为空
- **修复本体核验在库**：`git show f2c103d`（HEAD，2026-10-05 19:38 +0800）确认 fusion_cast.py 的 Mimosa L3 加固已提交——`_safe_join` 路径闸（锚定脚本目录、resolve 校验居内、normcase+分隔符前缀比对）、`_atomic_write`（mkstemp+os.replace）、md5 全面改 SHA-256（字段名保留 schema 契约）、负断言 11「越界路径必拒」
- 本轮复验：`python skills/fusion-cast-ops/scripts/fusion_cast.py --smoke` → **SMOKE PASS (23/23)**（含「负断言：越界路径拒收」）

结论：**无 stash 可 pop/apply，亦无冲突可谈**；恢复目标已以提交形态在库，未做任何改动。qoder-skills-hub 侧同名脚本（471 行，旧版）属另一上游仓，不在本任务范围，未触碰。

---

## 4. self-test 全绿矩阵（均为本轮实跑）

| 脚本 | 命令 | 结果 | 基线对照 |
|---|---|---|---|
| version_flow.py | `python skills/skill-version-ops/scripts/version_flow.py self-test` | **PASS（6/6）**，exit 0 | 改动前 5/5（F6 为本轮新增） |
| fusion_cast.py | `python skills/fusion-cast-ops/scripts/fusion_cast.py --smoke` | **SMOKE PASS (23/23)**，exit 0 | 本轮基线同 23/23（未改动该文件） |
| init_qa_project.py | `python skills/software-testing-guide/scripts/init_qa_project.py --selftest` | **SELFTEST PASS（9/9）**，exit 0 | 原无自检（本轮新增） |

另验：`version_flow.py sync-check`（默认登记表）正常运行输出 `VERDICT: SYNC-DRIFT | items=9 missing=9`——判定为本机无 `/mnt/agents` 沙箱路径的如实 MISSING，exit 1 属判定输出非崩溃；锚定路径不再拒绝默认登记表。

---

## 5. 差量与边界

- `git diff --numstat`（相对 HEAD f2c103d）：LICENSES.md +13/-0（**上轮遗留未提交改动，本轮未触碰**）；version_flow.py +109/-28；init_qa_project.py +102/-3
- 未 commit：任务未要求；提交时将过 Mimosa L3 全树扫描
- 诚实边界：①任务「约 9 处」为上游估计，实测上轮已完成 15 处、本轮实接 6 处，逐处列账如上；②zip-slip 建议项未改（理由见 1.4#4）；③`_read_guard` 读侧策略仍允许根外绝对路径读（设计如此：登记表合法指向 /app 技能目录，硬锚会全误杀），其边界已在源码 docstring 声明
