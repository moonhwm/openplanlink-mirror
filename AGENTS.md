# AGENTS.md —— 任何 AI 编辑器进入本工程前必读（共治契约 v1.0，2026-09-14）

本工程会被多个 AI 席位编辑（码道 IDE·鸿蒙开发智能体 / Kimi Code / Kimi Work 桌面席）。
为防止不同 AI 的架构风格互相踩踏，**先读完本文件再动手；动手前先看 CHANGELOG.md 最新条目**。

## 一、分区主权（不可越界）

| 目录 | 主权席 | 职责 |
|---|---|---|
| `harmony-app/`（本工程） | 码道 IDE（鸿蒙开发智能体 + ArkTS-SPARK） | 端侧 UI、播报交互、Push 封装 |
| `quant-lab/`（工作区外另一目录） | Kimi Code（顾权席） | 取数、策略、监测、服务端出数 |
| 接口边界 | **本文件 + `entry/src/main/ets/model/AlertItem.ets`** | 服务端产出 AlertFeed JSON 契约 |

越界规则：任何一方要动对方目录或改 AlertItem/AlertFeed 契约，须先在 CHANGELOG.md 写明意图并停机主确认。

## 二、硬约束（改代码不许破坏）

1. **适老化**：主界面=大字白话卡片流（28-34fp 高对比深色底），**禁止引入 K 线图/走势图等复杂图表组件**；点卡=听播报。
2. **红线**：只报客观异动事实（涨跌幅/量能/价格穿越），**禁止任何买卖建议措辞**。
3. **平台**：Stage 模型，`compatibleSdkVersion 20` / `targetSdkVersion 26`，纯 ArkTS，零三方依赖。
4. **PushService.ets 保持占位封装**：AGC 未配置前自动降级轮询，不得展开实装（实装步骤在 README「推送实装」）。
5. **首屏永不空白**：服务未连通时必须显示带「示例」字样的演示卡（现有 DEMO_ITEMS 机制）。

## 三、串行纪律

同一时间只允许一个 AI 席位在本工程写代码。开工前：
1. `git status` —— 有未提交改动先读 CHANGELOG 判断是谁的活，未明即提交快照再动手；
2. 读 CHANGELOG.md 最后一条；
3. 干完立即 `git add -A && git commit`，并在 CHANGELOG.md 追加条目（谁/何时/改了什么/为什么/遗留什么）。

## 四、架构基调（已定型，勿推翻）

- EntryAbility：Push 初始化 + onNewWant 带 alertId 拉起定位；
- Index.ets：List 卡片流 + 5s 前台轮询（AlertPoller）兜底；
- AudioPlayer：AVPlayer 播云端 TTS 音频流；
- 数据源：FEED_URL 待 X 服务器落地后替换，契约即 AlertFeed。

改进可以做，推翻须机主批准。
