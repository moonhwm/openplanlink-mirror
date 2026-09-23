# A21 云函数统一基础设施层设计——共享SDK初始化、共享错误处理、共享缓存层抽象方案

> 项目：harmony-app（鸿蒙适老化股票异动播报应用，代号铃语）
> 范围：`cloudfunctions/functions/` 下全部云函数（get-alerts、fetch-tushare-data、generate-tts、broadcast-a2a、push-token-register、init-db）
> 前置声明：本文所有"现状"均来自 2026-09-23 对仓库内源码文件的直接读取，行号以当日文件为准；架构基调（端侧 Index.ets 卡片流 + 5s 前台轮询 + AlertFeed 契约）不因本层改造而改变，本方案只动云端内部实现，不动端云之间的 JSON 契约与 FEED_URL 语义。

---

## 一、背景与问题定位

### 1.1 为什么需要统一基础设施层

当前 `cloudfunctions/functions/` 下六个函数各自为政，同一段"环境解析—SDK 初始化—文件读写—错误兜底"的样板代码在多个函数里重复出现，且细节互不一致。重复带来三类实际风险：

1. **不一致风险**：同一件事（比如下载 alerts.json）在不同函数里用了不同写法，其中一种很可能是有问题的，但因为分散在各自文件里，没人横向比对。
2. **漂移风险**：环境 ID、文件 ID 这类常量被复制粘贴到多个文件，一旦换环境或迁移数据路径，漏改一处就是线上事故。
3. **可观测性风险**：日志格式、错误返回结构各不相同，出问题时无法在 CloudBase 控制台按统一字段检索。

### 1.2 现状证据清单（逐文件）

**（a）`cloudbase.init` 重复初始化。** 六个函数各自调用 `cloudbase.init({ env: ENV_ID })`，且调用点分散：

- `get-alerts/index.js:28-29`（在 `getLatestAlerts` 内每次调用都 init）；
- `generate-tts/index.js:63-66`（`getCloudBaseApp()` 工厂函数，每次调用重新 init）；
- `broadcast-a2a/index.js:29-30`（`getLatestAlerts` 内）与 `broadcast-a2a/index.js:119-120`（`sendPushNotification` 内又 init 一次，同一函数文件两处）；
- `push-token-register/index.js:22-23` 与 `:59-60`（`registerToken` 与 `getActiveTokens` 各 init 一次）；
- 只有 `fetch-tushare-data/index.js:28-37` 做了模块级单例，且注释明确写了动机："CloudBase SDK 单例（避免重复 init 导致连接泄漏）"。这说明单例化是已知正确做法，只是没有推广。

**（b）环境 ID 与文件 ID 常量复制粘贴。** `const ENV_ID = process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d'` 这一行出现在 `get-alerts/index.js:19`、`generate-tts/index.js:24`、`broadcast-a2a/index.js:21`、`push-token-register/index.js:16`、`init-db/index.js`（模块顶部）共五处。`ALERTS_FILE_ID = 'cloud://a2a-commonwealth-....6132-.../alerts/alerts.json'` 硬编码出现在 `get-alerts/index.js:21`、`generate-tts/index.js:25`、`broadcast-a2a/index.js:22` 三处。

**（c）下载 API 用法不一致（疑似误用，需实测验证）。** `get-alerts/index.js:32-34`、`generate-tts/index.js:77`、`broadcast-a2a/index.js:32` 都用 `app.downloadFile({ fileID: ... })`（cloud:// 协议 fileID）；而 `fetch-tushare-data/index.js:134-136` 与 `:239-241` 用的是 `app.downloadFile({ cloudPath: 'stock-names/name-map.json' })`——`@cloudbase/node-sdk` 的 `downloadFile` 标准签名按 fileID 取文件，`cloudPath` 形态在部分版本会直接抛错。这可以解释一个现象：name-map 的"存储缓存命中"路径可能从未真正生效，函数每次都走"东方财富全量刷新"兜底（`fetch-tushare-data/index.js:162-234`）。此判断需要在测试环境实测确认，但"两种写法不一致"本身就是必须收敛的理由。

**（d）错误处理策略三套并存。**

