# code技能：ArkTS网络请求封装——超时、重试与降级

> 编写时间：2026-09-23
> 编写席位：Moon席位批次写手-B组-1号（GLM-5.3-Flash）
> 适用范围：harmony-app（铃语）端侧 ArkTS 与云函数 Node 两侧的全部网络代码
> 事实来源：端侧范式取自 `entry/src/main/ets/services/AlertPoller.ets`、`entry/src/main/ets/services/PushService.ets`、`entry/src/main/ets/services/SettingsService.ets:24-27`；云侧取自 `cloudfunctions/functions/fetch-tushare-data/index.js`。行号均已核对。

## 0. 两端分层总览（自包含背景）

铃语的网络路径只有两类：

1. **端侧 → CloudBase 云函数**：`Index.ets` 每 5 秒经 `AlertPoller.fetchLatest()` 拉 `FEED_URL`（默认 `https://a2a-commonwealth-d2eepjr928e9c4d-1475054847.ap-shanghai.app.tcloudbase.com/alerts`，`SettingsService.ets:24-27`），契约即 `AlertFeed`（`entry/src/main/ets/model/AlertItem.ets:19-22`）；另有 Push Token 上报 `POST /push-token-register`（`PushService.ets:12`）。
2. **云函数 → 外部 API**：Tushare 行情、东方财富列表、百炼 TTS WebSocket 等，运行在 Node 侧。

端侧零三方依赖，只用系统 `@kit.NetworkKit` 的 `http`；云侧只用 Node 内置 `https`。**两侧都不许引入 axios 等三方库**。

## 1. 端侧封装规范（NetworkKit / @ohos.net.http）

### 1.1 标准形态（现网 `AlertPoller.ets:34-85`）

```typescript
import { http } from '@kit.NetworkKit';

static async fetchLatest(limit: number = 20): Promise<PollResult> {
  const feedUrl = await SettingsService.getFeedUrl();
  const req = http.createHttp();               // 每次请求新建实例
  try {
    const resp = await req.request(`${feedUrl}?limit=${limit}`, {
      method: http.RequestMethod.GET,
      connectTimeout: 5000,                    // 连接超时
      readTimeout: 5000                        // 读取超时
    });
    // —— 状态码阶梯（见 1.2）——
    if (resp.responseCode === 429) { /* 限流：静默 */ }
    if (resp.responseCode >= 500) { /* 服务端错 */ }
    if (resp.responseCode !== 200) { /* 其他错 */ }
    const feed = JSON.parse(resp.result as string) as AlertFeed;  // 解析防护见 1.3
    return { ok: true, items: feed.items ?? [] };
  } catch (e) {
    return { ok: false, items: [] };           // 网络/超时异常统一收口
  } finally {
    req.destroy();                             // 无条件销毁，防句柄泄漏
  }
}
```

五条铁规：

1. **`http.createHttp()` 一次一建、`finally` 里 `destroy()`**——复用全局实例在弱网下会积累未完成请求；不 destroy 会泄漏底层句柄；
2. **双超时必设**（连接 5s、读取 5s），不设超时的请求在断网时悬挂到系统默认值，轮询节奏全乱；
3. **返回结构化结果而非抛异常**：`PollResult { ok, items, rateLimited? }`（`AlertPoller.ets:10-14`），调用方拿分支语义（成功/失败/限流）而不是 try-catch 控制流——UI 层不写 catch；
4. **`feed.items ?? []` 兜底**：服务端缺字段时落空数组，不落 undefined；
5. URL 从 `SettingsService.getFeedUrl()` 动态取（`AlertPoller.ets:35`），支持数据源切换（X 服务器落地后换 URL 即可，契约不变）。

### 1.2 状态码阶梯

| responseCode | 语义 | 处理 | 现网依据 |
| --- | --- | --- | --- |
| 200 | 成功 | 解析 JSON，`ok=true` | `AlertPoller.ets:57-76` |
| 429 | 限流 | `ok=false` + `rateLimited=true`，静默、退避、不清数据 | `AlertPoller.ets:44-49` |
| ≥500 | 服务端故障 | `ok=false`，退避 | `AlertPoller.ets:51-55` |
| 其他（4xx 等） | 客户端/网关异常 | `ok=false`，退避 | `AlertPoller.ets:57-61` |
| 抛异常 | DNS/超时/断网 | `ok=false`，退避 | `AlertPoller.ets:78-81` |

