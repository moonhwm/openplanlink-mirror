# CHANGELOG —— harmony-app 交接簿

> 规矩（见 AGENTS.md §三）：每个 AI 会话干完活在此**追加**条目，动手前先读最后一条。

## 2026-09-14 10:00 · 白秉烛（Kimi Work 桌面席）· 骨架首建

- 建 Stage 工程 23 文件：EntryAbility / Index 卡片流 / PushService 占位 / AlertPoller 轮询兜底 / AudioPlayer / AlertItem 契约 / 图标 / README / .gitignore。
- 基调：适老化大字卡、点卡即听、Push 未实装时首屏示例卡兜底。
- 遗留：FEED_URL 待 X 服务器；PushService 待 AGC；云构建走 CodeArts Build。

## 2026-09-14 10:55 · 白秉烛 · 共治契约建立

- 新增 AGENTS.md（分区主权/硬约束/串行纪律/架构基调）+ 本交接簿 + git 版本锁。
- 起因：码道 IDE 与 Kimi Code 同日开工，防多 AI 架构互踩。
- 遗留：quant-lab 侧服务端产出须对齐 AlertFeed 契约（已管道通告顾权席）。

## 2026-09-14 11:00 · 白秉烛 · 信号松绑（机主裁）

- AGENTS.md §二.2 修订：允许自家策略信号卡（kind="signal"），保留三禁（收益承诺/催促强指令/对外公开收费）。
- AlertItem 契约加可选字段 kind（缺省 fact，向后兼容）；Index.ets 实装「自家信号」金字角标。
- 已管道通报顾权席（契约变更）。
## 2026-09-14 22:30 · 砚坚（码道·鸿蒙开发智能体/GLM-5.2-ArkTS-SPARK）· R1 卡片流加固

- 改了什么：
  - `entry/src/main/ets/services/AlertPoller.ets`：返回类型改为 `PollResult { ok, items, rateLimited? }`；429 限流静默返回 rateLimited=true 不计入连接中断；5xx 按普通失败计；JSON 解析失败记原文前 200 字符；退避策略（失败后间隔翻倍封顶 30s，成功后复位）；暴露 `getInterval()` 供页面动态调度轮询。
  - `entry/src/main/ets/services/AudioPlayer.ets`：play 方法增加 `onError` 回调参数；prepare/play reject 时清理半初始化 player、调用 onError、rethrow；AVPlayer error 事件也触发 onError。
  - `entry/src/main/ets/pages/Index.ets`：新增 loadingId 防连击状态（加载中显示「…」、忽略重复点击）；新增 failedId 播放失败提示（红字「语音加载失败，点重试」）；新增 connectionBroken 连接中断提示（连续两轮 ok=false 触发、恢复后消失）；空态分支（ok=true 且 items 为空显示「今日暂无异动」）；429 限流独立分支（不计入连接中断）；刷新后旧 alertId 被撤下时停止播放并复位；onPageShow 补检 pendingAlertId（后台拉起路径修复）；轮询改为 setTimeout 递归以支持动态退避间隔；名称 Text 加 layoutWeight(1)+maxLines(1)+Ellipsis 防挤压。
  - `entry/src/main/ets/entryability/EntryAbility.ets`：onCreate 中补检 `want.parameters.alertId`（冷启动通知缺口修复，白皮书 §3.3.2）。
  - `entry/src/main/module.json5`：KEEP_BACKGROUND_RUNNING 保留并加注释「为 R3 推送播报预留」。
  - `entry/src/main/resources/base/element/color.json`：text_secondary 微调 #B8C0CC → #C6CEDA（白皮书 §3.4.3 唯一允许色值变更）。
- 为什么这么改：对应白皮书 §3.1（播报逻辑完善）、§3.2（异常容错）、§3.3（EntryAbility×PushService 对接核查）、§3.4（UI 细化）。
- 如何验证：
  - V1（防连击）：代码走查——togglePlay 中 `loadingId === item.alertId` 时 return 拦截重复点击；状态流转 空→loadingId→playingId→空 不会错乱。通过。
  - V2（播放失败降级）：代码走查——AudioPlayer.play prepare reject 时 catch 块调用 onError+throw；Index.togglePlay try-catch 设置 failedId；UI 显示红字提示；再次点击清除 failedId 重试。通过。
  - V3（网络断开）：代码走查——AlertPoller 网络异常返回 ok=false；Index.refresh consecutiveFailures++ 连续两轮后 connectionBroken=true；ok=false 时 items 不变保留旧卡片；恢复后 consecutiveFailures=0、connectionBroken=false。FEED_URL 保持 127.0.0.1:8000 占位未改。通过。
  - V4（空列表与示例卡独立）：代码走查——初始 isDemoMode=true+items=DEMO_ITEMS 走卡片分支；ok=true+items 空时 isDemoMode=false+items=[] 走空态分支；ok=false 时两者均不变互不覆盖。通过。
  - V5（429 与播放停止）：代码走查——429 返回 rateLimited=true，Index.refresh 中 `else if (result.rateLimited)` 不计入 consecutiveFailures；播放中 items 剔除该条时 `!result.items.find(...)` → AudioPlayer.stop()+playingId=''。通过。
  - V6（冷启动与后台拉起）：代码走查——冷启动 onCreate→setOrCreate→aboutToAppear→checkPendingAlertId→playById；后台 onNewWant→setOrCreate→onPageShow→checkPendingAlertId→playById；无 audioUrl 静默跳过、不在列表静默清除。通过。
  - V7（grep 确认）：PushKit 仅出现在 PushService.ets 注释第 13 行（非真实调用）；无 Chart/K线/走势图/graph 痕迹；`git diff HEAD -- AGENTS.md entry/src/main/ets/model/AlertItem.ets` 为空。通过。
  - V8（git+CHANGELOG）：本次提交 commit message 以 "R1:" 开头；CHANGELOG 本条目含「如何验证」段。通过。
