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

// DKnowC 深知可信统一API配置（内容安全合规层）
const DKNOWC_API_KEY = process.env.DKNOWC_API_KEY || '';
const DKNOWC_API_URL = 'https://open.dknowc.cn/chat/trusted/unification';

/**
 * 使用 https 模块发起 GET 请求（替代实验性 fetch）
 */
function fetchHttps(url) {
  return new Promise((resolve, reject) => {
    const https = require('https');
    const req = https.get(url, (res) => {
      let body = '';
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        try {
          resolve(JSON.parse(body));
        } catch (e) {
          reject(new Error(`JSON parse failed: ${e.message}, body length: ${body.length}`));
        }
      });
    });
    req.on('error', reject);
    req.setTimeout(15000, () => {
      req.destroy(new Error('Request timeout'));
    });
  });
}

// 最新交易日缓存（避免频繁调用 trade_cal）
let cachedTradeDate = null;
let cachedTradeDateTs = 0;
const TRADE_DATE_CACHE_TTL = 3600000; // 1小时缓存

// 股票名称映射缓存（ts_code → 中文名称）
let cachedNameMap = null;
let cachedNameMapTs = 0;
const NAME_MAP_CACHE_TTL = 86400000; // 24小时缓存（股票名称很少变化）

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
 * 获取股票名称映射（ts_code → 中文名称）
 * Tushare daily API 的 name 字段经常为空，需要用 stock_basic 接口补充
 * 
 * 缓存策略：
 * 1. 内存缓存（24小时TTL）——同一次函数调用内复用
 * 2. CloudBase 存储缓存——跨函数调用持久化，即使冷启动或限流也能读取
 * 3. stock_basic API（1次/小时限流）——仅在缓存失效时调用
 */
async function getStockNameMap() {
  // 检查内存缓存
  if (cachedNameMap && (Date.now() - cachedNameMapTs) < NAME_MAP_CACHE_TTL) {
    console.log('Using in-memory cached stock name map, size:', cachedNameMap.size);
    return cachedNameMap;
  }

  // 尝试从 CloudBase 存储读取缓存
  try {
    const cloudbase = require('@cloudbase/node-sdk');
    const app = cloudbase.init({
      env: process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d',
    });

    const result = await app.downloadFile({
      cloudPath: 'stock-names/name-map.json',
    });

    if (result && result.fileContent) {
      const stored = JSON.parse(result.fileContent.toString('utf-8'));
      if (stored && stored.names && stored.updatedAt) {
        const age = Date.now() - new Date(stored.updatedAt).getTime();
        // 存储缓存也在24小时TTL内时直接使用
        if (age < NAME_MAP_CACHE_TTL) {
          const nameMap = new Map(Object.entries(stored.names));
          cachedNameMap = nameMap;
          cachedNameMapTs = Date.now();
          console.log(`Using CloudBase stored name map: ${nameMap.size} entries (age: ${Math.round(age / 3600000)}h)`);
          return nameMap;
        }
        // 缓存过期但仍有数据——先用作 fallback，同时尝试刷新
        console.log(`Stored name map is stale (${Math.round(age / 3600000)}h old), will try refresh`);
        const fallbackMap = new Map(Object.entries(stored.names));
      }
    }
  } catch (e) {
    console.log('No stored name map in CloudBase:', e.message);
  }

  // 尝试从东方财富 API 刷新（替代 Tushare stock_basic，无频率限制）
  // 使用 https 模块而非 fetch（Node.js 18.15 的 fetch 是实验性的）
  try {
    console.log('Fetching stock names from EastMoney API (https module)...');
    const nameMap = new Map();
    const nameObj = {};

    const marketFilters = ['m:1+t:2', 'm:1+t:23', 'm:0+t:6', 'm:0+t:80'];

    for (const fs of marketFilters) {
      let page = 1;
      while (page <= 20) {
        const url = `https://80.push2.eastmoney.com/api/qt/clist/get?pn=${page}&pz=100&po=1&np=1&fltt=2&invt=2&fs=${encodeURIComponent(fs)}&fields=f12,f14`;
        console.log(`EastMoney fetching: fs=${fs}, page=${page}`);
        const data = await fetchHttps(url);

        if (!data || !data.data || !data.data.diff) {
          console.log(`EastMoney: no data for fs=${fs}, page=${page}`);
          break;
        }
        const stocks = data.data.diff;
        if (stocks.length === 0) break;

        for (const s of stocks) {
          const code = s.f12;
          const name = s.f14;
          if (!code || !name) continue;

          let tsCode;
          if (code.startsWith('6')) tsCode = code + '.SH';
          else if (code.startsWith('0') || code.startsWith('3')) tsCode = code + '.SZ';
          else if (code.startsWith('8') || code.startsWith('4')) tsCode = code + '.BJ';
          else continue;

          nameMap.set(tsCode, name);
          nameObj[tsCode] = name;
        }

        console.log(`EastMoney: fs=${fs}, page=${page}, got ${stocks.length} stocks`);
        if (stocks.length < 100) break;
        page++;
      }
    }

    console.log(`EastMoney total: ${nameMap.size} entries`);
    if (nameMap.size > 0) {
      cachedNameMap = nameMap;
      cachedNameMapTs = Date.now();
      console.log(`Got fresh stock name map from EastMoney: ${nameMap.size} entries`);

      try {
        const cloudbase = require('@cloudbase/node-sdk');
        const app = cloudbase.init({
          env: process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d',
        });
        await app.uploadFile({
          cloudPath: 'stock-names/name-map.json',
          fileContent: Buffer.from(JSON.stringify({
            names: nameObj,
            updatedAt: new Date().toISOString(),
            count: nameMap.size,
            source: 'eastmoney',
          }), 'utf-8'),
        });
        console.log('Name map persisted to CloudBase storage');
      } catch (storeErr) {
        console.log('Failed to persist name map:', storeErr.message);
      }

      return nameMap;
    } else {
      console.log('EastMoney returned 0 entries, will try fallback');
    }
  } catch (e) {
    console.log('EastMoney API failed:', e.message, e.stack);
  }

  // 最后 fallback：尝试用过期的存储缓存
  try {
    const cloudbase = require('@cloudbase/node-sdk');
    const app = cloudbase.init({
      env: process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d',
    });
    const result = await app.downloadFile({
      cloudPath: 'stock-names/name-map.json',
    });
    if (result && result.fileContent) {
      const stored = JSON.parse(result.fileContent.toString('utf-8'));
      if (stored && stored.names) {
        const nameMap = new Map(Object.entries(stored.names));
        cachedNameMap = nameMap;
        cachedNameMapTs = Date.now();
        console.log(`Using stale stored name map as fallback: ${nameMap.size} entries`);
        return nameMap;
      }
    }
  } catch (e) {
    // 无缓存可用
  }

// 最终 fallback：使用硬编码的名称映射（从东方财富API获取，2026-09-21）
  console.log('Using hardcoded name map fallback');
  try {
    const hardcoded = require('./hardcoded-names');
    const nameMap = new Map(Object.entries(hardcoded));
    cachedNameMap = nameMap;
    cachedNameMapTs = Date.now();
    console.log(`Hardcoded name map loaded: ${nameMap.size} entries`);
    return nameMap;
  } catch (e) {
    console.log('Hardcoded name map not available:', e.message);
  }

  // 绝对最终 fallback：返回空 Map
  console.log('Using empty name map fallback');
  return new Map();
}

