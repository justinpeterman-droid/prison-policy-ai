#!/usr/bin/env bash
# Re-encode the login page's background video.
#
# The original export was 2.99MB: 1280x720 h264 at 2.26 Mbps, plus a 128kbps
# AAC track that can never be heard because the <video> element is `muted`.
# It also had its moov atom at the end, so the browser had to finish the
# download before it could start playing.
#
# This encode strips the audio, drops to CRF 28 (SSIM 0.978 / PSNR 40.3 dB
# against the original — at or above the usual "visually lossless" line, and it
# plays behind a navy overlay at 25-72% opacity), and moves the moov atom to
# the front so playback starts while the rest streams in.
#
#   2,988,383 B  ->  1,214,405 B   (59% smaller)
#
# ⚠ Run this against the ORIGINAL export, never against the already-encoded
#   file in static/ — re-encoding a re-encode compounds generation loss. The
#   pre-optimization original is in git history:
#
#     git show 1a3e84f:backend/webapp/static/dragon-bg.mp4 > /tmp/dragon-bg.orig.mp4
#     scripts/optimize_video.sh /tmp/dragon-bg.orig.mp4
#
set -euo pipefail

SRC="${1:?usage: optimize_video.sh <original-dragon-bg.mp4>}"
DST="$(dirname "$0")/../backend/webapp/static/dragon-bg.mp4"

ffmpeg -y -i "$SRC" \
  -an \
  -c:v libx264 -crf 28 -preset slow -pix_fmt yuv420p \
  -movflags +faststart \
  "$DST"

echo "wrote $DST ($(stat -c%s "$DST") bytes)"
