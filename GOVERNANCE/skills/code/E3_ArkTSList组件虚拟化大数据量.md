# ArkTS List 组件虚拟化——大数据量渲染、LazyForEach、缓存计数、滑动性能

> 适用项目：harmony-app（铃语，适老化股票异动播报），Index.ets 主页面为 List 卡片流（28-34fp 大字白话卡片），5s 前台轮询 AlertPoller 兜底刷新。
> 本文归档于 `GOVERNANCE/skills/code/`，与 `A23_Indexets审查List卡片流渲.md`（页面审查）、`A34_性能审查List虚拟化图片懒加载渲染.md`（性能审查）、`E2_ArkTSComponentV2与O.md`（状态粒度）联动。API 行为按 ArkUI List/LazyForEach 公开文档口径书写，性能数字类结论以 DevEco Profiler 真机实测为准。

---

## 一、List 虚拟化的事实基础：容器懒、迭代器不懒

先纠正最常见误解：**List 容器本身是按需布局的，但子项构建多少取决于迭代器。**

- List 只为可视区域附近的 ListItem 申请布局与渲染资源；
- `ForEach` 在**首次渲染时一次性构建全部子项**——数据 1000 条就建 1000 个 ListItem，"容器懒"被"迭代器勤"抵消，大数据量下首帧被拖垮；
- `LazyForEach` 配合 `IDataSource` 才是完整虚拟化：**屏幕外条目不构建，滚动到附近才按需创建，滑远后销毁**。

结论一句话：**超过几十条的数据源，一律 LazyForEach；ForEach 只用于已知很小的常量集合。** 铃语异动流是轮询增长型列表（开盘时段持续追加），属于必须 LazyForEach 的场景。

## 二、IDataSource：虚拟化的数据契约

LazyForEach 不接受裸数组，要求实现 `IDataSource` 接口：`totalCount()`、`getData(index)`、`registerDataChangeListener(listener)`/`unregister()`。框架靠它问"一共几条、第 N 条是什么"，靠 listener 通知"数据变了、变在哪"。

```ts
class AlertDataSource implements IDataSource {
  private items: AlertItem[] = []
  private listeners: DataChangeListener[] = []

  totalCount(): number { return this.items.length }

  getData(index: number): AlertItem { return this.items[index] }

  registerDataChangeListener(l: DataChangeListener): void {
    this.listeners.push(l)
  }

  unregisterDataChangeListener(l: DataChangeListener): void {
    this.listeners = this.listeners.filter(i => i !== l)
  }

  // 通知方法：5s 轮询刷数据时按"变化种类"精确通知
  reloadAll(items: AlertItem[]): void {
    this.items = items
    this.listeners.forEach(l => l.onDataReloaded())
  }

  appendItems(news: AlertItem[]): void {
    const from = this.items.length
    this.items = this.items.concat(news)
    this.listeners.forEach(l => news.forEach((_, i) => l.onDataAdd(from + i)))
  }

  changeAt(index: number): void {
    this.listeners.forEach(l => l.onDataChange(index))
  }
}
```

**listener 方法与通知语义对照：**

| 方法 | 时机 | 虚拟化收益 |
| --- | --- | --- |
| onDataReloaded | 整表替换 | 全量重建，慎用（见 §五） |
| onDataAdd / onDataDelete | 增删某下标 | 只创建/销毁该条 |
| onDataChange | 某条内容变化 | 只刷新该条 |
| onMove | 条目移动 | 复用实例换位置 |

**纪律红线：数据变更必须走 listener 通知。** 改了 `items` 数组却不调 listener，UI 不会更新——LazyForEach 不做轮询探测，通知是唯一通道。反过来，**严禁"改一条、reload 全表"偷懒**：onDataReloaded 会丢弃已建条目整表重建，5s 轮询一次就重建一次列表，正是虚拟化要消灭的行为。

## 三、cachedCount：缓存计数怎么调

`LazyForEach(dataSource, itemGenerator, keyGenerator).cachedCount(n)` 控制可视区两侧**预创建/保留**的屏幕外条目数：

1. **作用**：预构建 n 个屏幕外 ListItem，滑入可视区时直接上屏，减少"滑得快时白块/跳帧"；滑出的条目保留 n 个供回滑复用。
2. **默认与建议起点**：默认值偏小，资讯流类列表从 `cachedCount(5)` 起步。
3. **调参依据是条目构建成本与滑动速度**：条目重（卡片层级深、含图片）→ 增大 n 换流畅；条目轻 → n 大了纯属浪费内存。铃语卡片是大字文本卡，构建成本低，`cachedCount(3~5)` 足够。
4. **不是越大越好**：cachedCount 直接线性增加常驻内存与首屏构建量，适老化应用常驻后台，内存预算要克制。
5. **配合分页**：滚动到底加载更多时，新数据 append 后刚好落在缓存区外，不会引起可视区重建。

