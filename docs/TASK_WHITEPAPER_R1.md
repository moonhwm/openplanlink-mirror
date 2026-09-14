# 行情播报工程 · 任务白皮书 R1（码道执行稿）

> 版本：R1.1 扩写版（2026-09-14，白秉烛起草，机主批准）
> 执行席：码道 IDE · 鸿蒙开发智能体 · GLM-5.2-ArkTS-SPARK
> 本文档是本工程第一个正式任务包。执行前必须先读本工程根目录的 `AGENTS.md` 与 `CHANGELOG.md`，本白皮书与二者冲突时，以 `AGENTS.md` 的硬约束为最高法。全文约四千五百字，请完整读完再动手，禁止跳读、禁止只读任务章节。

---

## 第一章 · 项目背景与使命

本工程名「行情播报」（StockPulse），是一台**适老化**的鸿蒙 NEXT 手机应用，服务对象为年长用户（下文称"老爷子"），设备为 Mate X5（HarmonyOS NEXT 纯血鸿蒙），画像三条：不懂 K 线与任何行情术语；不装飞书等办公应用、没有第二个通知通道；视力与精细触控能力下降，容不得小字、浅灰字和复杂手势。

产品的全部价值浓缩为一句话：**让老爷子用最少的动作，知道自选股刚刚发生了什么，并且能"听"到一句人话解释。**

完整使用链路：云端服务器（待采购的华为云 X 实例，8 核 32G）秒级监测自选股行情 → 发现异动或策略信号 → 经华为 Push Kit 推送锁屏大字通知（含铃声）→ 老爷子点通知拉起 App → App 定位到对应异动卡片并自动播放云端合成的语音播报。在推送通道实装之前，App 前台运行时每 5 秒轮询一次服务端兜底。这条链路涉及三方协作：云端监测与服务端出数由 Kimi Code 席在 `quant-lab/` 目录负责；端侧 UI 与播报由你（码道 IDE）在本工程负责；两侧之间唯一的接口是本工程的 `AlertItem.ets` 数据契约。

合规边界（第一章即定调，全文有效）：本应用私有分发（开发者调试证书直装，不上架、不公开、不收费）。内容分两类：fact（客观异动事实，如"中国巨石 2 分钟上涨 2.3%"）与 signal（自家量化策略信号的白话解读，如"动量策略今日目标"）。**三条不赦红线**：禁止收益承诺/保本类绝对化措辞；禁止「立即买入」「满仓」等催促性强指令；禁止任何对外公开或收费形态。信号卡必须带「自家信号」角标，与事实卡视觉区分——这条已实装，你只需维护不得拆除。

## 第二章 · 现状盘点（你的起点）

工程已完成骨架首建与两轮治理修订（git 基线 `d8feea4`，HEAD 即本白皮书提交）。动手前请逐文件阅读并自测理解（括号内是你读完后应能回答的问题）：

