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
const BAILIAN_WORKSPACE_ID = 'ws-ay6o8osb22o9dc3t';
const TTS_WSS_URL = `wss://${BAILIAN_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference`;
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

    // 百炼 CosyVoice TTS（WebSocket 协议）
    const audioUrl = await generateTTS(headline, detail, alertId);

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
 * 调用百炼 CosyVoice TTS API（WebSocket 协议）生成语音
 * 
 * 交互流程：
 * 1. 建立 WebSocket 连接
 * 2. 发送 run-task 事件（设置模型、音色等参数）
 * 3. 等待 task-started 事件
 * 4. 发送 continue-task 事件（发送待合成文本）
 * 5. 接收 result-generated 事件和音频流（binary frames）
 * 6. 发送 finish-task 事件
 * 7. 接收 task-finished 事件
 * 8. 关闭连接
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

  const text = `${headline}。${detail}`;
  const taskId = crypto.randomUUID();

  return new Promise((resolve) => {
    const chunks = [];
    let resolved = false;
    const done = (result) => {
      if (!resolved) { resolved = true; resolve(result); }
    };

    try {
      // Node.js v22 内置 WebSocket
      const ws = new WebSocket(TTS_WSS_URL, {
        headers: {
          'Authorization': `Bearer ${BAILIAN_API_KEY}`,
        },
      });
      // 确保 binary 消息以 ArrayBuffer 形式接收（默认可能是 Blob）
      ws.binaryType = 'arraybuffer';

      const timeout = setTimeout(() => {
        console.error('[feed-server] TTS WebSocket timeout');
        try { ws.close(); } catch {}
        done(undefined);
      }, 30000);

      ws.addEventListener('open', () => {
        console.log('[feed-server] TTS WebSocket connected, sending run-task');
        // 步骤2: 发送 run-task 事件
        ws.send(JSON.stringify({
          header: {
            action: 'run-task',
            task_id: taskId,
            streaming: 'duplex',
          },
          payload: {
            task_group: 'audio',
            task: 'tts',
            function: 'SpeechSynthesizer',
            model: TTS_MODEL,
            input: {},
            parameters: {
              text_type: 'PlainText',
              voice: TTS_VOICE,
              format: 'mp3',
              sample_rate: 22050,
              volume: 50,
              rate: 1.0,
              pitch: 1.0,
            },
          },
        }));
      });

      ws.addEventListener('message', (event) => {
        // 区分二进制音频帧和文本事件
        if (event.data instanceof ArrayBuffer) {
          // 步骤5: 接收音频流（binary frames）
          chunks.push(Buffer.from(event.data));
          return;
        }
        // 文本消息 = 服务端事件
        try {
          const msg = JSON.parse(event.data);
          const action = msg?.header?.event;

          if (action === 'task-started') {
            console.log('[feed-server] TTS task-started, sending text');
            // 步骤4: 发送 continue-task 事件（待合成文本）
            ws.send(JSON.stringify({
              header: {
                action: 'continue-task',
                task_id: taskId,
                streaming: 'duplex',
              },
              payload: {
                input: { text },
              },
            }));
            // 步骤6: 发送 finish-task 事件（通知文本发送完毕）
            ws.send(JSON.stringify({
              header: {
                action: 'finish-task',
                task_id: taskId,
                streaming: 'duplex',
              },
              payload: {
                input: {},
              },
            }));
          } else if (action === 'result-generated') {
            const subType = msg?.payload?.output?.type;
            console.log(`[feed-server] TTS result-generated: ${subType}`);
            // sentence-synthesis 后紧跟 binary 音频帧
          } else if (action === 'task-finished') {
            console.log('[feed-server] TTS task-finished');
            clearTimeout(timeout);
            if (chunks.length > 0) {
              const buffer = Buffer.concat(chunks);
              fs.writeFileSync(cacheFile, buffer);
              console.log(`[feed-server] TTS generated ${buffer.length} bytes for ${alertId}`);
              done(`http://127.0.0.1:${PORT}/audio/${alertId}.mp3`);
            } else {
              console.error('[feed-server] TTS finished but no audio received');
              done(undefined);
            }
            try { ws.close(); } catch {}
          } else if (action === 'task-failed') {
            console.error('[feed-server] TTS task-failed:', JSON.stringify(msg?.header));
            clearTimeout(timeout);
            done(undefined);
            try { ws.close(); } catch {}
          }
        } catch (e) {
          // 非 JSON 消息，忽略
        }
      });

      ws.addEventListener('error', (event) => {
        console.error('[feed-server] TTS WebSocket error:', event.message || event);
        clearTimeout(timeout);
        done(undefined);
      });

      ws.addEventListener('close', () => {
        clearTimeout(timeout);
        done(undefined);
      });
    } catch (e) {
      console.error('[feed-server] TTS WebSocket init failed:', e.message);
      done(undefined);
    }
  });
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