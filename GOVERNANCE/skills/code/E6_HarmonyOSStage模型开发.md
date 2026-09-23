# E6 HarmonyOS Stage模型开发：UIAbility生命周期、WindowStage、多实例管理

> 适用项目：harmony-app（代号"铃语"，鸿蒙适老化股票异动播报应用）。工程基线：compatibleSdkVersion 20、targetSdk 26、纯ArkTS、零三方依赖、Stage模型。本文自包含成文，不依赖任何对话记忆；示例为ArkTS，文件路径相对 `entry/src/main/ets`。沿用项目铁律：适老化=28-34fp大字白话卡片流，禁K线图等复杂图表；首屏永不空白（服务未连通显示带示例字样的演示卡）；EntryAbility只做Push初始化与alertId分发，业务不下沉到Ability。

## 1 Stage模型定位：为什么是它

鸿蒙NEXT（API 12起）只支持Stage模型，旧的FA模型已淘汰。Stage模型以"组件化"为核心拆解了四件事：进程由系统管、任务栈由系统管、窗口交给WindowStage、界面组件交给UIAbility，应用级配置变化与内存水位则上收到AbilityStage。相比FA模型，Stage模型让多实例、多窗口、跨端迁移、后台任务都有了清晰的挂载点。

铃语只有一个入口UIAbility（EntryAbility），架构基调已定：EntryAbility只承担Push初始化（PushService.ets占位封装，AGC未配置前内部降级轮询）与推送点击alertId的分发；页面渲染、5s前台轮询（AlertPoller）、TTS音频播放（AVPlayer）全部在 `pages/Index.ets` 与 `service/` 层完成。Ability层薄、页面层厚，是Stage模型在铃语的落地姿态。

Stage模型四个核心对象速查（均为系统框架对象，无三方依赖）：

| 对象 | 级别 | 核心职责 |
|---|---|---|
| AbilityStage | module级 | onAcceptWant（specified多实例）、onConfigurationUpdate（系统配置变化）、onMemoryLevel（内存告警） |
| UIAbility | 组件级 | 界面容器，持有UIAbilityContext（this.context），管理完整生命周期 |
| WindowStage | 窗口层 | 窗口树管理者，onWindowStageCreate时由系统注入 |
| Context族 | 上下文 | ApplicationContext → AbilityStageContext / UIAbilityContext；权限申请、startAbility、文件目录都从Context发起 |

## 2 生命周期全景

冷启动完整时序（顺序不能记错）：

1. AbilityStage.onCreate（模块加载，module.json5顶层srcEntry指向的类）
2. UIAbility.onCreate(want, launchParam)
3. UIAbility.onWindowStageCreate(windowStage)——此时loadContent加载首页
4. UIAbility.onForeground
5. 页面onPageShow

退后台：页面onPageHide → UIAbility.onBackground。回前台：UIAbility.onForeground → 页面onPageShow。正常销毁：onWindowStageDestroy → onDestroy。注意系统低内存时可能直接回收进程，不保证走完onDestroy，所以关键持久化不能押注在onDestroy里，铃语的做法是AlertFeed最新一份数据随取随存。

各回调在铃语中的职责与禁忌：

| 回调 | 触发时机 | 铃语职责 | 禁忌 |
|---|---|---|---|
| onCreate | 冷启动仅一次 | PushService.init(this.context)；缓存want中的alertId | 不做网络、不做同步IO |
| onNewWant | singleton热启动被再次拉起 | 解析推送点击的alertId暂存 | 不重复init Push |
| onWindowStageCreate | 窗口就绪 | loadContent加载pages/Index | 不等待FEED_URL返回再加载 |
| onForeground | 回前台 | 暂存alertId写入AppStorage，驱动Index定位；恢复轮询 | 不做重活 |
| onBackground | 退后台 | 暂停5s轮询；AVPlayer在播则申请AUDIO_PLAYBACK长时任务 | 不做超过百毫秒的工作 |
| onWindowStageDestroy | 窗口销毁 | 注销窗口监听 | 之后不得再碰windowStage |
| onDestroy | 组件销毁 | PushService.release()反注册 | 不押注关键持久化 |

