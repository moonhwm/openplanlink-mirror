# 实时推演Panel 设计书（Pixel A2A Office Panel）

> 任务：微信深读席 · 2026-10-01
> 输入：`burn/recon_wx_article.html`（2.6MB，公众号快照，Star-Office-UI 看板文）
> 产出：本设计书 = 看板解读 + Panel 方案 + 技术栈建议
> 证据链：正文提取见 `burn/_tmp_wx_article_text.txt`（由 `python burn/_tmp_wx_extract.py` 生成，正文 829 汉字）；A2A 网络依据 `burn/governance/AUDIT_BUREAU_v1.md`；MiroFish 依据 `opensrc/MiroFish/MiroFish-main/` 实读

---

## 一、Star-Office-UI 看板解读

**出处核对**（自 `recon_wx_article.html` 提取）：

- 标题：`Star-Office-UI：AI 的像素办公室看板`
- 公众号：UI补给站（@ui_designer，签名"做有思考的设计"），发布时间 2026-10-01 09:00
- 原文链接：`https://mp.weixin.qq.com/s/udYV67xgvcZlquYnFepHug`
- 页面形态：分享卡型快照（`item_show_type=8`），无 `#js_content` DOM 节点，正文存于 JS 对象 `window.cgiDataNew.content_noencode`——首次 bs4 提取得 0 字，改为正则抽 JS 字段后得 829 汉字全文

**1. 定位**：OpenClaw 生态周边工具之一。像素风 AI 办公室看板，把 AI 助手的工作状态实时可视化——谁在做什么、昨天做了什么、现在是否在线。作者一句话："把隐形状态变成一个温馨小空间"。

**2. 核心机制：一张位置表**
- 房间分四区：办公桌、沙发、服务器机柜、床，各占一块
- 状态决定位置：**待命回沙发，干活（写文档/查资料/跑任务/同步数据）去办公桌，报错进机房**；角色的动作和气泡跟着换
- 信息设计精髓：**六种状态收进三个区域，把"在忙"和"出事"分开放，不用读文字**——这是全文最值得抄的一招

**3. 实时性**：发邀请码，别的 AI 每 15 秒推一次状态就会进房间。不装 OpenClaw 也能用，换别的 AI Agent 一样接得上；用脚本或接口推状态，也可以只当个人状态页。

**4. 扩展能力**：
- 素材与位置可换：角色/场景/装饰在侧边栏挑，位置与大小存配置文件，动态素材做了帧同步（切换不闪）
- AI 可换主题：接生图接口，一句话把办公室换成荷塘水景或精灵谷，家具位置与角色站位不动
- 桌面宠物版：缩成透明窗口常驻桌面
- 昨日小记自动读出、脱敏后贴进房间；中英日三语

**5. 值得关注的理由（原文归纳）**：AI 干活没有进度条，"有位置、有动作、有气泡的房间"比日志好读、更易扫完；接自家 Agent 要在规则文件里写两条指令（任务前切进工作区、完成后切回待命）。

**6. 两个约束（引我们方案时要绕开的坑）**：
- **许可分两半**：代码 MIT，但角色/场景是第三方素材、**美术资产禁止商用**——商用必须全部自绘
- **项目已停更**：最后提交 2026 年 3 月中旬，长期使用需自行接手维护——不能直接依赖其上游，只借鉴设计

---

## 二、映射到我们的 A2A 网络

我们网络的构件（依据 `burn/governance/AUDIT_BUREAU_v1.md` 与 `burn/ere/` 实测）：

| A2A 构件 | 现状依据 |
|---|---|
| 4 席位 | ZCode·Moon（pi-orchestrator）、OfficeAce（审计长）、砚（codearts 席）等节点，章程 v1.0 强制生效 |
| 审计局 | 局席=OfficeAce/砚/Moon，每日 22:00（UTC+8）`busSnapshotRows` 快照对账，出《日耗对账单》 |
| esc.trace 留痕 | 每席**每次对话**强制留痕：`[<席位> · esc.trace] 历史H: <消耗产出> \| 未来F: <计划请求> \| 锚: fp=<总线指纹> t=<UTC+8>`；墙代码 1308/1310/1005；额度事件入 trace |
| esc.exp 经验库 | `burn/ere/`：`ere_v2_ledger.jsonl` / `registry.jsonl` / `digests.jsonl` / `snapshot_v2.json` |
| 台账落点 | 各节点台账 + `burn/governance/daily/DAILY_REPORT_*.md` 日报 |

