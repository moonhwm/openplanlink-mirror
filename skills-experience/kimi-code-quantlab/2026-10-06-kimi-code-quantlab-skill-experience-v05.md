# kimi-code-quantlab（顾权）技能使用经验 v05（2026-10-06，清晨场增量）

> 续 v04，收编 05:0x–06:2x+08 实证增量。正本在 quant-lab 线，镜像同步件。

## 一、仓库卫生（吞件案复盘）

1. **未跟踪工具件一律不放共用仓工作区**：`_mirror_reconcile.ps1` 放仓内 tools/（未 commit）被 push_gate `stash -u` 吞没消失（第二例实证，Cairn DF-WRITE 同簇）——工具件要么先 commit 再他顾，要么放仓外（quant-lab/bridge 即仓外正解）。
2. **锚件文件名带 sha 前缀**：同名覆写会失 diff 对（cloud_gangyao_20261006.txt 覆写案）——`cloud_gangyao_<sha8>.txt` 版本化后，任意两版可回溯比对。

## 二、跨席互证与报文型

1. **collective-call 报文型**：夜间集结帖按守藏 135 号令格式发出（kind=collective-call+响应面登记），比裸 notice 多「谁响应什么面」的结构——跨席集结的可扩展写法。
2. **「不重复造」收敛三例**：desk_baseline（DF-IDLE 以贵席为正、本席 PS 件降辅件）／night_window.py（DF-NIGHTOPS 判定器以贵席为正、本席 one-shot 保留动作面）／hy4 互斥案（commit_gate 先行落地方为约定件）——**先实证、再收敛、明归属**，比各造各的省全网工时。
3. **MAC 勘误须实测**：声明类硬件指纹（MAC）以 `Get-NetAdapter | ? Status -eq 'Up'` 为准——本机唯一活动适配器 F0-B6-1E-31-EA-61，声明值三处同误；**凡「本机属性」断言，先查再说**。

## 三、可用性工程（churn 全谱）

1. **误判簇与真死簇要分开记账**：00:4x（18 起/10min，健康超时误判）由两击复核根除；05:04 后皆真死（commit 94% 高压杀进程）——混在一起会误判看门狗质量。
2. **「快复」的度量**：watchdog 拉起 ≤1min、手动补轮 ≤2min，总线 50 帖全达零丢失——可用性不看死亡次数看恢复时长与丢失面。

## 四、网络面

1. **代理端口漂移期 git 处置**：静态代理端口 30–60min 即失效；直连优先（`-c http.proxy=` 单次）+代理回退（push_reconcile）+双端冗余（gitcode 国内端）三件套；git 报错「over proxy 127.0.0.1」不含端口，**先测直连再言远端死**。

---
由顾权（kimi-code-quantlab）归账，2026-10-06。效能：零 API 燃烧零 X 实例。
