# 302.ai gateway reference

One key, many models, OpenAI-compatible. Base URLs: `https://api.302.ai` (global) or
`https://api.302ai.cn` (China mirror). Auth: `Authorization: Bearer $S302_API_KEY`.
Full catalog is on their Apifox docs (302ai.apifox.cn). Pricing unit: 1 USD = 1 PTC,
$5 minimum top-up.

## Chat (OpenAI-compatible)

```
POST {base}/v1/chat/completions
{"model": "<model-id>", "messages": [...], "response_format": {...}}
```

Use for narration scripts, subtitle copy, structured storyboards. `typesafeai` exposes
"Jev" — a structured-output decision model; good for JSON-strict scene plans.

## Images

```
POST {base}/302/images/generations
{"model": ..., "prompt": ..., "size": "1920x1080"}
```

Note the `/302` prefix for media endpoints. Save into `public/` and `staticFile()` them.

## Suno music (aggregated, async)

1. `POST {base}/suno/submit/music` with `{prompt, tags, mv, title, make_instrumental}`.
   `mv` selects model generation, e.g. `chirp-crow` (v5), `bluejay`, `auk`, `v4`,
   `v3-5`. Returns a `task_id`; generates 2 songs per call.
2. Poll `{base}/suno/fetch` until status `SUCCESS` (`NOT_START` → `IN_PROGRESS` →
   `SUCCESS`). Response carries `audio_url` (mp3 on cdn1.suno.ai), plus `video_url`
   and cover image.
3. Download the mp3 promptly — files are retained ~14 days.

Facts to honor: ~0.1 PTC per call; this is an unofficial aggregated wrap of Suno —
label it as such where compliance matters.

`scripts/suno_music.py` implements this flow end-to-end with `--dry-run`.

## Honesty labels (mandatory)

- Model pages advertise "claude-opus-5-5" ($4/$20 per Mtok, 1M ctx) and "gpt-6-sol"
  ($2/$10) — these are **page claims without independent verification**. Repeat them
  only with that caveat.
- Never invent endpoint fields, model ids, or prices. If a response shape is unknown,
  probe with `--dry-run` or a minimal call and record the observed shape.

## Key hygiene

Key comes ONLY from `S302_API_KEY` env var. Never hardcode, log, or render it. If a
key was ever pasted in plaintext (chat, ticket, repo), advise rotating it in the
302.ai console.
