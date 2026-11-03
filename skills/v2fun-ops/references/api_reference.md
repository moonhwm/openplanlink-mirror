# V2Fun Algorithm API 参考（v1.6）

> 来源：https://doc.v2fun.ai（VitePress 中英双语官方文档站），侦察日期 2026-10-01；
> **2026-10-02 中国区 API 全链路实测回写**（建 key → /balance → 图生 3D → 轮询 → GLB 下载）。
> 标「实测」的条目以实测为准；标注 ⚠️ 者为未独立核实项。

## 基本信息

| 项 | 值 |
|---|---|
| Base URL | 中国区实测：**`https://api.v2fun.art/api/v1`**（key 分区：.art 控制台所建 key 只能在 .art 用）；`api.v2fun.ai` 从中国访问会被阿里云 WAF 拦（2026-10-02 实测） |
| 鉴权 | HTTP Bearer API Key，按 Scope 授权 |
| Key 自助获取 | https://api-console.v2fun.art（中国区控制台，主站账号 OAuth2 PKCE 登录）→ 创建 API Key；完整 Key 仅在创建成功时展示一次（首次建 Key 赠 100 API 积分，实测 /balance=100 到账） |
| 企业/定制 | v2fun.art/developers/api 营销页走商务申请（"定向开放"口径与自助通道并存） |
| 任务模式 | POST 创建任务 + GET `/{task_uuid}` 轮询；`block` 同步等待；`priority` 队列优先级；200=同步完成，201=异步接受 |
| 结果交付 | **实测结构（2026-10-02）**：`result` 是字符串化列表 `"['models/xxx.glb']"`；`metadata` 是 **list**，`metadata[0].downloads[]` 每项含 `asset_path` / `download_url`（阿里云 OSS 签名 URL，1 小时过期）/ `download_expires_at`；`status` 为大写（`COMPLETED`/`processing`） |
| 轮询纪律 | **实测**：5s 间隔触发 `RATE_LIMIT_EXCEEDED`（429）。建议 ≥15s + 429 指数退避；任务创建后服务端独立执行，断线可凭 task_uuid 续查，**不要重复提交**（会重复扣积分） |
| input_image 承载 | **实测**：`data:image/png;base64,...` 内联可用（2026-10-02） |
| 回调 | ⚠️ 营销页声称支持回调，公开文档未见 webhook/callback 参数——疑似仅企业定制 |

## Scope 一览

`image:prompt` / `image:imgen` / `image:imgedit` / `model:mesh` / `model:texture` / `model:remesh` / `model:convert` / `model:render` / `motion:animate` / `motion:query` / `video:capture` / `asset:read`

## 端点清单

### 图像
| 端点 | 用途 |
|---|---|
| POST /images/generations | 文生图 |
| POST /images/edits | 图像编辑/局部重绘 |
| POST /images/prompt_enhancements | 提示词增强 |
| POST /images/captions | 图像描述 |
| POST /images/processes | 图像处理（SeedVR2） |

### 3D
| 端点 | 用途 | 关键参数 |
|---|---|---|
| POST /3d_models/meshes | 网格生成 | 三种请求体：`prompt`（文生）/ `input_image`（图生）/ `input_images{front,left,back,right}`（多视图）；`model=pro\|flash`；`with_texture` / `hd_texture` / `pbr_texture` 开关 |
| POST /3d_models/textures | 纹理生成 | 参考图→白模贴图 |
| POST /3d_models/remeshings | 重拓扑 | |
| POST /3d_models/conversions | 格式转换 | |
| POST /3d_models/renderings | 渲染 | |

### 动作
| 端点 | 用途 |
|---|---|
| POST /motions/retrievals | 动作检索（动作库） |
| POST /motions/animations | 动画重定向（绑骨套用） |

### 视频
| 端点 | 用途 |
|---|---|
| POST /videos/pose_detections | 姿态检测 |
| POST /videos/motion_detections | 动作检测（视频动捕） |

### 账户
| 端点 | 用途 |
|---|---|
| GET /balance | 余额查询 |

## 调用骨架（curl 示例）

```bash
# 1) 创建任务（异步）——中国区 base 实测为 api.v2fun.art（key 分区，.ai 被 WAF 拦）
curl -sS -X POST "https://api.v2fun.art/api/v1/3d_models/meshes" \
  -H "Authorization: Bearer $V2FUN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"a low-poly fox, game asset","model":"pro","with_texture":true}'
# → 201 {"task_uuid":"..."}

# 2) 轮询结果（≥15s 间隔 + 429 退避；断线凭 task_uuid 续查，勿重复提交）
curl -sS "https://api.v2fun.art/api/v1/3d_models/meshes/<task_uuid>" \
  -H "Authorization: Bearer $V2FUN_API_KEY"
# → 200；status 大写 COMPLETED；result 为字符串化列表；
#   metadata 是 list，metadata[0].downloads[].download_url 为 OSS 签名 URL（1 小时过期）
```

生产调用优先用 `scripts/gen_mesh.py`（已内化上述实测纪律），勿手写裸轮询循环。

## 积分单价（API 口径，2026-10-01 快照）

见 `scripts/estimate_credits.py` 内置 PRICE_TABLE（与 doc.v2fun.ai/zh/pricing 逐项对应）。
要点：基础 3D 20；多视图 20；标准纹理 +20；8K 纹理 +5；PBR +2；重拓扑/格式转换各 5；
动画重定向 5/次；视频动捕基础 1 积分/3 秒、高级（含手部）10 积分/3 秒；
文生图 1~15 视模型（Qwen-Image 1 / NB2-Lite 5 / NB2 10 / NB-Pro 15 / GPT-Image 系 10）。

## 输出与上传

- 输出格式（官方各处口径合集）：GLB、FBX、OBJ、STL、USDZ、3MF、MP4、BVH（动作数据）
- Web 端上传：模型 glb/fbx/pmx/zip；动作文件 bvh/vmd；单文件上限 20MB
- AIGC 水印默认开启（合规：中国 AI 生成合成内容标识法规）

## ⚠️ 安全观察（仅记录，勿在生产复用）

中国区网关 `https://api.prod.v2fun.art/doc.html` 为公开可访问的 knife4j 聚合文档入口，
`/swagger-resources` 无鉴权列出 8 个微服务名。前端内部网关 apiUrl=`https://api.prod.v2fun.art/`。
公开 API 走 api.v2fun.ai，不要把内部网关端点当作公开 API 使用。
