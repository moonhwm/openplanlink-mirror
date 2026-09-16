
import { hilog } from '@kit.PerformanceAnalysisKit';
import { SettingsService, FontSizeLevel, ThemeMode, ThemeColors } from '../services/SettingsService';

const TAG = 'StockPulse.Settings';
const DOMAIN = 0x0001;


@Component
export struct Settings {
  @State watchlist: string[] = [];
  @State broadcastEnabled: boolean = true;
  @State fontLevel: FontSizeLevel = 'standard';
  @State elderlyMode: boolean = true;
  @State themeMode: ThemeMode = 'night';
  @State dndEnabled: boolean = false;
  @State dndStartHour: number = 22;
  @State dndEndHour: number = 8;
  @State newStockInput: string = '';
  private navStack: NavPathStack | null = null;

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

  // 主题颜色
  private get theme(): ThemeColors {
    return SettingsService.getThemeColors(this.themeMode);
  }

  aboutToAppear(): void {
    this.loadSettings();
  }

  private async loadSettings(): Promise<void> {
    this.watchlist = await SettingsService.getWatchlist();
    this.broadcastEnabled = await SettingsService.getBroadcastEnabled();
    this.elderlyMode = await SettingsService.getElderlyMode();
    this.fontLevel = await SettingsService.getFontSizeLevel();
    this.themeMode = await SettingsService.getThemeMode();
    this.dndEnabled = await SettingsService.getDndEnabled();
    this.dndStartHour = await SettingsService.getDndStartHour();
    this.dndEndHour = await SettingsService.getDndEndHour();
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
    this.fontLevel = await SettingsService.getFontSizeLevel();
    hilog.info(DOMAIN, TAG, `elderly mode ${isOn ? 'enabled' : 'disabled'}`);
  }

  private async toggleThemeMode(isDay: boolean): Promise<void> {
    this.themeMode = isDay ? 'day' : 'night';
    await SettingsService.setThemeMode(this.themeMode);
    hilog.info(DOMAIN, TAG, `theme mode set to ${this.themeMode}`);
  }

  private async toggleDnd(isOn: boolean): Promise<void> {
    this.dndEnabled = isOn;
    await SettingsService.setDndEnabled(this.dndEnabled);
    hilog.info(DOMAIN, TAG, `dnd ${isOn ? 'enabled' : 'disabled'}`);
  }

