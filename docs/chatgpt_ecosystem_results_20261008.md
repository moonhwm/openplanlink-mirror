# ChatGPT 生态成果索引

本索引整理现有分支成果与本次修复。各项历史验证的时间和范围以对应记录为准；插件安装、文档存在、数据库活动时间不等同于当前授权或独立签收。

| 成果 | 入口 | 验收范围 |
| --- | --- | --- |
| 有界云读取 | [SDD 011](../specs/011-cloud-reader-integration/spec.md) | 接口与历史读取；当前权限须回读 |
| A2A 节点发现 | [SDD 012](../specs/012-a2a-discovery/spec.md) | 发现边界与测试；认证、签收另验 |
| 夜间排期候选 | [SDD 013](../specs/013-night-scheduling/spec.md) | 前提证据约束建议；不证明云执行 |
| 内存采样修复 | [SDD 014](../specs/014-memory-sample-validity/spec.md) | 缺失不报安全，异常与有效零值区分 |
| 功能角色候选 | [人设说明](persona/initial-functional-persona.md) | 授名、身份登记、独立席位同意分别待证 |

## 本次新增

[只读内存工具](../tools/memory_sample_audit.py) 与 [回归测试](../tests/test_memory_sample_audit.py) 保留采样失败类别和时间，验证原始 KiB，输出严格 JSON。6 个测试方法覆盖 20 个输入场景，通过模拟采样验证；不把测试当实际设备或云性能测量。
派生自本仓库提交 f9d1380e85c3714fed327035da39e499621e1261 的 deliverables/20261007/seat-cairn/tools/mem_audit.py；原始文件 SHA-256 为 d2e03757478156136666e9ee16df2118daa79ba3bff8099dd0fc331f0c1b5971。

## 边界

WPS 原生格式、云 ACL、完整历史与元数据无损逐项待验。Supabase 保持只读，本次发布不宣称登录已恢复；Neon、百度取得新授权证据再读。节点签收、MFA、主控台/SOC 和华为云有效作业各需真实回执。HMAC/SHA3 不能代替后量子验收，本地副本不能代替云同步。
公开包仅含代码、测试、规格和整理经验，不含用户原件、凭据、私有备份或供应商技能原包。

Windows 用法：python tools/memory_sample_audit.py --out-dir <私有输出目录>。报告含进程信息，应留在私有目录。阈值不是获批政策，累计 CPU 时间低不能证明当前闲置；工具不停止进程或修改配置。