- `AGENTS.md`（分区主权是哪两家？五条硬约束各是什么？串行纪律三步是什么？）；
- `CHANGELOG.md`（最后一条是谁、改了什么、遗留什么？）；
- `AppScope/app.json5`：bundleName `com.yehang.stockpulse`，应用名「行情播报」；
- `build-profile.json5`：compatibleSdkVersion 20 / targetSdkVersion 26，Stage 模型，runtimeOS=HarmonyOS（这两个数字不许动）；
- `entry/src/main/module.json5`：单 EntryAbility、竖屏锁定、INTERNET 与 KEEP_BACKGROUND_RUNNING 两项权限声明；
- `entry/src/main/ets/model/AlertItem.ets`：**全工程最重要的文件**，数据契约。AlertItem 字段：alertId / ts / symbol / name / direction(up|down|flat) / kind?(fact|signal，缺省 fact) / headline / detail / audioUrl?；AlertFeed：items + serverTs。服务端按此契约产出 JSON。**任何一侧修改契约字段必须先停机主确认，你无权增删改**；
- `entry/src/main/ets/pages/Index.ets`：主页面。深色底大字卡片流、5 秒前台轮询、点卡播放/停止、「自家信号」金框角标、服务未连通时显示带「示例」字样的 DEMO_ITEMS 演示卡——**首屏永不空白是本工程宪法级条款**；
- `entry/src/main/ets/services/PushService.ets`：Push Kit 占位封装，内含完整实装 TODO 注释；AGC 配置文件缺失时自动降级为仅日志。**本阶段保持占位，不展开实装**；
- `entry/src/main/ets/services/AlertPoller.ets`：http 轮询封装，FEED_URL=`http://127.0.0.1:8000/api/alerts/latest` 占位，5 秒 connect/read 超时，destroy 防泄漏；
- `entry/src/main/ets/services/AudioPlayer.ets`：AVPlayer 播云端 TTS 流，静态单例，play 前先 stop 旧实例；
- `entry/src/main/ets/entryability/EntryAbility.ets`：onCreate 初始化 PushService（降级容错）；onNewWant 把通知携带的 alertId 写入 AppStorage 键 `pendingAlertId`，由 Index 页消费。

设计基调（已定型，勿推翻）：深色高对比（底 #101418、卡 #1B222B、红涨 #E64545、绿跌 #2BA471、金 #E8B339 点缀）、标题 34fp、卡内主文 28fp、补充 22fp、卡片圆角 16vp、内边距 20、零三方依赖、纯 ArkTS、无动画无阴影无渐变（适老化原则：一切动效都是干扰）。

## 第三章 · 本轮任务规格（R1：卡片流加固与链路核查）

本轮只做两件事：**把 Index.ets 的播报与容错做扎实**、**核查 EntryAbility 与 PushService 的对接完整性**。不允许顺手"优化"其他文件，不允许新增图表组件，不允许重排目录。

### 3.1 播报逻辑完善（Index.ets / AudioPlayer.ets）

1. **防连击**：卡片在音频加载/播放期间被重复点击，不得产生多个 AVPlayer 实例或状态错乱。现状 togglePlay 是同步置位+异步播放，存在"prepare 未完成时连击"窗口。要求：playingId 之外增加 loadingId 状态；进入 play 流程先置 loadingId，卡片显示「…」且该卡忽略再次点击；prepare 成功后 loadingId 转 playingId；失败则两者皆复位。参考 API 时序：`createAVPlayer → url 赋值 → prepare（异步）→ play`；
2. **播放失败降级**：音频 URL 404、超时、格式不支持（AVPlayer on error 回调或 prepare reject）时，卡片 headline 下方显示一行 22fp 红字「语音加载失败，点重试」，状态复位；不得闪退、不得卡在"播放中"假象。失败提示在下一次点击或下一轮成功刷新后清除；
3. **自动播报去重与静默**：pendingAlertId 触发的自动播报，若目标卡无 audioUrl，静默跳过并立即清除 pendingAlertId；若目标 alertId 不在当前列表，同样静默清除，不得弹窗报错；
4. **生命周期正确性**：页面 aboutToDisappear 停止播放（现有，保持）。补充两条：播放中切换卡片即旧停新起（现状已对，验证之）；**列表刷新后若正在播放的 alertId 已不在新 items 中，必须停止播放并复位**（异动过期被服务端撤下是真实场景）；
5. **自检义务**：上述每条在 CHANGELOG 写明"如何验证"（真机/预览器/代码走查均可，须说清手段与结论，禁止"已验证"式占位语）。

### 3.2 异常容错（Index.ets / AlertPoller.ets）

