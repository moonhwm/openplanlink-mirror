# 网络请求层审查——https 封装、超时处理、重试机制、降级策略

## 一、审查范围与总评

本篇为 harmony-app（代号铃语）端侧网络层的审查知识资产。端侧网络调用共两处（均在本审查当日完整通读）：

- entry/src/main/ets/services/AlertPoller.ets（100 行）：数据主通道，GET 拉取异动 feed；
- entry/src/main/ets/services/PushService.ets reportToken（:77-97）：token 上报通道，POST。

URL 配置层为 SettingsService.getFeedUrl（SettingsService.ets:351-361），默认值与 AlertPoller.DEFAULT_FEED_URL（AlertPoller.ets:10）同为 CloudBase 云函数 https 端点，Settings 页可改（Settings.ets:514-530）。

总评：**两处调用各自手写、没有统一封装，但单点质量都不差**——超时显式、finally 必 destroy、错误按 HTTP 语义分级、退避与静默降级齐全。当前"两处复制粘贴"尚可容忍，第三处网络调用出现之前应抽出统一封装（第三节给出骨架）。全链路 https、无明文 http、无内嵌密钥，合规红线达标。

## 二、https 与封装现状审查

两个端点均为 https（AlertPoller.ets:10、PushService.ets:11）， feed 地址支持用户改写但 Settings 页提示语明确"X 服务器落地后替换为正式地址；本机联调可填局域网 IP"（Settings.ets:532），改写入口与默认值同源（getFeedUrl），无第二真相源。

两处调用的公共样板完全一致：http.createHttp() → request(选项) → finally req.destroy()（AlertPoller.ets:39、:85-87；PushService.ets:78、:94-96）。destroy 纪律是 NetworkKit 的坑位知识——不 destroy 会泄漏连接，本仓两处都做对了。差异点：POST 带了 Content-Type: application/json（PushService.ets:84），GET 未带任何 header（无需）；AlertPoller 未显式设 expectDataType，NetworkKit 默认返回 string，与 JSON.parse 用法匹配（但见第七节建议 4）。

**封装建议（第三处出现前落地）：** 统一一个 NetKit 静态类收敛样板与常量，示意（零三方依赖，仅 @kit.NetworkKit）：

```typescript
export class NetKit {
  static readonly CONNECT_TIMEOUT = 5000;
  static readonly READ_TIMEOUT = 5000;

  static async getJson(url: string): Promise<string> {
    const req = http.createHttp();
    try {
      const resp = await req.request(url, {
        method: http.RequestMethod.GET,
        connectTimeout: NetKit.CONNECT_TIMEOUT,
        readTimeout: NetKit.READ_TIMEOUT,
        expectDataType: http.HttpDataType.STRING
      });
      if (resp.responseCode !== 200) {
        throw new Error(`http ${resp.responseCode}`);
      }
      return resp.result as string;
    } finally {
      req.destroy();   // 泄漏防线唯一收敛点
    }
  }
}
```

收益：超时常量单点、destroy 单点、状态码语义单点；AlertPoller 与 PushService 各删 15 行样板。

## 三、超时处理审查

两处均为 connectTimeout 5000 + readTimeout 5000（AlertPoller.ets:43-44；PushService.ets:82-83）。评估：

- **数值合理。** feed 是轻量 JSON（limit=20 条），5 秒读超时是服务端异常时的合理止损；token 上报同理。连接 5 秒照顾弱网老人（电梯、农村 4G）。
- **叠加上限明确。** 理论最坏 connectTimeout + readTimeout ≈ 10 秒一次请求；配合轮询退避（第四节），弱网下最长感知间隔可控，不会出现"永远转圈"的界面态——因为 UI 不转圈，界面始终显示旧数据或演示卡，超时只影响数据新鲜度。这正是适老化网络层的正确姿态：**网络慢不传导为界面焦虑**。
- **待改进：** 超时值在两文件各写一份字面量，应随第二节 NetKit 常量化；feed 未来若变大（limit 提高）需重估 readTimeout，建议与 limit 联动注释。

## 四、重试机制审查

**重试分两型，本仓各有一处，口径完整：**

1. **轮内退避型（AlertPoller）：** 单次 fetchLatest 不做同轮重试（快速失败），由外层 pollLoop 以 AlertPoller.getInterval() 决定下一轮（Index.ets:146-149）；失败 applyBackoff 间隔翻倍封顶 30000ms（AlertPoller.ets:90-95），成功 resetBackoff 复位 5000（:97-99）。指数退避 + 封顶，教科书式实现，且退避作用于"轮询节奏"而非"请求内 sleep"，不占主线程。
2. **即时延迟重试型（PushService.getToken）：** 命中官方文档口径的 4 个可重试错误码（1000900001、1000900008、1000900009、1000900011，PushService.ets:14）且未超 3 次（:15）时 setTimeout 1 秒重试（:63-71）。错误码白名单避免对确定性失败（未开通权益类）空转，正确。

**重试盲区（与 A26 审查呼应，此处从网络层视角补充）：** reportToken 的 POST 失败无重试（PushService.ets:90-93）——对一次性上报而言，失败即永久丢 token，建议补 3 次延迟重试；setTimeout 句柄未持有、init 重入会叠加（同前）。另有边界提醒：指数退避无抖动（jitter），多设备同时恢复时会形成同步脉冲，端侧规模小可忽略，记录在案。

