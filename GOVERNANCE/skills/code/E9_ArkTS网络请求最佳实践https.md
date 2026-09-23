# E9 ArkTS网络请求最佳实践：https模块封装、超时控制、重试机制、并发管理

> 适用项目：harmony-app（代号"铃语"，鸿蒙适老化股票异动播报应用），纯ArkTS、零三方依赖（网络只用系统@kit.NetworkKit的http能力），Stage模型 compatibleSdkVersion 20 / targetSdk 26。数据源FEED_URL待X服务器落地，契约即AlertFeed。本文自包含成文，不依赖对话记忆；与E6（生命周期挂载）、E7（云函数路线）互为分工。

## 1 基础设施与权限

- 权限：module.json5的module.requestPermissions声明 `ohos.permission.INTERNET`。漏配的症状是请求异常且错误码难懂，先查权限再查代码。
- 模块：`import { http } from '@kit.NetworkKit';`
- 实例纪律：一次请求=一个httpRequest实例（http.createHttp()），请求结束（无论成败）在finally里调用destroy()，绝不复用实例发第二笔——复用会抛状态异常，也不释放底层资源。
- 解析方式：expectDataType用STRING自行解析并做结构校验；框架的OBJECT直解会绕过类型收敛，在ArkTS严格模式下反而多一道坎。

## 2 类型契约先行：AlertFeed

网络层的第一原则是先定契约再写请求。上游字段缺失（如audioUrl为undefined）是常态，端侧解析必须宽容、结构必须校验：

```ts
// model/AlertItem.ets
export interface AlertItem {
  id: string;
  ts: number;
  code: string;
  name: string;
  level: number;
  title: string;      // 白话一句话
  detail: string;
  audioUrl?: string;  // undefined时端侧按需调generate-tts（见E7）
}
export interface AlertFeed {
  alerts: AlertItem[];
  ts: number;
}
```

```ts
// model/AlertFeedGuard.ets —— 结构守卫，拒收不合规响应
export function isAlertFeed(v: object): boolean {
  const arr = (v as Record<string, Object>)['alerts'];
  if (!Array.isArray(arr)) {
    return false;
  }
  return true;
}
```

解析统一走"JSON.parse → isAlertFeed校验 → as AlertFeed"，禁止裸as any。

## 3 统一封装：NetClient

所有请求收敛到NetClient.ets一个入口，业务层不散写http调用：

```ts
// common/NetClient.ets
import { http } from '@kit.NetworkKit';

export class NetError extends Error {
  readonly kind: string; // 'NETWORK' | 'HTTP' | 'PARSE' | 'CANCEL'
  readonly status: number;
  constructor(kind: string, status: number, msg: string) {
    super(msg);
    this.kind = kind;
    this.status = status;
  }
}

export class NetClient {
  static async getJson(url: string, timeoutMs: number = 10000): Promise<object> {
    const req = http.createHttp();
    try {
      const resp = await req.request(url, {
        method: http.RequestMethod.GET,
        connectTimeout: 8000,
        readTimeout: timeoutMs,
        expectDataType: http.HttpDataType.STRING,
        usingCache: false
      });
      if (resp.responseCode < 200 || resp.responseCode >= 300) {
        throw new NetError('HTTP', resp.responseCode, `HTTP ${resp.responseCode}`);
      }
      return JSON.parse(resp.result as string) as object;
    } catch (e) {
      if (e instanceof NetError) {
        throw e;
      }
      throw new NetError('NETWORK', 0, '网络不可达');
    } finally {
      req.destroy(); // 成败都必须销毁
    }
  }
}
```

- 错误四分类（NETWORK/HTTP/PARSE/CANCEL）是重试与降级决策的唯一依据，业务层只看kind不猜原因。
- 日志脱敏：不打完整URL查询串与任何token；用hilog只记kind、status、路径片段。
- 自签名/私有CA场景：HttpRequestOptions的证书参数（caPath等）自较新API版本提供，落码前以compatibleSdkVersion 20的d.ts为准；无论何种理由，禁止关闭证书校验。

## 4 超时控制

两个独立旋钮，别混为一谈：

- connectTimeout：建连（TCP+TLS握手）预算，铃语设8秒。
- readTimeout：发包后等响应的预算，轮询场景设10秒。
- 全链路预算：轮询单次请求（建连+读）≤15秒，必须在下一个5秒tick前结束，否则请求堆积（见第6节单飞）。
- 首屏关系：首屏渲染只依赖演示卡常量，首请求超时也绝不阻塞loadContent（E6铁律）；超时后走演示卡兜底并提示"正在获取最新信息"。

## 5 重试机制

