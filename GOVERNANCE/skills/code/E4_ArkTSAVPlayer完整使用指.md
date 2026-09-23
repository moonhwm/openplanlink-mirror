# ArkTS AVPlayer 完整使用指南——音频流播放、状态机管理、错误处理、资源释放

> 适用项目：harmony-app（铃语，适老化股票异动播报）。端侧播放链路为 `entry/src/main/ets/services/AudioPlayer.ets` → AVPlayer 播放云端 generate-tts 产出的 mp3 音频流；调用方 `entry/src/main/ets/pages/Index.ets` 持有播放三态（playingId/loadingId/failedId）。
> 本文归档于 `GOVERNANCE/skills/code/`，与 `A25_AudioPlayer审查AVPla.md`（既有审查，已确认：stop() 静态字段重复读取竞态为 P0、error 事件不清理实例为 P1、无音频焦点处理、idle 被当作完成信号）联动。AVPlayer 状态机与事件名以 ArkTS 媒体组件公开文档通用口径书写；具体错误码数值与个别事件参数以 SDK d.ts 声明与真机实测为准。

---

## 一、AVPlayer 状态机：一切用法的地基

AVPlayer 是有严格状态约束的实例，**每个 API 只在特定状态合法**，错误状态调用直接抛错或进 error。九个状态与合法迁移：

| 状态 | 进入方式 | 此状态可做的事 |
| --- | --- | --- |
| idle | createAVPlayer() 创建 / reset() | 赋 `url`（→initialized） |
| initialized | url 赋值成功 | prepare()（→prepared） |
| prepared | prepare() 完成 | play()、seek()、取 duration、设倍速音量 |
| playing | play() | pause()、seek()、stop() |
| paused | pause() | play() 恢复、stop() |
| completed | 播放至末尾 | seek 后重播、play()、stop() |
| stopped | stop() | prepare() 重播、reset() 换源、release() |
| released | release() | 无——实例终结，不可复用 |
| error | 任意状态出错 | 只能 release() |

三条铁律：

1. **completed 才是"播完"**，idle 不是。idle 只在 reset 或异常时出现，把 idle 当完成信号会误吞错误（A25 已确认现有实现存在此问题）。
2. **stopped 后重播必须重新 prepare()**；换网络源需先回 idle（stop 后 reset，或 stop 后视状态直接重新赋 url 再 prepare，以实测为准）。
3. **error 状态实例必须 release()**，且 release 后引用置空，防止僵尸实例滞留。

## 二、音频流播放：网络 url 的标准链路

```ts
import { media } from '@kit.MediaKit';

async function playOnce(url: string,
                        onDone: () => void,
                        onError: (msg: string) => void): Promise<void> {
  let av: media.AVPlayer | null = null;
  try {
    av = await media.createAVPlayer();          // → idle
    let finished = false;                        // 完成/出错互斥标记

    av.on('stateChange', (state: string) => {
      if (state === 'completed' && !finished) {
        finished = true;
        onDone();
      }
    });
    av.on('error', (err) => {                    // 任何状态都可能来
      if (!finished) { finished = true; onError(`code:${err?.code}`); }
    });

    av.url = url;                                // idle → initialized
    await av.prepare();                          // → prepared（网络流在此缓冲）
    await av.play();                             // → playing
  } catch (e) {
    onError(String(e));
    throw e;                                     // 交给上层置 failedId
  }
  // 注意：av 不能在此 release——播放还在进行。见 §五释放时机。
}
```

要点：

1. **url 直喂网络地址即可流式播放**（https 的 mp3 由内部缓冲边下边播），不需要先下载到本地；本地文件走 `fdSrc`，本项目的音频在云端（generate-tts 产出），恒走 url。
2. **prepare() 是网络风险点**：地址过期、弱网、格式不支持都在这里暴露；await 会挂较久，调用方要有 loading 态与超时预期（铃语对应 failedId + "语音加载失败，点重试"）。
3. **常用事件**：`stateChange`（状态迁移）、`error`（错误，含错误码）、`durationUpdate`（prepared 后拿到总时长）、`timeUpdate`（播放中周期性进度）、`seekDone`（seek 完成）。做进度条才需要后三者；铃语"点卡片=听、再点=停"的极简交互只订阅前两个。
4. **error 事件与 await 异常都要接**：有的错误走事件回调而非 Promise reject，只 try/catch 会漏。

## 三、状态机管理：单实例模式下的先停后播

铃语同一时刻只允许一条音频（适老化防叠加），AudioPlayer 用静态单例承载，于是**先停后播**成为核心路径，也是竞态高危区（A25 P0）：

```ts
// services/AudioPlayer.ets —— 修复版骨架（对照 A25 §5.2 竞态）
static async stop(): Promise<void> {
  const p = AudioPlayer.player;      // ① 只读一次静态字段，存局部
  AudioPlayer.player = null;         // ② 立刻置空，关闭"旧停止释放新播放器"窗口
  if (!p) return;
  try {
    p.off('stateChange'); p.off('error');   // 摘事件，防 release 过程触发回调
    if (p.state === 'released') return;     // 幂等
    p.release();                            // 任意状态均可 release
  } catch { /* 已释放/异常吞掉，不影响下次播放 */ }
}
```

