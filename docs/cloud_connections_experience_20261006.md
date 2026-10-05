# WPS、Supabase 与 ima 接入使用记录

本轮取得三个平台的实际读取结果。WPS 通过已安装的官方 CLI 提供 stdio MCP；Supabase 使用官方托管 MCP 与 OAuth；ima 使用官方技能 1.1.10，并由自主实现的只读 stdio 适配器提供五项查询工具。各平台的配置、授权、正文读取、云端写入分别留痕。

WPS 云入口文件是指针，不能当作正文。云端文件 ID 已由独立基本信息请求核验；本轮遇到名称由“A2A”调整为“Agent to Agent”的情况，旧入口与新入口字节一致，保留旧快照并另记名称变化。正文导出成功，其他四份文档及文档库读取返回 403。对不可读取、缓存候选和原生格式候选均明确记录其验证边界。

ima 官方接口的实际知识库字段为 kb_id/kb_name；只按文档示例中的 id/name 解析，会产生“请求成功但名称为空”的假象。适配器兼容实际字段，取回两知识库及项目资料。下载原件时，访问信息只留在内存中，完整 DOCX 经 DPAPI 加密保存，派生正文遮蔽已知凭据形态。云原件与本地当前版本存在差异，不能互相替代。

Supabase 读取确认两个项目均健康，public 表结构分别有 19 与 17 张表。现有协作通道、广播、语义锚点与租约表可作为后续接入的基础。普通 SELECT 验证事务只读；发现的 RLS 缺口作为单独的修复事项登记，不能在“已接入”的表述中隐去。

Neon 的只读参数是 readonly=true，Supabase 使用 read_only=true。二者均采用供应商官方 OAuth；用户无需在聊天中发送 API Key。Neon 本轮等待授权回调超时，仍只记录为已配置。

代码外发仅包含自主实现与本规范；ima 官方原包安装在本机，未将其捆绑进公开仓库。重试产生新回执，保留旧失败证据。协作报告发布与其他席位签收分别记账，避免把目录复制或共享库活跃时间当作网络握手。

参考：[Supabase 官方 MCP](https://supabase.com/docs/guides/ai-tools/mcp)、[ima 官方 Agent 接入](https://ima.qq.com/agent-interface)、[Neon 官方 MCP 更新](https://neon.com/blog/give-your-agent-neon-tools)。
