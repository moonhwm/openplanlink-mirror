/**
 * broadcast-a2a 云函数
 *
 * 功能：
 * 1. 从 CloudBase 存储读取最新异动条目（alerts.json）
 * 2. 通过 A2A 总线广播异动消息（Supabase 实时推送）
 * 3. 通过 CloudBase 推送服务向鸿蒙设备发送 Push 通知
 * 4. 支持 HTTP 触发（Web 函数模式，scf_bootstrap）和 Event 触发
 *
 * 环境变量：
 *   SUPABASE_URL - Supabase 项目 URL（可选）
 *   SUPABASE_ANON_KEY - Supabase 匿名密钥（可选）
 *   PUSH_BUNDLE_NAME - 鸿蒙应用包名
 *   PORT / SCF_RUNTIME_PORT - Web 函数模式端口（自动注入）
 */

const http = require('http');
const SUPABASE_URL = process.env.SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || '';
const PUSH_BUNDLE_NAME = process.env.PUSH_BUNDLE_NAME || 'com.lingyu.app';
const ENV_ID = process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d';
const ALERTS_FILE_ID = 'cloud://a2a-commonwealth-d2eepjr928e9c4d.6132-a2a-commonwealth-d2eepjr928e9c4d-1475054847/alerts/alerts.json';

/**
 * 从 CloudBase 存储获取最新异动
 */
async function getLatestAlerts(limit = 20) {
  try {
    const cloudbase = require('@cloudbase/node-sdk');
    const app = cloudbase.init({ env: ENV_ID });

    const result = await app.downloadFile({ fileID: ALERTS_FILE_ID });

    if (result && result.fileContent) {
      const text = result.fileContent.toString('utf-8');
      const data = JSON.parse(text);
      if (data && data.items && Array.isArray(data.items)) {
        const sorted = data.items.sort((a, b) => b.ts - a.ts);
        return sorted.slice(0, limit);
      }
    }

    return [];
  } catch (e) {
    console.error('broadcast-a2a: failed to read alerts.json:', e.message);
    return [];
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
 * 通过华为 Push Kit REST API 发送 Push 通知
 *
 * 华为 Push Kit 服务端推送流程：
 * 1. 获取 OAuth 2.0 Bearer Token（使用 AGC projectId + JWT）
 * 2. 调用 POST https://push-api.cloud.huawei.com/v3/{projectId}/messages:send
 *
 * 环境变量：
 *   HUAWEI_PUSH_PROJECT_ID - AGC projectId（必需）
 *   HUAWEI_PUSH_CLIENT_ID - AGC clientId（必需，用于获取OAuth Token）
 *   HUAWEI_PUSH_CLIENT_SECRET - AGC clientSecret（必需，用于获取OAuth Token）
 *   HUAWEI_PUSH_TOKEN - 设备Push Token（调试用，生产环境应从数据库获取）
 *
 * 当环境变量未配置时，Push功能自动跳过（不报错），等AGC配置完成后即可使用。
 */
async function sendPushNotification(alert) {
  const PROJECT_ID = process.env.HUAWEI_PUSH_PROJECT_ID || '';
  const CLIENT_ID = process.env.HUAWEI_PUSH_CLIENT_ID || '';
  const CLIENT_SECRET = process.env.HUAWEI_PUSH_CLIENT_SECRET || '';
  const DEVICE_PUSH_TOKEN = process.env.HUAWEI_PUSH_TOKEN || '';

  if (!PROJECT_ID || !CLIENT_ID || !CLIENT_SECRET) {
    console.log('Push Kit not configured (need HUAWEI_PUSH_PROJECT_ID/CLIENT_ID/CLIENT_SECRET), skipping push');
    return;
  }

  if (!DEVICE_PUSH_TOKEN) {
    console.log('No device push token available, skipping push');
    return;
  }

  try {
    // 步骤1：获取 OAuth 2.0 Bearer Token
    const tokenResp = await fetch('https://oauth-login.cloud.huawei.com/oauth2/v3/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'client_credentials',
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
      }).toString(),
    });

    if (!tokenResp.ok) {
      console.error('Push: OAuth token request failed:', tokenResp.status);
      return;
    }

    const tokenData = await tokenResp.json();
    const accessToken = tokenData.access_token;
    if (!accessToken) {
      console.error('Push: No access_token in OAuth response');
      return;
    }

    // 步骤2：发送 Push 消息
    const pushUrl = `https://push-api.cloud.huawei.com/v3/${PROJECT_ID}/messages:send`;
    const message = {
      notification: {
        title: alert.headline,
        body: alert.detail || '',
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
      data: JSON.stringify({
        alertId: alert.alertId,
        symbol: alert.symbol,
        kind: alert.kind || 'fact',
        audioUrl: alert.audioUrl || '',
      }),
      token: [DEVICE_PUSH_TOKEN],
    };

    const pushResp = await fetch(pushUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ message }),
    });

    if (pushResp.ok) {
      const pushResult = await pushResp.json();
      console.log('Push sent:', JSON.stringify(pushResult));
    } else {
      const pushError = await pushResp.text();
      console.error('Push send failed:', pushResp.status, pushError.substring(0, 200));
    }
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