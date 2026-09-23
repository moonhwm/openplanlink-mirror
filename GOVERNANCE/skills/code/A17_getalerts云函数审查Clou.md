# A17｜get-alerts 云函数审查——CloudBase 存储读取优化、缓存策略、降级方案

> 项目：harmony-app（铃语，鸿蒙适老化股票异动播报）。本篇自包含成文，全部结论基于本仓库源码通读，引用给路径与行号；未做云端压测（无环境），量化估算处均标注为估算。

## 一、审查范围与现状画像

审查对象：`cloudfunctions/functions/get-alerts/index.js`（76 行，全文通读）与同目录 package.json（仅依赖 `@cloudbase/node-sdk ^3.0.0`）。参照物：部署配置 `cloudfunctions/cloudbaserc.json`（get-alerts 段：Nodejs18.15，timeout 10 秒，无环境变量）；端侧消费方 `entry/src/main/ets/services/AlertPoller.ets`（100 行）与数据契约 `entry/src/main/ets/model/AlertItem.ets`；写入方 `cloudfunctions/functions/fetch-tushare-data/index.js`。

函数职责一句话：Event 函数 + CloudBase HTTP 访问服务（`--path /alerts`，文件头注释 15-16 行），每次请求从云存储下载 `alerts/alerts.json`，按 ts 降序取前 limit 条，返回 `{items, serverTs}`。它是端侧 5 秒轮询的唯一数据出口（AlertPoller.ets:10 默认地址 `https://a2a-commonwealth-d2eepjr928e9c4d.service.tcloudbase.com/alerts`，可被 SettingsService.getFeedUrl 覆盖，SettingsService.ets:351-356），是全应用"首屏永不空白"链条的第一环。契约与 `AlertItem.ets:19-22` 的 `AlertFeed{items,serverTs}` 完全一致。

## 二、读取链路审查

### 2.1 现状链路逐步拆解

`getLatestAlerts`（index.js:26-51）：require SDK → `cloudbase.init` → `app.downloadFile({fileID: ALERTS_FILE_ID})` → `JSON.parse` → `data.items.sort((a,b)=>b.ts-a.ts)` → `slice(0,limit)`。四个结构性事实：

1. **全量下载**：alerts.json 由 fetch-tushare-data 保留最新 500 条（fetch-tushare-data/index.js:537-540），单条 AlertItem 约 300-500 字节，全文件估 150-250KB。每次轮询都下载全量，**下载放大比** = 500/limit（limit 默认 20，即 25 倍）。
2. **每次请求重新 init**：`cloudbase.init({env})` 在函数体内（index.js:28-29），冷热启动都执行。对照 fetch-tushare-data/index.js:28-37 的单例模式（注释明言"避免重复 init 导致连接泄漏"），get-alerts 未跟进。
3. **fileID 硬编码**（index.js:21）：env 变更时需改代码，且与 generate-tts/index.js:25、broadcast-a2a/index.js:22 三处重复同一串 fileID——三胞胎常量，任何一处漂移都静默读旧桶。
4. **排序在读侧**：sort 每请求执行 O(n log n)，n=500 时微不足道，真正的成本全在下载与解析，不是排序。

### 2.2 下载放大的量化估算

端侧行为：前台每 5 秒一次（AlertPoller.ets:30 `currentInterval=5000`），失败退避翻倍封顶 30 秒（AlertPoller.ets:90-95）。假设 100 台在网设备、正常时段 5 秒节奏：100 × 12 次/分 × 200KB ≈ **每分钟 240MB 出口流量**，全部是重复内容（alerts.json 只在 fetch-tushare-data 定时触发后才变化，一天变化次数有限）。即使只有 10 台设备也在 24MB/分钟量级。HTTP 访问服务按流量计费且轮询是永久背景行为——这是当前架构里最贵的一条路，优化收益直接。

## 三、读取优化三方案

### 方案A：增量协议（改动最小，收益最大）

端侧 5 秒轮询的本质诉求是"有没有新条目"，绝大多数轮询答案是"没有"。给出口加 `since` 参数，命中"无更新"时返回极小响应：

```js
exports.main = async (event, context) => {
  const limit = Math.min(parseInt(event?.query?.limit || '20', 10), 100);
  const since = parseInt(event?.query?.since || '0', 10); // 端侧传上次 serverTs
  const data = await readAlertsFile();          // 见 3.1 缓存化
  const items = since > 0
    ? data.items.filter(i => i.ts > since).sort((a,b)=>b.ts-a.ts).slice(0, limit)
    : data.items.sort((a,b)=>b.ts-a.ts).slice(0, limit);
  const changed = data.serverTs > since && items.length > 0;
  return {
    items: changed ? items : [],   // 无更新时空数组，几百字节
    serverTs: data.serverTs,       // 数据水位，不是 Date.now()
    changed,
  };
};
```

