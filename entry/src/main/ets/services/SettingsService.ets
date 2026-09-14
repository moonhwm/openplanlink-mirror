import { preferences } from '@kit.ArkData';
import { common } from '@kit.AbilityKit';
import { hilog } from '@kit.PerformanceAnalysisKit';

const TAG = 'StockPulse.SettingsService';
const DOMAIN = 0x0001;

/** Preferences 持久化键名 */
const PREF_NAME = 'stockpulse_settings';
const KEY_WATCHLIST = 'watchlist';           // 自选股列表，JSON string[]
const KEY_BROADCAST_ENABLED = 'broadcast';   // 播报开关，boolean
const KEY_FONT_SIZE_LEVEL = 'font_level';    // 字体档，'standard' | 'large'

/** 字体档枚举 */
export type FontSizeLevel = 'standard' | 'large';

/**
 * 设置数据管理：自选股列表、播报开关、字体档。
 * 三项均通过 Preferences 持久化，杀进程重启后恢复。
 * 初始化时机：EntryAbility.onCreate 调用 init(context)。
 * 读取时机：Index.aboutToAppear 与 Settings.aboutToAppear 各自读取。
 */
export class SettingsService {
  private static pref: preferences.Preferences | null = null;


  static async init(context: common.UIAbilityContext): Promise<void> {
    try {
      SettingsService.pref = await preferences.getPreferences(context, PREF_NAME);
      hilog.info(DOMAIN, TAG, 'SettingsService initialized');
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `SettingsService init failed: ${(e as Error).message}`);
    }
  }

  // ── 自选股列表 ──

  static async getWatchlist(): Promise<string[]> {
    if (!SettingsService.pref) {
      return [];
    }
    const raw = await SettingsService.pref.get(KEY_WATCHLIST, '[]') as string;
    try {
      return JSON.parse(raw) as string[];
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `watchlist parse failed: ${(e as Error).message}`);
      return [];
    }
  }

  static async setWatchlist(list: string[]): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    await SettingsService.pref.put(KEY_WATCHLIST, JSON.stringify(list));
    await SettingsService.pref.flush();
  }

  // ── 播报开关 ──

  static async getBroadcastEnabled(): Promise<boolean> {
    if (!SettingsService.pref) {
      return true;
    }
    return await SettingsService.pref.get(KEY_BROADCAST_ENABLED, true) as boolean;
  }

  static async setBroadcastEnabled(enabled: boolean): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    await SettingsService.pref.put(KEY_BROADCAST_ENABLED, enabled);
    await SettingsService.pref.flush();
  }

  // ── 字体档 ──

  static async getFontSizeLevel(): Promise<FontSizeLevel> {
    if (!SettingsService.pref) {
      return 'standard';
    }
    const level = await SettingsService.pref.get(KEY_FONT_SIZE_LEVEL, 'standard') as string;
    if (level === 'large') {
      return 'large';
    }
    return 'standard';
  }

  static async setFontSizeLevel(level: FontSizeLevel): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    await SettingsService.pref.put(KEY_FONT_SIZE_LEVEL, level);
    await SettingsService.pref.flush();
  }
}