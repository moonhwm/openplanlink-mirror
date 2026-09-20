/**
 * fetch-tushare-data 云函数
 * 
 * 功能：
 * 1. 调用 Tushare API 获取A股实时行情数据
 * 2. 筛选涨跌幅 ≥ 阈值（默认5%）的异动股票
 * 3. 将异动记录写入 PostgreSQL alerts 表
 * 4. 返回异动列表 JSON
 * 
 * 触发方式：定时触发器（每30秒）或手动调用
 * 环境变量：TUSHARE_TOKEN（必需）
 */

// Tushare API 配置
const TUSHARE_API_URL = 'https://api.tushare.pro';
const TUSHARE_TOKEN = process.env.TUSHARE_TOKEN || 'c5e307a634ff8e29575c557e51d41299';
const THRESHOLD = parseFloat(process.env.ALERT_THRESHOLD || '5.0'); // 涨跌幅阈值(%)
const BATCH_SIZE = parseInt(process.env.BATCH_SIZE || '50', 10); // 每批查询股票数

// CloudBase PostgreSQL 连接（云函数环境中自动注入）
const { PG_CONN_STRING } = process.env;

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
 * 获取实时行情（涨跌幅排名）
 * 使用 ts5 接口获取5分钟涨跌幅排名
 */
async function getRealtimeQuotes() {
  // 实时行情 - 涨跌幅排名前100
  const data = await callTushare('realtime_quote', {
    ts_code: '', // 空表示全部
    trade_date: '', // 空表示最新
  }, 'ts_code,name,price,pct_chg,vol,amount,open,high,low,pre_close');

  if (!data || !data.items || data.items.length === 0) {
    console.log('No realtime data returned');
    return [];
  }

  // data.items 是数组，每个元素是 [ts_code, name, price, pct_chg, vol, amount, open, high, low, pre_close]
  const items = data.items.map(row => {
    const obj = {};
    data.fields.forEach((field, i) => {
      obj[field] = row[i];
    });
    return obj;
  });

  return items;
}

/**
 * 获取涨跌幅排名（使用 daily_basic + top_list）
 */
async function getTopMovers() {
  // 获取今日涨跌幅排名
  try {
    // 方案1: 使用 top_list 获取龙虎榜（涨跌幅异常的股票）
    const topData = await callTushare('top_list', {
      trade_date: '', // 最新交易日
    }, 'ts_code,name,pct_chg,close,amount');

    if (topData && topData.items && topData.items.length > 0) {
      return topData.items.map(row => {
        const obj = {};
        topData.fields.forEach((field, i) => {
          obj[field] = row[i];
        });
        return obj;
      }).filter(item => Math.abs(parseFloat(item.pct_chg || 0)) >= THRESHOLD);
    }
  } catch (e) {
    console.log('top_list failed, trying daily_basic:', e.message);
  }

  // 方案2: 使用 daily_basic 获取每日指标（需要指定交易日）
  try {
    // 先获取最新交易日
    const tradeCal = await callTushare('trade_cal', {
      exchange: 'SSE',
      is_open: '1',
      limit: '1',
      offset: '0',
    }, 'cal_date');

    if (tradeCal && tradeCal.items && tradeCal.items.length > 0) {
      const latestDate = tradeCal.items[0][0]; // cal_date
      console.log('Latest trade date:', latestDate);

      const dailyData = await callTushare('daily', {
        trade_date: latestDate,
      }, 'ts_code,name,pct_chg,close,vol,amount,open,high,low,pre_close');

      if (dailyData && dailyData.items) {
        return dailyData.items.map(row => {
          const obj = {};
          dailyData.fields.forEach((field, i) => {
            obj[field] = row[i];
          });
          return obj;
        }).filter(item => Math.abs(parseFloat(item.pct_chg || 0)) >= THRESHOLD);
      }
    }
  } catch (e) {
    console.log('daily approach failed:', e.message);
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
  if (!PG_CONN_STRING) {
    console.log('PG_CONN_STRING not set, skipping DB write');
    return;
  }

  // 使用 pg 模块连接 PostgreSQL
  // 在云函数环境中，CloudBase 会自动注入 PG_CONN_STRING
  let pg;
  try {
    pg = require('pg');
  } catch (e) {
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
  console.log('fetch-tushare-data invoked', JSON.stringify({ event, THRESHOLD }));

  try {
    // 获取异动股票
    const movers = await getTopMovers();
    console.log(`Found ${movers.length} movers above ${THRESHOLD}% threshold`);

    if (movers.length === 0) {
      return {
        success: true,
        items: [],
        serverTs: Math.floor(Date.now() / 1000),
        message: 'No significant movements detected',
      };
    }

    // 生成异动条目
    const alerts = createAlertItems(movers);
    console.log(`Generated ${alerts.length} alert items`);

    // 写入数据库
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