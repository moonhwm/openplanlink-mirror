# A19｜push-token-register 云函数审查——Push Token 注册流程、存储、更新机制

> 项目：harmony-app（铃语，鸿蒙适老化股票异动播报）。本篇自包含成文，结论全部来自本仓库源码逐行通读，引用给路径与行号；华为 Push Kit token 生命周期相关行为处标注"以华为官方文档为准"。

## 一、审查范围与端侧契约

审查对象：`cloudfunctions/functions/push-token-register/index.js`（95 行，全文通读）与同目录 package.json（仅依赖 `@cloudbase/node-sdk ^3.0.0`）。参照物：部署配置 `cloudfunctions/cloudbaserc.json`（push-token-register 段：Nodejs18.15、timeout 10 秒、无环境变量）；端侧唯一调用方 `entry/src/main/ets/services/PushService.ets`（107 行）；下游消费方 `cloudfunctions/functions/broadcast-a2a/index.js`（293 行）；建库方 `cloudfunctions/functions/init-db/index.js`。

端侧契约（PushService.ets:11、80-86）：POST 到 `https://a2a-commonwealth-d2eepjr928e9c4d.service.tcloudbase.com/push-token-register`，`Content-Type: application/json`，body 为 `{ token, bundleName: 'com.yehang.stockpulse' }`。超时 connect/read 各 5000ms，失败仅记日志不影响主流程（PushService.ets:77-97）。云函数头注释（index.js:9-12）声明同一契约，两侧一致。

## 二、注册流程审查

### 2.1 现有流程逐步拆解

main（index.js:72-92）：解构 `event.token/bundleName` → 非空校验（77-83）→ 调 `registerToken`（85-87）→ 返回 `{success, action, docId}`。`registerToken`（index.js:21-52）：`where({token}).get()` 查重 → 命中则 `doc(docId).update({lastReportTs, updatedAt})` 并返回 action='updated'（31-40）→ 未命中则 `add({token, bundleName, createdAt, lastReportTs, active:true})` 返回 action='created'（42-51）。日志对 token 做 `substring(0,20)` 脱敏（38、50）——脱敏意识正确。

event 解析的一个前提值得固化：该函数经 HTTP 访问服务触发，端侧以 `application/json` 请求体提交，CloudBase 会把 JSON body 解析后作为 event 传入（端侧 PushService.ets:84 已正确设置该头）。若未来有非 JSON 调用方直连，`event.token` 将恒为 undefined 并落入 77 行的校验拒绝——这是当前实现能安全兜住的形态，但应在文档里写明"只接受 JSON body"，避免后人改契约时踩空。

### 2.2 流程缺陷清单

1. **无 token 格式校验**：任何非空字符串都入库。华为 Push Kit 的 token 是定长格式串（以官方文档为准，长度量级在百字节），至少加长度区间与字符集校验，把脏数据挡在门外。
2. **无 bundleName 白名单**：端侧恒传 `com.yehang.stockpulse`（PushService.ets:85），服务端却接受任意值。加白名单一行代码即可把"任意第三方构造的注册请求"挡掉大半。
3. **查重-插入非原子**：29 行查重与 43 行插入之间存在竞态窗口。同一设备并发上报（如冷启动 PushService.init 与用户手动触发并存）、或两端网络重发，都会造出重复 token 文档。后果：broadcast-a2a 推送时同 token 收双份通知——对适老化用户是"铃响了两次"的体验事故。
4. **无频控**：公网可无限频调用，虽只写库不发推送，但可灌满集合。
5. **重复注册的更新语义偏弱**：重复路径只刷新 lastReportTs/updatedAt（34-37），不刷新 bundleName、不累计 reportCount——bundleName 理论上不变，可接受；但缺 reportCount 使后续"活跃设备统计"无从做起。

修复示例（2.2-3 的原子化，两选一）：

```js
// 方案A：token 指纹作主键的幂等 upsert（推荐，配唯一索引见 A18 篇四）
const fingerprint = crypto.createHash('sha256').update(token).digest('hex').substring(0, 16);
await collection.doc(fingerprint).set({   // set 为整文档覆盖写，天然幂等
  token, bundleName, active: true,
  createdAt: new Date().toISOString(),
  lastReportTs: Date.now(),
}, { upsert: true });                     // node-sdk doc().set upsert 能力以官方文档为准
// 方案B：保留查重-插入，但 token 建唯一索引，插入冲突时捕获后转 update
```

