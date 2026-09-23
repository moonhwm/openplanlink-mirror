# 状态管理审查——@State/@Prop/@Link 使用规范、数据流向、组件通信

## 一、审查范围与 ArkTS 状态管理基线

本篇为 harmony-app（代号铃语）状态管理层的审查知识资产。审查对象（均在本审查当日完整通读）：entry/src/main/ets/pages/Index.ets（459 行）、entry/src/main/ets/pages/Settings.ets（558 行）、entry/src/main/ets/entryability/EntryAbility.ets（124 行）、entry/src/main/ets/services/SettingsService.ets（456 行）。

ArkTS（状态管理 V1）基线：@State 组件内状态、@Prop 父到子单向拷贝、@Link 父子双向、@Provide/@Consume 跨层级、@Observed/@ObjectLink 对象级观察、AppStorage 应用级单例 KV、@StorageLink 双向挂接。审查方法：先盘点现状，再按"该用没用、用了没用对、没用但该引入"三问展开。一个重要的 grep 事实先行给出：**全仓 ets 源码中 @Prop、@Link、@Provide、@Consume、@Observed、@ObjectLink、@StorageLink、@Watch 的使用为零**（本次 grep 核实），即当前只有 @State + AppStorage 两件武器。

## 二、@State 现状盘点

Index（@Entry）持有 18 个 @State：items、playingId、loadingId、failedId、lastRefresh、connectionBroken、isDemoMode、fontLevel、elderlyMode、broadcastEnabled、broadcastOffVisible、themeMode、autoThemeEnabled、dndEnabled、dndActive、watchlist、readAlertIds、playHistory（Index.ets:28-45）；另有 4 个刻意非响应式的 private：timer、consecutiveFailures、navStack 及字号/间距 getter 依赖（:46-48 与 :51-96）。Settings（@Component）持有 10 个 @State（Settings.ets:11-22）。合计 28 个 @State，规模可控但已到该立规范的数量级。

**数组/对象变更纪律——做得对的地方：** 所有集合更新一律整体重赋值：this.items = filtered（Index.ets:178）、this.watchlist = [...this.watchlist, code]（Settings.ets:72）、this.readAlertIds = [...this.readAlertIds, item.alertId]（Index.ets:268-270）、this.playHistory = [historyItem, ...this.playHistory.filter(...)].slice(0, 50)（:280）。V1 的 @State 对数组仅观察第一层引用变化，push/splice 就地改不会触发刷新——本仓从未犯此错，ForEach 键函数也统一给足（Index.ets:425 以 alertId 为键、Settings.ets:410 以 code 为键），卡片复用身份正确。

**做了对的非响应式取舍：** timer 与 consecutiveFailures（:46-47）是纯逻辑变量，进 @State 只会白渲染，保持 private 正确。这是很多新手会犯而本仓没犯的坑。

## 三、数据流向审查：单向主干 + 事件回写

**读路径（服务 → 状态 → 视图）：** Preferences（SettingsService 持久化）→ Index.loadSettings()（Index.ets:118-136）批量拉 11 项配置写入 @State → build() 经字号 getter、主题 getter（:51-96）派生渲染。轮询数据流独立：pollLoop → refresh → AlertPoller.fetchLatest → this.items 整体替换（:146-200）。

**写路径（视图 → 状态 → 服务）：** Settings 页每个控件都是同一模式——先改自身 @State，再 await SettingsService.setXxx 落盘（如 toggleBroadcast，Settings.ets:84-88），无一例外。持久化层读写对偶完整（11 组 get/set，SettingsService.ets:83-373），杀进程可恢复。

**设置页与主页的状态同步机制（关键设计点）：** Index 与 Settings 是两个独立 struct，fontLevel/elderlyMode/themeMode 等各自持有**副本 @State**，互不 @Link。同步靠两个时机：Settings 建时 loadSettings 拉最新值（Settings.ets:43-45），返回主页时 Index.onPageShow 再拉一次（Index.ets:104-108，注释自证"设置页返回后刷新配置"）。**评价：** 在"零三方依赖 + 两页面"规模下，"副本 + onShow 重拉"比引入 @StorageLink 更简单直给，判定为合理现状；但它是隐式契约——任何新增设置项若忘记加进 Index.loadSettings，就会出现"设置页改了、主页不变"的脏读。第七节的规范条款正是为堵这个。

## 四、@Prop/@Link 缺位评估与抽取示例

当前零子组件、零 @Prop/@Link，卡片、顶栏全部内联在 Index.build() 里。缺位本身不是 bug，但 Index.build 已 150 行、卡片含 6 种状态组合（未读/播放/加载/失败/信号/普通），继续生长必然要抽 AlertCard 子组件。届时规范如下：

- **纯展示用 @Prop：** 卡片需要的 item（AlertItem）、未读、失败态，若纯由父驱动，用 @Prop 单向拷贝最不易错。

```typescript
@Component
struct AlertCard {
  @Prop item: AlertItem;
  @Prop isPlaying: boolean;
  onToggle: (item: AlertItem) => void;   // 回调上抛，父改 @State
  build() { /* … */ }
}
```

