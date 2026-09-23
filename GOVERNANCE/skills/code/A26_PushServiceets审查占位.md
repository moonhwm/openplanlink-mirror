# PushService.ets 审查——占位封装设计、AGC 降级轮询机制、实装步骤文档

## 一、审查范围与结论摘要

本篇为 harmony-app（代号铃语，鸿蒙适老化股票异动播报应用，bundleName 为 com.yehang.stockpulse，见 AppScope/app.json5）推送链路的代码审查知识资产。审查对象为以下三个文件，均在本审查当日完整通读：

- entry/src/main/ets/services/PushService.ets（107 行，Push Kit 集成封装）
- entry/src/main/ets/entryability/EntryAbility.ets（推送初始化、场景化消息接收、通知拉起链路）
- entry/src/main/ets/services/AlertPoller.ets（100 行，降级轮询兜底）

核心结论：占位封装设计成立，精确落实了项目"PushService.ets 保持占位封装，AGC 未配置前降级轮询"的不可逾越约束；探测式降级让实装动作收敛为"放入一个配置文件，端侧零改动"；降级链路闭环完整。同时发现 6 处可改进点（含 2 处死状态与 1 处硬编码），按优先级列于第六节；AGC 实装操作步骤列于第七节。

## 二、现状结构梳理

PushService.ets 全文单类、全静态成员，职责单一，结构如下：

| 成员 | 位置 | 职责 |
| --- | --- | --- |
| TOKEN_REPORT_URL | :11 | Token 上报端点（CloudBase push-token-register 云函数 HTTP 地址） |
| RETRYABLE_ERROR_CODES | :14 | getToken 可重试错误码集合（注释标明取自官方文档），共 4 个：1000900001、1000900008、1000900009、1000900011 |
| MAX_RETRY_COUNT / RETRY_INTERVAL | :15-16 | 最大重试 3 次、间隔 1000ms |
| tokenReported / retryCount | :25-26 | 静态状态字段 |
| init(context) | :28-40 | 入口：探测 AGC 配置，有则取 token，无则静默返回 |
| fetchToken() | :46-58 | getToken + 上报，失败进入重试判定 |
| handleTokenRetry(code) | :63-71 | 错误码可重试且未超 3 次时，setTimeout 1s 后重试 |
| reportToken(token) | :77-97 | POST 上报，失败仅记日志不影响主流程 |
| probeAgcConfig(context) | :99-106 | 读 rawfile/agconnect-services.json 判断 AGC 是否已配置 |

EntryAbility 侧对应三件事：onCreate 调用 PushService.init（:16-18）并再兜一层 catch；onCreate 补检冷启动 want 参数中的 alertId（:25-28，注释标明修复"冷启动点通知丢 alertId"缺陷）；registerPushMessageReceiver（:83-105）注册 DEFAULT 场景化消息接收，解析 data JSON 提取 alertId 写入 AppStorage。

## 三、占位封装设计评价：为什么"占位"是对的

1. **探测式降级，而非开关式降级。** probeAgcConfig 不读任何用户配置项，而是直接尝试 context.resourceManager.getRawFileContentSync('agconnect-services.json')（:101），文件存在且非空即认为 AGC 已配置，读取抛异常即返回 false（:103-105）。这使"实装动作"收敛为"往 rawfile 放一个文件"——端侧代码零改动，发布分支与占位分支天然合一。这是整个占位封装最有价值的设计决策。
2. **失败绝不外抛。** init 全程 try/catch，任何异常只记 hilog.warn（:37-39）；调用方 EntryAbility.onCreate 也再兜一层 catch（EntryAbility.ets:16-18）。推送初始化失败不阻断应用启动，保障"首屏永不空白"与轮询兜底可用，符合架构基调。
3. **重试口径显式收敛。** 只对注释标明来自官方文档的 4 个可重试错误码重试，上限 3 次、间隔 1 秒（:14-16、:63-71）；不可重试错误（如权益未开通类）直接放弃并记日志，避免对确定性失败做无意义循环。
4. **日志不泄密。** getToken 成功日志只打 token 长度不打明文（:49），上报请求体仅含 token 与 bundleName（:85），符合"不泄露任何 Token/密钥"的合规红线。
5. **无实例化设计。** 全静态成员表达"应用级单例服务"语义。代价是静态可变状态不利于测试，但在零三方依赖、单页面规模下是合理取舍。

