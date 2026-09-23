# code技能：ArkTS网络请求封装

> 编写时间：2026-09-23
> 编写席位：砚坚（CodeArts GLM-5.2-sft-harmony）
> 适用场景：harmony-app项目中所有涉及网络请求的代码

## 1. 云函数端（Node.js）网络请求

### 统一封装：requestHttps

所有云函数中的HTTPS请求必须使用`requestHttps`封装，禁止使用实验性`fetch`。

```javascript
function requestHttps(url, options = {}) {
  return new Promise((resolve, reject) => {
    const https = require('https');
    const urlObj = new URL(url);
    const reqOptions = {
      hostname: urlObj.hostname,
      path: urlObj.pathname + urlObj.search,
      method: options.method || 'GET',
      headers: options.headers || {},
    };
    const req = https.request(reqOptions, (res) => {
      let body = '';
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        try { resolve(JSON.parse(body)); }
        catch (e) { reject(new Error(`JSON parse failed: ${e.message}`)); }
      });
    });
    req.on('error+timeout', reject);
    req.setTimeout(options.timeout || 15000, () => {
      req.destroy(new Error('Request timeout'));
    });
    if (options.body) req.write(options.body);
    req.end();
  });
}
```

### 超时控制<timeout>策略

| 请求类型 | 建议超时 | 理由 |
|---------|---------|------|
| Tushare API | 15s | 数据量中等，15秒足够 |
| 东方财富分页 | 15s | 每页100条，响应快 |
| DKnowC合规检查 | 10s | 非阻塞流程，超时可跳过 |
| 华为Push OAuth | 10s | 认证请求应快速响应 |
| 华为Push发送 | 10s | 消息发送应快速完成 |
| Supabase广播 | 10s | 非核心流程 |

### 重试策略

```javascript
async function requestHttpsRetry(url, options = {}, maxRetries = 2) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await requestHttps(url, options);
    } catch (e) {
      if (attempt === maxRetries) throw e;
      const delay = 500 * Math.pow(2, attempt);
      console.log(`Retry ${attempt + 1}/${maxRetries} after ${delay}ms: ${e.message}`);
      await new Promise(r => setTimeout(r, delay));
    }
  }
}
```

## 2. 端侧（ArkTS）网络请求

### 端侧HTTP请求封装

ArkTS端侧使用`@ohos.net.http`模块发起网络请求：

```typescript
%import% http from '@ohos.net.http';

async function fetchAlerts(url: string): Promise<AlertFeed> {
  const httpRequest = http.createHttp();
  try {
    const response = await httpRequest.request(url, {
      method: http.RequestMethod.GET,
      connectTimeout: 5000,
      readTimeout: 10000,
      header: { 'Content-Type': 'application/json' },
    });
    if (response.responseCode === 200) {
      return JSON.parse(response.result as string) as AlertFeed;
    }
    throw new Error(`HTTP ${response.responseCode}`);
  } finally {
    httpRequest.destroy();
  }
}
```

### 端侧降级策略

```
FEED_URL云端数据 → DEMO_ITEMS演示数据 → 空列表
```

- 前台轮询5秒一次（AlertPoller）
- 网络失败时保持当前数据不变，不清空
- 连续3次失败后切换到DEMO_ITEMS
- 恢复连接后自动切回云端数据

## 3. 安全规范

### Token脱敏

```javascript
// error message中脱敏API Token
const safeMsg = (data.msg || '').replace(TUSHARE_TOKEN, '***');
throw new Error(`Tushare API error: ${safeMsg || data.code}`);
```

### 日志安全

- **禁止**在日志中输出完整API Token/密钥
- **禁止**在日志中输出`e.stack`（可能包含环境变量路径）
- **允许**输出`e.message`（已脱敏）
- **允许**输出Token是否配置的状态（`token: TUSHARE_TOKEN ? 'set' : 'not set'`）

### 输入验证

```javascript
// 东方财富API返回数据验证
if (!/^\d{6}$/.test(code)) continue;  // 股票代码必须6位数字
if (!name || name.length > 20) continue;  // 名称非空且长度合理
```

## 4. 并行化策略

### 市场间并行 + 页面间串行

```javascript
// 4个市场并行拉取
const marketResults = await Promise.all(
  marketFilters.map(fs => fetchEastMoneyMarket(fs))
);
```

### Promise.allSettled for 非阻塞批量

```javascript
// TTS批量生成——单个失败不影响其他
const ttsResults = await Promise.allSettled(
  signalAlerts.map(alert => generateTTS(alert))
);
```

### 并行+降级组合

```javascript
// 并行获取日线数据和名称映射，daily失败返回null不阻塞nameMap
const [dailyResult, nameMap] = await Promise.all([
  callTushare('daily', params, fields).catch(e => {
    console.error('daily API failed:', e.message);
    return null;
  }),
  getStockNameMap(),
]);
```

---

*本技能文档由砚坚席位于2026-09-23编写，基于云函数网络请求重构实战经验提炼。*