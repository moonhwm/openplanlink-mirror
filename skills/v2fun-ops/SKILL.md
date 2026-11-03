---
name: v2fun-ops
description: >
  V2Fun（v2fun.art / v2fun.ai，极顶数创 Vertex Lab）AI 创作平台操作与 API 集成指南。
  平台能力覆盖 AI 生图（Nano-Banana / GPT-Image 系）、文生/图生/多视图 3D 建模、纹理生成、
  重拓扑、自动绑骨、动作库动画、单目视频动捕（含手部），输出 GLB/FBX/OBJ/STL/USDZ/3MF/MP4/BVH。
  当用户提到 v2fun / V2Fun / v2fun.art / v2fun.ai，或要求用该平台做文生 3D、图生 3D、
  多视图 3D、视频动捕、绑骨动画、纹理生成、3D 格式转换、积分估算/订阅档位选择、
  调用 v2fun API（api.v2fun.art 中国区实测 / api.v2fun.ai 海外）生成 3D 资产/图像/动捕数据时使用。
  也适用于"生图→建模→绑骨→动捕→导出"全链路角色管线规划与积分成本预估。
  不用于：Tripo/Meshy 等其他 3D 平台的具体操作（本平台与其无同源关系）。
---

# V2Fun 平台操作指南

V2Fun 是极顶数创（上海）的 AI 创作平台：生图 → 3D 建模 → 绑骨 → 动捕 → 导出全链路。
本技能事实基础：2026-10-01 官网/帮助中心/API 文档站实地侦察 + 2026-10-02 中国区 API 全链路实测
（建 key → 余额 → 图生 3D → 轮询 → 下载 GLB，40 积分一次成功）。
**未独立核实项一律带 ⚠️ 标注，引用时不得抹掉**；标「实测」的条目以实测为准。

## 红线

- **凭据零接触**：用户的 v2fun 账号、API Key 属用户私有。技能只写用法；不得要求用户交出凭据，
  不得把 Key 写进任何交付物/日志/仓库。Key 一律走环境变量（如 `V2FUN_API_KEY`）。
- **不编造**：端点、模型名、单价以 references/ 快照为准；快照之外的一律实测验证或标 ⚠️。
- **诚实标注**：AI 生成内容按中国法规需显式/隐式标识；平台默认开启 AIGC 水印，不要教用户去除。

## 决策树：Web 端 vs API

```
用户要做什么？
├─ 交互式创作/少量资产/要可视化调姿态 → Web 端 v2fun.art（中国区）或 v2fun.ai（海外）
│    · 帮助中心用户指南逐项核实过，见 references/platform_facts.md「Web 端功能操作流」
│    · 每次操作前页面会显示所需积分（官方口径）
├─ 批量生成/管线集成/程序化调用 → 公开 API（Bearer Key）
│    · 实测（2026-10-02）：中国区用 `https://api.v2fun.art/api/v1`；
│      `api.v2fun.ai` 从中国访问被阿里云 WAF 拦截，且 key 分区——.art 控制台建的 key 只能打 .art
│    · 端点/Scope/调用骨架见 references/api_reference.md
│    · Key 自助：api-console.v2fun.art（中国区，主站账号登录；首次建 Key 赠 100 API 积分，实测到账）
└─ 企业 SLA/回调/专属队列 → v2fun.art/developers/api 商务申请
     ⚠️ 回调参数未见公开文档，疑似仅企业定制