EntryAbility骨架（对应 `entryability/EntryAbility.ets`，与A22审查结论一致）：

```ts
import { AbilityConstant, UIAbility, Want } from '@kit.AbilityKit';
import { window } from '@kit.ArkUI';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { PushService } from '../service/PushService';

export default class EntryAbility extends UIAbility {
  private pendingAlertId: string = '';

  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    PushService.init(this.context); // AGC未配置时内部降级为轮询，不抛出
    this.pendingAlertId = (want.parameters?.['alertId'] as string) ?? '';
  }

  onNewWant(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    // singleton下重复拉起（点推送）只走这里，不走onCreate
    this.pendingAlertId = (want.parameters?.['alertId'] as string) ?? '';
  }

  onForeground(): void {
    if (this.pendingAlertId !== '') {
      AppStorage.setOrCreate('pendingAlertId', this.pendingAlertId);
      this.pendingAlertId = '';
    }
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    windowStage.loadContent('pages/Index', (err) => {
      if (err.code !== 0) {
        hilog.error(0x0000, 'EntryAbility', 'loadContent failed %{public}d', err.code);
      }
    });
  }

  onDestroy(): void {
    PushService.release();
  }
}
```

三个要点：

- want.parameters取值必须判空加类型收敛，ArkTS禁用any，统一 `as string ?? ''` 兜底；推送侧键名与端侧解析键名要登记成常量，避免"点通知没反应"这种最难排查的静默失败。
- 冷启动want与热启动want都要处理：推送点击既可能冷启动（onCreate）也可能热启动（onNewWant），只写onCreate是首号坑。
- alertId经AppStorage传给Index，Index侧用@StorageLink('pendingAlertId')监听，滚动定位对应卡片后清空该值，避免下一次无关拉起重复触发定位。

## 3 WindowStage与窗口管理

onWindowStageCreate收到的windowStage是唯一窗口入口，常用操作：

```ts
onWindowStageCreate(windowStage: window.WindowStage): void {
  const mainWindow = windowStage.getMainWindowSync();
  // 大字卡片流沉浸式，安全区由组件自绘避让
  mainWindow.setWindowLayoutFullScreen(true);
  // 播报音频时保持亮屏（可按页面状态开关）
  mainWindow.setWindowKeepScreenOn(true);
  windowStage.loadContent('pages/Index', (err) => { /* 同上 */ });
}
```

- 安全区：底部手势条、顶部状态栏用 `getWindowAvoidArea(window.AvoidAreaType.TYPE_NAVIGATION_INDICATOR / TYPE_SYSTEM)` 取值再减去布局边距。适老化的大按钮（60vp以上热区）贴近屏幕边缘时必须避让，否则老人握持姿势下极易误触。
- 尺寸变化：`mainWindow.on('windowSizeChange', cb)` 监听折叠屏展开与旋转。铃语卡片流单列布局，只需卡片宽度百分比自适应，不必切列数。
- 生命周期边界：windowStage只在onWindowStageCreate到onWindowStageDestroy之间有效，不要在onBackground、onDestroy里持有并调用它，否则窗口已销毁直接异常。
- 首屏永不白屏：loadContent是异步回调但必须立即发起；Index首帧只渲染本地演示卡常量（带"示例"字样），FEED数据回来后才替换。任何"先等网络再loadContent"的写法都违反首屏铁律，这类等待应发生在页面onPageShow之后的数据层。

## 4 启动模式与多实例管理

module.json5中abilities的launchType有四种：

| launchType | 行为 | 适用场景 |
|---|---|---|
| singleton（默认） | 应用内唯一实例，重复拉起走onNewWant | 单主页应用，铃语采用 |
| standard | 每次startAbility新建实例 | 可并存的独立功能页 |
| multiton | 不同任务链（如分享、文件拉起）各建实例 | 多渠道独立入口 |
| specified | AbilityStage.onAcceptWant返回key，同key复用、异key新建 | 多账号、多文档并行 |

声明示例：

