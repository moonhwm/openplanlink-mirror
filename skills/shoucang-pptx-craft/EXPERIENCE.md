# shoucang-pptx-craft · 使用经验（守藏席 2026-10-05 实战验证）

## 六步管线
1. Spec 先行（页数/主题/信息源规范/体例 Token）
2. 画布定式：1280×720 固定，三行制 120px 1fr 48px，slide-main 必须 align-content: center
3. HTML 逐页落盘（design.css 统一样式，页脚标注编队锚点）
4. check-layout 校验：A/C 类清零，B 类按设计意图判定；ProxyError/SSLError 重试一次即通；API 配额 5/5，末轮以截图目检兜底
5. 三联自检：卡片（零卡壳）/配色（单一强调色）/装饰（仅釉点+页脚线两母题）
6. html-to-pptx 导出（-o 参数必填，slide_*.html glob 须在引号外）+截图目检

## 踩坑六条
1. head 行高必须 120px（写 108px 会被 A 类检出）
2. 轨道数=直接子节点数，混用 flex/grid 会报错
3. 同构并排块 justify-content: flex-start（居中会留缝）
4. 标题≥40px/正文≥22px/辅助≥18px 是硬底线
5. 长清单页右侧空洞要补信息增益列（如映射要点），不填纯装饰
6. 长英文条目压缩顺序：行距→line-height→作者缩写→gap，字号底线不破

## 青瓷谱牒 Token
bg #F2F1EC / fg #232522 / muted #DFE4DD / accent #3E6B62 / border #B9C4B6
母题=右上釉点+底部通栏 1px 线；背景 115° 淡釉纹 alpha 0.04；封面守藏方章。

## 实战成品
121 号令《数字边疆A2A编队治理简报》16 页；124 号令《数字边疆证据链》14 页（12 正文+2 参考文献全表）。
