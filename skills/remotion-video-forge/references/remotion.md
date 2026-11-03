# Remotion reference (v4.x)

Remotion renders React components to video: each frame is a deterministic function of
its frame number; headless Chrome screenshots frames, FFmpeg encodes.

## Project anatomy

```
npm run dev                 # Studio preview (hot reload, scrub timeline)
npx remotion render <id> out.mp4
npx remotion compositions   # list registered composition ids
```

`src/index.ts` calls `registerRoot(RemotionRoot)`; `src/Root.tsx` registers:

```tsx
<Composition
  id="MyVideo"
  component={MyVideo}
  durationInFrames={300}     // 10s at 30fps
  fps={30}
  width={1920}
  height={1080}
  defaultProps={{ title: "hello" }}
  schema={z.object({ title: z.string() })}   // optional Zod validation
  calculateMetadata={async ({ props }) => ({ props })}  // optional async override
/>
```

## Core API (use these, not CSS animation)

- `useCurrentFrame()`, `useVideoConfig()` — frame / fps / width / height.
- `interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" })` — fades, slides.
- `spring({ frame, fps, config: { damping: 100 } })` — physical entrances.
- `<Sequence from={90} durationInFrames={60}>` — offset / trim child timing.
- `<Series>` — children play back-to-back.
- `<Audio src={staticFile("bgm.mp3")} startFrom={...} volume={(f)=>...} />` — from
  `@remotion/media` (v4). Generated assets must live in `public/` and load via
  `staticFile()`.
- `delayRender()` / `continueRender()` — async data before a frame (30s default
  timeout). Fetch ONCE at module level or in `calculateMetadata`, NOT inside a
  component body per render thread (Lambda runs ~200 threads; each must return
  identical data).
- `@remotion/captions` — SRT → captions.
- Fonts: `@remotion/fonts` (load before render; system fonts differ per machine).

## Codecs / outputs

`--codec=h264` (default mp4) | `h265` | `vp8|vp9` (webm) | `av1` | `prores` (mov) |
`gif` | `--sequence` (PNG frames). Audio AAC default in mp4.

## Scale-out

- `@remotion/lambda` — AWS Lambda, ~200-way parallelism, pay per render.
- `@remotion/cloudrun` — experimental.
- Local renders parallelize across CPU cores automatically.

## Pitfalls (all observed in the wild)

- CORS: remote assets must send CORS headers or Chrome refuses them — prefer local
  `public/` files via `staticFile()`.
- Randomness: seed it (`random()` is seeded per frame in v4) — unseeded randomness
  flickers between frames.
- Frame purity: never read `Date.now()` / wall clock inside a component; derive
  everything from `frame`.
- Node ≥ 16; FFmpeg bundled.
- License: Remotion v4 is source-available; free for companies ≤ 3 people (commercial
  use included), paid seats/render fees above that. Verify current terms at
  remotion.dev/license before commercial deployment.
