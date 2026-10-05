# P0 账本并发竞态修复报告

- **档号**：FIX-20261005-OPL-P0-LEDGER-RACE
- **对象**：`A:\OPL_A2A\selfevo-sdd\src\selfevo\ledger.py`
- **性质**：修根因（非症状），并以 10 轮同命令连跑作为交付证据
- **commit**：`a18cf53bf2676637ebcd712fabb716112efb4036`（短 hash `a18cf53`）

---

## 〇、复现证据（修复前失败率，含每轮实际计数）

**关键事实须前置说明：本席在修复前未能复现出失败。** 这不是取证缺失，而是
如实报告——见下表。

### 0.1 修复前基线 10 轮（同一条命令，顺序执行）

命令：`python -X utf8 -m unittest discover -s tests`（cwd = 仓库根）

| 轮次 | FAIL | ERR | tests | 结论 |
|---|---|---|---|---|
| 01 | 0 | 0 | 155 | OK |
| 02 | 0 | 0 | 155 | OK |
| 03 | 0 | 0 | 155 | OK |
| 04 | 0 | 0 | 155 | OK |
| 05 | 0 | 0 | 155 | OK |
| 06 | 0 | 0 | 155 | OK |
| 07 | 0 | 0 | 155 | OK |
| 08 | 0 | 0 | 155 | OK |
| 09 | 0 | 0 | 155 | OK |
| 10 | 0 | 0 | 155 | OK |

**修复前实测失败率 = 0/10（0%）**。

### 0.2 为逼近间歇性而做的加压复现（全部修复前执行）

| 手段 | 参数 | 结果 |
|---|---|---|
| 3 套全量用例**并行**连跑 | 3 并行 × 3 轮 = 9 次套件 | 9/9 全绿，0 FAIL / 0 ERR |
| 跨进程台账完整性压测 | 8 进程 × 12 次 = 96 次 append | 96/96 成功，96 行 seq 连续、无半行 |
| 锁获取对抗探针 | 12 进程 × 15 轮 = 180 次 | 180/180 成功，最大延迟 0.014s |
| 同路径首触锁探针（真正争用同一文件） | 8 进程 × 10 轮 = 80 次 | 80/80 成功，最大延迟 0.009s |
| 持锁等待时长测量 | 6 进程竞争，3s 持锁 | 最长等待 3.003s，**0 次**越过 30s 阈值 |

### 0.3 结论（诚实边界）

1. 任务书转述的「4 跑 2 败、最严重 `FAIL=3 ERR=44`」**本席一次未复现**。
2. 复现失败的原因有据可查：仓库中**已存在上一席的修复**
   （`FIX-20261005-HY4-01`），其 `_open_lock_file()` 用 30s/5ms 盲重试
   兜住了 Windows 创建争用。该重试**掩盖了症状**，使失败不再外显——
   这正是本席要处理的问题：不是「测试不稳」，而是**协议本身仍有缺陷**。
3. 因此本席的定性**不依赖复现失败**，而依赖**代码级证明**（见第一节）：
   三处缺陷在代码中客观存在，其中 W2/W3 与 `ERR` 形态直接相关。
   修复属「消除隐患」，不是「掩盖已观测现象」——此点请主理人知悉。

> 一处需澄清的口径：任务书称「修复前 2/4 败」。本席的 0/10 与之不一致。
> 两者都如实记录在案。差异的可能来源（**均为推测，未验证**）：
> 验证席复跑时点上席修复尚未落盘、或两席使用了不同解释器/工作副本。
> 本席**未**验证这一推测。

---

## 一、根因分析（精确到文件:行号）

修复前三处缺陷（行号指**修复前**的 `ledger.py`）：

### W1 · 锁文件创建非原子（`ledger.py:97`）

```python
return os.open(str(path),os.O_RDWR|os.O_CREAT,0o600)   # 缺 O_EXCL
```

`O_CREAT` 不带 `O_EXCL` 时，「创建锁文件」这一步没有原子仲裁者：N 个进程
首次并发创建同一 `.lock`，Windows 上 `CreateFile` 的**创建-打开交接**存在
瞬时争用，失败者得 `PermissionError(Errno 13)`。原修复用**盲重试**兜住。

**窗口如何形成**：进程 P1 已 `O_CREAT` 建出 `.lock` 但尚未 `LockFile`；
P2 此刻 `os.open` 同一路径，Windows 判定「文件正被创建/打开」而拒绝。
原代码把「协议缺陷」降级为「重试一下就好」。

