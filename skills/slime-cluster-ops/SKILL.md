---
name: slime-cluster-ops
description: >
  黏菌算法（slime mould / SMA / MCPM）在 K3 集群运营中的全套应用：端口与路由选择、
  通道池管理、集群间异步协作、收缩与休眠判据、跨平台冗余。当任务涉及以下任一情景时使用：
  ①多通道/多模型/多 API 端点的路由选择与故障自动规避（如渲染炉模型池、金融数据四通道）；
  ②集群间无即时消息条件下的异步状态通信（踪迹介质/stigmergy）；
  ③通道或集群的休眠/收缩/再激活决策（S1-S5 判据）；
  ④黏菌算法本身的公式核验（SMA 三坑：log10/负分支/括号层级）与 MCPM 宇宙网复现；
  ⑤需要评估「全通道常开 vs 黏菌收缩」成本前沿的仿真。
  不用于：实时性要求毫秒级的路由（本方案为异步最终一致）；单体应用无冗余池的场景。
---

# slime-cluster-ops 黏菌集群运营

## 版本线
v0.2 基线 → v1.1 新鲜度/原子写 → v1.2 金丝雀复活 → v1.3 fail 原因分类 → v1.4 手动解冻 → v1.5 分账/质量/双轨/总线/快照/哈希链 → v1.6 → v1.6p2。

- **v1.6 哈希链尾行封存 + 修正案B补测**：`verify_event_chain` 原只校相邻 prev_hash，链尾末行被篡改不可检测；v1.6 每次 `_log` 后把链尾（末行 sha256、count、line_index）原子封存至 `<pool>.events.jsonl.tail.json`，末行哈希与封存值不符即报 `TAIL_TAMPER`（tail 文件缺失的旧账本报 stderr 提示并自动补建）。修正案B（fail_rate>10% → 休眠阈值放宽至 8%）此前零测试覆盖，T26 补齐（占比 >5%/<8% 档：highfail 休眠而 lowfail 存活；<8% 档：两者皆休眠）。自证 **T1–T26 26/26 PASS**（新增 T25 链尾篡改检测 + T26 修正案B，T1–T24 回归全过）。
- **v1.6p2 EV-2 八维审计向量**：证据从 L0–L4 一维标签拆为 claim 级八维向量（source/domain/fidelity/n/reproducibility/independence/verify_level/scope），未知一律显式填 `"unknown"`（n 填 null）；`report()` 新增可选 `ev2` 参，审计字段与路由字段平级落 events.jsonl，**绝不参与 select/score/休眠判定**。**可回滚开关 = 调用方不传 ev2 参**：零开销、零行为变化、无需改码迁账（T27a：传/不传 ev2 的 select 序列与事件流逐字节一致；T27 全量 27/27 PASS）。llm_real 单池只读试点：7 条 register 事件 source/domain 7/7，其余六维无可用元数据按原则填 unknown/null，**整格覆盖率 25.0%**；旧账本首行无 prev_hash 锚断链于 line 0，verify_level 如实落 "unknown"（覆盖率天花板受限于源账本信息量）。

## 核心心智模型（三拍）
1. **铺菌毯**：同职多通道冗余池并行接题（金融 wind/ifind/gildata/caixin、渲染炉多模型、QR 多库）。
2. **营养流观察**：调用结果即营养反馈——成功沉积踪迹（∝1/成本×1/时延）、失败半减、全池随时间衰减；ledger/broadcasts 即共享踪迹介质，零新基建。
3. **路径收缩**：低通量路径自动休眠（非删除，可再激活），成本感知只入休眠决策、不入路由分配（修正案A）。

## 快速上手：端口路由选择器
`scripts/slime_router.py`（纯标准库 CLI）：

```bash
python3 slime_router.py register <pool> <endpoint> --cost 1.0 --platform google
python3 slime_router.py select <pool>            # trail^2 加权 + 3% 探索
python3 slime_router.py report <pool> <ep> ok --latency_ms 18000 --cost_units 21.6
python3 slime_router.py report <pool> <ep> fail  # trail×0.5，事故率入休眠判据
python3 slime_router.py report <pool> <ep> fail --reason task          # 任务层不可解不罚通道；compliance 类附 --target 冻结目标
python3 slime_router.py status <pool>            # 踪迹场全量 JSON
```

调用方改造仅需两行：路由前 `select`，调用后 `report`。

判据与参数语义详见 `references/slime_router_manual.md`。

## 五条铁律（血泪教训，勿违反）
1. **成本感知只入休眠、不入路由**——路由层成本感知会过度集中撞容量上限（仿真 svc -14.3pt）。
2. **事故率必须入休眠判据**——最便宜的通道可能故障率最高，纯成本视角会误留。
3. **池内管理无法抵御平台级并发故障**——同类能力至少跨 2 个独立平台/供应商（实证：gemini+claude 双炉制，一炉通道死时另一炉兜底）。
4. **探索下限 z=0.03 不可为零**——v1.2 起探索候选集含 dormant 端口（金丝雀探测），修复的端口被探中 ok 即复活（trail=活性均值×10%，防 trail² 垄断）；零探索=永久拉黑。
5. **仿真数字只用百分比**——相对单位禁止当真实货币绝对值引用。