/**
 * 获取最新交易日（带缓存，避免 trade_cal 频率超限）
 * 关键修复：加 start_date/end_date 限制查询范围，避免返回未来交易日
 */
async function getLatestTradeDate() {
  // 检查缓存
  if (cachedTradeDate && (Date.now() - cachedTradeDateTs) < TRADE_DATE_CACHE_TTL) {
    console.log('Using cached trade date:', cachedTradeDate);
    return cachedTradeDate;
  }

  // 计算 end_date（今天）和 start_date（30天前，确保能查到数据）
  const now = new Date();
  const endDateObj = new Date(now);
  const startDateObj = new Date(now);
  startDateObj.setDate(now.getDate() - 30);

  const fmt = (d) => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}${m}${day}`;
  };

  const endDate = fmt(endDateObj);
  const startDate = fmt(startDateObj);

  try {
    // 查询最近30天内已开盘的交易日，按日期降序取最新一个
    const tradeCal = await callTushare('trade_cal', {
      exchange: 'SSE',
      is_open: '1',
      start_date: startDate,
      end_date: endDate,
      limit: '1',
      offset: '0',
    }, 'cal_date');

    if (tradeCal && tradeCal.items && tradeCal.items.length > 0) {
      cachedTradeDate = tradeCal.items[0][0];
      cachedTradeDateTs = Date.now();
      console.log('Got latest trade date:', cachedTradeDate, `(range: ${startDate}~${endDate})`);
      return cachedTradeDate;
    }
  } catch (e) {
    console.log('trade_cal failed:', e.message);
  }

  // Fallback：使用当前日期推算（如果是工作日，用今天；否则用最近的周五）
  const day = now.getDay(); // 0=周日, 6=周六
  let fallbackDate;
  if (day === 0) {
    const friday = new Date(now);
    friday.setDate(now.getDate() - 2);
    fallbackDate = friday;
  } else if (day === 6) {
    const friday = new Date(now);
    friday.setDate(now.getDate() - 1);
    fallbackDate = friday;
  } else {
    fallbackDate = now;
  }
  const fallbackStr = fmt(fallbackDate);
  console.log('Using fallback trade date:', fallbackStr);
  return fallbackStr;
}

/**
 * 获取日线行情数据并筛选异动
 * 关键修复：用 stock_basic 名称映射补充 daily API 返回的空 name 字段
 */
async function getDailyMovers() {
  const tradeDate = await getLatestTradeDate();
  console.log(`Fetching daily data for ${tradeDate}...`);

  // 并行获取日线数据和股票名称映射
  const [dailyResult, nameMap] = await Promise.all([
    callTushare('daily', {
      trade_date: tradeDate,
    }, 'ts_code,name,pct_chg,close,vol,amount,open,high,low,pre_close').catch(e => {
      console.error('daily API failed:', e.message);
      return null;
    }),
    getStockNameMap(),
  ]);

  if (dailyResult && dailyResult.items && dailyResult.items.length > 0) {
    console.log(`Got ${dailyResult.items.length} daily records, name map size: ${nameMap.size}`);

    const movers = dailyResult.items.map(row => {
      const obj = {};
      dailyResult.fields.forEach((field, i) => {
        obj[field] = row[i];
      });
      // 关键修复：用 stock_basic 映射补充名称，daily API 的 name 字段经常为空
      if (!obj.name && obj.ts_code) {
        const mappedName = nameMap.get(obj.ts_code);
        if (mappedName) {
          obj.name = mappedName;
        }
      }
      return obj;
    }).filter(item => {
      const pct = parseFloat(item.pct_chg || 0);
      return Math.abs(pct) >= THRESHOLD;
    });

    console.log(`Filtered to ${movers.length} movers above ${THRESHOLD}%`);
    // 统计有多少条成功映射了名称
    const withName = movers.filter(m => m.name && m.name !== m.ts_code).length;
    console.log(`Name mapping: ${withName}/${movers.length} have Chinese names`);
    return movers;
  }

  return [];
}

/**
 * DKnowC 深知可信统一API——内容安全合规检查
 * 
 * 对信号卡的播报文本进行安全合规检测，确保内容不违反 AGENTS.md §二.2 信号松绑三禁：
 * ①承诺收益/保本等绝对化措辞；②催促性强指令；③任何对外公开/收费形态
 * 
 * API文档：https://platform.dknowc.cn/maas-api-doc/
 * 端点：POST https://open.dknowc.cn/chat/trusted/unification
 * 认证：api-key header
 * 
 * @param {string} text - 待检测的播报文本
 * @returns {Promise<{safeType: string, compliant: boolean}>} - 安全类型与合规标记
 */
async function checkCompliance(text) {
  if (!DKNOWC_API_KEY) {
    // 未配置API Key时跳过合规检查，不阻塞流程
    return { safeType: 'Unknown', compliant: true, skipped: true };
  }

  try {
    const response = await fetch(DKNOWC_API_URL, {
      method: 'POST',
      headers: {
        'api-key': DKNOWC_API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        input: text,
        safeAnswerScope: 'none', // 只做安全判断，不需要代答
      }),
    });

    if (!response.ok) {
      console.log(`[compliance] DKnowC API HTTP ${response.status}, skipping`);
      return { safeType: 'Unknown', compliant: true, skipped: true };
    }

    const data = await response.json();
    const safeType = data.safeType || 'Unknown';
    
    // Safe = 合规通过；ConditionallySafe = 有条件合规（可放行但留意）
    // Unsafe/Focus = 不合规（需审查）
    const compliant = safeType === 'Safe' || safeType === 'ConditionallySafe';
    
    console.log(`[compliance] "${text.substring(0, 30)}..." → safeType=${safeType}, compliant=${compliant}`);
    return { safeType, compliant, skipped: false };
  } catch (e) {
    console.log(`[compliance] DKnowC check failed: ${e.message}, skipping`);
    return { safeType: 'Unknown', compliant: true, skipped: true };
  }
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
 * 将异动数据上传到 CloudBase 存储（JSON 文件）
 * 替代 PostgreSQL——用存储服务存取 alerts.json
 */
async function saveAlertsToDB(alerts) {
  try {
    const cloudbase = require('@cloudbase/node-sdk');
    const app = cloudbase.init({
      env: process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d',
    });

    // 先下载现有数据（合并新旧，保留历史）
    let existingItems = [];
    let existingServerTs = 0;
    try {
      const result = await app.downloadFile({
        cloudPath: 'alerts/alerts.json',
      });
      if (result && result.fileContent) {
        const data = JSON.parse(result.fileContent.toString('utf-8'));
        existingItems = data.items || [];
        existingServerTs = data.serverTs || 0;
      }
    } catch (e) {
      // 文件不存在时正常，用空数组
      console.log('No existing alerts.json, creating new');
    }

    // P2 并发写入保护：若现有数据的 serverTs 比当前数据的最新 ts 更新，
    // 说明另一个实例已经写入了更新的4更新的数据，跳过本次写入避免覆盖
    const currentLatestTs = alerts.length > 0 ? Math.max(...alerts.map(a => a.ts)) : 0;
    if (existingServerTs > currentLatestTs) {
      console.log(`Skip write: existing serverTs=${existingServerTs} > current latestTs=${currentLatestTs} (concurrent write protection)`);
      return;
    }

    // 合并新旧数据，按 alertId 去重
    const alertMap = new Map();
    // 先放旧数据
    for (const item of existingItems) {
      alertMap.set(item.alertId, item);
    }
    // 再放新数据（覆盖同 alertId 的旧数据）
    for (const alert of alerts) {
      alertMap.set(alert.alertId, alert);
    }

    // 保留最新的 500 条（按 ts 降序）
    const allItems = Array.from(alertMap.values())
      .sort((a, b) => b.ts - a.ts)
      .slice(0, 500);

    const jsonContent = JSON.stringify({
      items: allItems,
      serverTs: Math.floor(Date.now() / 1000),
      updatedAt: new Date().toISOString(),
    });

    // 上传到 CloudBase 存储
    const uploadResult = await app.uploadFile({
      cloudPath: 'alerts/alerts.json',
      fileContent: Buffer.from(jsonContent, 'utf-8'),
    });

    console.log(`Saved ${alerts.length} new alerts (total ${allItems.length}) to CloudBase storage, fileID: ${uploadResult?.fileID || 'N/A'}`);
  } catch (e) {
    console.error('CloudBase storage error:', e.message);
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

    // 为信号卡（kind=signal）批量生成 TTS 音频，预填充 audioUrl
    // 信号卡是"自家信号"，更需要语音播报；事实卡用户可自行阅读
    // 限制最多10条，避免百炼额度过度消耗
    // DKnowC 合规检查：对播报文本进行安全合规检测，添加 complianceStatus 元数据
    const signalAlerts = alerts.filter(a => a.kind === 'signal').slice(0, 10);
    if (signalAlerts.length > 0) {
      console.log(`Generating TTS for ${signalAlerts.length} signal alerts...`);

      // 并行执行：DKnowC合规检查 + TTS生成
      // 合规检查不阻塞TTS生成——只添加元数据，不阻断流程
      const [complianceResults, ttsResults] = await Promise.all([
        Promise.allSettled(
          signalAlerts.map(alert =>
            checkCompliance(`${alert.headline}。${alert.detail}`)
          )
        ),
        (async () => {
          try {
            const cloudbase = require('@cloudbase/node-sdk');
            const app = cloudbase.init({
              env: process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d',
            });

            return await Promise.allSettled(
              signalAlerts.map(alert =>
                app.callFunction({
                  name: 'generate-tts',
                  data: {
                    alertId: alert.alertId,
                    text: `${alert.headline}。${alert.detail}`,
                  },
                })
              )
            );
          } catch (e) {
            console.log('TTS batch generation failed (non-blocking):', e.message);
            return signalAlerts.map(() => ({ status: 'rejected', reason: e }));
          }
        })(),
      ]);

      // 处理合规检查结果
      let compliantCount = 0;
      let nonCompliantCount = 0;
      for (let i = 0; i < signalAlerts.length; i++) {
        const cr = complianceResults[i];
        if (cr.status === 'fulfilled') {
          signalAlerts[i].complianceStatus = cr.value.safeType;
          if (cr.value.compliant) {
            compliantCount++;
          } else {
            nonCompliantCount++;
            console.log(`[compliance] ⚠ NON-COMPLIANT: ${signalAlerts[i].headline} → ${cr.value.safeType}`);
          }
        } else {
          signalAlerts[i].complianceStatus = 'Unknown';
        }
      }
      console.log(`[compliance] ${compliantCount} compliant, ${nonCompliantCount} non-compliant, ${signalAlerts.length - compliantCount - nonCompliantCount} unknown`);

      // 处理TTS结果
      let ttsSuccess = 0;
      for (let i = 0; i < signalAlerts.length; i++) {
        const result = ttsResults[i];
        if (result.status === 'fulfilled' && result.value?.result?.success) {
          signalAlerts[i].audioUrl = result.value.result.audioUrl;
          ttsSuccess++;
          console.log(`TTS OK for ${signalAlerts[i].alertId}: ${result.value.result.audioUrl?.substring(0, 60)}...`);
        } else {
          const errMsg = result.status === 'rejected'
            ? result.reason?.message || 'unknown error'
            : result.value?.result?.error || 'unknown error';
          console.log(`TTS FAIL for ${signalAlerts[i].alertId}: ${errMsg}`);
        }
      }
      console.log(`TTS batch done: ${ttsSuccess}/${signalAlerts.length} succeeded`);
    }

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
