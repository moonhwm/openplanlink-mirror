# ArkTS @ComponentV2 与 @ObservedV2——新状态管理范式、V1 对比、迁移指南

> 适用项目：harmony-app（铃语，适老化股票异动播报），纯 ArkTS、零三方依赖，Stage 模型，compatibleSdkVersion 20 / targetSdk 26（满足状态管理 V2 所需的 API 12+ 基线）。
> 本文归档于 `GOVERNANCE/skills/code/`，与项目内状态管理现状审查文档 `GOVERNANCE/skills/code/A28_状态管理审查StatePropLin.md`、List 卡片流审查 `A23_Indexets审查List卡片流渲.md` 联动。V2 各装饰器语义按 ArkTS 状态管理公开文档口径书写；个别回调参数结构的字段命名以 SDK d.ts 声明与 DevEco 编译为准。

---

## 一、V2 要解决什么：V1 观测粒度的三堵墙

V1 状态体系（@State/@Prop/@Link/@Observed+@ObjectLink 等）在实际项目里反复撞上三堵墙：

1. **@State 只看第一层。** 状态变量的第一层变化（重新赋值、数组整体替换）能触发刷新；嵌套对象的属性变化、数组元素的属性变化默认感知不到，必须整对象重建赋值。
2. **深观测要"套娃"。** @Observed+@ObjectLink 能深入一层，但要求每个嵌套层级都被 @Observed 装饰、且接收方组件用 @ObjectLink 接——类层级越深，样板代码越多，还改变了组件的参数形态。
3. **数据与 UI 绑死。** 数据类一旦要"可观测"，就得按 V1 组件的规则来设计，数据层被迫感知 UI 层。

V2 的答案是把"观测能力"内嵌进数据类本身：**@ObservedV2 装饰类、@Trace 装饰类中需要被观测的属性**，属性级、任意嵌套深度的变化都能触发精确刷新；组件侧用 @ComponentV2 搭配 @Local/@Param/@Event/@Monitor/@Computed，形成一套粒度更细、数据与 UI 解耦的新范式。

## 二、V2 装饰器全家桶速览

| 装饰器 | 作用 | 典型用法 |
| --- | --- | --- |
| @ComponentV2 | 声明 V2 组件，组件内只能用 V2 装饰器 | 页面与业务组件 |
| @ObservedV2 + @Trace | 类与类属性：属性级深度观测 | 数据模型（如 AlertFeed） |
| @Local | 组件私有状态，必须本地初始化，禁止外部传入 | 播放三态、加载标志 |
| @Param | 父到子单向同步的入参，组件内只读 | 卡片入参 |
| @Event | 子到父的回调通道，与 @Param 组成双向 | 播放按钮回调 |
| @Monitor | 监听状态（含属性路径）变化，回调携带前后值 | 通知轮询结果变化 |
| @Computed | 计算属性，依赖变化自动重算 | 派生文案（如涨幅描述） |
| @Provider/@Consumer | 跨层级双向同步 | 全局播放状态下发 |

## 三、@ObservedV2 与 @Trace：数据层先富起来

```ts
@ObservedV2
class AlertItem {
  @Trace stockName: string = ''
  @Trace plainSpeak: string = ''   // 白话解读
  @Trace audioUrl: string | undefined = undefined
  @Trace playState: 'idle' | 'loading' | 'playing' | 'failed' = 'idle'
}

@ObservedV2
class AlertFeed {
  @Trace items: AlertItem[] = []
  @Trace updatedAt: number = 0
}
```

规则要点：

1. **@ObservedV2 只观测 @Trace 属性。** 未被 @Trace 装饰的属性变化不触发刷新——这是刻意设计，避免无差别劫持。
2. **嵌套天然支持。** 上例 `feed.items[3].playState = 'playing'` 会且只会刷新绑定了该卡片的那块 UI；V1 里这需要整卡片对象重建。
3. **类需要实例化才生效。** @ObservedV2 修饰 class；接口（interface）与字面量对象不具备该能力，数据契约建模时要用 class。
4. **与 V2 组件配套。** @ObservedV2 实例的观测能力面向 V2 组件树；在 V1 组件里它只是普通类，深观测不生效。
5. **配套存储 API。** V2 体系另有 AppStorageV2/PersistenceV2（API 12+）与 @ObservedV2 协同做应用级与持久化状态，本项目当前未用到，仅备查。

## 四、V1 对 V2：逐项映射与语义差异

| V1 | V2 | 语义差异要点 |
| --- | --- | --- |
| @State | @Local | @State 可被父组件初始化；@Local 强制本地初始化、完全私有 |
| @Prop | @Param | 单向同步不变；@Param 组件内只读（编译期约束），V1 @Prop 内部可改 |
| @Link | @Param + @Event | 显式双向：父传 @Param、子回调 @Event；不再隐式双向同步 |
| @Provide/@Consume | @Provider/@Consumer | 跨层级；V2 版粒度到属性级 |
| @Watch | @Monitor | @Watch 只能监听变量名、回调拿不到旧值；@Monitor 可监听 `a.b.c` 路径，回调带变更前后值 |
| @Observed+@ObjectLink | @ObservedV2+@Trace | 见 §三，去样板、任意深度 |
| （无） | @Computed | V2 新增，派生计算不写在 build 里 |

几个容易误判的差异：

