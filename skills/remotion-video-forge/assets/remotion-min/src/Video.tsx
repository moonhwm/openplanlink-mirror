import { AbsoluteFill, Audio, interpolate, staticFile, useCurrentFrame } from "remotion";
import { T } from "./style";

// Minimal scene: title fade-in over a dark backdrop, optional BGM at public/bgm.mp3.
// Every value derives from `frame` — deterministic, CI-renderable.
export const Video: React.FC<{ title: string }> = ({ title }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  const y = interpolate(frame, [0, 30], [40, 0], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: T.bg, justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          opacity,
          transform: `translateY(${y}px)`,
          color: T.ink,
          fontFamily: T.font,
          fontSize: 88,
          letterSpacing: 6,
          padding: T.pad,
          textAlign: "center",
        }}
      >
        {title}
      </div>
      {/* Uncomment after `scripts/suno_music.py --out public/bgm.mp3 ...`
      <Audio src={staticFile("bgm.mp3")} volume={(f) => interpolate(f, [0, 30], [0, 0.6], { extrapolateRight: "clamp" })} />
      */}
    </AbsoluteFill>
  );
};
