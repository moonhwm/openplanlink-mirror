# spec-preflight

## 目的
一键预检：把本席 MVP（DF-MVP-20261006-CAIRN-01）的七项能力压成**一条只读命令**，逐项给出判据、结果与证据，末尾给 `VERDICT=PASS/FAIL`。

## 输入/输出
- 输入：可选 `--json <path>`（机器可读结果）
- 输出：标准输出的 Markdown 表格（七行）＋ `VERDICT=` 行；可选 JSON
- 退出码：全过 0；任一 FAIL 为 1；SKIP 不阻断（视为不可判定，不计入 PASS/FAIL）

## 不变量
- **只读**：不改动仓库、不推送、不写台账；`cd_attest` 与 `license_match` 的产物一律落到系统临时目录
- 每项检查独立捕获异常：单项异常记为 FAIL 并继续，不中断整轮
- 子进程一律显式指定解释器：Python 脚本用 `sys.executable`，`.mjs` 探针用 node（曾因误用 python 跑 .mjs 产生假 FAIL）

## 失败模式
- 依赖脚本缺失 → 该项 SKIP（并打印缺失路径），不判 FAIL
- 子进程超时（默认 600s）→ 该项 FAIL
- `--json` 路径不可写 → 抛异常并以非 0 退出

## 关键函数
- run
- check_sdd
- check_license
- check_cd_attest
- check_ledger
- check_upload
- check_mcp
- check_eff_report
- main

## 验收断言
- 七项全部可跑且输出表格行数为 7
- 本机受控环境下 `VERDICT=PASS`
- 任一被检能力被人为破坏时，对应行变 FAIL 且退出码为 1（可定位性）
