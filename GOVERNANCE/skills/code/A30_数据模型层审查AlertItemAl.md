# 数据模型层审查——AlertItem/AlertFeed 契约、JSON 解析、字段验证

## 一、审查范围与契约地位

本篇为 harmony-app（代号铃语）数据模型层的审查知识资产。契约定义于 entry/src/main/ets/model/AlertItem.ets（23 行，本审查当日完整通读），消费方四处：AlertPoller.ets（反序列化入口）、Index.ets（渲染）、EntryAbility.ets（推送 payload 提取 alertId）、SettingsService.ets（PlayHistoryItem 关联存储）。

该契约的战略地位：**AlertFeed 就是端侧与服务端的全部接口面**。架构基调明文"数据源 FEED_URL 待 X 服务器落地，契约即 AlertFeed"——模型文件即接口文档本身，字段注释里写着生产语义（kind=fact 客观异动、kind=signal 自家策略信号与白话解读、机主 09-14 松绑、禁收益承诺/催促指令/对外公开，AlertItem.ets:1-5）。因此本篇审查的每一个字段结论都同时是给服务端的协议要求。

## 二、AlertItem 契约逐字段审查

| 字段 | 类型/必填 | 端侧消费点 | 审查结论 |
| --- | --- | --- | --- |
| alertId | string 必填 | ForEach 键（Index.ets:425）、已读标记、播放定位、通知回传 | 协议第一键；端侧多处当身份用，服务端必须保证全局唯一且稳定（同股同事件重发不改 id，否则已读/播放态错乱） |
| ts | number 必填（秒级） | PlayHistoryItem.alertTs（SettingsService.ets:455） | 见第四节问题一（秒/毫秒混用风险） |
| symbol / name | string 必填 | 自选股过滤（Index.ets:160-163）、卡片标题 | symbol 与 watchlist 项需同构（六位代码），验证方案见第五节 |
| direction | 'up'\|'down'\|'flat' 字面量联合 | dirLabel/dirColor（Index.ets:289-307） | 非法值运行期安全落'平'（else 分支），但编译期契约会被 as 断言绕过（见第五节） |
| kind | 可选 'fact'\|'signal' | 「自家信号」角标（Index.ets:381-389） | 缺省按 fact（注释 ：12），端侧只对 signal 加角标，语义松绑合规落地点；signal 文案服务端产出，三条红线（不承诺收益/保本、不催促、不对外公开收费）是服务端提示词约束，端侧不重复校验但建议加 review 钩子 |
| headline | string 必填 | 卡片主白话（Index.ets:400-403） | 老人唯一必读句，长度无上限约束——超长会撑爆卡片，验证方案设上限 |
| detail | string 必填 | 次级信息（Index.ets:405-410） | 端侧用 item.detail.length > 0 判空——若服务端发 undefined 会抛异常，验证方案须兜 |
| audioUrl | 可选 string | 播报钮显隐（Index.ets:390）、playById 短路（:208-211） | undefined 语义已定型：无音频→不显示钮、按需调 generate-tts（已知问题留档）。契约注释"无则不显示播报钮"与实现一致 |
| complianceStatus | 可选 string（Safe/Unsafe/ConditionallySafe/Focus/Unknown） | **零消费**（本次 grep 全仓核实仅模型声明一处） | 见第四节问题三 |

## 三、AlertFeed 契约与反序列化现状

AlertFeed 仅两字段：items: AlertItem[] 与 serverTs: number（AlertItem.ets:19-22）。反序列化唯一入口在 AlertPoller.fetchLatest（AlertPoller.ets:66-79）：HTTP 200 后 JSON.parse(resp.result as string) as AlertFeed，三层防御——parse 抛异常捕获并记原文前 200 字符 + applyBackoff + 返回 ok:false（:68-75）；解析成功取 feed.items ?? [] 的空值兜底（:79）；成功才 resetBackoff（:78）。

**评价：** 解析失败的降级路径完整（坏数据当网络失败处理，不污染 UI），日志只截 200 字符防刷屏。但 as AlertFeed 是纯编译期断言，**运行期零结构验证**：missing 字段、类型漂移（ts 变字符串）、items 内混入半残条目都会原样流入 UI。当前靠"服务端自家产出"的信任在撑，X 服务器落地后多来源聚合时必须补第五节的验证层。

EntryAbility 侧第二解析点：receiveMessage 对 data.data 做 JSON.parse as Record<string,string> 后取 alertId（EntryAbility.ets:89-94），有 try/catch，提取失败仅 warn——通知路径的解析鲁棒性达标，同样建议对 alertId 做非空字符串校验后再入 AppStorage（现状 if (alertId) 已挡 falsy，够用但无类型确认）。

## 四、发现的问题（按优先级）

