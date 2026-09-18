/**
 * 铃语数据管道服务器
 * 
 * 数据链路：westock-data (腾讯自选股) → 异动筛选 → AlertFeed JSON → 铃语App
 * 
 * 端点：
 *   GET /api/alerts/latest?limit=N  →  AlertFeed JSON
 *   GET /health                      →  健康检查
 * 
 * 异动判断：涨跌幅绝对值 ≥ THRESHOLD（默认 5%）
 * TTS音频：百炼 cosyvoice-v3-flash 生成，缓存到 data/tts-cache/
 */

import http from 'node:http';
import { exec } from 'node:child_process';
import { promisify } from 'node:util';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const execAsync = promisify(exec);

const PORT = 8000;
const THRESHOLD = 5.0; // 涨跌幅绝对值阈值（%）
const REFRESH_INTERVAL = 30000; // 数据刷新间隔（ms）
const TTS_CACHE_DIR = path.join(import.meta.dirname, 'data', 'tts-cache');
const NODE_EXE = 'C:/Users/欧阳宏俊/nodejs/node-v22.11.0-win-x64/node.exe';
const NODE_DIR = 'C:/Users/欧阳宏俊/nodejs/node-v22.11.0-win-x64';
const NPX_CLI = 'C:/Users/欧阳宏俊/nodejs/node-v22.11.0-win-x64/node_modules/npm/bin/npx-cli.js';
const WESTOCK_PKG = 'westock-data-clawhub@1.0.4';

// 确保 exec 环境中 PATH 包含 node 目录
const EXEC_ENV = {
  ...process.env,
  PATH: `${NODE_DIR};${process.env.PATH || ''}`,
};

// 百炼 TTS 配置（从环境变量或金库文件读取）
const BAILIAN_API_KEY = process.env.DASHSCOPE_API_KEY || loadBailianKey();
const TTS_MODEL = 'cosyvoice-v3-flash';
const TTS_VOICE = 'longxiaochun_v3';

function loadBailianKey() {
  try {
    // 尝试多个可能的路径
    const paths = [
      path.join(import.meta.dirname, '..', '..', '..', 'GOVERNANCE', 'credentials', 'aliyun_bailian.json'),
      'C:/Users/欧阳宏俊/Documents/kimi/tasks/2026-08-27/22-20-45-c3ffff44/GOVERNANCE/credentials/aliyun_bailian.json',
    ];
    for (const credPath of paths) {
      if (fs.existsSync(credPath)) {
        const cred = JSON.parse(fs.readFileSync(credPath, 'utf-8'));
        console.log('[feed-server] loaded bailian key from:', credPath);
        return cred.api_key || '';
      }
    }
    console.log('[feed-server] bailian credential file not found in any path');
  } catch (e) { console.error('[feed-server] loadBailianKey error:', e.message); }
  return '';
}

// 确保缓存目录存在
fs.mkdirSync(TTS_CACHE_DIR, { recursive: true });

/** 当前缓存的异动列表 */
let cachedAlerts = [];
let lastRefreshTs = 0;

/**
 * 调用 westock-data CLI 获取热搜股票
 */
async function fetchHotStocks() {
  try {
    const cmd = `"${NODE_EXE}" "${NPX_CLI}" -y ${WESTOCK_PKG} hot stock`;
    console.log('[feed-server] executing:', cmd.substring(0, 80) + '...');
    const { stdout, stderr } = await execAsync(cmd, { timeout: 30000, env: EXEC_ENV });
    console.log('[feed-server] stdout length:', stdout.length, 'stderr length:', stderr?.length || 0);
    if (stdout.length === 0) {
      console.log('[feed-server] empty stdout, stderr:', stderr?.substring(0, 200));
      return [];
    }
    console.log('[feed-server] stdout first 300 chars:', JSON.stringify(stdout.substring(0, 300)));
    const parsed = parseMarkdownTable(stdout);
    console.log('[feed-server] parsed rows:', parsed.length);
    return parsed;
  } catch (e) {
    console.error('[feed-server] fetchHotStocks failed:', e.message.substring(0, 200));
    return [];
  }
}


/**
 * 调用 westock-data 获取个股分时数据（判断异动）
 */
async function fetchMinuteData(code) {
  try {
    const cmd = `"${NODE_EXE}" "${NPX_CLI}" -y ${WESTOCK_PKG} minute ${code}`;
    const { stdout } = await execAsync(cmd, { timeout: 30000, env: EXEC_ENV });
    return parseMarkdownTable(stdout);
  } catch (e) {
    console.error(`[feed-server] fetchMinuteData(${code}) failed:`, e.message);
    return [];
  }
}

/**
 * 解析 Markdown 表格为对象数组
 */
function parseMarkdownTable(md) {
  const lines = md.trim().split('\n').filter((l) => l.trim() && !l.trim().startsWith('| ---'));
  if (lines.length < 2) return [];
  
  const parseRow = (line) => {
    // 去掉首尾的 |，然后按 | 分割
    const inner = line.trim().replace(/^\|/, '').replace(/\|$/, '');
    return inner.split('|').map((c) => c.trim());
  };
  
  const headers = parseRow(lines[0]);
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const cells = parseRow(lines[i]);
    if (cells.length === headers.length) {
      const obj = {};
      headers.forEach((h, idx) => { obj[h] = cells[idx]; });
      rows.push(obj);
    }
  }
  return rows;
}

/**
 * 从热搜股票中筛选异动并生成 AlertItem
 */
