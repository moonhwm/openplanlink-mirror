# A18｜init-db 云函数审查——数据库初始化逻辑、表结构、索引设计、初始化脚本

> 项目：harmony-app（铃语）。本篇自包含成文，结论全部来自本仓库源码逐行通读，引用给路径与行号；索引创建途径等平台行为处标注"以官方文档为准"。安全发现（硬编码凭证）只描述位置与处置办法，不在文中复述凭证值本身。

## 一、审查范围：一份云函数、两份实现、五份脚本的分叉现状

与"init-db"相关的初始化资产在仓库里有五处，先列清单再逐个审：

1. `cloudfunctions/functions/init-db/index.js`（61 行）——部署版。`cloudfunctions/cloudbaserc.json` 的 functions 列表登记了 `init-db`（timeout 30、installDependency true），CLI 从 functions/ 目录取码部署，**这份才是线上逻辑**。
2. `cloudfunctions/init-db/index.js`（40 行）——仓库根 cloudfunctions/ 下的历史残留版，逻辑不同（见 2.2），是分叉的直接证据。
3. `cloudbase-init.js`（39 行，仓库根）——用 `@cloudbase/manager-node` 的 `scf.database.createCollection`，但 `new CloudBase({ envId })` **未传任何凭证**（第 9-10 行），在需要鉴权的环境下必然失败。
4. `cloudbase-create-collections.js`（84 行，仓库根）——走 OpenAPI + 读取本机 `~/.cloudbase/config.json` 登录态，依赖执行机本地环境，不可移植。
5. `create-collections.mjs`（53 行，仓库根）——manager-node + **硬编码明文临时凭证**（第 6-10 行，secretId/secretKey/token 三件套直接写在源码里），详见第六节，这是本次审查的最高优先级发现。

五处做同一件事、五种实现、三种凭证来源——初始化这件事的第一问题不是代码，是治理。

## 二、初始化逻辑审查（部署版为主）

### 2.1 部署版主路径

`cloudfunctions/functions/init-db/index.js:15` 定义集合清单 `['alerts', 'user_stocks', 'user_preferences', 'tts_cache']`，主循环逐个 `db.createCollection(coll)`（第 22 行），成功记 `created`；catch 里判断错误信息含 `already exists` 或 `e.code === -502001` 则记 `already_exists`（第 29-31 行）——幂等语义正确，重复执行安全，这是本函数最值得肯定的设计。

### 2.2 兜底路径失效（代码级确认）

第 33-44 行的兜底逻辑：createCollection 抛出非"已存在"错误时，改试 `db.command({ create: coll })`，注释称之为"runCommand 方式（MongoDB 兼容）"。**这个兜底是无效代码**：`@cloudbase/node-sdk` 的 `db.command` 是查询指令构造器入口（用于 `_.inc`、`_.gt` 之类的操作符），不是透传 MongoDB 命令的 runCommand；把一个对象当函数调用 `db.command({...})` 会直接抛 `TypeError: db.command is not a function`，被内层 catch 捕获记为 `error`（第 43 行）。也就是说：凡是走到兜底分支的集合，结果必然是 error，返回体里的 `created_via_command` 状态在真实运行中不可能出现。修复：删掉这段兜底，把 createCollection 的真实错误码如实上抛或记录；若确需命令式建集合，唯一正路是 manager-node 的 `database.createCollection`（仓库根已有三份脚本在用），云函数内不必再造。

### 2.3 历史残留版的问题

`cloudfunctions/init-db/index.js:13` 用 `db.collection(coll).add({...})` 插入初始化文档来"创建"集合。CloudBase 文档数据库的集合原则上需先显式创建，向不存在集合 add 的行为在不同运行环境下不一致（部分环境报 -502003 集合不存在），**依赖 add 隐式建集合不可靠**；且它会给每个集合塞进一条 `{_init:true, note:...}` 脏文档，污染 count 验证（第 32-34 行的 verify 会把脏文档计入 total）。处置：整份删除或归档，避免后来者误把残留版当部署版再次部署，两份实现的行为差异（createCollection vs add）足以造成环境间数据形态不一致。

### 2.4 验证段

第 50-58 行逐集合 `count()` 验证并返回 `{collection, count}`，设计正确；配合 2.2 修复后，返回体 `results + verify` 就能完整回答"建了什么、成了没有、里面有多少东西"。建议补充一项：用 manager-node 在云端跑 `listCollections` 对账（本地脚本已有此逻辑，cloudbase-init.js:32-36），云函数内因权限面不同可不做，但人工验收步骤里应保留。

## 三、表结构审查：清单与实际使用脱节（核心发现）

### 3.1 四个集合的真实使用情况逐一核对

