# A33 错误边界审查——try-catch覆盖、用户可见错误提示、降级UI方案

> 项目：harmony-app（鸿蒙适老化股票异动播报应用「铃语」），纯 ArkTS + 云函数，零三方依赖。
> 本篇自包含：所有结论引用仓库文件与行号。适老化错误呈现铁律：白话、大字、不吓人、不催促；错误兜底必须保证「首屏永不空白」。

## 一、审查方法与总览

方法：对 `entry/src/main/ets/` 全部 8 个文件做 try-catch 逐点清点；再将「代码捕获」与「用户可见反馈」逐一对齐；对每条故障链做端到端走查（代码行为→用户所见）。总评：**服务层（网络/播放/存储/推送）覆盖优秀，页面交互层（Settings）覆盖为零**；用户可见提示覆盖断网、语音失败、空数据三大主故障，但配置写入静默失败一条提示都没有。

## 二、错误分级与捕获策略规范（评判基准）

审查前先立规范，后文按此判定。错误按处置方式分三级：

| 级别 | 判据 | 处置 | 本项目对应 |
|---|---|---|---|
| 可静默降级 | 有兜底默认值，用户无感更好 | catch→取默认值→hilog.warn | SettingsService 全部 getter（如 84-94 行返回空数组）、PushService AGC 缺失降级轮询（32 行） |
| 需用户知晓 | 影响当前操作结果 | catch→状态位→大字白话提示+可重试 | 语音失败 failedId、断网 connectionBroken |
| 需阻断并反馈 | 操作结果不可信 | catch→回滚 UI→白话 toast | Settings 写入失败（当前缺失，P1-A） |

配套两条原则：**底层吞错、顶层呈现**——服务层把异常翻译成类型化结果，页面层只关心结果分流；**吞错必须留痕**——任何 catch 至少打一条 hilog，禁止空 catch（本项目已做到，逐条核对无空 catch）。

## 三、try-catch 覆盖盘点

### 3.1 已覆盖清单（逐文件核对）

| 文件:行 | 保护对象 | 处理方式 |
|---|---|---|
| EntryAbility.ets:16-18,20-22 | Push/Settings 初始化 | catch 后 warn 降级，不阻塞启动 |
| EntryAbility.ets:84-99 | 推送消息 JSON.parse | 内层 try，解析失败仅 warn |
| EntryAbility.ets:100-104 | receiveMessage 注册 | catch 打错误码（BusinessError.code） |
| AlertPoller.ets:41-88 | HTTP 请求 | 外层 try + 429/5xx/非 200 分支 + finally destroy（85-87） |
| AlertPoller.ets:68-75 | 响应 JSON.parse | 内层 try，打原文前 200 字符（72）辅助定位 |
| AudioPlayer.ets:20-26 | createAVPlayer | 失败回调 onError 并 throw |
| AudioPlayer.ets:40-52 | prepare/play | 失败时 release 半初始化实例（47-49）+ onError + throw，双通道都反馈 |
| AudioPlayer.ets:34-37 | 播放中 error 事件 | 回调 onError |
| SettingsService.ets 各方法 | Preferences 读写 | 每 getter/setter 独立 try，失败返回安全默认值 |
| PushService.ets:29-39 | AGC 探测+取 token | catch 后静默降级为轮询，符合「AGC 未配置前降级」红线 |
| PushService.ets:47-57,63-71 | getToken 失败 | 按错误码白名单重试 3 次间隔 1s（14-16 行常量） |
| PushService.ets:79-96 | token 上报 | catch + finally destroy，失败仅日志不碍主流程 |
| Index.ets:248-286 | togglePlay 全异步链 | catch 置 failedId 出红字提示（281-286） |

亮点：AlertPoller 把「连通但无异动」与「网络故障」建模为类型化结果 `PollResult { ok, items, rateLimited }`（`AlertPoller.ets:13-17`），页面据此分流（`Index.ets:151-199`），正是「底层吞错、顶层呈现」的正确落地。

### 3.2 缺口清单