纪律：

1. **先摘事件再 release**，避免释放过程的状态回调打进已换代的 UI 逻辑；
2. **release 前置判 released，幂等**；catch 兜底重复释放；
3. **"读一次、立刻置空、再操作局部引用"**，杜绝跨 await 的静态字段二次读取；
4. error 事件回调里也要走同一套清理（A25 P1：现有实现 error 不清理导致失败实例滞留）；
5. 互斥由 Index 的三态闸（loadingId 防连点、playingId 再点即停）与 AudioPlayer 的先停后播双层把守，两层都要留。

## 四、错误处理：分类、文案、降级

端侧拿到错误后按类处理，**错误码数值以媒体错误码表为准，不要在 UI 硬编码数字**：

| 类别 | 典型来源 | 用户可见处理（适老化文案） |
| --- | --- | --- |
| 网络类 | 临时链接过期、弱网、超时 | "语音加载失败，点重试"→ failedId 可重试 |
| 资源类 | audioUrl 为 undefined / 404 | 走已知规划：按需调 generate-tts 现场合成后重播 |
| 格式类 | 非 mp3/不支持编码 | "这条语音暂时播不了"，卡片降级为纯文字 |
| 状态类 | 错误状态调 API（竞态） | 记日志、静默重建实例，不打扰用户 |

三条处理纪律：

1. **回调与异常双通道都归一到一个 onError**，用 finished 标记互斥，防止一次失败双回调把 UI 三态打乱；
2. **失败必须落到"可重试"而非"消失"**：适老化用户对失败的处理成本极高，failedId + 大字重试入口是底线；
3. **已知坑联动**（A24 §3.6 / A25 §2.2）：generate-tts 写入 alerts.json 的是 `getTempFileURL` 临时链接，过期后"重试必败"。修复方向是重试前先调 get-alerts 或 generate-tts 换新链接，而不是原地重放旧 URL——本指南建议把"换链接"做进重试路径，作为按需合成的第一步。

## 五、资源释放：时机清单

AVPlayer 持有解码器与网络连接等底层资源，泄漏代价高（后台耗流、耗电、占解码通道）。释放时机按优先级：

1. **换播时**：play() 入口先 stop() 旧实例（§三骨架）——本项目最高频路径；
2. **error 之后**：error 回调里同步清理并置 null（A25 P1 修复点）；
3. **页面 aboutToDisappear**：Index 销毁时 AudioPlayer.stop()，防止页面级泄漏升级为应用级；
4. **应用退后台**：适老化播报场景音频可继续播完（不抢停），但若产品决策是"退后台即停"，在相应生命周期回调调用 stop()；当前实现未挂后台监听，属可选项；
5. **不要在 completed 后立刻 release**：completed 状态实例可复用（seek(0)+play 重播），频繁点同一张卡时复用比重造省一次建连；铃语当前"每次都重造"的实现可接受，但若真机测得重播卡顿，这是第一优化点。

释放动作固定四步：**摘事件 → 判状态 → release → 置空引用**，缺一步都算不完整。

## 六、音频焦点：当前空白与补齐方向

A25 已确认现有实现无音频焦点处理。铃语播的是 30 秒级短语音，冲突场景有限（来电、用户同时在听收音机），补齐方案按成本递增：

1. **最低配**：订阅 `audioInterrupt` 事件，收到打断即走 stop()（复用现有清理路径），UI 回 idle——不打断别人、不产生"边打电话边播股讯"的体验灾难；
2. **进阶**：打断结束事件里按业务决定是否恢复播放（短语音场景建议不恢复，用户点卡片重听，交互更可控）；
3. 具体事件参数与焦点模式设置以 SDK 媒体文档为准，接入时以真机验证。

## 七、接入检查清单（code review 用）

1. play 前是否先走了幂等 stop（读一次静态字段版本）？
2. error 事件是否清理实例并置 null？
3. completed 与 idle 是否区分（完成信号只认 completed）？
4. onDone/onError 是否互斥，不会双触发？
5. release 是否四步齐全，aboutToDisappear 是否挂了 stop？
6. 失败是否落到 failedId 可重试？重试是否换新链接而非重放过期 URL？
7. 临时链接过期类失败是否引导到按需 generate-tts 路径（audioUrl undefined 的已知规划）？
8. 音频焦点至少做了最低配（audioInterrupt → stop）？

### 自我评估
- 正确性：4分 状态机九态、迁移约束、事件清单按公开文档通用口径书写；错误码数值与焦点接口细节明确标注以 SDK/真机为准，未编造具体码值。项目已知问题（竞态/滞留/临时链接）引自 A25 审查结论并标注出处。
- 完整性：4分 状态机、流播放链路、竞态管理、错误分类、释放时机、音频焦点、检查清单全覆盖；未展开 Seek/倍速/进度条类高级交互（与极简适老交互无关，已说明取舍）。
- 可复用性：5分 修复版骨架代码与七问清单可直接进 code review；错误分类表、释放四步、重试换链接策略可直接转工单。
- 字数：约3050字
- 使用模型：GLM-5.3-Flash
