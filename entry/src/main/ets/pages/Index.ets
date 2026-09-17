
import { hilog } from '@kit.PerformanceAnalysisKit';
import { AlertItem } from '../model/AlertItem';
import { AlertPoller } from '../services/AlertPoller';
import { AudioPlayer } from '../services/AudioPlayer';
import { SettingsService, FontSizeLevel, ThemeMode, ThemeColors, PlayHistoryItem } from '../services/SettingsService';
import { Settings } from './Settings';

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
  @State fontLevel: FontSizeLevel = 'standard';
  @State elderlyMode: boolean = true;
  @State broadcastEnabled: boolean = true;
  @State broadcastOffVisible: boolean = false;
  @State themeMode: ThemeMode = 'night';
  @State autoThemeEnabled: boolean = true;
  @State dndEnabled: boolean = false;
  @State dndActive: boolean = false;
  @State watchlist: string[] = [];
  @State readAlertIds: string[] = [];
  @State playHistory: PlayHistoryItem[] = [];
  private timer: number = -1;
  private consecutiveFailures: number = 0;
  private navStack: NavPathStack = new NavPathStack();

  // 字体档驱动字号
  private get titleSize(): number {
    return this.fontLevel === 'large' ? 40 : 34;
  }
  private get cardTitleSize(): number {
    return this.fontLevel === 'large' ? 34 : 30;
  }
  private get headlineSize(): number {
    return this.fontLevel === 'large' ? 34 : 28;
  }
  private get detailSize(): number {
    return this.fontLevel === 'large' ? 26 : 22;
  }
  private get statusSize(): number {
    return this.fontLevel === 'large' ? 24 : 20;
  }
  private get playBtnSize(): number {
    return this.fontLevel === 'large' ? 32 : 28;
  }
  private get badgeSize(): number {
    return this.fontLevel === 'large' ? 20 : 18;
  }

  // 适老化模式驱动布局参数
  private get cardSpace(): number {
    return this.elderlyMode ? 20 : 12;
  }
  private get cardPadding(): number {
    return this.elderlyMode ? 20 : 16;
  }
  private get cardInnerSpace(): number {
    return this.elderlyMode ? 12 : 8;
  }
  private get topBarPaddingTop(): number {
    return this.elderlyMode ? 16 : 12;
  }
  private get topBarPaddingBottom(): number {
    return this.elderlyMode ? 12 : 8;
  }
  private get listSidePadding(): number {
    return this.elderlyMode ? 16 : 12;
  }

  // 主题颜色（夜间/白天动态切换）
  private get theme(): ThemeColors {
    return SettingsService.getThemeColors(this.themeMode);
  }

  aboutToAppear(): void {
    this.loadSettings();
    this.pollLoop();
    this.checkPendingAlertId();
  }

  onPageShow(): void {
    // 后台拉起路径修复（白皮书 §3.3.2）+ 设置页返回后刷新配置
    this.loadSettings();
    this.checkPendingAlertId();
  }

  aboutToDisappear(): void {
    if (this.timer >= 0) {
      clearTimeout(this.timer);
      this.timer = -1;
    }
    AudioPlayer.stop();
  }

  private async loadSettings(): Promise<void> {
    this.elderlyMode = await SettingsService.getElderlyMode();
    this.fontLevel = await SettingsService.getFontSizeLevel();
    this.broadcastEnabled = await SettingsService.getBroadcastEnabled();
    this.broadcastOffVisible = !this.broadcastEnabled;
    this.autoThemeEnabled = await SettingsService.getAutoThemeEnabled();
    if (this.autoThemeEnabled) {
      this.themeMode = SettingsService.computeAutoThemeMode();
    } else {
      this.themeMode = await SettingsService.getThemeMode();
    }
    this.dndEnabled = await SettingsService.getDndEnabled();
    const dndStart = await SettingsService.getDndStartHour();
    const dndEnd = await SettingsService.getDndEndHour();
    this.dndActive = SettingsService.isDndActive(this.dndEnabled, dndStart, dndEnd);
    this.watchlist = await SettingsService.getWatchlist();
    this.readAlertIds = await SettingsService.getReadAlertIds();
    this.playHistory = await SettingsService.getPlayHistory();
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
        // 自选股过滤：有自选股列表时只显示列表中的股票
        let filtered = result.items;
        if (this.watchlist.length > 0) {
          filtered = result.items.filter((it) => this.watchlist.includes(it.symbol));
        }

        // 刷新后检查正在播放/加载的 alertId 是否还在新列表中（白皮书 §3.1.4）
        if (this.playingId && !filtered.find((it) => it.alertId === this.playingId)) {
          AudioPlayer.stop();
          this.playingId = '';
        }
        if (this.loadingId && !filtered.find((it) => it.alertId === this.loadingId)) {
          // 加载中的卡片被服务端撤下：停止 prepare 并复位，防止 prepare 完成后设置已失效的 playingId
          AudioPlayer.stop();
          this.loadingId = '';
        }
        if (this.failedId && !filtered.find((it) => it.alertId === this.failedId)) {
          this.failedId = '';
        }
        this.items = filtered;
      } else {
        // 空态：服务端连通但无异动（白皮书 §3.2.3）
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
      hilog.info(DOMAIN, TAG, 'rate-limited, keeping current items');
    } else {
      this.consecutiveFailures++;
      if (this.consecutiveFailures >= 2) {
        this.connectionBroken = true;
      }
    }
  }

  private playById(id: string): void {
    const hit = this.items.find((it) => it.alertId === id);
    if (!hit) {
      hilog.info(DOMAIN, TAG, `pendingAlertId ${id} not in current list, silently cleared`);
      return;
    }
    if (!hit.audioUrl) {
      hilog.info(DOMAIN, TAG, `pendingAlertId ${id} has no audioUrl, silently skipped`);
      return;
    }
    // 播报开关关闭时：自动播报静默跳过（白皮书 R2 §2）
    if (!this.broadcastEnabled) {
      hilog.info(DOMAIN, TAG, `broadcast disabled, auto-play skipped for ${id}`);
      return;
    }
    // 免打扰时段：自动播报静默跳过（用户手动点击仍可播放）
    if (this.dndActive) {
      hilog.info(DOMAIN, TAG, `dnd active, auto-play skipped for ${id}`);
      return;
    }
    this.togglePlay(hit);
  }

  private async togglePlay(item: AlertItem): Promise<void> {
    if (!item.audioUrl) {
      return;
    }
    if (this.loadingId === item.alertId) {
      return;
    }
    if (this.playingId === item.alertId) {
      this.playingId = '';
      AudioPlayer.stop();
      return;
    }
    if (this.playingId) {
      AudioPlayer.stop();
      this.playingId = '';
    }

    if (this.failedId === item.alertId) {
      this.failedId = '';
    }

    this.loadingId = item.alertId;

    try {
      await AudioPlayer.play(
        item.audioUrl,
        () => {
          this.playingId = '';
        },
        () => {
          this.loadingId = '';
          this.playingId = '';
          this.failedId = item.alertId;
        }
      );
      // refresh 可能在 await 期间清除了 loadingId（卡片被服务端撤下）——此时不应设置 playingId
      if (this.loadingId !== item.alertId) {
        return;
      }
      this.loadingId = '';
      this.playingId = item.alertId;
      // 标记已读 + 记录播报历史
      SettingsService.markAlertRead(item.alertId);
      if (!this.readAlertIds.includes(item.alertId)) {
        this.readAlertIds = [...this.readAlertIds, item.alertId];
      }
      const historyItem: PlayHistoryItem = {
        alertId: item.alertId,
        symbol: item.symbol,
        name: item.name,
        headline: item.headline,
        ts: Date.now(),
        alertTs: item.ts,
      };
      SettingsService.addPlayHistory(historyItem);
      this.playHistory = [historyItem, ...this.playHistory.filter((it) => it.alertId !== item.alertId)].slice(0, 50);
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `togglePlay failed: ${(e as Error).message}`);
      this.loadingId = '';
      this.playingId = '';
      this.failedId = item.alertId;
    }
  }

  private dirColor(d: string): string {
    if (d === 'up') {
      return this.theme.riseRed;
    }
    if (d === 'down') {
      return this.theme.fallGreen;
    }
    return this.theme.textSecondary;
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
    Navigation(this.navStack) {
      Column() {
        // 顶栏：标题 + 播报关提示 + 刷新时刻 + 设置入口
        Row() {
          Text('铃语')
            .fontSize(this.titleSize)
            .fontWeight(FontWeight.Bold)
            .fontColor(this.theme.textPrimary)
          if (this.broadcastOffVisible) {
            Text('播报关')
              .fontSize(this.statusSize)
              .fontColor(this.theme.riseRed)
              .margin({ left: 8 })
          }
          if (this.dndActive) {
            Text('免打扰')
              .fontSize(this.statusSize)
              .fontColor(this.theme.accentGold)
              .margin({ left: 8 })
          }
          Blank()
          Column() {
            Text(this.lastRefresh)
              .fontSize(this.statusSize)
              .fontColor(this.theme.textSecondary)
            if (this.connectionBroken) {
              Text('连接中断，显示旧数据')
                .fontSize(this.statusSize)
                .fontColor(this.theme.textSecondary)
            }
          }
          // 设置入口按钮（热区 ≥48vp）
          Text('设置')
            .fontSize(this.statusSize)
            .fontWeight(FontWeight.Bold)
            .fontColor(this.theme.accentGold)
            .padding({ left: 12, right: 12, top: 10, bottom: 10 })
            .constraintSize({ minWidth: 48, minHeight: 48 })
            .margin({ left: 12 })
            .onClick(() => this.navStack.pushPath({ name: 'pages/Settings' }))
        }
        .width('100%')
        .padding({ left: 20, right: 20, top: this.topBarPaddingTop, bottom: this.topBarPaddingBottom })

        if (this.items.length > 0) {
          List({ space: this.cardSpace }) {
            ForEach(this.items, (item: AlertItem) => {
              ListItem() {
                Column({ space: this.cardInnerSpace }) {
                  Row() {
                    // 未读标记：小圆点
                    if (!this.readAlertIds.includes(item.alertId)) {
                      Circle({ width: 10, height: 10 })
                        .fill(this.theme.accentGold)
                        .margin({ right: 8 })
                    }
                    Text(this.dirLabel(item.direction))
                      .fontSize(this.cardTitleSize)
                      .fontWeight(FontWeight.Bold)
                      .fontColor(Color.White)
                      .backgroundColor(this.dirColor(item.direction))
                      .borderRadius(10)
                      .padding({ left: 14, right: 14, top: 4, bottom: 4 })
                    Text(item.name)
                      .fontSize(this.cardTitleSize)
                      .fontWeight(FontWeight.Bold)
                      .fontColor(this.theme.textPrimary)
                      .margin({ left: 12 })
                      .layoutWeight(1)
                      .maxLines(1)
                      .textOverflow({ overflow: TextOverflow.Ellipsis })
                    if (item.kind === 'signal') {
                      Text('自家信号')
                        .fontSize(this.badgeSize)
                        .fontColor(this.theme.accentGold)
                        .border({ width: 1, color: this.theme.accentGold })
                        .borderRadius(6)
                        .padding({ left: 8, right: 8, top: 2, bottom: 2 })
                        .margin({ left: 10 })
                    }
                    if (item.audioUrl) {
                      Text(this.loadingId === item.alertId ? '…' :
                        this.playingId === item.alertId ? '■ 停' : '▶ 听')
                        .fontSize(this.playBtnSize)
                        .fontWeight(FontWeight.Bold)
                        .fontColor(this.theme.accentGold)
                    }
                  }
                  .width('100%')

                  Text(item.headline)
                    .fontSize(this.headlineSize)
                    .fontColor(this.theme.textPrimary)
                    .width('100%')

                  if (item.detail.length > 0) {
                    Text(item.detail)
                      .fontSize(this.detailSize)
                      .fontColor(this.theme.textSecondary)
                      .width('100%')
                  }

                  if (this.failedId === item.alertId) {
                    Text('语音加载失败，点重试')
                      .fontSize(this.detailSize)
                      .fontColor(this.theme.riseRed)
                      .width('100%')
                  }
                }
                .width('100%')
                .padding(this.cardPadding)
                .backgroundColor(this.theme.cardBackground)
                .borderRadius(16)
                .onClick(() => this.togglePlay(item))
              }
            }, (item: AlertItem) => item.alertId)
          }
          .width('100%')
          .layoutWeight(1)
          .padding({ left: this.listSidePadding, right: this.listSidePadding })
        } else {
          Column() {
            Text('今日暂无异动')
              .fontSize(this.headlineSize)
              .fontColor(this.theme.textSecondary)
            Text('监测进行中，有新情况会自动推送')
              .fontSize(this.statusSize)
              .fontColor(this.theme.textSecondary)
              .margin({ top: 12 })
          }
          .width('100%')
          .layoutWeight(1)
          .justifyContent(FlexAlign.Center)
        }
      }
      .width('100%')
      .height('100%')
      .backgroundColor(this.theme.pageBackground)
    }
    .navDestination((name: string) => {
      if (name === 'pages/Settings') {
        return Settings()
      }
      return null
    })
    .hideTitleBar(true)
    .mode(NavigationMode.Stack)
  }
}