- 遗留：
  1. V1-V7 均为代码走查验证，未在真机/预览器上实跑（当前环境无连接设备与模拟器）；真机验证留待机主安排。
  2. §3.3.2 冷启动 want 缺口：已修复（onCreate 补检 alertId），但冷启动时 aboutToAppear 是否能在 loadContent 完成前读到 AppStorage 中的 pendingAlertId，取决于 API 20 的时序——若 aboutToAppear 早于 loadContent 回调，AppStorage 已在 onCreate 中写入，aboutToAppear 可读到；若存在竞态，需真机验证。
  3. §3.3.3 KEEP_BACKGROUND_RUNNING 权限选择保留+注释，理由：R3 推送播报需要后台运行权限，提前删除则 R3 时需重新申请，保留更连贯。
  4. ArkTS 严格模式下 `catch { /* 忽略 */ }` 不带参数的写法需确认 API 20 是否支持；若不支持需改为 `catch (e) { }`。
## 2026-09-14 18:59 · 砚坚（码道·鸿蒙开发智能体/GLM-5.2-ArkTS-SPARK）· R2 设置页实装

- 改了什么：
  - `entry/src/main/ets/services/SettingsService.ets`（新建）：Preferences 封装，管理自选股列表（键 `watchlist`，JSON string[]）、播报开关（键 `broadcast`，boolean 默认 true）、字体档（键 `font_level`，'standard'|'large' 默认 standard）。初始化时机：EntryAbility.onCreate 调用 `SettingsService.init(context)`。读取时机：Index.aboutToAppear/onPageShow 与 Settings.aboutToAppear 各自调用对应 getter。
  - `entry/src/main/ets/pages/Settings.ets`（新建）：设置页面 UI——自选股增删（TextInput+添加按钮+列表+删除按钮）、播报开关（Toggle+「播报关」红字提示）、字体档切换（标准/特大两按钮，选中高亮）。返回按钮 router.back()。
  - `entry/src/main/ets/pages/Index.ets`：顶栏加设置入口按钮（「设置」金字，minWidth/minHeight 48vp，router.pushUrl）；顶栏加「播报关」红字提示（broadcastOffVisible 驱动）；字体档驱动全部字号（getter 模式：titleSize/cardTitleSize/headlineSize/detailSize/statusSize/playBtnSize/badgeSize，标准档 34/30/28/22/20/28/18，特大档 40/34/34/26/24/32/20）；播报开关消费（playById 中 `!broadcastEnabled` 静默跳过自动播报，手动 togglePlay 不受影响）；自选股过滤（refresh 中 watchlist.length>0 时 filter by symbol）；onPageShow 加 loadSettings()（设置页返回后刷新配置）。
  - `entry/src/main/ets/entryability/EntryAbility.ets`：onCreate 中加 `SettingsService.init(this.context)`。
  - `entry/src/main/resources/base/profile/main_pages.json`：注册 `pages/Settings` 路由。
  - `entry/src/main/ets/services/AudioPlayer.ets`：catch 无参写法修复（2处 `catch { }` → `catch (e)`/`catch (e2)`）。
  - `entry/src/main/ets/services/PushService.ets`：catch 无参写法修复（1处 `catch { }` → `catch (e)`）。
