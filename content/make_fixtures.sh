#!/usr/bin/env bash
# Render the talk track in seven synthetic English accents (macOS `say`), 16 kHz mono WAV.
#   ./make_fixtures.sh            # writes stt-fixtures/tts_<voice>.wav (gitignored)
# Missing voices: System Settings > Accessibility > Spoken Content > System Voice > Manage Voices.
set -euo pipefail
cd "$(dirname "$0")"
for v in Aman Rishi Daniel Karen Moira Tessa Samantha; do
  say -v "$v" -f stt-fixtures/talk_track.txt -o "stt-fixtures/tts_$v.wav" \
    --file-format=WAVE --data-format=LEI16@16000 && echo "tts_$v.wav" || echo "skip $v (voice not installed)"
done