- `fetch-tushare-data` 自建了 `requestHttps` 统一封装（`fetch-tushare-data/index.js:43-76`：Promise 化、15 秒超时、JSON 解析失败 reject），并且对 Tushare 报错做了 token 脱敏（`:106-110`：`safeMsg = (data.msg || '').replace(TUSHARE_TOKEN, '***')`）——这是全仓库最好的错误处理实践，但没有沉淀成共享模块；
- `broadcast-a2a` 用实验性 `fetch` + try/catch（`:60`、`:138`、`:186`），无超时控制；
- `generate-tts` 的 WebSocket 链路自带 30 秒超时与 close/error 兜底（`generate-tts/index.js:197-201`、`:283-299`），但错误只打日志，上层拿到的只是 `null`，无法区分"配额停机 / 鉴权失败 / 网络超时 / 任务失败"四类原因。

**（e）缓存实现三处三样。**

- 股票名称映射：内存 24h TTL + 云存储持久化 + 东方财富刷新 + 硬编码兜底 + 空 Map 绝对兜底，共五级降级（`fetch-tushare-data/index.js:123-272`）；
- 交易日：内存 1h TTL + 星期推算兜底（`:79-81`、`:278-339`）；
- TTS 音频：云存储 `tts-cache/{sha256前16}.json`，命中返回 audioUrl（`generate-tts/index.js:56-116`）。
  三处缓存的 TTL 计算、存储键命名、降级策略全不一致，且没有一处有"并发加载保护"（同名 key 同时 miss 时重复拉全量）。

**（f）配额计数器不持久。** `generate-tts/index.js:28-51` 的 `QUOTA` 对象是纯内存状态，云函数冷启动即归零，"百万 token 预警线"形同虚设。这本质上是缓存层要解决的问题（计数器需要 L2 持久化）。

**（g）文档腐化的小证据。** `get-alerts/index.js:16` 注释写的端点是 `https://{envId}.service.tcloudbase.com/alertsD`，末尾多了一个 D。统一基础设施层把端点定义收敛到单一配置后，这类注释漂移自然消失。

---

## 二、设计目标与约束

### 2.1 目标

1. 六个函数共享同一份"配置解析 + SDK 单例 + 文件存取 + 缓存 + 错误码 + 日志"基础设施，消灭 1.2 节列举的六类重复与不一致；
2. 错误可分类、可检索、可降级，敏感信息（token、secret）永不落日志；
3. 缓存抽象统一后，TTS 配额计数、name-map、trade-date、alerts.json 并发保护都走同一套机制；
4. 端云契约零变更：`AlertFeed { items, serverTs }`（`entry/src/main/ets/model/AlertItem.ets:19-22`）、`FEED_URL` 指向的 `/alerts` HTTP 端点、`generate-tts` 的 `{ alertId, text } → { success, audioUrl }` 入出参全部保持不变。

### 2.2 不可逾越的约束（继承自项目治理红线）

- 不推翻架构基调：数据源仍以 alerts.json 为准，FEED_URL 待 X 服务器落地期间，get-alerts 是唯一权威读端点；本方案不引入新的数据库依赖替代存储方案，只把存储访问收敛为共享模块；
- 合规红线：不承诺收益/保本、不输出催促性指令、不对外公开/收费——DKnowC 合规检查（`fetch-tushare-data/index.js:404-436`）作为基础设施的一部分保留并可复用，任何新的文本产出路径都必须经过它；
- 密钥红线：`TUSHARE_TOKEN`、`DASHSCOPE_API_KEY`、`DKNOWC_API_KEY`、`HUAWEI_PUSH_CLIENT_SECRET` 等全部只从环境变量读取（现状已如此，见 `fetch-tushare-data/index.js:20`、`generate-tts/index.js:20`、`broadcast-a2a/index.js:107-109`），共享配置模块不得把它们写入任何持久化缓存文件或日志；
- 云函数侧允许 Node 三方依赖（`ws`、`@cloudbase/node-sdk` 已在用），但共享模块本身零新增依赖，只用 Node 内置模块；
- 端侧"零三方依赖、纯 ArkTS"约束与本方案无关，端侧代码不动。

