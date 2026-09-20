/**
 * get-alerts 云函数（Event 函数模式）
 *
 * 功能：从 PostgreSQL alerts 表读取最新异动条目，返回 AlertFeed 格式 JSON。
 * 轻量级只读端点——不触发广播、不发送Push，专供客户端轮询。
 *
 * 返回格式（与 AlertItem.ets 的 AlertFeed 契约完全一致）：
 *   {
 *     items: AlertItem[],
 *     serverTs: number
 *   }
 *
 * AlertItem 字段映射（DB snake_case → 客户端 camelCase）：
 *   alert_id → alertId
 *   audio_url → audioUrl
 *   其余字段名相同
 *
 * 触发方式：Event 函数 + CloudBase HTTP 访问服务（--path /alerts）
 *   URL: https://{envId}.service.tcloudbase.com/alerts
 */

/**
 * 从 PostgreSQL 获取最新异动，映射为 AlertItem 格式
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

    // 映射 snake_case → camelCase，与 AlertItem 契约对齐
    return result.rows.map(row => ({
      alertId: row.alert_id,
      ts: row.ts,
      symbol: row.symbol,
      name: row.name,
      direction: row.direction,
      kind: row.kind || 'fact',
      headline: row.headline,
      detail: row.detail || '',
      audioUrl: row.audio_url || undefined,
    }));
  } catch (e) {
    console.error('DB query error:', e.message);
    return [];
  } finally {
    await client.end();
  }
}

/**
 * Event 函数入口
 * CloudBase HTTP 访问服务会将 HTTP GET 请求的 query 参数传入 event
 */
exports.main = async (event, context) => {
  // 从 HTTP 访问服务的 event 中提取 limit 参数
  const limit = Math.min(
    parseInt(event?.query?.limit || event?.limit || '20', 10),
    100
  );

  try {
    const items = await getLatestAlerts(limit);
    return {
      items,
      serverTs: Math.floor(Date.now() / 1000),
    };
  } catch (e) {
    console.error('get-alerts error:', e.message);
    return {
      items: [],
      serverTs: Math.floor(Date.now() / 1000),
    };
  }
};
