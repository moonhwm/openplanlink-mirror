# pipeline：三系要点与坑位全册（2026-09-11 实战校准）

## 目录
一、女娲系（吸收）／ 二、仓颉系（锻件）／ 三、达尔文系（评审）／ 四、守门两件 ／ 五、坑位速查

## 一、女娲系（吸收段）

- **分流先于动手**：Phase 0A=快速档（3 维度×5 来源，材料薄/主题熟时用）；Phase 0B=深档（材料厚/陌生域）。
- **铁律**：捕捉 HOW they think，不是 WHAT they said。产出是思维流程、判据排序、禁令与失效转介——不是内容摘要。
- 实锚：munger-mind-ops 快速档成稿 135 行，判官受评 84.4（d5 具体性/d9 禁令最强，d6 资源引用最弱）。
- 引句纪律：授权文本为准；无源引句标 attributed 或不采。

## 二、仓颉系（锻件段）

- RIA-TV++ 五阶段 + Capability Bundle + `cangjie.py compile` 确定性编译（single/pack 双模）。
- **坑（实踩）**：`compile --bundle` 必须指 **capabilities 目录**，指 verified.yaml 文件 → NotADirectoryError（sidecar=bundle.parent 当 name=="capabilities"）。
- **坑**：`run_trigger_evals.py split|prepare|score` 只吃单技能 should_trigger 套件格式；多类路由任务集（'tasks'/'expected'）须自建判分器。
- **坑**：`count_tokens.py` 需 tiktoken；配置走位置参数非 --config。
- 无编译器在场时：按 skill-creator 章法手工成形（frontmatter/<500 行/重者入 references/官方 package_skill.py 验证）。

## 三、达尔文系（评审段）

- 9 维 rubric 权重：d1=7 d2=12 d3=12 d4=6 d5=18 d6=4 d7=12 **d8=23** d9=6。d8=实测表现维，静态不可评，**留判官**。
- 静态 8 维法典化扫描器=`scripts/rubric_score.py`（与 93 件大筛查同一法典；software-testing 复打 76.9 与总榜逐点相符=口径保真）。
- **静态偏差两条在案**：①短而密件被低估（stat-verdict 静态 57.0 vs 判官 75.8；munger 静态 74.8 vs 判官 84.4）；②营销话术不可捕（software-testing 静态 76.9 vs 判官 60.5）。修法三条登记：信号按行长归一/营销词入 dim7/d4 加权。
- **棘轮规矩**：换装判 KEEP/REVERT=paired 同判官比较+奇数 N 多数决；绝对分数降级 triage-only；甲乙顺序交叉防位置偏倚。
- **同源偏倚披露制**：judge 编组跨 2 独立 provider 下限，否则裁决降级 triage；马甲模型登记疑似同源族；paired 裁决同族异族分歧时异族判官优先。

## 四、守门两件（收件端）

| 件 | 管什么 | 联动 |
|---|---|---|
| skill-intake-audit-ops | 十探针安检（穿越/符号链/炸弹/撞名/触发面/注入/脚本/凭证/清单自证） | `--audit-script` 传入；FAIL 拒收 |
| backup-delta-ops | 解包归一化与增量打包（扁平包壳、MANIFEST、四闸） | 归一化逻辑内嵌于 lineage_intake.py |

## 五、坑位速查

| 坑 | 解法 |
|---|---|
| --bundle 指文件 → NotADirectoryError | 指 capabilities 目录 |
| 多类路由集喂 run_trigger_evals → 不兼容 | 自建判分器（严格/可接受/miss 三档+多数决） |
| count_tokens --config 报错 | 位置参数 + 先装 tiktoken |
| 扁平 zip 批量解包串件 | 归一化包壳（本件第 2 段已内置） |
| 静态分当终审 | 边界案送判官；d8 恒留判官；棘轮走 paired |