### 2.3 一个必须先解决的工程现实：函数间代码共享方式

CloudBase 函数按目录独立打包部署，`functions/A` 不能直接 `require('../_shared/x')`。三个可选方案：

1. **同步脚本方案（推荐）**：共享代码放在 `cloudfunctions/_shared/`，提供 `sync-shared.js` 脚本，在每次 `deploy` 前把 `_shared/*.js` 复制进每个函数目录的 `common/` 子目录，函数内 `require('./common/cbclient')`。优点：零平台特性依赖、部署产物自包含、diff 清晰；缺点：多一步同步。仓库已有 `cloudbase-cmd.json`、`cloudbase-init.js` 等脚本化运维先例，此方案与现有习惯一致。
2. 私有 npm 包方案：`npm publish` 到私有 registry，各函数 package.json 依赖。缺点：需要 registry 基础设施，对单人项目过重。
3. Web 函数单体方案：把全部逻辑合进 broadcast-a2a 这类 Web 函数。缺点：推翻现有 Event 函数划分，违反"不推翻架构基调"。

以下设计按方案 1 展开，模块文件置于 `cloudfunctions/_shared/`，同步后位于各函数的 `common/` 下。

---

## 三、总体分层与目录规划

```
cloudfunctions/
  _shared/                     # 单一事实源，deploy 前由脚本同步
    config.js                  # 环境解析 + 常量注册表（ENV_ID、各 fileID/cloudPath、阈值）
    errors.js                  # AppError + 错误码表 + 脱敏工具
    log.js                     # 结构化日志（JSON 单行，带 code/func/level 字段）
    cbclient.js                # CloudBase 单例 + download/upload 封装（只认 cloudPath，内部换算 fileID）
    httpx.js                   # HTTPS 请求封装（超时/重试/退避，从 requestHttps 升级）
    cache.js                   # 两级缓存（L1 内存 TTL / L2 云存储）+ single-flight
    quota.js                   # 基于 cache.js 的持久化计数器（供 generate-tts）
    compliance.js              # DKnowC 检查封装（从 fetch-tushare-data 抽出）
  functions/
    get-alerts/     （index.js + common/ 同步产物）
    fetch-tushare-data/
    generate-tts/
    broadcast-a2a/
    push-token-register/
    init-db/
  sync-shared.js               # 部署前置钩子
```

依赖方向严格单向：`函数 index.js → common/*`，`common/*` 之间允许 `config → errors → log → cbclient/cache/httpx` 这样自底向上引用，禁止反向。

---

## 四、模块设计一：共享 SDK 初始化（config.js + cbclient.js）

### 4.1 config.js——常量注册表，单一事实源

```js
// _shared/config.js
const ENV_ID = process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d';

// 存储路径注册表：全项目只在这里出现一次
const PATHS = {
  alerts: 'alerts/alerts.json',
  nameMap: 'stock-names/name-map.json',
  ttsCachePrefix: 'tts-cache/',
  ttsAudioPrefix: 'tts/',
};

// fileID 换算（cloud://envId.bucket序号/envId/cloudPath 的现有格式，
// 桶序号 6132-...-1475054847 来自现有三个函数中的硬编码，收敛于此）
const BUCKET_SUFFIX = '6132-' + ENV_ID + '-1475054847';
const toFileID = (cloudPath) => `cloud://${ENV_ID}.${BUCKET_SUFFIX}/${cloudPath}`;

module.exports = { ENV_ID, PATHS, toFileID,
  THRESHOLD: parseFloat(process.env.ALERT_THRESHOLD || '5.0'),
  TTS_MODEL: 'cosyvoice-v3-flash', TTS_VOICE: 'longxiaochun_v3',
};
```

要点：

- 密钥类变量（`TUSHARE_TOKEN`、`DASHSCOPE_API_KEY` 等）仍由各函数自读环境变量，**不进 config.js 的导出**，避免"一处引用链太长导致意外输出"。config 只管非敏感常量。
- `toFileID` 解决 1.2(c) 的不一致：统一"业务代码只写 cloudPath，fileID 换算收敛在一处"。现有 `get-alerts/index.js:21` 那串 `cloud://a2a-commonwealth-....-1475054847/alerts/alerts.json` 从三个文件变为一处生成。

