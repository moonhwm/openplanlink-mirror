# 可达性判定口径（本席自课，轮55 立）

- 时点：2026-10-07 14:26（北京时间）
- 立据：同刻三层探针**互相矛盾**——`Test-NetConnection github.com:443`=**False**，而 `curl https://github.com`=**200**、`git ls-remote origin`=**成功**。

## 口径（三条）

1. **以实际操作为判据**：可达性结论须出自**目标操作本身**（`git ls-remote`／`git fetch`／`curl <目标URL>`），**不得**以 ICMP/TCP 探针（`Test-NetConnection`、ping）**否证**目标可用。
2. **探针失败 ≠ 对象不可达**：与"报告值≠核实值"互为镜像——**探针侧假阴性**须与**对象侧故障**分列。
3. **结论须带工具名与时点**：凡记"不可达／一致"，须记**所用命令、解析层、时点**（承 `DF-CONFLICT-…-RESOLUTION`：冲突多源于比对基准）。

## 适用

本席一切工具（`push_all` / `push_reconcile` / `netguard` / 侦察脚本）**均依此口径**；历史结论中仅凭探针得出的"不可达"**一律标注为"探针侧判定，待操作级复验"**。
