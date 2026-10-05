# 实施计划

实现 `tools/night_schedule.py`，将运维窗口、供应商规则、外部回执声明检查、并发参考和输出契约分别写成纯函数。CLI 要求 `--at`，可选 `--input` 读取受限 JSON，默认输出 JSON 至 stdout，可选 `--output` 独占保存同一结果。固定北京时间偏移保证 Windows 环境不依赖额外 tzdata。

输入的 `task` 提供自己的身份、节点、实例、任务范围及必需独立席位的摘要引用。`identity`、`instance_authorization`、`node_receipt`、`standard_methods_receipt`、`peer_acknowledgements` 分开；全部是外部核验声明，程序只计算结构、匹配及有效期，不读取任何签名密钥。`qoder` 和 `holiday_calendar` 的外部证据同样不被当作账户或日历实测。

`workload` 中的 `local_samples` 与 `huawei_x_samples` 隔离；只依据两份当前、同实例、同任务scope、同workload摘要、同成果单位且有回执引用的云样本声明形成有条件的吞吐建议。CPU 和内存上限为保护协同服务及 VPN 的保守参考，不是资源占用目标。供应商规则快照单独设有限观察有效区间，早于下界或过期的计价时窗保持待核；更新须重新只读核对官方规则。

测试采用 unittest 和临时目录；调用 main 时捕获 stdout，验证 JSON 受限输出和固定错误码。真实节点、VPN、浏览器、云实例、供应商 API 及 Git 远端均不参与本组件运行。最后更新 verification 与经验记录，报告本地结果和真实云执行接口缺口。
