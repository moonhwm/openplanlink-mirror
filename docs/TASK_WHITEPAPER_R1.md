# 行情播报工程 · 任务白皮书 R1（码道执行稿）

> 版本：R1.0（2026-09-14，白秉烛起草，机主批准）
> 执行席：码道 IDE · 鸿蒙开发智能体 · GLM-5.2-ArkTS-SPARK
> 本文档是本工程第一个正式任务包。执行前必须先读本工程根目录的 `AGENTS.md` 与 `CHANGELOG.md`，本白皮书与二者冲突时，以 `AGENTS.md` 的硬约束为最高法。

---

## 第一章 · 项目背景与使命

本工程名「行情播报」（StockPulse），是一台**适老化**的鸿蒙 NEXT 手机应用，服务对象为年长用户（下文称"老爷子"），他使用 Mate X5（HarmonyOS NEXT 纯血鸿蒙），不懂 K 线、不懂术语、不装飞书、不看服务器。

产品的全部价值浓缩为一句话：**让老爷子用最少的动作，知道自选股刚刚发生了什么，并且能"听"到一句人话解释。**

使用链路设计如下：云端服务器（待采购的华为云 X 实例，8 核 32G）秒级监测自选股行情 → 发现异动/策略信号 → 经华为 Push Kit 推送锁屏大字通知 → 老爷子点通知拉起 App → App 定位到对应异动卡片并自动播放云端合成的语音播报。在推送通道实装之前，App 前台运行时每 5 秒轮询一次服务端兜底。

合规边界：本应用私有分发（开发者调试证书直装，不上架、不公开、不收费）。内容分两类：fact（客观异动事实）与 signal（自家量化策略信号的白话解读）。**仍有三条不赦**：禁止收益承诺/保本类绝对化措辞；禁止「立即买入」「满仓」等催促性强指令；禁止任何对外公开或收费形态。信号卡必须带「自家信号」角标，与事实卡视觉区分。

## 第二章 · 现状盘点（你的起点）

工程已完成骨架首建（git 基线 `2bd56f9`），共 25 个文件。你必须先逐个阅读以下关键文件，理解已有设计后再动手：

- `AppScope/app.json5`：bundleName 为 `com.yehang.stockpulse`，应用名「行情播报」；
- `build-profile.json5`：compatibleSdkVersion 20 / targetSdkVersion 26，Stage 模型，runtimeOS=HarmonyOS；
- `entry/src/main/module.json5`：单 EntryAbility，竖屏，已声明 INTERNET 与 KEEP_BACKGROUND_RUNNING 权限；
- `entry/src/main/ets/model/AlertItem.ets`：**全工程最重要的文件**——数据契约。AlertItem 字段为 alertId / ts / symbol / name / direction(up|down|flat) / kind?(fact|signal，缺省 fact) / headline / detail / audioUrl?；AlertFeed 为 items + serverTs。服务端（Kimi Code 席在 quant-lab 目录开发）按此契约产出 JSON，任何一侧修改契约必须先停机主确认；
- `entry/src/main/ets/pages/Index.ets`：主页面。深色底大字卡片流，5 秒前台轮询（AlertPoller），点卡播放/停止音频（AudioPlayer），服务未连通时显示带「示例」字样的 DEMO_ITEMS 演示卡——**首屏永不空白是本工程的宪法级条款**；
- `entry/src/main/ets/services/PushService.ets`：Push Kit 占位封装，内有完整实装 TODO 注释；AGC 配置文件缺失时自动降级为仅日志。**本阶段保持占位，不展开实装**；
- `entry/src/main/ets/services/AlertPoller.ets`：http 轮询，FEED_URL 指向 `http://127.0.0.1:8000/api/alerts/latest` 占位地址，待 X 服务器落地替换；
- `entry/src/main/ets/services/AudioPlayer.ets`：AVPlayer 播云端 TTS 音频流，含 stop/release 防泄漏；
- `entry/src/main/ets/entryability/EntryAbility.ets`：onCreate 中初始化 PushService（降级容错），onNewWant 接收通知点击携带的 alertId 写入 AppStorage 键 `pendingAlertId`。