1. **P1-A：Settings 页全部 async 方法零 try-catch。** `Settings.ets:64-76`（addStock）、78-82（removeStock）、84-88（toggleBroadcast）、90-94（switchFontLevel）、96-101（toggleElderlyMode）、103-110（toggleThemeMode）、112-121（toggleAutoTheme）、123-130/132-139（免打扰时段调整）、141-144（saveFeedUrl）、146-150（toggleDnd）共 11 个方法直接 await。底层吞错掩盖了**状态不一致**：先改 `this.watchlist` 再持久化（72-74 行），flush 失败被吞后 UI 显示已添加、重启后回滚——老人视角即「昨天加的股票不见了」，且无任何线索。
2. **P2-B：Index.loadSettings 无外层 catch**（`Index.ets:98,118` fire-and-forget），内部吞错兜底使其低危，但中段同步逻辑一旦抛错即 unhandled rejection 无日志。
3. **P2-C：无全局错误兜底。** 未注册 `errorManager.on('error')`，无 unhandledRejection 监听，异常仅散落 hilog，无汇聚点、无上报通道。
4. **Index.refresh 的隐式安全**（验证通过）：refresh 本身无 try，但依赖两层防护——AlertPoller 返回前已 catch 全部网络/解析异常；`feed.items ?? []`（`AlertPoller.ets:79`）保证 items 非空引用，后续 filter/find（`Index.ets:161-177`）不因畸形数据崩溃。属「契约式免 try」，可接受，但契约一旦变更需同步补防。

## 四、错误传播路径走查（三条主链）

**网络链**：HTTP 异常/超时（AlertPoller.ets:81-84）或非 200（54-64）→ applyBackoff + 返回 `ok:false` → Index.refresh 的 else 分支计数 `consecutiveFailures`（195-198）→ ≥2 次置 `connectionBroken` → 顶栏灰字「连接中断，显示旧数据」（335-339）。全程用户只看到一句白话，技术细节零外泄，路径完整。429 分支额外走 `rateLimited`（192-193）静默跳过，正确区分了「服务端限流不该怪网络」。

**播放链**：四个失败入口（createAVPlayer 20-26、prepare/play 40-52、播放中 error 事件 34-37、调用方 togglePlay catch 281-286）全部收口到 `onError` 回调或 catch → 统一置 `failedId` → 卡片红字「语音加载失败，点重试」（412-417）→ 用户点卡片重试（242-244 清 failedId 后重新 togglePlay）。四入口一出口的漏斗结构清晰，无双提示、无漏提示。

**存储链**：Preferences flush 失败 → SettingsService catch 吞掉 → **到此为止**，UI 已先行更新的状态不回滚、无提示——链路在「顶层呈现」环节断裂，即 P1-A。

## 五、典型异常场景走查表

| 场景 | 代码行为 | 用户所见 | 判定 |
|---|---|---|---|
| feed 返回畸形 JSON | 内层 catch 打前 200 字符（AlertPoller.ets:72），按失败退避 | 计满 2 次后见「连接中断」 | 合规 |
| feed 429 限流 | 静默跳过不计数惊动（47-52） | 无感知，旧数据继续 | 合规 |
| audioUrl 为 undefined | playById 与 togglePlay 双重拦截（Index.ets:208-211,226-228）静默 return；且无 audioUrl 卡片连播放钮都不渲染（390-396） | 点卡片**完全无反应** | **P2-D**：对应已知问题「alerts.json 的 audioUrl undefined 端侧按需调 generate-tts」，静默在技术上安全，但老人无法区分「坏了」和「还没生成」，应显示「语音生成中，稍后可听」灰字 |
| 音频地址失效（404 等） | prepare/play reject → release → onError → failedId | 红字「语音加载失败，点重试」 | 合规 |
| 播放中断网 | error 事件回调 → failedId | 同上红字 | 合规 |
| 推送 payload 非法 JSON | 内层 catch（EntryAbility.ets:96-98）仅 warn | 无感知 | 合规 |
| Preferences 未初始化 | getter 判空返回默认值（如 SettingsService.ets:84-86） | 显示默认配置 | 合规（但引入 A32 P1-A 首帧闪变，另案） |
| 小艺拉起列表外 alertId | playById 未命中静默清掉（Index.ets:203-207） | 无感知 | 合规，且堵死外部注入播报内容 |
| 快速双击播放按钮 | loadingId 拦截重复触发（229-231） | 按钮显示「…」 | 合规 |
| 设置保存时 flush 失败 | 底层吞错，UI 已更新 | **以为保存成功，重启回滚** | 缺陷（P1-A） |

## 六、用户可见错误提示盘点

| 故障 | 用户可见呈现 | 位置 | 适老化判定 |
|---|---|---|---|
| 语音加载/播放失败 | 卡片内红字「语音加载失败，点重试」，字号用 detailSize（22/26fp） | Index.ets:412-417 | 合格：白话+行动指引+大字 |
| 网络连续失败 ≥2 次 | 顶栏灰字「连接中断，显示旧数据」 | Index.ets:195-198 置位，335-339 呈现 | 合格：不惊吓、说明现状 |
| 服务端限流 429 | 静默保持旧数据 | Index.ets:192-193 | 合格：服务端问题不让老人买单 |
| 未连通初始态 | 刷新时刻显示「未连接」+ 演示卡 | Index.ets:32 与 13-23 | 合格：见第七节 |
| 服务连通但无异动 | 空态「今日暂无异动 / 监测进行中，有新情况会自动推送」 | Index.ets:432-437 | 合格：安抚式文案，无催促 |
| 播报关/免打扰生效 | 顶栏「播报关」红字、「免打扰」金字角标 | Index.ets:318-329 | 合格：状态可见不误判「坏了」 |
| 配置写入失败 | 无任何提示 | Settings.ets 全部方法 | 缺陷（P1-A） |

