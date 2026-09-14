import { hilog } from '@kit.PerformanceAnalysisKit';
import { AlertItem } from '../model/AlertItem';
import { AlertPoller } from '../services/AlertPoller';
import { AudioPlayer } from '../services/AudioPlayer';

const TAG = 'StockPulse.Index';
const DOMAIN = 0x0001;

/** 服务未连通时的演示卡（保证首屏可用，不产生误导：明确标「示例」） */
const DEMO_ITEMS: AlertItem[] = [
  {
    alertId: 'demo-1',
    ts: 0,
    symbol: '600176',
    name: '中国巨石',
    direction: 'up',
    headline: '示例：中国巨石 2 分钟上涨 2.3%',
    detail: '示例数据，服务器接通后自动换成真实异动',
  }
];

@Entry
@Component
struct Index {
  @State items: AlertItem[] = DEMO_ITEMS;
  @State playingId: string = '';
  @State loadingId: string = '';
  @State failedId: string = '';
  @State lastRefresh: string = '未连接';
  @State connectionBroken: boolean = false;
  @State isDemoMode: boolean = true;
  private timer: number = -1;
  private consecutiveFailures: number = 0;

  aboutToAppear(): void {
    this.pollLoop();
    this.checkPendingAlertId();
  }

  onPageShow(): void {
    // 后台拉起路径修复（白皮书 §3.3.2）：页面已存在时 aboutToAppear 不会再跑，
    // onPageShow 补检 pendingAlertId，确保 onNewWant 写入的 alertId 不滞留
    this.checkPendingAlertId();
  }

  aboutToDisappear(): void {
    if (this.timer >= 0) {
      clearTimeout(this.timer);
      this.timer = -1;
    }
    AudioPlayer.stop();
  }

  private checkPendingAlertId(): void {
    const pending = AppStorage.get('pendingAlertId') as string | undefined;
    if (pending) {
      AppStorage.delete('pendingAlertId');
      this.playById(pending);
    }
  }

  private async pollLoop(): Promise<void> {
    await this.refresh();
    this.timer = setTimeout(() => this.pollLoop(), AlertPoller.getInterval());
  }

