# E7 HarmonyOS CloudBase SDK集成：init单例化、存储操作、云函数调用、错误处理

> 适用项目：harmony-app（代号"铃语"，鸿蒙适老化股票异动播报应用）。现状：纯ArkTS+云函数、零三方依赖；数据源FEED_URL待X服务器落地，契约即AlertFeed；alerts.json中audioUrl可能为undefined，端侧按需调generate-tts合成后再播。本文自包含成文，不依赖对话记忆。"CloudBase"在鸿蒙语境下有两条实现路线：华为AGC云开发服务（Cloud Foundation Kit，系统Kit）与腾讯云开发（CloudBase鸿蒙SDK，三方包），本文以华为路线为主线（契合本项目AGC生态与零三方依赖），腾讯路线作对照，适配层设计保证两线可互换。

## 1 两条路线与决策规则

| 维度 | 华为 Cloud Foundation Kit（AGC云开发） | 腾讯 CloudBase 鸿蒙SDK |
|---|---|---|
| 依赖形态 | `@kit.CloudFoundationKit`，系统Kit | `@cloudbase/harmonyos-sdk`（包名以docs.cloudbase.net鸿蒙篇当前发布为准），三方依赖 |
| 是否违反零三方依赖 | 不违反（系统Kit） | 违反，需GOVERNANCE豁免记录 |
| 初始化 | 无端侧显式init入口，鉴权与环境由AGC项目配置承载 | `CloudBase.init({ env: '环境ID' })` 显式init |
| 前置条件 | AGC开通云函数/云存储，包名与AGC应用一致 | 腾讯云侧建环境、配鉴权 |

决策规则：铃语后端云函数（getalerts、generate-tts、pushtokenregister、initdb等六个函数，见A20调用链图谱）目前由自建HTTPS触发，FEED_URL落地后若迁AGC云开发，用Cloud Foundation Kit；若迁腾讯云开发，则引入三方SDK但必须隔离在适配层。无论哪条线，业务模块（AlertPoller、AudioPlayer、Index）只依赖适配层接口，不直接import任何云SDK——保住"换后端不改业务"与安全审计点唯一。

适配层接口先行：

```ts
// common/CloudApi.ets —— 业务层唯一可见的云能力接口
import { AlertFeed } from '../model/AlertFeed';

export interface CloudApi {
  fetchAlerts(): Promise<AlertFeed>;
  requestTts(alertId: string, text: string): Promise<string>; // 返回audioUrl
  registerPushToken(token: string): Promise<void>;
}
```

## 2 init单例化

华为Cloud Foundation Kit没有端侧init调用，"init单例化"落地为适配层单例：环境（超时、降级开关、鉴权上下文）在应用生命周期内装配一次、全局唯一。腾讯CloudBase SDK则有显式init，重复init会丢登录态、重复建连，同样必须单例。

```ts
// common/CloudClient.ets —— 全工程唯一允许import云SDK的文件（华为线）
import { cloudFunction } from '@kit.CloudFoundationKit';

export class CloudClient {
  private static api: CloudApi | null = null;
  private static initialized: boolean = false;

  static async init(): Promise<void> {
    if (CloudClient.initialized) {
      return; // 幂等：EntryAbility热启动、多模块重复调用都安全
    }
    CloudClient.api = new CloudFoundationApi();
    CloudClient.initialized = true;
  }

  static getApi(): CloudApi {
    if (CloudClient.api === null) {
      throw new Error('CloudClient未初始化');
    }
    return CloudClient.api;
  }
}
```

要点：

- 初始化时机：EntryAbility.onCreate里异步发起（`CloudClient.init()`不await网络握手），绝不阻塞loadContent——这是E6首屏铁律在云层的延伸。SDK未就绪期间，Index照常渲染演示卡。
- 环境ID、域名等低敏配置可入库；任何-secret、云函数密钥、Tushare token类凭据绝不放端侧，只存在于云函数环境变量或服务端。
- AGC未开通/未配置时，CloudClient.init要能走通：内部标记降级态，fetchAlerts回落到FEED_URL直连，与PushService.ets"AGC未配置前降级轮询"是同一套同构降级思想。

## 3 云函数调用

华为线API形态（API 12起，`@kit.CloudFoundationKit`的cloudFunction模块）：

```ts
// common/CloudFoundationApi.ets
import { cloudFunction } from '@kit.CloudFoundationKit';
import { CloudApi } from './CloudApi';
import { AlertFeed } from '../model/AlertFeed';
import { isAlertFeed } from '../model/AlertFeedGuard';

export class CloudFoundationApi implements CloudApi {
  async fetchAlerts(): Promise<AlertFeed> {
    const fn = cloudFunction.getCloudFunction('getalerts');
    const res = await fn.call({ since: Date.now() });
    const feed = res.result as object;
    if (!isAlertFeed(feed)) {
      throw new Error('告警数据结构不合规');
    }
    return feed;
  }

  async requestTts(alertId: string, text: string): Promise<string> {
    const fn = cloudFunction.getCloudFunction('generate-tts');
    const res = await fn.call({ alertId, text });
    const result = res.result as Record<string, Object>;
    const url = result['audioUrl'] as string;
    if (url === undefined || url === '') {
      throw new Error('TTS返回缺少audioUrl');
    }
    return url;
  }

  async registerPushToken(token: string): Promise<void> {
    await cloudFunction.getCloudFunction('pushtokenregister').call({ token });
  }
}
```

