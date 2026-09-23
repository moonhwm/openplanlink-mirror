# A22 EntryAbility.ets 审查——Push 初始化流程、onNewWant 处理、alertId 拉起定位逻辑

> 审查对象：`entry/src/main/ets/entryability/EntryAbility.ets`（共 123 行），关联文件 `entry/src/main/ets/services/PushService.ets`（107 行）、`entry/src/main/ets/pages/Index.ets`、`entry/src/main/module.json5`。
> 审查方式：2026-09-23 直接通读上述源文件并交叉核对引用关系（grep 核对了 `pendingAlertId`、`xiaoYiQuery`、`autoPlay` 的全工程消费点），未做真机运行验证——凡属运行时行为推断均已标注。

---

## 一、总体结论

EntryAbility 的骨架符合架构基调："EntryAbility = Push 初始化 + onNewWant 带 alertId 拉起定位"，且冷启动 alertId 补检、AGC 未配置降级这两个关键点都已落实。主要问题集中在：①两个写了却没人读的 AppStorage 死标志（`xiaoYiQuery`、`autoPlay`）；②小艺 PLAY_AUDIO 语音指令会被播报开关/免打扰静默拦截的链路冲突；③Push 消息接收器直接在 Ability 内注册、绕开了 PushService 封装的分层不一致；④alertId 提取逻辑三处重复。以下分节展开，每条结论附行号证据。

---

## 二、Push 初始化流程审查（onCreate 阶段）

### 2.1 流程还原

`EntryAbility.ets:13-31` 的 onCreate 依次做了四件事：

1. `PushService.init(this.context)`（:16-18），`.catch` 只打 `push init degraded` 警告——不 await、不阻塞启动，方向正确；
2. `SettingsService.init(this.context)`（:20-22），同样 fire-and-forget + 降级日志；
3. 冷启动 alertId 补检（:23-28）：`want?.parameters?.alertId` 存在则 `AppStorage.setOrCreate('pendingAlertId', alertId)`，注释援引白皮书 §3.3.2，明确说明这是修"原代码只在 onNewWant 处理 alertId、冷启动点通知会丢失"的缺陷；
4. `registerPushMessageReceiver()`（:30，实现于 :83-105）。

### 2.2 降级设计核对（合规约束：PushService 保持占位封装、AGC 未配置前降级轮询）

`PushService.ets:99-106` 的 `probeAgcConfig` 用 `resourceManager.getRawFileContentSync('agconnect-services.json')` 探测 AGC 配置文件，异常即返回 false；`PushService.ets:30-34` 探测失败直接 return 并记日志 'agconnect-services.json absent, push degraded to polling'。链路闭环成立：**AGC 未配置 → init 静默返回 → 前台轮询（AlertPoller 5s）兜底**，与治理约束逐字吻合。`EntryAbility.ets:16-18` 的 catch 再兜一层，双保险成立。

细节核实：

- `PushService.ets:14` 定义可重试错误码 `[1000900001, 1000900008, 1000900009, 1000900011]`，`:63-71` 的 `handleTokenRetry` 限 3 次、间隔 1s，用 `setTimeout` 重入 `fetchToken`——重试不阻塞 onCreate，正确；
- `PushService.ets:77-97` 的 `reportToken` 上报地址硬编码为 CloudBase `push-token-register` HTTP 端点（:11），POST `{token, bundleName}`，失败仅记日志不影响主流程——与"占位封装、上报失败不伤主流程"一致；
- **脱敏缺口**：`PushService.ets:49` 日志输出 `token length=${token.length}`，只打长度不打内容，这点做得对；但注意 EntryAbility 内的接收器日志（下文 2.4）打印了整个 payload。

### 2.3 初始化时序的一个注意点

`registerPushMessageReceiver()`（:30）在 onCreate 同步调用，而 `PushService.init` 是异步的——即"接收器注册"先于"AGC 配置探测完成"。若 AGC 未配置，`pushService.receiveMessage(...)` 可能抛错，代码用 try/catch 兜住并打 `receiveMessage register failed`（:101-104），行为是安全的。但这带来一个结构问题：**接收器注册与 AGC 状态解耦了，日志里可能出现"receiver registered"与"agconnect absent"并存的矛盾现场**，排查时会误导。建议改为 `PushService.init` 完成且探测通过后再注册接收器，或把注册逻辑整体下沉进 PushService。