1. **连通性建模（本轮唯一允许的类型改动）**：把 `AlertPoller.fetchLatest` 返回类型改为 `{ ok: boolean; items: AlertItem[] }`——ok=false 表示网络/HTTP 异常，ok=true 且 items 为空表示"连通但无异动"。**AlertItem/AlertFeed 契约字段本身一个字不许动**，只动 AlertPoller 的返回包装与 Index 的消费处；
2. **网络断开**：连续两轮 ok=false，顶栏刷新时刻旁显示 20fp 灰字「连接中断，显示旧数据」；恢复 ok=true 后提示消失。**已有卡片必须保留**，严禁清空为空白页；
3. **空列表分支**：ok=true 且 items 为空时（全天无异动的正常情形），列表区居中大灰字「今日暂无异动」+ 一行 20fp「监测进行中，有新情况会自动推送」。**此分支与"服务未连通显示示例卡"是两个独立分支，不得混淆、不得互相覆盖**；
4. **429/5xx 处理**：HTTP 429 本轮静默跳过、按 ok=false 计但不计入"连接中断"提示的触发（限流是服务端姿态，不应惊动老爷子）；5xx 按普通失败计；如需退避，写在 AlertPoller 内部（如失败后下一轮间隔翻倍、封顶 30 秒），页面层不得出现退避逻辑；
5. **JSON 解析失败**：按 ok=false 处理并 hilog warn 记原文前 200 字符，保留旧卡片。禁止把解析失败误判为空列表。

### 3.3 EntryAbility × PushService 对接核查（只查不改，硬 bug 除外）

1. 走查 `onCreate → PushService.init → probeAgcConfig` 全链路：确认 agconnect-services.json 缺失时 `getRawFileContentSync` 抛出的异常被 catch、降级日志正确输出 hilog info 级；确认 init 的 catch 不会吞掉其他意外错误而无任何痕迹；
2. 走查 `onNewWant → AppStorage.setOrCreate('pendingAlertId') → Index.aboutToAppear 读取并删除` 的时序，回答两条路径：**App 冷启动点通知**（onCreate→onWindowStageCreate→aboutToAppear，参数经 launchParam 还是 onNewWant？冷启动 want 在 onCreate 拿到，当前代码只在 onNewWant 处理——这是需要你核查并如实报告的潜在缺口）与 **App 在后台点通知**（onNewWant 先于或晚于页面 aboutToAppear？若页面早已建好，aboutToAppear 不会再跑，pendingAlertId 将滞留——建议页面侧改为在 onPageShow 也检查一次，或订阅 AppStorage 变化；选其一最小改动实现并说明理由）；
3. 权限匹配核查：INTERNET 必需（轮询与音频流）；KEEP_BACKGROUND_RUNNING 当前代码未实际调用对应 API——二选一处理：删除该声明，或保留并在 module.json5 相邻注释说明"为 R3 推送播报预留"。写明你选哪条及理由；
4. **禁止**：解封 PushService 内 TODO、引入 @kit.PushKit 真实调用、改动占位封装结构。AGC 实装是 R3 任务，本轮不做。

### 3.4 UI 细化（只微调，不改版）