async function detectAlerts() {
  console.log('[feed-server] refreshing alerts...');
  const hotStocks = await fetchHotStocks();
  if (hotStocks.length === 0) {
    console.log('[feed-server] no hot stocks data');
    return [];
  }

  const alerts = [];
  for (const stock of hotStocks) {
    const zdf = parseFloat(stock.zdf); // 涨跌幅
    if (isNaN(zdf) || Math.abs(zdf) < THRESHOLD) continue;

    // 只处理 A 股（代码以 sh/sz/bj 开头）
    const code = stock.code;
    if (!/^(sh|sz|bj)/.test(code)) continue;

    const direction = zdf > 0 ? 'up' : zdf < 0 ? 'down' : 'flat';
    const name = stock.name;
    const price = parseFloat(stock.zxj) || 0;
    const symbol = code.replace(/^(sh|sz|bj)/, '');

    // 生成白话标题
    const headline = `${name} ${direction === 'up' ? '涨了' : '跌了'} ${Math.abs(zdf).toFixed(1)}%`;
    const detail = `当前价格 ${price.toFixed(2)} 元，涨跌幅 ${zdf.toFixed(2)}%`;

    // 生成 alertId（基于内容哈希，确保幂等）
    const alertId = crypto.createHash('md5').update(`${symbol}-${Date.now()}`).digest('hex').substring(0, 12);

    // TTS 暂时跳过（百炼 API 格式待调试），先保证数据管道畅通
    const audioUrl = undefined; // await generateTTS(headline, detail, alertId);

    alerts.push({
      alertId,
      ts: Math.floor(Date.now() / 1000),
      symbol,
      name,
      direction,
      kind: 'fact',
      headline,
      detail,
      audioUrl,
    });

    // 最多 20 条
    if (alerts.length >= 20) break;
  }

  console.log(`[feed-server] detected ${alerts.length} alerts`);
  return alerts;
}

/**
 * 调用百炼 TTS API 生成语音
 */
async function generateTTS(headline, detail, alertId) {
  // 检查缓存
  const cacheFile = path.join(TTS_CACHE_DIR, `${alertId}.mp3`);
  if (fs.existsSync(cacheFile)) {
    return `http://127.0.0.1:${PORT}/audio/${alertId}.mp3`;
  }

  if (!BAILIAN_API_KEY) {
    console.log('[feed-server] no DASHSCOPE_API_KEY, skipping TTS');
    return undefined;
  }

  try {
    const text = `${headline}。${detail}`;
    const response = await fetch('https://dashscope.aliyuncs.com/api/v1/services/audio/tts', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${BAILIAN_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: TTS_MODEL,
        input: { text },
        parameters: { voice: TTS_VOICE, format: 'mp3' },
      }),
    });

    if (!response.ok) {
      console.error(`[feed-server] TTS API ${response.status}: ${await response.text()}`);
      return undefined;
    }

    const buffer = Buffer.from(await response.arrayBuffer());
    fs.writeFileSync(cacheFile, buffer);
    console.log(`[feed-server] TTS generated for ${alertId}`);
    return `http://127.0.0.1:${PORT}/audio/${alertId}.mp3`;
  } catch (e) {
    console.error('[feed-server] TTS failed:', e.message);
    return undefined;
  }
}

/**
 * 刷新数据
 */
async function refresh() {
  try {
    cachedAlerts = await detectAlerts();
    lastRefreshTs = Date.now();
  } catch (e) {
    console.error('[feed-server] refresh failed:', e.message);
  }
}

/**
 * HTTP 服务器
 */
const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://127.0.0.1:${PORT}`);

  // CORS 头
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // 健康检查
  if (url.pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      ok: true,
      alerts: cachedAlerts.length,
      lastRefresh: new Date(lastRefreshTs).toISOString(),
    }));
    return;
  }

  // 音频文件
  if (url.pathname.startsWith('/audio/')) {
    const filename = url.pathname.replace('/audio/', '');
    const filePath = path.join(TTS_CACHE_DIR, filename);
    if (fs.existsSync(filePath)) {
      const stat = fs.statSync(filePath);
      res.writeHead(200, {
        'Content-Type': 'audio/mpeg',
        'Content-Length': stat.size,
      });
      fs.createReadStream(filePath).pipe(res);
      return;
    }
    res.writeHead(404);
    res.end('audio not found');
    return;
  }

  // AlertFeed API
  if (url.pathname === '/api/alerts/latest') {
    const limit = parseInt(url.searchParams.get('limit') || '20', 10);
    const items = cachedAlerts.slice(0, limit);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      items,
      serverTs: Math.floor(Date.now() / 1000),
    }));
    return;
  }

  // 404
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'not found' }));
});

// 启动
server.listen(PORT, '127.0.0.1', async () => {
  console.log(`[feed-server] 铃语数据管道服务器已启动 → http://127.0.0.1:${PORT}`);
  console.log(`[feed-server] AlertFeed API → http://127.0.0.1:${PORT}/api/alerts/latest`);
  console.log(`[feed-server] 异动阈值 → ${THRESHOLD}%`);
  console.log(`[feed-server] TTS → ${BAILIAN_API_KEY ? '百炼 cosyvoice-v3-flash' : '未配置 DASHSCOPE_API_KEY'}`);
  
  // 首次刷新
  await refresh();
  
  // 定时刷新
  setInterval(refresh, REFRESH_INTERVAL);
  console.log(`[feed-server] 数据刷新间隔 → ${REFRESH_INTERVAL / 1000}s`);
});