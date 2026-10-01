# slime_router — K3 黏菌协作架构 v1.5「踪迹加权路由」实装

日期：2026-09-09（v0.2 → v1.1 接口升级 → v1.2 canary/revival 修复 → v1.3 失败三分类 → v1.4 人工解冻 → v1.5 六大升级：provenance 分籍 / cc 双轨 / 质量权重 / 总线直发 / 审计快照+哈希链 / 阻尼防羊群。版本冻结令已经用户裁决作废，先进算法全速推进）｜ 单文件 Python 3（仅标准库）｜ 状态介质：`state/<pool>.json` + `state/<pool>.events.jsonl` + `state/<pool>.heartbeat.json`

## 用法

```bash
python3 slime_router.py register  <pool> <endpoint> [--cost C] [--platform P]
python3 slime_router.py select    <pool> [--eta 2.0]
python3 slime_router.py report    <pool> <endpoint> <ok|fail> [--latency_ms L] [--cost_units U] [--decay 0.97]
                                  [--reason channel|task|compliance] [--target T]
                                  [--prov real|replay|synthetic]      # v1.5
                                  [--quality 0-10 [--quality-src blind_review|auto|manual]]  # v1.5
python3 slime_router.py status    <pool>                 # JSON 输出
python3 slime_router.py heartbeat <pool> --cluster <id>  # v1.1 集群心跳/租约
python3 slime_router.py unfreeze  <pool> --target T      # v1.4 人工解冻
python3 slime_router.py snapshot  <pool>                 # v1.5 全量快照
python3 slime_router.py rollback  <pool> --to <snapfile> # v1.5 回滚
```

示例：

```bash
python3 slime_router.py register finance ep1 --cost 1 --platform aws
python3 slime_router.py register finance ep2 --cost 2 --platform gcp
python3 slime_router.py select finance            # -> ep1
python3 slime_router.py report finance ep1 ok --latency_ms 120 --cost_units 1
python3 slime_router.py report finance ep2 fail
python3 slime_router.py status finance
```

## 参数表

| 参数 | 默认 | 含义 |
|---|---|---|
| `--eta` | 2.0 | select 权重指数：w = trail^ETA |
| z (代码常量 `Z_EXPLORE`) | 0.03 | 探索下限：3% 概率在候选中均匀随机（SMA.m L55） |
| `--decay` | 0.97 | 每次 report 后全池踪迹衰减 |
| `DEP_BASE` | 1.0 | ok 沉积基数；×(1/cost_units)×(1000/max(latency,1))（若给出） |
| fail 惩罚 | trail ×= 0.5, fail_count += 1 | — |
| `DORM_STREAK` / `DORM_SHARE` | 10 / 5% | 活性端口占比连续 10 次 report <5% 且池内活性>2 → 休眠（S1-S5 v2） |
| 修正案B | fail_rate>10% → 阈值放宽到 8% | 防事故通道被误留 |
| `CC_WINDOW_S` / `CC_MIN_FAILS` | 10s / 3 | 同窗 ≥3 个不同端口 fail → common-cause 平台事件 |

## 与 v0.2 判据对应关系

| v0.2 条款 | 实装位置 |
|---|---|
| trail^ETA 加权随机 | `Router.select`（默认 ETA=2.0） |
| 探索下限 z=0.03 | `select` 中 `rng.random() < Z_EXPLORE` → 均匀随机（v1.2：候选含 dormant，选中 dormant 即金丝雀探测，记 `canary` 事件） |
| D2 熔断（活性<2 唤醒最低 fail_rate 休眠端口） | `select` 入口，记 `reactivation` 事件 |
| v1.2 金丝雀/复活（canary/revival） | dormant 端口被探索选中 → `canary` 事件；随后 `report ok` → 状态回 active、trail 重置为活性均值×10%（防 trail² 瞬间垄断）、记 `revival` 事件；`report fail` → 保持 dormant 且 below_streak 重置 |
| 沉积/惩罚/衰减 | `Router.report`：ok 沉积（成本/延迟感知）、fail 半减、全池 ×DECAY |
| 休眠判据 S1-S5 v2 简版 + 修正案B | `report` 末尾：below_streak ≥10 且活性>2 → `dormancy` 事件 |
| 修正案A（成本只入休眠不入路由） | `select` 只用 trail；`status` 暴露 `efficiency = trail/cost` 休眠效率分 |
| v1.1 新鲜度/心跳/原子写/协议段 | `_save`（ts_written/ttl/protocol、tmp+os.replace、.bak）、`heartbeat`/`_cluster_status`、`status`（age_seconds/stale/clusters） |
| common-cause 条款 | `report`：10s 窗内 ≥3 端口 fail → 冻结当次 DECAY、`common_cause_frozen=true`、`common_cause` 事件；冻结期 `select` 优先选择与最近 fail 端口不同 `--platform` 的候选；窗口清空且有 ok 到达时自动解冻（`common_cause_cleared` 事件） |