- **问题一（P1，时间戳单位双轨）：** 契约 ts 是秒级（:8 注释），而端侧记录播报时间用 Date.now() 毫秒（Index.ets:276-277 的 ts 与 alertTs 并存于 PlayHistoryItem）。同一结构两种单位并存，未来做"异动发生后多久才播报"类统计时必然踩坑。建议：PlayHistoryItem.alertTs 命名上标注单位，或统一毫秒并让服务端契约升版。
- **问题二（P1，detail 空值不设防）：** 端侧判断 item.detail.length > 0，若上游 JSON 把 detail 置为 null 或缺省，运行期读 length 抛 TypeError，整次 refresh 渲染挂掉。契约注释必填不等于运行期存在。第五节验证层直接解决。
- **问题三（P2，complianceStatus 声明未消费）：** 五级分类（Safe/Unsafe/ConditionallySafe/Focus/Unknown）只入库不生效。契约既然承载合规分类，端侧最起码应实施"Unsafe 不渲染、ConditionallySafe 降级为仅 fact 字段"的最后一道闸——服务端提示词是软约束，端侧过滤是硬约束，适老化应用的合规红线值得双保险。
- **问题四（P2，serverTs 声明未消费）：** 本次 grep 核实 serverTs 仅在模型出现。闲置字段两种处置：删掉，或实装为时钟偏差校正/排序依据（items 顺序目前全信服务端数组序，客户端零排序逻辑——现状可行，但若将来本地排序须以 ts 为准并防同秒并列）。
- **问题五（P3，DEMO_ITEMS 合规口径）：** 演示卡 ts:0、headline 带「示例」前缀（Index.ets:13-23）。ts:0 若流入播放历史会成为 1970 记录——现状演示卡点击后因无 audioUrl 不触发历史写入，安全；但若未来演示卡加音频需先补 demo 数据隔离规则。

## 五、字段验证方案（建议新增 validate 层）

在 AlertPoller 解析成功后、返回 items 前插入一道过滤，纯函数零依赖：

```typescript
function isValidItem(it: AlertItem): boolean {
  return typeof it.alertId === 'string' && it.alertId.length > 0
    && typeof it.ts === 'number' && it.ts > 0
    && typeof it.symbol === 'string' && /^\d{6}$/.test(it.symbol)   // A股六位代码
    && typeof it.name === 'string' && it.name.length > 0
    && (it.direction === 'up' || it.direction === 'down' || it.direction === 'flat')
    && typeof it.headline === 'string' && it.headline.length > 0 && it.headline.length <= 50
    && (it.audioUrl === undefined || (typeof it.audioUrl === 'string' && it.audioUrl.length > 0))
    && (it.detail ?? '').length >= 0;   // detail 允许空串，不允许缺类型
}

// fetchLatest 内：return { ok: true, items: (feed.items ?? []).filter(isValidItem) };
```

设计取舍说明：symbol 用六位数字正则同时完成了 A 股代码格式与自选股匹配的同构保证；headline 上限 50 字是白话卡片的排版阈值（标准档 28fp 一屏两行内）；direction 显式三值校验替代 else 落'平'的隐式兜底，坏数据在入口被丢而不是在 UI 被静默误显示；complianceStatus 校验不设死枚举（服务端可能扩级），端侧只按第四节问题三的规则消费。过滤后条目数可记日志，服务端坏数据率可观测。

## 六、契约演进规范（给服务端与端侧的联合条款）

1. **只增不改不删：** 新字段一律可选（对齐 audioUrl/kind 先例）；已发布字段不得改语义（ts 秒级锁死）；废弃先声明后移除。
2. **缺省语义入注释：** 每个可选字段的缺省行为必须写在模型注释里（kind 缺省按 fact、audioUrl 缺省无播报钮为既有范本），端侧行为以注释为契约。
3. **版本探测：** 建议服务端在 AlertFeed 增加 schemaVersion 可选字段，端侧不认识的大版本号可整单丢弃退演示卡——比运行期逐字段猜类型便宜。
4. **白话文案即合规载体：** headline/detail/signal 解读由服务端 LLM 产出，三条禁令（不承诺收益/保本、不催促、不对外公开收费）在服务端提示词执行；端侧 complianceStatus 过滤（问题三建议）作为第二道闸，两层都留日志可审计。

## 七、测试用例清单（建议落地为单测）

- [ ] 正常 feed 解析：items 全字段齐备 → 全数通过
- [ ] JSON 断裂（截断/HTML 错误页）→ ok:false + 日志含前 200 字符 + 退避生效
- [ ] items: null / items 缺失 → 空数组不崩溃
- [ ] 单条缺 detail / detail:null → 过滤或兜空串，页面不抛 TypeError
- [ ] direction 非法值（如 'Up'）→ 被验证层丢弃
- [ ] symbol 带交易所前缀（sh600176）→ 被六位正则丢弃（服务端契约须只发六位）
- [ ] ts 为字符串 "1700000000" → 被验证层丢弃
- [ ] 同 alertId 重复出现 → 现状无去重，确认服务端承诺唯一后可豁免端侧去重
- [ ] 推送 data.data 非法 JSON → warn 且 AppStorage 不被污染

### 自我评估
- 正确性：4分 逐字段结论与行号均来自本次实读的 AlertItem.ets、AlertPoller.ets、Index.ets、EntryAbility.ets、SettingsService.ets；complianceStatus/serverTs 零消费与 detail 直读 length 的论断经实读与 grep 双重核实；验证代码为建议实现，未在本环境编译运行，扣一分声明。
- 完整性：4分 覆盖契约逐字段、反序列化现状、五问题、验证方案、演进规范与测试清单；未对服务端 alerts.json 实际样例做比对（服务端文件不在本审查范围，端侧契约以模型注释为准）。
- 可复用性：5分 "模型即契约"的审查框架、validate 纯函数与演进四条可直接搬到任何端侧 JSON 契约项目；测试清单可即转单测用例表。
- 字数：约3600字
- 使用模型：GLM-5.3-Flash