### 2.4 分层不一致：接收器绕开了 PushService 封装

`EntryAbility.ets:6` 直接 `import { pushService, pushCommon } from '@kit.PushKit'`，`:83-105` 在 Ability 内直接调用 `pushService.receiveMessage('DEFAULT', this, callback)`。而治理基调是"PushService.ets 保持占位封装"——Push 的一切端侧细节（getToken、上报、接收）都应收敛在 PushService 内。现状造成：

- Push 逻辑分裂两处：token 生命周期在 PushService，消息接收在 EntryAbility；
- EntryAbility 顶部同时存在 `PushService`（:4）与裸 `pushService`（:6）两个名字极易混淆的导入；
- 接收器内 `JSON.parse(data.data)`（:90）这类解析健壮性逻辑放在了 Ability 层。

（说明：`pushService.receiveMessage` 这一 API 形态本次未做 SDK 文档比对与真机验证，其签名与'DEFAULT'场景类型的行为以实测为准；本条审查针对的是分层归属，不否定 API 用法本身。）

---

## 三、onNewWant 处理审查（:43-69）

### 3.1 四条分支还原

1. **通知拉起**（:45-48）：`want?.parameters?.alertId` → `pendingAlertId`。热启动点通知走这里，与 onCreate 冷启动补检（:25-28）配对，冷/热两条启动路径都已覆盖，白皮书 §3.3.2 的缺口修复完整；
2. **小艺 QUERY_ALERTS**（:52-54）：`action === 'com.yehang.stockpulse.QUERY_ALERTS'` → 置 `AppStorage.setOrCreate('xiaoYiQuery', true)`，注释说"让 Index 页面返回异动摘要"；
3. **小艺 DETAIL_ALERT**（:55-60）：从 `want.parameters.alertId` 取 `xiaoYiAlertId` → `pendingAlertId`；
4. **小艺 PLAY_AUDIO**（:61-68）：取 `playAlertId` → 同时置 `pendingAlertId` 与 `autoPlay = true`。

三个自定义 action 与 `module.json5` 的 skills 声明（`module.json5` abilities[0].skills 第三组 actions：`com.yehang.stockpulse.QUERY_ALERTS / DETAIL_ALERT / PLAY_AUDIO`）一一对应，清单完整。onNewWant 本身无返回值、无 await，符合同步回调约束。

### 3.2 问题 P1（高）：`xiaoYiQuery` 与 `autoPlay` 是死标志

本审查用 grep 对全工程 `entry/src` 检索确认：`xiaoYiQuery` 仅在 `EntryAbility.ets:54` 出现一次，`autoPlay` 仅在 `:66` 出现一次，**两个标志没有任何消费点**（Index.ets 全文无读取）。后果：

- 小艺"查询异动列表"的语音意图被静默吞掉——用户问了，应用没有任何响应路径；
- PLAY_AUDIO 语义上"用户明确要求播放"，但 `autoPlay` 置位后无人理睬，实际播放与否完全退化为 `pendingAlertId → Index.playById` 的自动播报链路，还受下述 P2 的开关拦截。

修复方向（任选其一并在 Index 落地）：① 在 `Index.aboutToAppear/onPageShow` 的 `loadSettings()` 后消费 `xiaoYiQuery`——为真时把当前 items 摘要拼成白话短句（仅复述 headline，不含任何收益承诺措辞，遵守三禁）写回 AppStorage 供小艺读取，随后清除标志；② 消费 `autoPlay`：置位时走一条绕过开关的播放路径（见 P2），用完即 `AppStorage.delete`。当前"只写不读"的状态属于半成品功能上线的典型形态，应在小艺联调前补齐或注释禁用，避免"看起来支持"的假语义。

### 3.3 问题 P2（高）：小艺 PLAY_AUDIO 会被播报开关/免打扰误杀

链路推演（静态）：PLAY_AUDIO → `pendingAlertId` → Index `checkPendingAlertId()`（`Index.ets:138-144`）→ `playById(id)`（`Index.ets:202-223`）。而 `playById` 内有两道闸门：`if (!this.broadcastEnabled)`（:213-216）与 `if (this.dndActive)`（:217-221），命中即"自动播报静默跳过"。`Index.ets:217` 的注释写"用户手动点击仍可播放"——但小艺语音指令同样是用户的显式意图，却走了自动播报通道被一并拦截。老年用户对小艺说"播放这条异动"，若恰逢免打扰时段或播报开关关闭，得到的是完全无响应。

