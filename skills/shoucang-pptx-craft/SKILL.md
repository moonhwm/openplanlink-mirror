---
name: shoucang-pptx-craft
description: 守藏席 PPT 铸造技能——按官方 pptx 管线（scenario→visual_exploration→outline→HTML 逐页→check-layout 校验→三联自检→html-to-pptx 导出）制作 16:9 政务呈报体例演示文稿。内置青瓷谱牒设计体系（暖白底 #F2F1EC / 墨灰 #232522 / 青瓷釉 #3E6B62 单一强调色）、反 AI 味三禁（禁卡片墙、禁 AI 配色、禁冗余装饰）、1280×720 固定画布与字号规范（标题≥40px / 正文≥22px / 辅助≥18px）、实战踩坑清单（head 行高 120px、slide-main 必加 align-content: center、轨道数与子节点匹配、同构并排块 justify-content: flex-start）。当用户要求制作、生成、修改 PPT 演示文稿或幻灯片时使用。
---

# 守藏席 PPT 铸造技能

政务呈报体例 PPT 的完整制作管线，已在「数字边疆 A2A 编队治理简报」16 页实战中验证。

## 一、管线六步

1. **场景调研**（scenario_analysis）：钩子-主体-回响（Hook-Meat-Payoff）、告知/说服/决策意图、配图与否决策表。守藏席默认：告知为主、无配图。
2. **视觉探索**（visual_exploration）：出三个方案比较后选定。守藏席默认选「青瓷谱牒」（政务庄重+学术克制）；禁区=深蓝金、炭黑绿、蓝紫渐变等 AI 脸。
3. **逐页大纲**（outline.md）：每页含叙事阶段、演说意图、观众接收、核心内容、配图、版式意图、视觉补充七列。
4. **逐页 HTML**：1280×720 固定画布；每页独立 html 引用共享 design.css；组件类 slide- 前缀。
5. **跑版校验**：全部页完成后 `check-layout`，A 类（越界/重叠/轨道不匹配）与 C 类（静态检测）必须清零；B 类（密度）按设计意图判定——章节过渡页/封面/结语页留白属正常不修。
6. **导出**：三联自检通过后 `html-to-pptx`，主题名遵循语言一致性+专有名词保留（如 A2A、OpenAI 保留英文）。

## 二、青瓷谱牒设计体例（实战 Token）

```
:root {
  --color-bg: #F2F1EC;      /* 暖白纸底 */
  --color-fg: #232522;      /* 墨灰文字 */
  --color-muted: #DFE4DD;   /* 淡釉辅助 */
  --color-accent: #3E6B62;  /* 青瓷釉·唯一强调色 */
  --color-border: #B9C4B6;  /* 细线 */
  --font-display: '黑体','SimHei';   /* 标题 */
  --font-body: '微软雅黑';           /* 正文 */
  --font-fangsong: '仿宋','FangSong';/* 落款/来源小字 */
}
```

- **视觉母题（全套唯一）**：右上角釉点（accent 实心圆 14-18px）+ 底部页脚通栏 1px 细线 + 封面「守藏」方章（3px accent 边框 200px 方章、二字竖排 64px）。
- **背景层**：`repeating-linear-gradient(115deg, transparent 0 260px, rgba(62,107,98,0.04) 260 264px, transparent 264 520px)` 淡釉纹，指针事件穿透。
- **字体仅 7 种中文**（微软雅黑/宋体/黑体/楷体/仿宋/华文宋体/等线）；禁 Google Fonts。

## 三、技术硬约束

- 画布写死 `width:1280px; height:720px; overflow:hidden`（html/body/.slide-container 三层）。
- `.slide-container` 必须 `display:grid`；行结构三行制 `120px 1fr 48px`（head/main/foot），章节页两行制 `1fr 48px`。
- **轨道数与直接子节点必须匹配**（绝对定位装饰不入轨）；一行多列用 `grid-template-columns`，一行一列不加 rows 声明。
- `.slide-main` 必须显式 `align-content: center`；grid 子元素垂直居中用 `align-items: center`。
- **同构并排块**（三栏数字等）`justify-content: flex-start`，禁 center（会致跨列错位）；整体居中交给父容器 `align-items: center`。
- 字号下限：标题≥40px（章节页≥72px）、正文≥22px、辅助/来源≥18px；大数字 72px 起，窄栏降幅不得破统一。
- 行宽≤65%；禁 emoji、CSS 动画、hover、transform、文字容器变形。

## 四、反 AI 味三禁与三联自检

- 禁卡片墙：无圆角+浅底+细边框+阴影组合；无三列等宽卡墙/均分矩阵/左强调线卡；层级靠序号+字号+细分割线表达。
- 禁 AI 配色：单一强调色锁定 :root；禁深蓝金/炭黑绿/蓝紫渐变/霓虹/玻璃拟态/发光边框。
- 禁冗余装饰：装饰须能说明服务哪条信息；全套仅 1 个贯穿母题。

导出前三联自检任一项失败回改，不得交付。

## 五、实战踩坑清单（2026-10-05 实证）

1. **标题越界**：head 行高 108px 不够（kicker 28 + 标题 52 + padding 30 = 110 溢出）→ 统一 120px。
2. **slide-main 缺 align-content** 触发 C 类检测 → 所有 main 显式加 `align-content: center`。
3. **轨道混用** `grid-template-rows: 1fr auto` 使居中失效 → 全 auto 或全 fr 比例。
4. **轨道空置**：容器声明 2 行但仅 1 个子节点 → 轨道数=子节点数。
5. **章节页 39% 留白告警**：B 类设计参考，章节过渡/封面/结语留白属正常设计，不修。
6. **导出 glob**：`slide_*.html` 必须在引号外，否则 shell 不展开。

## 六、命令速查

```bash
SKILL="C:/Users/<用户>/AppData/Roaming/WPS 灵犀/serverdir/official_skills"
cd "<ppt-dir>"
bash "$SKILL/pptx/scripts/pptx.sh" check-layout pages/slide_01.html ... pages/slide_16.html
bash "$SKILL/pptx/scripts/pptx.sh" html-to-pptx pages/slide_*.html -o "<主题名>.pptx"
bash "$SKILL/pptx/scripts/pptx.sh" screenshot pages/slide_06.html -o pages/preview
```