## 四、AGC 降级轮询机制：降级链路全图

**判定与降级：** init() → probeAgcConfig() 返回 false（文件缺失或读取异常）→ 记日志 'agconnect-services.json absent, push degraded to polling'（:32）→ 直接 return，不触碰 getToken。

**兜底轮询：** Index.ets 的 pollLoop()（Index.ets:146-149）以 AlertPoller.getInterval()（基线 5000ms，AlertPoller.ets:28-30）循环调用 refresh() → AlertPoller.fetchLatest()。任何失败路径统一 applyBackoff()：间隔翻倍、封顶 30000ms（AlertPoller.ets:90-95）；成功后 resetBackoff() 复位 5000ms（:97-99）。因此推送未实装期间，前台 5 秒轮询是用户获知异动的唯一通道，退避保证弱网下不至于打爆服务端。

**双通道关系：** 推送实装后轮询保留作"拉齐补偿"（AlertPoller.ets:20-21 注释），两者非互斥——推送降低时延，轮询保证应用在前台时数据最终一致。这是架构基调明文设计，不应在实装后移除轮询。

**前台消息与拉起链路三入口统一：** alertId 从三条路径进入 AppStorage('pendingAlertId')：冷启动 onCreate want 参数（EntryAbility.ets:25-28）、热启动 onNewWant（:43-48）、前台 DEFAULT 推送消息（:91-94）。Index.checkPendingAlertId()（Index.ets:138-144）在 aboutToAppear 与 onPageShow 两个时机读取并 AppStorage.delete 消费，命中卡片后经 playById（:202-223）自动播报，且自动播报尊重播报开关（:212-215）与免打扰时段（:217-220）——用户关掉的、睡觉时，机器不吵人，这是适老化合规在链路上的落点。

**一处时序瑕疵：** registerPushMessageReceiver 在 onCreate 无条件调用（:30），不受 AGC 探测结果约束。未配置 AGC 时 receiveMessage 注册会抛异常，被 :101-104 的 catch 吞掉，行为无害但多一次无效异常路径，建议实装时改为探测通过后再注册。

## 五、与已知问题的对应关系

- **broadcast-a2a 的 Push 需换华为 Push Kit REST：** 本文件只负责"端侧收"（getToken/receiveMessage）与"token 上报"；服务端发送侧需由 X 服务器按华为 Push Kit REST API（token 定向推送、data 携带 alertId）重写，替换原 broadcast-a2a 推送出口。第七节步骤 6 涵盖。
- **alerts.json 的 audioUrl undefined 端侧按需调 generate-tts：** 与 PushService 无直接耦合；端侧已按"无 audioUrl 则隐藏播报钮"处理（Index.ets:390 的 if (item.audioUrl)），TTS 生成属数据链路问题，不在本审查展开。

## 六、发现的问题与改进建议（按优先级）

