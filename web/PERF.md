# Performance baseline

Measured Nov 9, 2026, 3:30 to 3:40 PM MT, on `main` at `0036a06`. Targets are first guesses
from the planning prompt, not requirements from the plan.

## Hot path

| Hop | p50 | p95 | Target | How it was measured |
| --- | --- | --- | --- | --- |
| 1. Audio to interim caption (Deepgram lag) | 119 to 141 ms | 264 to 437 ms | under 300 ms p50 | Two runs streaming a 21 s speech clip in real time, in 43 ms chunks (the phone's worklet batch), to Deepgram with the app's own `listen_url` and keyterms, from a laptop on Wi-Fi. Lag = arrival time minus the end of the audio the result covers. |
| 1b. Audio to final transcript | 123 to 137 ms | 198 to 332 ms | none | Same runs. |
| 2. Transcript to card | not measured on a device | | under 150 ms p50 | Cards come from interim results, not finals, and the glossary index is built once (`web/src/lib/match/matcher.ts`), so no card waits for a final. The app reports `confpilot.card.word_to_card_ms` to Dash0 on every card paint, but no phone session has sent one yet (0 events in the last 6 hours). |
| 3. Room WebSocket fan-out | not measured | | under 100 ms added | Needs two phones. |
| 4. First-load JS (gzipped) | 186 KB (`index` 73 KB + `App` 113 KB) | | under 150 KB | `pnpm build`. StageView (8 KB) and the Dash0 SDK (28 KB) already load separately. Lighthouse was not run. |
| 5. ES calls blocking captions | no | | never | Captions go phone to Deepgram to phone. The API and Elasticsearch are not in that path. |

## What was checked and ruled out

- Deepgram settings: `nova-3`, `interim_results=true`, 16 kHz linear16. Audio is sent in about
  43 ms batches, which is below the 100 ms suggested.
- Matcher: runs on the phone, index built once, safe to call on every interim.
- Glossary: fetched from `/api/glossary` at runtime, not bundled.
- ES and the LLM: not in the caption or card path.

## Changes tried

| Change | Result | Kept? |
| --- | --- | --- |
| Lazy-load Recap, Flashcards and Ask routes | Initial JS 186 to 183 KB. The App chunk lost 17 KB but a 14 KB shared chunk still loads on first paint. | No, under 2 percent |

## Next steps, if there is time after the demo

- Read real `word_to_card_ms` from Dash0 after the phone test to get hops 2 and 3 on devices.
- The rest of the first-load JS is mostly `motion`, `radix-ui` and `react-router`. Switching to
  `LazyMotion` with `m` components would cut the most, but it touches the card animation in 9
  files, too risky before the demo.
