import { AbilityConstant, UIAbility, Want } from '@kit.AbilityKit';
import { window } from '@kit.ArkUI';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { PushService } from '../services/PushService';
import { SettingsService } from '../services/SettingsService';
import { pushService, pushCommon } from '@kit.PushKit';
import { BusinessError } from '@kit.BasicServicesKit';

const TAG = 'StockPulse.EntryAbility';
const DOMAIN = 0x0001;

export default class EntryAbility extends UIAbility {
  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    hilog.info(DOMAIN, TAG, 'onCreate');
    // Push Kit 初始化（取 token 上报服务端）；未配置 AGC 时内部降级为仅日志
    PushService.init(this.context).catch((e: Error) => {
      hilog.warn(DOMAIN, TAG, `push init degraded: ${e.message}`);
    });
    // Settings 初始化（Preferences 持久化：自选股/播报开关/字体档）
    SettingsService.init(this.context).catch((e: Error) => {
      hilog.warn(DOMAIN, TAG, `settings init degraded: ${e.message}`);
    });
    // 冷启动通知缺口修复（白皮书 §3.3.2）：冷启动时 want 参数经 onCreate 传入，
    // 原代码只在 onNewWant 处理 alertId，冷启动点通知会丢失。此处补检。
    const alertId = want?.parameters?.alertId as string | undefined;
    if (alertId) {
      AppStorage.setOrCreate('pendingAlertId', alertId);
    }
    // 接收 DEFAULT 场景化消息（应用在前台时，推送消息直接传递给应用处理）
    this.registerPushMessageReceiver();
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

  onForeground(): void {
    hilog.info(DOMAIN, TAG, 'onForeground');
    // 订阅通知自分类（SUBSCRIPTION）——需 AGC 平台审批通过后启用（P5）
    // 审批期间用 DEFAULT 类通知调试，此调用注释保留
    // this.requestSubscribe();
  }

  /**
   * 注册 Push Kit 场景化消息接收器。
   * DEFAULT 类型：应用在前台时，推送消息直接传递给应用处理，
   * 不在通知中心显示。应用在后台时，消息走通知中心 → click → onNewWant 链路。
   */
  private registerPushMessageReceiver(): void {
    try {
      pushService.receiveMessage('DEFAULT', this, (data: pushCommon.PushPayload) => {
        try {
          hilog.info(DOMAIN, TAG, `received push message: ${JSON.stringify(data)}`);
          // 从推送消息中提取 alertId，写入 AppStorage 供 Index 页消费
          const remoteData = data.remoteData;
          if (remoteData) {
            const alertId = remoteData['alertId'] as string | undefined;
            if (alertId) {
              AppStorage.setOrCreate('pendingAlertId', alertId);
            }
          }
        } catch (e) {
          hilog.warn(DOMAIN, TAG, `push message handle error: ${(e as Error).message}`);
        }
      });
      hilog.info(DOMAIN, TAG, 'push message receiver registered');
    } catch (e) {
      const err = e as BusinessError;
      hilog.warn(DOMAIN, TAG, `receiveMessage register failed: code=${err.code}, message=${err.message}`);
    }
  }

  /**
   * 请求订阅通知授权（SUBSCRIPTION 自分类）。
   * 前置条件：AGC 平台已开通订阅通知自分类权益（P5）。
   * 审批未通过时调用会返回错误码 1000900025（No rights to access entity id）。
   */
  // private async requestSubscribe(): Promise<void> {
  //   // entityIds 替换为 AGC 平台申请的订阅模板 ID
  //   const entityIds = ['stock_alert_subscription'];
  //   try {
  //     const result = await serviceNotification.requestSubscribeNotification(this.context, entityIds);
  //     hilog.info(DOMAIN, TAG, `subscribe result: ${JSON.stringify(result.entityResult)}`);
  //   } catch (e) {
  //     const err = e as BusinessError;
  //     hilog.warn(DOMAIN, TAG, `subscribe failed: code=${err.code}, message=${err.message}`);
  //   }
  // }
}