## 五、降级策略审查（本篇核心）

网络层的降级设计是本仓最成熟的部分，分四层：

1. **通道级降级：** Push 未配置（AGC 缺探测，PushService.init :30-33）→ 前台 5 秒轮询兜底（AlertPoller 注释 :20-21 明示推送实装后轮询保留作拉齐补偿）。推送与轮询双通道并存，任一失效另一可用。
2. **响应级降级（按 HTTP 语义分支）：** fetchLatest 对 429 单列——返回 { ok:false, rateLimited:true } 并静默跳过（AlertPoller.ets:47-52），Index.refresh 对 rateLimited 分支不递增失败计数、不惊动用户（Index.ets:192-193，白皮书 §3.2.4 的落地）；5xx 与其他非 200 统一 ok:false + 退避（:54-64）。语义区分准确：429 是"服务端让慢点来"，5xx 是"服务端坏了"，前者不该吓用户也不该立刻加倍重试风暴——现状 429 也 applyBackoff，属于温和加轮间隔，可接受。
3. **界面级降级：** 连续失败 ≥2 次置 connectionBroken，顶栏提示「连接中断，显示旧数据」（Index.ets:195-199），旧 items 不清空——断网时老人看到的是"旧行情 + 一行说明"，不是白屏或报错弹窗。首屏未连通时用 DEMO_ITEMS 演示卡（:13-23，「示例」字样防误导）。连通但空 feed 显示「今日暂无异动」（:430-443）。**ok 与 items 空的语义分离**（PollResult 接口注释，AlertPoller.ets:12-17）是整套降级的地基：ok=true 且空 = 真没异动（可信空态）；ok=false = 数据不可信（保旧/演示）。
4. **生态级降级（服务端侧，端侧只留契约）：** Tushare token 失效（40101）已降级东财 API、百炼 TTS 只支持 WebSocket、audioUrl undefined 时端侧按需调 generate-tts——这三件属 X 服务器/云函数域，端侧对策已内建：audioUrl 缺失仅隐藏播报钮（Index.ets:390 的 if (item.audioUrl)），feed 契约不变。端侧网络层对上游抖动是封闭的，这是"契约即 AlertFeed"架构基调的红利。

## 六、并发与状态一致性审查

pollLoop 是 setTimeout 串行链：refresh await 完成后才排下一轮（Index.ets:146-149），**天然无并发重叠**，不需要请求去重/取消逻辑；refresh 内部对 playingId/loadingId/failedId 与新列表做三方核对，被服务端撤下的卡片会停播复位（:166-177），防止"对已消失的 alert 调 stop 后又设 playingId"的竞态——togglePlay await 返回后再核对 loadingId 是否仍是自己（:260-263），注释明示此防御。审查结论：**异步时序已按"await 后状态可能已变"的前提设防，是本仓质量最高的段落之一。**

## 七、改进建议汇总（按优先级）

- P2 抽 NetKit 统一封装（第二节骨架），收敛超时/destroy/状态码样板；三处网络调用出现前完成。
- P2 reportToken 补 3 次延迟重试；PushService 的 setTimeout 句柄化。
- P3 AlertPoller.request 显式 expectDataType: http.HttpDataType.STRING，防服务端异常头导致 result 类型漂移。
- P3 429 可考虑不加退避仅维持 5s（限流已是服务端明确节奏信号）；或对 429 计数连续 N 次后才退避，避免单次限流拖慢后续真数据。
- P3 feed 支持 If-Modified-Since/ETag（需服务端配合），省流量——老人多为流量敏感人群。
- 红线自查：请求头与日志不含任何 token 明文/密钥（token 上报是业务字段非凭据泄露，push token 本身即设备标识，仅上报给自有云函数，符合边界）。

## 八、验证清单

- [ ] 断网冷启：演示卡出现，退避日志间隔 5s→10s→…→30s
- [ ] 断网中途：顶栏「连接中断，显示旧数据」，旧卡不清
- [ ] 429 注入：无用户可见变化，日志 rate-limited
- [ ] 恢复网络：1 轮内复位 5s 间隔，connectionBroken 消失
- [ ] 抓包确认全部 https、无自定义 header 泄密
- [ ] req.destroy 覆盖所有请求路径（含异常路径）

### 自我评估
- 正确性：4分 全部行号来自本次实读的 AlertPoller.ets、Index.ets、PushService.ets、SettingsService.ets、Settings.ets；降级分层与时序防御结论均对应具体代码段；NetKit 骨架未在本环境编译运行（属建议代码），扣一分声明。
- 完整性：4分 覆盖 https/封装、超时、两型重试、四层降级、并发一致性、改进与验证清单；服务端侧降级（东财/WS/generate-tts）仅述端侧对策，服务器内幕超出端侧审查边界。
- 可复用性：4分 四层降级框架与"ok/空语义分离"可直接迁移到任何轮询型应用；NetKit 骨架零依赖可直接取用。
- 字数：约3600字
- 使用模型：GLM-5.3-Flash
