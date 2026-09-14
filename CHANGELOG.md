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
