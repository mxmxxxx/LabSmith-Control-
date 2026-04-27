#!/usr/bin/env bash
# Record an end-to-end mock-driver demo of labsmith_gui to an mp4.
# Prereqs (macOS):
#   * ffmpeg in $PATH (brew install ffmpeg)
#   * Screen Recording permission granted to whatever terminal runs this
#     (System Settings > Privacy & Security > Screen Recording)
# Output defaults to /tmp/labsmith_demo.mp4 — override with OUT=<path>.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PYROOT="$(cd "$HERE/.." && pwd)"
OUT="${OUT:-/tmp/labsmith_demo.mp4}"
# Main-display index. `ffmpeg -f avfoundation -list_devices true -i ""` lists
# them; on most Macs this is "3" (first "Capture screen N" entry).
SCREEN_IDX="${SCREEN_IDX:-3}"
# Hard cap so we never leave a runaway recorder — orchestrator completes ~22s.
MAX_SECONDS="${MAX_SECONDS:-45}"

echo "[record] ffmpeg capturing screen $SCREEN_IDX -> $OUT (cap $MAX_SECONDS s)"

ffmpeg -hide_banner -loglevel warning \
    -f avfoundation -framerate 30 -capture_cursor 1 \
    -i "${SCREEN_IDX}:none" \
    -t "$MAX_SECONDS" \
    -vf "scale=1920:-2" \
    -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p \
    -movflags +faststart \
    -y "$OUT" \
    < /dev/null &
FFMPEG_PID=$!

# Give ffmpeg a beat so the first frame isn't the terminal focused state.
sleep 1.5

echo "[record] launching demo_orchestrator"
cd "$PYROOT"
python3 dev_tools/demo_orchestrator.py || true

# Cleanly stop ffmpeg: SIGINT makes libx264 flush / finalize the mp4 header.
if kill -0 "$FFMPEG_PID" 2>/dev/null; then
    echo "[record] sending SIGINT to ffmpeg"
    kill -INT "$FFMPEG_PID" || true
fi
wait "$FFMPEG_PID" 2>/dev/null || true

if [[ -f "$OUT" ]]; then
    SIZE=$(stat -f%z "$OUT" 2>/dev/null || stat -c%s "$OUT")
    echo "[record] done: $OUT ($((SIZE/1024)) KiB)"
else
    echo "[record] FAILED: $OUT not produced" >&2
    exit 1
fi