文案规范提炼（供后续新提示沿用，即「错误文案四要素」）：说现状（发生了什么，白话）、说影响（还能不能用）、给动作（点什么能解决）、守红线（禁催促词「立即/马上/最后」、禁收益暗示、禁技术黑话）。现有七条提示逐条比对全部合格。

## 七、降级 UI 方案审查

1. **首屏演示卡（约束达成）**：`Index.ets:13-23` 定义 DEMO_ITEMS 常量并作为 `@State items` 初始值（28 行）。headline 明确写「示例：中国巨石…」、detail 写「示例数据，服务器接通后自动换成真实异动」，不冒充真实行情，满足「首屏永不空白 + 不误导」双约束。可改进点（P2-E）：`isDemoMode` 在 refresh 152-156 置 false 后再无 UI 利用，断网模式下无「正在使用演示数据」的持续角标，老人可能把示例数据当真实异动长时间观看——建议顶栏在 isDemoMode && connectionBroken 时追加「演示中」灰字。
2. **数据降级链**：主源失败不清空 items（192-199 分支），保留旧数据 + 状态提示，符合「宁旧勿空」原则；与共享上下文的服务端降级（Tushare 40101 已降级东财 API）形成端云双层降级。
3. **推送降级**：AGC 缺失时 `probeAgcConfig`（`PushService.ets:99-106` 读 rawfile 判空）返回 false 直接跳过取 token，前台轮询兜底，链路自洽。

## 八、整改代码示例

```typescript
// 整改一（P1-A）：Settings 写入失败提示。以 addStock 为例，其余 10 个方法同型。
import { promptAction } from '@kit.ArkUI';
private async addStock(): Promise<void> {
  const code = this.newStockInput.trim();
  if (code.length === 0 || this.watchlist.includes(code)) { return; }
  const next = [...this.watchlist, code];
  const saved = await SettingsService.setWatchlistWithResult(next); // setter 返回 boolean
  if (saved) {
    this.watchlist = next;      // 持久化成功才动 UI，消灭状态不一致
    this.newStockInput = '';
  } else {
    promptAction.showToast({ message: '没保存上，请再试一次' }); // 白话+无催促
  }
}
// SettingsService.setWatchlist 改造：catch 里 return false，成功 return true；其余 setter 同型。

// 整改二（P2-C）：EntryAbility.onCreate 全局兜底注册。
import { errorManager } from '@kit.AbilityKit';
errorManager.on('error', (err) => {
  hilog.error(DOMAIN, TAG, 'global error: ' + JSON.stringify(err));
});

// 整改三（P2-D）：无语音卡片给出预期管理。
// Index.ets:390-396 的 if (item.audioUrl) 分支补 else：
// Text('语音生成中，稍后可听').fontSize(this.badgeSize).fontColor(this.theme.textSecondary)
```

## 九、验收清单

- [ ] Settings 页 11 个 async 方法全部具备「持久化成功才更新 UI + 失败白话 toast」（P1-A）。
- [ ] 无 audioUrl 卡片显示「语音生成中，稍后可听」，点按不再无反应（P2-D）。
- [ ] 断网演示模式顶栏出现「演示中」角标（P2-E）。
- [ ] 全局 errorManager 监听注册成功，未捕获异常有汇聚日志（P2-C）。
- [ ] 回归：语音失败红字→点卡片重试→成功后红字消失（Index.ets:242-257 链路）。
- [ ] 回归：连续失败 2 次出现「连接中断，显示旧数据」，恢复后消失（Index.ets:154-156 复位链路）。
- [ ] 全部新增文案过「四要素+三禁」检查：现状/影响/动作齐全，禁催促、禁收益暗示、禁技术黑话。

### 自我评估
- 正确性：5分 try-catch 清点逐行核对仓库源码，三条传播链与十场景走查均可按行号复核；audioUrl undefined 场景对应共享上下文已知问题并给出行号证据。
- 完整性：4分 捕获、可见提示、降级 UI 三维度加分级规范与传播链走查；云函数侧错误码规范属服务端席位范围，已注明边界。
- 可复用性：5分 错误三级分级表、「底层吞错顶层呈现」「吞错必须留痕」、文案四要素均为可直接移植的方法论；toast 与 errorManager 代码贴合纯 ArkTS 用法。
- 字数：约3700字
- 使用模型：GLM-5.3-Flash