要点：429 与普通失败**分开表达**——限流说明服务活着，不打扰用户（不置"连接中断"提示），但同样触发退避让服务喘口气。

### 1.3 解析防护

`JSON.parse` 单独 try-catch，失败记**原文前 200 字符**再返回失败（`AlertPoller.ets:64-72`）：截断既保留排障线索，又避免把整页 HTML 错误页打进日志。解析失败按 `ok=false` 计，不把半截数据交给 UI。

### 1.4 轮询循环的组织

- 自调度 `setTimeout` 链而非 `setInterval`：`pollLoop()` 先 `await refresh()` 再排下一轮（`Index.ets:146-149`），上一轮未完成不会叠帧；
- 间隔从 `AlertPoller.getInterval()` 动态取（148 行），退避态自动拉长；
- **清理对称**：`aboutToDisappear` 里 `clearTimeout(this.timer)`（`Index.ets:110-116`），页面销毁后循环必停。

## 2. 超时控制总表

| 层 | 请求 | 连接/总超时 | 依据 |
| --- | --- | --- | --- |
| 端侧 | feed 轮询 GET | 5s / 5s | `AlertPoller.ets:40-41` |
| 端侧 | Token 上报 POST | 5s / 5s | `PushService.ets:83-84` |
| 云侧 | Tushare / 东财 | 15s | `fetch-tushare-data/index.js:152` 走 requestHttps 默认档 |
| 云侧 | TTS WebSocket | 15s 级 | `generate-tts/index.js:202`（超时后走部分音频兜底） |

原则：**端侧超时 < 轮询间隔**（5s 请求超时对 5s 轮询，最坏刚好错过一轮，可接受）；**云侧单请求超时 < 云函数总执行预算**；跨层叠加的最坏路径（端 5s → 云 15s → 外部 15s）要保证端侧先超时返回，不让用户侧悬挂。

## 3. 重试机制

### 3.1 端侧：轮询本身就是重试

前台 5 秒一轮意味着"最多 5 秒后自动重试"，**端侧不做请求内重试**——避免同一时刻双倍请求放大服务端压力。失败的处理交给退避与降级（第 4 节）。

### 3.2 端侧例外：错误码白名单重试（PushService 范式）

Push Token 获取不是轮询场景，采用**白名单 + 有限次 + 固定间隔**（`PushService.ets:14-17,64-72`）：

```typescript
const RETRYABLE_ERROR_CODES = [1000900001, 1000900008, 1000900009, 1000900011];
const MAX_RETRY_COUNT = 3;
const RETRY_INTERVAL = 1000;
// 失败时：错误码在白名单内且未超次数 → 1s 后重试；否则放弃并降级
```

规则：只有**明确可重试的系统错误码**才重试（白名单来自 Push Kit 官方文档语义）；业务性失败（如 AGC 未配置，`PushService.ets:100-107` 探测 rawfile 缺失即静默降级轮询）重试无意义；重试次数与间隔写死常量，不做无限重试。

### 3.3 云侧：指数退避重试

```javascript
async function requestHttpsRetry(url, options = {}, maxRetries = 2) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try { return await requestHttps(url, options); }
    catch (e) {
      if (attempt === maxRetries) throw e;
      const delay = 500 * Math.pow(2, attempt);   // 500ms → 1s
      await new Promise(r => setTimeout(r, delay));
    }
  }
}
```

只对幂等读重试；写/推送类不重试防重复副作用。配套的 `requestHttps` 完整封装（含 `req.on('error')` 与 `setTimeout → req.destroy(err)` 收口，超时默认 15s）的逐行规范见姊妹篇 `GOVERNANCE/skills/code/arkts-cloud-function-pattern.md` 第 1 节——注意 `req.on('error+timeout', ...)` 这类伪事件名写法是历史文档笔误，Node 无此事件，超时必须走 destroy 转发。

