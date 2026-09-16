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
const KEY_ELDERLY_MODE = 'elderly_mode';    // 适老化模式，boolean（默认 true）
const KEY_THEME_MODE = 'theme_mode';        // 显示模式，'night' | 'day'（默认 'night'）
const KEY_DND_ENABLED = 'dnd_enabled';      // 免打扰开关，boolean（默认 false）
const KEY_DND_START = 'dnd_start';          // 免打扰开始时段，number（默认 22）
const KEY_DND_END = 'dnd_end';              // 免打扰结束时段，number（默认 8）

/** 字体档枚举 */
export type FontSizeLevel = 'standard' | 'large';

/** 显示模式枚举 */
export type ThemeMode = 'night' | 'day';

/** 主题颜色方案 */
export interface ThemeColors {
  pageBackground: string;
  cardBackground: string;
  textPrimary: string;
  textSecondary: string;
  accentGold: string;
  riseRed: string;
  fallGreen: string;
}

/** 夜间模式配色 */
export const NIGHT_COLORS: ThemeColors = {
  pageBackground: '#0d1117',
  cardBackground: '#1c2433',
  textPrimary: '#e8edf5',
  textSecondary: '#c6ceda',
  accentGold: '#f0b232',
  riseRed: '#e74c3c',
  fallGreen: '#2ecc71',
};

/** 白天模式配色 */
export const DAY_COLORS: ThemeColors = {
  pageBackground: '#f5f7fa',
  cardBackground: '#ffffff',
  textPrimary: '#1d2129',
  textSecondary: '#86909c',
  accentGold: '#d4951a',
  riseRed: '#cf0a2c',
  fallGreen: '#00b42a',
};

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
    try {
      const raw = await SettingsService.pref.get(KEY_WATCHLIST, '[]') as string;
      return JSON.parse(raw) as string[];
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `watchlist read failed: ${(e as Error).message}`);
      return [];
    }
  }

  static async setWatchlist(list: string[]): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_WATCHLIST, JSON.stringify(list));
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `watchlist write failed: ${(e as Error).message}`);
    }
  }

  // ── 播报开关 ──

  static async getBroadcastEnabled(): Promise<boolean> {
    if (!SettingsService.pref) {
      return true;
    }
    try {
      return await SettingsService.pref.get(KEY_BROADCAST_ENABLED, true) as boolean;
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `broadcast read failed: ${(e as Error).message}`);
      return true;
    }
  }

  static async setBroadcastEnabled(enabled: boolean): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_BROADCAST_ENABLED, enabled);
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `broadcast write failed: ${(e as Error).message}`);
    }
  }

  // ── 字体档 ──

  static async getFontSizeLevel(): Promise<FontSizeLevel> {
    if (!SettingsService.pref) {
      return 'standard';
    }
    try {
      const level = await SettingsService.pref.get(KEY_FONT_SIZE_LEVEL, 'standard') as string;
      if (level === 'large') {
        return 'large';
      }
      return 'standard';
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `font level read failed: ${(e as Error).message}`);
      return 'standard';
    }
  }

  static async setFontSizeLevel(level: FontSizeLevel): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_FONT_SIZE_LEVEL, level);
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `font level write failed: ${(e as Error).message}`);
    }
  }

  // ── 适老化模式 ──

  static async getElderlyMode(): Promise<boolean> {
    if (!SettingsService.pref) {
      return true;
    }
    try {
      return await SettingsService.pref.get(KEY_ELDERLY_MODE, true) as boolean;
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `elderly mode read failed: ${(e as Error).message}`);
      return true;
    }
  }

  static async setElderlyMode(enabled: boolean): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_ELDERLY_MODE, enabled);
      // 适老化模式开启时自动设为特大字体，关闭时恢复标准字体
      if (enabled) {
        await SettingsService.pref.put(KEY_FONT_SIZE_LEVEL, 'large');
      } else {
        await SettingsService.pref.put(KEY_FONT_SIZE_LEVEL, 'standard');
      }
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `elderly mode write failed: ${(e as Error).message}`);
    }
  }

  // ── 显示模式（夜间/白天） ──

  static async getThemeMode(): Promise<ThemeMode> {
    if (!SettingsService.pref) {
      return 'night';
    }
    try {
      const mode = await SettingsService.pref.get(KEY_THEME_MODE, 'night') as string;
      return mode === 'day' ? 'day' : 'night';
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `theme mode read failed: ${(e as Error).message}`);
      return 'night';
    }
  }

  static async setThemeMode(mode: ThemeMode): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_THEME_MODE, mode);
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `theme mode write failed: ${(e as Error).message}`);
    }
  }

  static getThemeColors(mode: ThemeMode): ThemeColors {
    return mode === 'day' ? DAY_COLORS : NIGHT_COLORS;
  }

  // ── 免打扰模式 ──

  static async getDndEnabled(): Promise<boolean> {
    if (!SettingsService.pref) {
      return false;
    }
    try {
      return await SettingsService.pref.get(KEY_DND_ENABLED, false) as boolean;
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `dnd read failed: ${(e as Error).message}`);
      return false;
    }
  }

  static async setDndEnabled(enabled: boolean): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_DND_ENABLED, enabled);
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `dnd write failed: ${(e as Error).message}`);
    }
  }

  static async getDndStartHour(): Promise<number> {
    if (!SettingsService.pref) {
      return 22;
    }
    try {
      return await SettingsService.pref.get(KEY_DND_START, 22) as number;
    } catch (e) {
      return 22;
    }
  }

  static async setDndStartHour(hour: number): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_DND_START, hour);
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `dnd start write failed: ${(e as Error).message}`);
    }
  }

  static async getDndEndHour(): Promise<number> {
    if (!SettingsService.pref) {
      return 8;
    }
    try {
      return await SettingsService.pref.get(KEY_DND_END, 8) as number;
    } catch (e) {
      return 8;
    }
  }

  static async setDndEndHour(hour: number): Promise<void> {
    if (!SettingsService.pref) {
      return;
    }
    try {
      await SettingsService.pref.put(KEY_DND_END, hour);
      await SettingsService.pref.flush();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `dnd end write failed: ${(e as Error).message}`);
    }
  }

  /** 判断当前时间是否处于免打扰时段 */
  static isDndActive(dndEnabled: boolean, startHour: number, endHour: number): boolean {
    if (!dndEnabled) {
      return false;
    }
    const now = new Date();
    const hour = now.getHours();
    // 跨天时段（如 22:00-8:00）
    if (startHour > endHour) {
      return hour >= startHour || hour < endHour;
    }
    // 同天时段（如 9:00-18:00）
    return hour >= startHour && hour < endHour;
  }
}