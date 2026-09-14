import { media } from '@kit.MediaKit';
import { hilog } from '@kit.PerformanceAnalysisKit';

const TAG = 'StockPulse.AudioPlayer';
const DOMAIN = 0x0001;

/** 云端 TTS 音频流点按播报（适老化核心交互：点卡片=听） */
export class AudioPlayer {
  private static player: media.AVPlayer | null = null;

  static async play(url: string, onDone?: () => void): Promise<void> {
    await AudioPlayer.stop();
    const av = await media.createAVPlayer();
    AudioPlayer.player = av;
    av.on('stateChange', (state: media.AVPlayerState) => {
      if (state === 'completed' || state === 'idle') {
        onDone?.();
      }
    });
    av.on('error', (err) => {
      hilog.warn(DOMAIN, TAG, `play error: ${err.message}`);
      onDone?.();
    });
    av.url = url;
    await av.prepare();
    await av.play();
  }

  static async stop(): Promise<void> {
    if (AudioPlayer.player) {
      try {
        await AudioPlayer.player.stop();
        await AudioPlayer.player.release();
      } catch { /* 忽略重复释放 */ }
      AudioPlayer.player = null;
    }
  }
}
