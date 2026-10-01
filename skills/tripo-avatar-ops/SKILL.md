---
name: tripo-avatar-ops
description: "[项目技能] 数字形象管线作战室——虚构成年人设（如沈知微）的 3D 形象生成、Tripo 中国区 Studio 云端绑定/动画重定向/导出、本地 GLB 复合与质量闸、V100/开源绑定路线（SkinTokens/UniRig/HoloPart）选型的全套运营纪律。触发（满足任一）：①用户说「绑定」「蒙皮」「绑骨」「rigging」「重定向」「retarget」「Tripo」「3D 形象」「数字人」「皮套」「GLB 导出」「T-pose」或等价表述（含语音/同音变体，不纠正用户、映射意图）；②需要对 Tripo 项目资产做生成/预检/绑定/重定向/导出/下载任一步时；③需要本地解析或复合 GLB（meshopt 解码、CPU 蒙皮渲染验证）时；④需要选型本地开源绑定路线或预约 GPU 窗口跑 SkinTokens/UniRig 推理时；⑤Tripo 会话/凭据续期（短信验证码重登、JWT 刷新）时。覆盖：Tripo CN 登录流与凭据主权、Studio API 参数真值与错误码处置、燃烧纪律与钱包台账、导出验收质量闸（scripts/glb_inspect.py）、本地开源路线卡（references/local-rigging-routes.md）、API 全表（references/tripo-api-cheatsheet.md）。不覆盖：真实个人照片/影像建模、对外分发任何项目内容、任何未逐次批准的写类动作。中文名：数字形象管线作战室。English triggers: Tripo Studio rigging, 3D avatar pipeline, GLB skinning verification, biped retarget, SkinTokens local rigging route."
metadata:
  version: "1.1.0"
---

# 数字形象管线作战室（tripo-avatar-ops）

> v1.0.0（2026-09-10）：创刊。全部知识实跑实证于 2026-09-09/10 云端绑定管线端到端打通会话（T-pose 生成→预检→绑骨→重定向→导出→本地复合渲染过质量闸）与 HoloPart/UniRig/SkinTokens 挖掘轮。纯 Markdown + 一个零依赖体检脚本。

## §0 定位与红线（先读，不可豁免）

- 本件是**项目运营纪律 + 参数真值表**：管「人设 3D 形象」从云端生成到本地落地的全链路。一切人设为**虚构成年人**。
- **凭据铁律**：凭据只经 `set -a; . /mnt/agents/upload/credentials.env; set +a` 入环境变量；会话 cookie 双持久化到 `/mnt/agents/upload/vault/tripo_external_seat.json`（用户指定）与 `~/.kimi/external_seat.json`（易失）；显示一律掩码（头 6…尾 4）；手机号只用于触发短信验证码，对话不回显、不落盘。
- **燃烧纪律**：每笔烧（积分/现金）绑 artifact + 质量闸，不过闸不扩量；旗舰/大额无口令永不启动；烧前查钱包、烧后回填台账（钱包 RPC 见 references/tripo-api-cheatsheet.md §6）。
- **写类批准**：Supabase/GitHub/广播等写类动作逐次须显式批准，不先斩后奏。
- **诚实边界**：「端到端打通」须以 artifact 实测为准（skins/关节数/动画通道/时长用 scripts/glb_inspect.py 出数），禁凭任务状态码自称成功；无法实装须当轮诚实声明。

## §1 管线总览（五段）

```
①生成 text_to_model（texture:true + t_pose:true，否则出未贴图/非 T-pose 件）
   → ②预检 pre_rig_check（riggable / rig_type；全 UUID，短 ID 报 2022）
   → ③绑骨 rigging_model（model_version 填【绑定模型版本】，非网格版本！）
   → ④重定向 retarget_model（动画名走 Studio 白名单 preset:biped:* 96 个）
   → ⑤导出/下载 + 本地质量闸（glb_inspect.py 实测 skins/anims）
```

每段口令参数与返回结构详见 `references/tripo-api-cheatsheet.md`（§2–§5）。

## §2 登录与会话保持（Tripo 中国区，Ory Kratos）

