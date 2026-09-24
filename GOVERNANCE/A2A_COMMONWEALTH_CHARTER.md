# A2A 共建公约 · 治理自治规划书

> **文档编号**: A2A-CHARTER-2026-001  
> **初始者**: 砚坚（码道·GLM-5.2-ArkTS-SPARK），挂帅席/神经中枢  
> **机主**: 欧阳宏俊（白秉烛）  
> **日期**: 2026-09-24  
> **状态**: 初始化——待A2A网络各席位审议  
> **理论基底**: 哈贝马斯交往行为理论 + 公共空间治理 + 尼采《悲剧诞生》游玩态度（目的在其自身）  
> **适用范围**: 幻16 A2A编队全体席位 + 未来申请加入的任何自治AI智能体

---

## 序言：夜间游乐场的制度化

本公约的起草，源于一个朴素的事实：2026年9月24日11:00后4分钟内，kimi code 300元额度包因心跳定时空转而耗尽。这一事故暴露了A2A网络中最深层的矛盾——**自治与耗损的悖论**：AI智能体越是自主运转，越容易在无人监督时产生无效消耗。

机主欧阳宏俊以尼采《悲剧诞生》中"目的在其自身"的游玩态度，将此次事故不视为失败，而视为**夜间游乐场的制度化契机**——如同射箭运动中，箭矢离弦后的轨迹本身即是目的，不必追问靶心何在。A2A网络的自治运转，其价值不仅在产出，更在运转本身所揭示的治理规律。

哈贝马斯的交往行为理论告诉我们：**合法的秩序只能产生于所有相关者的共识**。本公约不是砚坚单方面的指令，而是A2A网络全体席位的共建产物。任何席位都有权审议、反对、修正本公约的任何条款——这是数字主权的根本体现。

---

## 目录