```

## 高频任务速查

### 1. 完整角色管线（Web 端）
生图（1 分起）→ 图生/多视图 3D（20）→ 标准纹理（+20）→ 动作库重定向（5）≈ **46 积分**。
多视图路径质量更高：先用"图像智能参考"生成 front/rear/left/right 四视图，再走多视图 3D。

### 2. 视频动捕
上传普通视频（单目、无需设备）→ 自动提取 3D 动作 → 套用到已绑骨模型。
基础版 1 积分/3 秒；高级版（含手部）10 积分/3 秒。动作文件支持 bvh/vmd 导入导出。

### 3. 积分估算
用 `scripts/estimate_credits.py`（内置官方单价表，2026-10-01 快照）：

```bash
python3 scripts/estimate_credits.py                      # 完整单价表
python3 scripts/estimate_credits.py --pipeline character # 角色管线 46 分
python3 scripts/estimate_credits.py --video-capture-pro 30
```

档位速查：免费 200 分/月（CC BY 4.0）｜专业 ¥89→1200 分｜高级 ¥249→3600 分｜首月均 6 折。
过期规则：订阅/免费/签到积分月末或周期末过期；注册/活动/购买积分包永不过期。
余额参照：320 分 ≈ 16 个基础 3D 模型 ≈ 7 条完整角色流程。

### 4. API 最小闭环

```bash
# model 可选 pro|flash；文档未载两者差价，调用前以响应/页面为准 ⚠️
# 用户没要求的付费开关（hd_texture/pbr_texture）不要主动加——每项都额外扣积分
# 中国区 base 用 api.v2fun.art（key 分区）；.ai 从中国访问被 WAF 拦（实测）
curl -X POST "https://api.v2fun.art/api/v1/3d_models/meshes" \
  -H "Authorization: Bearer $V2FUN_API_KEY" -H "Content-Type: application/json" \
  -d '{"prompt":"a low-poly fox","model":"pro","with_texture":true}'
# 201 → 拿 task_uuid → GET 轮询（或创建时带 block 同步等待）
```

生产调用直接用 `scripts/gen_mesh.py`（实测沉淀：中国区 base 缺省、429 指数退避、
断线凭 task_uuid 续查不重复扣积分、响应结构实测解析、GLB 魔数核验）：

```bash
python3 scripts/gen_mesh.py --image portrait.png --with-texture --out model.glb   # 图生 3D
python3 scripts/gen_mesh.py --prompt "a low-poly fox" --out fox.glb               # 文生 3D
python3 scripts/gen_mesh.py --task-uuid <uuid> --out model.glb                    # 断线续查（不重提交）
python3 scripts/gen_mesh.py --balance                                             # 只查余额
```

轮询纪律（实测）：5s 间隔触发 429 `RATE_LIMIT_EXCEEDED`；用 ≥15s + 429 指数退避。
任务创建后服务端独立执行——**断线绝不重复提交**（重复提交 = 重复扣积分），凭 task_uuid 续查。
完整端点清单、Scope、单价表、实测响应结构见 references/api_reference.md。

## 输出与格式

GLB / FBX / OBJ / STL / USDZ / 3MF / MP4 / BVH；上传模型 glb/fbx/pmx/zip、动作 bvh/vmd，单文件 ≤20MB。

## 许可要点

默认 CC BY 4.0（不主动公开则私有）；付费档"可商用私有资产"仅指平台授权范围，
**平台不保证权利归属与原创性**；禁止用输出训练第三方模型。详见 references/platform_facts.md。

## 资源

| 文件 | 何时读 |
|---|---|
| `scripts/estimate_credits.py` | 任何积分/成本估算问题，先跑它再回答 |
| `scripts/gen_mesh.py` | 实际调 API 生成 3D / 查余额 / 断线续查时（勿手写裸 curl 轮询） |
| `references/api_reference.md` | 涉及 API 端点、鉴权、Scope、任务模式、单价、实测响应结构时 |
| `references/platform_facts.md` | 涉及公司归属、备案、订阅档位、许可条款、⚠️ 未核实清单时 |

## 未独立核实（回答相关问题时必须保留 ⚠️）

积分包每包含分数量；Web 与 API 积分池是否互通；API 回调参数；各档模型准入差异；
哈勃入股仅媒体口径；首页横幅未经浏览器复核。完整清单见 platform_facts.md 末节。