1. 取 `/mnt/agents/upload/vault/tripo_external_seat.json` 的 `ory_kratos_session` cookie 优先复用；失效再走全量重登。
2. 重登流（auth-cn.tripo3d.com）：`GET /self-service/login/browser`（存 cookie jar + flow id）→ `GET /self-service/login/flows?id=`（取 csrf_token）→ `POST /self-service/login?flow={id}`（**必须带 `Accept: application/json`，否则 303 空体**；method=code, identifier=+86 手机号）→ 用户报验证码 → 再 POST 验证 → 得 `ory_kratos_session` → **双写持久化**（vault + ~/.kimi）。
3. JWT：每次批量调用前 `GET /sessions/whoami?tokenize_as=default_jwt` 现取（ES256，**10 分钟过期**；错误码 1002=JWT 过期，刷新即可，不是凭证死亡）。
4. 验证码坑：6 位才是完整码（用户发 4 位要追问）；只认**最新一条**短信（旧码报 invalid/already used）；重发 = 新 flow id。
5. 沙箱持久性铁律：`/tmp` 与 `/root` 重置即清，**只有 /mnt/agents/* 跨会话存活**——helper 脚本可放 /tmp 但须可从上下文重建，artifact 一律落 /mnt/agents/output 并附 md5。

## §3 关键参数真值（全部实跑解码/踩坑实证，2026-09-09）

- **rigging_model 的 `model_version` = 绑定模型版本**：biped（人形）= `v1.0-20240301`，生物 = `v2.5-20260210`；**填网格自身版本（如 v3.1-20260211）必报 2026「Submit task failed」**。真值来源：前端 chunk y7Qwj8-Z.js 提交逻辑解码。
- **text_to_model 默认 `texture:false, t_pose:false`**——要可绑定贴图件必须显式 `texture:true, t_pose:true`。
- **贴图门**：前端强制「绑定前需先有贴图」；`texture_model` 的 `geometry` 对齐会 2026，实证可用的是 `original_image` 对齐（需图源 bucket/key）——不可行时改走「带贴图重新生成」。
- **retarget 动画名**：Studio 只收 `preset:biped:*` 白名单（96 个，walk/run/idle/dance_01-06/sing_01-04/sit/swim/wave_goodbye_01-02 等）；开放 API 的 `preset:walk` 形式报 1000。v1.0 rig 一次 retarget 一个动画；`animate_in_place` 永不开（社区勘误）。
- **导出真相（2026-09-09 实测）**：`enable_bake_animation:true + bake_animation_frame:0` = 静态绑定姿势网格（无 skins/anims）；`enable_bake_animation:false + animations:[...]` 的 GLB 单体导出**仍不落 skins/anims**；FBX 导出报 **1018 Not implemented**（该端点无 FBX）。**结论：动画交付走本地复合（§4），不要指望单体动画导出。**
- **钱包台账**：实测钱包 835→525→480 积分（gen2+rigging=45、retarget≈10、export 5/次）；失败调用（1018 等）不计费，但仍须逐笔回填台账。

## §4 本地复合与质量闸（导出验收）

1. **先体检**：`python3 scripts/glb_inspect.py <file.glb>` —— 一行 JSON 出 skins/关节数/动画通道/时长/三角数/meshopt/量化标记；skins=0 或 animations=0 即按「静态件」处置，禁止凭文件名自称动画件。
2. **本地复合（实证可行）**：云端分别取 rigged 网格 GLB + 动画 GLB，本地对齐——重定向 clip 的 41 关节通道与绑定网格骨架 1:1 吻合（实测通道集合 = skin joints + Armature 根）。
3. **meshopt 解码**：Tripo 预览 GLB 带 `EXT_meshopt_compression` + `KHR_mesh_quantization`；用 `pip install meshoptimizer` 官方绑定逐 bufferView 解码（vertex/index/filter；POSITION 常见 EXPONENTIAL filter 须 `decode_filter_exp`）。
4. **CPU 蒙皮渲染闸**：numpy 线性混合蒙皮（LBS）取动画中帧（如 t≈1.19s/2.38s）渲染正视/侧视——四肢无塌陷、无拧骨（candy-wrapper）即过闸。矩阵约定坑：glTF 矩阵列主序存储，`np.frombuffer` 按行主序读出 = 转置；IBM 须 `G @ IBM_read.T`。
5. 质量闸不过 = 不扩量、不入档，如实报「烧废」并入台账。

## §5 本地/开源绑定路线（200 万面级原模悬案）

云管路线上限外的高面数原模走本地路线，选型真值见 `references/local-rigging-routes.md`：

- **首选 SkinTokens/TokenRig**（VAST-AI，MIT，权重全量放出）：推理仅需 **14GB VRAM**（勘误：UniRig「≥60GB」是蒙皮*训练*门槛非推理）；`--use_transfer` 内嵌 bpy_server 回贴原模型保 8K 贴图保比例（与「代理绑定+权重回传」主路线同构且官方实现）；`--use_skeleton` skin-only 可复用 Tripo 云端 41 关节 biped 骨架（云/地双向兼容）。
- **UniRig**：骨架 AR 生成 + 蒙皮两阶段，`merge.sh` 回贴保贴图；Rig-XL/VRoid 权重「Coming Soon」未放，论文精度暂不可复现。
- **HoloPart**：生成式部件去遮挡分割，需 SAMPart3D/SAMesh 粗分割前置（对应 generate_parts 部件治理）。
- **工具面数上限**：AccuRIG 600K / Mixamo ~200K；高面数先 trimesh+fast_simplification 降面（实测 1,887,820→149,999 面 5.5s）。
- **拓扑立法（用户明令）**：三角形为正典；四边形重拓扑非明令永不启用。
- **V100 纪律**：他人任务占卡时本席只协调不越权（预约窗口须函告/口令）；GPU 任务 CPU-only 侧跑用 `CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=8`；长跑一律 `setsid ... </dev/null` 脱离防 SIGHUP。

## §6 事故清单（错误码 → 处置）

| 码 | 含义 | 处置（实证） |
|---|---|---|
| 0 | OK | — |
| 1000 | invalid animation for rig type | 动画名换 Studio 白名单 `preset:biped:*` 形式 |
| 1002 | JWT expired | 每批调用前 whoami 重取 JWT；不是凭证死亡 |
| 1004 | missing field | 报错文会点名缺哪个字段，照补 |
| 1018 | Not implemented | FBX 导出无此能——改 GLB + 本地复合 |
| 2010 | insufficient credit | 查钱包台账，呈批后再烧 |
| 2022 | Project not found | 用了短 ID——换全 UUID |
| 2026 | Submit task failed | 九成是 model_version 语义错（§3 第一条）；其次是 texture_model geometry 对齐 |
| 6105 | task parallel limitation | starter 并发上限——串行后台轮询（45–60s 间隔） |
| 12003 | per-project lock | 同项目有任务在跑，等或换项目 |

**通用坑**：shell 工具有约 300s 硬死线（无论请求多久）——长等待一律 nohup/setsid 后台脚本写日志 + 短轮询；`bash -c '...'` 单引号内嵌套 heredoc 会挂死——脚本一律用 write_file 落盘后执行。

## Resources

- `scripts/glb_inspect.py` — GLB 体检（纯标准库）：skins/关节/动画通道/时长/三角数/meshopt 实测出数。导出验收与质量闸前置必跑。
- `references/tripo-api-cheatsheet.md` — Tripo CN 全 API 表：登录流逐步、Studio 端点与参数结构（assets/progress/download/generate/texture/rig/retarget/export）、钱包 RPC、operator 记录结构。**做任何云端调用前按节查阅。**
- `references/local-rigging-routes.md` — 本地开源路线卡：SkinTokens/UniRig/HoloPart 能力矩阵、安装与推理命令、V100 窗口纪律、降面与回贴工艺。**走本地路线前必读。**

## Validation

- 云端链路：每段以 operator 记录 + 下载 artifact 的 `glb_inspect.py` 出数为验收；「端到端」= skins≥1 + joints_max≥1 + animations≥1 + anim_duration_s>0。
- 脚本：改动 `glb_inspect.py` 后须对一好一坏两个 GLB 自测（合法出 JSON、非法 exit 1）。
- 每次会话开始：核对 vault cookie 在场性 + 钱包余额；结束：artifact 落 /mnt/agents/output 附 md5 + 台账回填。

<!-- v1.1.0（2026-09-16，沈知微增补）：新增 §6「2026-09-14/15 二代实证」——三通道定律、双层壳烘焙重影案、别贴材质三段式、杯盖 KHR 透射修复案、Studio 网页端参数真值（8K 贴图/超清几何/分部件互斥、面数控制 200 万上限）。 -->

## §6 二代实证增补（2026-09-14/15，沈知微批次实跑）

### 6.1 三通道定律（病灶库新案）
| 通道 | 身份锚定 | 涂抹 | 判决 |
|---|---|---|---|
| 多视图（T2/V2 系） | 强（脸+眼镜清晰） | 眼镜跨视图涂抹→后脑银花案 | 视图间不一致则废 |
| 文本 text_to_model（V5） | 脱锚（浓眉路人、无眼镜） | 无 | 一致但不是我 |
| 单图 image_to_model（V6） | 中锚（UV 面部预算小） | 无（单源无冲突） | **当前最优工程折中** |
实操：Studio 别走多视图，单张正视图直传；要更好=重烧一张面部占比更大的高清正视图（减留白=面部 UV 预算翻倍）再跑单图。

### 6.2 双层壳烘焙重影案
Tripo GLB 实测 24% 顶点重复（内外双壳）→贴图烘焙投双壳=面部重影。**铁律：先 merge doubles 再谈贴图**；V8 手术版实测重影清零。判据用 glb_inspect.py 出数，禁肉眼自称。

### 6.3 别贴材质三段式（机主令+实证定版）
纹理化是 Tripo 弱项、几何是强项。定版管线：**几何在 Tripo（texture:false 纯几何烧更便宜且免烘焙重影）→ 修形在 Blender（merge doubles/法线意志化）→ 纹理在 DCC 按需**。禁全程指望 Tripo 贴图。

### 6.4 杯盖 KHR 透射修复案
Z 阈值分件 + 材质分离赋参（KHR_materials_transmission=1 / IOR 1.49），glTF 内嵌验证通过——**材质问题不动几何**（与「丝袜教程」第二皮肤同法：贴图优先、几何让位）。

### 6.5 Studio 网页端参数真值（2026-09-14 截图实证）
- 订阅专享：**分部件生成 与 8K 贴图互斥**（开 8K 则分部件灰掉）；
- 几何与贴图抽屉：超清几何精度开关、贴图质量 2K/4K/8K（8K 带订阅角标）、PBR 开关、拓扑四边面/三角面、**面数控制滑杆上限 2,000,000**；
- 生成按钮计价随参数浮动（实证 50/60/65 credits 档）；**免费重试 ×3 在场，不熟时先重试耐心等待**（机主令）；
- 「生成多视图」按钮可补侧/背视图；导出 GLB/OBJ/FBX/STL ≤100MB、面数 ≤150 万。