### W2 · 取锁预算被拆成两段，最坏 60s（`ledger.py:88` + `ledger.py:133`）

```python
_OPEN_RETRY_DEADLINE=30.0          # 开锁阶段预算
...
deadline=_time.monotonic()+30.0    # 自旋阶段预算（另一份！）
```

两段预算**各自独立计时**，取锁全过程最坏 **30s + 30s = 60s**。
而跨进程用例在 **30s** 处放弃子进程：

- `tests/unit/test_ledger.py:170` — `process.communicate(timeout=30)`
- `tests/unit/test_idempotency.py:177` — `worker.communicate(timeout=30)`

一旦某次争用使子进程取锁耗时越过 30s，父进程抛
`subprocess.TimeoutExpired` → 该用例 **ERROR**。这与观测到的
`ERR=44`（**量级远大于单点失败**，符合「一批用例被系统性拖超时」的特征）
高度吻合。

**预算是「一个」语义，不该是两段相加。** 这是本席认定的**主根因**。

### W3 · POSIX 分支无限等待（`ledger.py:145`）

```python
fcntl.flock(lock.fileno(),fcntl.LOCK_EX)    # 无截止
```

`LOCK_EX` 阻塞且**无超时预算**。持锁进程若崩溃/死锁，第二个进程**永久挂起**：
既不超时、也不 fail-closed。Windows 分支已用 `LK_NBLCK` 自旋（受约束），
POSIX 分支却无——两条分支**语义不对称**。

### 为何「锁不是数据损坏的根因」

诊断明确：既有缺陷属**可用性缺陷**，非幂等/完整性缺陷——去重始终正确。
W1 抛错、W2 超时、W3 挂起，三者都**不会**写出半行或粘连行（写路径
`ledger.py:244-247` 已 `flush()+fsync` 且全程在临界区内）。
故本席定性为：**该 P0 是可用性/可复现性缺陷，不是「审计链已被写坏」**。
此区分重要：不应夸大，但按宪法第四条，间歇性不可复现同样不可接受。

---

## 二、修复方案与实现说明

### 2.1 改动清单（唯一文件：`src/selfevo/ledger.py`）

| 位置 | 改动 |
|---|---|
| `:8` | 新增 `import errno`（标准库） |
| `:83-108` | 新增锁协议常量 `_LOCK_TIMEOUT=30.0` / `_LOCK_POLL_INTERVAL=0.005` / `_OPEN_RETRY_INTERVAL=0.005`，并以注释固化三处竞态窗口的成因 |
| `:111-112` | 新增 `class LockTimeout(LedgerError)` |
| `:115-144` | 重写 `_open_lock_file(path,deadline)`：`O_EXCL` 原子创建 + 已存在则直接开 |
| `:159-196` | 重写 `_locked()`：单一 deadline 贯穿全过程；POSIX 改 `LOCK_EX\|LOCK_NB` 纳入同一预算；锁字节落盘补 `fsync` |

### 2.2 为什么这个方案是原子的

- **创建原子**：`O_CREAT|O_EXCL` 由内核保证「N 个创建者恰 1 个成功」。
  首次创建不再依赖事后重试去补窗口 → W1 消除。
- **已存在则直开**：这是本席**踩过一次坑**才写对的第二段语义。
  `O_EXCL` 在文件已存在时**永远失败**，若不退回 `O_RDWR|O_CREAT`，
  第二个进程起必然 `LockTimeout`（实测 `got_rows=1 / LockTimeout × 34`，
  已在修复过程中发现并改正，见 §2.4）。
- **互斥原子**：`msvcrt.locking`(Windows) / `flock`(POSIX) 为内核字节级锁，
  跨进程有效；本席**未**依赖「先删锁文件再建」这类依赖删除的方案
  （既撞沙箱 safe-delete 守卫，本身也不是正确并发修法）。
- **预算原子（单一语义）**：`deadline=time.monotonic()+_LOCK_TIMEOUT` 在
  `_locked()` 入口**只算一次**，同时传入 `_open_lock_file` 与两处自旋。
  取锁全过程最坏 **30s**，不再 60s → W2 消除。
- **POSIX 有界**：`LOCK_EX|LOCK_NB` + 同一 deadline 自旋，语义与 Windows
  分支对齐 → W3 消除。

