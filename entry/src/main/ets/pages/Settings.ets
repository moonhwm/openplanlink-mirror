
import { hilog } from '@kit.PerformanceAnalysisKit';
import { SettingsService, FontSizeLevel } from '../services/SettingsService';

const TAG = 'StockPulse.Settings';
const DOMAIN = 0x0001;


@Component
export struct Settings {
  @State watchlist: string[] = [];
  @State broadcastEnabled: boolean = true;
  @State fontLevel: FontSizeLevel = 'standard';
  @State elderlyMode: boolean = true;
  @State newStockInput: string = '';
  private navStack: NavPathStack = new NavPathStack();

  // 字体档驱动字号
  private get titleSize(): number {
    return this.fontLevel === 'large' ? 40 : 34;
  }
  private get bodySize(): number {
    return this.fontLevel === 'large' ? 34 : 28;
  }
  private get labelSize(): number {
    return this.fontLevel === 'large' ? 26 : 22;
  }
  private get inputSize(): number {
    return this.fontLevel === 'large' ? 28 : 24;
  }

  aboutToAppear(): void {
    this.loadSettings();
  }

  private async loadSettings(): Promise<void> {
    this.watchlist = await SettingsService.getWatchlist();
    this.broadcastEnabled = await SettingsService.getBroadcastEnabled();
    this.elderlyMode = await SettingsService.getElderlyMode();
    this.fontLevel = await SettingsService.getFontSizeLevel();
  }

  private async addStock(): Promise<void> {
    const code = this.newStockInput.trim();
    if (code.length === 0) {
      return;
    }
    if (this.watchlist.includes(code)) {
      return;
    }
    this.watchlist = [...this.watchlist, code];
    this.newStockInput = '';
    await SettingsService.setWatchlist(this.watchlist);
    hilog.info(DOMAIN, TAG, `added stock ${code}, watchlist now ${this.watchlist.length} items`);
  }

  private async removeStock(code: string): Promise<void> {
    this.watchlist = this.watchlist.filter((s) => s !== code);
    await SettingsService.setWatchlist(this.watchlist);
    hilog.info(DOMAIN, TAG, `removed stock ${code}, watchlist now ${this.watchlist.length} items`);
  }

  private async toggleBroadcast(isOn: boolean): Promise<void> {
    this.broadcastEnabled = isOn;
    await SettingsService.setBroadcastEnabled(this.broadcastEnabled);
    hilog.info(DOMAIN, TAG, `broadcast ${this.broadcastEnabled ? 'enabled' : 'disabled'}`);
  }

  private async switchFontLevel(level: FontSizeLevel): Promise<void> {
    this.fontLevel = level;
    await SettingsService.setFontSizeLevel(level);
    hilog.info(DOMAIN, TAG, `font level set to ${level}`);
  }

  private async toggleElderlyMode(isOn: boolean): Promise<void> {
    this.elderlyMode = isOn;
    await SettingsService.setElderlyMode(isOn);
    // 适老化模式切换后重新加载字体档（setElderlyMode 内部已联动修改）
    this.fontLevel = await SettingsService.getFontSizeLevel();
    hilog.info(DOMAIN, TAG, `elderly mode ${isOn ? 'enabled' : 'disabled'}`);
  }