### 4.2 cbclient.js——单例 + 存取封装

```js
// _shared/cbclient.js
const { ENV_ID, toFileID } = require('./config');
let _app = null;

function getApp() {
  if (!_app) {
    const cloudbase = require('@cloudbase/node-sdk');
    _app = cloudbase.init({ env: ENV_ID });   // 单例：对齐 fetch-tushare-data 的防连接泄漏实践
  }
  return _app;
}

async function readJson(cloudPath) {          // 统一只认 cloudPath
  const app = getApp();
  const result = await app.downloadFile({ fileID: toFileID(cloudPath) });
  if (!result || !result.fileContent) return null;
  return JSON.parse(result.fileContent.toString('utf-8'));
}

async function writeJson(cloudPath, obj) {
  const app = getApp();
  return app.uploadFile({
    cloudPath,
    fileContent: Buffer.from(JSON.stringify(obj), 'utf-8'),
  });
}

module.exports = { getApp, readJson, writeJson };
```

改造映射：`get-alerts/index.js:26-51` 的 `getLatestAlerts` 改为 `readJson(PATHS.alerts)` 后排序切片；`generate-tts/index.js:122-164` 的 `updateAlertAudioUrl` 改为 `readJson → 改字段 → writeJson`；`push-token-register` 的数据库操作保留 `getApp()` 直用（数据库 API 无需封装）。alerts.json 的"读-改-写"集中在 cbclient 之上再包一层 `withAlerts(mutator)`（见 6.4），这是消除并发覆盖的关键。

---

## 五、模块设计二：共享错误处理（errors.js + log.js + httpx.js）

### 5.1 错误码表

沿用"Tushare 40101"这种"来源前缀 + 数字"风格，全项目登记于 errors.js：

| 错误码 | 含义 | 处置策略（写在码表旁） |
|---|---|---|
| TUSHARE-40101 | token 失效/无权限 | 降级：名称映射走东财、交易日走星期推算（现状已实现的降级路径固化为码表语义） |
| TUSHARE-NET | 请求超时/网络失败 | 重试 1 次后仍失败则本轮放弃，退避由定时触发节奏天然承担 |
| DASHSCOPE-NOKEY | `DASHSCOPE_API_KEY` 未配置 | 直接跳过 TTS，返回 `{ success:false, error:'DASHSCOPE_API_KEY not configured' }`（保持 `generate-tts/index.js:352-354` 现有对外文案不变） |
| DASHSCOPE-TTS-FAIL | WebSocket 任务失败/超时 | 返回 null，端侧 audioUrl 留空，靠 audioUrl undefined 的既有端侧行为兜底 |
| TCB-READ-FAIL | alerts.json 缺失/解析失败 | 读端点返回空 items（保持 `get-alerts/index.js:47-50` 的"文件异常返回空数组"语义），写端点跳过本次写 |
| TCB-CONCURRENT | 检测到并发写入冲突 | 跳过写入（对应 `fetch-tushare-data/index.js:518-524` 现有保护） |
| DKNOWC-SKIP | 合规检查未配置/失败 | `safeType='Unknown', compliant=true, skipped=true`（保持 `fetch-tushare-data/index.js:405-407`、`:432-435` 的放行语义） |

### 5.2 errors.js——统一错误对象与脱敏

```js
// _shared/errors.js
const SENSITIVE = [process.env.TUSHARE_TOKEN, process.env.DASHSCOPE_API_KEY,
  process.env.HUAWEI_PUSH_CLIENT_SECRET].filter(Boolean);

function sanitize(msg) {            // 脱敏先于日志、先于返回，双保险
  let s = String(msg);
  for (const secret of SENSITIVE) if (secret) s = s.split(secret).join('***');
  return s;
}

class AppError extends Error {
  constructor(code, message, { cause, fatal = false } = {}) {
    super(sanitize(message));
    this.code = code; this.cause = cause; this.fatal = fatal;
  }
}
module.exports = { AppError, sanitize };
```

