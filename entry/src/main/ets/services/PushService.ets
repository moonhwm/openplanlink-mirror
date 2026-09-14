import { common } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';

const TAG = 'StockPulse.PushService';
const DOMAIN = 0x0001;

/**
 * Push Kit 占位封装。
 *
 * 实装步骤（候 AGC 配置，见 README「推送实装」）：
 * 1. AppGallery Connect 建项目+应用，开通 Push Kit；
 * 2. 下载 agconnect-services.json 放 AppScope/resources/rawfile/；
 * 3. 此处调用 @kit.PushKit 的 pushService.getToken() 取 token 上报 X 服务器；
 * 4. 服务端用 Push Kit REST API 下发「订阅类 SUBSCRIPTION」通知（锁屏+铃声）；
 * 5. 通知 click 带 alertId → EntryAbility.onNewWant → 页面自动播报音频流。
 *
 * 降级：AGC 未配置时，本服务静默降级，前台轮询（AlertPoller）兜底。
 */
export class PushService {
  private static tokenReported = false;

  static async init(context: common.UIAbilityContext): Promise<void> {
    try {
      // AGC 配置文件存在性探针；不存在即降级
      const hasAgc = await PushService.probeAgcConfig(context);
      if (!hasAgc) {
        hilog.info(DOMAIN, TAG, 'agconnect-services.json absent, push degraded to polling');
        return;
      }
      // TODO(实装): const token = await pushService.getToken();
      // TODO(实装): await PushService.reportToken(token);
      PushService.tokenReported = true;
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `init failed: ${(e as Error).message}`);
    }
  }

  private static async probeAgcConfig(context: common.UIAbilityContext): Promise<boolean> {
    try {
      const raw = context.resourceManager.getRawFileContentSync('agconnect-services.json');
      return raw != null && raw.length > 0;
    } catch {
      return false;
    }
  }

  private static async reportToken(token: string): Promise<void> {
    // TODO(实装): POST 到 X 服务器 /api/push/register
    hilog.info(DOMAIN, TAG, `token length=${token.length}`);
  }
}