  build() {
    NavDestination() {
      Column() {
        // 顶栏：返回按钮 + 标题
        Row() {
          Text('← 返回')
            .fontSize(this.bodySize)
            .fontWeight(FontWeight.Bold)
            .fontColor($r('app.color.accent_gold'))
            .onClick(() => this.navStack.pop())
            .padding({ left: 8, right: 8, top: 8, bottom: 8 })
            .constraintSize({ minWidth: 48, minHeight: 48 })
          Text('设置')
            .fontSize(this.titleSize)
            .fontWeight(FontWeight.Bold)
            .fontColor($r('app.color.text_primary'))
            .margin({ left: 16 })
        }
        .width('100%')
        .padding({ left: 20, right: 20, top: 16, bottom: 12 })

        Scroll() {
          Column({ space: 24 }) {
            // ── 适老化模式 ──
            Column({ space: 12 }) {
              Text('适老化模式')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor($r('app.color.text_primary'))
                .width('100%')

              Row() {
                Text(this.elderlyMode ? '适老化已开' : '正常模式')
                  .fontSize(this.bodySize)
                  .fontColor(this.elderlyMode ? $r('app.color.accent_gold') : $r('app.color.text_primary'))
                  .layoutWeight(1)
                Toggle({ type: ToggleType.Switch, isOn: this.elderlyMode })
                  .onChange((isOn: boolean) => this.toggleElderlyMode(isOn))
                  .width(60)
                  .height(48)
              }
              .width('100%')

              Text(this.elderlyMode ?
                '适老化模式：大字大卡，点卡即听，界面极简' :
                '正常模式：标准字体，紧凑布局，信息更密')
                .fontSize(this.labelSize)
                .fontColor($r('app.color.text_secondary'))
                .width('100%')
            }
            .width('100%')
            .padding(20)
            .backgroundColor($r('app.color.card_background'))
            .borderRadius(16)

            // ── 自选股管理 ──
            Column({ space: 12 }) {
              Text('自选股管理')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor($r('app.color.text_primary'))
                .width('100%')

              // 添加输入区
              Row() {
                TextInput({ placeholder: '输入股票代码' })
                  .fontSize(this.inputSize)
                  .fontColor($r('app.color.text_primary'))
                  .placeholderColor($r('app.color.text_secondary'))
                  .layoutWeight(1)
                  .height(48)
                  .onChange((value: string) => {
                    this.newStockInput = value;
                  })
                Button('添加')
                  .fontSize(this.labelSize)
                  .fontColor(Color.White)
                  .backgroundColor($r('app.color.accent_gold'))
                  .height(48)
                  .margin({ left: 12 })
                  .onClick(() => this.addStock())
              }
              .width('100%')

              // 自选股列表
              if (this.watchlist.length > 0) {
                ForEach(this.watchlist, (code: string) => {
                  Row() {
                    Text(code)
                      .fontSize(this.bodySize)
                      .fontColor($r('app.color.text_primary'))
                      .layoutWeight(1)
                    Text('删除')
                      .fontSize(this.labelSize)
                      .fontColor($r('app.color.rise_red'))
                      .padding({ left: 12, right: 12, top: 8, bottom: 8 })
                      .constraintSize({ minWidth: 48, minHeight: 48 })
                      .onClick(() => this.removeStock(code))
                  }
                  .width('100%')
                  .padding({ left: 16, right: 16, top: 12, bottom: 12 })
                  .backgroundColor($r('app.color.card_background'))
                  .borderRadius(12)
                }, (code: string) => code)
              } else {
                Text('暂无自选股，添加后只显示关注的股票')
                  .fontSize(this.labelSize)
                  .fontColor($r('app.color.text_secondary'))
                  .width('100%')
                  .textAlign(TextAlign.Center)
                  .padding({ top: 16, bottom: 16 })
              }
            }
            .width('100%')
            .padding(20)
            .backgroundColor($r('app.color.card_background'))
            .borderRadius(16)

            // ── 播报开关 ──
            Column({ space: 12 }) {
              Text('播报开关')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor($r('app.color.text_primary'))
                .width('100%')

              Row() {
                Text(this.broadcastEnabled ? '播报已开' : '播报关')
                  .fontSize(this.bodySize)
                  .fontColor(this.broadcastEnabled ? $r('app.color.text_primary') : $r('app.color.rise_red'))
                  .layoutWeight(1)
                Toggle({ type: ToggleType.Switch, isOn: this.broadcastEnabled })
                  .onChange((isOn: boolean) => this.toggleBroadcast(isOn))
                  .width(60)
                  .height(48)
              }
              .width('100%')

              if (!this.broadcastEnabled) {
                Text('播报关后，通知拉起的自动播报将静默；卡片仍可手动点按收听')
                  .fontSize(this.labelSize)
                  .fontColor($r('app.color.text_secondary'))
                  .width('100%')
              }
            }
            .width('100%')
            .padding(20)
            .backgroundColor($r('app.color.card_background'))
            .borderRadius(16)

            // ── 字体大小（适老化模式开启时锁定特大） ──
            Column({ space: 12 }) {
              Text('字体大小')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor($r('app.color.text_primary'))
                .width('100%')

              if (this.elderlyMode) {
                // 适老化模式：锁定特大，提示由适老化模式控制
                Row() {
                  Text('特大（适老化模式锁定）')
                    .fontSize(this.bodySize)
                    .fontColor($r('app.color.accent_gold'))
                    .layoutWeight(1)
                }
                .width('100%')
                .padding({ left: 16, right: 16, top: 12, bottom: 12 })
                .backgroundColor($r('app.color.page_background'))
                .borderRadius(12)
              } else {
                // 正常模式：自由选择标准/特大
                Row() {
                  Button('标准')
                    .fontSize(this.labelSize)
                    .fontColor(this.fontLevel === 'standard' ? Color.White : $r('app.color.text_primary'))
                    .backgroundColor(this.fontLevel === 'standard' ? $r('app.color.accent_gold') : $r('app.color.card_background'))
                    .borderWidth(1)
                    .borderColor(this.fontLevel === 'standard' ? $r('app.color.accent_gold') : $r('app.color.text_secondary'))
                    .height(48)
                    .layoutWeight(1)
                    .onClick(() => this.switchFontLevel('standard'))
                  Button('特大')
                    .fontSize(this.labelSize)
                    .fontColor(this.fontLevel === 'large' ? Color.White : $r('app.color.text_primary'))
                    .backgroundColor(this.fontLevel === 'large' ? $r('app.color.accent_gold') : $r('app.color.card_background'))
                    .borderWidth(1)
                    .borderColor(this.fontLevel === 'large' ? $r('app.color.accent_gold') : $r('app.color.text_secondary'))
                    .height(48)
                    .layoutWeight(1)
                    .margin({ left: 12 })
                    .onClick(() => this.switchFontLevel('large'))
                }
                .width('100%')
              }
            }
            .width('100%')
            .padding(20)
            .backgroundColor($r('app.color.card_background'))
            .borderRadius(16)
          }
          .width('100%')
          .padding({ left: 16, right: 16 })
        }
        .width('100%')
        .layoutWeight(1)
      }
      .width('100%')
      .height('100%')
      .backgroundColor($r('app.color.page_background'))
    }
    .hideTitleBar(true)
    .onReady((context: NavDestinationContext) => {
      this.navStack = context.pathStack
    })
  }
}