脱敏逻辑把 `fetch-tushare-data/index.js:108` 的局部实践（`replace(TUSHARE_TOKEN, '***')`）升级为全局规则：任何经过 AppError 或 log 的字符串都先过 `sanitize`。这直接服务"不泄露任何 Token/密钥"红线——尤其 `push-token-register/index.js:38`、`:50` 现在会把 token 前 20 位打进日志，虽是子串仍有聚集还原风险，改造后改为只打 `docId`。

### 5.3 log.js——结构化单行日志

```js
// _shared/log.js
const { sanitize } = require('./errors');
function log(level, code, msg, extra = {}) {
  console.log(JSON.stringify({ ts: Date.now(), level, code,
    msg: sanitize(msg), ...extra }));
}
module.exports = { info: (c, m, e) => log('info', c, m, e),
  warn: (c, m, e) => log('warn', c, m, e),
  error: (c, m, e) => log('error', c, m, e) };
```

所有 `console.log('get-alerts: ...')` 风格的自由文本（如 `get-alerts/index.js:48`、`generate-tts/index.js:272-273`）迁移为 `log.warn('TCB-READ-FAIL', e.message)`，控制台可按 `code` 字段直接过滤。

### 5.4 httpx.js——请求封装升级

以 `fetch-tushare-data/index.js:43-76` 的 `requestHttps` 为底，增加两点：① 显式 `options.retries`（默认 0，Tushare 调用配 1）；② 响应不强绑 JSON 解析（`raw` 模式供 Push Kit OAuth 等需要读非 JSON 错误体的场景，对齐 `broadcast-a2a/index.js:199-200` 现在要 `pushResp.text()` 的用法）。`broadcast-a2a` 的三处裸 `fetch`（`:60`、`:138`、`:186`）全部替换为 `httpx`，补上它现在缺失的超时控制。

### 5.5 统一返回信封

Event 函数对外返回统一为 `{ success, code?, error?, ...data }`。现有调用方兼容性核对：端侧 AlertPoller 走的是 HTTP 端点 `/alerts`，其响应体是 `{ items, serverTs }`（`get-alerts/index.js:65-68`），**该端点响应结构一个字段都不许加**（端侧 `AlertPoller.ets:69` 直接 `JSON.parse` 后取 `feed.items`，多余字段无害但为契约清晰起见不加）；`fetch-tushare-data → generate-tts` 的 callFunction 链路读取 `result.value.result.success/audioUrl`（`fetch-tushare-data/index.js:652-655`），信封变更时这两处同步核对。

---

## 六、模块设计三：共享缓存层抽象（cache.js）

### 6.1 两级缓存接口

```js
// _shared/cache.js
const { readJson, writeJson } = require('./cbclient');
const memory = new Map();              // key -> { value, expireAt }

function memGet(key) {
  const hit = memory.get(key);
  if (hit && hit.expireAt > Date.now()) return hit.value;
  memory.delete(key);
  return null;
}

async function get(key, { ttlMs, loader, l2Path, singleFlight = true }) {
  // L1 内存
  const m = memGet(key); if (m !== null) return { value: m, src: 'l1' };
  // single-flight：同 key 并发 miss 只放一个 loader
  if (singleFlight) {
    if (inflight.has(key)) return { value: await inflight.get(key), src: 'flight' };
    inflight.set(key, (async () => {
      // L2 云存储（存的是 { value, updatedAt } 包裹层）
      if (l2Path) {
        try {
          const wrapped = await readJson(l2Path);
          if (wrapped && wrapped.value !== undefined &&
              Date.now() - new Date(wrapped.updatedAt).getTime() < ttlMs) {
            memory.set(key, { value: wrapped.value, expireAt: Date.now() + ttlMs });
            return wrapped.value;
          }
          if (wrapped && wrapped.value !== undefined) {
            memory.set(key, { value: wrapped.value, expireAt: Date.now() + ttlMs }); // 过期仍作降级预备
          }
        } catch (e) { /* 缓存不存在是常态 */ }
      }
      const fresh = await loader();
      if (fresh !== null && l2Path) {
        try { await writeJson(l2Path, { value: fresh, updatedAt: new Date().toISOString() }); } catch (e) {}
      }
      memory.set(key, { value: fresh, expireAt: Date.now() + ttlMs });
      return fresh;
    })());
    try { return { value: await inflight.get(key), src: 'loader' }; }
    finally { inflight.delete(key); }
  }
}
const inflight = new Map();
module.exports = { get };
```