## 4. 降级策略

### 4.1 端侧四层降级（现网行为）

```
拉取成功 → 正常渲染
   ↓ 失败
保持当前数据不清空（旧数据继续可见）
   ↓ 连续 2 次失败
顶栏提示「连接中断，显示旧数据」（Index.ets:194-198,335-339）
   ↓ 从未成功过
DEMO_ITEMS 演示卡兜底（Index.ets:13-28，带「示例」字样，首屏永不空白）
   ↓ 连通但空
空态文案「今日暂无异动」（Index.ets:430-443）
```

要点：**失败永不删数据**——老年用户最怕"内容消失"；提示是行内文字不是弹窗；恢复成功即 `connectionBroken=false`、`isDemoMode=false` 自动切回（`Index.ets:153-156`）。

### 4.2 指数退避（端侧）

失败后间隔翻倍、封顶 30 秒，成功复位 5 秒（`AlertPoller.ets:25-27,87-96`）：`5000 → 10000 → 20000 → 30000 → 30000...`。既让故障服务喘息，又保证恢复探测密度。

### 4.3 服务端降级链（端侧感知的另一半）

Tushare token 失效（40101）已在云侧降级东方财富 API（`fetch-tushare-data/index.js:100,272`）；`audioUrl` undefined 时端侧按需调 `generate-tts`。端侧无需感知源切换，只认 `AlertFeed` 契约——**契约稳定是最大的降级设计**：换数据源不动端侧代码。

## 5. 安全与日志规范

- **Token 脱敏**：云侧错误信息先 `replace(TUSHARE_TOKEN, '***')` 再抛（`fetch-tushare-data/index.js:161`）；状态日志只打 `token: 'set' : 'not set'`（616 行）；
- **不打 `e.stack`**（可能携带环境变量路径），只打 `e.message`；端侧 hilog 同理只记 message（`AlertPoller.ets:79`）；
- **响应体截断入日志**（前 200 字符）；
- **输入校验**：外部数据入库前验形（股票代码 `/^\d{6}$/`、名称非空限长）；
- 上行数据最小化：Token 上报只带 `{token, bundleName}`（`PushService.ets:86`），不夹带多余设备信息。

## 6. 并行化（云侧）

- 市场间并行 + 页内串行：`Promise.all(marketFilters.map(fs => fetchEastMoneyMarket(fs)))`；
- 非核心批量用 `Promise.allSettled`（如 TTS 批量，单条失败不拖垮整批，`generate-tts` 场景）；
- 并行 + 局部降级：`Promise.all([callTushare(...).catch(() => null), getStockNameMap()])`——主数据失败置 null 不阻塞名称映射。

## 7. 审查清单

- [ ] 端侧请求均 `createHttp` + `finally destroy`，双超时显式设置；
- [ ] 返回结构化结果（ok/items/rateLimited），UI 层无 try-catch；
- [ ] 429 与普通失败区分处理；解析失败记 200 字符原文；
- [ ] 轮询为自调度 setTimeout 链，`aboutToDisappear` 清理；
- [ ] 端侧无请求内重试（轮询即重试）；Push 类白名单重试 ≤3 次；
- [ ] 失败不清数据、演示兜底带「示例」字样、退避封顶 30s；
- [ ] 日志无 Token/stack/全量响应体；云侧外呼走 requestHttps 系。

### 自我评估
- 正确性：4分 端侧全部条文对齐 `AlertPoller/PushService/Index` 现网源码并标行号；云侧引用 `fetch-tushare-data` 实测行号；历史文档 `error+timeout` 笔误已指出并给出正确写法（依据 Node 事件语义，未在本地跑 Node 复验）。
- 完整性：4分 超时/重试/降级三大主题均有分层展开与表格；requestHttps 完整实现按分工引用姊妹篇避免重复，自包含性略有取舍但已给路径。
- 可复用性：4分 端侧模板可直接粘贴改 URL 使用；清单可直接进 CR。
- 字数：约3050字
- 使用模型：GLM-5.3-Flash
