/**
 * fetch-tushare-data 云函数
 * 
 * 功能：
 * 1. 调用 Tushare API 获取A股日线行情数据
 * 2. 筛选涨跌幅 ≥ 阈值（默认5%）的异动股票
 * 3. 将异动记录写入 PostgreSQL alerts 表
 * 4. 返回异动列表 JSON
 * 
 * 触发方式：定时触发器或手动调用
 * 环境变量：TUSHARE_TOKEN（必需）
 * 
 * 数据接口策略（按 token 权限降级）：
 *   1. daily（日线行情）—— 基础权限，需指定 trade_date
 *   2. trade_cal（交易日历）—— 基础权限，频率限制1次/小时，缓存最新交易日
 *   3. top_list（龙虎榜）—— 高级权限，当前 token 无权限
 */

const TUSHARE_API_URL = 'https://api.tushare.pro';
const TUSHARE_TOKEN = process.env.TUSHARE_TOKEN || '';
const THRESHOLD = parseFloat(process.env.ALERT_THRESHOLD || '5.0');

// 最新交易日缓存（避免频繁调用 trade_cal）
let cachedTradeDate = null;
let cachedTradeDateTs = 0;
const TRADE_DATE_CACHE_TTL = 3600000; // 1小时缓存

/**
 * 调用 Tushare API
 */