## 成本三杠杆（分层，缺一不可）
1. **路由层成本盲**：select 只用 trail，成本不入路由分配（铁律1不变，防过度集中撞容量上限）。
2. **休眠层成本感知**：efficiency = trail/cost 只入休眠决策（修正案A），持续低效通道被休眠。
3. **运营层直接杠杆**：配额上限、fallback_only 角色（平时零调用、仅兜底启用）、缓存 TTL、请求合并。
   此层明确借鉴熔断器范式的直接成本控制手段。评估教训：单靠休眠压不住「健康但贵」的通道——
   它既不触发事故率判据、活跃度也高于 5% 休眠线，必须用运营层杠杆直接限价限流。

## 与熔断器范式的分工（互补，非替代）
- **熔断器**管秒级快速失败与半开探测：故障即刻切断、半开状态放探测流量验证恢复，低流量场景也能恢复。
- **黏菌**管长周期经济性与休眠/复活：踪迹积累反映成本/时延/事故率的长期画像，决定收缩与再激活。
- 低流量场景单独用黏菌恢复慢（评估实证：z=0.03 的探索流量在低 QPS 下几乎到不了 dormant 端口）；
  建议探测流量由熔断器半开机制承担，黏菌以 `report` 接口接收其探测结果（ok 即触发 v1.2 revival）。

## 异步通信的边界（实证结论）
踪迹介质是**异步最终一致**，非实时：读端须检查状态新鲜度（v1.1 起 state 含 ts_written/ttl）、
集群活性靠心跳租约区分「安静」与「死亡」。毫秒级实时路由不要用本方案。
v1.1 起 state 含 `ts_written`/`ttl`/`stale` 与心跳租约（`heartbeat` 子命令），读端必须先查 stale 再决策。

## references 加载指引
| 情景 | 读 |
|---|---|
| 路由/端口选择、休眠判据实操 | slime_router_manual.md |
| 池内管路框架（三拍/D1-D4/S1-S5 原始版） | architecture_v0.1_pipeline_framework.md |
| 集群间协作、跨平台冗余立法、判据 v2 修订 | architecture_v0.2_cluster_coordination.md |
| 收缩仿真成本前沿与结论 | simulation_findings.md |
| SMA 公式实现（三坑） | evidence_sma_fgcs_verification.md |
| MCPM 宇宙网/PolyPhy 复现 | evidence_cosmic_mcpm_verification.md |

### references 增补（v1.6 同步，外部工件）

- **cold_pointer 冷层指针原型**（`/mnt/agents/output/runs_r99/cold_pointer/`，纯标准库）：指针 = {id, path, title, summary(前200字符), sha256, bytes}，原文零字节进索引；30 件语料 bench 实跑 **top-1 命中 3/3、平均压缩比 17.5x**（方案A 全量 169,393B vs 方案B 指针+回取）。**诚实局限**（bench_results_2026-09-09.md 原文）：①tf 子串匹配只命中字面重叠，同义改写/跨语言/纯语义查询会 MISS，需回退全量扫描；②summary 为机械截取前 200 字符，标题含关键词的语使命中率偏乐观；③指针本身占上下文，语料翻 100 倍且查询模糊时 B 成本可逼近甚至超过 A；④回取是串行精确读+sha256 校验，指针失效只能报 CORRUPT 重查；⑤3/3 样本量太小不可外推。
- **search 池 Retro 演示**（`/mnt/agents/output/runs_r98/slime_router/retro_search_分析_2026-09-09.md`，synthetic/replay 重放、非实时流量，seed=20260909 可复现）：5 端点检索池 **42 次 report** 四阶段战史重放；**cache_replay 终局 trail 占比 86.48%**（近零成本沉积的算术放大，业务上需调用层设混合比例上限防缓存垄断）；**browser_visit** 两次 30s channel fail 后自动**休眠**（fail_rate 0.50）；compliance fail 不罚通道且 `forbidden-crawl.example` 池级**冻结**。链校验 verify_event_chain=True（16 事件 + v1.6 尾封一致）。意外点如实记录：任务盲路由无法按任务类型分流（pdf 分流 B 阶段流量）、冷门端点需调用方喂首次成功才能复活。

## 与既有技能的接口
- 金融通道真实调用钩子骨架：runs_r98/slime_router/finance/（待台账积累校准成本参数）
- 投标场景 QR 多库池：bidding-ops 技能 §pipelines Ⅰ.6 的通道冗余即本框架实例
- 渲染炉模型池：extpool-furnace-ops 双炉制=跨平台冗余条款现成实例

## 质量红线
关键断言标 conf；不编造数据与引用；判例/仿真材料仅作合规自证与风险识别。