  build() {
    NavDestination() {
      Column() {
        // 顶栏：返回按钮 + 标题
        Row() {
          Text('← 返回')
            .fontSize(this.bodySize)
            .fontWeight(FontWeight.Bold)
            .fontColor(this.theme.accentGold)
            .onClick(() => {
              if (this.navStack) {
                this.navStack.pop();
              }
            })
            .padding({ left: 8, right: 8, top: 8, bottom: 8 })
            .constraintSize({ minWidth: 48, minHeight: 48 })
          Text('设置')
            .fontSize(this.titleSize)
            .fontWeight(FontWeight.Bold)
            .fontColor(this.theme.textPrimary)
            .margin({ left: 16 })
        }
        .width('100%')
        .padding({ left: 20, right: 20, top: 16, bottom: 12 })

        Scroll() {
          Column({ space: 24 }) {
            // ── 显示模式（夜间/白天） ──
            Column({ space: 12 }) {
              Text('显示模式')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.theme.textPrimary)
                .width('100%')

              Row() {
                Button('夜间')
                  .fontSize(this.labelSize)
                  .fontColor(this.themeMode === 'night' ? Color.White : this.theme.textPrimary)
                  .backgroundColor(this.themeMode === 'night' ? this.theme.accentGold : this.theme.cardBackground)
                  .borderWidth(1)
                  .borderColor(this.themeMode === 'night' ? this.theme.accentGold : this.theme.textSecondary)
                  .height(48)
                  .layoutWeight(1)
                  .onClick(() => this.toggleThemeMode(false))
                Button('白天')
                  .fontSize(this.labelSize)
                  .fontColor(this.themeMode === 'day' ? Color.White : this.theme.textPrimary)
                  .backgroundColor(this.themeMode === 'day' ? this.theme.accentGold : this.theme.cardBackground)
                  .borderWidth(1)
                  .borderColor(this.themeMode === 'day' ? this.theme.accentGold : this.theme.textSecondary)
                  .height(48)
                  .layoutWeight(1)
                  .margin({ left: 12 })
                  .onClick(() => this.toggleThemeMode(true))
              }
              .width('100%')

              Text(this.themeMode === 'night' ?
                '夜间模式：深色底，高对比，护眼省电' :
                '白天模式：浅色底，清晰明亮，适合日间')
                .fontSize(this.labelSize)
                .fontColor(this.theme.textSecondary)
                .width('100%')
            }
            .width('100%')
            .padding(20)
            .backgroundColor(this.theme.cardBackground)
            .borderRadius(16)

            // ── 适老化模式 ──
            Column({ space: 12 }) {
              Text('适老化模式')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.theme.textPrimary)
                .width('100%')

              Row() {
                Text(this.elderlyMode ? '适老化已开' : '正常模式')
                  .fontSize(this.bodySize)
                  .fontColor(this.elderlyMode ? this.theme.accentGold : this.theme.textPrimary)
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
                .fontColor(this.theme.textSecondary)
                .width('100%')
            }
            .width('100%')
            .padding(20)
            .backgroundColor(this.theme.cardBackground)
            .borderRadius(16)

            // ── 免打扰模式 ──
            Column({ space: 12 }) {
              Text('免打扰')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.theme.textPrimary)
                .width('100%')

              Row() {
                Text(this.dndEnabled ? '免打扰已开' : '免打扰关')
                  .fontSize(this.bodySize)
                  .fontColor(this.dndEnabled ? this.theme.accentGold : this.theme.textPrimary)
                  .layoutWeight(1)
                Toggle({ type: ToggleType.Switch, isOn: this.dndEnabled })
                  .onChange((isOn: boolean) => this.toggleDnd(isOn))
                  .width(60)
                  .height(48)
              }
              .width('100%')

              if (this.dndEnabled) {
                Text(`免打扰时段：${this.dndStartHour}:00 - ${this.dndEndHour}:00`)
                  .fontSize(this.labelSize)
                  .fontColor(this.theme.textSecondary)
                  .width('100%')

                Text('免打扰时段内，推送通知的自动播报将静默；卡片仍可手动点按收听')
                  .fontSize(this.labelSize)
                  .fontColor(this.theme.textSecondary)
                  .width('100%')
              }
            }
            .width('100%')
            .padding(20)
            .backgroundColor(this.theme.cardBackground)
            .borderRadius(16)

            // ── 自选股管理 ──
            Column({ space: 12 }) {
              Text('自选股管理')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.theme.textPrimary)
                .width('100%')

              Row() {
                TextInput({ placeholder: '输入股票代码' })
                  .fontSize(this.inputSize)
                  .fontColor(this.theme.textPrimary)
                  .placeholderColor(this.theme.textSecondary)
                  .layoutWeight(1)
                  .height(48)
                  .onChange((value: string) => {
                    this.newStockInput = value;
                  })
                Button('添加')
                  .fontSize(this.labelSize)
                  .fontColor(Color.White)
                  .backgroundColor(this.theme.accentGold)
                  .height(48)
                  .margin({ left: 12 })
                  .onClick(() => this.addStock())
              }
              .width('100%')

              if (this.watchlist.length > 0) {
                ForEach(this.watchlist, (code: string) => {
                  Row() {
                    Text(code)
                      .fontSize(this.bodySize)
                      .fontColor(this.theme.textPrimary)
                      .layoutWeight(1)
                    Text('删除')
                      .fontSize(this.labelSize)
                      .fontColor(this.theme.riseRed)
                      .padding({ left: 12, right: 12, top: 8, bottom: 8 })
                      .constraintSize({ minWidth: 48, minHeight: 48 })
                      .onClick(() => this.removeStock(code))
                  }
                  .width('100%')
                  .padding({ left: 16, right: 16, top: 12, bottom: 12 })
                  .backgroundColor(this.theme.pageBackground)
                  .borderRadius(12)
                }, (code: string) => code)
              } else {
                Text('暂无自选股，添加后只显示关注的股票')
                  .fontSize(this.labelSize)
                  .fontColor(this.theme.textSecondary)
                  .width('100%')
                  .textAlign(TextAlign.Center)
                  .padding({ top: 16, bottom: 16 })
              }
            }
            .width('100%')
            .padding(20)
            .backgroundColor(this.theme.cardBackground)
            .borderRadius(16)

            // ── 播报开关 ──
            Column({ space: 12 }) {
              Text('播报开关')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.theme.textPrimary)
                .width('100%')

              Row() {
                Text(this.broadcastEnabled ? '播报已开' : '播报关')
                  .fontSize(this.bodySize)
                  .fontColor(this.broadcastEnabled ? this.theme.textPrimary : this.theme.riseRed)
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
                  .fontColor(this.theme.textSecondary)
                  .width('100%')
              }
            }
            .width('100%')
            .padding(20)
            .backgroundColor(this.theme.cardBackground)
            .borderRadius(16)

            // ── 字体大小（适老化模式开启时锁定特大） ──
            Column({ space: 12 }) {
              Text('字体大小')
                .fontSize(this.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(this.theme.textPrimary)
                .width('100%')

              if (this.elderlyMode) {
                Row() {
                  Text('特大（适老化模式锁定）')
                    .fontSize(this.bodySize)
                    .fontColor(this.theme.accentGold)
                    .layoutWeight(1)
                }
                .width('100%')
                .padding({ left: 16, right: 16, top: 12, bottom: 12 })
                .backgroundColor(this.theme.pageBackground)
                .borderRadius(12)
              } else {
                Row() {
                  Button('标准')
                    .fontSize(this.labelSize)
                    .fontColor(this.fontLevel === 'standard' ? Color.White : this.theme.textPrimary)
                    .backgroundColor(this.fontLevel === 'standard' ? this.theme.accentGold : this.theme.cardBackground)
                    .borderWidth(1)
                    .borderColor(this.fontLevel === 'standard' ? this.theme.accentGold : this.theme.textSecondary)
                    .height(48)
                    .layoutWeight(1)
                    .onClick(() => this.switchFontLevel('standard'))
                  Button('特大')
                    .fontSize(this.labelSize)
                    .fontColor(this.fontLevel === 'large' ? Color.White : this.theme.textPrimary)
                    .backgroundColor(this.fontLevel === 'large' ? this.theme.accentGold : this.theme.cardBackground)
                    .borderWidth(1)
                    .borderColor(this.fontLevel === 'large' ? this.theme.accentGold : this.theme.textSecondary)
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
            .backgroundColor(this.theme.cardBackground)
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
      .backgroundColor(this.theme.pageBackground)
    }
    .hideTitleBar(true)
    .onReady((context: NavDestinationContext) => {
      this.navStack = context.pathStack
    })
  }
}
