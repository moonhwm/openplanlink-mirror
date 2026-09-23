---
name: tts-websocket
type: diag
created: 2026-09-23
updated: 2026-09-23
version: 1.1.0
trigger: generate-tts 云函数合成失败、REST 报错提示仅支持 WebSocket、端侧播报无声、audioUrl 长期为 undefined
source_files: [cloudfunctions/generate-tts/index.js（云函数，以仓库实际路径为准）]
---

# diag技能：百炼TTS WebSocket诊断——REST报错识别、WebSocket协议切换、连接调试

## 概述

harmony-app（铃语）的语音播报链路：alerts 卡片携带 audioUrl；audioUrl 为 undefined 时端侧按需调用 generate-tts 云函数合成，合成结果经 CloudBase 存储缓存后由端侧 AudioPlayer.ets（AVPlayer）播放音频流。已知问题：百炼 CosyVoice TTS 只支持 WebSocket 协议，REST 调用直接报错，项目已从 REST 迁移到 WebSocket。本技能覆盖三段：识别 REST 报错、掌握 WebSocket 协议流程、连接与音频调试。

## 适用场景

- REST 端点返回 InvalidParameter，message 含 "WebSocket is the only supported protocol for this model"。
- WebSocket 握手失败（401/1006）、task-started 迟迟不回、task-failed。
- 合成出的音频无法播放、时长异常、杂音。
- 端侧播报无声，需要区分"没合成""没上传""没拉流"三段。

红线：DASHSCOPE_API_KEY 只存云函数环境变量，不得进端侧代码、仓库与日志；演示卡可无音频但首屏永不空白。

## 执行步骤

### 步骤一：识别 REST 报错

典型错误调用与返回（项目实战记录）：

```
POST https://dashscope.aliyuncs.com/api/v1/services/audio/tts
→ {"code": "InvalidParameter",
   "message": "WebSocket is the only supported protocol for this model"}
```

判读表：

| 返回 | 判读 | 处置 |
| --- | --- | --- |
| InvalidParameter 且 message 提 WebSocket | TTS 无 REST 合成端点，方向性结论 | 进入步骤二，不要换 URL 绕过 |
| HTTP 404 / InvalidEndpoint | 路径不存在 | 同上 |
| HTTP 401 | Key 无效或欠费 | 查控制台开通状态与 Key |
| HTTP 429 | 限流 | 退避重试，另查调用方放大 |

判读原则：凡 message 或官方文档明确 TTS 只支持 WebSocket，立即走协议切换；反复更换 REST URL 与参数组合属于方向性浪费时间。

### 步骤二：WebSocket 协议切换

连接地址（项目现行配置）：`wss://{workspaceId}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference`；公共接入点 `wss://dashscope.aliyuncs.com/api-ws/v1/inference/` 亦存在于官方文档，以项目实际接通者为准。

认证通过握手 header 传递：

```javascript
const ws = new WebSocket(TTS_WSS_URL, {
  headers: { 'Authorization': `Bearer ${BAILIAN_API_KEY}` },
});
```

任务生命周期五步（JSON 文本帧交互）：

1. 客户端 → run-task：声明模型与参数。
2. 服务端 → task-started：任务已启动，此后才能发文本。
3. 客户端 → continue-task（携带文本）+ finish-task（结束输入）。
4. 服务端 → 多个二进制音频帧（与 JSON 事件帧交错下发）。
5. 服务端 → task-finished；异常路径为 task-failed。

run-task 关键参数（项目现行值）：

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

rate=0.9、pitch=0.95 是适老化刻意放慢放缓的播报口径，调整前先与适老化规范对齐。

### 步骤三：云函数侧实现要点

"零三方依赖"约束仅指端侧纯 ArkTS；generate-tts 云函数（Node.js）使用 WebSocket 客户端库合法。实现必须包含以下四件套（项目既有实现）：

1. 30 秒超时，超时关闭连接并返回 null，绝不让云函数悬挂到实例回收：

```javascript
const timeout = setTimeout(() => {
  console.error('TTS WebSocket timeout');
  try { ws.close(); } catch (e) {}
  done(null);
}, 30000);
```

2. Promise 防重入，避免超时与正常完成双路回调：

```javascript
let resolved = false;
const done = (result) => {
  if (!resolved) { resolved = true; resolve(result); }
};
```

3. 部分音频降级：连接提前关闭但已收到音频帧时，用部分音频兜底而不是直接失败：