修复建议：onNewWant 的 PLAY_AUDIO 分支额外置一个 `explicitPlay` 标志（或直接复用 `autoPlay`），Index 消费时对显式播放跳过 broadcastEnabled/dndActive 两道闸（保留 playingId 冲突处理），并在免打扰被显式穿透时于顶栏短暂提示。此改动不违反合规红线——免打扰是体验设计而非合规要求，显式指令穿透是通用助手惯例。

### 3.4 问题 P3（中）：alertId 提取逻辑三处重复

`EntryAbility.ets:25-28`（onCreate）、`:45-48`（onNewWant）、`:89-95`（push receiver）三段几乎同构的 `want?.parameters?.alertId → AppStorage.setOrCreate('pendingAlertId', ...)`。重复本身不产生 bug，但已经产生了不一致苗头：push receiver 分支会打印 payload（:87），另两处不打印。建议抽一个私有静态方法 `stashPendingAlertId(alertId?: string): void`，三处调用，顺便在其中统一"hilog.debug 是否打 id"的口径（打 id 需评估日志暴露面，alertId 格式为 `symbol_ts`，泄露面小但建议统一）。

### 3.5 问题 P4（低）：参数未做类型与格式校验

三处取值都直接 `as string | undefined`。若服务端/小艺传入非字符串（例如嵌套对象），`as` 强转会掩盖类型问题，直到 Index 端 `items.find((it) => it.alertId === id)` 匹配失败静默返回（`Index.ets:203-207`）。建议 stash 方法内加一道 `typeof alertId === 'string' && alertId.length > 0 && alertId.length < 128` 的门槛，超界记 warn 丢弃。

---

## 四、alertId 拉起定位链路审查（Ability → AppStorage → Index）

### 4.1 全链路还原

```
通知/小艺携带 alertId
  ├─ 冷启动：onCreate(:25-28) 写 pendingAlertId
  │     → onWindowStageCreate loadContent('pages/Index')（:33-41）
  │     → Index.aboutToAppear → checkPendingAlertId（Index.ets:98-102, 138-144）
  ├─ 热启动/后台拉起：onNewWant(:45-48) 写 pendingAlertId
  │     → Index.onPageShow → checkPendingAlertId（Index.ets:104-108）
  └─ 前台 DEFAULT 推送：receiver(:83-99) 写 pendingAlertId
        → 下一次 aboutToAppear/onPageShow 消费（注意：页面常驻时无自动触发，见 4.3）
消费侧：checkPendingAlertId 取出即删（AppStorage.delete，Index.ets:141）→ playById
```

取用即删（`Index.ets:141`）保证标志不会重复消费，这是正确的幂等设计。三条路径汇入同一个 AppStorage 键，解耦了 Ability 与页面的生命周期差异，整体设计是干净的。

### 4.2 定位失败的静默策略核对

`Index.playById`（`Index.ets:202-223`）对三种失败均静默：目标不在当前列表（:204-207，含被自选股过滤与已被服务端撤下两种原因）、无 audioUrl（:208-211）、播报关闭/免打扰（:213-221）。对"通知点了没反应"的老年用户场景，静默是体验硬伤：用户被通知拉起，列表里却找不到对应卡片时没有任何解释。建议至少做一层：定位失败时把该 alertId 对应的卡片置顶补拉一次 feed（调用一次 `AlertPoller.fetchLatest`），仍失败则用 30fp 白话 toast 提示"这条消息已过期"。是否实施属产品决策，本审查先记为缺口。

### 4.3 前台推送路径的时效缺口

前台收 DEFAULT 推送时（receiver :89-95）只写 `pendingAlertId`，而消费点只有 `aboutToAppear`/`onPageShow`——页面已展示时这两个钩子都不会再触发，标志会一直躺着，直到用户切去设置页再回来才被消费。此时 alertId 可能已过期，`playById` 静默跳过，行为等于"前台推送不带任何定位效果"。核对：前台推送的本意更可能是"新增一条卡片"而非"定位播放"，receiver 或许根本不该写 pendingAlertId。建议明确语义：前台推送若含 alertId 且需要播放，应通过回调/事件通知 Index 立即 `checkPendingAlertId()`（可在 AppStorage 上用 `@StorageLink` 监听，或把 receiver 回调注入 Index），而非依赖页面钩子。

### 4.4 onWindowStageCreate 与启动窗口

