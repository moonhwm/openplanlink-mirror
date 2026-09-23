# A32 生命周期管理审查——aboutToAppear/aboutToDisappear、资源释放、内存管理

> 项目：harmony-app（鸿蒙适老化股票异动播报应用「铃语」），纯 ArkTS + 云函数，零三方依赖。
> 本篇自包含：所有结论引用仓库文件与行号，不依赖对话记忆。架构基调不改：EntryAbility=Push 初始化+onNewWant 带 alertId 拉起定位；Index.ets=List 卡片流+5s 前台轮询 AlertPoller 兜底；AudioPlayer=AVPlayer 播云端 TTS 音频流。

## 一、生命周期全景与审查方法

本应用生命周期分两层。**UIAbility 层**（`entry/src/main/ets/entryability/EntryAbility.ets`）：`onCreate`（13-31 行）做 Push/Settings 异步初始化、冷启动 alertId 补检、注册推送接收器；`onWindowStageCreate`（33-41 行）加载 `pages/Index`；`onNewWant`（43-69 行）处理通知与小艺 action 拉起；`onForeground`（71-76 行）仅打日志，`onBackground` 未实现（grep 实证全仓库仅一处 onForeground）。**页面层**（`entry/src/main/ets/pages/Index.ets`）：`aboutToAppear`（98-102 行）加载设置+启动轮询+消费拉起信号；`onPageShow`（104-108 行）重读设置+再消费；`aboutToDisappear`（110-116 行）清定时器+停播。子页 Settings.ets 仅有 `aboutToAppear`（43-45 行）。

审查方法：逐文件通读，对定时器、AVPlayer、Preferences、HTTP 句柄四类资源做「创建-释放」配对核对，对每条异步链做时序推演。

## 二、生命周期触发矩阵与挂接点

| 事件 | 触发时机 | 本项目挂接点 | 挂接质量 |
|---|---|---|---|
| UIAbility.onCreate | 冷启动首建 | EntryAbility.ets:13-31 | 已挂 |
| onWindowStageCreate | 窗口首建 | EntryAbility.ets:33-41 | 已挂 |
| onNewWant | 热启动单例再入 | EntryAbility.ets:43-69 | 已挂 |
| onForeground | 回前台 | EntryAbility.ets:71-76 | 已挂但仅日志 |
| onBackground | 切后台 | 无 | **缺失（P1-F）** |
| aboutToAppear | 组件首建 | Index.ets:98；Settings.ets:43 | 已挂 |
| onPageShow | 页面每次可见 | Index.ets:104 | 已挂 |
| aboutToDisappear | 组件销毁 | Index.ets:110 | 已挂 |
| NavDestination onShown/onHidden | 子页每次显隐 | 未挂 | 缺失（见第七节） |

页面层与 Ability 层是「父子再包一层」的关系：页面生命周期只在 Ability 前后台翻转或页面级切换时触发，同一页面内部 Navigation 出入栈不惊动它——这条机理是本篇 3.1 竞态、第六节后台缺口与 A31 P1-3 的共同根源，先在此立据。

## 三、want 参数双路径与拉起时序

通知/小艺拉起携 alertId 进入应用有两条互斥路径，本项目两条都已覆盖：冷启动走 `onCreate` 的 want（`EntryAbility.ets:25-28`，注释 23-24 行明确这是补原代码只处理 onNewWant 的缺口）；热启动走 `onNewWant`（45-48 行）。两条路径收口到同一个 AppStorage 键 `pendingAlertId`，再由页面层 `checkPendingAlertId`（`Index.ets:138-144`）消费并删除，先删后用的顺序保证重复触发安全，设计自洽。

两个细节点评：其一，取参写法 `want?.parameters?.alertId as string | undefined`（25、45 行）全链路可选链 + 判空，无空指针风险，是好范本；其二，小艺三个 action（50-68 行）中 `PLAY_AUDIO` 额外写的 `autoPlay`（66 行）全仓库无消费者（grep 实证仅此一处命中），属孤立信号，处置建议见 A31 P2-3。**前台推送路径的时序缺口**：应用在前台收到 DEFAULT 推送时，接收器（EntryAbility.ets:83-99）仅写 pendingAlertId，而它的两个消费点都在页面生命周期回调里，前台常驻场景二者均不触发，自动播报失效——完整论证与整改代码见 A31 P1-4，此处从生命周期视角补充结论：**凡是「写 AppStorage 等页面回调来消费」的设计，都必须确认消费回调在目标场景真的会触发**，否则信号悬空。

