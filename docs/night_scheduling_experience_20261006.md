# 夜间排期组件使用经验（2026-10-06）

SDD 013 已形成可运行的标准库排期工具、规格、计划、任务与验证记录。它将北京时间运维窗口、供应商计价时窗、外部证据就绪程度和吞吐建议放在同一份受限 JSON 中。当前成果属于排期及就绪判定阶段；实际 A2A 协同、华为云 X 作业和费用验收仍未完成。

## 使用入口

```powershell
python tools/night_schedule.py --at '2026-10-06T06:30:00+08:00'
python tools/night_schedule.py --at '2026-10-06T07:30:00+08:00' --closeout-minutes 30
```

`--at` 必须有秒和显式 `Z` 或数值偏移。不使用机器本地时间。可加 `--input claims.json` 读取受限规划声明，也可加 `--output result.json` 保存新文件；文件已存在即返回错误，禁止覆写。输入最多 64 KiB，stdout 是完整受限 JSON；失败返回退出码 2 和固定错误对象，不回显文件名或原始错误。正常计算返回 0，即使就绪状态为 blocked；退出码 0 表示计算成功，不表示可执行任务。

暂行运维窗口为北京时间 23:00 至次日 08:00。默认最后 30 分钟停止扩展计划并提示保存成果和回执；具体提前量可显式调为 1—180 分钟，并始终标注为暂行参数、未取得他席批准。07:30、08:00 和午夜均有真实边界测试。

## 输入契约

| 顶层字段 | 接受的规划数据 |
|---|---|
| `task` | `scope_sha256`、`own_subject_sha256`、`node_subject_sha256`、`instance_subject_sha256`、`workload_sha256`、`units_kind` 及最多 32 个去重的 `required_peer_subject_sha256` |
| `identity`、`instance_authorization`、`node_receipt`、`standard_methods_receipt` | 各自独立的回执声明，不相互替代 |
| `peer_acknowledgements` | 各必需独立席位的回执声明列表；自己或本节点身份不作独立席位 |
| `qoder` | `account_type` 为 unknown/regular/service_account；`selected_model` 为 unspecified/Qwen3.8-Max/other；可选 `eligibility` 声明。不改变当前模型 |
| `holiday_calendar` | 日期、是否中国公共假日、source_kind 及有限验证声明。source_kind=stock_exchange 的数据不能确定供应商费率 |
| `workload` | 待处理成果单元数、当前/请求并发（1—64）、最多两份 `local_samples` 及最多两份 `huawei_x_samples` |

一份身份/授权/节点/标准方法/席位回执声明包括：`subject_sha256`、`scope_sha256`、`receipt_sha256`、`verifier_sha256`、`issued_at`、`expires_at`、`verification_status`，签名类还需 `signature_scheme`。引用必须是 64 位小写十六进制摘要，不能传入原文、密钥、用户路径、设备地址或完整下载链接。`verification_status` 仅接受 verified/unverified；`signature_scheme` 仅接受 hmac-sha256、ed25519、ecdsa-p256、ml-dsa、unknown。这里的“verified”是外部输入声明，不是本程序的验证结论。

公共假日声明不绑定任务主体，另需 source_kind、date、is_public_holiday、receipt_sha256、verifier_sha256、issued_at、expires_at、verification_status。UTC 工作日高峰时段内无当前供应商公共假日声明时输出 unknown；其余时段的 documented_offpeak 只是官方规则与明确时间的匹配，不表示账户账单实测。

每份样本可用字段为：observed_at、expires_at、instance_sha256、scope_sha256、workload_sha256、units_kind、execution_receipt_sha256、verifier_sha256、verification_status、concurrency、completed_units、failed_units、elapsed_seconds、p95_latency_seconds、cpu_utilization_percent、memory_utilization_percent、healthy。云样本用于候选建议时需要全部字段、正成果数、正耗时、当前有效期以及当前 task 的实例、范围、负载摘要和单位绑定。units_kind 仅接受 completed_artifacts/processed_records/validated_items；不同负载、任务或单位的成果率不能比较。测试只使用合成摘要，公开文件不保存真实回执原件。

## 结果应怎样读

`prerequisites_satisfied_given_trusted_evidence` 是有前提的纯计算结果。所有结构和有效期满足时可为 true，但 `dispatch_authorized`、`eligible_for_task_dispatch`、`dispatch_performed` 均为 false；本组件不读取原始签名或可信注册表，也不调用执行器。HMAC 只在节点认证声明层被识别，不能算独立席位签名；自报 ML-DSA 不能算已验 PQC，所有输出的 PQC 与共识验证仍为 false。

并发建议先要求身份、实例授权、节点回执、标准方法验收及独立席位声明全部当前有效并匹配任务。任一缺失或失效，即使样本显示吞吐改善也保持当前并发，原因码为 `missing_current_bound_prerequisite_claims`。满足此前提后，仅在同任务、同实例、同负载摘要及同单位的云样本显示增加并发后吞吐至少提高 5%、失败率不升、P95 不超过基线 110%，且 CPU≤90%、内存≤80% 时，才输出 `consider_candidate_after_independent_verification`。上限是保护协同服务及 VPN 的暂行参考，不是占用目标；没有工作时保持空闲，不以空转或填充内存凑利用率。近收尾无条件暂停扩展。不把本机样本、输入中的数值或测试结果写成云实测。阈值用标准库 Fraction 精确比较，避免浮点除法把恰好 5% 的提升或 110% 的延迟误判为越界；派生无穷吞吐同样阻断。

华为云输出的 measurement_status 为 unmeasured，指标和执行回执为 null；verified_jobs=0 的范围严格限定为本组件发起并独立核验的云作业。实例/profile 未知不解释成空账户；未核验费用不写 0 元。

## 官方规则快照

2026-10-06 核对 [Qoder CN 官方特惠页](https://docs.qoder.cn/product-overview/qwen-3-7-series-model-staggering-discount)：Qwen3.8-Max 标准 Credits 倍率 0.5x、错峰 0.2x，相对标准四折；普通产品北京时间 22:00—08:00，Service Account 01:00—07:00。活动结束日未公布，当前账户、套餐、版本及 Credits 是否满足条件没有核实。[DeepSeek 官方定价](https://api-docs.deepseek.com/quick_start/pricing/) 的高峰为工作日 UTC 01:00—04:00 和 06:00—10:00，排除中国公共假日；低峰价为高峰一半。未把股票开市日替换成供应商日历。

规则只读核验没有调用付费接口。本次规则快照使用显式 24 小时暂行区间 `[2026-10-06T06:28:30+08:00,2026-10-07T06:28:30+08:00)`，观察下界按实际时钟回读设定，不能解释为供应商保证期。早于下界或过期时 provider_rules.rule_status 和 DeepSeek classification 均为 needs_revalidation，Qoder 当前时窗结果为 null、优惠候选 false。未来使用应重新核对供应商规则与具体账户并更新受控快照；调用者声明不能延长规则有效期。

2026-10-06 版本的 48 项本地测试及边界 CLI 检查记录在 `specs/013-night-scheduling/verification.md`；根侧和该版本独立只读复核均运行 48 项并通过。2026-10-07 修复前置声明与吞吐建议的组合缺陷，新增五类缺失、五类失效场景，当前 50 项测试由根侧及独立只读复核代理分别运行通过；独立复核另验证了 20 个失效组合及完整声明候选场景。前版 44 项的审议记录单独保留。代码审查不等于 A2A 独立席位签收。后续应接入可信验证器、实际华为云 X 执行接口，以及独立任务成果与费用回读；该组件不创建后台排期、自动化或执行 Git 推送。