`:33-41` 的 `loadContent('pages/Index')` 错误分支只打日志不重试不提示——加载失败用户将面对白屏/黑屏，与"首屏永不空白"约束存在理论冲突（实际触发概率极低，`main_pages.json` 中 `pages/Index` 注册在案）。`module.json5` 已配置 `startWindowIcon/startWindowBackground` 启动窗，冷启动观感有兜底。建议 loadContent 失败分支至少二次尝试或提示文案，列入低优先级。

---

## 五、其余发现

1. **SDK 版本口径差异（需治理侧确认）**：治理上下文声明 compatibleSdkVersion 20 / targetSdk 26，但仓库 `build-profile.json5:8-9` 实际为 `compatibleSdkVersion: "6.0.2(22)"` 与 `targetSdkVersion: "6.0.2(22)"`（HarmonyOS 6.0.2 / API 22）。两者不一致，影响文档口径而非编译（以仓库为准可编译）。建议在 GOVERNANCE 中统一口径，或修正 build-profile。
2. **onForeground 的订阅预留**（:71-76）：`requestSubscribe` 整段注释保留并注明 P5（AGC 审批中）与错误码 1000900025 前置条件（:107-122），状态清晰，无问题。
3. **onBackground 缺失**：Ability 层未重写 `onBackground`。页面级轮询/播放在退到后台后的行为由 Index 决定（详见 A23 审查），Ability 层无兜底。建议未来 R3 后台播报实装时（`module.json5` 已预留 `KEEP_BACKGROUND_RUNNING` 权限，注释标明"R3 实装后启用"）在 onBackground 处统一调度。
4. **导入冗余**：`EntryAbility.ets:4` 导入 `PushService`，但本文件对 PushService 的唯一引用是 `:16` 的 init 调用；`:6` 的裸 kit 导入与 2.4 分层问题应一并解决，二者取其一。

---

## 六、问题清单汇总与优先级

| 编号 | 级别 | 问题 | 证据 | 建议动作 |
|---|---|---|---|---|
| P1 | 高 | xiaoYiQuery/autoPlay 死标志，小艺意图无响应 | EntryAbility.ets:54、:66 全工程无消费 | Index 消费或注释禁用 |
| P2 | 高 | 小艺显式播放被播报开关/免打扰静默拦截 | Index.ets:213-221 链路推演 | 显式播放通道绕闸 |
| P3 | 中 | alertId 提取三处重复且日志口径不一 | EntryAbility.ets:25-28/45-48/89-95 | 抽 stashPendingAlertId |
| P4 | 中 | 前台推送 pendingAlertId 无消费时机 | Index.ets:98-108 仅页面钩子触发 | 明确前台推送语义并补通知机制 |
| P5 | 低 | 接收器绕开 PushService 封装、初始化时序日志矛盾 | EntryAbility.ets:6,30,83-105 | 下沉 PushService |
| P6 | 低 | alertId 无类型/长度校验 | EntryAbility.ets:25,45 | stash 内加门槛 |
| P7 | 低 | SDK 版本口径与治理文档不一致 | build-profile.json5:8-9 | 治理侧统一口径 |
| P8 | 低 | loadContent 失败无用户可见兜底 | EntryAbility.ets:34-38 | 失败提示或重试 |

## 七、审查方法声明与遗留项

本审查完成于 2026-09-23，依据为当日仓库快照的源码通读与 grep 交叉核对（`pendingAlertId`、`xiaoYiQuery`、`autoPlay`、`complianceStatus` 四键的全工程消费点均已检索）。**未执行项**：真机/模拟器运行验证、Push Kit SDK 签名比对（`pushService.receiveMessage`）、hilog 输出实测——涉及运行时行为的结论（P2 链路推演、P4 时效缺口）均基于静态代码路径推演并已标注，实施修复前建议先在模拟器复现 P1/P2。

### 自我评估
- 正确性：4分 全部结论附行号，死标志经 grep 全工程核实；运行时推断已明确标注未验证，扣一分。
- 完整性：4分 覆盖任务指定的三条主线（Push 初始化/onNewWant/alertId 链路）并延伸到时序、分层、版本口径；真机验证未做已如实声明。
- 可复用性：4分 问题清单表可直接转为工单；链路图与行号引用便于他人复核；修复建议保留产品决策空间。
- 字数：约3600字
- 使用模型：GLM-5.3-Flash
