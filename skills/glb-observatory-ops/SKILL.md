---
name: glb-observatory-ops
description: "观模台规程——把本地 GLB 3D 模型注造为零外部 CDN 的单文件观展页（three.js 全链本地 vendor + 自制轨道控制 + 加载进度 + 实机渲染验证）。触发（满足任一）：①用户说「把这个 glb/3D 模型做成网页」「模型上站」「3D 观展页」「GLB viewer」或等价表述；②手头有 .glb/.gltf 资产需要浏览器可开的展示页且要求离线可用/零外链时；③需要在已有静态站内新增 3D 展示子页并纯增量接回索引时。覆盖：vendor 链获取与导入符改写、模型归一化落台、三灯布光、极简轨道控制、swiftshader 实渲验证、版本快照交付。不覆盖：React/全栈 3D 应用脚手架（归 webapp-building 链）；模型生成/修模本身（归 Tripo 等生成域）；多模型展厅级状态管理。中文名：观模台规程。English triggers: GLB viewer page, three.js local vendoring, zero-CDN 3D page, model observatory."
metadata:
  version: "1.1.1"
---

# 观模台规程（glb-observatory-ops）

> 立法锚：**「模型本地、渲染本地、验证实机——零外链不是口号，是逐文件的导入符改写。」**
> 溯源：2026-10-06 R74 实战固化（守藏人自体_3D_v1.glb 21.4 MB 首展，swiftshader 实渲通过，pageerrors=0）。
> v1.1.0（2026-10-07 R75 群评迭代）：skill-creator-swarm 第五步群评一轮（with_skill vs baseline 盲评，机检门禁全绿 vs 基线一处 xmlns 误伤出局；盲评基线凭「截图自证」险胜）。修订四项：①模板内置页内自证仪表（`window.__pageErrors` + dataset 旗标 + 截图内状态行 + 页脚运行时渲染器串），验证证据从「笔记声称」升为「截图自携带」；②模板内置 `data:,` favicon，灭 favicon 404 噪声；③check_page.py 豁免 XML 命名空间标识符（`www.w3.org/...`，data-URI SVG 内，不产生网络请求）；④断言四件扩为六件（加截图自证行与程序化交互后机位变化），留痕增记失败路径。评估底稿在 `/mnt/agents/output/glb-eval-workspace/iteration-1/`。
> v1.1.1（2026-10-08 R76 勘正）：R76 回炉实战揪出 v1.1.0 三处修订未落盘（模板回调自证段、recipe 失败路径段、SKILL.md 失败模式三行）——根因：**同文件并行 edit_file 竞态丢更新**（各 edit 基于原文计算、后写覆盖先写）。已全部串行重修并逐条即验。新纪律：**同一文件的多次 edit_file 严禁并行，且每次编辑后立即回读断言**；技能文件改完必跑「预期标记词全数在场」清点。

## 五条铁律（不可裁剪）

1. **运行时零外部 CDN**：three.js/GLTFLoader 全部本地 vendor；构建期可联网取件，运行时一个外链都不许有。交付前 `grep -noE 'https?://[^"'\'' ]+' page.html` 清空（注释铭文除外）。
2. **版本对齐**：GLTFLoader 必须与 three.module.js 同 REVISION（查 `REVISION = 'NNN'`）；r150+ 的 GLTFLoader 还依赖 `../utils/BufferGeometryUtils.js`，漏件即运行时空白。
3. **导入符改写是必做工序**：vendor 后把 `from 'three'` 等裸导入改写为相对路径，改写用「精确替换 + count==1 断言」，禁肉眼改。
4. **实机验证才作数**：node --check 只证语法；必须 Playwright（chromium+swiftshader）渲染截图确认模型可见；**`preserveDrawingBuffer` 默认 false，canvas 读像素/drawImage 读回全黑是读数假象，不是缺陷——以截图为准**（references/verification-recipe.md）。
5. **诚实标注**：页面铭文写明模型文件名/大小/来源（生成工具/授权），加载期明示体积与耗时预期；不把本地资产说成「云端」。

## 工作流（四环）

1. **盘点**：定位 GLB 资产与站内既有 vendor（先找 `three.module*.js` 复用同版本）；无则 `scripts/vendor_three.py --rev 170 --dest <page>/vendor/` 一键取件+改写（构建期联网）。
2. **注造**：以 `assets/viewer-template.html` 为母本——占位符 `{{TITLE}}` `{{GLB_PATH}}` `{{ASSET_NOTE}}` `{{ACCENT}}`；模型归一化（包围盒缩放+落台）与三灯布光已内置，轨道控制为自制极简实现（拖拽旋转/滚轮推拉/双击归位/自动缓转），不引 OrbitControls addon。
3. **验证**：`scripts/check_page.py <page>`（抽 module 脚本 node --check + 外链 grep + 本地引用清点）→ Playwright 实渲（断言六件见 references/verification-recipe.md §3：遮罩消失、HUD 非空、截图可见模型、pageerrors=0、截图内含自证状态行、程序化交互后机位变化）。
4. **交付**：拷入 `/mnt/agents/output/app/` 目标位 → 索引页纯增量接回（只加不改现有链接）→ website_version_manager 快照（html 类型，project_dir=含 index.html 目录）→ 只展示其返回结果，不自造 URL。

## 失败模式（if-then）

| 触发 | 处置 |
|---|---|
| 页面白屏、console 报 `Failed to resolve module specifier 'three'` | 导入符未改写或改写路径错——回工作流第 1 步重跑 vendor_three.py |
| GLTFLoader 404 `BufferGeometryUtils.js` | 漏 vendor 依赖件；r150+ 必带 utils/ 子目录 |
| 截图全黑但 HUD 有统计 | 多为灯光/相机落位问题：查包围盒归一化与 `fitDist`；**勿信 canvas 读像素**（铁律 4） |
| 模型载入超长无反馈 | GLB >20 MB 时进度条按 `ev.loaded/ev.total` 驱动；确认服务器支持 Range/流式，本地 file:// 直开亦可 |
| 索引接回后旧链接 404 | 接回只许纯增量；任何既有 href 变动即刻回滚 |
| console 报 favicon.ico 404 | 模板已内置 `data:,` favicon；旧页补 `<link rel="icon" href="data:,">`，勿在笔记里辩解 |
| `chromium --headless --screenshot --virtual-time-budget` 超时无产出 | rAF 无限渲染循环在虚拟时间下逐帧软渲，大模型必超时——走 references/verification-recipe.md §2 Playwright 配方，失败路径记入留痕 |
| 验证只有笔记声称 pageerrors=0 | 证据须自证：模板 `#vstatus` 状态行进截图，dataset 旗标供脚本断言（断言六件，recipe §3） |

## 资源

- `scripts/vendor_three.py` — 取件+导入符改写一体（指定 REVISION 与目标目录）
- `scripts/check_page.py` — 语法/外链/本地引用三检
- `assets/viewer-template.html` — 观展页母本（暗色台位审美，占位符四套）
- `references/verification-recipe.md` — swiftshader 实渲验证配方与读数假象判例

## 诚实边界

- 本件管「GLB→观展页」的注造与验证纪律；模型质量归生成侧，本件不美化模型缺陷（HUD 如实报网格数/面数）。
- 母本审美为暗色台位风，换肤改 `{{ACCENT}}` 与 CSS 变量即可，但每页仍须先定一句话视觉语言再动工（反 slop）。
- 21 MB 级资产首次载入数秒属物理事实，页面须明示，禁伪装瞬时。