两个关键点：其一，`serverTs` 必须回传**文件内的数据水位**（fetch-tushare-data/index.js:544 写入的 serverTs），而不是现在的 `Date.now()`（index.js:67）——现在端侧拿到的 serverTs 每次都变，根本没法当水位用；其二，端侧 AlertPoller 需配套记住上次 serverTs 并在 URL 拼接 `?since=`，AlertPoller.ets:41 的请求拼串处是唯一改动点。**注意语义变化**：AlertItem.ts 是秒级时间戳（AlertItem.ets:8），fetch-tushare-data 的 createAlertItems 用 `alertId: ${symbol}_${now}` 且同一秒内可能产出多条同 symbol 条目（fetch-tushare-data/index.js:476-489），用 `i.ts > since` 过滤是安全的（水位比较），但端侧去重逻辑（若靠 alertId）不受影响，需在联调时确认同秒多条不丢。

### 方案B：函数实例内存缓存

无论是否上增量协议，都应在实例内缓存 alerts.json 解析结果，TTL 1-2 秒：

```js
let _cache = null, _cacheTs = 0; const TTL = 2000;
async function readAlertsFile() {
  if (_cache && Date.now() - _cacheTs < TTL) return _cache;
  const app = getCloudbaseApp();               // 单例，同 fetch-tushare-data 纪律
  const result = await app.downloadFile({ fileID: ALERTS_FILE_ID });
  _cache = JSON.parse(result.fileContent.toString('utf-8'));
  _cacheTs = Date.now();
  return _cache;
}
```

效果：同一实例 2 秒内的 N 次轮询合并为 1 次下载。云函数实例常驻窗口内（SCF 热实例通常存活数十秒到数分钟），热路径下载次数可降一个数量级。代价是实例间缓存不一致——但 TTL 2 秒的陈旧度完全在"5 秒轮询"的容忍度内。方案A+B 叠加是推荐落点。

### 方案C：迁数据库集合（治本，配合 A18/A20）

文件总线（alerts.json）的根问题是"读放大 + 写覆盖竞态 + 无索引"。把 alerts 迁入数据库集合（fetch-tushare-data 写入时按 alertId upsert；get-alerts 查询 `collection.where({}).orderBy('ts','desc').limit(limit)`，ts 建降序索引）后：读取量 = limit 条而非全文件；get-alerts 出口直接查库，downloadFile 从热路径消失；generate-tts 的 audioUrl 回写也变成单字段 update（根治 A16 篇 6.4 的覆盖丢数据问题）。这是与 A18（init-db 集合与索引设计）、A20（架构演进）联动的方向，建议作为二期，一期先落 A+B 止血。

## 四、缓存策略分层总览

全链路现有与建议的缓存层次：

| 层 | 现状 | 建议 |
|---|---|---|
| 端侧内存 | AlertPoller 每轮全换、Index 卡片流按 alertId 合并（Index.ets:226-250 一带） | 维持；增量协议下只 append 新条目 |
| 端侧退避 | 失败翻倍封顶 30s（AlertPoller.ets:90-95）；429 静默（47-52） | 维持，是服务端限流的对端契约 |
| HTTP 访问服务 | 无缓存头可控性（Event 函数形态） | 如需 `Cache-Control` 需转 Web 函数模式，非必需 |
| 函数实例内存 | 无 | 方案B，TTL 2 秒 |
| 存储层 | alerts.json 本身就是上游产物快照（500 条滚动） | 维持；二期集合化后此层退役为备份 |

一个明确结论：**不建议在 get-alerts 里做"演示数据兜底缓存"**。首屏永不空白由端侧演示卡实现（共享约束），服务端掺演示数据会让"连通但无异动"与"故障"两种状态在协议上无法区分，污染契约。

## 五、语义缺陷：读失败伪装成"无异动"

现有两层 catch 都把异常吞成空数组：`getLatestAlerts` 内层 catch 返回 `[]`（index.js:47-50），main 外层 catch 返回 `{items:[], serverTs}`（index.js:69-75），加上文件不存在也是 `[]`（index.js:46）。于是**服务端故障与真实无异动对端侧完全同形**：都是 HTTP 200 + items:[]。端侧 PollResult 的三态设计（ok=false 网络/HTTP 异常、ok=true items 空 = 连通但无异动，AlertPoller.ets:12-17 注释写得很清楚）在服务端这一侧被破坏了——云存储故障时，用户看到的是干净的空列表，AlertPoller 认为 ok=true 不退避，还会以 5 秒频率继续打在故障的服务上。

修复：让失败显式失败。文件读取异常时向上抛，让 HTTP 访问服务返回 5xx（端侧 54-58 行已有 5xx 分支会退避）；或保守起见返回带 degraded 标记：

```js
} catch (e) {
  console.error('get-alerts error:', e.message);
  throw e;   // 推荐：映射为 5xx，端侧已有退避分支承接
  // 或：return { items: [], serverTs: 0, degraded: true };
}
```

