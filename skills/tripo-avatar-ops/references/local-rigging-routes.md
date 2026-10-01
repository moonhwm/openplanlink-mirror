# 本地/开源绑定路线卡（2026-09-10 挖掘轮实证）

> 面向 200 万面级高精度原模（云端管线上限外）的本地绑定路线。来源：VAST-AI-Research 官方仓库 README/LICENSE/demo.py 直读 + 沙箱/V100 实测。版权蒸馏件仅内部学习，永不上公开分发轨。

## §1 能力矩阵

| 路线 | 性质 | 权重 | 资源门槛 | 回贴/兼容 | 状态（2026-09-10） |
|---|---|---|---|---|---|
| **SkinTokens / TokenRig**（arXiv:2602.04805） | UniRig 官方继任者，蒙皮 token 化 | **全量放出（MIT）** | **推理仅 14GB VRAM** | `--use_transfer` 内嵌 bpy_server 回贴原模型，保 8K 贴图保比例；`--use_skeleton` skin-only 可复用现成骨架 | **首选** |
| UniRig（SIGGRAPH'25，清华+Tripo） | 骨架 AR 生成 + 蒙皮两阶段 | 基础权重已放；Rig-XL/VRoid「Coming Soon」 | 「≥60GB」是蒙皮**训练**门槛（勘误：非推理） | `merge.sh` 回贴保贴图 | 论文精度暂不可复现，待权重 |
| HoloPart | 生成式部件去遮挡分割 | 已放 | 需 SAMPart3D/SAMesh 粗分割前置 | 对应 generate_parts 部件治理 | 分割件用，非绑定件 |
| AccuRIG / Mixamo | 商业/免费在线绑定 | — | 面数上限 600K / ~200K | 高面数须先降面 | 备用 |

## §2 主路线（200 万面原模）

```
原模（如 1,887,820 面）
  → trimesh + fast_simplification 降面（实测 →149,999 面 / 5.5s / 2.86MB）
  → SkinTokens 推理（V100 窗口，14GB VRAM 足够）
  → --use_transfer 回贴原模（保贴图保比例）
```

- 与 Tripo 云端的衔接：SkinTokens `--use_skeleton` 可直接复用云端那副 41 关节 biped 骨架 → 云/地产物同骨架，动画 clip 互通。
- 零成本预验：HF Spaces 在线 demo 传降面代理验质量，不占任何积分/窗口。
- **拓扑立法（用户明令，不可豁免）**：三角形为正典；四边形重拓扑非明令永不启用。

## §3 V100 / 沙箱纪律（实证坑）

- **V100 协调**：GPU 被他人任务（ASR 等）占用时本席只协调不越权——预约窗口须函告/口令，不擅动。
- **CPU-only 侧跑**：`CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=8`（与在卡任务共存）。
- **防 SIGHUP**：长跑一律 `setsid <cmd> </dev/null` 脱离会话（首跑被 SIGHUP 杀过的实证）。
- **沙箱硬死线**：shell 工具约 300s 硬死线（无论 timeout 请求多久）——长等待 = nohup/setsid 后台写日志 + 短轮询；`bash -c '...'` 单引号内嵌套 heredoc 会挂死，脚本一律 write_file 落盘执行。
- **持久性**：/tmp 与 /root 重置即清；只有 /mnt/agents/* 跨会话存活。artifact 落 /mnt/agents/output 附 md5。
- **低内存**：沙箱 3GB RAM——全尺寸 CPU 蒙皮/渲染大网格会 OOM，重活预约 V100 窗口。
- **凭据**：credentials.env 不上 V100；长效 AK/SK 冷藏；动账类（BillingCenter）永不使用。

## §4 本地 GLB 复合工艺（云端动画交付的现实路径）

云端单体导出不落动画（见 SKILL.md §3），动画件 = 本地复合：

1. 分别下载 rigged 网格 GLB（meshopt 压缩预览件）与动画 GLB（meshes:0，纯 clip）。
2. meshopt 解码：`pip install meshoptimizer`，逐 bufferView 按 `EXT_meshopt_compression` 头（mode/filter/count/byteStride）解码；POSITION 常见 EXPONENTIAL filter → `decode_filter_exp`；JOINTS/WEIGHTS 多为 u8 normalized 直接读。
3. 通道对齐：重定向 clip 关节通道与绑定骨架 1:1（实测 41 关节 + Armature 根）。
4. numpy LBS 中帧渲染：采样（旋转 slerp/位置 scale lerp）→ 组全局矩阵 → `v' = Σ w_i · J[joint_i] @ v`。**矩阵坑**：glTF 列主序存储、frombuffer 行主序读出 = 转置，蒙皮矩阵 = `G @ IBM_read.T`。
5. 验收：正视+侧视渲染，四肢无塌陷、无拧骨即过质量闸；anim 空间原点偏移（如整体 +X）是坐标系现象，不算缺陷。
