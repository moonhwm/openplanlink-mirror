# Tripo 中国区 Studio API 备忘表（2026-09-09/10 实跑实证）

> 本表全部条目来自端到端实跑（含前端 JS 解码与错误码踩坑）。凭据本体永不入档；cookie/JWT 经 vault 与环境变量取用，显示掩码（头 6…尾 4）。

## §1 域名与认证体系

| 域 | 用途 |
|---|---|
| `auth-cn.tripo3d.com` | Ory Kratos 登录流（浏览器流 + 短信验证码） |
| `api-cn.tripo3d.com` | Studio API（Bearer JWT + Origin/Referer `studio.tripo3d.com`） |
| `msapi.tripo3d.com` | 钱包微服务 RPC |

- 会话 cookie：`ory_kratos_session`（domain `.tripo3d.com`），持久化于 `/mnt/agents/upload/vault/tripo_external_seat.json`（用户指定主份）+ `~/.kimi/external_seat.json`（镜像，易失）。
- JWT：`GET {auth}/sessions/whoami?tokenize_as=default_jwt` → ES256，**10 分钟过期**；每批调用前重取（`tripo_jwt > jwt.txt` 模式）。

## §2 登录流（逐步，全部必需）

1. `GET /self-service/login/browser` —— 带 cookie jar；从响应/跳转取 flow id。
2. `GET /self-service/login/flows?id={flow_id}` —— 取 `csrf_token`。
3. `POST /self-service/login?flow={flow_id}` —— **必带头 `Accept: application/json`**（缺则 303 空体重定向，无报错信息）；body：`method=code`、`identifier=+86<手机号>`、csrf_token → 触发短信。
4. 再 POST 同端点，`method=code` + `code=<6 位验证码>` → 得 `ory_kratos_session`。
5. 坑：验证码 6 位（4 位必拒）；旧码报「invalid or already been used」——只认最新一条；重发验证码 = 新 flow id，旧 flow 作废。

## §3 Studio 资产与进度端点

| 操作 | 方法与路径 | 要点 |
|---|---|---|
| 资产列表 | `GET /v2/studio/assets/v2?asset_type=mine&type=all` | 结构：`data.projects[].id / project_name / operator{model_version, is_textured, is_rigged, rigging{model_url, type}, text_to_model{...params}}`；**只示每项目最新 operator**，导出类 operator 不在此列 |
| 进度 | `POST /v2/studio/progress` body `{"ids":[...]}` | 轮询任务状态 |
| 下载 | `POST /v2/studio/operation/download_with_name` body `{file_name, operator_id}` | 返签名 `model_url`；绑定件的 `rigging.model_url` 为 meshopt 压缩 GLB |
| 预检 | `pre_rig_check` body `{model_version:<RIG版本>, project_id, rig_type?<可选hint>}` | project_id 必须**全 UUID**（短 ID 报 2022）；前端 store 默认 `v2.5-20260210` |
| 绑骨 | `rigging_model` body `{model_version:<RIG模型版本>, project_id, rig_type:<预检返回>}` | **biped=`v1.0-20240301`、生物=`v2.5-20260210`；填网格版本必报 2026**（前端 y7Qwj8-Z.js 解码真值） |

## §4 生成 / 贴图 / 重定向 / 导出参数

- **text_to_model**：`{model_version, prompt, negative_prompt, quad, smart_poly, face_limit, texture(bool 默认 false), pbr, texture_quality, texture_alignment, generate_parts, t_pose(bool), geometry_quality, symmetry}`。**默认 texture:false + t_pose:false**——可绑定贴图件须显式双 true。贴图档位实测：standard +10 / detailed +20 / extreme +30 积分。
- **texture_model**：`{model_version, project_id, texture_quality("extreme" 有实证), texture_alignment("original_image" 有实证，需 image bucket/key + part_names)}`；`"geometry"` 对齐报 2026——不可行时改走「带贴图重新生成」。
- **retarget_model**：`{animations:["preset:biped:*"], model_version:"default", project_id, rig_type:"biped"}`；白名单 96 个 `preset:biped:*`（js_Ec7637qF.js：afraid/agree/angry_01-03/basketball_shot/walk/run/idle/dance_01-06/sing_01-04/sit/swim/wave_goodbye_01-02…）；开放 API 的 `preset:walk` 形式被拒（1000）；v1.0 rig 一次一个动画；**`animate_in_place` 永不开**（社区 2026-06 勘误：v1.0 GLB retarget bake 有拧骨 bug，FBX 才对——但本端点 FBX 又 1018，故动画一律本地复合）。
- **导出（export_model）**：`{animate_in_place, animations[], bake_animation_frame, enable_bake_animation, export_vertex_colors, fbx_preset:"blender", format:"gltf", model_version:"default", name, pack_uv, pivot_to_center_bottom, project_id, texture_packaging:"embedded", texture_size}`。实测：`enable_bake_animation:true + bake_animation_frame:0` → 静态绑定姿势网格（无 skins/anims）；`enable_bake_animation:false + animations:[...]` → GLB 单体**仍无 skins/anims**；`format:"fbx"` → 1018 Not implemented。

## §5 operator / 项目标识管理

- 项目（8+2 例，脱敏结构）：`data.projects[].id` 为全 UUID；资产卡片字段含 `operator{model_version, is_textured, is_rigged, rigging{...}}`——**生成参数可在 operator 记录的 `text_to_model` 块回溯**（「gen1 意外未贴图」即由此查明默认 texture:false）。
- 每类 operator（gen/rigging/retarget/export）各有独立 UUID；下载须持对应 operator_id。
- 并发：starter 档 6105 并发上限 + 12003 项目级锁——串行后台轮询脚本（45–60s 间隔）实证可用。

## §6 钱包 RPC 与台账

- 查询：`POST https://msapi.tripo3d.com/ms/web/api`，头 `Authorization: Bearer <JWT>` + `X-Micro-Method: /tripo.subscription.api.assets.AssetsApi/GetAssets` → `{"credit":{"availableCredits":"480",...}}`。
- 台账约定：每次会话开场查一次、每笔烧后回填；实测费率：gen2+rigging=45、retarget≈10（计费不明时如实标「未证实」）、export=5/次、失败调用（1018 等）未计费。

## §7 错误码全表

| 码 | 含义 | 处置 |
|---|---|---|
| 0 | OK | — |
| 1000 | invalid animation for rig type | 换 `preset:biped:*` 白名单形式 |
| 1002 | Authentication failed | JWT 10 分钟过期，重取即可 |
| 1004 | missing field | 报错文点名缺字段，照补 |
| 1018 | Not implemented | FBX 导出无此能，改 GLB+本地复合 |
| 2010 | insufficient credit | 呈批充值或改零积分本地方案 |
| 2022 | Project not found | 换全 UUID |
| 2026 | Submit task failed | 先查 model_version 语义（绑骨须 RIG 版本）；再查 texture 对齐方式 |
| 6105 | task parallel limitation | 串行后台轮询 |
| 12003 | per-project lock | 等待或换项目 |