注意 `serverTs: 0` 的降级返回不可与"正常水位"混淆——端侧若已用方案A，收到 serverTs=0 应视作异常不更新本地水位。同时建议区分"文件不存在"（首次部署前的正常态，返回空列表即可）与"文件存在但 JSON.parse 失败"（数据损坏，应告警并抛错），现在是混在一处 catch 里（index.js:47-49）。

## 六、降级方案设计

### 6.1 故障面盘点

get-alerts 的依赖只有两样：CloudBase 存储（alerts.json）与 CloudBase 平台本身。对应故障面：a) alerts.json 缺失（首次部署/误删）；b) alerts.json 损坏（写覆盖竞态的产物，A16 篇 6.4 已证实回写无保护）；c) 云存储服务故障；d) HTTP 访问服务限流/故障。

### 6.2 分级降级

- **c/d 级（平台级）**：函数侧无能为力，交给端侧既有机制——5xx/网络异常 → ok=false → 演示卡兜底 + 退避轮询。这符合共享约束"服务未连通显示带示例字样演示卡"，服务端不要画蛇添足返回假数据。
- **b 级（数据损坏）**：建议引入**双写备份**。写入方 fetch-tushare-data 在覆盖 alerts.json 前先把旧文件复制为 `alerts/alerts-backup.json`（或写入数据库 alerts_backup 集合）；get-alerts 读主文件 JSON.parse 失败时自动回退读备份并在响应中带 `source:'backup'`，控制台日志告警。改动集中在写入方一行 + 读取方一个 fallback 分支，收益是把"单文件损坏 = 数据全灭"变成"最多丢最近一个写入周期"。
- **a 级（文件缺失）**：返回空 items 是正确行为（端侧演示卡接管），但要打 `console.error` 级别日志（现在 catch 内是 error 级，可保持），避免首部署静默无数据无人发现。
- **限流协同**：端侧对 429 的静默处理（AlertPoller.ets:47-52，rateLimited 单独标记不惊动用户）是现成的对端契约，建议在 CloudBase HTTP 访问服务上对 /alerts 路径配置并发/频率限流，把方案A/B 的收益转化为真实的成本保护，而不是裸奔。

### 6.3 与上游降级的边界

共享上下文已知问题"Tushare token 失效(40101)已降级东财 API"发生在 fetch-tushare-data 层（其 index.js:123-272 的名称映射五级降级），get-alerts 自身零外部数据源依赖，不需要也不应该复刻任何数据源降级逻辑——它的降级问题全部围绕"自己那份文件的可用性"。

## 七、其余小项

limit 解析（index.js:58-61）已做 Math.min(…,100) 上限保护且容忍 query 与顶层两种入参形态，正确保留。`sort` 前未校验 `ts` 类型：若上游某条目 ts 为字符串，`b.ts - a.ts` 会算出 NaN 破坏排序——当前写入方恒写数字（fetch-tushare-data/index.js:443 `const now = Math.floor(Date.now()/1000)`），风险低，但集合化改造时应在 schema 层约束。日志面：请求级日志未记录 limit/since 与命中情况，方案A落地时建议补 `console.log(JSON.stringify({limit, since, changed, took}))` 便于观察轮询命中率。

## 八、修复优先级清单

| 级别 | 事项 | 位置 | 依据 |
|---|---|---|---|
| P0 | 失败显式化：读异常抛错/带 degraded，区分损坏与缺失 | index.js:47-50, 69-75 | 五，故障被伪装成无异动 |
| P0 | serverTs 回传数据水位而非 Date.now()（配合 since 增量） | index.js:67 | 方案A，端侧已备好三态 |
| P1 | 实例内存缓存 TTL 2s + SDK 单例化 | index.js:28-29 | 方案B/2.1-2 |
| P1 | since 增量参数 + 端侧 AlertPoller 拼接联动 | index.js:57-76 | 方案A，降流量 25 倍起 |
| P1 | 上游双写备份 + 读取 fallback | fetch-tushare-data/index.js:549 附近 | 6.2-b |
| P2 | HTTP 访问服务配置 /alerts 限流 | cloudbaserc.json（访问服务侧） | 6.2-限流协同 |
| P2 | alerts 集合化与 ts 降序索引 | 联动 A18/A20 | 方案C |

## 九、未实测项

未做：真实环境压测（下载放大与缓存命中率是估算值）、CloudBase HTTP 访问服务对 Event 函数抛错时的具体状态码映射（建议施工 P0 第一项时用 curl 验证一次 5xx 形态）、AlertPoller 端侧 since 联动的联调（属端侧任务）。上述均已标注，不作为已验证结论。

### 自我评估
- 正确性：4分 全部结论有行号证据；"失败伪装成无异动"与"serverTs 不能当水位"两处为源码直读所得的关键发现；下载放大比标注为估算。
- 完整性：4分 读取优化三方案、四层缓存、分级降级、优先级清单齐备；未展开 HTTP 访问服务计费细则。
- 可复用性：4分 方案A/B 代码可直接粘贴，P0 两项可独立施工；方案C 依赖 A18/A20 联动已明示边界。
- 字数：约5000字
- 使用模型：GLM-5.3-Flash