- **需要子改父（点卡播放、停止）走回调而非 @Link：** @Link 双向会让"谁改了 playingId"不可追踪，本应用播放态变更伴随 AudioPlayer 副作用，必须留在父层统一调度（现状 togglePlay 已把调度集中，Index.ets:225-287），子组件只上抛事件。
- **注意 @Prop 深拷贝成本：** AlertItem 是平面对象，拷贝代价可忽略；若未来 items 变深层嵌套，才考虑 @Observed/@ObjectLink。
- 本仓"零装饰器"与"回调上抛"的判断框架，比盲目上 @Link 更值得留档。

## 五、跨组件通信审查：AppStorage 信箱模式

**主信箱 pendingAlertId：** 三处写入（EntryAbility.ets:27 冷启动、:47 热启动、:93 前台推送）+ 一处读取并 delete（Index.checkPendingAlertId，Index.ets:138-144，在 aboutToAppear 与 onPageShow 双时机消费，:98-108）。用"读后即删"实现一次性消息，消费方两时机双保险，冷启动时序（AppStorage 先于页面创建存在）安全。这是本仓最规范的跨组件通信。

**两处死信号（本次 grep 全仓核实，写入方存在、读取方不存在）：**

- 'autoPlay'：EntryAbility.ets:66 在小艺 PLAY_AUDIO action 时 AppStorage.setOrCreate('autoPlay', true)，全仓无任何 get——直接播放意图丢失，自动播报实际靠 pendingAlertId + 默认开着的播报开关"碰巧"成立。
- 'xiaoYiQuery'：EntryAbility.ets:54 设置后无人读取，小艺查询异动摘要的 E1 能力处于半接线状态。

处置建议：短期删死信号防误导；实装小艺时在 Index.onPageShow 补消费逻辑（对齐 checkPendingAlertId 的模式），并把三个 AppStorage 键名收进常量文件，杜绝字符串散落。

## 六、@State 用的对与不对（问题清单）

- **对：** 集合整体重赋值纪律；ForEach 键函数齐备；timer/计数器不进 @State；派生值用 getter（theme、titleSize 等，:51-96）而非冗余 @State。
- **问题一（死状态）：** isDemoMode 声明 :34、置 false :156，build 从未读取——演示卡实由 items 初始值承担，该状态应删或实装为徽标。
- **问题二（派生冗余）：** broadcastOffVisible = !broadcastEnabled 仅在 loadSettings 赋值一次（:38、:122），运行期不会随 broadcastEnabled 变化（运行期它也确实不变），属可删的镜像状态；若未来主页内可切播报开关，它会静默失真——删除、模板里直接用 !this.broadcastEnabled。
- **问题三（隐式契约）：** 第三节所述"副本 + onShow 重拉"缺强制清单，建议 loadSettings 里 11 个 getter 顺序固化为检查表，新设置项必须同步登记两处。
- **问题四（粒度预警）：** 18 个 @State 平铺，尚可；再加 5 个以上应按"播放态/设置态/网络态"分三个 @Observed 类或干脆拆子组件，防一处变更全页重绘。

## 七、沉淀为本仓状态管理规范（六条）

1. 集合只整体重赋值，禁止 push/splice 触发刷新的写法；ForEach 一律给键函数（现有两处即范本）。
2. 纯逻辑变量（timer、计数、navStack）禁止 @State 化。
3. 派生值一律 getter，禁止镜像 @State（删 broadcastOffVisible、isDemoMode）。
4. 父子通信用 @Prop + 回调上抛；仅当父子共享可变配置时才用 @Link；跨页共享配置优先考虑 @StorageLink 接 AppStorage，替换"副本 + onShow 重拉"前须评估 loadSettings 全量重拉的代价（当前规模重拉更稳）。
5. AppStorage 键名集中常量化；一次性消息必须"读后即 delete"且消费方在 aboutToAppear 与 onPageShow 双时机兜底。
6. EntryAbility 写入的每个 AppStorage 键，必须有对应的消费方（grep 可验），消灭 autoPlay/xiaoYiQuery 类死信号。

## 八、验证清单

- [ ] grep @Prop/@Link 使用点与设计一致（现为零，引入时按第七条 4 审）
- [ ] grep 全部 AppStorage 键有读写配对
- [ ] 每个新设置项同时出现在 Settings 写路径与 Index.loadSettings
- [ ] ForEach 键函数覆盖率 100%
- [ ] 无 push/splice 就地改 @State 集合

### 自我评估
- 正确性：4分 全部行号来自本次实读四文件；"零装饰器/死信号/死状态"三个关键论断均有本次 grep 输出佐证；ArkTS V1 装饰器语义为官方文档通行口径，未在本环境编译验证，扣一分声明。
- 完整性：4分 覆盖盘点、流向、缺位评估、通信、问题清单与规范沉淀；@StorageLink 替代方案只给决策框架未给迁移代码（当前规模不推荐迁移，故不给）。
- 可复用性：4分 六条规范与验证清单可直接进 GOVERNANCE 技能库；"@Prop+回调优于@Link"的取舍逻辑适用于一切副作用型播放/下载场景。
- 字数：约3600字
- 使用模型：GLM-5.3-Flash
