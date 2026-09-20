/**
 * generate-tts 云函数
 * 
 * 功能：
 * 1. 接收异动条目（alertId + headline + detail）
 * 2. 通过 WebSocket 调用阿里百炼 TTS API 生成语音（与 feed-server 同协议）
 * 3. 将音频上传到 CloudBase 云存储
 * 4. 更新 alerts 表的 audio_url 字段
 * 5. 缓存到 tts_cache 表避免重复生成
 * 
 * 触发方式：由 fetch-tushare-data 调用 或 手动调用
 * 环境变量：DASHSCOPE_API_KEY（必需）
 * 依赖：ws（WebSocket 客户端）
 */

const WebSocket = require('ws');
const crypto = require('crypto');

const BAILIAN_WORKSPACE_ID = process.env.BAILIAN_WORKSPACE_ID || 'ws-ay6o8osb22o9dc3t';
const BAILIAN_API_KEY = process.env.DASHSCOPE_API_KEY || '';
const TTS_MODEL = 'cosyvoice-v3-flash';
const TTS_VOICE = 'longxiaochun_v3';
const TTS_WSS_URL = `wss://${BAILIAN_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference`;

// 百炼额度监控
const QUOTA = {
  totalEstimated: 1000000,
  usedTokens: 0,
  warningThreshold: 0.8,
  stopThreshold: 1.0,

  recordUsage(textLength) {
    this.usedTokens += Math.ceil(textLength * 2.5);
  },

  shouldStop() {
    return this.usedTokens / this.totalEstimated >= this.stopThreshold;
  },

  getStatus() {
    const ratio = this.usedTokens / this.totalEstimated;
    return {
      level: ratio >= this.stopThreshold ? 'stop' : ratio >= this.warningThreshold ? 'warning' : 'normal',
      usedTokens: this.usedTokens,
      totalEstimated: this.totalEstimated,
      usageRatio: parseFloat(ratio.toFixed(4)),
    };
  },
};

/**
 * 生成缓存键（文本的 SHA256 前16位）
 */
function getCacheKey(text) {
  return crypto.createHash('sha256').update(text).digest('hex').substring(0, 16);
}

/**
 * 查询 tts_cache 表是否已有缓存
 */
async function checkCache(cacheKey) {
  const { PG_CONN_STRING } = process.env;
  if (!PG_CONN_STRING) return null;

  let pg;
  try { pg = require('pg'); } catch (e) { return null; }

  const client = new pg.Client({ connectionString: PG_CONN_STRING });
  try {
    await client.connect();
    const result = await client.query(
      'SELECT audio_url FROM tts_cache WHERE cache_key = $1 AND (expires_at IS NULL OR expires_at > NOW())',
      [cacheKey]
    );
    if (result.rows.length > 0) {
      await client.query('UPDATE tts_cache SET accessed_at = NOW() WHERE cache_key = $1', [cacheKey]);
      return result.rows[0].audio_url;
    }
  } catch (e) {
    console.error('Cache check error:', e.message);
  } finally {
    await client.end();
  }
  return null;
}

/**
 * 保存缓存到 tts_cache 表
 */
async function saveCache(cacheKey, text, audioUrl) {
  const { PG_CONN_STRING } = process.env;
  if (!PG_CONN_STRING) return;

  let pg;
  try { pg = require('pg'); } catch (e) { return; }

  const client = new pg.Client({ connectionString: PG_CONN_STRING });
  try {
    await client.connect();
    await client.query(
      `INSERT INTO tts_cache (cache_key, text, audio_url, voice, model, expires_at)
       VALUES ($1, $2, $3, $4, $5, NOW() + INTERVAL '7 days')
       ON CONFLICT (cache_key) DO UPDATE SET accessed_at = NOW(), audio_url = $3`,
      [cacheKey, text, audioUrl, TTS_VOICE, TTS_MODEL]
    );
  } catch (e) {
    console.error('Cache save error:', e.message);
  } finally {
    await client.end();
  }
}

/**
 * 更新 alerts 表的 audio_url
 */
async function updateAlertAudioUrl(alertId, audioUrl) {
  const { PG_CONN_STRING } = process.env;
  if (!PG_CONN_STRING) return;

  let pg;
  try { pg = require('pg'); } catch (e) { return; }

  const client = new pg.Client({ connectionString: PG_CONN_STRING });
  try {
    await client.connect();
    await client.query('UPDATE alerts SET audio_url = $1 WHERE alert_id = $2', [audioUrl, alertId]);
  } catch (e) {
    console.error('Alert update error:', e.message);
  } finally {
    await client.end();
  }
}

/**
 * 通过 WebSocket 调用百炼 TTS API 生成语音
 * 与 feed-server/server.mjs 使用完全相同的协议
 */