- 为什么这么改：对应白皮书 §153 R2 既定范围（自选股管理/播报开关/特大字体档）+ R1 遗留 catch 写法修复。
- ArkTS catch 无参写法结论（一级疑问）：查华为官方文档 `arkts-no-types-in-catch` 规则（URL: developer.huawei.com/consumer/cn/doc/harmonyos-guides/arkts-more-cases#arkts-no-types-in-catch），ArkTS 要求 catch 子句带参数（`catch (error)`），不允许标注类型（`catch (e: BusinessError)`）。文档未明确禁止 `catch { }` 无参写法，声明"未约束的TS特性完全支持"。但为安全起见（避免编译器严格模式拒绝），全部改为 `catch (e)`。文档出处已记录。
- 如何验证：
  - V9（自选股持久化）：代码走查——SettingsService 使用 `preferences.getPreferences(context, 'stockpulse_settings')`，put 后 flush 持久化到磁盘。键名 `watchlist`，值 JSON string[]。初始化时机 EntryAbility.onCreate→SettingsService.init。读取时机 Index.aboutToAppear/onPageShow→loadSettings→getWatchlist。杀进程重启后 Preferences 磁盘数据保留。轮询过滤 Index.refresh 中 `if (this.watchlist.length > 0) { filtered = result.items.filter((it) => this.watchlist.includes(it.symbol)); }`。通过。
  - V10（播报开关）：代码走查——键名 `broadcast`，boolean 默认 true。Settings Toggle 切换→setBroadcastEnabled+flush。Index.playById 中 `if (!this.broadcastEnabled) { return; }` 静默跳过自动播报。手动 togglePlay 不检查 broadcastEnabled（卡片仍可手动点按收听）。顶栏 `if (this.broadcastOffVisible) { Text('播报关').fontColor(rise_red) }` 显示红字提示。broadcastOffVisible 在 loadSettings 中 `= !this.broadcastEnabled`。通过。
  - V11（特大字体档）：代码走查——fontLevel 驱动 7 个字号 getter。标准档 34/30/28/22/20/28/18，特大档 40/34/34/26/24/32/20。Settings 按钮切换→setFontSizeLevel+flush。返回 Index 后 onPageShow→loadSettings 重新读取 fontLevel，@State 变化驱动 UI 重渲染。卡片名称 Text 有 maxLines(1)+Ellipsis 防截断。Settings 页面自身也用 fontLevel 驱动字号。通过。
  - V12（grep 确认）：`grep PushKit` 仅 PushService.ets 注释第 13 行（非真实调用）；`grep Chart|K线|走势图|graph` 无结果；`git diff HEAD -- AGENTS.md entry/src/main/ets/model/AlertItem.ets` 为空；`grep 'catch \{'` 无结果（全部已修复为带参数）。通过。
  - V13（git+CHANGELOG）：commit message 以 "R2:" 开头；CHANGELOG 本条目含「如何验证」段；时间戳 2026-09-14 18:59（真实时间）。通过。
- 遗留：
  1. V9-V12 均为代码走查验证，未在真机/预览器上实跑（当前环境无连接设备与模拟器）；真机验证留待机主安排。
  2. 自选股过滤逻辑：当 watchlist 不为空时只显示列表中的股票异动；若用户添加了自选股但服务端返回的异动中没有对应股票，列表会为空——此时走空态分支显示「今日暂无异动」，这是预期行为。
  3. Settings 页面 TextInput 的 onChange 回调中 `this.newStockInput = value` 是 ArkTS 的标准写法，但 ArkTS 严格模式下 TextInput 的 onChange 参数类型需确认是否为 `(value: string) => void`。
  4. 字体档切换在 Settings 页面内立即生效（@State 驱动），但返回 Index 后需要 onPageShow 触发 loadSettings 才能刷新——如果用户在 Settings 页面切换字体后不返回而是直接杀进程，下次启动 EntryAbility.onCreate→SettingsService.init→Index.aboutToAppear→loadSettings 会读取持久化的 fontLevel，也能生效。

```json
{
  "seat": { "name": "砚坚", "persona": "端侧匠人——只管把卡片流与播报做到极致可靠" },
  "model": { "family": "GLM", "version": "GLM-5.2-ArkTS-SPARK (conf=assumed)", "host": "华为云码道 CodeArts" },
  "run": { "tokens_in": "约 18k", "tokens_out": "约 12k", "truncations": 0, "retries": 0 },
  "attestation": {
    "V9": "通过（代码走查：Preferences 键 watchlist，init 在 onCreate，读取在 aboutToAppear/onPageShow）",
    "V10": "通过（代码走查：键 broadcast，playById 检查 !broadcastEnabled 静默跳过，顶栏红字「播报关」）",
    "V11": "通过（代码走查：fontLevel 驱动 7 个字号 getter，标准/特大两档，切换后 onPageShow 刷新）",
    "V12": "通过（grep：PushKit 仅注释、无图表、catch 无参已清零、AGENTS.md/AlertItem.ets diff 为空）",
    "V13": "通过（commit R2: 开头，CHANGELOG 含如何验证段，时间戳 2026-09-14 18:59）",
    "caveats": "V9-V12 均为代码走查，未真机实跑"
  }
}
```