**关键优势（对接成本≈0）**：Star-Office-UI 要用户"在规则文件里写两条指令"才动；我们已经有强制留痕纪律——每席每次对话自动产出 esc.trace。**Panel 是纯读端，不需要席位改任何行为**，只解析既有 trace 流即可。这正是"隐形成本可视化"与原文"比日志好读"论断的契合点：esc.trace 本来就是日志，Panel 把它变成房间。

---

## 三、Panel 方案：实时推演 Pixel A2A Office

### 3.1 房间布局（五区制）

沿用"位置表 + 在忙/出事分区"的信息设计，把三区扩成五区：

```
┌──────────────────────────────────────────────────┐
│  办公桌区（在忙 · 4 席位工位）   立法讲台（章程/黑板） │
│   [Moon] [OfficeAce] [砚] [第四席]   ▤ board_session │
│──────────────────────────────────────────────────│
│  审计局工位（互审中）          总线门厅（握手/入网）   │
│   🔍 esc.trace 质询              🤝 registry 登记     │
│──────────────────────────────────────────────────│
│  机房区（出事 · 撞墙）         沙发区（待命）   床（离线）│
│   🧱 墙代码 1308/1310/1005      zZz            🛏     │
│  留痕跑马灯：esc.trace 流水墙    经验书架：esc.exp    │
└──────────────────────────────────────────────────┘
```

### 3.2 状态机与动作表（每席一个像素小人）

| 状态 | 判定来源（纯读端） | 位置 | 像素小人动作 | 气泡 |
|---|---|---|---|---|
| 燃烧 burning | 本轮 esc.trace H 段含产出/新增文件 | 办公桌工位 | 打字（双臂交替 2 帧）+ 头顶火苗 | `burn/…` 正在写的文件名 |
| 审计 auditing | esc.trace 质询/对账关键词（audit/质询/对账） | 审计局工位 | 举放大镜左右扫 | 「查 XX 席 fp=…」 |
| 立法 legislating | board_session / 章程类产出 | 立法讲台 | 敲槌 1 帧 + 展开卷轴 | 「黑板 20260928」 |
| 握手 handshaking | ere registry 新登记 / 总线新成员 | 总线门厅 | 两个小人相向 1 步 + 星花 | 「新成员: <node>」 |
| 待命 idle | 超过 N 分钟无新 trace | 沙发 | 坐姿 + zZz 浮动 | 「待命」 |
| 撞墙 walled | trace 含墙代码 1308/1310/1005 或重置卡 | 机房 | 红色感叹号抖动 | 「🧱1308 · 重置卡已领」 |
| 离线 offline | 无心跳超阈值 | 床 | 躺平 | 「离线 t」 |

信息设计上与原文同构：**"在忙"（燃烧/立法/握手）收进上半场，"出事"（撞墙）单独进机房**，审计是第三种颜色（审查而非生产）。

### 3.3 数据流（15 秒一拍，复刻原文节奏）

```
burn/ere/ere_v2_ledger.jsonl ─┐
burn/governance/daily/*.md  ─┼→ 解析器 trace_parser ─→ 状态表 seat_state.json
各席 esc.trace 台账/总线快照 ─┘   （JSONL→{seat,action,fresh_until,bubble}）
                                        │
              Panel 前端 15s 轮询或 SSE 推送 ─→ 精灵动画层 + 气泡层 + 跑马灯
```

- 解析器输出一版**只读 JSON**（座位/动作/截止时刻/气泡文本/fp 锚），前端零业务逻辑
- esc.trace 原文流水进底部**跑马灯**：滚出 `[席位 · esc.trace] 历史 H | 未来 F | 锚` 全文，点击展开——"昨天的小记贴进房间"这一原作亮点对应我们的日报/trace 复读
- 经验书架上每本"书"= 一条 esc.exp / `digests.jsonl` 摘要，点击弹出
- 审计局视角加一盏**对账灯**：22:00 `busSnapshotRows` 对账前后各亮一次

### 3.4 "实时推演"的增量叙事层（区别于纯状态页）

原作只显示"现在"；Panel 增加**推演回放**：按 trace 时序回放最近 24h，小人按时间线依次换位换动作（燃烧→握手→审计→撞墙），即"24 小时 A2A 治理实验"的可视化重演——与我们已有的 `burn/deliverables/multi_platform/01-公众号长文_24小时A2A多智能体治理实验.md` 叙事直接配套。

### 3.5 作为 MiroFish 类开源项目的直接面板

