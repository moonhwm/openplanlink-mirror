/**
 * broadcast-a2a 云函数
 * 
 * 功能：
 * 1. 从 PostgreSQL alerts 表获取最新异动条目
 * 2. 通过 A2A 总线广播异动消息（Supabase 实时推送）
 * 3. 通过 CloudBase 推送服务向鸿蒙设备发送 Push 通知
 * 4. 支持 HTTP 触发（Web 函数模式，scf_bootstrap）和 Event 触发
 * 
 * 环境变量：
 *   SUPABASE_URL - Supabase 项目 URL
 *   SUPABASE_ANON_KEY - Supabase 匿名密钥
 *   PUSH_BUNDLE_NAME - 鸿蒙应用包名
 *   PORT / SCF_RUNTIME_PORT - Web 函数模式端口（自动注入）
 */

const http = require('http');
const SUPABASE_URL = process.env.SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || '';
const PUSH_BUNDLE_NAME = process.env.PUSH_BUNDLE_NAME || 'com.lingyu.app';

/**
 * 从 PostgreSQL 获取最新异动
 */
async function getLatestAlerts(limit = 20) {
  const { PG_CONN_STRING } = process.env;
  if (!PG_CONN_STRING) return [];

  let pg;
  try { pg = require('pg'); } catch (e) { return []; }

  const client = new pg.Client({ connectionString: PG_CONN_STRING });
  try {
    await client.connect();
    const result = await client.query(
      `SELECT alert_id, ts, symbol, name, direction, kind, headline, detail, audio_url
       FROM alerts
       ORDER BY ts DESC
       LIMIT $1`,
      [limit]
    );
    return result.rows;
  } catch (e) {
    console.error('DB query error:', e.message);
    return [];
  } finally {
    await client.end();
  }
}

/**
 * 通过 Supabase Realtime 广播异动消息
 */
async function broadcastToSupabase(alerts) {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    console.log('Supabase not configured, skipping broadcast');
    return;
  }

  try {
    const response = await fetch(`${SUPABASE_URL}/rest/v1/a2a_messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        channel: 'alerts',
        message_type: 'alert_feed',
        payload: JSON.stringify({
          items: alerts,
          serverTs: Math.floor(Date.now() / 1000),
        }),
        created_at: new Date().toISOString(),
      }),
    });

    if (response.ok) {
      console.log(`Broadcast ${alerts.length} alerts to Supabase`);
    } else {
      console.error('Supabase broadcast failed:', response.status);
    }
  } catch (e) {
    console.error('Supabase broadcast error:', e.message);
  }
}

/**
 * 通过 CloudBase 推送服务发送 Push 通知
 */
async function sendPushNotification(alert) {
  let cloudbase;
  try {
    cloudbase = require('@cloudbase/node-sdk');
  } catch (e) {
    console.log('cloudbase node-sdk not available, skipping push');
    return;
  }

  const app = cloudbase.init({
    env: process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d',
  });

  try {
    const message = {
      title: alert.headline,
      body: alert.detail || '',
      data: {
        alertId: alert.alert_id,
        symbol: alert.symbol,
        kind: alert.kind || 'fact',
        audioUrl: alert.audio_url || '',
      },
      android: {
        notification: {
          channel_id: 'alert_channel',
          sound: 'default',
          click_action: {
            type: 1,
            intent: `${PUSH_BUNDLE_NAME}.EntryAbility`,
          },
        },
      },
    };

    const result = await app.messaging().send({
      message,
      topic: 'stock_alerts',
    });

    console.log('Push sent:', JSON.stringify(result));
  } catch (e) {
    console.error('Push error:', e.message);
  }
}

/**
 * 核心处理逻辑——获取异动、广播、推送
 */
async function handleBroadcast(limit = 20) {
  const alerts = await getLatestAlerts(limit);

  if (alerts.length === 0) {
    return {
      success: true,
      items: [],
      serverTs: Math.floor(Date.now() / 1000),
      message: 'No alerts found',
    };
  }

  await broadcastToSupabase(alerts);

  let pushCount = 0;
  for (const alert of alerts) {
    if (alert.kind === 'signal' || alert.direction !== 'flat') {
      await sendPushNotification(alert);
      pushCount++;
    }
  }

  return {
    success: true,
    items: alerts,
    serverTs: Math.floor(Date.now() / 1000),
    count: alerts.length,
    pushCount,
  };
}

/**
 * Event 触发入口
 */
exports.main = async (event, context) => {
  console.log('broadcast-a2a Event invoked');
  try {
    return await handleBroadcast(20);
  } catch (e) {
    console.error('broadcast-a2a error:', e.message);
    return { success: false, error: e.message };
  }
};

/**
 * Web 函数模式——HTTP 服务器（scf_bootstrap 启动）
 * 当 PORT 环境变量存在时自动启动
 */
const port = process.env.PORT || process.env.SCF_RUNTIME_PORT || 9000;

if (process.env.PORT || process.env.SCF_RUNTIME_PORT) {
  const server = http.createServer(async (req, res) => {
    console.log(`HTTP ${req.method} ${req.url}`);

    // CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
      res.writeHead(204);
      res.end();
      return;
    }

    // 解析 URL 参数
    const url = new URL(req.url, `http://localhost:${port}`);
    const limit = parseInt(url.searchParams.get('limit') || '20', 10);

    try {
      const result = await handleBroadcast(limit);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(result));
    } catch (e) {
      console.error('HTTP handler error:', e.message);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: false, error: e.message }));
    }
  });

  server.listen(port, () => {
    console.log(`broadcast-a2a HTTP server listening on port ${port}`);
  });
}
