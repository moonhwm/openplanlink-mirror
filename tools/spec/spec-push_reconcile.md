# spec-push_reconcile

## 目的
双远端一致性诊断与安全修复：定位「部分推送失败」造成的 origin / gitcode 不一致，并仅在快进可行时补推落后端。

## 输入/输出
- 输入：`--repo`（默认镜像仓）、可选 `--remotes`、`--apply`（默认只诊断）
- 输出：本地 HEAD、各远端实查 HEAD、各端状态判定（一致／落后可快进／本地落后／分叉）、复核结果
- 远端真值取 `git ls-remote`，**不信任可能过期的本地跟踪引用**

## 不变量
- **全程不使用 `--force`**
- 分叉（diverged）时**不动手**，只报结论并指向 `tools/push_gate.py`
- 默认只读；写动作须显式 `--apply`
- 补推仅限快进（`is_ancestor` 为真）

## 失败模式
- 非 git 仓库或无 HEAD → 退出码 2
- 远端不可达 → 该端标「不可达」并继续诊断其余端
- 补推失败 → 打印 stderr 摘要，不重试、不改史

## 关键函数
- run
- local_head
- remote_head
- is_ancestor
- main

## 验收断言
- 三面一致时报「无需动作」且退出码 0
- 落后端在 `--apply` 下补推后复核为「一致」
- 分叉场景下**不产生任何写入**
