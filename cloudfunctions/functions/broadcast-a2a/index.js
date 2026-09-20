/**
 * broadcast-a2a 云函数
 * 
 * 功能：
 * 1. 从 PostgreSQL alerts 表获取最新异动条目
 * 2. 通过 A2A 总线广播异动消息（Supabase 实时推送）
 * 3. 通过 CloudBase 推送服务向鸿蒙设备发送 Push 通知
 * 4. 支持 HTTP 触发（供 feed-server 调用）和 Event 触发（定时）
 * 
 * 环境变量：
 *   SUPABASE_URL - Supabase 项目 URL
 *   SUPABASE_ANON_KEY - Supabase 匿名密钥
 *   PUSH_BUNDLE_NAME - 鸿蒙应用包名
 */

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

  // 使用 Supabase REST API 插入消息到 realtime 频道
  // 客户端订阅 'alerts' 频道即可实时接收
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
    // 使用 CloudBase 的推送服务
    // 注意：鸿蒙 Push 需要通过 HMS Push Kit，这里通过 CloudBase 的 messaging API
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

    // 调用 CloudBase messaging API
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
 * HTTP 触发入口
 */
exports.main = async (event, context) => {
  console.log('broadcast-a2a invoked', JSON.stringify({
    event: event.httpMethod ? 'HTTP' : 'Event',
    path: event.path || '',
  }));

  // HTTP 触发模式
  if (event.httpMethod === 'GET' || event.httpMethod === 'POST') {
    const limit = parseInt(event.queryString?.limit || '20', 10);

    const alerts = await getLatestAlerts(limit);

    if (alerts.length === 0) {
      return {
        statusCode: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          success: true,
          items: [],
          serverTs: Math.floor(Date.now() / 1000),
          message: 'No alerts found',
        }),
      };
    }

    // 广播到 Supabase
    await broadcastToSupabase(alerts);

    // 对重要异动（kind=signal 或涨跌幅大）发送 Push
    for (const alert of alerts) {
      if (alert.kind === 'signal' || alert.direction !== 'flat') {
        await sendPushNotification(alert);
      }
    }

    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        success: true,
        items: alerts,
        serverTs: Math.floor(Date.now() / 1000),
        count: alerts.length,
      }),
    };
  }

  // Event 触发模式（定时器或手动调用）
  try {
    const alerts = await getLatestAlerts(20);

    if (alerts.length === 0) {
      return {
        success: true,
        items: [],
        message: 'No alerts to broadcast',
      };
    }

    // 广播到 Supabase
    await broadcastToSupabase(alerts);

    // 对重要异动发送 Push
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
      count: alerts.length,
      pushCount,
      serverTs: Math.floor(Date.now() / 1000),
    };
  } catch (e) {
    console.error('broadcast-a2a error:', e.message);
    return { success: false, error: e.message };
  }
};