| 集合 | init-db 清单 | 实际被云函数使用？ | 证据 |
|---|---|---|---|
| alerts | 在 | **否**——alerts 数据全程走云存储文件 `alerts/alerts.json` | fetch-tushare-data/index.js:549-552（写）、get-alerts/index.js:32-34（读）、broadcast-a2a/index.js:32（读） |
| user_stocks | 在 | 否——自选股存端侧 Preferences | SettingsService.ets（端侧本地持久化，EntryAbility.ets:20 初始化注释"Preferences 持久化：自选股/播报开关/字体档"） |
| user_preferences | 在 | 否——同上，端侧本地 | 同上 |
| tts_cache | 在 | 否——generate-tts 的缓存是云存储 `tts-cache/{cacheKey}.json` 文件，不用数据库 | generate-tts/index.js:75、108 |
| push_tokens | **不在清单** | **是**——push-token-register 写入（index.js:26、43-49），broadcast-a2a 读取（index.js:122） | push-token-register/index.js、broadcast-a2a/index.js |

结论：**初始化清单创建的四个集合没有一个被任何云函数使用；唯一被使用的集合 push_tokens 反而不在清单里**。这意味着 push_tokens 集合至今只能靠手工在控制台创建——如果目标环境是全新的，push-token-register 第一次运行就会因集合不存在而失败（writes/queries on nonexistent collection），整条 Push 注册链路（端侧 PushService.ets:80-86 → 云函数 → 集合）在建库这一步就断。这是必须最先修的一处。

### 3.2 修正后的目标集合清单与文档结构

按"最小够用"原则重定清单——只建真实使用与明确规划的：

```js
const collections = ['push_tokens'];          // 当前必需
// 二期规划（A17/A20 联动的集合化改造）再加：
// const collections = ['push_tokens', 'alerts', 'tts_cache_meta', 'quota_daily'];
```

push_tokens 文档结构（现状字段 push-token-register/index.js:43-49 为 token/bundleName/createdAt/lastReportTs/active，建议扩展）：

```js
{
  _id: String,            // 建议：token 的 SHA256 前 16 位作主键，天然防重复
  token: String,          // 华为 Push Kit 设备 token（明文，属设备标识非密钥）
  bundleName: String,     // 包名，当前恒 'com.yehang.stockpulse'（PushService.ets:85）
  deviceModel: String,    // 可选：适老化排障有用
  active: Boolean,        // 默认 true；推送报失效错误码后置 false
  createdAt: String,      // ISO
  lastReportTs: Number,   // 毫秒时间戳，端侧每次冷启动上报刷新
  reportCount: Number,    // 上报次数，识别活跃设备
  lastPushError: String,  // 可选：最近一次推送失败码，供回收参考
}
```

若二期把 alerts 入库，文档结构即 `AlertItem`（entry/src/main/ets/model/AlertItem.ets:6-17：alertId/ts/symbol/name/direction/kind/headline/detail/audioUrl/complianceStatus），alertId 唯一键、ts 数字。user_stocks/user_preferences 两集合**建议从清单移除**：端侧已用本地 Preferences 实现，云端集合是为"多设备同步"预留的，当前产品无此诉求，留着只会诱惑后人造第二份事实源。

## 四、索引设计

init-db 现在完全不建索引（无任何 index 相关代码）。CloudBase 文档数据库不建索引时查询走全集合扫描，量小无感，量起即慢。按 3.2 的清单给出索引需求：

| 集合 | 索引 | 类型 | 服务场景 |
|---|---|---|---|
| push_tokens | token | 唯一 | ①防并发重复注册（A19 篇 4.2 的竞态）②注册时按 token 查重（push-token-register/index.js:29）从全扫变点查 |
| push_tokens | (active, lastReportTs) 组合 | 普通 | broadcast-a2a 拉活跃 token（broadcast-a2a/index.js:122）；过期清理任务按 lastReportTs 扫描 |
| alerts（二期） | alertId | 唯一 | upsert 写入与 audioUrl 单字段回写 |
| alerts（二期） | ts 降序 | 普通 | get-alerts 的 orderBy('ts','desc').limit(20) |
| quota_daily（二期） | date | 唯一 | 额度原子累加（A16 篇 6.3） |

创建途径说明（此处以平台官方文档为准）：node-sdk 不提供索引管理 API；实践路径有二——控制台手工建（一次性集合可接受），或 `@cloudbase/manager-node`/腾讯云 OpenAPI 的数据库索引管理接口编程创建（仓库根脚本已引 manager-node，加 `database` 索引调用即可）。注意唯一索引建前先清重：若 push_tokens 已因历史并发产生重复 token 文档，先跑去重脚本再建唯一索引，否则建索引本身会失败。

建议把索引创建并入 init-db 的职责（运维函数干运维活），部署版改造骨架：

```js
// 伪代码：createCollection 成功后接 createIndex（经 manager-node 或控制台预建并在此校验）
for (const idx of INDEX_PLAN[coll] || []) {
  // 校验索引存在，不存在则经 OpenAPI 创建；已存在跳过（幂等）
}
```

## 五、初始化脚本治理：统一为一

五处分叉的处置建议：保留两处——`cloudfunctions/functions/init-db/index.js`（云函数形态，幂等建集合+校验，修 2.2 后）与一份新的本地脚本 `scripts/init-db.mjs`；删除 `cloudfunctions/init-db/`（残留版）、`cloudbase-init.js`（无凭证必败）、`cloudbase-create-collections.js`（绑定执行机环境）、`create-collections.mjs`（涉密，见下节，删除前先完成凭证吊销）。`scripts/init-db.mjs` 的目标形态：