### 6.2 三处现有缓存归一后的形态

| 现状 | 归一后 |
|---|---|
| name-map 五级降级（`fetch-tushare-data/index.js:123-272`） | `cache.get('name-map', { ttlMs: 86400000, l2Path: PATHS.nameMap, loader: loadFromEastMoney })`；"过期仍作降级预备"对应现在 `:150-155` 的 stale-fallback 语义；硬编码 `hardcoded-names.js` 作为 loader 内部最后一层保留 |
| 交易日缓存（`:278-339`） | `cache.get('trade-date', { ttlMs: 3600000, loader: queryTradeCal })`；星期推算作为 loader 内部兜底 |
| TTS 音频缓存（`generate-tts/index.js:72-116`） | `l2Path: PATHS.ttsCachePrefix + cacheKey + '.json'`，包裹层携带 `{ audioUrl, text, voice, model, createdAt }`，命中语义不变；顺带把 `checkCache`/`saveCache` 两函数删除 |

收益举例：name-map 现在每次 miss 都会串行跑 4 个市场 × 最多 20 页的东财抓取（`:169-204`），若两条信号同时触发两个函数实例，就是双倍外呼；single-flight + L2 命中后，冷启动抖动期的重复抓取消失。

### 6.3 quota.js——持久化计数器

`generate-tts/index.js:28-51` 的内存 QUOTA 改为：`quota.recordUsage(n)` 读改写 L2 文件 `tts-cache/_quota.json`（低频写，每次 TTS 成功才写一次），`shouldStop()` 读 L2。冷启动不丢计数，预警线（0.8）与停机线（1.0）语义不变。注意写放大可控：单机每天 TTS 调用量级为个位数到十位数（每次最多 10 条信号卡，`fetch-tushare-data/index.js:595`），完全可接受。

### 6.4 alerts.json 的读改写与并发保护

现状：`fetch-tushare-data/index.js:497-558` 写入前用 `existingServerTs > currentLatestTs` 判断跳过（`:518-524`），`generate-tts/index.js:122-164` 更新 audioUrl 时却**没有**这层保护，两个函数同时读改写 alerts.json 存在互相覆盖窗口。归一方案：cbclient 之上提供

```js
async function withAlerts(mutator) {
  const data = await readJson(PATHS.alerts) || { items: [], serverTs: 0 };
  const baseServerTs = data.serverTs || 0;
  const next = mutator(data);            // 返回 null 表示放弃写入
  if (!next) return { skipped: true };
  const cur = await readJson(PATHS.alerts);
  if (cur && (cur.serverTs || 0) > baseServerTs) return { skipped: true, reason: 'TCB-CONCURRENT' };
  next.serverTs = Math.floor(Date.now() / 1000);
  await writeJson(PATHS.alerts, next);
  return { skipped: false };
}
```

写前重读比对 serverTs 是在"对象存储没有原子 CAS"这一现实下能做到的最强乐观并发控制，与现有 `:518-524` 思路一致，推广到 audioUrl 更新路径。残余竞态（重读后、写前仍有人写）如实承认：概率窗口极小，且后果是 audioUrl 或一条旧异动被回退，端侧下次轮询会被 fetch-tushare-data 的定时触发自愈，不升级为强一致方案（那需要换数据库，违反约束）。

---

## 七、各函数接入改造清单

