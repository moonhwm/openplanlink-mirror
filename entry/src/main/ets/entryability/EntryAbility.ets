import { AbilityConstant, UIAbility, Want } from '@kit.AbilityKit';
import { window } from '@kit.ArkUI';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { PushService } from '../services/PushService';

const TAG = 'StockPulse.EntryAbility';
const DOMAIN = 0x0001;

export default class EntryAbility extends UIAbility {
  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    hilog.info(DOMAIN, TAG, 'onCreate');
    // Push Kit 初始化（取 token 上报服务端）；未配置 AGC 时内部降级为仅日志
    PushService.init(this.context).catch((e: Error) => {
      hilog.warn(DOMAIN, TAG, `push init degraded: ${e.message}`);
    });
    // 冷启动通知缺口修复（白皮书 §3.3.2）：冷启动时 want 参数经 onCreate 传入，
    // 原代码只在 onNewWant 处理 alertId，冷启动点通知会丢失。此处补检。
    const alertId = want?.parameters?.alertId as string | undefined;
    if (alertId) {
      AppStorage.setOrCreate('pendingAlertId', alertId);
    }
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    windowStage.loadContent('pages/Index', (err) => {
      if (err.code) {
        hilog.error(DOMAIN, TAG, `loadContent failed: ${JSON.stringify(err)}`);
        return;
      }
      hilog.info(DOMAIN, TAG, 'loadContent ok');
    });
  }

  onNewWant(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    // 点击通知拉起时携带 alertId，跳转对应异动卡片并自动播报
    const alertId = want?.parameters?.alertId as string | undefined;
    if (alertId) {
      AppStorage.setOrCreate('pendingAlertId', alertId);
    }
  }
}