## 四、aboutToAppear 审查

### 4.1 初始化时序竞态（发现 P1-A：init 与首帧读配置赛跑）

`EntryAbility.onCreate` 中 `SettingsService.init(this.context)` 异步且未 await（`EntryAbility.ets:20-22`），内部 `preferences.getPreferences`（`SettingsService.ets:72-79`）走 IPC 需要时间；紧接着 `onWindowStageCreate` → `loadContent` → Index `aboutToAppear` 执行 `loadSettings()`（`Index.ets:98-99`），内部十连发 `SettingsService.getXxx()`。时序推演四步：t0 onCreate 发起 init；t1 loadContent 同步执行、页面构建启动；t2 aboutToAppear 调 loadSettings，此刻 pref 仍为 null，全部 getter 走默认值分支（如 `SettingsService.ets:84-86` 返回空自选、136-139 返回标准字体档）；t3 getPreferences 才 resolve，但无人再触发重读（要等 onPageShow）。后果：老用户已保存的特大字体在首帧闪回标准档再跳回，对以大字为生命线的适老化应用是可感缺陷，且自选股过滤（`Index.ets:161-163`）首帧不生效。

整改：SettingsService 暴露就绪 Promise，两处共用：

```typescript
// SettingsService.ets
private static readyPromise: Promise<void> | null = null;
static ready(): Promise<void> {
  if (!SettingsService.readyPromise) {
    SettingsService.readyPromise = SettingsService.doInit(); // 原 init 逻辑改名迁入
  }
  return SettingsService.readyPromise;
}
// Index.loadSettings 首行：await SettingsService.ready();
```

EntryAbility.onCreate 仍调用 init 预热（内部转调 ready），架构不动。

### 4.2 loadSettings 无 await、无外层 catch（发现 P2-B）

`Index.ets:98-101` 对 async 的 `loadSettings()/pollLoop()` 均为 fire-and-forget。各 getter 内部已 try-catch 吞错并返回默认值（如 `SettingsService.ets:90-93`），风险被压到很低；但 `loadSettings` 中段同步逻辑若抛错（如 124-132 行的免打扰计算）即成为 unhandled rejection 且无日志。整改一行：`loadSettings().catch((e) => hilog.warn(DOMAIN, TAG, 'loadSettings failed: ' + (e as Error).message))`。

### 4.3 初始化三件套的顺序（合规）

`aboutToAppear` 内先 `loadSettings`（拿播报开关/免打扰状态），再 `pollLoop`（首轮 refresh 会用到 watchlist 过滤），最后 `checkPendingAlertId`（播报判断依赖 broadcastEnabled/dndActive 已就位）。三步顺序正确；因 loadSettings 是 async 未 await，首轮 refresh 与设置读取实际并行，watchlist 过滤可能首轮不生效——与 4.1 竞态同源，`ready()` 修复后建议把 pollLoop 挪到 loadSettings await 之后串行，代价仅几十毫秒。

### 4.4 Settings 页 aboutToAppear（正常带前提）

`Settings.ets:43-45` 仅重读配置，无资源创建，无需配对释放。正确性依赖「每次入栈新建实例、无复用」；若未来引入组件复用须改挂 NavDestination 的 onShown，登记为约束（同 A31 6.1）。

## 五、aboutToDisappear 审查

### 5.1 定时器清理的复活漏洞（发现 P0-C：轮询在页面销毁后复活）

`aboutToDisappear` 执行 `clearTimeout(this.timer)`（`Index.ets:111-114`），但轮询是异步自递归：`pollLoop` 先 `await this.refresh()`（152 行，内部网络请求 5s 超时量级）再注册下一轮 `this.timer = setTimeout(...)`（148 行）。时序推演：t0 第 N 轮 refresh 开始，await 悬挂；t1 页面销毁，clearTimeout 清掉的是**已执行完的第 N-1 轮句柄**（无效操作）；t2 refresh resolve 返回；t3 代码继续走到 148 行注册新定时器——轮询复活且永不停止，闭包持有已销毁组件，流量电量内存三重泄漏。当前单页结构里 Index 销毁罕见，但该模式是公共隐患，任何未来接入 pollLoop 的子页都会踩中，必须按 P0 修。

