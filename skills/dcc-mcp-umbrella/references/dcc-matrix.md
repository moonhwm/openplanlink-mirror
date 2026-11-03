# 七线对比矩阵与排错速查

> 事实纪律：本文件只记录**实测过**的内容；「未见/预留位」的线不预填任何
> 工具签名。实测日期随条目标注，端点漂移时必须更新。

## 一、线 × 域总览

| 线 | 域 | 接入形态 | 授权 | 当前状态（2026-10-02 基线） |
|---|---|---|---|---|
| Maya | 网格/动画 | 插件 MCP（服务器名 `maya`，工具名 `mcp__plugin-<id>_maya__*`） | 插件安装 + 本地 Maya 常驻服务 | 已注册；服务器间歇断连，断连期工具不可用 |
| 3ds Max | 网格/动画 | 预留位 | 同 DCC 规程 | 未见注册 |
| Blender | 网格/动画 | 社区 MCP（已知开源项目 blender-mcp 形态：Blender 插件 + 本地 Socket；以实际部署为准） | 本地连接 | 未见注册 |
| Rodin (Hyper3D) | 网格/动画（AI 生成） | 远端 MCP `https://api.hyper3d.com/api/mcp` | OAuth：授权服务器 `https://api.hyper3d.com/api/grant/oauth`，scopes `rodin:generate rodin:read`，PKCE S256；device_code 仅官方客户端开放，自注册客户端走 authorization_code | 端点漂移记录：2026-09-23 initialize 免鉴 → 2026-10-01 initialize 亦 401 |
| Tripo | 网格/动画（AI 生成） | 插件 MCP + agent-gw | `TRIPO_API_KEY` 环境变量 | 24 件 `tripo_*` 工具在册，可用 |
| SolidWorks | 工程/参数化 | 预留位 | 以实际部署为准 | 未见注册；未见知名官方 MCP |
| CAD（AutoCAD 等） | 工程/参数化 | 预留位 | 以实际部署为准 | 未见注册；未见知名官方 MCP |

## 二、已知工具清单（实测锚点）

### Rodin 线（7 件，2026-09-23 tools/list 定谳）
`rodin_create_uploads`（1–5 图预签 PUT 上传位）/ `rodin_import_images`（仅 ChatGPT
附件场景）/ `rodin_generate`（文生/图生 Gen-2.5，烧 credits）/ `rodin_generate_bang`
（后置拆件，asset_id=已完成 generation_id）/ `rodin_get_status` / `rodin_wait`
（单次≤45s，超时≠失败）/ `rodin_get_result`（只展示 display_url，永不暴露
files[].url 临时签名链）。
调用链：generate → wait（循环）→ get_result；超时**不自动重试**，先查 Hyper3D Mine。

### Tripo 线（24 件，会话工具表在册）
生成：`tripo_text_to_3d` / `tripo_image_to_3d` / `tripo_multiview_to_3d` /
`tripo_image_to_splat` / `tripo_generate_image`
资产处理：`tripo_convert` / `tripo_decimate` / `tripo_segment` /
`tripo_smart_segment` / `tripo_mesh_complete` / `tripo_mesh_edit` /
`tripo_texture` / `tripo_rig` / `tripo_rig_check` / `tripo_animate`
多视图与导入：`tripo_image_to_multiview` / `tripo_edit_multiview` /
`tripo_import_model` / `tripo_upload_image` / `tripo_upload_ticket`
任务管理：`tripo_task_list` / `tripo_task_status` / `tripo_task_wait` /
`tripo_plan` / `tripo_usage` / `tripo_balance`
调用链：生成 → `tripo_task_wait` → 产物 GLB/FBX/OBJ/STL/USDZ/3MF；
烧前 `tripo_balance` 查余额。

### Maya / 3ds Max / Blender / SolidWorks / CAD
**未探活，不预填**。接入后第一件事：跑 `probe_dcc.py --from-list` 或端点
探活，把真实清单回填到本节并标注日期。

## 三、排错速查

| 症状 | 判定 | 处置 |
|---|---|---|
| `mcp__plugin-*` 工具全体消失 | 插件 MCP 服务器断连（系统会有故障通知） | 提示用户重连/重授权；**期间不得假装调用** |
| 远端 MCP initialize 401 | 未授权或 token 过期 | 走 OAuth 授权链接（浏览器）；Rodin 授权构造法见 playbooks |
| device_code 注册被拒 | `Device Flow is not enabled for this client` | 自注册客户端改用 authorization_code + oob redirect |
| 生成超时 | 任务可能已在队列 | 查任务列表（tripo_task_list / Hyper3D Mine），不盲目重发 |
| 工程域需求进了网格域 | 数据模型错配 | 停止，如实声明精度损失风险，等工程域线接入或转人工 |

## 四、新线接入规程（七线之外再加线时）

1. 确认接入形态（插件 MCP / 远端 MCP / 本地 Socket），登记进 REGISTRY。
2. 探活拿真实工具清单，回填第二节，标注日期。
3. 写清授权链路与凭据纪律（key 只进环境变量）。
4. 在 SKILL.md 任务词汇表补一行路由。
5. 跑一轮脚本自测：`probe_dcc.py --self-test`。