腾讯线对照：`app.callFunction({ name: 'generate-tts', data: { alertId, text } })`，返回体经 `res.result` 取业务对象，接口语义相同，仅替换实现类。

调用纪律：

- 幂等键：generate-tts以alertId为幂等键，云函数侧同键直接返回已合成audioUrl，避免重复烧TTS配额；端侧并发去重（同一alertId在途请求复用Promise，见E9并发管理）。
- 超时：云函数侧配置自身超时上限，端侧仍要套自己的超时预算（铃语全链路≤15s），超时后取消等待而非无限挂起。
- audioUrl为undefined是常态而非异常（见已知问题），正确路径是：拿到AlertFeed后，逐条检查audioUrl，缺省的条目在用户点播时才调generate-tts，合成成功再喂给AVPlayer。

## 4 存储操作

存储用于两类对象：generate-tts合成的音频文件、告警快照类文件。华为线API形态（cloudStorage模块，具体签名以compatibleSdkVersion 20的d.ts为准）：

```ts
import { cloudStorage } from '@kit.CloudFoundationKit';

const bucket = cloudStorage.bucket(); // 默认桶

// 上传：本地合成/缓存文件 → 云端固定路径
await bucket.uploadFile(localPath, `tts/${alertId}.mp3`);

// 获取带有效期的下载直链，喂给AVPlayer
const url: string = await bucket.getDownloadURL(`tts/${alertId}.mp3`);

// 删除过期文件（例如内存告警或过期清理任务）
await bucket.deleteFile(`tts/${oldAlertId}.mp3`);
```

腾讯线对照：`app.uploadFile({ cloudPath, filePath })` 得到fileID；`app.getTempFileURL({ fileList })` 换临时链接；`app.deleteFile({ fileList })` 删除。概念一一对应。

存储纪律：

- 云端路径按alertId组织（`tts/{alertId}.mp3`），天然幂等可覆盖，重合成不产生垃圾。
- 直链有有效期：AVPlayer播放遇403时，先刷新直链再重试一次，仍失败才走白话错误提示。
- 清理策略：已播且超过保留期的音频由云函数定期清理，端侧不做批量删除写操作，减少端侧权限面。

## 5 错误处理

三层归一，业务层只见白话：

1. 传输/SDK层：连接失败、超时、未登录或鉴权过期。处理：标记降级态、按E9指数退避重试；鉴权过期先重登录（华为线由系统托管，腾讯线重新signIn）再重试一次。
2. 云函数层：函数内部throw会带错误码回传。端侧维护一张错误码映射表，例如：token失效类（参考已知问题Tushare 40101）触发源切换降级（东财API备份源），配额类错误进入长退避，结构类错误不重试直接降级到演示卡。
3. 业务层：统一转成适老化白话文案——"这条暂时读不了，稍后再试试"，绝不暴露码值、堆栈、URL细节，也绝不出现催促性措辞（红线）。

降级链完整形态：AGC云函数 → FEED_URL直连 → 本地演示卡。任何一层失败都必须让首屏有内容，这是与"首屏永不空白"铁律绑定的一条。

日志纪律：hilog不打Authorization头、不打云函数入参全文、不打任何凭据；错误码与alertId足够定位问题。

## 6 安全与合规

- 端侧只做最小权限：读告警、按需申请TTS、注册推送token；告警的写操作（管理alerts.json）只存在于云函数/服务端，不开放端侧写路径。
- 云函数侧必须复校验入参（长度、类型、幂等键），端侧校验只是省流量，不是安全边界。
- 云函数环境变量承载全部密钥（Tushare、百炼TTS等）；已知问题清单中的token失效处理（40101降级东财）只在云函数层发生，端侧无感。
- 不涉对外公开/收费红线：云能力只服务本应用用户，不提供公开API网关给第三方。

## 7 验收清单

1. 冷启动到演示卡≤3秒，且演示卡渲染不依赖CloudClient初始化结果。
2. 断网/AGC未配置时：轮询降级到FEED_URL或演示卡，无崩溃、无空白。
3. audioUrl为undefined的条目：点播触发generate-tts成功播放；连续快速点同一卡片只发一次请求。
4. 直链过期路径：自动刷新一次后播放成功。
5. 错误文案抽查：无码值、无堆栈、无催促性词汇、无收益承诺。
6. 全工程grep云SDK import：只出现在CloudClient/CloudFoundationApi适配层文件内。

### 自我评估
- 正确性：4分——Cloud Foundation Kit与腾讯CloudBase两条路线的API形态按官方公开文档方向书写，其中cloudStorage具体方法签名标注了需按API 20的d.ts核对；错误码表给出的是类型化策略而非虚构码值。
- 完整性：4分——覆盖init单例、云函数、存储、错误处理、安全合规与验收清单，并打通了audioUrl按需合成与降级链两条项目已知问题；腾讯SDK细节（包名/登录API）标注以官方文档为准。
- 可复用性：4分——适配层接口加双实现对照的写法可直接迁移到任何"多后端候选"的鸿蒙工程，与E9网络层、E6生命周期形成明确分工引用。
- 字数：约3200字
- 使用模型：GLM-5.3-Flash