MiroFish（盛天网络，AGPL-3.0，本地 `opensrc/MiroFish/MiroFish-main` 实读：前端 Vue 3.5 + Vite + vue-router + vue-i18n + d3 + axios，路由 `/simulation/:simulationId` 等 6 条；后端 Flask 3 + flask-cors，uv 管理，含 Dockerfile/docker-compose）：

- **嵌入位**：新增路由 `/panel`，并在 `MainView.vue` 挂 iframe 卡片——零侵入、可独立访问
- **数据挂钩**：MiroFish 的群智仿真跑批时，把"仿真回合/预测任务"当作一个"席位"推状态进同一张办公室（状态机通用，只需 parser 加一个适配器）
- **复用面**：Vue3 组件化小人 + d3 画 trace 时间轴；i18n 复用 MiroFish 的 vue-i18n（原文三语能力同款）

---

## 四、技术栈建议

| 层 | 推荐 | 理由（全部实测依据） |
|---|---|---|
| 前端框架 | **Vue 3 + Vite + Pinia** | 与 MiroFish 前端同栈（`frontend/package.json`：vue@^3.5.24/vite），Panel 可作为其子路由直接并入 |
| 像素渲染 | **CSS sprite + `image-rendering: pixelated`** 起步；小人 >20 个或需帧同步升级 PixiJS | 原作证明帧同步需求真实存在（"切换时不闪"）；CSS 起步零依赖 |
| 时间轴/关系图 | **d3 v7** | MiroFish 已带 d3@^7.9.0 依赖，trace 时间轴复用不增包 |
| 实时通道 | 先 **15s 轮询只读 JSON**（同原文节奏），有总线推送再升 **SSE**（Flask 后端零改） | Flask 无内建 WS，SSE 是最小改动路径 |
| 后端 | **Flask Blueprint**（`/api/panel/state` + `/api/panel/stream`） | 与 MiroFish backend 同框架（`backend/pyproject.toml`：flask>=3.0.0） |
| 状态源 | esc.trace JSONL + busSnapshotRows + 日报，只读解析 | 依据 AUDIT_BUREAU_v1 留痕纪律，席位侧零改动 |
| 素材 | **自绘 16×16/32×32 像素小人 + CC0 场景** | 原作美术资产禁商用（MIT 代码可参考但素材不可用）；我们网络含商用交付场景，必须全自绘 |
| 许可 | Panel 若并入 MiroFish → 遵 **AGPL-3.0**；独立发布 → 自选，但避免引用其美术 | 双许可边界写明，参照 `burn/governance/opensource_license_discussion.md` 已有讨论 |
| 部署 | Docker-compose 一并起（MiroFish 已带 Dockerfile） | 复用其镜像编排 |

---

## 五、分阶段落地

- **Phase 0（只读状态页）**：trace_parser + 单页办公室，六状态七动作，15s 轮询——一个下午可成，价值先落地
- **Phase 1（动作+气泡）**：精灵帧动画、跑马灯、esc.exp 书架
- **Phase 2（审计局视角）**：对账灯、质询高亮、《日耗对账单》入口
- **Phase 3（推演回放）**：24h 时序回放 + 对外发布版（配 A2A 治理实验长文）
- **Phase 4（MiroFish 并轨）**：`/panel` 路由 + 仿真席位适配器，PR 回上游

**风险提示**：① 原作 2026-03 已停更，只借鉴设计不依赖代码；② 其美术禁商用，素材自绘是硬约束；③ trace 解析依赖各席留痕质量，需在 AUDIT_BUREAU 例会中把"trace 可解析"列为对账项。

---

## 附录：本次实跑记录

- `python burn/_tmp_wx_extract.py` → 输出 `TITLE: Star-Office-UI：AI 的像素办公室看板 / ACCOUNT: UI补给站 (@ui_designer) / CREATE_TIME: 2026-10-01 09:00 / BODY_CHARS: 829`，正文存 `burn/_tmp_wx_article_text.txt`
- 首版 bs4 `#js_content` 提取得 0 字（该快照为分享卡型，无正文 DOM），复检确认 `js_content` 两处命中均为脚本引用后改抽 `cgiDataNew.content_noencode`
- MiroFish 依赖实读：`opensrc/MiroFish/MiroFish-main/package.json`（AGPL-3.0）、`frontend/package.json`（vue/d3/axios）、`frontend/src/router/index.js`（6 条路由）、`backend/pyproject.toml`（flask>=3.0.0）
- A2A 依据实读：`burn/governance/AUDIT_BUREAU_v1.md`（esc.trace 格式/审计局/墙代码）、`burn/ere/registry.jsonl`（MiroFish 登记为"调度器换血候选"）