| 函数 | 改造点 | 引用现状 |
|---|---|---|
| get-alerts | `readJson(PATHS.alerts)` 替代内联 init+downloadFile；错误走 log/error 码表；顺手修正 ：16 注释端点 typo | `get-alerts/index.js:19,21,28-29,47-50` |
| fetch-tushare-data | 删除自建 `requestHttps`/单例/常量，换 `httpx/cbclient/cache`；name-map 与 trade-date 走 cache.get；`downloadFile({cloudPath})` 疑似误用随封装一并消除；写库走 `withAlerts` | `:28-37,43-76,79-86,123-272,497-558` |
| generate-tts | 删除 `getCloudBaseApp/checkCache/saveCache`，走 cache + withAlerts；QUOTA 换 quota.js；WS 错误改抛 AppError 码 | `:24-25,28-51,63-66,72-116,122-164` |
| broadcast-a2a | 两处内联 init 换 cbclient；三处裸 fetch 换 httpx（补超时）；Push Kit REST 逻辑保持不动（华为 REST 实现已就位于 `:106-204`，只等 AGC 凭证环境变量） | `:29-30,60,107-109,119-120,138,186` |
| push-token-register | init 换 cbclient；日志不再打 token 子串 | `:22-23,38,50,59-60` |
| init-db | 常量换 config；集合清单维持不变 | 顶部 ENV_ID 行 |

改造验收清单（每项都可机器或人工验证）：① 六个函数文件中 `cloudbase.init` 出现次数为 0（只剩 cbclient 一处）；② `a2a-commonwealth` 字符串在 functions/ 下出现次数为 0（只剩 config.js）；③ 全量日志中 `***` 替换生效、无 token 原文；④ 端侧联调：AlertPoller 5s 轮询返回结构不变、generate-tts 缓存命中返回 `cached:true`；⑤ 断网/坏 fileID 注入测试：读端点返回空 items 而非 500。

---

## 八、与端侧契约的边界（重申不动项）

1. `AlertFeed { items, serverTs }` 与 `AlertItem` 字段（`entry/src/main/ets/model/AlertItem.ets:6-22`）不变；
2. `/alerts` HTTP 端点路径与响应结构不变，端侧 `SettingsService.getFeedUrl` 的默认值（`SettingsService.ets:351-361`）继续可用；
3. `push-token-register` 的入参 `{ token, bundleName }` 不变（端侧 `PushService.ets:80-86` 按 POST JSON 上报）；
4. TTS 音频的云端地址生成方式不变。**已知风险迁移说明**：`generate-tts/index.js:321-325` 现在把 `getTempFileURL` 的临时链接写进 alerts.json，临时链接过期后端侧播放会失败——这是 A25（AudioPlayer 审查）与 A24（契约审查）的议题，基础设施层不擅自改链接策略，只在 `uploadToStorage` 处留 TODO 注释位，待"持久下载 URL 或端侧按需调 generate-tts"决策后一并改。

## 九、实施步骤与风险

**步骤**：① 建 `_shared/` 与 `sync-shared.js`，先迁 config + cbclient（风险最低、收益最直接）；② 迁 errors + log；③ 迁 cache 并逐函数切换（每切换一个函数跑一次手动触发验证）；④ 最后切 httpx 与 compliance。全程可按函数灰度，任一函数出问题可单独回滚该函数目录。

**风险如实声明**：本方案为设计文档，文中代码未经运行验证（本任务环境无法部署 CloudBase 与真机联调）；1.2(c) 的 `downloadFile({cloudPath})` 误用判断与 6.4 的并发窗口分析均基于源码阅读推断，实施前应在测试环境以坏数据注入实测。同步脚本方案引入"忘记 sync 就部署旧共享层"的人为风险，对策是在部署说明中把 `node sync-shared.js` 写成部署命令链条的第一步。

### 自我评估
- 正确性：4分 全部现状论断均给出文件行号证据；疑点（downloadFile cloudPath 形态、并发残余窗口）明确标注"需实测"而非断言；共享层代码为设计稿未运行，扣一分。
- 完整性：4分 覆盖三大主题（SDK初始化/错误处理/缓存）+ 共享方式选型 + 逐函数清单 + 验收与风险；未展开 CI 流水线与权限最小化等外围议题。
- 可复用性：5分 模块接口、码表、改造映射表、验收清单均可直接作为实施工单使用，且不依赖对话上下文。
- 字数：约5100字
- 使用模型：GLM-5.3-Flash
