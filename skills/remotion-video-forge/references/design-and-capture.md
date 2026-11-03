# Design tokens (uupm.cc) & ShareX capture fallback

## uupm.cc design tokens

uupm.cc ("UI/UX Pro Max") is a catalog of design tokens: ~57 UI styles, ~95 palettes,
~56 font pairs (as advertised on the site). Use it at the design stage, before
composing scenes:

1. Pick one style + palette + font pair; do not mix palettes across scenes.
2. Encode the choice in `src/style.ts` as plain exported constants (colors, font
   stacks, spacing) so every scene imports from one source of truth:

```ts
export const T = {
  bg: "#050810",        // deep space black-blue
  ink: "#d4c4a8",       // warm gold text
  accent: "#8fb3d9",
  font: "'Noto Serif SC', 'Songti SC', serif",
  pad: 96,              // safe margin px at 1080p
} as const;
```

3. Video-specific rules: keep text inside ~90% safe area; min font-size ≈ 42px at
   1080p for body copy; animate opacity/transform only (GPU-cheap); dark scenes need
   ≥ 4.5:1 contrast for subtitles.

## ShareX (screen capture) — fallback only

ShareX is a Windows-only capture tool. It CANNOT be invoked by the agent and is never
the primary path — Remotion's headless render is deterministic and higher fidelity.
Use ShareX only when the content cannot be rendered headless (interactive WebGL,
live data walls, one-off previews of Studio).

Protocol when the user must capture:

1. Prefer mp4 (H.264) via ShareX's FFmpeg backend; set region capture to the exact
   player window; disable cursor unless narration needs it.
2. Match fps to the composition (30/60); fixed window, no resizing mid-take.
3. After capture, hash the file with `scripts/sha3_256.py` and record it in the
   manifest alongside rendered deliverables, labeled `source: sharex-capture`.

Honesty: a ShareX capture is a screen recording, not a Remotion render — label it in
the manifest and never present it as frame-exact output.