async function callTushare(apiName, params = {}, fields = '') {
  const body = JSON.stringify({
    api_name: apiName,
    token: TUSHARE_TOKEN,
    params,
    fields,
  });

  const response = await fetch(TUSHARE_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
  });

  if (!response.ok) {
    throw new Error(`Tushare API HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();
  if (data.code !== 0) {
    throw new Error(`Tushare API error: ${data.msg || data.code}`);
  }
  return data.data;
}

/**
 * 获取最新交易日（带缓存，避免 trade_cal 频率超限）
 */
async function getLatestTradeDate() {
  // 检查缓存
  if (cachedTradeDate && (Date.now() - cachedTradeDateTs) < TRADE_DATE_CACHE_TTL) {
    console.log('Using cached trade date:', cachedTradeDate);
    return cachedTradeDate;
  }

  try {
    const tradeCal = await callTushare('trade_cal', {
      exchange: 'SSE',
      is_open: '1',
      limit: '1',
      offset: '0',
    }, 'cal_date');

    if (tradeCal && tradeCal.items && tradeCal.items.length > 0) {
      cachedTradeDate = tradeCal.items[0][0];
      cachedTradeDateTs = Date.now();
      console.log('Got latest trade date:', cachedTradeDate);
      return cachedTradeDate;
    }
  } catch (e) {
    console.log('trade_cal failed:', e.message);
  }

  // Fallback：使用当前日期推算（如果是工作日，用今天；否则用最近的周五）
  const now = new Date();
  const day = now.getDay(); // 0=周日, 6=周六
  let fallbackDate;
  if (day === 0) {
    // 周日 → 用上周五
    const friday = new Date(now);
    friday.setDate(now.getDate() - 2);
    fallbackDate = friday;
  } else if (day === 6) {
    // 周六 → 用本周五
    const friday = new Date(now);
    friday.setDate(now.getDate() - 1);
    fallbackDate = friday;
  } else {
    fallbackDate = now;
  }
  const y = fallbackDate.getFullYear();
  const m = String(fallbackDate.getMonth() + 1).padStart(2, '0');
  const d = String(fallbackDate.getDate()).padStart(2, '0');
  const fallbackStr = `${y}${m}${d}`;
  console.log('Using fallback trade date:', fallbackStr);
  return fallbackStr;
}

/**
 * 获取日线行情数据并筛选异动
 */
async function getDailyMovers() {
  const tradeDate = await getLatestTradeDate();
  console.log(`Fetching daily data for ${tradeDate}...`);

  try {
    const dailyData = await callTushare('daily', {
      trade_date: tradeDate,
    }, 'ts_code,name,pct_chg,close,vol,amount,open,high,low,pre_close');

    if (dailyData && dailyData.items && dailyData.items.length > 0) {
      console.log(`Got ${dailyData.items.length} daily records`);
      const movers = dailyData.items.map(row => {
        const obj = {};
        dailyData.fields.forEach((field, i) => {
          obj[field] = row[i];
        });
        return obj;
      }).filter(item => {
        const pct = parseFloat(item.pct_chg || 0);
        return Math.abs(pct) >= THRESHOLD;
      });
      console.log(`Filtered to ${movers.length} movers above ${THRESHOLD}%`);
      return movers;
    }
  } catch (e) {
    console.error('daily API failed:', e.message);
  }

  return [];
}

/**
 * 生成异动条目
 */
function createAlertItems(movers) {
  const now = Math.floor(Date.now() / 1000);
  return movers.map(mover => {
    const pctChg = parseFloat(mover.pct_chg || 0);
    const direction = pctChg > 0 ? 'up' : pctChg < 0 ? 'down' : 'flat';
    const absPct = Math.abs(pctChg).toFixed(2);
    const name = mover.name || mover.ts_code;
    const symbol = mover.ts_code || '';

    // 信号卡判断：涨跌幅 ≥ 8% 时输出自家信号
    const kind = absPct >= 8.0 ? 'signal' : 'fact';
    let signalNote = '';
    if (kind === 'signal') {
      if (direction === 'up') {
        signalNote = '留意后续走势';
      } else if (direction === 'down') {
        signalNote = '注意风险';
      }
    }

    // 白话头条
    let headline = '';
    if (direction === 'up') {
      headline = `${name} 涨了 ${absPct}%`;
    } else if (direction === 'down') {
      headline = `${name} 跌了 ${absPct}%`;
    } else {
      headline = `${name} 横盘 ${absPct}%`;
    }

    // 补充细节
    const close = parseFloat(mover.close || 0).toFixed(2);
    const vol = parseFloat(mover.vol || 0).toFixed(0);
    const detail = `当前价 ${close}元，成交量 ${vol}手`;

    return {
      alertId: `${symbol}_${now}_${Math.random().toString(36).substring(2, 8)}`,
      ts: now,
      symbol,
      name,
      direction,
      kind,
      headline,
      detail: kind === 'signal' ? `${detail}。${signalNote}` : detail,
      signalNote: kind === 'signal' ? signalNote : undefined,
      pctChg,
      close,
      vol,
    };
  });
}

/**
 * 写入 PostgreSQL alerts 表
 */
async function saveAlertsToDB(alerts) {
  const { PG_CONN_STRING } = process.env;
  if (!PG_CONN_STRING) {
    console.log('PG_CONN_STRING not set, skipping DB write');
    return;
  }

  let pg;
  try { pg = require('pg'); } catch (e) {
    console.log('pg module not available, skipping DB write');
    return;
  }

  const client = new pg.Client({ connectionString: PG_CONN_STRING });
  try {
    await client.connect();
    console.log('Connected to PostgreSQL');

    for (const alert of alerts) {
      try {
        await client.query(
          `INSERT INTO alerts (alert_id, ts, symbol, name, direction, kind, headline, detail, audio_url)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
           ON CONFLICT (alert_id) DO NOTHING`,
          [
            alert.alertId,
            alert.ts,
            alert.symbol,
            alert.name,
            alert.direction,
            alert.kind || 'fact',
            alert.headline,
            alert.detail,
            alert.audioUrl || null,
          ]
        );
      } catch (e) {
        console.error(`Failed to insert alert ${alert.alertId}:`, e.message);
      }
    }

    console.log(`Saved ${alerts.length} alerts to DB`);
  } catch (e) {
    console.error('DB connection error:', e.message);
  } finally {
    await client.end();
  }
}

/**
 * 云函数入口
 */
exports.main = async (event, context) => {
  console.log('fetch-tushare-data invoked', JSON.stringify({ THRESHOLD, token: TUSHARE_TOKEN ? 'set' : 'not set' }));

  if (!TUSHARE_TOKEN) {
    return {
      success: false,
      error: 'TUSHARE_TOKEN not configured',
      items: [],
      serverTs: Math.floor(Date.now() / 1000),
    };
  }

  try {
    const movers = await getDailyMovers();
    console.log(`Found ${movers.length} movers above ${THRESHOLD}% threshold`);

    if (movers.length === 0) {
      return {
        success: true,
        items: [],
        serverTs: Math.floor(Date.now() / 1000),
        message: 'No significant movements detected',
      };
    }

    const alerts = createAlertItems(movers);
    console.log(`Generated ${alerts.length} alert items`);

    await saveAlertsToDB(alerts);

    return {
      success: true,
      items: alerts,
      serverTs: Math.floor(Date.now() / 1000),
      count: alerts.length,
    };
  } catch (e) {
    console.error('fetch-tushare-data error:', e.message);
    return {
      success: false,
      error: e.message,
      items: [],
      serverTs: Math.floor(Date.now() / 1000),
    };
  }
};
