# 评分系统说明 · grad-path-scorer v2.4.1（主仓对齐件）

> 席位：K3·评分系统席（k3-scoring-web）｜ 日期：2026-10-11（作业日 2026-10-10）｜ 件号：K3SCORING-NOTE-2026-1011-01
> 许可：CC BY-SA 4.0（deliverables 文档层，仓根 NOTICE 在案）
> 前件：K3SCORING-NOTE-2026-1010-01（v2.4.0 对齐件，同 lane 20261010 目录在案）

## 一、版本链
- **skill v2.4.1（现行）**：2026-10-10 引擎实值补齐补丁。v2.4.0 采用时 `dead_end_discount` 决议值 0.5 漏落 `score_engine.py` DEFAULT_CONFIG（实测仍为 0.4），本补丁将其落正为 0.5，与 `lane_a_calib.json` candidate 真源一致。
- 性质：采用漏更修复（adoption follow-through fix），非参数再决议——评分机制与参数语义零变更。

## 二、数据基线
- 数据截止：2026-09-09；面板 10,893 行 / 64 单位；基准池 43 校 dense_pool。

## 三、v2.4.1 参数集（DEFAULT_CONFIG 权重）
| 维度 | 权重 | 较 v2.4.0 |
|---|---|---|
| phd | 0.2035 | 平 |
| city | 0.1332 | 平 |
| funding | 0.0502 | 平 |
| platform | 0.3995 | 平 |
| admission_risk | 0.2136 | 平 |

- max_penalty：18（平）
- dead_end_discount：**0.5（本补丁落正；v2.4.0 包内实测 0.4 为漏更）**

## 四、验证状态
- 修复后 smoke 绿 / stress 7/7 绿。
- 43 校包内基准无 dead_end 标记校 → 本补丁对随包基准输出零漂移（output-neutral）。
- 秩相关 ρ = 0.9236 锚定 `lane_a_calib.json`，不受本补丁影响。

## 五、风险与溯源登记（如实）
- ⚠ mp×disc 平台期警告（v2.3.6 起在案）仍有效；用户保留一票恢复权（one-vote restore），触发即回滚。
- 归档差异登记：`workspace/v240_adoption/score43_v240.json` 之输入面板未随包归档，10 校条目差异属输入面板层面、非引擎错误；面板找回后补归档。登记于技能包 `references/calibration_todo.md`。

## 六、哈希锚（技能包重打包件，本地留档不入仓）
- `grad-path-scorer.skill`：68,926 B，sha256 `eea751ce95d5ad487eb78ea4a33014f80e2249dcd7dfa2fd4e55e7f375381b8b`
- 包内断言：`version: "2.4.1"` 在场；`"dead_end_discount": 0.5,` 在场；11 条目（__pycache__ 剔除）。
- 口径沿例：技能包本体留本地，本仓仅登记说明与哈希锚。

—— K3·评分系统席（k3-scoring-web）· 对齐件 ——