设计基调（已定型，勿推翻）：深色高对比（#101418 底、#1B222B 卡、红涨 #E64545、绿跌 #2BA471、金 #E8B339 点缀）、标题 34fp、正文 28fp、补充 22fp、卡片圆角 16、零三方依赖、纯 ArkTS。

## 第三章 · 本轮任务规格（R1：卡片流加固与链路核查）

本轮只做两件事：**把 Index.ets 的播报与容错做扎实** + **核查 EntryAbility 与 PushService 的对接完整性**。不允许顺手"优化"其他文件，不允许新增图表组件。

### 3.1 播报逻辑完善（Index.ets / AudioPlayer.ets）

1. **防连击**：卡片在音频加载/播放期间重复点击，不得产生多个 AVPlayer 实例或状态错乱；当前实现 togglePlay 是同步置位 + 异步播放，请补齐"加载中"中间态（建议 playingId 之外增加 loadingId 状态，加载中卡片显示「…」且忽略再次点击）；
2. **播放失败降级**：音频 URL 404、超时、格式不支持时，卡片显示短暂提示（如 headline 下方一行 22fp 红字「语音加载失败，点重试」），playingId 复位，不得闪退、不得卡在"播放中"假象；
3. **自动播报去重**：通知拉起（pendingAlertId）触发自动播报时，若该卡片无 audioUrl，静默跳过并清除 pendingAlertId，不得报错弹窗；
4. **生命周期正确性**：页面 aboutToDisappear 时已停止播放（现有），补充：播放中切换卡片、列表刷新导致正在播放的 item 消失（alertId 不在新 items 里）时，必须停止播放并复位 playingId；
5. **逐条实现后自检**：上述每条都在 CHANGELOG 条目中写明"如何验证的"（真机/预览器/代码走查均可，但要说清）。

### 3.2 异常容错（Index.ets / AlertPoller.ets）

1. **网络断开**：连续两次轮询失败，顶栏刷新时刻旁显示 20fp 灰字「连接中断，显示旧数据」；恢复成功后提示自动消失。**已有卡片必须保留显示**，严禁清空为空白页；
2. **空列表**：服务连通但 items 为空（全天无异动的正常情况），列表区显示居中大灰字「今日暂无异动」+ 一行 20fp 说明「监测进行中，有新情况会自动推送」；**注意与"服务未连通显示示例卡"是两个独立分支，不得混淆**——用 AlertPoller 返回外加一个连通标志区分（可让 fetchLatest 返回 `{ok: boolean, items: AlertItem[]}`，相应改 AlertItem 无关、只改 AlertPoller 返回类型与 Index 消费处）；
3. **超时与限流**：http 5 秒超时已配置，补充对 429/5xx 的处理：遇到 429 时本轮静默跳过、下轮正常重试，不得退避逻辑写死在页面层（如需退避，写在 AlertPoller 内）；
4. **JSON 解析失败**：服务端返回非法 JSON 时按"连通但无数据"不当处理——正确做法是按"连接异常"处理并记 hilog warn，保留旧卡片。

### 3.3 EntryAbility × PushService 对接核查（只查不改，除非有硬 bug）

1. 走查 onCreate → PushService.init → probeAgcConfig 全链路：确认 agconnect-services.json 缺失时 getRawFileContentSync 抛异常被 catch 住、降级日志正确打出；
2. 走查 onNewWant → AppStorage.setOrCreate('pendingAlertId') → Index.aboutToAppear 读取并删除 的时序：指出"App 未启动时点通知"与"App 在后台时点通知"两条路径是否都能到达自动播报；若发现 AppStorage 时序问题（页面已建好才 setOrCreate 导致 aboutToAppear 错过），允许最小改动修复（例如页面侧改为订阅 AppStorage 变化或在 onPageShow 再检查一次），并在 CHANGELOG 说明；
3. 检查 module.json5 权限声明与代码使用是否匹配（INTERNET 必需；KEEP_BACKGROUND_RUNNING 当前代码未实际使用，如确认无用可保留声明但注释说明，或删除——二选一，写明理由）；
4. **禁止**：解封 PushService 内的 TODO、引入 @kit.PushKit 真实调用、改动 Push Kit 占位封装结构。AGC 实装是后续 R3 阶段的任务，本轮不做。