### 2.3 逐条对照任务六项约束

| # | 约束 | 落实 |
|---|---|---|
| 1 | 锁获取原子 | `O_CREAT\|O_EXCL` 创建 + 内核字节锁；不依赖删除 |
| 2 | 超时与降级，**不无限等待、不静默跳过** | 单一 30s 预算覆盖全过程；超时抛 `LockTimeout`（`LedgerError` 子类）= **fail-closed**。宪法精神：锁只用于串行化临界区，**绝不用于把失败变成成功**——静默跳过会让两条记录拿到同一 seq，直接写出不可复现的坏链 |
| 3 | append-only 语义不被竞态破坏 | 读—改—写全程在临界区内；写路径保持 `flush()+fsync`；锁字节落盘亦补 `fsync`；`_read()` 的严格校验（半行/断链即抛）**未放宽一字** |
| 4 | 无第三方依赖 | 仅标准库：新增 `errno`；`msvcrt`/`fcntl` 为条件导入。**AC-8 满足** |
| 5 | 不违反凭据零字面量 | 未引入任何密钥/键值；提交前 pre-commit 门禁 `✅ 凭据扫描 PASS`（详见第五节） |
| 6 | 保持 API 兼容 | **未改任何公开签名**。`append/append_once/checkpoint/read_verified/verify` 全部原样；仅新增 `LockTimeout`（`LedgerError` 子类，**旧代码 `except LedgerError` 仍能捕获**）。已 grep 全部调用方确认（见下） |

### 2.4 修复过程中我自己引入并纠正的一次回归（如实记录）

首版 `_open_lock_file` 只写 `O_EXCL` 未写「已存在则直开」的第二段，
导致压测出现 `LockTimeout` × 34、`got_rows=1`（48 应有）。定位为
**自身缺陷**（非环境问题），补上第二段语义后复测
`6 进程 × 8 次 = 48/48 全绿`。**记录此点是因为它证明本次修复经过了
实测检验，而非仅凭推理。**

---

## 三、10 轮复跑结果（逐轮列出，不省略）

命令与修复前**完全相同**：`python -X utf8 -m unittest discover -s tests`
（cwd = `A:\OPL_A2A\selfevo-sdd`），解释器 `3.13.12`（managed）

| 轮次 | rc | FAIL | ERR | tests | 结论 |
|---|---|---|---|---|---|
| 01 | 0 | **0** | **0** | 155 | OK (skipped=4) |
| 02 | 0 | **0** | **0** | 155 | OK (skipped=4) |
| 03 | 0 | **0** | **0** | 155 | OK (skipped=4) |
| 04 | 0 | **0** | **0** | 155 | OK (skipped=4) |
| 05 | 0 | **0** | **0** | 155 | OK (skipped=4) |
| 06 | 0 | **0** | **0** | 155 | OK (skipped=4) |
| 07 | 0 | **0** | **0** | 155 | OK (skipped=4) |
| 08 | 0 | **0** | **0** | 155 | OK (skipped=4) |
| 09 | 0 | **0** | **0** | 155 | OK (skipped=4) |
| 10 | 0 | **0** | **0** | 155 | OK (skipped=4) |

**判据：10/10 轮全部 0 FAIL / 0 ERR —— 达成。**

未放宽判据、未加 retry 掩盖、未只报最好一轮；原始日志落盘于
`.racefix/after_round01..10.log` 与 `.racefix/after_summary.txt` 可复核。

### 附加压测（修复后，同一压力口径）

| 手段 | 结果 |
|---|---|
| 6 进程 × 8 次跨进程 append | 48/48 成功，48 行 seq 连续、**无半行/粘连/丢记录** |
| 单测定向回归（ledger + idempotency） | 41 tests **OK** |

---

## 四、回归确认（对抗性负对照）

定向复跑 `tests.unit.test_ledger` + `tests.unit.test_idempotency`：
**41 tests OK**。关键负对照逐条确认**仍通过**（未被修复破坏）：