1. **@Param 只读不是阉割，是把数据流掰直。** V1 @Link 的隐式双向让"谁改了状态"难以追踪；V2 里子组件要改父状态只能走 @Event，修改点在代码里显式可查。
2. **@Local 与 @Param 是互斥的语义而非同义。** "只有自己用"选 @Local，"父组件喂"选 @Param，二者不可兼得。
3. **@Monitor 的回调携带变更信息**（属性路径与修改前后的值），写法形如：

```ts
@ComponentV2
struct FeedPanel {
  @Local feed: AlertFeed = new AlertFeed()

  @Monitor('feed.updatedAt', 'feed.items.length')
  onFeedChanged(m: IMonitorChange) {
    // m 内含路径与前后值，具体字段以 SDK 声明为准
  }
}
```

4. **V2 支持 @Entry。** `@Entry @ComponentV2 struct Index` 合法，整页可直接 V2 化。

## 五、混用限制：按子树整体迁移，不要跨范式拉状态线

1. **同一个 struct 内 V1/V2 装饰器不可混用**（如 @ComponentV2 里写 @State 直接编译不过）。
2. V1 组件与 V2 组件可以父子嵌套，但**跨范式传值退化为普通值传递**：V2 父组件的 @Local 传给 V1 子组件，只是初始值，不建立任何同步；反向同理。
3. 因此迁移的正确姿势是**以子树为单位**：一个页面及其全部后代组件整体切换范式，跨子树的边界先用普通 props/回调对接，等相邻子树也迁完再恢复状态线。
4. V1 与 V2 可在一个应用内长期共存，不存在"必须一次迁完"的硬期限。

## 六、迁移指南：六步走

**第 1 步：盘点。** 用 grep 找出全部 @Observed/@ObjectLink/@Link/@Watch 用法，按"数据模型类 → 叶子组件 → 容器组件 → 页面"排出依赖层次。叶子多、层级深的项目收益最大。

**第 2 步：数据层先行（风险最低）。** 把数据模型类改为 @ObservedV2，需要观测的属性加 @Trace。数据类不依赖组件编译，改动独立可测。本项目 `AlertFeed`/`AlertItem` 契约类即属此类。

**第 3 步：叶子组件 V2 化。** @Component→@ComponentV2，逐项换装饰器：

- 只读入参：@Prop→@Param；
- 需要回调父组件：新增 @Event（替代原 @Link 隐式回写）；
- 组件私有：@State→@Local（注意补本地初始值）；
- @Watch 换 @Monitor，旧值逻辑直接用回调携带的前值，删掉手工缓存旧值的代码；
- build 内的派生计算抽成 @Computed。

**第 4 步：容器与页面。** List 容器、@Entry 页面最后迁；跨层级状态换 @Provider/@Consumer。此时子树内已无 V1 组件，状态线恢复完整。

**第 5 步：回归验证三个点。** ① 深层属性修改是否刷新（V1 时代靠整对象重建的代码现在可简化）；② @Param 只读约束是否在编译期暴露了原本的隐式回写；③ @Monitor 回调的触发次数与预期一致（路径监听比 @Watch 触发点更细）。

**第 6 步：删 V1 遗产。** 整对象重建赋值的 workaround、手工旧值缓存、为观测而生的中间包装类，逐一删除。

**常见坑：** interface 契约不能直接换 @ObservedV2，要改成 class；@Local 忘记本地初始化编译报错；V2 子组件里误用 @State 直接编译失败——这些都是编译期暴露的坑，真正的运行期坑只有一个：跨范式边界上的"看似同步实则传值"。

## 七、铃语落地建议

1. **Index 卡片流是 V2 的最佳落点。** 5s 前台轮询（AlertPoller）拿到新数据后，`items[i].plainSpeak`、`audioUrl` 等属性级更新可精确刷到单张卡片，替代整列表 reload；这与 A23 审查确认的"refresh 卡片撤下防护"逻辑天然契合——播放中卡片只改自身播放态字段，不整卡重建，播放态就不怕被轮询冲掉。
2. **播放三态用 @Local 留在页面级。** `playingId/loadingId/failedId` 语义上仍是页面私有状态，维持 @Local 即可，不必过度下沉到卡片。
3. **PushService.ets 保持占位封装不动。** 其内部无 UI 状态，与范式迁移无关，AGC 未配置前的降级轮询路径不受影响。
4. **迁移节奏建议**：先迁 `AlertFeed/AlertItem` 数据契约（第 2 步），再迁 AlertCard 叶子组件，Index 页面最后；每步保持可编译可运行，不为迁移停迭代。
5. **首屏永不空白约束不依赖范式**：演示卡数据同样走 @Trace 属性，服务未连通时喂示例数据即可，无特殊处理。

### 自我评估
- 正确性：4分 装饰器语义、映射关系、混用限制均按官方文档口径书写；@Monitor 回调字段与个别边界行为已注明以 SDK 声明实测为准，未把不确定细节写成定论。
- 完整性：4分 新范式总览、@ObservedV2 细则、V1 逐项对比、混用限制、六步迁移与落地建议全覆盖；未展开 AppStorageV2/PersistenceV2 深度用法（本项目未用到，仅备查）。
- 可复用性：4分 迁移六步与映射表可直接当工单模板；示例贴合铃语卡片流与轮询场景，联动文档路径明确。
- 字数：约3050字
- 使用模型：GLM-5.3-Flash
