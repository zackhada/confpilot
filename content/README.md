# content/ — glossary and transcription test (owner: Skyler)

- `glossary.json` / `glossary.csv`: the 200 preloaded terms the phone matches against. Generated; edit `build_glossary.py`, never the outputs.
- `build_glossary.py`: term table, validator (200 terms, unique ids, definitions of 20 words or fewer, no self-definition, alias collisions, prerequisites exist and have no cycles), STT normalizer and matcher.
- `stt-fixtures/talk_track.txt`: the demo conversation.

```bash
python3 content/build_glossary.py                          # validate and regenerate glossary.json/csv
content/make_fixtures.sh                                   # macOS: render the talk track in 7 accents (gitignored)
DEEPGRAM_API_KEY=... content/stt_test.sh                   # Deepgram nova-3 + keyterms, then score
python3 content/build_glossary.py --check some/*.txt       # score any transcripts; exit 1 if a must-catch term is missed
```

Must-catch terms: SRE, RAG, embed, BM25, RRF. Put real phone recordings of the talk track in `stt-fixtures/` (`.wav` or `.m4a`); audio and `stt-out/` stay out of git.