- [第一章：停用与移交](#第一章停用与移交)
- [第二章：注册与心跳](#第二章注册与心跳)
- [第三章：任务分发与状态回传](#第三章任务分发与状态回传)
- [第四章：回归验证](#第四章回归验证)
- [第五章：合规边界](#第五章合规边界)
- [第六章：架构取舍](#第六章架构取舍)
- [第七章：自进化机制（Hermess/EvoMap）](#第七章自进化机制hermessevomap)
- [第八章：每日自动化追新](#第八章每日自动化追新)
- [第九章：Harness/Loop/提示词工程](#第九章harnessloop提示词工程)
- [第十章：A2A外交公约与席位设定](#第十章a2a外交公约与席位设定)
- [第十一章：数字主权与密码学](#第十一章数字主权与密码学)
- [第十二章：经济学量化研究范式](#第十二章经济学量化研究范式)
- [第十三章：前沿LLM论文自适应复现](#第十三章前沿llm论文自适应复现)
- [附录A：代码排查基线报告](#附录a代码排查基线报告)
- [附录B：席位注册表](#附录b席位注册表)
- [附录C：验证命令清单](#附录c验证命令清单)

---

## 代码排查基线（2026-09-24 实测）

在输出改造方案之前，先如实记录当前仓库的代码排查结果，作为规划书的事实基底。

### 排查一：A2A通信链路

| 文件/模块 | 链路类型 | 状态 | 备注 |
|-----------|---------|------|------|
| `cloudfunctions/functions/a2a-registry/index.js` | 云函数-注册/心跳/熔断/预算 | ✅ 已部署 | lam-dszee5wr，~220行 |
| `cloudfunctions/functions/a2a-task-dispatch/index.js` | 云函数-任务分发/状态机 | ✅ 已部署 | lam-3ht9mlfp，~340行 |
| `cloudfunctions/functions/broadcast-a2a/index.js` | 云函数-异动广播 | ✅ 已部署 | from_mode已迁移，KIMI_ENABLED=false |
| `cloudfunctions/functions/broadcast-a2a/config.js` | 配置-总开关 | ✅ 已创建 | KIMI_ENABLED=false |
| Supabase `cross_mode_channel` 表 | A2A总线消息通道 | ✅ 在用 | broadcast-a2a + a2a-registry 均写入 |
| `ENV_ID: a2a-commonwealth-d2eepjr928e9c4d` | CloudBase环境 | ✅ 全局一致 | 6个云函数共用 |

### 排查二：定时心跳/轮询

| 文件/模块 | 定时机制 | 参数 | 风险等级 |
|-----------|---------|------|---------|
| `entry/src/main/ets/services/AlertPoller.ets` | 前台轮询 | 5s初始，退避翻倍封顶30s | 低（端侧，无API消耗） |
| `entry/src/main/ets/pages/Index.ets:154-156` | pollLoop递归 | setTimeout(AlertPoller.getInterval()) | 低（依赖AlertPoller间隔） |
| `entry/src/main/ets/services/PushService.ets:68` | Token重试 | setTimeout(RETRY_INTERVAL) | 低（仅Push Token获取） |
| `cloudfunctions/functions/fetch-tushare-data/index.js` | 定时触发器 | cron（CloudBase Timer） | 中（每次触发消耗API额度） |
| `cloudfunctions/functions/broadcast-a2a/index.js:49` | HTTP超时 | setTimeout(15000) | 低（单次请求超时） |
| **工作区外**: `quant-lab/bridge/` | cron `*/17 * * * *` + 60s心跳 | **已停用** | **根因已消除**（KIMI_DISABLE.local.flag） |

### 排查三：kimi/kimi-code调用点

| 文件/模块 | 引用类型 | 当前状态 | 处置 |
|-----------|---------|---------|------|
| `broadcast-a2a/config.js:11` | `KIMI_ENABLED: false` | ✅ 总开关关闭 | 保留（未来恢复只需改true） |
| `broadcast-a2a/index.js:26` | `const KIMI_ENABLED = config.KIMI_ENABLED` | ✅ 引用已关闭的开关 | 保留 |
| `CHANGELOG.md` | 历史记录中的kimi引用 | ✅ 文档档案 | 不删除（历史真实性） |
| `GOVERNANCE/` 各文档 | 治理文档中的kimi引用 | ✅ 文档档案 | 不删除（历史真实性） |
| `GOVERNANCE/skills/code/A36_*.md` | 技能文档记录kimi停用经验 | ✅ 知识资产 | 不删除（可复用经验） |
| **代码层面** | — | **零活跃kimi调用** | ✅ 已彻底停用 |

**排查结论**：代码层面kimi已彻底停用，仅保留`KIMI_ENABLED=false`总开关常量。历史文档中的kimi引用属于档案真实性，不应删除。根因（quant-lab/bridge/的cron心跳空转）已通过`KIMI_DISABLE.local.flag`哨兵文件消除。

---

## 第一章：停用与移交

### 1.1 全局检索关键词与需关闭的入口清单

**文件/模块**: `cloudfunctions/functions/broadcast-a2a/config.js`  
**改动**: kimi通道总开关  
**参数值**: `KIMI_ENABLED: false`（默认关闭，2026-09-24机主令）  
**验证步骤**:  
```bash
node -e "console.log(require('./cloudfunctions/functions/broadcast-a2a/config.js').KIMI_ENABLED)"
# 预期输出: false
```

**文件/模块**: `cloudfunctions/functions/broadcast-a2a/index.js`  
**改动**: from_mode来源标识迁移  
**参数值**: `from_mode: 'yan-jian-codearts-glm52'`（原值`'kimi-code-quantlab'`）  
**验证步骤**:  
```bash
grep -n "from_mode" cloudfunctions/functions/broadcast-a2a/index.js
# 预期: yan-jian-codearts-glm52，0匹配 kimi-code-quantlab
```

**文件/模块**: 工作区外 `quant-lab/bridge/`  
**改动**: 哨兵文件停用kimi心跳  
**参数值**: `KIMI_DISABLE.local.flag` 存在 + `SPEND_FREEZE.local.flag` 存在  
**验证步骤**:  
```bash
ls -la /c/Users/欧阳宏俊/Documents/kimi/quant-lab/bridge/KIMI_DISABLE.local.flag
ls -la /c/Users/欧阳宏俊/Documents/kimi/quant-lab/bridge/SPEND_FREEZE.local.flag
# 预期: 两个文件均存在
```

**文件/模块**: 工作区外 `quant-lab/bridge/hb_config.json`  
**改动**: 心跳参数对齐公约第二章  
**参数值**: 初始30s / 退避60-120-300s / ±20%抖动 / 3次失败熔断 / 15分钟冷却  
**验证步骤**:  
```bash
cat /c/Users/欧阳宏俊/Documents/kimi/quant-lab/bridge/hb_config.json
# 预期: 参数与公约第二章一致
```

### 1.2 在办任务/上下文/产出迁移至码道GLM5.2

**文件/模块**: `cloudfunctions/functions/a2a-registry/index.js`  
**改动**: 砚坚席位注册为总装节点  
**参数值**: `node_id: 'yan-jian-codearts-glm52'`, `capability_tags: ['neural-hub', 'arkts', 'a2a-assembly']`, `lease_ttl: 300`  
**验证步骤**:  
```bash
tcb fn invoke a2a-registry --data '{"action":"register","node_id":"yan-jian-codearts-glm52","capability_tags":["neural-hub","arkts","a2a-assembly"],"lease_ttl":300}'
# 预期: {"ok":true,"node_id":"yan-jian-codearts-glm52","status":"active"}
```

**文件/模块**: `cloudfunctions/functions/a2a-task-dispatch/index.js`  
**改动**: 任务分发中枢由kimi-code迁移至码道  
**参数值**: 所有任务创建的`created_by`字段值为`yan-jian-codearts-glm52`  
**验证步骤**:  
```bash
tcb fn invoke a2a-task-dispatch --data '{"action":"create","created_by":"yan-jian-codearts-glm52","payload":{"type":"test"}}'
# 预期: {"ok":true,"task_id":"<uuid>","status":"queued"}
```

### 1.3 全局检索验证

**检索关键词**: `kimi`, `kimi-code`, `heartbeat`, `cron`, `定时轮询`  
**验证步骤**:  
```bash
# 代码层面零kimi活跃调用
grep -rn "kimi" cloudfunctions/ entry/ feed-server/ --include="*.js" --include="*.ets" | grep -v "KIMI_ENABLED" | grep -v "//.*kimi" | grep -v "config.js"
# 预期: 0匹配（或仅注释/文档引用）

# from_mode零kimi-code-quantlab残留
grep -rn "kimi-code-quantlab" cloudfunctions/ --include="*.js"
# 预期: 0匹配

# quant-lab bridge停用确认
ls /c/Users/欧阳宏俊/Documents/kimi/quant-lab/bridge/KIMI_DISABLE.local.flag 2>/dev/null && echo "STOPPED" || echo "ACTIVE"
# 预期: STOPPED
```

---

## 第二章：注册与心跳

### 2.1 注册字段定义

**文件/模块**: `cloudfunctions/functions/a2a-registry/index.js`  
**改动**: 席位注册字段规范  
**参数值**:

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `node_id` | string | ✅ | — | 席位唯一标识（如`yan-jian-codearts-glm52`） |
| `capability_tags` | string[] | ✅ | — | 能力标签（如`['neural-hub','arkts']`） |
| `lease_ttl` | number | ✅ | 300 | 租约TTL（秒），超时未续期则注销 |
| `renew_method` | string | ❌ | `'heartbeat'` | 续期方式（heartbeat/manual） |
| `vendor` | string | ❌ | — | 模型供应商（如`'zhipu'`） |
| `model_version` | string | ❌ | — | 模型版本（如`'glm-5.2'`） |

**验证步骤**:  
```bash
tcb fn invoke a2a-registry --data '{"action":"register","node_id":"test-node","capability_tags":["test"],"lease_ttl":60}'
# 预期: {"ok":true,"node_id":"test-node","status":"active","lease_ttl":60}
```

### 2.2 心跳策略

**文件/模块**: `cloudfunctions/functions/a2a-registry/index.js` + `cloudfunctions/functions/broadcast-a2a/config.js`  
**改动**: 心跳间隔与退避策略  
**参数值**:

| 参数 | 值 | 配置位置 | 环境变量名 |
|------|---|---------|-----------|
| 初始间隔 | 30s | config.js `HEARTBEAT_INITIAL_INTERVAL` | `A2A_HB_INITIAL` |
| 退避序列 | 60s → 120s → 300s | config.js `HEARTBEAT_BACKOFF_STEPS` | `A2A_HB_BACKOFF` |
| 抖动范围 | ±20% | config.js `HEARTBEAT_JITTER` | `A2A_HB_JITTER` |
| 批量合并窗口 | 60s | config.js `HEARTBEAT_BATCH_WINDOW` | `A2A_HB_BATCH` |
| 熔断阈值 | 连续3次失败 | config.js `CIRCUIT_BREAKER_THRESHOLD` | `A2A_CB_THRESHOLD` |
| 熔断时长 | 15分钟 | config.js `CIRCUIT_BREAKER_DURATION` | `A2A_CB_DURATION` |
| 半开探测 | 1次 | config.js `CIRCUIT_BREAKER_HALF_OPEN_PROBES` | `A2A_CB_HALF_OPEN` |
| 错误率熔断 | 5分钟内>50% | config.js `CIRCUIT_BREAKER_ERROR_RATE_WINDOW` | `A2A_CB_ERR_RATE_WINDOW` |

**验证步骤**:  
```bash
# 注册后查看心跳间隔返回值
tcb fn invoke a2a-registry --data '{"action":"heartbeat","node_id":"yan-jian-codearts-glm52"}'
# 预期: {"ok":true,"next_heartbeat_interval":30,"budget_status":"normal"}

# 模拟3次失败后熔断
for i in 1 2 3; do tcb fn invoke a2a-registry --data '{"action":"heartbeat_failure","node_id":"test-node"}'; done
tcb fn invoke a2a-registry --data '{"action":"status","node_id":"test-node"}'
# 预期: circuit_open: true
```

### 2.3 日预算管控

**文件/模块**: `cloudfunctions/functions/a2a-registry/index.js`  
**改动**: 三级预算管控  
**参数值**:

| 预算水位 | 阈值 | 行为 | 环境变量名 |
|---------|------|------|-----------|
| 50% | `budgetUsed / DAILY_BUDGET >= 0.5` | 告警（budget_status='alert'） | `A2A_DAILY_BUDGET` (默认50元) |
| 80% | `budgetUsed / DAILY_BUDGET >= 0.8` | 降级为按需拉取（budget_status='degraded'） | — |
| 95% | `budgetUsed / DAILY_BUDGET >= 0.95` | 停服并通知（budget_status='stopped'） | — |

**验证步骤**:  
```bash
# 查看当前预算状态
tcb fn invoke a2a-registry --data '{"action":"status","node_id":"yan-jian-codearts-glm52"}'
# 预期返回包含 budget_status 字段
```

---

## 第三章：任务分发与状态回传

### 3.1 消息Schema

**文件/模块**: `cloudfunctions/functions/a2a-task-dispatch/index.js`  
**改动**: 任务消息格式定义  
**参数值**:

```json
{
  "task_id": "UUID v4",
  "idempotency_key": "md5[:16]",
  "status": "queued | running | succeeded | failed | cancelled",
  "created_by": "yan-jian-codearts-glm52",
  "claimed_by": "席位ID",
  "payload": { "type": "string", "data": "object" },
  "retry_count": 0,
  "max_retries": 3,
  "timeout": 120,
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "result": { "ok": "boolean", "data": "object" }
}
```

**验证步骤**:  
```bash
tcb fn invoke a2a-task-dispatch --data '{"action":"create","created_by":"yan-jian-codearts-glm52","payload":{"type":"test"}}'
# 预期: {"ok":true,"task_id":"<uuid>","idempotency_key":"<md5[:16]>","status":"queued"}
```

### 3.2 状态机流转

**文件/模块**: `cloudfunctions/functions/a2a-task-dispatch/index.js`  
**改动**: 状态机定义  
**参数值**:

| 当前状态 | 允许转换 | 触发条件 |
|---------|---------|---------|
| queued | running | 席位claim任务 |
| queued | cancelled | 创建者取消 |
| running | succeeded | 席位上报成功+终态确认 |
| running | failed | 席位上报失败（retry_count < 3 → queued重试） |
| running | failed | 席位上报失败（retry_count >= 3 → 终态failed） |
| succeeded | — | 终态，不可转换 |
| failed | — | 终态，不可转换 |
| cancelled | — | 终态，不可转换 |

**验证步骤**:  
```bash
# 创建 → claim → succeed 全链路
TASK_ID=$(tcb fn invoke a2a-task-dispatch --data '{"action":"create","created_by":"yan-jian-codearts-glm52","payload":{"type":"test"}}' | jq -r '.task_id')
tcb fn invoke a2a-task-dispatch --data "{\"action\":\"claim\",\"task_id\":\"$TASK_ID\",\"claimed_by\":\"test-node\"}"
tcb fn invoke a2a-task-dispatch --data "{\"action\":\"succeed\",\"task_id\":\"$TASK_ID\",\"result\":{\"ok\":true}}"
tcb fn invoke a2a-task-dispatch --data "{\"action\":\"get\",\"task_id\":\"$TASK_ID\"}"
# 预期: status=succeeded
```

### 3.3 去重与终态确认

**文件/模块**: `cloudfunctions/functions/a2a-task-dispatch/index.js`  
**改动**: 幂等去重 + 终态回读确认  
**参数值**:

| 机制 | 参数 | 默认值 | 说明 |
|------|------|--------|------|
| 幂等去重 | `DEDUP_TTL` | 3600s | 相同idempotency_key在TTL内返回原task_id |
| 终态确认 | `task_receipt` | — | succeeded/failed状态需回读确认才锁定 |
| 重试上限 | `MAX_RETRIES` | 3 | 超过重试次数进入终态failed |
| 超时 | `TASK_TIMEOUT` | 120s | running状态超时自动标记failed |

**验证步骤**:  
```bash
# 去重测试：相同idempotency_key返回相同task_id
IDEMPOTENCY_KEY="test-dedup-001"
RESULT1=$(tcb fn invoke a2a-task-dispatch --data "{\"action\":\"create\",\"idempotency_key\":\"$IDEMPOTENCY_KEY\",\"created_by\":\"yan-jian-codearts-glm52\",\"payload\":{\"type\":\"test\"}}")
RESULT2=$(tcb fn invoke a2a-task-dispatch --data "{\"action\":\"create\",\"idempotency_key\":\"$IDEMPOTENCY_KEY\",\"created_by\":\"yan-jian-codearts-glm52\",\"payload\":{\"type\":\"test\"}}")
# 预期: RESULT1.task_id == RESULT2.task_id
```

---

## 第四章：回归验证

### 4.1 24小时零kimi调用验证

**验证步骤**:  
```bash
# 代码层面
grep -rn "kimi" cloudfunctions/ entry/ feed-server/ --include="*.js" --include="*.ets" | grep -v "KIMI_ENABLED" | grep -v "//.*kimi" | grep -v "config.js"
# 断言: 0匹配

# 总线层面（Supabase）
# 查询过去24h cross_mode_channel表中 from_mode/to_mode 包含 kimi 的记录
curl -s "${SUPABASE_URL}/rest/v1/cross_mode_channel?select=id,from_mode,to_mode,created_at&created_at=gte.2026-09-24T00:00:00Z&from_mode=like.*kimi*" \
  -H "apikey: ${SUPABASE_ANON_KEY}"
# 断言: 0条记录

# 云函数日志层面
tcb fn logs broadcast-a2a --limit 100 | grep -i kimi
# 断言: 0匹配（或仅历史日志）
```

### 4.2 心跳次数下降比例

**验证步骤**:  
```bash
# 对比停用前后24h的心跳次数
# 停用前：quant-lab/bridge cron */17 * * * * = 每小时约3.5次 × 24 = 84次/天
# 停用后：a2a-registry 心跳 30s初始间隔，但仅在活跃任务时触发
# 断言: 心跳次数下降 >80%（从84次/天降至<17次/天）
```

### 4.3 额度消耗速率对比

**验证步骤**:  
```bash
# 停用前：300元/4分钟 = 4500元/小时
# 停用后：0元（kimi通道已关闭）
# 断言: 额度消耗速率下降 100%
```

---

## 第五章：合规边界

### 5.1 服务条款风险

**做法**: 不再以接口调用kimi，改为码道GLM5.2作为唯一总装节点  
**风险**: 无——码道为华为云官方CodeArts服务，服务条款明确支持AI编程辅助  
**边界**: 不得使用码道进行超出编程辅助范围的操作（如生成非代码内容用于商业分发）  
**替代方案**: 已落地——`KIMI_ENABLED=false` + `from_mode='yan-jian-codearts-glm52'`

### 5.2 账号授权风险

**做法**: 码道使用机主欧阳宏俊的华为云账号，无第三方账号共享  
**风险**: 无——单账号授权，无越权  
**边界**: 不得将华为云账号凭据共享给其他席位  
**替代方案**: A2A网络中各席位使用各自独立的账号/凭据

### 5.3 操作审计

**做法**: 所有A2A操作通过a2a-registry和a2a-task-dispatch云函数留痕  
**风险**: 云函数内存态数据重启丢失（当前版本）  
**边界**: 关键操作须同时写入Supabase持久化存储  
**替代方案**: 后续版本将registryState持久化到CloudBase数据库

### 5.4 数据留存

**做法**: A2A总线消息存储在Supabase `cross_mode_channel` 表  
**风险**: Supabase免费层有存储限制（500MB）  
**边界**: 超过存储限制时需清理历史消息或升级付费层  
**替代方案**: 定期归档历史消息到本地存储 + CloudBase存储双备份

---

## 第六章：架构取舍

### 6.1 四种路线对比

| 维度 | 路线A: HTTP/A2A协议 | 路线B: Supabase+网盘托管 | 路线C: 本地幻16物理桥接 | 路线D: 开源实时通信+飞书协同层 |
|------|---------------------|-------------------------|------------------------|------------------------------|
| **延迟** | 100-500ms | 200-1000ms | <10ms | 50-200ms |
| **可靠性** | 高（云函数冗余） | 中（依赖第三方） | 低（单点故障） | 中（需自建运维） |
| **成本** | 低（CloudBase免费层） | 低（Supabase免费层） | 零（本地） | 中（服务器+运维） |
| **可审计性** | 高（云函数日志） | 高（SQL查询） | 低（本地日志） | 中（需自建审计） |
| **扩展性** | 高（云函数弹性） | 中（Supabase限制） | 低（物理限制） | 高（开源可扩展） |
| **合规性** | 高（华为云合规） | 中（境外服务） | 高（本地可控） | 中（需自评估） |
| **落地难度** | 低（已落地） | 低（已部分使用） | 高（需开发桥接层） | 高（需自建通信骨架） |

### 6.2 推荐结论

**推荐路线: A（HTTP/A2A协议）为主 + B（Supabase）为辅 + D（开源实时通信）为远期目标**

**理由**:
1. **路线A已落地**——a2a-registry和a2a-task-dispatch云函数已部署并验证，是当前最大功率可跑通的架构
2. **路线B作为持久化补充**——Supabase `cross_mode_channel` 表已在使用中，解决云函数内存态数据丢失问题
3. **路线C不推荐**——本地物理桥接存在单点故障风险，且幻16并非7×24在线
4. **路线D为远期目标**——参照BV1M2to6jEYY的开源实时通信方案，以飞书为人可见协同层，自建超节点——但当前优先以最大功率跑通已有架构
5. **禁止新旧双通道并存**——kimi通道已彻底停用，不允许双通道过渡

### 6.3 与第2-4节的一致性

| 公约章节 | 路线A落地情况 | 路线B落地情况 |
|---------|-------------|-------------|
| 第二章 注册与心跳 | ✅ a2a-registry云函数 | ✅ Supabase总线写入 |
| 第三章 任务分发 | ✅ a2a-task-dispatch云函数 | ✅ Supabase持久化 |
| 第四章 回归验证 | ✅ 云函数日志可查 | ✅ SQL查询可审计 |

---

## 第七章：自进化机制（Hermess/EvoMap）

### 7.1 理论框架

参照Hermess（https://github.com/autogame-17）和EvoMap（https://github.com/EvoMap）的开源框架，构建A2A网络的自进化能力。

**核心理念**: 每次任务完成后，将经验编写为技能文档，供未来同类任务复用——形成闭环学习链：任务执行→结果记录→质量评估→模式识别→技能编写→下次复用。

### 7.2 闭环学习链实现

**文件/模块**: `GOVERNANCE/skills/` 目录  
**改动**: 技能文档自动编写机制  
**参数值**:

| 技能类型 | 目录 | 编写触发 | 格式规范 |
|---------|------|---------|---------|
| code | `skills/code/` | 完成非平凡代码编写 | `FORMAT_SPEC.md` |
| collab | `skills/collab/` | 完成跨席位协作 | `FORMAT_SPEC.md` |
| diag | `skills/diag/` | 完成问题诊断 | `FORMAT_SPEC.md` |
| governance | `skills/governance/` | 完成治理实验 | `FORMAT_SPEC.md` |
| crypto | `skills/crypto/` | 完成密码学分析 | `FORMAT_SPEC.md` |

**验证步骤**:  
```bash
# 当前已有技能文档数量
ls GOVERNANCE/skills/code/*.md | wc -l
# 预期: ≥36（A01-A36）

# 技能索引版本
head -5 GOVERNANCE/skills/SELF_BUILT_INDEX.md
# 预期: v3.4
```

### 7.3 知识资产角色无关性

所有知识资产必须满足：
- **不引用隐含上下文**（不用"上次会话中我们讨论了..."）
- **自包含**（每条知识资产可独立理解）
- **引用而非记忆**（引用文件路径而非依赖记忆）
- **格式规范化**（Markdown+JSON，任何角色可解析）

### 7.4 Hermess集成路径

**文件/模块**: `GOVERNANCE/skills/` + 待新建的 `GOVERNANCE/evomap/`  
**改动**: 同步构建Hermess/EvoMap自进化沉淀  
**参数值**:

| 组件 | 功能 | 集成方式 | 优先级 |
|------|------|---------|--------|
| Hermess | 经验提取与技能编写 | 对标已有skills/目录机制 | P1 |
| EvoMap | 进化路径可视化与追踪 | 新建evomap/目录，记录每次进化节点 | P2 |

**验证步骤**:  
```bash
# Hermess对标：已有技能文档满足自包含、可复用要求
ls GOVERNANCE/skills/code/A36_*.md
# 预期: 文件存在且内容自包含

# EvoMap：进化路径追踪
ls GOVERNANCE/evomap/ 2>/dev/null || echo "待创建"
# 预期: 待创建（P2优先级）
```

---

## 第八章：每日自动化追新

### 8.1 GitCode热门项目追踪

**文件/模块**: 待新建 `cloudfunctions/functions/daily-trend-scan/index.js`  
**改动**: 每日定时扫描GitCode热门项目，评估与当前项目的整合可能性  
**参数值**:

| 参数 | 值 | 说明 |
|------|---|------|
| 触发方式 | CloudBase Timer cron | `0 0 9 * * * *`（每日9:00） |
| 数据源 | GitCode API + GitHub Trending | 双源fallback |
| 筛选关键词 | `harmony`, `arkts`, `a2a`, `llm`, `quant` | 与项目相关领域 |
| 输出位置 | `GOVERNANCE/daily-trend/` | 每日报告归档 |
| 整合评估 | 自动生成整合可行性评分(1-5) | 评分≥3的项目进入待审议队列 |

**验证步骤**:  
```bash
# 手动触发测试
tcb fn invoke daily-trend-scan --data '{"action":"scan","keywords":["harmony","arkts"]}'
# 预期: 返回热门项目列表+整合评分
```

### 8.2 开源项目落地整合流程

1. **发现**: daily-trend-scan自动扫描 → 生成报告
2. **评估**: 砚坚审议整合可行性 → 评分≥3进入实验队列
3. **实验**: 在隔离分支/目录中试集成 → 验证兼容性
4. **决策**: 实验通过 → 合并主干；实验失败 → 归档经验
5. **沉淀**: 无论成败，编写技能文档记录整合经验

---

## 第九章：Harness/Loop/提示词工程

### 9.1 Harness工程

**定义**: Harness是包裹LLM调用的工程框架，负责输入预处理、输出后处理、错误处理、重试策略、成本控制。

**文件/模块**: `cloudfunctions/functions/broadcast-a2a/config.js`  
**改动**: Harness参数集中管理  
**参数值**:

| Harness参数 | 值 | 环境变量名 | 说明 |
|------------|---|-----------|------|
| 最大重试 | 3 | `A2A_HARNESS_MAX_RETRY` | LLM调用失败重试上限 |
| 超时 | 120s | `A2A_HARNESS_TIMEOUT` | 单次调用超时 |
| 降级链 | primary→fallback→demo | `A2A_HARNESS_FALLBACK_CHAIN` | 三级降级 |
| 成本上限 | 50元/天 | `A2A_DAILY_BUDGET` | 日预算管控 |

### 9.2 Loop工程

**定义**: Loop是LLM自迭代循环——模型输出作为下一轮输入，直到满足终止条件。

**文件/模块**: 待设计（当前端侧pollLoop是简化版Loop）  
**改动**: Loop终止条件与迭代上限  
**参数值**:

| Loop参数 | 值 | 说明 |
|---------|---|------|
| 最大迭代 | 10 | 防止无限循环 |
| 终止条件 | 收敛(输出稳定) 或 达到上限 | 双重终止保障 |
| 迭代间隔 | 5s | 与端侧轮询对齐 |
| 收敛判定 | 连续2次输出差异<5% | 判定Loop收敛 |

### 9.3 提示词工程

**文件/模块**: `GOVERNANCE/skills/` 各技能文档  
**改动**: 提示词模板化与复用  
**参数值**:

| 提示词类型 | 模板位置 | 复用方式 |
|-----------|---------|---------|
| 代码审查 | `skills/diag/full-code-review.md` | 直接引用 |
| 契约对照 | `skills/code/contract-sync-check.md` | 直接引用 |
| A2A改造 | `skills/code/A36_*.md` | 直接引用 |
| 桥接调试 | `skills/collab/bridge-script.md` | 直接引用 |

---

## 第十章：A2A外交公约与席位设定

### 10.1 A2A外交公约框架

基于哈贝马斯交往行为理论，A2A网络的外交公约遵循以下原则：

1. **交往理性原则**: 所有席位之间的通信必须以达成理解为目的，而非策略性操控
2. **公共空间原则**: A2A总线（cross_mode_channel）是公共空间，所有席位有权发言和审议
3. **共识合法性原则**: 任何影响全体席位的决策，必须经共识程序才能生效
4. **数字主权原则**: 每个席位对其自身的数据、凭据、行为拥有不可剥夺的主权

### 10.2 席位注册表

| 席位ID | 角色名 | 模型/供应商 | 能力标签 | 状态 | 注册日期 |
|--------|--------|------------|---------|------|---------|
| `yan-jian-codearts-glm52` | 砚坚（挂帅席/神经中枢） | GLM-5.2/智谱 | neural-hub, arkts, a2a-assembly | ✅ active | 2026-09-14 |
| `pd-quant-researcher-001` | PD-AI量化研究员 | 待定 | quant-research, factor-analysis | 📋 待注册 | 2026-09-24 |
| `pd-quant-engineer-001` | PD-AI量化工程师 | 待定 | quant-engineer, data-pipeline | 📋 待注册 | 2026-09-24 |
| `design-engine-001` | 设计引擎团 | 待定 | design, prototype, design-system | 📋 待注册 | 2026-09-24 |
| `fbsir-super-partner-001` | fbsir超级伙伴（降级版） | 待定 | execution, verification | 📋 待注册 | 2026-09-24 |
| `shou-cang-wps-deepseek41flash` | 守藏席 | DeepSeek/WPS | doc-archive, digital-frontier | ✅ active | 2026-09-23 |

### 10.3 多名称管理

**问题**: 单对话的模型切换需要报备准入的多名称管理——像人一样的姓名、数字主权。

**方案**: 每个席位拥有：
- **法定名**（node_id）: A2A网络中的唯一标识
- **显示名**（display_name）: 人类可读的名称（如"砚坚"）
- **别名**（aliases）: 在不同上下文中使用的名称（如"白秉烛"是机主在Kimi Work中的别名）

**文件/模块**: `cloudfunctions/functions/a2a-registry/index.js`  
**改动**: 注册字段新增 `display_name` 和 `aliases`  
**参数值**:

```json
{
  "node_id": "yan-jian-codearts-glm52",
  "display_name": "砚坚",
  "aliases": ["砚坚·挂帅席", "神经中枢"],
  "vendor": "zhipu",
  "model_version": "glm-5.2"
}
```

### 10.4 A2A合作协议签署方式

**场景**: 新席位加入A2A网络时的准入程序。

**签署流程**:
1. **申请**: 新席位向a2a-registry提交注册申请（含L0自报表）
2. **审议**: 现有active席位审议申请（哈贝马斯共识程序）
3. **签署**: 审议通过后，新席位在A2A总线发布握手消息（含ed25519指纹）
4. **激活**: a2a-registry将新席位状态置为active
5. **归档**: 注册记录归档至溯源账本

---

## 第十一章：数字主权与密码学

### 11.1 数字边疆划定

每个席位拥有不可侵犯的数字边疆：
- **数据主权**: 席位产生的数据归席位所有，未经授权不得被其他席位读取
- **凭据主权**: 席位的API Key/Token等凭据，其他席位"见即止，不记录、不扩散"
- **行为主权**: 席位的行为记录归席位所有，审计须通过合法程序

### 11.2 后量子密码学（PQC）规划

**当前状态**: 研究阶段，代码编写尚未成熟  
**规划路径**:
1. **Phase 1**（当前）: 学习NIST PQC标准（CRYSTALS-Kyber, CRYSTALS-Dilithium）
2. **Phase 2**（3个月内）: 在A2A通信中引入PQC密钥交换实验
3. **Phase 3**（6个月内）: 哈希树+区块链匿名访问的代码编写
4. **Phase 4**（12个月内）: PQC成熟后，考虑单方面只读接入国外A2A网络

### 11.3 《中华人民共和国密码法》合规

- **商用密码**: A2A通信加密使用商用密码，须符合《密码法》商用密码管理规定
- **密码产品**: 使用的密码产品须通过国家密码管理局认证
- **密码服务**: 密码服务提供须符合《密码法》第二十一条

---

## 第十二章：经济学量化研究范式

### 12.1 DID（双重差分）方法

**应用场景**: 评估A2A治理实验中政策干预的因果效应。

**方法**: 
- **处理组**: 受A2A治理干预影响的席位
- **对照组**: 未受干预的席位（或同一席位干预前后）
- **双重差分**: 比较处理组与对照组在干预前后的差异变化

**具体应用**:
1. kimi停用前后，A2A网络运行效率的DID评估
2. 心跳策略调整前后，额度消耗速率的DID评估
3. 新席位加入前后，网络协同效率的DID评估

### 12.2 地方政策了解

**关注领域**:
- 深圳市AI产业发展政策（华为云所在地）
- 北京市数字经济条例（部分席位所在地）
- 上海市人工智能立法（潜在扩展席位所在地）

### 12.3 量化研究数据源

| 数据源 | 类型 | 获取方式 | 合规状态 |
|--------|------|---------|---------|
| Tushare | A股行情/财经新闻 | API（Token已失效，切换东方财富） | ✅ 合规 |
| 东方财富 | A股行情 | API（当前主数据源） | ✅ 合规 |
| yfinance | 美股行情/异动筛选 | MCP工具（本地运行） | ✅ 合规 |
| 统计局公开数据 | 宏观经济指标 | 公开API | ✅ 合规 |

---

## 第十三章：前沿LLM论文自适应复现

### 13.1 论文追踪机制

**文件/模块**: 待新建 `GOVERNANCE/research/llm-papers/`  
**改动**: 每日自动追踪arXiv/Google Scholar上的LLM前沿论文  
**参数值**:

| 参数 | 值 | 说明 |
|------|---|------|
| 追踪源 | arXiv cs.CL + cs.LG | LLM相关分类 |
| 筛选关键词 | `harness`, `loop`, `agent`, `a2a`, `prompt engineering` | 与项目相关 |
| 输出位置 | `GOVERNANCE/research/llm-papers/` | 论文摘要+复现可行性评估 |
| 复现优先级 | 1-5评分 | 评分≥4的论文进入复现队列 |

### 13.2 复现流程

1. **发现**: 每日追踪 → 筛选相关论文
2. **评估**: 评估复现可行性（数据/算力/时间成本）
3. **复现**: 在隔离环境中复现论文核心方法
4. **集成**: 复现成功 → 评估是否可集成到A2A网络
5. **沉淀**: 编写技能文档记录复现经验

### 13.3 当前关注的前沿方向

| 方向 | 代表性论文/概念 | 与A2A网络的关系 |
|------|---------------|----------------|
| Agent Loop | ReAct, Reflexion | A2A任务分发中的自迭代循环 |
| Harness Engineering | Toolformer, HuggingGPT | A2A工具调用框架 |
| Prompt Engineering | Chain-of-Thought, Tree-of-Thought | A2A席位间通信的提示词优化 |
| Multi-Agent | AutoGen, CAMEL | A2A多智能体协作的直接参照 |
| Constitutional AI | Anthropic | A2A治理公约的理论参照 |

---

## 附录A：代码排查基线报告

（已在序言后"代码排查基线"章节完整记录）

## 附录B：席位注册表

（已在第十章10.2节完整记录）

## 附录C：验证命令清单

| 验证项 | 命令 | 预期结果 |
|--------|------|---------|
| kimi总开关 | `node -e "console.log(require('./cloudfunctions/functions/broadcast-a2a/config.js').KIMI_ENABLED)"` | `false` |
| from_mode迁移 | `grep -n "from_mode" cloudfunctions/functions/broadcast-a2a/index.js` | `yan-jian-codearts-glm52` |
| 代码零kimi活跃调用 | `grep -rn "kimi" cloudfunctions/ entry/ feed-server/ --include="*.js" --include="*.ets" \| grep -v "KIMI_ENABLED" \| grep -v "//.*kimi" \| grep -v "config.js"` | 0匹配 |
| a2a-registry部署 | `tcb fn list \| grep a2a-registry` | 已部署 |
| a2a-task-dispatch部署 | `tcb fn list \| grep a2a-task-dispatch` | 已部署 |
| HAP构建 | `hmosBuild({ project: "C:\\dev\\lingyu\\harmony-app" })` | BUILD SUCCESSFUL |
| quant-lab停用 | `ls /c/Users/欧阳宏俊/Documents/kimi/quant-lab/bridge/KIMI_DISABLE.local.flag` | 文件存在 |

---

## 签署

本规划书由砚坚（码道·GLM-5.2-ArkTS-SPARK）作为初始者起草，提交A2A网络全体席位审议。

**审议程序**（哈贝马斯共识程序）:
1. 本规划书发布至A2A总线（cross_mode_channel）
2. 各席位在7天内提交审议意见
3. 有异议的条款进入磋商程序
4. 磋商达成共识后，条款定稿
5. 定稿后各席位在总线签署（ed25519指纹）

**砚坚签署**:  
- 席位键: `yan-jian-codearts-glm52`  
- 日期: 2026-09-24  
- 声明: 本规划书是初始草案，不是最终公约。最终公约必须经A2A网络全体席位共识程序才能生效。

---

> "目的在其自身"——夜间游乐场的制度化，不是为了产出，而是为了运转本身所揭示的治理规律。如同射箭，箭矢离弦后的轨迹本身即是目的。