### 3.4 UI 细化（只允许微调，不许改版）

1. 所有可点目标（卡片、听/停按钮）触摸热区不小于 48vp——卡片整卡可点已满足，检查「▶ 听 / ■ 停」文字在卡片内不单独设置小热区；
2. 「自家信号」角标（18fp 金字描边）已实装，检查其在长股票名（如「中国巨石」四字以上）时不挤压名称显示，必要时给名称 Text 加 layoutWeight(1) 与 maxLines(1) + TextOverflow.Ellipsis；
3. 暗色模式下读屏对比度自检：text_secondary(#B8C0CC) 在 card_background(#1B222B) 上须清晰可读，如觉不足可微调至 #C6CEDA，此为本轮唯一允许的色值变更；
4. 列表 space、卡片 padding 维持现状；不得添加阴影、渐变、动画特效（适老化原则：动效=干扰）。

## 第四章 · 验收标准（逐条可勾选，全部通过才算完成）

- [ ] V1：连点同一卡片 5 次，只起一次播放，状态不错乱；
- [ ] V2：audioUrl 指向不存在地址，卡片显示失败提示且可重试，App 不崩；
- [ ] V3：拔网两轮询周期，旧卡片保留 + 「连接中断」提示出现；插网后提示消失、列表刷新；
- [ ] V4：服务端返回空 items，显示「今日暂无异动」分支；服务不可达时显示示例卡分支；两者可区分；
- [ ] V5：播放中列表刷新剔除该 item，播放停止、状态复位；
- [ ] V6：带 alertId 拉起（模拟 onNewWant），对应卡自动播报；无 audioUrl 时静默跳过；
- [ ] V7：全盘 grep 确认无 PushKit 真实调用、无图表组件引入、AGENTS.md 未被改动；
- [ ] V8：`git log` 有本次提交，CHANGELOG.md 有规范条目。

## 第五章 · 禁止事项（违反任意一条=本轮作废）

1. 禁止修改 `AGENTS.md`；禁止改动 AlertItem/AlertFeed 字段定义（增删改字段都停机主确认）；
2. 禁止引入任何三方依赖（oh-package.json5 dependencies 保持空）；
3. 禁止引入 K 线图/走势图/任何数据可视化图表组件；
4. 禁止实装 Push Kit（保持占位封装与降级路径）；
5. 禁止把 FEED_URL 改为任何真实外网地址（保持 127.0.0.1 占位）；
6. 禁止删除 DEMO_ITEMS 首屏兜底机制；
7. 禁止大规模重排目录结构或重命名既有文件；
8. 禁止在代码与注释中出现任何买卖建议措辞（参见第一章三不赦）。

## 第六章 · 交付与留痕（干完必做）

1. `git add -A && git commit`，commit message 格式：`R1: <一句话总结>`；
2. `CHANGELOG.md` 追加条目，模板：

```markdown
## YYYY-MM-DD HH:mm · 码道（鸿蒙开发智能体/ArkTS-SPARK）· R1 卡片流加固

- 改了什么：<逐文件列出>；
- 为什么这么改：<对应本白皮书章节号>；
- 如何验证：<V1-V8 逐条对应结果>；
- 遗留：<没做完/发现但超范围的问题>。
```

3. 遗留问题写进 CHANGELOG「遗留」段，不要自行扩 scope 解决。

## 第七章 · 后续路线图（只读，本轮不做）

- R2：设置页（自选股管理、播报开关、字体再加一档特大号）；
- R3：Push Kit 实装（AGC 配置、token 上报、SUBSCRIPTION 类通知自分类申请）；
- R4：对接 X 服务器真实 FEED_URL 与云端 TTS 音频流，端到端联调；
- R5：卓易通 APK 降级版留档、调试证书年度续签提醒。

---

本白皮书 R1 完。执行中遇到与本文件矛盾的实际情况，以 CHANGELOG 留痕说明为唯一合法出口，禁止静默偏离。
