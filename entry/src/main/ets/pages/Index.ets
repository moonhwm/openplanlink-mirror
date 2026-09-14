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
  @State lastRefresh: string = '未连接';
  private timer: number = -1;

  aboutToAppear(): void {
    this.refresh();
    this.timer = setInterval(() => this.refresh(), 5000);
    const pending = AppStorage.get('pendingAlertId') as string | undefined;
    if (pending) {
      AppStorage.delete('pendingAlertId');
      this.playById(pending);
    }
  }

  aboutToDisappear(): void {
    if (this.timer >= 0) {
      clearInterval(this.timer);
      this.timer = -1;
    }
    AudioPlayer.stop();
  }

  private async refresh(): Promise<void> {
    const items = await AlertPoller.fetchLatest();
    if (items.length > 0) {
      this.items = items;
      const d = new Date();
      this.lastRefresh = `${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
    }
  }

  private playById(id: string): void {
    const hit = this.items.find((it) => it.alertId === id);
    if (hit?.audioUrl) {
      this.togglePlay(hit);
    }
  }

  private togglePlay(item: AlertItem): void {
    if (!item.audioUrl) {
      return;
    }
    if (this.playingId === item.alertId) {
      this.playingId = '';
      AudioPlayer.stop();
      return;
    }
    this.playingId = item.alertId;
    AudioPlayer.play(item.audioUrl, () => {
      this.playingId = '';
    });
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
      // 顶栏：大字标题 + 刷新时刻
      Row() {
        Text('行情播报')
          .fontSize(34)
          .fontWeight(FontWeight.Bold)
          .fontColor($r('app.color.text_primary'))
        Blank()
        Text(this.lastRefresh)
          .fontSize(20)
          .fontColor($r('app.color.text_secondary'))
      }
      .width('100%')
      .padding({ left: 20, right: 20, top: 16, bottom: 12 })

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
                if (item.kind === 'signal') {
                  Text('自家信号')
                    .fontSize(18)
                    .fontColor($r('app.color.accent_gold'))
                    .border({ width: 1, color: $r('app.color.accent_gold') })
                    .borderRadius(6)
                    .padding({ left: 8, right: 8, top: 2, bottom: 2 })
                    .margin({ left: 10 })
                }
                Blank()
                if (item.audioUrl) {
                  Text(this.playingId === item.alertId ? '■ 停' : '▶ 听')
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
    }
    .width('100%')
    .height('100%')
    .backgroundColor($r('app.color.page_background'))
  }
}
