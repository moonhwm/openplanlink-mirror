# 典型任务剧本

> 每个剧本第一步永远是探活。剧本里的工具名以最近一次探活清单为准。

## 剧本一：文生/图生 3D 模型（Rodin 线）

前置：Rodin OAuth 已授权（token 在环境变量，如 `RODIN_TOKEN`）。

1. `python3 scripts/probe_dcc.py --url https://api.hyper3d.com/api/mcp --token-env RODIN_TOKEN`
   确认 `endpoint_ok: true` 且 7 件工具在列。
2. 文生：`rodin_generate(prompt=...)`；图生：先 `rodin_create_uploads` → HTTP PUT
   传图 → `rodin_generate(reference_upload_ids=[...])`。
3. `rodin_wait(generation_id)` 循环至终态（单次≤45s，超时报 stage 进度，不判死）。
4. `rodin_get_result` → **只给用户 display_url**。
5. 烧前报数（credits），失败如实回传原因。

**未授权时的授权链（实测可行，2026-10-01）**：
- DCR：`POST https://api.hyper3d.com/api/grant/oauth/register`，
  redirect_uris 用 `["urn:ietf:wg:oauth:2.0:oob"]`，
  grant_types `["authorization_code","refresh_token"]`，`token_endpoint_auth_method:"none"`。
  （device_code grant 对自注册客户端**关闭**，勿试。）
- 构造 authorize URL：response_type=code + PKCE S256 + scope `rodin:generate rodin:read`
  + resource `https://api.hyper3d.com/api/mcp` + redirect_uri=oob。
- 用户浏览器打开 → 登录 Hyper3D（注意与 Tripo 开发者站是两套账户）→ 授权 →
  页面显示一次性 code → 用户贴回 → 本地用 code+verifier 换 token。
- code 一次性、短时效、绑 verifier；token 只进环境变量，零落盘。

## 剧本二：DCC 场景操作（Maya/3ds Max/Blender 线）

1. 会话内盘点：把当前可见工具名写入临时文件，
   `python3 scripts/probe_dcc.py --from-list <file>`，确认目标线的工具在列。
2. 不在列（服务器断连）→ **停止并如实报告**，给出重连路径：
   插件页重装/重授权；本地 DCC 常驻服务先启动。不得编造调用结果。
3. 在列 → 按真实 schema 调用；破坏性操作（删除、覆盖保存、批量改名）
   先列清单给用户确认再执行。

## 剧本三：格式转换/减面/绑骨链（Tripo 线）

1. `tripo_balance` 查余额，报数（这是开工闸，不是可选项）。
2. 链式：`tripo_import_model`（本地文件先导入拿资产句柄）→ `tripo_decimate`
   （面数预算先行声明；压缩比 >10:1 时考虑两步减面）→ `tripo_rig` +
   `tripo_rig_check`（如需动画）→ `tripo_animate` → **最后** `tripo_convert`
   出目标格式（GLB/FBX/OBJ/STL/USDZ/3MF）。
   convert 放最后是刻意的：保证导出文件内含骨架+动画，避免二次导出——
   用户字面顺序不同时一句话解释原因。
3. 每步 `tripo_task_wait` 到终态再进下一步；失败回传 task 原始错误。

**质检清单（每步过闸）**：
- 减面后：抽检面部/手部细节、UV 与法线是否存活、游离顶点；
- 绑骨前：确认模型 T-pose/人形直立（非人形先声明自动绑骨高风险）；
- 动画后：检查滑步、关节反向、root motion。

**降级路径（单点故障时）**：
- 配额不足/任务失败 → 减面与格式转换可降级本地 Blender/MeshLab/FBX2glTF；
  走路动画可降级 Mixamo 下载后 retarget；
- 降级动作必须显式告知用户「已离开 Tripo 线」。

## 剧本四：工程/参数化任务（SolidWorks/CAD 线）

当前两线均未接入。**正确动作**：如实声明「工程域线未接入」，列出可选：
(a) 用户在本机部署对应 MCP/插件后走剧本二协议接入；
(b) 网格域近似（必须显式标注：三角网格近似，无特征树/公差/工程图能力）；
(c) 转人工。禁止拿 Tripo/Rodin 生成的网格冒充参数化模型。

## 剧本五：视频项目配 3D 资产（与 remotion-video-forge 协同）

1. 需求拆解：哪些镜头要 3D 资产（GLB 最通用）。
2. Rodin/Tripo 出资产 → 转 GLB → 放入视频项目 `public/` → Remotion
   Three.js 场景引用。
3. 资产与视频一并 SHA3-256 封印进 manifest（封印纪律见 remotion-video-forge）。