## v1.1 新增接口

1. **快照新鲜度**：每次 `_save` 在 state json 顶层写入 `ts_written`（epoch，随写更新）与 `ttl_seconds`（默认 300）。`status` 输出增 `age_seconds` 与 `stale`（age > ttl，或旧快照无 ts_written 时保守判 stale=true）。
2. **心跳/租约**：`heartbeat <pool> --cluster <id>` 原子写 `state/<pool>.heartbeat.json`（每集群 `{cluster_id, ts, ttl=120}`）。`status` 增 `clusters` 段，列各集群 `age_seconds` / `ttl` / `liveness`（`alive`|`dead`），区分「安静」与「集群死亡」。
3. **半写防护**：所有 state 写入改为 `tmp + fsync + os.replace` 原子写；覆盖前把上一版留作 `.bak`；读端 json 解析失败自动回退读 `.bak`。
4. **协议语义落盘**：state json 增 `protocol` 段 `{version:"1.1", eta:2.0, z_explore:0.03, decay:0.97, dorm_streak:10, dorm_share:0.05, fail_punish:0.5, cc_window_s:10.0, cc_min_eps:3}`，读端无需外部 README 即可解释字段语义；`status` 同步输出该段。
5. **向后兼容**：`select`/`report`/`status` 行为不变；旧版 state 文件缺新字段时读入即补默认（`ttl_seconds=300`、`protocol` 全量默认、`ts_written=None`→保守 stale）。

## 集群B读端实证发现 → v1.1 修复对照

| 实证发现（集群B读端实证_2026-09-09.md「元问题」） | v1.1 修复 |
|---|---|
| ① 写读延迟＋② 状态无时间戳，读端无法判断快照多旧 | `ts_written`/`ttl_seconds` 落盘 + status `age_seconds`/`stale`（T6） |
| ③ 语义盲区：协议参数不落盘，读端只能猜 | `protocol` 段落盘（T8） |
| ④ 无锁单文件 JSON 可能读到截断/半写 | tmp+os.replace 原子写 + `.bak` 回退（T9） |
| ⑤ 无失效检测：写端宕机与安静不可区分 | `heartbeat` 子命令 + status `clusters` 存活段（T7） |

注：事件流 `events.jsonl` 的 `ts` 字段此前已有，保留不变；事件追加与 select/report/status 语义均未改。

## v1.2 修复：dormant 端口的金丝雀/复活机制（swarm 评估发现的真 bug）

v1.1 及以前，dormant 端口**不在** select 的 z 探索候选集内——z=0.03 的探索流量永远到不了 dormant 端口，「修复后靠探索重新发现」的机制实际不存在，恢复只能靠 D2 熔断（活性<2 时被动唤醒）。v1.2 修复：

1. **canary（金丝雀探测）**：z 探索分支的候选集改为活性+dormant 全体（均匀随机）。选中 dormant 端口是合法返回，并在 events 落 `"canary"` 事件（含当时 active/dormant 数）。仅被选中不改变状态——复活需要真实流量回执。
2. **revival（复活）**：dormant 端口被 `report ok` 后解除休眠：状态回 active，`below_streak` 清零，trail 给一个小重启值 = 当前活性端口 trail 均值 × `CANARY_REVIVE_TRAIL_RATIO`(0.1)，防止 trail² 加权下复活端口瞬间垄断路由；落 `"revival"` 事件。被 `report fail` 则保持 dormant 且 below_streak 重置。
3. **protocol 段**升级：`version: "1.2"`，新增 `canary_revival_trail_ratio: 0.1`；旧 state 无新字段时读入即补默认（向后兼容，T10 覆盖）。
4. **铁律4 现在代码级成立**：「休眠不是死刑，探索流量可以重新发现 dormant 端口」从 v1.2 起由 select 探索分支 + canary/revival 事件链实际兑现，而非仅靠 D2 熔断兜底（T11–T13 实证）。

## v1.3 失败三分类（fail_reasons）

v1.2 及以前 `report fail` 一律 trail×0.5 并计入 fail_rate——但失败其实有三类，混在一起会冤枉好通道（实证：opencv/curl_direct 冤案，见 retro_v13_2026-09-09.md）。