```json5
{
  "module": {
    "srcEntry": "./ets/entryability/EntryAbilityStage.ets",
    "abilities": [
      {
        "name": "EntryAbility",
        "srcEntry": "./ets/entryability/EntryAbility.ets",
        "launchType": "singleton",
        "exported": true,
        "skills": [
          { "entities": ["entity.system.home"], "actions": ["action.system.home"] }
        ]
      }
    ]
  }
}
```

铃语选singleton的理由：卡片流只有一个真相源（AlertFeed契约），多实例意味着两条轮询、两份AppStorage状态、两次Push注册，适老化用户也理解不了"两个铃语"。推送点击拉起统一收敛到onNewWant，状态清晰可测。

specified模式示例（备用知识，铃语当前不启用）：

```ts
import { AbilityStage, Want } from '@kit.AbilityKit';

export default class EntryAbilityStage extends AbilityStage {
  onAcceptWant(want: Want): string {
    if (want.abilityName === 'DocAbility') {
      return `doc_${want.parameters?.['docId'] as string}`;
    }
    return '';
  }
}
```

系统按返回的key做实例复用：同key已存在则复用该实例（走onNewWant），不存在则新建（走完整onCreate）。onAcceptWant必须同步返回字符串，不能异步。

## 5 配置变化与内存水位

- onConfigurationUpdate：监听语言、字号（fontScale）、深浅色变化。适老化关键点：老人常在系统设置里把字体调到最大，铃语28-34fp的基础字号还要乘上系统fontScale，回调里把新fontScale写入AppStorage，Index用@StorageProp联动重排；文本容器高度禁写死，用百分比与弹性布局吸收溢出。
- onMemoryLevel（AbilityStage与UIAbility均可注册）：LEVEL_CRITICAL时释放非必要缓存，例如已播完的TTS临时音频文件；白名单只保留AlertFeed最近一份数据，保证重进不白屏。

## 6 与架构基调的对齐清单

1. EntryAbility只做三件事：Push初始化（占位封装、AGC未配置前降级轮询）、alertId分发、窗口加载。
2. Index.ets承担：List卡片流、5s前台轮询AlertPoller兜底、pendingAlertId滚动定位。
3. AudioPlayer用AVPlayer播云端TTS音频流；需要退后台续播时在onBackground申请AUDIO_PLAYBACK长时任务（backgroundTaskKit的startBackgroundRunning，需配wantAgent），回前台或播完即停，不靠多实例撑后台。
4. 数据契约AlertFeed不变；首屏演示卡兜底不变；禁三条红线（承诺收益/保本、催促性指令、对外公开/收费）在通知与卡片文案层生效，Ability层不做文案。

## 7 高频坑位速查

1. 点推送无反应：只写了onCreate没写onNewWant，或want.parameters键名与推送侧不一致。
2. 首屏白屏：在onWindowStageCreate里await网络再loadContent；正确做法是先loadContent，数据异步补。
3. windowStage空引用：在onBackground/onDestroy里调用windowStage的接口。
4. 热启动重复初始化：singleton下onCreate只走一次，把"每次拉起都要做"的逻辑放onNewWant/onForeground。
5. specified不生效：onAcceptWant返回key与预期不一致，或ability的launchType没改成specified。
6. 系统字号放大后布局溢出：未监听fontScale，或文本容器固定了vp高度。
7. 销毁路径内存泄漏：窗口监听（on('windowSizeChange')）在onWindowStageDestroy里忘了off。

### 自我评估
- 正确性：4分——生命周期时序、四类启动模式、WindowStage边界均基于官方公开机制书写，EntryAbility骨架与项目A22审查结论一致；个别API细节（AvoidAreaType组合、长时任务签名）以compatibleSdkVersion 20的d.ts为准。
- 完整性：4分——覆盖Stage核心对象、全生命周期、WindowStage、多实例、配置与内存、坑位清单；Push降级与音频续播只交代接口边界，细节在E7、E9等篇。
- 可复用性：4分——表格加骨架代码加坑位清单可直接迁移到其他Stage工程，铃语特有约束已单独标注，specified示例可平移到多账号类应用。
- 字数：约3150字
- 使用模型：GLM-5.3-Flash