整改：停止标志 + 每轮先查：

```typescript
private stopped: boolean = false;
aboutToDisappear(): void {
  this.stopped = true;
  if (this.timer >= 0) { clearTimeout(this.timer); this.timer = -1; }
  AudioPlayer.stop();
}
private async pollLoop(): Promise<void> {
  if (this.stopped) { return; }
  await this.refresh();
  if (this.stopped) { return; }
  this.timer = setTimeout(() => this.pollLoop(), AlertPoller.getInterval());
}
```

实测方法：临时在 refresh 首行打 hilog，销毁页面后 logcat 过滤 `StockPulse` 观察 30 秒，不应再出现新 fetch 日志。

### 5.2 播放器停止（正确）

`Index.ets:115` 销毁时 `AudioPlayer.stop()`，与播放创建配对，合规；stop 为 async 未等待，销毁不阻塞，登记为可接受取舍（P2-E）。

## 六、资源释放审查

### 6.1 AVPlayer 状态机对照（总体正确，两处瑕疵）

AVPlayer 状态机为 idle→initialized（赋 url，`AudioPlayer.ets:39`）→prepared（prepare，41 行）→playing（play，42 行）→completed/idle（回调 onDone，29-33 行）。本项目释放路径核对：

| 场景 | 处理 | 位置 | 判定 |
|---|---|---|---|
| 播放新音频前 | 先 await stop 复位旧实例 | AudioPlayer.ets:18 | 合规 |
| createAVPlayer 失败 | onError 回调 + throw | 20-26 | 合规 |
| prepare/play 失败 | release 半初始化实例 + 置空静态引用 + onError + throw | 46-52 | 合规，**泄漏主路径已堵死** |
| stop | stop+release 双 try、忽略重复释放、置空 | 55-63 | 合规 |
| 事件监听 | on('stateChange')/on('error') 注册后未 off | 29-37 | **P2-D** |

P2-D 瑕疵说明：监听未解绑，release 后原生对象回收风险低，但 error 回调闭包经 `Index.ets:249-259` 持有 Index 组件 `this`，播放中途销毁页面会令旧组件延迟释放。整改：release 前 `av.off('stateChange'); av.off('error')`，一行成本。另外 completed 与 idle 共用 onDone 回调（30-32 行）是刻意的宽匹配，注释已说明，保持即可。

### 6.2 Preferences 与 HTTP 句柄（合规）

写路径全部 `put + flush` 成对（如 `SettingsService.ets:101-102`），无只 put 不 flush 的丢写路径；读路径判空 pref 防未初始化崩溃（84-86 行范式贯穿全部 getter）。HTTP 句柄：`AlertPoller.ets` 85-87 行与 `PushService.ets` 94-96 行均 `finally { req.destroy() }`，异常路径不漏句柄。

## 七、前后台切换缺口（发现 P1-F：后台照常轮询）

UIAbility 未实现 `onBackground`，应用切后台后 ArkTS 单线程继续运行，148 行 setTimeout 链照常 5s 一跳，**后台持续消耗流量电量**，与 `AlertPoller.ets:20-21` 注释自述的「App 打开期间」定位不符。配套疑点：`module.json5:45-52` 已声明 `KEEP_BACKGROUND_RUNNING` 权限（注释自述 R3 预留未调用），若未来真开长时任务，后台轮询将常驻，必须与退避策略联动（退避机制本身 5s 起步翻倍封顶 30s、成功复位，见 `AlertPoller.ets:28-30,90-99`，设计正确）。

整改：paused 标志 + 前后台钩子 + 回前台立即拉齐：

```typescript
// EntryAbility.ets
onBackground(): void { AppStorage.setOrCreate('appPaused', true); }
onForeground(): void { AppStorage.setOrCreate('appPaused', false); }
// Index.ets：pollLoop 注册定时器前检查 paused；@StorageLink('appPaused') @Watch 回调
// 恢复时先 this.refresh() 再续 pollLoop，保证回前台首屏数据即时刷新。
```

