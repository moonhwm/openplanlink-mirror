import { http } from '@kit.NetworkKit';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { AlertItem, AlertFeed } from '../model/AlertItem';

const TAG = 'StockPulse.AlertPoller';
const DOMAIN = 0x0001;

/** X 服务器地址（采购落地后替换；本机联调可指局域网） */
const FEED_URL = 'http://127.0.0.1:8000/api/alerts/latest';

/**
 * 前台轮询兜底：App 打开期间每 5s 拉一次最新异动。
 * 推送（PushService）实装后，本件仅作拉齐补偿。
 */
export class AlertPoller {
  static async fetchLatest(limit: number = 20): Promise<AlertItem[]> {
    const req = http.createHttp();
    try {
      const resp = await req.request(`${FEED_URL}?limit=${limit}`, {
        method: http.RequestMethod.GET,
        connectTimeout: 5000,
        readTimeout: 5000
      });
      if (resp.responseCode !== 200) {
        hilog.warn(DOMAIN, TAG, `feed http ${resp.responseCode}`);
        return [];
      }
      const feed = JSON.parse(resp.result as string) as AlertFeed;
      return feed.items ?? [];
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `fetch failed: ${(e as Error).message}`);
      return [];
    } finally {
      req.destroy();
    }
  }
}
