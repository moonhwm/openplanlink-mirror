# code技能：ArkTS云函数开发模式

> 编写时间：2026-09-23
> 编写席位：砚坚（CodeArts GLM-5.2-sft-harmony）
> 适用场景：harmony-app项目中所有CloudBase云函数的开发与维护

## 1. requestHttps统一封装规范

### 问题背景
Node.js 18.15的实验性`fetch`存在已知缺陷（如name字段返回代码而非名称），云函数中不应使用`fetch`。应统一使用`https`模块封装的`requestHttps`。

### 标准封装代码

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
    req.on('error', reject);
    req.setTimeout(options.timeout || 15000, () => {
      req.destroy(new Error('Request timeout'));
    });
    if (options.body) req.write(options.body);
    req.end();
  });
}
```

### 带重试的版本

```javascript
async function requestHttpsRetry(url, options = {}, maxRetries = 2) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await requestHttps(url, options);
    } catch (e) {
      if (attempt === maxRetries) throw e;
      const delay = 500 * Math.pow(2, attempt);
      await new Promise(r => setTimeout(r, delay));
    }
  }
}
```

### 使用规则
- **禁止**在云函数中使用`fetch()`（实验性API）
- **必须**使用`requestHttps`或`requestHttpsRetry`发起所有HTTPS请求
- **必须**为每个请求设置`timeout`（默认15秒）
- **推荐**对外部API调用使用`requestHttpsRetry`（最多2次重试，指数退避）

## 2. CloudBase SDK单例模式

### 问题背景
`cloudbase.init()`每次调用都创建新的SDK实例，消耗资源且可能导致连接泄漏。在单个云函数中多处调用`init`会造成严重的性能问题。

### 标准单例代码

```javascript
let _cloudbaseApp = null;
function getCloudbaseApp() {
  if (!_cloudbaseApp) {
    const cloudbase = require('@cloudbase/node-sdk');
    _cloudbaseApp = cloudbase.init({
      env: process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d',
    });
  }
  return _cloudbaseApp;
}
```

### 使用规则
- **禁止**在函数体内直接调用`cloudbase.init()`
- **必须**通过`getCloudbaseApp()`获取SDK实例
- **每个云函数**都需要自己的`getCloudbaseApp()`定义（云函数间不共享模块作用域）

## 3. 错误降级链设计

### 设计原则
云函数中的每个外部依赖都可能失败，必须设计多层降级链确保核心功能可用。

### 降级链模板

```
主数据源 → 降级源1 → 降级源2 → 硬编码fallback → 空值兜底
```

### fetch-tushare-data中的降级链实例

```
股票名称映射降级链：
内存缓存(24h TTL) → CloudBase存储缓存(24h TTL) → 东方财富API → 过期存储缓存 → 硬编码5560条 → 空 Map

交易日降级链：
内存缓存(1h TTL) → Tushare trade_cal API → 当前日期推算(工作日/最近周五)

数据源降级链：
Tushare daily API → 东方财富行情API（待实现）→ DEMO_ITEMS演示数据
```

### 降级链设计规则
1. 每层降级必须**不阻塞**后续尝试（失败后继续尝试下一层）
2. 每层降级必须有**独立的try-catch**
3. 降级到硬编码数据时必须**日志标注**（`console.log('Using hardcoded fallback')`）
4. 最终兜底必须返回**有效空值**（空数组/空Map），不能返回null/undefined

## 4. 并发写入保护

### 问题背景
多个云函数实例可能同时写入同一个CloudBase存储文件（如alerts.json），导致数据覆盖。

### 标准保护代码

```javascript
// 检查 serverTs：如果现有数据比当前数据更新，跳过写入
const currentLatestTs = alerts.length > 0 ? Math.max(...alerts.map(a => a.ts)) : 0;
if (existingServerTs > currentLatestTs) {
  console.log(`Skip write: existing serverTs=${existingServerTs} > current latestTs=${currentLatestTs}`);
  return;
}
```

### 去重合并策略

```javascript
// 按 alertId 去重合并
const alertMap = new Map();
for (const item of existingItems) {
  alertMap.set(item.alertId, item);
}
for (const alert of alerts) {
  alertMap.set(alert.alertId, alert); // 新数据覆盖同ID旧数据
}
// 保留最新500条
const allItems = Array.from(alertMap.values())
  .sort((a, b) => b.ts - a.ts)
  .slice(0, 500);
```

## 5. 确定性ID生成

### 问题背景
使用`Math.random()`生成ID有碰撞风险，在去重场景中可能导致数据丢失。

### 标准方案

```javascript
// 确定性alertId：同一股票同一秒只生成一条alert
alertId: `${symbol}_${now}`,
```

### 规则
- ID必须由**业务关键字段**组合生成（symbol + timestamp）
- **禁止**使用`Math.random()`作为ID组成部分
- ID格式应**人类可读**，便于调试

---

*本技能文档由砚坚席位于2026-09-23编写，基于fetch-tushare-data云函数的P0/P1修复实战经验提炼。*