```ts
List({ space: 12 }) {
  LazyForEach(this.dataSource,
    (item: AlertItem) => {
      ListItem() { AlertCard({ alert: item }) }
    },
    (item: AlertItem) => item.id   // keyGenerator：稳定唯一键
  ).cachedCount(5)
}
.onReachEnd(() => this.loadMore())   // 触底分页
```

## 四、keyGenerator：虚拟化的身份系统

第三个参数常被省略，但它是正确复用的前提：

1. **必须稳定且唯一**：同一逻辑条目永远返回同一个 key。用业务主键（异动 id），不要用数组下标——下标会随插入漂移，导致复用时张冠李戴。
2. 缺省时框架按 item 引用与位置生成 key，数据 reload 后引用全变，等于全量重建。
3. key 冲突（重复）时框架按异常处理，列表行为不可预期——异动 id 撞车要当作数据层 bug 修掉。

## 五、5s 轮询场景：增量刷新，别整表 reload

铃语 Index 的刷新纪律（与 A23/A34 结论一致）：

1. 轮询拿到新 feed 后做 **diff**：新出现的 id → `onDataAdd(0)` 插头部；内容变化的 id → `onDataChange(i)`；已撤下的 → `onDataDelete(i)`。**不要 onDataReloaded。**
2. "播放中卡片不被轮询冲掉"依赖两点：条目级通知（整卡不重建）+ 播放态由页面级状态（playingId 等）独立持有，不寄存在会被替换的数据对象里。若已按 E2 迁移 @ObservedV2，播放态可下沉到 `@Trace playState`，配合 onDataChange 天然不冲。
3. 首屏兜底：服务未连通时 dataSource 先装演示数据（带"示例"字样），走同一条 onLoad 流程，保证首屏永不空白。

## 六、滑动性能清单（按收益排序）

1. **迭代器换 LazyForEach**——大数据量下唯一的决定性优化，For Each 全量构建是首帧杀手。
2. **削组件层级**：ListItem 内层深一寸，批量创建慢一截。用 @Builder 拆块（见 E1）而不是层层嵌套容器；Row/Column 能省则省。
3. **条目复用 @Reusable**：条目结构相同的滚动列表可加 `@Reusable` 装饰器，配合 keyGenerator 让滑出条目的组件树被复用而非销毁重建；与 LazyForEach 叠加效果最好。
4. **固定主轴尺寸/约束**：条目高度可预估时给 ListItem 明确约束，减少测量次数；大字卡片行数有限，天然适合。
5. **不在 itemGenerator 里做重计算**：格式化、时间换算放数据层预计算（E2 的 @Computed 亦可）；itemGenerator 每次创建都会执行，里面的函数调用都在滚动的关键路径上。
6. **嵌套滚动收敛**：List 内不要再嵌 List/Scroll 同向滚动；卡片内长文本用 Text 自身展开，不要内部再套滚动容器。
7. **滚动事件节流**：onScroll/onScrollIndex 高频触发，回调里只做轻逻辑；图片懒加载、埋点等挂在这里时必须节流。
8. **图片**：铃语当前为纯文本卡，无图；未来加图必须用 ImageKnife 式按需加载思路（可视区才解码），且这与"禁 K 线图等复杂图表"约束一致——只允许简单静态配图。
9. **避免 scrollToIndex 传越界/未创建大跨度跳转**：大跨度跳转可指定是否动画与对齐模式，滥用会造成一次性大量构建。
10. **Profiler 验证**：用 DevEco Profiler 的渲染与内存面板，实测滑动帧率与缓存的内存占用，再回填 cachedCount——所有调参结论以实测为准。

## 七、铃语落地路线

1. `Index.ets` 将 ForEach（若审查 A34 确认存在）替换为"AlertDataSource + LazyForEach + cachedCount(5) + id 作 key"四件套；
2. AlertPoller 刷新改为 diff 后调用 onDataAdd/onDataChange/onDataDelete，onDataReloaded 仅允许冷启动首装数据使用；
3. 条目组件按 E1 拆 @Builder、按需加 @Reusable；
4. 真机跑 Profiler 滑动录制，记录基线帧率与内存，作为 cachedCount 调参依据；
5. 分页（onReachEnd + loadMore）在数据源增长到百条量级前不必实装，但 DataSource 的 appendItems 接口先行预留。

### 自我评估
- 正确性：4分 IDataSource 接口形状、listener 语义、cachedCount 作用域描述均按 ArkUI 公开文档口径；性能量级结论已标注"以 Profiler 实测为准"，未虚构具体数字。
- 完整性：4分 虚拟化原理、数据源实现、缓存调参、keyGenerator、轮询增量刷新、滑动清单全覆盖；未展开多 List 联动与瀑布流变体（与本项目无关）。
- 可复用性：5分 AlertDataSource 模板与通知语义表可直接抄用，轮询 diff 纪律与 A23/A34/E2 交叉引用形成闭环。
- 字数：约3050字
- 使用模型：GLM-5.3-Flash