### 三分类语义表

| `--reason` | 语义 | trail | fail_count / fail_rate | 计数/事件 | 典型判例 |
|---|---|---|---|---|---|
| `channel`（默认，向后兼容 v1.2） | 通道自身故障，该罚 | ×0.5 | fail_count+1，进 fail_rate 分母分子 | —（沿用原 fail 路径） | 环境漂移（pyzbar/zxing 装不上）、端点未实装（rust_browser_pilot） |
| `task` | 任务层不可解，通道无责 | 不罚（仅全池正常 decay） | 不进 fail_rate | `task_fail_count+1`，落 `task_fail` 事件 | 萨莉亚 QR 图像素饱和、信息物理丢失，八通道全灭也非通道之罪 |
| `compliance` | 合规禁止，通道无责且目标应冻结 | 不罚 | 不进 fail_rate | `compliance_count+1`，落 `compliance_fail` 事件；带 `--target T` 时 T 去重写入池级 `frozen_targets` 并落 `frozen_target` 事件 | robots 禁爬 / LII 站点（`--target lii.org`） |

### 机制细则

- **fail_rate 只算 channel 类**：分母 = ok_count + fail_count（fail_count 仅 channel 失败累加）；`status` 每端点分列 `fail_rate_channel` / `task_fail_count` / `compliance_count`（`fail_rate` 字段保留 = fail_rate_channel，向后兼容）。
- **common-cause 窗口只收 channel fail**：任务/合规失败不进 10s 窗口，不会触发平台级冻结。
- **select 无变化**：`frozen_targets` 不做进路由；目标冻结由调用方查 `status['frozen_targets']` 自觉遵守。
- **protocol 段**升 `version: "1.3"`，增 `fail_reasons: ["channel","task","compliance"]`；旧 state 缺 `task_fail_count`/`compliance_count`/`frozen_targets` 时读入即补默认（向后兼容，T10 覆盖）。

### 使用规约

1. 判例与合规材料（robots.txt、站点条款、授权书等）仅作**合规自证**存档用途；`frozen_targets` 是本系统的**自律冻结记录，不构成法律意见**。是否合规由调用方（人）负责判定，路由器只忠实记账。
2. 归因纪律：只有确证通道自身故障（装不上、未实装、超时、崩溃）才用默认 `channel`；任务本身不可解（信息物理丢失、规格矛盾）用 `task`；被规则/条款禁止用 `compliance` 并尽量带 `--target`。拿不准时先查再报，不要把 task/compliance 失败图省事记成 channel——那正是 v1.3 要消灭的冤案。
3. `frozen_targets` 是池级名单、冻结路径只增（去重）；解冻走 v1.4 `unfreeze` 子命令（见下节）。

## v1.4 人工解冻（unfreeze）

- 用法：`python3 slime_router.py unfreeze <pool> --target T`——从池级 `frozen_targets` 移除 T，落 `unfrozen` 事件（含 `target` 与 `source: "manual"` 操作来源标注）。
- 目标不在冻结名单：报错退出码 1，且不写盘（state 与 events 均不变）。
- **解冻是人工裁决动作，需操作者确认合规依据，事件留痕即审计链。**
- **protocol 段**升 `version: "1.4"`；无其他协议字段变化，v1.3 state 读入即兼容。

## v1.5 六大升级（2026-09-09，版本冻结令作废后全速推进）

protocol version 升 `"1.5"`，新增协议字段：`provs`、`evidence_levels`（L0-L4）、`quality_srcs`、`herd_window/threshold/discount`、`cc_kinds`、`bus_direct: true`。旧 state 读入即补默认（`trail_by_prov` 三账清零、`common_cause_frozen` 布尔→对象 `{"active","kind"}`（旧 true 记 cc_supplier）、`recent_selects` 空窗）。

