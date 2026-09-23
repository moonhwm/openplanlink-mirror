# A32 生命周期管理审查——aboutToAppear/aboutToDisappear、资源释放、内存管理

> 项目：harmony-app（鸿蒙适老化股票异动播报应用「铃语」），纯 ArkTS + 云函数，零三方依赖。
> 本篇自包含：所有结论引用仓库文件与行号。架构基调不改：EntryAbility=Push 初始化+onNewWant 拉起定位；Index.ets=卡片流+5s 前台轮询兜底；AudioPlayer=AVPlayer 播云端 TTS。

## 一、生命周期全景与审查方法

本应用生命周期分两层。**UIAbility 层**（`entry/src/main/ets/entryability/EntryAbility.ets`）：`onCreate`（13-31 行）做 Push/Settings 异步初始化、冷启动 alertId 补检、注册推送接收器；`onWindowStageCreate`（33-41 行）加载 `pages/Index`；`onNewWant`（43-69 行）处理通知与小艺 action 拉起；`onForeground`（71-76 行）仅打日志。**页面层**（`entry/src/main/ets/pages/Index.ets`）：`aboutToAppear`（98-102 行）加载设置+启动轮询+消费 pendingAlertId；`onPageShow`（104-108 行）重读设置+再消费拉起信号；`aboutToDisappear`（110-116 行）清定时器+停播。子页 Settings.ets 仅有 `aboutToAppear`（43-45 行）。

审查方法：逐文件通读 + 定时器/播放器/Preferences 三类资源的创建-释放配对核对。

## 二、aboutToAppear 审查

### 2.1 初始化时序竞态（发现 P1-A：init 与首帧读配置赛跑）

`EntryAbility.onCreate` 中 `SettingsService.init(this.context)` 是**异步且未 await**（`EntryAbility.ets:20-22`），内部 `preferences.getPreferences`（`SettingsService.ets:72-79`）走 IPC 有耗时；紧接着 `onWindowStageCreate` → `loadContent` → Index `aboutToAppear` 执行 `loadSettings()`（`Index.ets:98-99`），内部十连发 `SettingsService.getXxx()`。若此刻 `pref` 仍为 null，所有 getter 走「返回默认值」分支（如 `SettingsService.ets:84-86` 返回空自选、136-139 返回标准字体）。默认值恰好安全（适老化 true/夜间模式），但**老用户已保存的特大字体档在首帧会闪回标准档**，且 init 完成后无人触发重读（下一次重读要等 onPageShow）。竞态窗口小但真实存在，对以大字为生命线的适老化应用属可感缺陷。

整改：SettingsService 暴露就绪 Promise，loadSettings 前先等它：

```typescript
// SettingsService.ets
private static readyPromise: Promise<void> | null = null;
static ready(): Promise<void> {
  if (!SettingsService.readyPromise) {
    SettingsService.readyPromise = SettingsService.doInit();
  }
  return SettingsService.readyPromise;
}
// Index.loadSettings 首行
await SettingsService.ready();
```

保持 EntryAbility.onCreate 仍调用 init 预热，两处共用同一 Promise，不改架构。

### 2.2 loadSettings 无 await、无外层 catch（发现 P2-B）

`Index.ets:98-101` 对 async 的 `loadSettings()/pollLoop()` 均为 fire-and-forget。各 getter 内部已 try-catch 吞错并返回默认值（如 `SettingsService.ets:90-93`），风险被压到很低；但 `loadSettings` 中段同步逻辑若抛错（如 124-128 行分支判断之外的未来改动），会变成 unhandled rejection 且无任何日志。整改：包一层 `loadSettings().catch((e) => hilog.warn(...))`，两行成本买全链路可观测。

### 2.3 Settings 页 aboutToAppear（正常）

`Settings.ets:43-45` 仅重读配置，无资源创建，无需配对释放，判为合规。

## 三、aboutToDisappear 审查

### 3.1 定时器清理的复活漏洞（发现 P0-C：轮询在页面销毁后复活）

`aboutToDisappear` 执行 `clearTimeout(this.timer)`（`Index.ets:111-114`），但轮询结构是**异步自递归**：`pollLoop` 先 `await this.refresh()`（152 行，内部网络请求 5s 超时量级）再注册下一轮 `this.timer = setTimeout(...)`（148 行）。若销毁恰好发生在 `await refresh()` 悬挂期间，clearTimeout 清掉的是**旧的、已执行完的**定时器句柄；refresh resolve 后代码继续走到 148 行，重新注册定时器——轮询复活且永不停止，同时闭包持有已销毁组件，内存与流量双重泄漏。Index 销毁在当前单页结构里罕见（页面即应用），但 Settings 里没有轮询、风险主体验证逻辑成立，且未来任何子页接入 pollLoop 都会踩中。

整改：加停止标志，销毁置位，自递归每轮先查：

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

### 3.2 播放器停止（正确）

`Index.ets:115` 销毁时调用 `AudioPlayer.stop()`，与播放创建配对，判合规。

## 四、资源释放审查

### 4.1 AVPlayer（总体正确，两处小瑕）

`AudioPlayer.ets` 为静态单例：`play()` 先 `await AudioPlayer.stop()` 复位旧实例（18 行）；`createAVPlayer` 失败即回调 onError 并 throw（20-26 行）；`prepare/play` 失败时对半初始化实例执行 `av.release()` 并置空静态引用（46-49 行），**泄漏主路径已堵死**。`stop()` 对 `stop()/release()` 双 try 包裹、忽略重复释放并置空（55-63 行）。两处瑕疵：

