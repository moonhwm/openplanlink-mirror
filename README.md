# 铃语（StockPulse）· 鸿蒙 NEXT 私有分发工程

适老化语音提醒 App。**云端（X 服务器）秒级监测 → Push Kit 推送 → 锁屏大字通知 → 点按拉起 → 自动语音播报**。只报客观异动事实，不含任何买卖建议。

> 应用显示名「铃语」（典出苏轼塔铃：铃先响，风将至），bundleName `com.yehang.stockpulse` 保持不变（AGC 注册锚）。

- 目标机型：Mate X5（HarmonyOS NEXT 纯血）；`compatibleSdkVersion 6.0.2(22)` / `targetSdkVersion 6.0.2(22)`
- 形态：原生 ArkTS Stage 模型，单 entry 模块，零三方依赖
- 分发：私有调试证书直装（免审核免软著免备案零公开，100 台/年）

## 目录

```
AppScope/                 应用级配置（bundleName=com.yehang.stockpulse）
entry/src/main/ets/
  entryability/           EntryAbility（Push 初始化 + Settings 初始化 + 通知点击带 alertId 拉起）
  pages/Index.ets         大字异动卡片流，点卡即听（服务未连通时显示「示例」卡）
  pages/Settings.ets      设置页（自选股增删 / 播报开关 / 字体档切换）
  services/PushService    Push Kit 集成封装（AGC 未配置时自动降级为轮询）
  services/AlertPoller    前台 5s 轮询兜底（FEED_URL 待 X 落地后替换）
  services/AudioPlayer    云端 TTS 音频流点按播报（AVPlayer）
  services/SettingsService 设置数据持久化（Preferences：自选股/播报开关/字体档）
  model/AlertItem         异动事实卡数据契约
```

## 构建

**本机构建**（A 盘 DevEco Studio 6.0.2，纯英文路径）：

```bash
# devecocli 构建（debug 模式）
devecocli build --build-mode debug
# 产物：entry/build/default/outputs/default/entry-default-unsigned.hap
```

**云构建**（CodeArts Build）：

1. 把本目录上传码道仓库（CodeArts Repo）。
2. CodeArts Build 新建构建任务 → 选官方「HarmonyOS 应用构建」模板（自带 SDK/Hvigor）。
3. 产物 `entry-default-signed.hap` 下载后经 `hdc install` 装 X5。

注意：码道 AI 编码额度（体验版 500 万 tokens/月）09-09 已 100% 封顶，10 月重置——本工程不依赖码道额度，不受影响。

## 签名与装机（机主一次动作，约 10 分钟）

1. 免费注册华为个人开发者（无费用）。
2. 任一可联网电脑装 DevEco Studio → 打开本工程 → 自动化签名（自动生成调试证书+profile）。
3. X5 开开发者模式 → UDID 录入调试设备列表 → `hdc install` 直装。
4. 调试证书一年有效，到期重签（已建日历提醒）。

## 推送实装（候 AGC）

1. AppGallery Connect 建项目+应用，开通 Push Kit，下载 `agconnect-services.json` 放 `AppScope/resources/rawfile/`。
2. `PushService.ets` 已实装 `pushService.getToken()` → 上报 X 服务器 `/api/push/register`（AGC 配置到位后自动激活）。
3. 服务端经 Push Kit REST 下发「订阅类 SUBSCRIPTION」通知（含行情提醒，锁屏+铃声+不限量；自分类申请约 15 工作日）。
4. 通知 click 参数带 `alertId` → `onNewWant` → 页面自动播报对应音频。

降级链：Push 未实装时 App 打开期间 5s 轮询兜底，首屏永不空白。

## 合规红线

1 台自用、不收费；只报涨跌幅/量能/价格穿越等客观事实；不碰荐股。
## 功能清单（当前版本 0.1.0）

- ✅ 大字异动卡片流（点卡即听）
- ✅ 适老化模式 / 正常模式切换（适老化=大字大卡，正常=标准紧凑）
- ✅ 夜间模式 / 白天模式切换（夜间=深色底高对比，白天=浅色底清晰明亮）
- ✅ 免打扰模式（指定时段内自动播报静默，手动点击不受限）
- ✅ 自选股管理（添加/删除，过滤显示）
- ✅ 播报开关（关后自动播报静默，手动点击不受限）
- ✅ 字体大小切换（标准/特大，适老化模式锁定特大）
- ✅ 首屏示例卡兜底（服务未连通时显示带「示例」字样的演示卡）
- ✅ Push Kit 占位封装（AGC 未配置时自动降级轮询）
- ✅ 前台 5s 轮询兜底（退避策略：失败翻倍封顶 30s，429 限流静默跳过）
- ✅ 冷启动通知缺口修复（want 参数 alertId 经 onCreate 补检）
- ✅ Push 场景化消息接收器（DEFAULT 类型，前台时直接传递给应用）
- ✅ 信号卡「自家信号」角标（kind=signal，与事实卡 kind=fact 视觉区分）
- ⏳ 签名配置（需机主在 DevEco Studio 中配置 signingConfigs）
- ⏳ AGC 平台审批 P5（订阅通知自分类，约 15 工作日）
- ⏳ X 服务器落地（替换 FEED_URL 占位值）
- ⏳ 模拟器验证（DevEco Studio 6.0.2 < devecocli 要求的 6.1.0）