```javascript
ws.addEventListener('close', () => {
  clearTimeout(timeout);
  if (!resolved && chunks.length > 0) {
    done(Buffer.concat(chunks));   // 部分音频降级
  } else if (!resolved) {
    done(null);
  }
});
```

4. 缓存与额度控制：cacheKey = SHA256(text) 前 16 位，查 CloudBase 存储 `tts-cache/{cacheKey}.json`，命中直接返回 audioUrl 不消耗额度；未命中才走 WebSocket 合成并回写缓存。QUOTA 记录用量，shouldStop() 为真时停止生成返回 null，防止额度击穿。

合成成功后上传对象存储、以 cacheKey/alertId 命名实现幂等，返回 audioUrl 供卡片使用。

### 步骤四：连接调试

先做最小复现：独立脚本只做"连接 → run-task → task-started → 一句固定文本 → finish-task → 落盘 out.mp3"，用播放器验证时长，排除业务干扰。

常见失败判读表：

| 现象 | 可能原因 | 处置 |
| --- | --- | --- |
| 握手 HTTP 401 | Key 无效、欠费、百炼未开通 | 控制台核对 Key 与开通状态 |
| 连接 1006/被重置 | 云函数 VPC/安全组拦 wss 出网、TLS/SNI 异常 | 放行 443 出网，确认用域名而非 IP |
| 握手成功但无 task-started | Authorization 前缀写错（项目用 Bearer）、task_id 非法、payload 字段拼错 | 对照步骤二逐字段核对 |
| task-failed InvalidParameter | voice 与 model 不匹配、参数越界 | voice 换该 model 支持的音色 |
| task-failed Arrearage/Throttling | 欠费/限流 | 充值或退避 |
| 音频杂音/无法播放 | 帧边界处理不当、format 与扩展名不符 | 核对二进制帧解析与 mp3 拼接逻辑 |

调试工具用 wscat 或 Node 脚本均可；日志打印事件名与 task_id，不打印 Key，正文日志截断脱敏。

### 步骤五：端侧衔接与降级

- generate-tts 成功 → 返回 audioUrl；失败或超时 → 卡片 audioUrl 保持 undefined，端侧按需重试或显示纯文字大字卡片；绝不能因 TTS 失败导致首屏空白。
- 端侧 AudioPlayer.ets 只认音频流 URL，不感知协议切换；播报无声时先 `curl -I <audioUrl>` 确认公网可达（200 且 content-type 为音频），再回查合成链路。
- 幂等：同一 alertId/同文案命中 SHA256 缓存直接复用，避免端侧 5 秒轮询放大重复合成；失败用指数退避。

## 质量门槛

- [ ] DASHSCOPE_API_KEY 已配置，未出现在端侧与仓库
- [ ] 使用 wss 地址与 Bearer 前缀，run-task 含正确 model/voice/parameters
- [ ] 30 秒超时、Promise 防重入、部分音频降级三件套齐全
- [ ] SHA256 缓存命中不重复消耗额度；QUOTA.shouldStop 生效
- [ ] task-failed/超时/额度三种路径都返回 null 而非悬挂
- [ ] 端侧验证：audioUrl 可公网访问，AVPlayer 播放正常

## 经验记录

- TTS 没有 REST 端点，REST 报错里的 WebSocket 提示就是最终答案，换 URL 无解。
- voice 必须与 model 配套（cosyvoice-v3-flash 配 longxiaochun_v3），跨系列混用直接 task-failed。
- rate=0.9/pitch=0.95 是适老化放缓口径，改回 1.0 会被评审打回。
- 云函数连接提前关闭时，已收到的部分音频可用，丢弃等于白白消耗额度。
- 缓存键用 SHA256(text) 而非 alertId，同文案跨卡片复用，额度省一半以上。

## 关联文档

- GOVERNANCE/skills/diag/tushare-token-failure.md（数据源降级与熔断模式）
- GOVERNANCE/skills/diag/cloudbase-cache.md（tts-cache 元数据缓存诊断）
- GOVERNANCE/skills/diag/feed-server-cache.md（轮询放大与幂等）

### 自我评估
- 正确性：4分 REST 报错信息、端点、参数与三件套实现均沿用项目既有实战记录，协议字段与当期官方文档可能存在版本差异，已注明以实际接通者为准；本次未实调百炼线上接口
- 完整性：5分 覆盖 REST 识别、协议切换、实现要点、连接调试、端侧衔接、质量门槛与经验记录
- 可复用性：5分 生命周期五步、判读表与实现四件套可直接复用到任何 DashScope 类 WebSocket 任务
- 字数：约3200字
- 使用模型：GLM-5.3-Flash