1. **P2-D：事件监听未解绑。** 29-37 行注册的 `stateChange`/`error` 回调未 `off`。release 后监听随原生对象回收，风险低，但 error 回调闭包持有 Index 的 `this`（经 Index.togglePlay 传入，`Index.ets:249-259`），播放中途销毁页面会令旧组件实例延迟释放。建议 release 前 `av.off('stateChange'); av.off('error')`。
2. **P2-E：stop 为 async 而 aboutToDisappear 未等待。** `Index.ets:115` 直接调用，销毁不阻塞、可接受；登记为已知取舍。

### 4.2 Preferences（正确）

写路径全部 `put + flush` 成对（如 `SettingsService.ets:101-102`），无只 put 不 flush 的丢写路径；读路径判空 pref 防未初始化崩溃。

### 4.3 HTTP 句柄（正确）

`AlertPoller.ets` 85-87 行与 `PushService.ets` 94-96 行均 `finally { req.destroy() }`，异常路径不漏句柄。

## 五、前后台切换缺口（发现 P1-F：后台照常轮询）

UIAbility 未实现 `onBackground`（grep 证实全仓库仅 `EntryAbility.ets:71` 一个 onForeground）。应用切后台后，ArkTS 单线程继续运行，148 行的 setTimeout 链照常 5s 一跳，**后台持续消耗流量电量**，与「前台轮询兜底」的设计定位（`AlertPoller.ets:20-21` 注释自述「App 打开期间」）不符。另有配套疑点：`module.json5:45-52` 声明了 `KEEP_BACKGROUND_RUNNING` 权限（注释自述 R3 预留未调用），若未来真开长时任务，后台轮询将长期常驻，必须与退避策略联动。

整改：paused 标志 + 前后台钩子：

```typescript
// EntryAbility
onBackground(): void { AppStorage.setOrCreate('appPaused', true); }
onForeground(): void { AppStorage.setOrCreate('appPaused', false); }
// Index.pollLoop 注册 setTimeout 前检查 paused，恢复时立即 refresh 一次拉齐数据
```

退避机制本身（`AlertPoller.ets:28-30` 5s 起步、翻倍封顶 30s、97-99 行成功复位）设计正确，后台缺口修复后即为完整的省流方案。

## 六、内存管理盘点

| 资源 | 上限机制 | 位置 | 判定 |
|---|---|---|---|
| 卡片数据 items | 服务端 limit=20 | AlertPoller.ets:37 | 合规 |
| 已读列表 readAlertIds | 200 条 splice 截断 | SettingsService.ets:399-402 | 合规 |
| 播报历史 playHistory | 50 条 + 同 ID 去重 | SettingsService.ets:433-439 | 合规 |
| AVPlayer | 单例、用后即 release、半初始化也 release | AudioPlayer.ets:46-49,55-63 | 合规 |
| http 句柄 | finally destroy | AlertPoller.ets:85-87 | 合规 |
| 演示卡 | 模块级常量，非每次构建新建 | Index.ets:13-23 | 合规 |

播报与加载状态的悬挂竞态已有专门防护：刷新时校验正在播放/加载的 alertId 是否仍在新列表，不在则停播复位（`Index.ets:166-177`）；`togglePlay` 在 await 后复核 loadingId 未被清除才置 playingId（`Index.ets:260-265`），防「prepare 期间卡片被撤、完成后错误亮播放态」。这类异步状态机防护是本仓库生命周期处理的亮点，整改时不得回退。

## 七、整改优先级汇总

| 编号 | 级别 | 问题 | 位置 |
|---|---|---|---|
| P0-C | P0 | pollLoop 销毁后复活泄漏 | Index.ets:146-149,110-116 |
| P1-A | P1 | init 与首帧读配置竞态 | EntryAbility.ets:20-22；Index.ets:98 |
| P1-F | P1 | 后台轮询不暂停 | EntryAbility.ets 缺 onBackground |
| P2-B | P2 | loadSettings 无 catch | Index.ets:98 |
| P2-D | P2 | AVPlayer 监听未 off | AudioPlayer.ets:29-37 |
| P2-E | P2 | 销毁时 async stop 未等待（登记取舍） | Index.ets:115 |

## 八、验收清单

- [ ] 页面销毁后 5 秒以上不再产生轮询请求（hilog 无新 fetch 日志）。
- [ ] 冷启动首帧即呈现用户已保存的字体档（竞态修复后）。
- [ ] 切后台 10 秒无网络请求，回前台立即刷新一次。
- [ ] 连续播报 20 次不同卡片，无 AVPlayer 实例残留（ Profiler 内存平稳）。
- [ ] Settings 各 getter 在 pref 未初始化时返回默认值且无崩溃（现有行为回归确认）。

### 自我评估
- 正确性：4分 P0 复活泄漏与 P1 竞态均由代码路径逐步推导并给出行号链，AVPlayer/Preferences/HTTP 配对逐一核对；后台轮询行为基于 ArkTS 运行时语义推断，已建议以 logcat 实测佐证。
- 完整性：4分 覆盖 UIAbility 与页面两层、三类资源创建-释放配对与内存上限盘点；UIAbility onCreate/onDestroy 与 want 缓存细节未展开（本应用无相关用法）。
- 可复用性：5分 停止标志模板、就绪 Promise 模板、前后台暂停模板均为可直接粘贴的通用 ArkTS 资产，上限机制表可作新功能评审基线。
- 字数：约3650字
- 使用模型：GLM-5.3-Flash