1. **provenance 分籍**：`report --prov real|replay|synthetic`（默认 real）。每端点 `trail_by_prov` 三本账（real/replay/synthetic 分列，fail 惩罚与全池 decay 对三本账同步同因子作用）；`status` 每端点分列输出。`select` 路由**只用 real 账**；全池 real 账皆空时降级用总账，`status` 标 `"low_real": true`。证据等级常量 L0-L4 落 protocol 段：`L0 unattributed / L1 synthetic / L2 replay / L3 real / L4 reviewed_real`。
2. **cc 双轨制**：common-cause 触发时分类——齐灭端口 platform 全部相同 → `cc_supplier`（冻结衰减 + 平台排除，即 v1.4 前行为）；platform 各异 → `cc_environment`（只冻结衰减，不做平台排除）。`status` 的 `common_cause_frozen` 改为对象 `{active, kind}`（对旧读端保持 truthy/falsy 语义：active=false 时布尔值为假）。
3. **质量权重沉积**：`report ok --quality 0-10` 可选；沉积 ×(0.5+quality/10)（quality 缺省不乘）。质量分来源 `--quality-src blind_review|auto|manual` 随 `deposit` 事件落盘（含 quality/quality_src/dep/prov）。
4. **report 内直发总线**：report 落盘后若环境变量 `SLIME_BUS_SOCK` 指向存在的 sock，经 runs_r99 slime_bus 客户端库 `publish` 把 report 事件发到 topic `<pool>.events`；整段 try/except，失败静默降级为仅文件事件，绝不阻断 report。protocol 落 `"bus_direct": true`。
5. **审计与快照**：`snapshot <pool>` 把 state 全量复制到 `state/<pool>.snap.<ts>.json`（同秒冲突自动加序号，落 `snapshot` 事件）；`rollback <pool> --to <snapfile>` 恢复（落 `rollback` 事件，缺文件抛 FileNotFoundError）。`events.jsonl` 每行附 `prev_hash` = 前行原始字节的 sha256，首行锚定 `"GENESIS"`，篡改任一行即在该行之后断链（`verify_event_chain(path)` 返回 (ok, 断链行号)）。
6. **阻尼防羊群**：select 记录每池最近 20 次选择（`recent_selects`）；某端口占比 >60% 时其本次权重 ×0.5 临时折扣并落 `damping` 事件（含 herd_share/discount）。trail² 加权保留不变；`status` 增 `"herd_risk": true/false`（占比 >60% 即 true）。

### v1.5 与批判/推演文书的对照表

| 文书指摘/推演（来源） | v1.5 机制回应 | 实证 |
|---|---|---|
| 「合成/回放流量与真实流量同账记账，证据污染路由」（retro_v13 与集群B实证对 opencv 冤案的归因讨论） | 升级1：三本账分记、路由只用 real 账、无 real 数据时 low_real 显式标注，证据等级 L0-L4 落盘 | T19（合成巨量沉积不污染路由；清空 real 账后 low_real=true 且降级总账） |
| 「common-cause 一刀切平台排除：环境性齐灭（多平台同死）被误判为供应商故障」 | 升级2：platform 同一→cc_supplier（维持排除），platform 各异→cc_environment（只冻结衰减） | T18（两分类各触发一次，kind 与衰减冻结数值均验证；cc_environment 下最近 fail 平台仍可选中） |
| 「沉积不区分回执质量，盲审高分与垃圾 ok 同权」 | 升级3：quality 0-10 → 沉积 ×(0.5+q/10)，来源标注落 deposit 事件 | T20（q=10 沉积 1.5、q=0 沉积 0.5 数值精确断言；缺省不乘；q=11 拒绝） |
| 「事件只靠文件 tail，跨进程订阅要轮询」（集群B读端实证「写读延迟」条的后续） | 升级4：SLIME_BUS_SOCK 存在即直发 `<pool>.events`，失败静默降级文件 | T24（真实 slime_bus 守护进程收到 report 事件；sock 失效 report 不受影响） |
| 「state 可被静默改写、无审计链、无后悔药」 | 升级5：snapshot/rollback 往返 + events.jsonl sha256 链式哈希（GENESIS 锚定） | T21（快照→变异→回滚逐端点复原）、T22（篡改中间行 → 断链于下一行） |
| 「trail² 加权会羊群效应，头部端口自我强化」（swarm 评估对垄断风险的推演） | 升级6：最近 20 次 select 占比 >60% → 当轮 ×0.5 阻尼 + damping 事件 + herd_risk 标志 | T23（20 连选同端口 → herd_risk=true，第 21 轮落 damping 事件，discount=0.5） |

## 自证测试