| 判据 | 对应用例 | 结果 |
|---|---|---|
| **禁止静默回落**（异常须 fail-closed 为 BLOCK，不得当成功） | `test_incomplete_row_is_not_silently_repaired`（半行不自动修） | ok |
| 同上 | `test_internal_deletion_rejected`（内部删行必被拒） | ok |
| 同上 | `test_payload_tamper_detected` / `test_wrong_key_is_rejected` | ok |
| 同上 | `test_duplicate_keys_rejected` / `test_non_finite_payload_rejected_before_write` | ok |
| 同上 | `test_partial_tail_is_refused_without_repair` | ok |
| **异常须 fail-closed**（不返回半成品） | `test_short_key_rejected` / `test_unknown_or_forward_correction_rejected_without_write` | ok |
| **异常须 fail-closed**（授权吊销即拒，绝不静默放行） | `test_auth_revoked_even_for_persisted_event` | ok |
| **负对照须返回 INCOMPARABLE**（负对照语义） | `test_malformed_inputs_are_incomparable_not_raise` | ok（属 `test_ooxml_meta`，全量 10/10 绿即覆盖） |
| 同上 | `test_compare_name_set_mismatch_is_incomparable` / `test_missing_name_field_is_incomparable` | ok |
| **凭据零字面量**（异常内容不进台账） | `test_auth_exception_content_is_not_exposed` / `test_exception_message_and_source_lines_do_not_enter_audit` | ok |
| 幂等收敛（同一事件只记一次） | `test_processes_repeat_same_event_from_absent_lock_file`（4 进程 × 4 次） | ok |
| 跨进程序列化（12 行 seq 连续） | `test_separate_process_writers_are_serialized`（3 进程 × 4 次） | ok |
| 并发只记一条（24 线程） | `test_concurrent_delivery_produces_one_record` | ok |
| 密钥扫描门禁 | `test_tier1_hit_fails_closed_and_json_survives` / `test_missing_target_is_not_a_silent_pass` | ok |

**关于 AC-3/AC-4/AC-6 的对应说明**：AC-3（禁止静默回落）与 AC-4（负对照
INCOMPARABLE）的用例位于 `tests/unit/test_ooxml_meta.py`，AC-6（异常
fail-closed 为 BLOCK）分布于 `test_ledger/test_idempotency/test_secretscan`。
本次修复**只改 `ledger.py` 的取锁协议**，未触碰任何判据、阈值与 INCOMPARABLE
判定逻辑；上述 155 项全量 10/10 绿即为覆盖证据。

---

## 五、git 提交信息与 commit hash

```
IMPL-20261005-SELFVO-FIX-LEDGER-RACE: ledger.py 锁原子化 + 10轮复跑0失败
```

- **commit hash**：`a18cf53bf2676637ebcd712fabb716112efb4036`
- **短 hash**：`a18cf53`
- **分支**：`master`
- **变更**：`1 file changed, 330 insertions(+)`（`ledger.py` 为**新增入库**，
  此前从未纳入版本管理 —— 详见第六节）
- **提交前密钥扫描**：两道均 PASS
  1. 人工正则扫描 `git diff --cached`（SK 类前缀 / AKIA / Bearer / PEM / hex64 / URL 凭据
     六类）→ **0 命中**
  2. 仓库 pre-commit 门禁 → `🔒 [pre-commit] 凭据零字面量门禁 —— 扫描 1 个
     暂存文件 / ✅ 凭据扫描 PASS`
- **入库范围纪律**：仅 `git add src/selfevo/ledger.py` 一个文件，
  `git diff --cached --name-status` 确认为 `A src/selfevo/ledger.py`，
  未夹带任何无关文件。

---

## 六、仍未入 git 的文件清单

**重要发现：`src/selfevo/ledger.py` 此前亦为 untracked**——即上一席的
HY4-01 修复**从未进入版本控制**。这意味着除本次提交外，整个
`src/selfevo/` 核心实现目前**不在 git 管辖内**，属责任边界上的重大缺口，
请主理人决策。

### 6.1 未跟踪 `.py`（9 个，均在 `src/selfevo/`）

| 文件 | 备注 |
|---|---|
| `src/selfevo/__init__.py` | 包声明 |
| `src/selfevo/busadapter.py` | A2A 总线适配 |
| `src/selfevo/deadletter.py` | 死信（依赖 `ledger.Ledger`） |
| `src/selfevo/envelope.py` | 信封 |
| `src/selfevo/hashing.py` | **被 ledger 依赖**（`chain_mac`/`get_hmac_key`） |
| `src/selfevo/idempotency.py` | 幂等（依赖 `ledger`） |
| `src/selfevo/identity_sha3.py` | 身份 |
| `src/selfevo/ooxml_meta.py` | OOXML 门禁 |
| `src/selfevo/policy.py` | 重试策略 |

