# A33 错误边界审查——try-catch覆盖、用户可见错误提示、降级UI方案

> 项目：harmony-app（鸿蒙适老化股票异动播报应用「铃语」），纯 ArkTS + 云函数，零三方依赖。
> 本篇自包含：所有结论引用仓库文件与行号。适老化的错误呈现铁律：白话、大字、不吓人、不催促；错误兜底必须保证「首屏永不空白」。

## 一、审查方法与总览

方法：对 `entry/src/main/ets/` 全部 8 个文件做 try-catch 逐点清点，再将「代码捕获」与「用户可见反馈」对齐，最后核查降级 UI 链路。总评：**服务层（网络/播放/存储/推送）覆盖优秀，页面交互层（Settings）覆盖为零**，用户可见提示覆盖了三大主故障（断网、语音失败、空数据），但配置写入静默失败一条都没有提示。

## 二、try-catch 覆盖盘点

### 2.1 已覆盖清单（逐文件核对）

| 文件:行 | 保护对象 | 处理方式 |
|---|---|---|
| EntryAbility.ets:16-18,20-22 | Push/Settings 初始化 | catch 后 warn 降级，不阻塞启动 |
| EntryAbility.ets:84-99 | 推送消息 JSON.parse | 内层 try，解析失败仅 warn |
| EntryAbility.ets:100-104 | receiveMessage 注册 | catch 打错误码（BusinessError.code） |
| AlertPoller.ets:41-88 | HTTP 请求 | 外层 try + 429/5xx/非 200 分支 + finally destroy（85-87） |
| AlertPoller.ets:68-75 | 响应 JSON.parse | 内层 try，打原文前 200 字符（72 行）辅助定位 |
| AudioPlayer.ets:20-26 | createAVPlayer | 失败回调 onError 并 throw |
| AudioPlayer.ets:40-52 | prepare/play | 失败时 release 半初始化实例（47-49）+ onError + throw，防双通道死锁 |
| AudioPlayer.ets:34-37 | 播放中 error 事件 | 回调 onError |
| SettingsService.ets 各方法 | Preferences 读写 | 每 getter/setter 独立 try，失败返回安全默认值（如 84-94 返回空数组） |
| PushService.ets:29-39 | AGC 探测+取 token | catch 后静默降级为轮询（32 行），符合「AGC 未配置前降级」红线 |
| PushService.ets:47-57,63-71 | getToken 失败 | 按错误码白名单重试 3 次间隔 1s（14-16 行常量） |
| PushService.ets:79-96 | token 上报 | catch + finally destroy，失败仅日志不碍主流程 |
| Index.ets:248-286 | togglePlay 全异步链 | catch 置 failedId 出红字提示（281-286） |

亮点：AlertPoller 把「连通但无异动」与「网络故障」建模为类型化结果 `PollResult { ok, items, rateLimited }`（`AlertPoller.ets:13-17`），页面据此分流，避免了到处 try 的碎片化——这是错误边界设计的正确姿势。

### 2.2 缺口清单

1. **P1-A：Settings 页全部 async 方法零 try-catch。** `Settings.ets:64-76`（addStock）、78-82（removeStock）、84-88（toggleBroadcast）、90-94（switchFontLevel）、96-101（toggleElderlyMode）、103-110（toggleThemeMode）、112-121（toggleAutoTheme）、123-130/132-139（免打扰时段）、141-144（saveFeedUrl）、146-150（toggleDnd）均直接 await。底层 SettingsService 虽会吞错，但存在**状态不一致风险**：先改 `this.watchlist` 再持久化（72-74 行），flush 失败被吞后 UI 显示已添加、重启后回滚——老人视角即「昨天加的股票不见了」。详见第四节整改。
2. **P2-B：Index.loadSettings 无外层 catch**（`Index.ets:98,118` fire-and-forget），内部吞错兜底使其低危，但中段同步逻辑一旦抛错即 unhandled rejection 无日志。
3. **P2-C：无全局错误兜底。** 未注册 `errorManager.on('error')`，无 unhandledRejection 监听，异常仅散落 hilog，无汇聚点、无上报通道。
4. **Index.refresh 的隐式安全**（验证通过）：refresh 本身无 try，但依赖两层防护——AlertPoller 返回前已 catch 全部网络/解析异常；`feed.items ?? []`（`AlertPoller.ets:79`）保证 items 非空引用，后续 filter/find（`Index.ets:161-177`）不会因畸形数据崩溃。属「契约式免 try」，判定可接受，但契约一旦变更需同步补防。

## 三、用户可见错误提示盘点