- **P1 bundleName 硬编码：** reportToken 请求体写死字符串 'com.yehang.stockpulse'（:85），与 AppScope/app.json5 的 bundleName 重复定义，改包名即静默断链。建议改读 context.applicationInfo（运行时取真实包名），至少提取常量并注释指回 app.json5。
- **P1 tokenReported 死状态：** :25 声明、:52 赋 true，全工程再无读取（本次以 grep 全仓核实，仅此两处）。应删除；或实装后升级为幂等开关——重复 init 时跳过 fetchToken，避免冷热启动叠加重试链。
- **P2 reportToken 无重试：** getToken 有 3 次重试，但 token 上报 HTTP 失败只记日志（:90-91、:93）。token 拿到而上报丢失意味着该设备永远收不到推送且无自愈机会。建议对上报失败复用同样延迟重试（3 次封顶）。
- **P2 setTimeout 不可取消：** handleTokenRetry 用裸 setTimeout 延迟重试（:67），期间若 init 被再次调用（如 Ability 重建）会叠加重试链。建议持有 timer 句柄，init 入口先 clearTimeout。
- **P3 同步 IO 在主线程：** getRawFileContentSync 于启动时同步读文件（:101）。文件小、仅一次，可接受；若 rawfile 日趋复杂应改异步。
- **P3 SDK 版本口径漂移：** 本仓库 build-profile.json5 实际配置为 compatibleSdkVersion 与 targetSdkVersion 均 "6.0.2(22)"；而项目宪法口径及既有技能文档 GOVERNANCE/skills/code/harmonyos-arkts-适老化开发.md 写的是"compatibleSdkVersion 20、targetSdkVersion 26"。两套口径并存，应在下次升版时统一对齐（本审查只提示，不擅改宪法）。

## 七、AGC 实装步骤（端侧零改动的落地清单）

1. AGC 控制台创建项目与应用：包名必须与 AppScope/app.json5 的 bundleName（com.yehang.stockpulse）完全一致；按 AGC 指引用 debug/release 证书分别登记 SHA-256 指纹。
2. 下载 agconnect-services.json，放入 entry/src/main/resources/rawfile/。放入后 probeAgcConfig 自动返回 true——此即占位封装的验收点，端侧无需改一行代码。
3. 在 AGC 开通 Push Kit 服务（增长 → 推送服务）。
4. 真机验证 getToken：观察 hilog TAG=StockPulse.PushService，应出现 'agconnect-services.json found, initializing Push Kit'（:35）与 'getToken succeeded, token length=…'（:49）；如命中可重试码，确认出现 'getToken retry n/3'（:66）且不超过 3 次。
5. 验证 token 上报：CloudBase push-token-register 云函数应收到 POST，body 含 token 与 bundleName，返回 200（对应 :87-88 日志 'token reported to server'）。
6. 服务端发送侧改造：X 服务器以华为 Push Kit REST 按 token 定向下发，data 字段携带 alertId；替换 broadcast-a2a 原推送出口；推送文案遵守合规红线（不承诺收益、不催促、不对外公开）。
7. 三链路验收：前台 DEFAULT 消息（AppStorage 链路）、后台点通知拉起（onNewWant）、冷启动点通知（onCreate want 参数），三者最终都应定位卡片并自动播报；播报关/免打扰时段下应静默但卡片可见可手动点听。
8. 回归降级路径：删除 rawfile 的 agconnect-services.json 重新构建，确认日志回到 'push degraded to polling' 且应用无崩溃、轮询正常。

## 八、验证清单

- [ ] agconnect-services.json 存在时出现 found + getToken succeeded 日志
- [ ] 文件缺失时出现 degraded 日志且无崩溃
- [ ] token 上报 200；非 200 与网络异常仅 warn 不重试（现状）/ 重试（实装改进后）
- [ ] 可重试码触发 ≤3 次重试，不可重试码直接放弃
- [ ] 三条 alertId 拉起链路均能定位并自动播报
- [ ] 全链路日志与请求体不含 token 明文与任何密钥

### 自我评估
- 正确性：4分 全部行号与行为描述来自本次实读的 PushService.ets、EntryAbility.ets、Index.ets、AlertPoller.ets 及 build-profile.json5；grep 核实了 tokenReported 死状态；错误码具体含义与 AGC 控制台操作细节按官方文档口径转述、未逐项实测，扣一分在此声明。
- 完整性：4分 覆盖结构梳理、设计评价、降级链路、问题清单、实装步骤、验证清单；服务端 Push Kit REST 发送侧只给方向与验收点，未给服务端代码（属端侧审查边界外）。
- 可复用性：4分 实装步骤可直接照做；问题清单带优先级与修法；探测式降级模式对任何"先占位后实装"的 Kit 集成都可平移复用。
- 字数：约3500字
- 使用模型：GLM-5.3-Flash