## 八、Settings 子页生命周期缺口

Settings 作为 NavDestination 只挂了 aboutToAppear，未挂 onShown/onHidden。影响评估：当前 Settings 无轮询无播放器，隐藏时不释放任何资源，无实害；但「设置返回后主界面刷新」依赖的恰是这层缺失的事件通道——Index 的 onPageShow 在 Navigation 内部出入栈时不触发（机理见第二节），配置变更无法自动回流主界面，完整整改方案（AppStorage 镜像 + @StorageLink）见 A31 P1-3，本节登记为交叉引用，避免重复维护两份方案。

## 九、内存管理盘点

| 资源 | 上限机制 | 位置 | 判定 |
|---|---|---|---|
| 卡片数据 items | 服务端 limit=20 | AlertPoller.ets:37 | 合规 |
| 已读列表 readAlertIds | 200 条 splice 截断 | SettingsService.ets:399-402 | 合规 |
| 播报历史 playHistory | 50 条 + 同 ID 去重 | SettingsService.ets:433-439 | 合规 |
| AVPlayer | 单例、用后即 release、半初始化也 release | AudioPlayer.ets:46-49,55-63 | 合规 |
| http 句柄 | finally destroy | AlertPoller.ets:85-87 | 合规 |
| 演示卡 | 模块级常量，非每次构建新建 | Index.ets:13-23 | 合规 |

异步状态机防护是本仓库亮点，整改时不得回退：刷新时校验正在播放/加载的 alertId 是否仍在新列表，不在则停播复位（`Index.ets:166-177`）；`togglePlay` 在 await 后复核 loadingId 未被清除才置 playingId（260-265 行），防「prepare 期间卡片被服务端撤下、完成后错误亮播放态」。这类防护直接决定适老化用户会不会看到「明明点了停、声音还在响」的诡异现象，属于生命周期正确性的关键路径。

## 十、整改优先级汇总

| 编号 | 级别 | 问题 | 位置 |
|---|---|---|---|
| P0-C | P0 | pollLoop 销毁后复活泄漏 | Index.ets:146-149,110-116 |
| P1-A | P1 | init 与首帧读配置竞态，首帧闪标准字体 | EntryAbility.ets:20-22；Index.ets:98 |
| P1-F | P1 | 后台轮询不暂停，耗电耗流 | EntryAbility.ets 缺 onBackground |
| P2-B | P2 | loadSettings 无外层 catch | Index.ets:98 |
| P2-D | P2 | AVPlayer 事件监听未 off | AudioPlayer.ets:29-37 |
| P2-E | P2 | 销毁时 async stop 未等待（登记取舍） | Index.ets:115 |

## 十一、验收清单

- [ ] 页面销毁后 30 秒内 logcat 无新 fetch 日志（P0-C 实测法见 5.1）。
- [ ] 冷启动首帧即呈现用户已保存的特大字体档（P1-A 修复后）。
- [ ] 切后台 10 秒无网络请求，回前台立即刷新一次（P1-F）。
- [ ] 连续播报 20 次不同卡片，DevEco Profiler 内存曲线平稳、无 AVPlayer 残留。
- [ ] Settings 各 getter 在 pref 未初始化时返回默认值且无崩溃（现有行为回归确认）。
- [ ] 播放中销毁页面（可借助命令行 force-stop 模拟），无崩溃无悬挂播放。

### 自我评估
- 正确性：4分 P0 复活泄漏给出 t0-t3 时序推演，P1-A 竞态有四步推导与行号链；AVPlayer 状态机与释放路径逐行核对。后台轮询行为基于 ArkTS 运行时语义推断，已给出 logcat 实测法，未冒充已验证。
- 完整性：4分 覆盖 UIAbility 与页面两层触发矩阵、want 双路径、四类资源创建-释放配对与内存上限盘点；UIAbility onConfigurationUpdate 等冷门钩子未展开（本应用未用到）。
- 可复用性：5分 停止标志、就绪 Promise、前后台 paused 三个模板可直接粘贴复用；触发矩阵表与「写 AppStorage 必须确认消费回调会触发」原则适用于所有 ArkTS 项目。
- 字数：约3700字
- 使用模型：GLM-5.3-Flash