  private async refresh(): Promise<void> {
    const result = await AlertPoller.fetchLatest();
    if (result.ok) {
      this.consecutiveFailures = 0;
      this.connectionBroken = false;
      this.isDemoMode = false;

      if (result.items.length > 0) {
        // 刷新后检查正在播放/加载的 alertId 是否还在新列表中（白皮书 §3.1.4）
        if (this.playingId && !result.items.find((it) => it.alertId === this.playingId)) {
          AudioPlayer.stop();
          this.playingId = '';
        }
        if (this.loadingId && !result.items.find((it) => it.alertId === this.loadingId)) {
          this.loadingId = '';
        }
        // 成功刷新清除失败提示（白皮书 §3.1.2：下一轮成功刷新后清除）
        if (this.failedId && !result.items.find((it) => it.alertId === this.failedId)) {
          this.failedId = '';
        }
        this.items = result.items;
      } else {
        // 空态：服务端连通但无异动（白皮书 §3.2.3）
        // 停止正在播放的音频（异动已被服务端撤下）
        if (this.playingId) {
          AudioPlayer.stop();
          this.playingId = '';
        }
        this.loadingId = '';
        this.failedId = '';
        this.items = [];
      }

      const d = new Date();
      this.lastRefresh = `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
    } else if (result.rateLimited) {
      // 429 限流：不计入连接中断提示，保留旧卡片（白皮书 §3.2.4）
      hilog.info(DOMAIN, TAG, 'rate-limited, keeping current items');
    } else {
      this.consecutiveFailures++;
      // 连续两轮 ok=false 才显示连接中断（白皮书 §3.2.2）
      if (this.consecutiveFailures >= 2) {
        this.connectionBroken = true;
      }
      // ok=false：保留旧卡片，严禁清空为空白页（白皮书 §3.2.2）
    }
  }

  private playById(id: string): void {
    const hit = this.items.find((it) => it.alertId === id);
    if (!hit) {
      // 目标 alertId 不在当前列表，静默清除（白皮书 §3.1.3）
      hilog.info(DOMAIN, TAG, `pendingAlertId ${id} not in current list, silently cleared`);
      return;
    }
    if (!hit.audioUrl) {
      // 目标卡无 audioUrl，静默跳过（白皮书 §3.1.3）
      hilog.info(DOMAIN, TAG, `pendingAlertId ${id} has no audioUrl, silently skipped`);
      return;
    }
    this.togglePlay(hit);
  }

  private async togglePlay(item: AlertItem): Promise<void> {
    if (!item.audioUrl) {
      return;
    }
    // 防连击：正在加载时忽略点击（白皮书 §3.1.1）
    if (this.loadingId === item.alertId) {
      return;
    }
    // 正在播放同一卡片：停止
    if (this.playingId === item.alertId) {
      this.playingId = '';
      AudioPlayer.stop();
      return;
    }
    // 正在播放其他卡片：先停旧再起新
    if (this.playingId) {
      AudioPlayer.stop();
      this.playingId = '';
    }

    // 清除该卡之前的失败提示（白皮书 §3.1.2：下一次点击清除）
    if (this.failedId === item.alertId) {
      this.failedId = '';
    }

    // 进入加载状态（白皮书 §3.1.1）
    this.loadingId = item.alertId;

    try {
      await AudioPlayer.play(
        item.audioUrl,
        () => {
          // 播放完成回调
          this.playingId = '';
        },
        () => {
          // 播放失败回调（AVPlayer error 事件）
          this.loadingId = '';
          this.playingId = '';
          this.failedId = item.alertId;
        }
      );
      // prepare + play 成功：loadingId 转 playingId（白皮书 §3.1.1）
      this.loadingId = '';
      this.playingId = item.alertId;
    } catch (e) {
      // prepare/play reject（白皮书 §3.1.2）
      hilog.warn(DOMAIN, TAG, `togglePlay failed: ${(e as Error).message}`);
      this.loadingId = '';
      this.playingId = '';
      this.failedId = item.alertId;
    }
  }

  private dirColor(d: string): ResourceColor {
    if (d === 'up') {
      return $r('app.color.rise_red');
    }
    if (d === 'down') {
      return $r('app.color.fall_green');
    }
    return $r('app.color.text_secondary');
  }

  private dirLabel(d: string): string {
    if (d === 'up') {
      return '涨';
    }
    if (d === 'down') {
      return '跌';
    }
    return '平';
  }

  build() {
    Column() {
      // 顶栏：大字标题 + 刷新时刻 + 连接中断提示
      Row() {
        Text('行情播报')
          .fontSize(34)
          .fontWeight(FontWeight.Bold)
          .fontColor($r('app.color.text_primary'))
        Blank()
        Column() {
          Text(this.lastRefresh)
            .fontSize(20)
            .fontColor($r('app.color.text_secondary'))
          if (this.connectionBroken) {
            Text('连接中断，显示旧数据')
              .fontSize(20)
              .fontColor($r('app.color.text_secondary'))
          }
        }
      }
      .width('100%')
      .padding({ left: 20, right: 20, top: 16, bottom: 12 })

      if (this.items.length > 0) {
        // 异动卡片流：一张卡=一条白话事实，点卡即听
        List({ space: 16 }) {
          ForEach(this.items, (item: AlertItem) => {
            ListItem() {
              Column({ space: 10 }) {
                Row() {
                  Text(this.dirLabel(item.direction))
                    .fontSize(30)
                    .fontWeight(FontWeight.Bold)
                    .fontColor(Color.White)
                    .backgroundColor(this.dirColor(item.direction))
                    .borderRadius(10)
                    .padding({ left: 14, right: 14, top: 4, bottom: 4 })
                  Text(item.name)
                    .fontSize(30)
                    .fontWeight(FontWeight.Bold)
                    .fontColor($r('app.color.text_primary'))
                    .margin({ left: 12 })
                    .layoutWeight(1)
                    .maxLines(1)
                    .textOverflow({ overflow: TextOverflow.Ellipsis })
                  if (item.kind === 'signal') {
                    Text('自家信号')
                      .fontSize(18)
                      .fontColor($r('app.color.accent_gold'))
                      .border({ width: 1, color: $r('app.color.accent_gold') })
                      .borderRadius(6)
                      .padding({ left: 8, right: 8, top: 2, bottom: 2 })
                      .margin({ left: 10 })
                  }
                  if (item.audioUrl) {
                    Text(this.loadingId === item.alertId ? '…' :
                      this.playingId === item.alertId ? '■ 停' : '▶ 听')
                      .fontSize(28)
                      .fontWeight(FontWeight.Bold)
                      .fontColor($r('app.color.accent_gold'))
                  }
                }
                .width('100%')

                Text(item.headline)
                  .fontSize(28)
                  .fontColor($r('app.color.text_primary'))
                  .width('100%')

                if (item.detail.length > 0) {
                  Text(item.detail)
                    .fontSize(22)
                    .fontColor($r('app.color.text_secondary'))
                    .width('100%')
                }

                // 播放失败提示（白皮书 §3.1.2）
                if (this.failedId === item.alertId) {
                  Text('语音加载失败，点重试')
                    .fontSize(22)
                    .fontColor($r('app.color.rise_red'))
                    .width('100%')
                }
              }
              .width('100%')
              .padding(20)
              .backgroundColor($r('app.color.card_background'))
              .borderRadius(16)
              .onClick(() => this.togglePlay(item))
            }
          }, (item: AlertItem) => item.alertId)
        }
        .width('100%')
        .layoutWeight(1)
        .padding({ left: 16, right: 16 })
      } else {
        // 空态：服务连通但无异动（白皮书 §3.2.3）
        // 与"服务未连通显示示例卡"是两个独立分支，互不覆盖
        Column() {
          Text('今日暂无异动')
            .fontSize(30)
            .fontColor($r('app.color.text_secondary'))
          Text('监测进行中，有新情况会自动推送')
            .fontSize(20)
            .fontColor($r('app.color.text_secondary'))
            .margin({ top: 12 })
        }
        .width('100%')
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor($r('app.color.page_background'))
  }
}
