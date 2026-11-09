#!/usr/bin/env bash
# Run every fixture through Deepgram with the same model + keyterms as the app, then score the transcripts.
#   DEEPGRAM_API_KEY=... ./stt_test.sh            # default model nova-3
#   DEEPGRAM_API_KEY=... ./stt_test.sh flux-...    # try another model
# Add your own phone recordings of the talk track to stt-fixtures/ (.wav or .m4a) — those matter most.
# This uses the pre-recorded endpoint as a fast proxy. Do the final check by replaying audio
# through the live streaming path the app uses.
set -euo pipefail
cd "$(dirname "$0")"
MODEL="${1:-nova-3}"
KEYTERMS=(SRE RAG embed embeddings BM25 RRF Elasticsearch Kubernetes "hybrid search" "keyword search" "knowledge base")
Q="model=${MODEL}&smart_format=true"
for k in "${KEYTERMS[@]}"; do
  Q+="&keyterm=$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$k")"
done
mkdir -p stt-out
shopt -s nullglob
for f in stt-fixtures/*.wav stt-fixtures/*.m4a; do
  ctype="audio/wav"; [[ $f == *.m4a ]] && ctype="audio/mp4"
  out="stt-out/$(basename "${f%.*}").txt"
  curl -sS -X POST "https://api.deepgram.com/v1/listen?${Q}" \
    -H "Authorization: Token ${DEEPGRAM_API_KEY:?set DEEPGRAM_API_KEY}" \
    -H "Content-Type: ${ctype}" --data-binary @"$f" \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["results"]["channels"][0]["alternatives"][0]["transcript"])' > "$out"
done
python3 build_glossary.py --check stt-out/*.txt
