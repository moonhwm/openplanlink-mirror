# diag技能：Tushare token失效诊断

> 编写时间：2026-09-23
> 编写席位：砚坚（CodeArts GLM-5.2-sft-harmony）
> 适用场景：fetch-tushare-data云函数中Tushare API调用失败的诊断与降级

## 1. 症状识别

### 40101错误

```json
{"code": 40101, "msg": "token无效或已过期"}
```

### 其他常见错误码

| 错误码 | 含义 | 处理方式 |
|--------|------|---------|
| 40101 | token无效/过期 | 切换到东方财富API降级 |
| 40201 | 频率超限 | 等待并重试，增加缓存TTL |
| 40203 | 权限不足 | 降级到基础权限接口 |
| 50000 | 系统错误 | 重试3次后放弃 |

## 2. 诊断流程

```
1. 检查TUSHARE_TOKEN环境变量是否配置
   → 未配置 → 返回错误"TUSHARE_TOKEN not configured"
   → 已配置 → 继续

2. 调用callTushare('daily', ...)
   → 成功 → 正常流程
   → 40101错误 → token失效，切换降级源
   → 40201错误 → 频率超限，增加缓存
   → 超时 → requestHttps 15s超时，检查网络

3. 降级到东方财富API
   → 东方财富行情API获取涨跌幅数据
   → 东方财富名称映射API获取股票名称

4. 最终降级
   → DEMO_ITEMS演示数据（首屏永不空白）
```

## 3. 东方财富API降级方案

### 行情数据替代

东方财富行情API可替代Tushare daily接口：
```
https://80.push2.eastmoney.com/api/qt/clist/get
参数：pn(页码)、pz(每页数量)、fs(市场过滤)、fields(字段)
```

### 名称映射替代

已在fetch-tushare-data中实现完整的6层降级链：
```
内存缓存 → CloudBase存储 → 东方财富API → 过期存储 → 硬编码5560条 → 空 Map
```

### 东方财富API优势

- 无频率限制（Tushare trade_cal限1次/小时）
- 无需token
- 数据实时性好
- 支持分页获取全市场数据

### 东方财富API劣势

- 返回格式与Tushare不同（需要字段映射）
- 股票代码格式不同（需要SH/SZ/BJ后缀转换）
- 无交易日历接口（需要自行推算）

## 4. 代码层面防护

### callTushare中的错误处理

```javascript
async function callTushare(apiName, params = {}, fields = '') {
  const data = await requestHttps(TUSHARE_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_name: apiName, token: TUSHARE_TOKEN, params, fields }),
    timeout: 15000,
  });

  if (data.code !== 0) {
    const safeMsg = (data.msg || '').replace(TUSHARE_TOKEN, '***');
    throw new Error(`Tushare API error: ${safeMsg || data.code}`);
  }
  return data.data;
}
```

### getDailyMovers中的降级

```javascript
const [dailyResult, nameMap] = await Promise.all([
  callTushare('daily', { trade_date: tradeDate }, fields).catch(e => {
    console.error('daily API failed:', e.message);
    return null;  // 不阻塞nameMap获取
  }),
  getStockNameMap(),
]);

if (dailyResult && dailyResult.items && dailyResult.items.length > 0) {
  // 正常处理
} else {
  return [];  // 降级返回空数组
}
```

## 5. 验证清单

- [ ] TUSHARE_TOKEN环境变量已配置
- [ ] callTushare超时设置为15秒
- [ ] error message中token已脱敏
- [ ] daily API失败后返回null不阻塞nameMap
- [ ] 东方财富API作为名称映射降级源已实现
- [ ] 硬编码5560条名称映射fallback已存在
- [ ] DEMO_ITEMS演示数据确保首屏永不空白

---

*本技能文档由砚坚席位于2026-09-23编写，基于Tushare token失效(40101)后的降级实战经验提炼。*