```js
// scripts/init-db.mjs —— 唯一权威初始化脚本
import CloudBase from '@cloudbase/manager-node';
const scf = new CloudBase({
  envId: process.env.TCB_ENV,
  secretId: process.env.TCB_SECRET_ID,     // 全部走环境变量，禁止入库
  secretKey: process.env.TCB_SECRET_KEY,
});
// 1) listCollections 对账  2) createCollection（幂等捕获 DATABASE_COLLECTION_EXISTS）
// 3) 建索引（幂等）        4) 打印 results/verify 终态
```

## 六、安全红线发现：create-collections.mjs 硬编码云凭证

`create-collections.mjs:6-10` 将腾讯云临时凭证三件套（secretId、secretKey、session token）**明文硬编码在源码中**，且该文件随仓库持久化。对照共享合规红线"不泄露任何 Token/密钥"，这构成已发生的事实违规，无论凭证是否过期都应按泄露处置。处置步骤（按序）：①立即在腾讯云访问管理控制台**吊销/禁用该子账号密钥**（临时凭证等待其自然过期前，先收窄其权限策略为只读或禁用）；②从仓库删除该文件，并检查它是否曾被提交进任何远端历史（有则需清理历史或接受"凭证已吊销"的结论）；③本篇与任何后续文档一律不得复述凭证值，仅以"create-collections.mjs 第 6-10 行的已吊销凭证"指代；④以本篇第五节的环境变量方案重建脚本。另注意 `cloudbase-create-collections.js` 读取 `~/.cloudbase/config.json` 登录态的做法本身合规（凭证在用户目录不入库），可作为环境变量之外的备选，但该文件绑死本机 Node 路径（第 24 行硬编码 `C:/Users/欧阳宏俊/nodejs/...`），仍建议废弃重写。

## 七、初始化检查清单（验收用）

目标环境每次初始化/迁移后按此单验收：

1. 集合存在：push_tokens（必需）、二期规划的 alerts 等；
2. 索引存在：push_tokens.token 唯一、(active,lastReportTs) 组合；alerts.alertId 唯一、ts 降序；
3. 安全规则：push_tokens 端侧不可直读直写（只允许云函数管理态访问；HTTP 注册入口是唯一写通道）——CloudBase 集合默认权限可能放开客户端读写，必须在控制台收紧，此项 init-db 代码管不到，列清单人工确认；
4. 触发器：fetch-tushare-data 的定时触发器已配置（其 index.js:10 注释声明依赖定时触发）；
5. 环境变量：各函数 envVariables 已注入（cloudbaserc.json 中 TUSHARE_TOKEN/DASHSCOPE_API_KEY 等当前为空串，属已知未配置态，不属 init-db 职责但验收单上需区分"库没建"与"配置没给"）；
6. 冒烟：调 init-db 一次应全部 already_exists 且 verify.count 无 error。

## 八、修复优先级清单

| 级别 | 事项 | 位置 | 依据 |
|---|---|---|---|
| P0 | 吊销 create-collections.mjs 内硬编码凭证并删除该文件 | create-collections.mjs:6-10 | 六，安全红线 |
| P0 | 集合清单加入 push_tokens（或控制台立即手工创建） | functions/init-db/index.js:15 | 3.1，Push 链路建库缺失 |
| P1 | 删除 db.command 兜底死代码 | functions/init-db/index.js:33-44 | 2.2 |
| P1 | 归档删除残留版与两份废脚本 | cloudfunctions/init-db/、cloudbase-init.js、cloudbase-create-collections.js | 一/2.3 |
| P1 | push_tokens 唯一索引 + 组合索引（先去重后建索引） | 第四节 | 四 |
| P2 | 新建 scripts/init-db.mjs 统一脚本（环境变量凭证） | scripts/（新建） | 五 |
| P2 | 集合清单瘦身：移除 user_stocks/user_preferences | functions/init-db/index.js:15 | 3.2 |
| P3 | 二期 alerts 集合化 + 索引随 A17/A20 落地 | 联动 | 3.2/四 |

## 九、未实测项

未做：云端实调 init-db 验证 -502001 错误码匹配（本地无凭证）；索引管理接口的具体函数签名（标注"以官方文档为准"，脚本骨架为伪代码）；push_tokens 集合在目标环境的现存状态（可能已手工建过，P0 第二项施工前先 listCollections 对账）。以上均如实标注。

### 自我评估
- 正确性：5分 "清单四集合无一被用、实际所需 push_tokens 不在清单"由六文件交叉核对得出；db.command 兜底失效为 node-sdk API 语义判断；安全发现给出位置与处置且不复述凭证。
- 完整性：4分 覆盖初始化逻辑、表结构、索引、脚本治理、验收清单；索引 API 具体签名未展开（已标注）。
- 可复用性：4分 优先级清单可当工单，目标文档结构与脚本骨架可直接施工；索引创建需按平台文档二次确认。
- 字数：约5100字
- 使用模型：GLM-5.3-Flash