`python3 test_slime_router.py -v`（v1.5 全量 T1–T24，详见 test_results_v1.5_2026-09-09.txt）：本次运行 **24/24 PASS**。v1.5 新增 T18 cc 双轨两分类（cc_supplier/cc_environment 各触发，kind、衰减冻结、cc_environment 不排除平台均验证）、T19 prov 分账路由隔离（合成沉积不污染 real 路由、清空 real 账后 low_real=true 降级总账）、T20 质量权重数值（q=10→dep 1.5、q=0→dep 0.5、缺省不乘、quality_src 落事件、q=11 拒绝）、T21 快照回滚往返（快照后变异再回滚，trail/ok_count 逐端点复原，rollback 事件落盘）、T22 哈希链篡改检测（GENESIS 锚定；篡改第 2 行 → verify_event_chain 断链于第 3 行）、T23 阻尼触发（20 连选同端口 → herd_risk=true，次轮落 damping 事件 herd_share>0.6 discount=0.5）、T24 总线直发（真实 slime_bus 守护进程订阅收到 report 事件含 prov；sock 失效时 report 静默降级不受影响）。T1–T17 回归全过（T8/T10 的 protocol version 断言随规格升至 "1.5"，版本字段随协议升级，非行为变更；common_cause_frozen 对象化后保持 truthy/falsy 语义，T2/T15 原断言未改）。v1.4 运行记录（T1–T17 17/17 PASS，test_results_v1.4_2026-09-09.txt）：T17 freeze 后 unfreeze → `frozen_targets` 移除且落 `unfrozen` 事件（source=manual）；对不存在目标 unfreeze → 返回失败（CLI 退出码 1）且 state/events 字节级不变。T8/T10 的 protocol version 断言随规格升至 "1.4"；T1–T16 行为不变全过。v1.3 运行记录（T1–T16 16/16 PASS，test_results_v1.3_2026-09-09.txt）（Python 3.12.12）。T14 task fail 不罚 trail（仅全池 decay）、fail_rate_channel 不变、task_fail_count=1 且落 `task_fail` 事件；T15 compliance fail+`--target lii.org` → `frozen_targets` 含 lii.org（重复冻结去重、不二次落事件）、不罚 trail、不触发 common-cause；T16 默认 fail（无 --reason）与 v1.2 行为逐位一致（trail×0.5×decay、fail_count=1、fail_rate=1/5、无 v1.3 新事件）。T8/T10 的 protocol version 断言随规格升至 "1.3"（版本字段随协议升级，非行为变更）；T1–T13 行为不变全过。v1.2 运行记录（T1–T13 13/13 PASS）：T11 强制 z=1.0 后 dormant 端口被探索选中、合法返回且落 `canary` 事件（未复活前状态保持 dormant）；T12 dormant `report ok` → `revival` 事件、状态回 active、trail ≤ 活性均值×10%×1.01；T13 dormant `report fail` → 保持 dormant、below_streak 重置、无 revival。T8/T10 的 protocol version 断言随规格升至 "1.2"（版本字段随协议升级，非行为变更）；T1–T7、T9 行为不变全过。v1.1 运行记录（T1–T10 10/10 PASS）：T1 持续 fail 端口 50 轮后占比<5% 且休眠；T2 同窗 3 fail 冻结且触发批次不衰减；T3 活性<2 唤醒最低 fail_rate 端口；T4 1000 次 select 低踪迹端口命中落在 [5,60]（期望≈15）；T5 等 trail 成本差 10× 时 select 卡方 p>0.05 而效率分比=10；T6 伪造老化 ts_written → stale=true；T7 心跳写入 alive、伪造老化 → dead；T8 protocol 段存在且数值正确；T9 原子写后 state 非空可解析且 `.bak` 存在、无 tmp 残留；T10 删除 protocol/ts_written/ttl_seconds 后 status/select/report 正常且默认回填。旧版 state（state/llm.json，v0.2 格式）直接 `status` 可读：age_seconds=null、stale=true、端点数据完好（v0.2 结果存档于 test_results_2026-09-09.txt）。

## top3_likely_wrong

1. **conf 0.55** — v1.5「low_real」判定取「全池 real 账总和 ≤0」；register 的初始 1.0 踪迹记入 real 账，若规格原意是「只算 report 沉积的 real」，新注册池会被误判为有 real 数据。
2. **conf 0.50** — cc 双轨分类用「窗口内 fail 端口的 platform 集合」；同窗混入无关单平台 fail 时可能把 cc_environment 误判为 cc_supplier。
3. **conf 0.55** — common-cause「冻结期优先选不同平台」的语义：规格未定义“与谁不同”，实装取“与最近一个 fail 端口的 platform 不同”，可能只是众多合理解释之一。
2. **conf 0.45** — 解冻条件（窗口清空 + ok 到达即清除 `common_cause_frozen`）是自拟的；规格只说冻结一次 DECAY 与 status 标注，未规定何时复位。
3. **conf 0.35** — 休眠判据中“占比”按活性端口归一化（不含休眠端口踪迹）；若 v0.2 原意是全池归一化，边界情形（大量休眠踪迹残留）行为会不同。

## 红线声明

未编造数据/引文；测试结果为上文实际运行输出；未对外分发任何内容。