| 故障 | 用户可见呈现 | 位置 | 适老化判定 |
|---|---|---|---|
| 语音加载/播放失败 | 卡片内红字「语音加载失败，点重试」，字号用 detailSize（22/26fp），点卡片即重试 | Index.ets:412-417；重试清 failedId 见 242-244 | 合格：白话+行动指引+大字 |
| 网络连续失败 ≥2 次 | 顶栏灰字「连接中断，显示旧数据」 | Index.ets:195-198 置位，335-339 呈现 | 合格：不惊吓、说明现状 |
| 服务端限流 429 | 静默保持旧数据，不提示 | Index.ets:192-193 | 合格：服务端问题不该让老人买单 |
| 未连通初始态 | 刷新时刻显示「未连接」+ 演示卡 | Index.ets:32 与 13-23 | 合格：见第四节 |
| 服务连通但无异动 | 空态页「今日暂无异动 / 监测进行中，有新情况会自动推送」 | Index.ets:432-437 | 合格：安抚式文案，无催促 |
| 播报关/免打扰生效 | 顶栏「播报关」红字、「免打扰」金字角标 | Index.ets:318-329 | 合格：状态可见不误判「坏了」 |
| 配置写入失败 | **无任何提示** | Settings.ets 全部方法 | 缺陷（对应 P1-A） |

文案合规核对：全部提示为白话短句，无「失败代码 0x…」类技术黑话，无催促性措辞，符合「不催促、不承诺收益」红线。

## 四、降级 UI 方案审查

1. **首屏演示卡（约束达成）**：`Index.ets:13-23` 定义 DEMO_ITEMS 常量并作为 `@State items` 初始值（28 行），`isDemoMode` 默认 true（34 行）。headline 明确写「示例：中国巨石…」、detail 写「示例数据，服务器接通后自动换成真实异动」，不冒充真实行情，满足「首屏永不空白 + 不误导」双约束。可改进点（P2-D）：`isDemoMode` 置 false 后再无任何 UI 差异利用（仅在 refresh 152-156 置 false），若首屏数据即真实数据，演示卡会被直接替换，行为正确；但断网模式下无「正在使用演示数据」的持续角标，老人可能把示例数据当真实异动长时间观看——建议顶栏在 isDemoMode && connectionBroken 时追加「演示中」灰字。
2. **数据降级链**：主源失败不清空 items（192-199 分支），保留旧数据 + 状态提示，符合「宁旧勿空」原则；且与共享上下文的服务端降级（Tushare 40101 已降级东财 API）形成端云双层降级。
3. **推送降级**：AGC 缺失时 `probeAgcConfig`（`PushService.ets:99-106` 读 rawfile 判空）返回 false 直接跳过取 token，前台轮询兜底，链路自洽。

## 五、整改代码示例

```typescript
// 整改一（P1-A）：Settings 写入失败提示。以 addStock 为例，其余方法同型。
import { promptAction } from '@kit.ArkUI';
private async addStock(): Promise<void> {
  const code = this.newStockInput.trim();
  if (code.length === 0 || this.watchlist.includes(code)) { return; }
  const next = [...this.watchlist, code];
  const saved = await SettingsService.setWatchlistWithResult(next); // 见下
  if (saved) {
    this.watchlist = next;      // 持久化成功才动 UI，消灭状态不一致
    this.newStockInput = '';
  } else {
    promptAction.showToast({ message: '没保存上，请再试一次' }); // 白话+无催促
  }
}
// SettingsService.setWatchlist 改造：catch 里 return false（或在原方法追加返回值），其余 setter 同型。

// 整改二（P2-C）：EntryAbility.onCreate 全局兜底注册。
import { errorManager } from '@kit.AbilityKit';
errorManager.on('error', (err) => {
  hilog.error(DOMAIN, TAG, 'global error: ' + JSON.stringify(err));
});
```

## 六、验收清单

- [ ] 设置页 11 个 async 方法全部具备「持久化成功才更新 UI + 失败白话 toast」。
- [ ] 断网演示模式下顶栏出现「演示中」角标（新增）。
- [ ] 全局 errorManager 监听注册成功且日志含未捕获异常汇聚点。
- [ ] 回归：语音失败红字→点卡片重试→成功后红字消失（Index.ets:242-257 链路）。
- [ ] 回归：连续失败 2 次出现「连接中断，显示旧数据」，恢复后消失（Index.ets:154-156 复位链路）。
- [ ] 全部错误文案通过合规三查：无收益承诺、无催促、无技术黑话。

### 自我评估
- 正确性：5分 try-catch 清点逐行核对仓库源码，覆盖/缺口/提示三张表均可按行号复核；refresh 隐式安全性系实际阅读 AlertPoller 与 Index 代码后得出。
- 完整性：4分 三大维度（捕获、可见提示、降级 UI）均有独立清单与整改；未覆盖云函数侧错误码规范（属服务端席位范围，已注明边界）。
- 可复用性：4分 「持久化成功才动 UI」模式与 PollResult 类型化错误契约可直接推广；toast 整改代码贴合 ArkTS 纯原生用法。
- 字数：约3600字
- 使用模型：GLM-5.3-Flash
