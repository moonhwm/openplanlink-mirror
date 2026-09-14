/**
 * 异动条目：服务端（X 服务器云端秒级监测）产出的事实卡。
 * 红线：只报客观异动事实（涨跌幅/量能/价格穿越），不含任何买卖建议。
 */
export interface AlertItem {
  alertId: string;      // 唯一 ID，通知点击回传定位用
  ts: number;           // 秒级时间戳
  symbol: string;       // 如 600176
  name: string;         // 如 中国巨石
  direction: 'up' | 'down' | 'flat';
  headline: string;     // 一句话白话结论，如「中国巨石 2 分钟涨了 2.3%」
  detail: string;       // 补充事实（量能、价位）
  audioUrl?: string;    // 云端 TTS 音频流地址；无则不显示播报钮
}

export interface AlertFeed {
  items: AlertItem[];
  serverTs: number;
}