> 任务书称「11 个未入 git 的 .py」。本席实测为 **9 个**（`ledger.py` 已由本次
> 提交入库，故 10 - 1 = 9）。差异原因**未验证**，可能是任务书统计时刻不同。
> 如实报告实测值。

### 6.2 未跟踪其他（11 项）

`%SystemDrive%/`、`.racefix/`、`.tmptest/`、`evidence/`、`handshake/`、
`tests/`、`specs/001-self-evolving-a2a/evidence/`、
`specs/002-ooxml-meta-traceability/`、以及 3 个档期 Markdown
（`FINDING-20261005-HY4-01`、`FIX-20261005-HY4-01`、`DF-INCR-2026-1005-HY4-02`）。

其中 `.racefix/` 是**本席新建**的取证脚本与日志目录（10 轮原始日志在此，
可复核）。`%SystemDrive%/` 为 Windows 缓存路径被当字面量展开产生的**污染目录**
（内含 `ProgramData/Microsoft/Windows/Caches/*.db`），**建议清理**，但按沙箱
铁律本席未执行删除。

### 6.3 已跟踪但有未提交改动（2 个，非本席责任）

`specs/001-self-evolving-a2a/tasks.md`、`src/selfevo/secretscan/scan.py`
—— 属其他席位在制品，本席**未触碰**，留待主理人处置。

---

## 七、遗留风险

1. **本席未能复现原始失败（最高优先诚实声明）**。修复前 10 轮 + 9 次并行
   压测 + 180/96/80 次专项压测全绿。因此本次修复的性质是
   **「依代码证明消除隐患」**，而非**「依观测证据闭合已复现故障」**。
   10/10 绿**不能**反向证明「原 `ERR=44` 必由 W1/W2/W3 引起」——
   那是**推断**，非实测。请主理人据此校准对本修复的置信度。
2. **W2 与 `ERR=44` 的关联是形态学推断**，非因果实测。依据是
   「44 个 ERROR 的量级符合『一批用例被系统性拖超时』」，
   未取得「某轮确实在 30s 处 TimeoutExpired」的失败日志。**属推测**。
3. **POSIX 分支未实测**。本机为 Windows，`fcntl.flock` 分支代码路径
   **完全未被执行**。W3 的修复属静态审查结论，需在 Linux/macOS 复测一次。
4. **`_LOCK_TIMEOUT=30.0` 的标定无实测基线**。沿用既有 `LK_NBLCK` 自旋的
   30s 口径以保持一致，但**未**实测真实部署（并发度 >> 8）下的合理值。
   若 30s 仍不可得锁，应作独立缺陷另行登记，**不得**简单调大此值了事。
   另注：本席已把它从「两段各 30s」收敛为「全过程 30s」，此改动**缩短**了
   最坏等待（60s → 30s），不会加剧超时风险。
5. **沙箱未改变并发时序**这一点本身**未被独立证明**；本席所有压测均在沙箱
   上下文内执行。压测脚本已按记忆铁律让子进程**落盘**结果、由父进程回读，
   未依赖管道回传（避免首版压力脚本的 stdout 空串误判教训）。
6. `LockTimeout` 为**新增**异常类。旧调用方 `except LedgerError` 兼容，
   但若下游有**按具体异常类型**分支的代码（本席已 grep 仓库内调用方，
   未发现），需复核。仓库外的下游消费者不在本次可见范围内。

---

## 附：取证脚本清单（本席新建，`.racefix/`）

| 脚本 | 用途 |
|---|---|
| `run_rounds.py` | N 轮全量套件连跑，逐轮记录 FAIL/ERR |
| `stress_integrity.py` | 跨进程 append 压测 + **seq 连续性/半行完整性校验** |
| `probe_lock.py` | 锁获取异常类逃逸探针 |
| `probe_firsttouch.py` | **同路径**首触锁争用探针（真争用） |
| `repro_contention.py` | 多套并行压测 |
| `probe_deadline.py` | 取锁等待时长测量（验证 W2 预算叠加） |
| `probe_exc_class.py` | winerror→异常类映射探测（**未得出结论**，见遗留风险 1） |

`probe_exc_class.py` 未能给出确定结论（ctypes `restype` 截断导致探测失效），
故**未**据其下判断。该脚本保留在案以示「已尝试且失败」，不充作证据。
