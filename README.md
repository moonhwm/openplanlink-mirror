# 行情播报（StockPulse）· 鸿蒙 NEXT 私有分发工程

适老化行情异动播报 App。**云端（X 服务器）秒级监测 → Push Kit 推送 → 锁屏大字通知 → 点按拉起 → 自动语音播报**。只报客观异动事实，不含任何买卖建议。

- 目标机型：Mate X5（HarmonyOS NEXT 纯血）；`compatibleSdkVersion 20`（6.0）/ `targetSdkVersion 26`（7.0）
- 形态：原生 ArkTS Stage 模型，单 entry 模块，零三方依赖
- 分发：私有调试证书直装（免审核免软著免备案零公开，100 台/年）

## 目录

```
AppScope/                 应用级配置（bundleName=com.yehang.stockpulse）
entry/src/main/ets/
  entryability/           EntryAbility（Push 初始化 + 通知点击带 alertId 拉起）
  pages/Index.ets         大字异动卡片流，点卡即听（服务未连通时显示「示例」卡）
  services/PushService    Push Kit 占位封装（无 AGC 配置自动降级）
  services/AlertPoller    前台 5s 轮询兜底（FEED_URL 待 X 落地后替换）
  services/AudioPlayer    云端 TTS 音频流点按播报（AVPlayer）
  model/AlertItem         异动事实卡数据契约
```

## 构建（CodeArts Build 云构建，本机红灯机不装 DevEco）

1. 把本目录上传码道仓库（CodeArts Repo）。
2. CodeArts Build 新建构建任务 → 选官方「HarmonyOS 应用构建」模板（自带 SDK/Hvigor，免本机环境）。
3. 产物 `entry-default-signed.hap` 下载后经 `hdc install` 装 X5。

待核：Build 鸿蒙模板免费分钟数、机主码道挂账是否含 Build（X 采购时一并问客服经理）。
注意：码道 AI 编码额度（体验版 500 万 tokens/月）09-09 已 100% 封顶，10 月重置——本工程不依赖码道额度，不受影响。

## 签名与装机（机主一次动作，约 10 分钟）

1. 免费注册华为个人开发者（无费用）。
2. 任一可联网电脑装 DevEco Studio → 打开本工程 → 自动化签名（自动生成调试证书+profile）。
3. X5 开开发者模式 → UDID 录入调试设备列表 → `hdc install` 直装。
4. 调试证书一年有效，到期重签（已建日历提醒）。

## 推送实装（候 AGC）

1. AppGallery Connect 建项目+应用，开通 Push Kit，下载 `agconnect-services.json` 放 `AppScope/resources/rawfile/`。
2. `PushService.ets` 内 TODO 解封：`pushService.getToken()` → 上报 X 服务器 `/api/push/register`。
3. 服务端经 Push Kit REST 下发「订阅类 SUBSCRIPTION」通知（含行情提醒，锁屏+铃声+不限量；自分类申请约 15 工作日）。
4. 通知 click 参数带 `alertId` → `onNewWant` → 页面自动播报对应音频。

降级链：Push 未实装时 App 打开期间 5s 轮询兜底，首屏永不空白。

## 合规红线

1 台自用、不收费；只报涨跌幅/量能/价格穿越等客观事实；不碰荐股。
