---
name: remotion-video-forge
description: >
  Programmatic video production pipeline: compose videos as React code with Remotion,
  generate BGM / narration / images through the 302.ai API gateway (Suno music,
  OpenAI-compatible chat), pick design tokens from uupm.cc, fall back to ShareX screen
  capture only when headless render is impossible, and seal deliverables with SHA3-256
  identity manifests. Use when the user asks to create, render, or edit videos
  programmatically (code-driven video, Remotion composition, parameterized / batch
  videos, video generated from data or markdown), needs AI-generated background music
  or voiceover for a video, wants a reproducible CI render pipeline, or asks to turn
  articles, slides, or data into mp4. Triggers on: "用代码做视频", "Remotion",
  "Suno 配乐", "302.ai 做音乐/视频", "批量出片", "视频流水线", "programmatic video".
---

# Remotion Video Forge

## Overview

Produce videos as code: every frame is a pure function of its frame number (Remotion),
audio and images are generated through one 302.ai gateway key, and every deliverable
carries a SHA3-256 sealed manifest so identity and integrity are verifiable without
ever exposing plaintext credentials.

## Workflow

1. **Scaffold** — run `scripts/new_video.sh <dir>` (copies `assets/remotion-min/`) or
   `npx create-video@latest` for the full official template. Node ≥ 16 required.
2. **Design tokens** — read `references/design-and-capture.md`; pick a style / palette /
   font pair (uupm.cc catalog) and encode them in `src/style.ts` before composing.
3. **Generate assets** — BGM: `scripts/suno_music.py` (Suno via 302.ai, ~0.1 PTC per
   call, polls then downloads mp3). Narration / images / structured copy: see
   `references/gateway-302.md`. Put files under `public/` and load via `staticFile()`.
4. **Compose & render** — read `references/remotion.md`. Preview with `npm run dev`
   (Studio), render with `npx remotion render <comp-id> out.mp4`.
5. **Seal** — `scripts/sha3_256.py manifest <files...>` writes a SHA3-256 manifest next
   to the deliverable. Identity anchoring in this pipeline is **SHA3-256 only, never
   SHA3-512**; account identifiers appear only as their SHA3-256 fingerprint, never as
   plaintext in any file, log, or video frame.

## Render targets

| Target | Command | Notes |
| --- | --- | --- |
| mp4 (H.264/AAC) | `npx remotion render <id> out.mp4` | default, right default for delivery |
| H.265 / VP9 / AV1 / ProRes | `npx remotion render <id> out.<ext> --codec=...` | see references/remotion.md |
| GIF / frame sequence | `--codec=gif` / `--sequence` | for previews and pipelines |
| AWS Lambda at scale | `@remotion/lambda` | up to ~200 concurrent chunks; per-thread fetches must return identical data |
| ShareX screen capture | manual fallback only | see references/design-and-capture.md — never the primary path |

## Security red lines (absolute)

- The 302.ai key lives ONLY in the `S302_API_KEY` environment variable. Never hardcode
  it, never print it, never bake it into videos, manifests, or git history.
- Quota discipline: Suno calls cost real quota (~0.1 PTC each). Always `--dry-run`
  first; call live only when the user asked for the asset.
- Model names advertised on 302.ai pages (e.g. "claude-opus-5-5", "gpt-6-sol",
  "typesafeai/Jev") are **page claims, not verified upstream identities** — label them
  as such wherever surfaced.
- Do not fabricate endpoints, model IDs, prices, or hashes. If an API shape is
  uncertain, code defensively and mark the assumption in comments.

## Resources

- `scripts/new_video.sh` — scaffold a minimal Remotion project from the bundled template.
- `scripts/suno_music.py` — Suno music via 302.ai: submit → poll → download mp3, with `--dry-run` and SHA3-256 receipt. stdlib only.
- `scripts/sha3_256.py` — SHA3-256 CLI: hash text/files, build manifests, verify the seat fingerprint, self-test (known-answer vectors).
- `references/remotion.md` — Remotion core API, CLI, rendering, Lambda, fonts, pitfalls.
- `references/gateway-302.md` — 302.ai gateway: auth, chat, images, Suno flow, pricing facts, honesty labels.
- `references/design-and-capture.md` — uupm.cc design tokens applied to video scenes; ShareX capture fallback protocol.
- `assets/remotion-min/` — minimal project template (Root.tsx + Video.tsx + style.ts) used by `new_video.sh`.
