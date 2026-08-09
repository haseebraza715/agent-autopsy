#!/usr/bin/env bash
# record.sh — regenerate the README demo assets (asciinema cast → mp4 + gif).
#
#   bash scripts/demo/record.sh
#
# Pipeline (mirrors the host mkdemo.sh tooling):
#   1. asciinema records scripts/demo/demo_body.sh at 100x30   → assets/demo/demo.cast
#   2. agg renders the cast at 30fps                            → gif source
#   3. ffmpeg transcodes to h264 mp4 (crf 28 keeps the file ≤4MB for README hosting)
#   4. agg renders a 12s preview gif (≤2.5MB)                   → assets/demo/demo.gif
#
# Requirements:
#   - `asciinema` and `agg` on PATH (https://github.com/asciinema/agg)
#   - MEDIA_VENV: a Python virtualenv with `imageio-ffmpeg` installed
#     (used only to locate the ffmpeg binary)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$ROOT/assets/demo"
BODY="$ROOT/scripts/demo/demo_body.sh"
CAST="$OUT/demo.cast"

mkdir -p "$OUT"

# --- tool detection ------------------------------------------------------
need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: '$1' not found on PATH — install it and retry (see asciinema.org / github.com/asciinema/agg)" >&2
    exit 1
  fi
}
need asciinema
need agg

MEDIA_VENV="${MEDIA_VENV:-}"
FF=""
if [ -n "$MEDIA_VENV" ] && [ -x "$MEDIA_VENV/bin/python" ]; then
  FF="$("$MEDIA_VENV/bin/python" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())' 2>/dev/null || true)"
fi
if [ -z "$FF" ]; then
  echo "error: MEDIA_VENV must point at a venv with imageio-ffmpeg installed (provides the ffmpeg binary)" >&2
  echo "example: MEDIA_VENV=/path/to/media-venv bash scripts/demo/record.sh" >&2
  exit 1
fi

# --- record ---------------------------------------------------------------
cd "$ROOT"
export PATH="$ROOT/.venv/bin:$PATH"
export TERM="${TERM:-xterm-256color}"
echo "== recording the demo (terminal 100x30) — Ctrl+D when done"
if [ -t 0 ]; then
  COLUMNS=100 LINES=30 asciinema rec -q --overwrite "$CAST" -c "bash '$BODY'"
else
  echo "   (no tty on stdin — wrapping the recorder in a 100x30 pty)"
  script -q /dev/null bash -c \
    "stty cols 100 rows 30; export TERM=xterm-256color; exec asciinema rec -q --overwrite \"$CAST\" -c \"bash '$BODY'\""
fi
echo "== cast written: $CAST"

# --- render mp4 (30fps, full length, crf 28 size pass) ---------------------
echo "== rendering 30fps gif source (for mp4)"
agg --theme dracula --cols 100 --rows 30 --fps-cap 30 --idle-time-limit 0.12 \
  --speed 1.0 --last-frame-duration 1.5 "$CAST" /tmp/autopsy-raw30.gif

echo "== transcoding to mp4 (h264, yuv420p, faststart, crf 28)"
"$FF" -y -i /tmp/autopsy-raw30.gif -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
  -c:v libx264 -preset slow -crf 28 -pix_fmt yuv420p -movflags +faststart -an "$OUT/demo.mp4"

# --- render preview gif (first 12s, 10fps) ---------------------------------
echo "== rendering preview gif (first 12s, 10fps)"
agg --theme dracula --cols 100 --rows 30 --fps-cap 10 --idle-time-limit 0.12 \
  --speed 1.5 --last-frame-duration 1.5 --select ..12 "$CAST" "$OUT/demo.gif"

rm -f /tmp/autopsy-raw30.gif

# --- report ---------------------------------------------------------------
echo "== results"
"$FF" -i "$OUT/demo.mp4" 2>&1 | grep -E "Duration|Video:" || true
ls -la "$OUT"
