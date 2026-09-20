/**
 * generate-tts 云函数
 * 
 * 功能：
 * 1. 接收异动条目（alertId + headline + detail）
 * 2. 调用阿里百炼 TTS API 生成语音
 * 3. 将音频上传到 CloudBase 云存储
 * 4. 更新 alerts 表的 audio_url 字段
 * 5. 缓存到 tts_cache 表避免重复生成
 * 
 * 触发方式：由 fetch-tushare-data 调用 或 手动调用
 * 环境变量：DASHSCOPE_API_KEY（必需）
 */

const BAILIAN_WORKSPACE_ID = process.env.BAILIAN_WORKSPACE_ID || 'ws-ay6o8osb22o9dc3t';
const BAILIAN_API_KEY = process.env.DASHSCOPE_API_KEY || '';
const TTS_MODEL = 'cosyvoice-v3-flash';
const TTS_VOICE = 'longxiaochun_v3';
const TTS_WSS_URL = `wss://${BAILIAN_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference`;

// 百炼额度监控（与 feed-server 同逻辑）
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
  const crypto = require('crypto');
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
      // 更新访问时间
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
 * 调用百炼 TTS API 生成语音
 * 使用 HTTP API（非 WebSocket）简化云函数环境兼容
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

  // 使用百炼 REST API
  const apiUrl = `https://${BAILIAN_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/text2audio/generation`;

  const requestBody = JSON.stringify({
    model: TTS_MODEL,
    input: {
      text: text,
    },
    parameters: {
      voice: TTS_VOICE,
      format: 'mp3',
      sample_rate: 16000,
    },
  });

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${BAILIAN_API_KEY}`,
        'X-DashScope-DataInspection': 'enable',
      },
      body: requestBody,
    });

    if (!response.ok) {
      const errText = await response.text();
      console.error(`TTS API HTTP ${response.status}: ${errText}`);
      return null;
    }

    // 百炼 TTS 返回 JSON，包含 audio 字段（base64 编码的音频数据）
    const result = await response.json();
    if (result.output && result.output.audio) {
      QUOTA.recordUsage(text.length);
      return result.output.audio; // base64 编码的音频数据
    }

    // 某些版本返回 URL
    if (result.output && result.output.url) {
      QUOTA.recordUsage(text.length);
      return result.output.url; // 直接返回 URL
    }

    console.error('TTS API unexpected response:', JSON.stringify(result));
    return null;
  } catch (e) {
    console.error('TTS API error:', e.message);
    return null;
  }
}

/**
 * 上传音频到 CloudBase 云存储
 */
async function uploadToStorage(audioData, cacheKey) {
  // 在云函数环境中，使用 @cloudbase/node-sdk 上传文件
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
    // 如果 audioData 是 base64，先解码
    let buffer;
    if (typeof audioData === 'string' && audioData.length > 200) {
      // base64 编码的音频数据
      buffer = Buffer.from(audioData, 'base64');
    } else {
      // 已经是 URL，直接返回
      return audioData;
    }

    const result = await app.uploadFile({
      cloudPath: storagePath,
      fileContent: buffer,
    });

    if (result.fileID) {
      // 获取公共访问 URL
      const urlResult = await app.getTempFileURL({
        fileList: [result.fileID],
      });
      if (urlResult.fileList && urlResult.fileList[0] && urlResult.fileList[0].tempFileURL) {
        return urlResult.fileList[0].tempFileURL;
      }
      return result.fileID; // 返回 fileID 作为 fallback
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
      // 更新 alert 的 audio_url
      if (alertId) {
        await updateAlertAudioUrl(alertId, cachedUrl);
      }
      return { success: true, audioUrl: cachedUrl, cached: true };
    }

    // 2. 生成 TTS 音频
    console.log('Generating TTS audio...');
    const audioData = await generateTTSAudio(text);
    if (!audioData) {
      return { success: false, error: 'TTS generation failed' };
    }

    // 3. 上传到云存储
    console.log('Uploading to cloud storage...');
    const audioUrl = await uploadToStorage(audioData, cacheKey);
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
      quotaStatus: QUOTA.getStatus(),
    };
  } catch (e) {
    console.error('generate-tts error:', e.message);
    return { success: false, error: e.message };
  }
};