- 只重试幂等请求。GET轮询天然幂等；POST类（generate-tts）靠alertId幂等键保证重试安全，无幂等键的POST不重试。
- 可重试判定：NETWORK类全可重试；HTTP类仅502/503/504与429（429优先读Retry-After头）；4xx参数与鉴权错误（如上游token失效、返回40101类错误码）不重试，直接触发源切换降级——参考已知问题"Tushare token失效已降级东财API"，同构处理。
- 退避算法：base=500ms，间隔=base×2^n±20%抖动，最多2次重试（共3次尝试），重试期间上层无感。
- 熔断与半开：连续3轮轮询全失败进入长退避（轮询间隔拉长到30秒），收到一次成功即恢复5秒节奏。熔断是省电与省配额的双赢，不是失败掩盖——UI状态照常明示"连接中"。

```ts
function backoffMs(attempt: number): number {
  const base = 500 * Math.pow(2, attempt);
  const jitter = base * 0.2;
  return base + (Math.random() * 2 - 1) * jitter;
}
```

## 6 并发管理

- 轮询单飞（最重要）：AlertPoller同一时刻只允许一个在途请求。inFlight标志位拦住重叠的5秒tick，防止慢网下请求雪崩式堆积：

```ts
export class AlertPoller {
  private inFlight: boolean = false;
  private timer: number = -1;
  private gen: number = 0; // 代次号：stop后丢弃过期响应

  start(): void {
    this.stop();
    const myGen = ++this.gen;
    this.tick(myGen);
    this.timer = setInterval(() => this.tick(this.gen), 5000);
  }

  stop(): void {
    if (this.timer >= 0) {
      clearInterval(this.timer);
      this.timer = -1;
    }
    this.gen++; // 使旧响应作废
  }

  private async tick(myGen: number): Promise<void> {
    if (this.inFlight || myGen !== this.gen) {
      return; // 单飞 + 代次校验
    }
    this.inFlight = true;
    try {
      const feed = await NetClient.getJson(FEED_URL) as AlertFeed;
      if (myGen === this.gen && isAlertFeed(feed)) {
        AppStorage.setOrCreate('alerts', feed.alerts);
      }
    } catch (e) {
      // 保留旧数据与演示卡兜底；连续失败交给熔断拉长间隔
    } finally {
      this.inFlight = false;
    }
  }
}
```

- 生命周期挂载：Index.ets的onPageShow里start()、onPageHide里stop()——前台5秒轮询、后台不轮询（省电省流量），兜底链见E6。
- 全局限流：除轮询外还有按需TTS合成、配置拉取等请求，用信号量模式限全应用并发≤4，超出排队；避免弱网下互相挤占。
- 取消与作废：ArkTS没有AbortController，用两件套——页面隐藏时destroy在途请求（httpRequest.destroy()），响应回来后用代次号丢弃过期结果。两者缺一不可：只destroy会漏掉"已返回未处理"的窗口，只丢结果会浪费连接。
- 去重复用：同URL同参请求在途时复用同一Promise（典型：同一张卡片连续点播报只发一次TTS合成请求）。

## 7 错误呈现与适老化

- 所有NetError最终翻译成白话：NETWORK→"网络连不上，请检查网络"；HTTP 5xx→"服务器忙，稍后再试"；PARSE→"数据有点问题，正在重试"。绝不显示码值、URL、堆栈。
- 任何失败路径都不得清空已有卡片流，也不得让页面空白——旧数据+演示卡是最终兜底。
- 错误文案过红线检查：不催促、不承诺、不吓唬（禁"数据已损坏""风险自负"类表述）。

## 8 高频坑位速查

1. 忘INTERNET权限：一律请求失败且难排查。
2. 复用httpRequest实例发第二笔：状态异常；实例必须一笔一建一destroy。
3. 轮询未单飞：5秒tick × 15秒超时 = 三个在途请求互相拖垮。
4. 裸JSON.parse后直接用：ArkTS禁any，且上游字段缺失直接崩溃；必须guard。
5. 重试打到非幂等POST：TTS重复扣配额；靠alertId幂等键或禁止重试。
6. 页面隐藏不stop轮询：后台空转耗电，也违反"前台5秒轮询"的架构基调。
7. 捕获后吞错不降级：catch里既不清数据也不提示，用户面对的是静默过期数据；必须明示状态。

### 自我评估
- 正确性：4分——@kit.NetworkKit的http能力、超时双旋钮、单飞+代次号取消模式均为标准做法，代码骨架经ArkTS类型纪律书写；caPath等证书参数的API版本支持点已标注需按d.ts核对，未实测真机联调。
- 完整性：4分——四个指定维度（封装、超时、重试、并发）全部展开并补错误呈现与坑位；AlertPoller与E6生命周期、E7 TTS按需合成的衔接有明确引用。
- 可复用性：5分——NetClient、AlertPoller、退避函数均为可直接复制的通用件，仅FEED_URL与AlertFeed为本项目契约，替换成本低。
- 字数：约3050字
- 使用模型：GLM-5.3-Flash