async function generateTTSAudio(text) {
  if (!BAILIAN_API_KEY) {
    console.error('DASHSCOPE_API_KEY not set');
    return null;
  }

  if (QUOTA.shouldStop()) {
    console.error('Bailian quota exceeded, stopping TTS generation');
    return null;
  }

  return new Promise((resolve) => {
    const taskId = crypto.randomUUID();
    const chunks = [];
    let resolved = false;
    const done = (result) => {
      if (!resolved) { resolved = true; resolve(result); }
    };

    try {
      const ws = new WebSocket(TTS_WSS_URL, {
        headers: {
          'Authorization': `Bearer ${BAILIAN_API_KEY}`,
        },
      });

      ws.binaryType = 'arraybuffer';

      const timeout = setTimeout(() => {
        console.error('TTS WebSocket timeout');
        try { ws.close(); } catch (e) {}
        done(null);
      }, 30000);

      ws.addEventListener('open', () => {
        console.log('TTS WebSocket connected, sending run-task');
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
              sample_rate: 16000,
              volume: 65,
              rate: 0.9,
              pitch: 0.95,
            },
          },
        }));
      });

      ws.addEventListener('message', (event) => {
        if (event.data instanceof ArrayBuffer) {
          chunks.push(Buffer.from(event.data));
          return;
        }
        try {
          const msg = JSON.parse(event.data);
          const action = msg?.header?.event;

          if (action === 'task-started') {
            console.log('TTS task-started, sending text');
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
          }

          if (action === 'task-finished') {
            console.log(`TTS task-finished, ${chunks.length} audio chunks received`);
            clearTimeout(timeout);
            QUOTA.recordUsage(text.length);
            const audioBuffer = Buffer.concat(chunks);
            done(audioBuffer);
            try { ws.close(); } catch (e) {}
          }

          if (action === 'task-failed') {
            console.error('TTS task-failed:', JSON.stringify(msg));
            clearTimeout(timeout);
            done(null);
            try { ws.close(); } catch (e) {}
          }
        } catch (e) {
          // 非 JSON 消息，忽略
        }
      });

      ws.addEventListener('error', (event) => {
        console.error('TTS WebSocket error:', event.message || 'unknown');
        clearTimeout(timeout);
        done(null);
      });

      ws.addEventListener('close', () => {
        clearTimeout(timeout);
        if (!resolved && chunks.length > 0) {
          console.log(`WebSocket closed with ${chunks.length} chunks, using partial audio`);
          QUOTA.recordUsage(text.length);
          const audioBuffer = Buffer.concat(chunks);
          done(audioBuffer);
        } else if (!resolved) {
          done(null);
        }
      });
    } catch (e) {
      console.error('TTS WebSocket init error:', e.message);
      done(null);
    }
  });
}

/**
 * 上传音频到 CloudBase 云存储
 */
async function uploadToStorage(audioBuffer, cacheKey) {
  let cloudbase;
  try {
    cloudbase = require('@cloudbase/node-sdk');
  } catch (e) {
    console.error('cloudbase node-sdk not available');
    return null;
  }

  const app = cloudbase.init({
    env: process.env.TCB_ENV || 'a2a-commonwealth-d2eepjr928e9c4d',
  });

  const storagePath = `tts/${cacheKey}.mp3`;

  try {
    const result = await app.uploadFile({
      cloudPath: storagePath,
      fileContent: audioBuffer,
    });

    if (result.fileID) {
      const urlResult = await app.getTempFileURL({
        fileList: [result.fileID],
      });
      if (urlResult.fileList && urlResult.fileList[0] && urlResult.fileList[0].tempFileURL) {
        return urlResult.fileList[0].tempFileURL;
      }
      return result.fileID;
    }
  } catch (e) {
    console.error('Storage upload error:', e.message);
  }

  return null;
}

/**
 * 云函数入口
 */
exports.main = async (event, context) => {
  console.log('generate-tts invoked', JSON.stringify({
    alertId: event.alertId,
    text: event.text?.substring(0, 50) + '...',
    quotaStatus: QUOTA.getStatus(),
  }));

  const { alertId, text } = event;

  if (!text) {
    return { success: false, error: 'text is required' };
  }

  if (!BAILIAN_API_KEY) {
    return { success: false, error: 'DASHSCOPE_API_KEY not configured' };
  }

  try {
    // 1. 检查缓存
    const cacheKey = getCacheKey(text);
    const cachedUrl = await checkCache(cacheKey);
    if (cachedUrl) {
      console.log('Cache hit, returning cached audio URL');
      if (alertId) {
        await updateAlertAudioUrl(alertId, cachedUrl);
      }
      return { success: true, audioUrl: cachedUrl, cached: true };
    }

    // 2. 通过 WebSocket 生成 TTS 音频
    console.log('Generating TTS audio via WebSocket...');
    const audioBuffer = await generateTTSAudio(text);
    if (!audioBuffer) {
      return { success: false, error: 'TTS generation failed' };
    }

    console.log(`TTS audio generated: ${audioBuffer.length} bytes`);

    // 3. 上传到云存储
    console.log('Uploading to cloud storage...');
    const audioUrl = await uploadToStorage(audioBuffer, cacheKey);
    if (!audioUrl) {
      return { success: false, error: 'Storage upload failed' };
    }

    // 4. 保存缓存
    await saveCache(cacheKey, text, audioUrl);

    // 5. 更新 alert 的 audio_url
    if (alertId) {
      await updateAlertAudioUrl(alertId, audioUrl);
    }

    return {
      success: true,
      audioUrl,
      cached: false,
      audioSize: audioBuffer.length,
      quotaStatus: QUOTA.getStatus(),
    };
  } catch (e) {
    console.error('generate-tts error:', e.message);
    return { success: false, error: e.message };
  }
};
