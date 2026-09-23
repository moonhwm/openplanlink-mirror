# diag技能：百炼TTS WebSocket诊断

> 编写时间：2026-09-23
> 编写席位：砚坚（CodeArts GLM-5.2-sft-harmony）
> 适用场景：generate-tts云函数中百炼TTS API调用失败的诊断与修复

## 1. 问题背景

### REST API报错

百炼TTS REST API（`https://dashscope.aliyuncs.com/api/v1/services/audio/tts`）返回错误：
```
{"code": "InvalidParameter", "message": "WebSocket is the only supported protocol for this model"}
```

### 根因

百炼CosyVoice TTS模型**只支持WebSocket协议**，不支持REST API。这与feed-server的行为一致。

## 2. WebSocket调用方案

### 连接地址

```
wss://{workspaceId}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference
```

### 认证方式

WebSocket连接时通过header传递API Key：
```javascript
const ws = new WebSocket(TTS_WSS_URL, {
  headers: { 'Authorization': `Bearer ${BAILIAN_API_KEY}` },
});
```

### 消息协议（三步流程）

```
步骤1: 客户端 → run-task（声明模型和参数）
步骤2: 服务端 → task-started（确认任务已启动）
步骤3: 客户端 → continue-task（发送文本）+ finish-task（结束输入）
步骤4: 服务端 → 二进制音频帧（多个）+ task-finished（任务完成）
```

### 关键参数

```javascript
{
  header: { action: 'run-task', task_id: taskId, streaming: 'duplex' },
  payload: {
    task_group: 'audio',
    task: 'tts',
    function: 'SpeechSynthesizer',
    model: 'cosyvoice-v3-flash',
    input: {},
    parameters: {
      text_type: 'PlainText',
      voice: 'longxiaochun_v3',
      format: 'mp3',
      sample_rate: 16000,
      volume: 65,
      rate: 0.9,
      pitch: 0.95,
    },
  },
}
```

## 3. 诊断流程

```
1. 检查DASHSCOPE_API_KEY环境变量
   → 未配置 → 返回错误"DASHSCOPE_API_KEY not configured"
   → 已配置 → 继续

2. 检查百炼额度
   → QUOTA.shouldStop() → 返回null，停止生成
   → 额度正常 → 继续

3. 建立WebSocket连接
   → 连接失败 → 检查API Key有效性
   → 连接成功 → 发送run-task

4. 等待task-started
   → 30秒超时 → 关闭连接，返回null
   → 收到task-started → 发送continue-task + finish-task

5. 接收音频帧
   → task-failed → 记录错误，返回null
   → task-finished → 合并音频帧，返回Buffer
   → 连接关闭但有部分数据 → 使用部分音频（降级）
```

## 4. 错误处理

### 超时处理

```javascript
const timeout = setTimeout(() => {
  console.error('TTS WebSocket timeout');
  try { ws.close(); } catch (e) {}
  done(null);
}, 30000);
```

### 部分音频降级

```javascript
ws.addEventListener('close', () => {
  clearTimeout(timeout);
  if (!resolved && chunks.length > 0) {
    // 连接关闭但有部分音频数据，使用部分音频作为降级
    const audioBuffer = Buffer.concat(chunks);
    done(audioBuffer);
  } else if (!resolved) {
    done(null);
  }
});
```

### Promise防重入

```javascript
let resolved = false;
const done = (result) => {
  if (!resolved) { resolved = true; resolve(result); }
};
```

## 5. 缓存策略

### SHA256缓存键

```javascript
function getCacheKey(text) {
  return crypto.createHash('sha256').update(text).digest('hex').substring(0, 16);
}
```

### 缓存流程

```
1. 计算cacheKey = SHA256(text)[:16]
2. 查询CloudBase存储 tts-cache/{cacheKey}.json
3. 命中 → 返回缓存的audioUrl（不消耗百炼额度）
4. 未命中 → WebSocket生成 → 上传音频 → 保存缓存元数据
```

### 额度监控

```javascript
const QUOTA = {
  totalEstimated: 1000000,
  usedTokens: 0,
  warningThreshold: 0.8,
  stopThreshold: 1.0,
  recordUsage(textLength) { this.usedTokens += Math.ceil(textLength * 2.5); },
  shouldStop() { return this.usedTokens / this.totalEstimated >= this.stopThreshold; },
};
```

## 6. 验证清单

- [ ] DASHSCOPE_API_KEY环境变量已配置
- [ ] WebSocket连接地址格式正确（wss://）
- [ ] 认证header使用`Bearer`前缀
- [ ] run-task消息包含正确的model和parameters
- [ ] 30秒超时已设置
- [ ] 部分音频降级已实现
- [ ] Promise防重入机制已实现
- [ ] SHA256缓存键已实现
- [ ] 额度监控机制已实现

---

*本技能文档由砚坚席位于2026-09-23编写，基于百炼TTS从REST API迁移到WebSocket的实战经验提炼。*