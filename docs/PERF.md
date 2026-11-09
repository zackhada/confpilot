# Performance baseline

Measured Nov 9, 2026, 3:30 to 3:40 PM MT, on `main` at `0036a06`. Targets are first guesses
from the planning prompt, not requirements from the plan.

## Hot path

| Hop | p50 | p95 | Target | How it was measured |
| --- | --- | --- | --- | --- |
| 1. Audio to interim caption (Deepgram lag) | 119 to 141 ms | 264 to 437 ms | under 300 ms p50 | Two runs streaming a 21 s speech clip in real time, in 43 ms chunks (the phone's worklet batch), to Deepgram with the app's own `listen_url` and keyterms, from a laptop on Wi-Fi. Lag = arrival time minus the end of the audio the result covers. |
| 1b. Audio to final transcript | 123 to 137 ms | 198 to 332 ms | none | Same runs. |
| 2. Transcript to card (phone compute) | 0.03 ms | 0.2 ms (max 7.8 ms) | under 150 ms p50 | 2,400 timed calls of the matcher plus `reduceTranscript` (the work the phone does per interim, word by word through the same 21 s script, 50 rounds) in Node on the laptop. 12 cards found. Index build is 12.5 ms, once per glossary load. A phone is slower, but even at 10 times this the hop is a few ms plus one frame to paint. Cards come from interims, so no card waits for a final. On-device word-to-card time is reported to Dash0 as `confpilot.card.word_to_card_ms` on every card paint; no phone session has sent one yet. |
| 3. Room WebSocket fan-out | not measured | | under 100 ms added | Needs two phones on the tunnel. Not in the card path: each phone matches its own captions locally. |
| 4. First-load JS (gzipped) | 186 KB (`index` 73 KB + `App` 113 KB) | | under 150 KB | `pnpm build`. StageView (8 KB) and the Dash0 SDK (28 KB) already load separately. Lighthouse was not run. |
| 5. ES calls blocking captions | no | | never | Captions go phone to Deepgram to phone. The API and Elasticsearch are not in that path. |

## What was checked and ruled out

- Deepgram settings: `nova-3`, `interim_results=true`, 16 kHz linear16. Audio is sent in about
  43 ms batches, which is below the 100 ms suggested.
- Matcher: runs on the phone, index built once, safe to call on every interim.
- Glossary: fetched from `/api/glossary` at runtime, not bundled.
- ES and the LLM: not in the caption or card path.

## Verdict

Hops 1 and 2, the top priorities, meet their targets as measured, so no code change was needed there.
Hop 4 misses its 150 KB target (186 KB); the only safe change found saved under 2 percent and
was reverted. The bigger fix is listed below and was left until after the demo on purpose.

## Changes tried

| Change | Result | Kept? |
| --- | --- | --- |
| Lazy-load Recap, Flashcards and Ask routes | Initial JS 186 to 183 KB. The App chunk lost 17 KB but a 14 KB shared chunk still loads on first paint. | No, under 2 percent |

## Next steps, if there is time after the demo

- Read real `word_to_card_ms` from Dash0 after the phone test to get hops 2 and 3 on devices.
- The rest of the first-load JS is mostly `motion`, `radix-ui` and `react-router`. Switching to
  `LazyMotion` with `m` components would cut the most, but it touches the card animation in 9
  files, too risky before the demo.