## 三、存储审查

### 3.1 集合与字段现状

存储集合 `push_tokens`（index.js:26）。**交叉发现（与 A18 篇联动）**：init-db 的集合清单是 `['alerts','user_stocks','user_preferences','tts_cache']`（init-db/index.js:15），**不含 push_tokens**——而全仓库唯一真正被读写的集合恰是它（push-token-register 写、broadcast-a2a/index.js:122 读）。新环境部署时 push_tokens 只能手工建，漏建则注册链路直接报错。这是存储层的 P0 修复项：要么把 push_tokens 加进 init-db 清单，要么控制台立即手工创建。

字段现状 `{token, bundleName, createdAt, lastReportTs, active}`。评估：最小可用，缺三样——设备维度（同一账号多设备/重装场景无法区分）、上报次数、失效原因记录。建议的目标结构已在 A18 篇 3.2 给全（tokenFingerprint 主键/deviceModel/reportCount/lastPushError），此处不重复，只强调一条原则：**token 明文存库可以接受**（它是推送地址不是密钥，合规红线管的是 API key/secret 一类凭证），但日志脱敏（现有 substring(0,20)）与集合权限收紧（安全规则禁止客户端直读，只留云函数管理态）必须配齐，防止 token 集合被第三方拉走后定向推垃圾消息。

### 3.2 查重查询的成本

`where({token}).get()` 无索引时全集合扫描（A18 篇四已列 token 唯一索引方案）。当前设备量个位数无感；该查询也可换成 `where({token}).count()` 先判存在再操作，但不如直接上唯一索引 + upsert 一劳永逸。

## 四、更新机制审查

### 4.1 更新路径现状

现有更新只有一条：重复 token 刷 lastReportTs（2.1）。缺失的三条更新路径才是本函数的核心欠账：

1. **失效回收（对端是华为侧错误码）**：Push Kit 的设备 token 在卸载重装、清除应用数据等场景会失效/更换（以华为官方文档为准）。失效 token 留在库中且 active:true，broadcast-a2a 每次广播都会向它发推送（broadcast-a2a/index.js:186-204），华为侧返回失败错误码，白白消耗推送配额并污染日志。正确闭环：broadcast-a2a 推送失败且错误码属"token 无效"类时，回写该 token 的 active:false；本函数应暴露这一能力（加 `deactivate` 动作或单独函数），并配一个按 lastReportTs 的定时清理（如 90 天未上报置 inactive——设备长期不打开 App 时其 token 不值得继续推）。
2. **重装换 token 的收敛**：同一设备重装后产生新 token，旧 token 若只靠"推送失败回收"会有一个广播周期内的双推窗口；若端侧在上报时附带旧 token（或设备唯一标识）做关联迁移，可即时 deactivate 旧档。当前端侧 PushService.ets 未传设备标识，属可选优化，非必须。
3. **active 标志的写入入口**：现库中 active 恒为 true（index.js:48），无任何代码会写 false——"支持 token 过期更新与设备去重"（index.js:7）这句头注释承诺的能力，实际只落地了去重的一半。

### 4.2 getActiveTokens 导出无效（代码级确认）

index.js:58-67 定义并第 95 行导出 `getActiveTokens`，注释称"供 broadcast-a2a 云函数调用"。**这个导出在跨函数场景下不可达**：callFunction 只能触发目标函数的 main 入口（event/context 传入 main），无法调用其模块级导出；而 broadcast-a2a 的实际实现也确实没走这条路，是直接查库（broadcast-a2a/index.js:119-123）。结论：`exports.getActiveTokens` 是死代码，且注释有误导性。处置：删除导出或改注释为"供函数内/未来 HTTP 查询用"；若真要做跨函数读 token，保持现状直查库即可（同库低频读，无需中转一跳）。

## 五、鉴权与滥用防护

该函数是全仓库攻击面最宽的入口之一：公网可达、无鉴权、无频控、写入不可逆（只增不减）。最现实的攻击是垃圾注册——灌入大量伪造 token，broadcast-a2a 广播时全部携带（broadcast-a2a/index.js:183 `token: deviceTokens` 是数组整体下发），华为侧对无效 token 返回错误，虽然不至于推送成功，但会持续烧推送配额并触发华为侧风控（以官方文档为准）。防护组合拳（按性价比排序）：

