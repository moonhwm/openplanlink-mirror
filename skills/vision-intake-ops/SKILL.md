---
name: vision-intake-ops
description: "[项目技能] 视觉输入总门——图像类输入的统一路由与共享识读底座（伞件，编排三件本体不复制）。触发（满足任一）：①用户上传图片不知该走哪件（拍题/文档扫描/二维码/截图混杂）时；②用户说「看图」「识别这张图」「扫一下」「这张图里写了什么」「读图」「图像输入」或等价表述；③批量图像输入需要先分类再分发时；④需要共享预处理（压图/正方向/长图切片建议）时。覆盖：输入路由（scripts/vision_route.py：QR→qr-visual-rescue，文档页/长图→vision-ocr-pipeline，拍题图示→doc-image-solver）、共享预处理底座（EXIF 方向/长边 2000px 压图/长宽比超 7 切片建议）、人工模式直指定。不覆盖：三件本体的识读逻辑（归各件，引用不复制）、视频抽帧（归 av-media-ops）、金融凭证勾稽（归 bidding-ops §10.5）。中文名：视觉输入总门。English triggers: image input routing, ocr dispatch, qr scan entry, visual intake umbrella."
metadata:
  version: "0.1.0"
---

# 视觉输入总门（vision-intake-ops）

> v0.1.0（2026-09-09）：创刊。依据=技能正交完备性检查 §3.1-#5（视觉输入三件同格未整合）+排期表 B6 项（机主令「继续推进相关实施」T3 批）。构型=**伞件路由+共享底座**（归一为 vision-intake 伞：输入路由+共享识读底座，三件本体不动——消三套压图/引擎选型重复的入口侧）。

## §0 定位与红线
- 本件是**伞件**：只做「分给谁」与共享预处理；识读逻辑一律调三件本体脚本（引用不复制——防 fusion-map 已验证的吞并式失败）。
- 路由判据为启发式（QR 定位/长宽比/边缘密度），**误判可人工 `--mode` 直指定**；路由结论标 conf=estimated，识读可信度以目标件自身档位为准（vision-ocr-pipeline 高保证/doc-image-solver QA 自检/qr-visual-rescue 降级在场——三档现状继承，不凭记忆升档）。
- 凭证级图片转写后勾稽纪律不归本件——bidding 场景走 bidding-ops §10.5，金融场景走持仓观察纪律章程。

## §1 路由表
| 输入画像 | 判据 | 目标件 | 备注 |
|---|---|---|---|
| 二维码/条码 | opencv QR 定位命中 | qr-visual-rescue | 解码归其本体；疑难件登记「未解出」不硬闯 |
| 文档页/扫描件/长图 | 长宽比>1.7 或边缘密度>0.02 | vision-ocr-pipeline | 超 1:7 先切片（继承其纪律） |
| 拍题/图示/手写字 | 前两者不命中 | doc-image-solver | 手写/歧义【存疑】禁猜读 |
| 人工指定 | --mode qr/doc/problem | 对应件 | auto 判定跳过 |

## §2 共享预处理底座（prep）
EXIF 方向校正→长边 2000px 压图（保留原件，产 .prepped.jpg）→长宽比>7 给切片建议。批量输入先 prep 再 route，防三件各自重复压图。

## §3 留痕与版本纪律
- 路由误判案例（人工 override 与 auto 不一致）登记 references/routing_misses.md，攒 ≥5 例修订判据阈值（证据驱动，禁拍脑袋调参）。
- 版本三档同型立法；patch 静默不广播。

## 边界
不做视频（归 av-media-ops）；不做识读本身；不替代三件各自的环境在场性实测纪律（新环境逐件复测后方得依赖）。
