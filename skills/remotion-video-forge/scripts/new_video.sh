#!/usr/bin/env bash
# Scaffold a minimal Remotion project from the bundled template, then (optionally) render.
# Usage: new_video.sh <target-dir> [--render <comp-id> <out.mp4>]
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DST="${1:?usage: new_video.sh <target-dir> [--render <comp-id> <out.mp4>]}"

mkdir -p "$DST"
cp -r "$SKILL_DIR/assets/remotion-min/." "$DST/"
echo "scaffolded: $DST (from assets/remotion-min)"

cd "$DST"
if [ ! -d node_modules ]; then
  npm install --no-audit --no-fund
fi

if [ "${2:-}" = "--render" ]; then
  COMP="${3:?comp id}"; OUT="${4:?out file}"
  npx remotion render "$COMP" "$OUT"
  echo "rendered: $OUT"
  echo "seal it:  $(dirname "$SKILL_DIR")/scripts/sha3_256.py file $OUT"
else
  echo "next: cd $DST && npm run dev   # Studio preview"
  echo "then: npx remotion render MyVideo out.mp4"
fi