1. bundleName 白名单（2.2-2，一行）；
2. token 格式校验（2.2-1，两行）；
3. 单 token 上报频控：同 fingerprint 一小时内重复上报直接短路返回成功（既防刷又符合"端侧每次冷启动都上报"的真实频率——冷启动上报本就该幂等短路）；
4. 可选：HTTP 访问服务层对 /push-token-register 路径限流，与 get-alerts 的限流策略统一配置。

合规面核对：本函数无任何密钥/凭证处理（依赖 CloudBase 管理态鉴权），日志脱敏已有，白名单校验后也不会成为对外公开的数据通道——满足共享红线"不泄露任何 Token/密钥、不涉对外公开"。

## 六、端侧协同与降级链路

注册链路的完整生命周期（端侧视角，供联调对照）：EntryAbility.ets:16 冷启动调 PushService.init → probeAgcConfig 探测 agconnect-services.json（PushService.ets:99-106）→ **AGC 未配置则静默降级为轮询**（PushService.ets:31-33，本函数零流量，符合共享约束"PushService 保持占位封装，AGC 未配置前降级轮询"）→ 配置到位则 getToken（46-58）→ 可重试错误码（1000900001 等四种，第 14 行）最多 3 次、间隔 1s（14-16、63-71）→ reportToken POST（77-97）。两侧超时对齐检查：端侧 readTimeout 5000ms（PushService.ets:84），云函数 timeout 10 秒（cloudbaserc.json）——端侧会先超时，云函数还在跑完注册，结果不丢只是端侧不确认，语义安全。但有一个真实缺口：**reportToken 失败后无补报机制**（PushService.ets:89-91 仅记日志，tokenReported 置 false 后无人再触发），冷启动恰逢弱网则该设备在下次冷启动前收不到推送。建议端侧补一条：上报失败把 token 存入本地 Preferences，下次任意时机（前台恢复/轮询成功后）重试一次——改动小，收益直接。

另核对 broadcast-a2a 的容错衔接：云函数读库失败时有 env 单 token 兜底（broadcast-a2a/index.js:124-129 的 HUAWEI_PUSH_TOKEN），注册链路故障不会立即断推送——这是链路上现成的降级设计，保持即可。

## 七、修复优先级清单

| 级别 | 事项 | 位置 | 依据 |
|---|---|---|---|
| P0 | push_tokens 纳入 init-db 清单（或控制台立即建集合） | init-db/index.js:15 | 3.1，链路建库缺失 |
| P0 | bundleName 白名单 + token 格式校验 | index.js:75-83 | 2.2-1/2、五 |
| P1 | token 唯一索引 + 指纹主键 upsert 消竞态 | index.js:21-52；A18 篇四 | 2.2-3，双推事故 |
| P1 | 失效回收：broadcast 推送失败回写 active:false + 90 天未上报清理 | index.js（新增 deactivate）；broadcast-a2a/index.js:195-201 | 4.1-1 |
| P1 | 单 token 频控短路 | index.js:main | 五-3 |
| P2 | 字段扩展 reportCount/deviceModel/lastPushError | index.js:43-49 | 3.1 |
| P2 | 删除 getActiveTokens 死导出或改注释 | index.js:58-67, 94-95 | 4.2 |
| P2 | 端侧补报机制（失败 token 本地暂存重报） | PushService.ets:77-97 | 六 |
| P3 | 集合安全规则收紧（禁客户端直读写） | 控制台 | 3.1 |

## 八、未实测项

未做：云端实调（无测试设备 token，无法验证注册-推送全链路）；华为 Push Kit 失效错误码的具体码表（"推送失败回写 inactive"的匹配规则需按官方文档施工，本文只定机制不定码表）；node-sdk doc().set 的 upsert 支持形态（方案A 施工时以官方文档为准，方案B 为保底路径）。以上均如实标注，未作为已验证结论。

### 自我评估
- 正确性：4分 流程拆解与竞态、死代码、清单缺集合三处发现均有行号级证据；华为侧行为与 SDK upsert 细节如实标注未实测。
- 完整性：4分 覆盖注册流程、存储、更新机制、鉴权防护、端侧协同全链；未展开华为错误码码表与多设备同步方案。
- 可复用性：4分 P0-P3 清单与修复片段可直接施工，与 A18/A20 的联动边界写明；方案A 需按平台文档二次确认。
- 字数：约5000字
- 使用模型：GLM-5.3-Flash