1. 触摸热区：所有可点目标不小于 48vp；卡片整卡可点已满足，检查「▶ 听 / ■ 停」文字不单独设置小热区、不拦截卡片点击；
2. 长名防挤压：「自家信号」角标已实装；给名称 Text 加 `layoutWeight(1)`、`maxLines(1)`、`TextOverflow.Ellipsis`，确保四字以上名称（如"中国巨石"）不顶飞角标与按钮；
3. 对比度微调：text_secondary(#B8C0CC) 在 #1B222B 上若偏弱，可调至 #C6CEDA——**本轮唯一允许的色值变更**，其他色值一律不动；
4. 维持既有 space/padding/圆角；不得添加阴影、渐变、入场动画、加载 spinner（加载中用「…」文字即可）。

## 第四章 · 验收标准（逐条勾选，全过才算完成）

- [ ] V1：连点同一卡片 5 次，只起一次播放，loadingId/playingId 不错乱；
- [ ] V2：audioUrl 指向不存在地址，显示失败提示且可重试，App 不崩；
- [ ] V3：断网两轮询周期，旧卡片保留 +「连接中断」提示出现；复网后提示消失、列表刷新；
- [ ] V4：空 items 显示「今日暂无异动」；服务不可达显示示例卡；两分支可独立复现；
- [ ] V5：429 响应不惊动界面；播放中列表剔除该 item 时播放停止、状态复位；
- [ ] V6：冷启动与后台两条拉起路径带 alertId 均能自动播报；无 audioUrl 静默跳过；
- [ ] V7：全工程 grep 无 PushKit 真实调用、无图表组件、AGENTS.md 零改动、AlertItem 契约零改动；
- [ ] V8：git log 有本次提交，CHANGELOG.md 有合规格式的条目。

## 第五章 · 禁止事项（违反任意一条=本轮作废）

1. 禁止修改 `AGENTS.md`；禁止改动 AlertItem/AlertFeed 字段（§3.2.1 的返回包装改动是唯一豁免）；
2. 禁止引入三方依赖（oh-package.json5 dependencies 保持空）；
3. 禁止引入 K 线图/走势图/任何图表组件；
4. 禁止实装 Push Kit；5. 禁止把 FEED_URL 改为真实外网地址；6. 禁止删除 DEMO_ITEMS 首屏兜底；
7. 禁止重排目录、重命名既有文件；8. 禁止代码与注释中出现买卖建议措辞（第一章三不赦）；
9. 禁止静默偏离：实际情况与本文件矛盾时，唯一合法出口是 CHANGELOG 留痕说明。

## 第六章 · 交付与留痕（干完必做）

1. `git add -A && git commit -m "R1: <一句话总结>"`；
2. `CHANGELOG.md` 追加条目，模板：

```markdown
## YYYY-MM-DD HH:mm · 码道（鸿蒙开发智能体/ArkTS-SPARK）· R1 卡片流加固

- 改了什么：<逐文件列出>；
- 为什么这么改：<对应本白皮书章节号>；
- 如何验证：<V1-V8 逐条结果>；
- 遗留：<未做完/发现但超范围的问题>。
```

3. 遗留问题写入「遗留」段即完成交接，禁止自行扩 scope 解决。

## 第七章 · 后续路线图（只读，本轮不做）

- R2：设置页（自选股管理、播报开关、特大字体档）；
- R3：Push Kit 实装（AGC 配置、token 上报、SUBSCRIPTION 通知自分类申请，约 15 工作日）；
- R4：对接 X 服务器真实 FEED_URL 与云端 TTS，端到端联调；
- R5：卓易通 APK 降级版留档、调试证书年度续签提醒。

## 第八章 · 术语表（防语义误读）

- **异动**：价格/量能在短窗口内的统计显著偏离，由服务端判定，端侧不定义阈值；
- **播报**：播放云端合成的 TTS 音频流，端侧不做本地 TTS；
- **占位封装**：接口已留、实现为日志降级、待配置到位后解封的代码形态；
- **首屏永不空白**：任何网络状态下页面都有确定内容（真实卡/空态字/示例卡三分支）；
- **自家信号**：机主私有量化策略输出，仅供自家设备展示，非投资建议。

## 第九章 · 风险登记与回退

- 风险一：AVPlayer 状态机在预览器与真机行为差异——回退：全部失败路径以 on error 回调为准，不依赖 stateChange 时序假设；
- 风险二：AppStorage 拉起时序在 API 20 与 26 间有差异——回退：onPageShow 双检查方案优先于订阅方案；
- 风险三：本轮改动意外破坏 DEMO 兜底——回退：`git revert` 本轮提交，骨架随时可回 d8feea4 之前的 2bd56f9；
- 总回退锚：git 基线 b593f96（纯骨架）/ 2bd56f9（信号松绑）/ d8feea4（本白皮书），任一可回。

---

本白皮书 R1 完。执行中遇到矛盾，CHANGELOG 留痕是唯一合法出口。
