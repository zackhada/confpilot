# Contracts

Every shape that crosses a boundary (phone, API, Elasticsearch, stage view) is defined here.
`types.ts` is the source of truth. `fixtures/` holds shared test data. Change anything here
only by PR, and update every consumer in the same PR.

These contracts also settle six questions the plan left open.

## 1. One WebSocket per phone, and partial transcripts are relayed

Each phone opens `wss://<host>/ws/rooms/{room}` and keeps it open. There is no SSE.

In the demo each phone decodes the *other* speaker, so the fast path cannot depend on a
phone's own mic. A speaker's phone sends every interim and final speech-to-text result as a
`transcript` event. The API relays it to the rest of the room immediately, before any
Elasticsearch work. Every phone runs the same on-device matcher over what it receives.

Only final transcripts are stored and percolated. Anything the percolator or the LLM finds
that the phone could not have matched comes back as a `card` event (tier 2 or 3).

The room hub is in memory, so **the API runs as exactly one replica**. The server pings every
20 seconds to keep load balancer idle timeouts from closing the socket.

## 2. Latency is measured to the rendered card, and cards are never queued

`word_to_card_ms = rendered_at - spoken_at`, where `spoken_at` is when the matched word
*ended* (`started_at + word.end_ms`) and `rendered_at` is when the card was painted.

A card renders the moment it is detected. At most three full cards are visible; older ones
collapse into small chips. Nothing waits in a queue, so the badge and the SLO stay honest.

## 3. Clock sync

Phones do not share a clock. On connect, and every 30 seconds, a phone sends `time.ping` and
uses the `time.pong` to compute `offset = server_ts - (t0 + t1) / 2`. Every timestamp on the
wire is epoch milliseconds in server time.

## 4. The latency SLI comes from `card.shown`

A phone sends `card.shown` for every card it renders. The API relays it to viewers (this is
the stage view's feed) and records `word_to_card_ms` as the histogram
`confpilot.card.word_to_card_ms` with attributes `confpilot.card.tier` and `confpilot.room`.
The Dash0 SLO (95% under 800 ms) is built on that histogram.

## 5. Rooms and identity

There is no login. `user_id` is a UUID kept on the phone, and a persona switcher changes it.
A room is a short code in the URL (`/?room=slc1`). The stage view (`/stage?room=slc1`) joins
as a `viewer` and shows a QR code for the room.

Both phones may hear both voices, so the same sentence can arrive as two utterances from two
speakers. Speakers get a mic toggle, and duplicates are handled in three places:

- **Relay is never delayed.** The API relays every interim and final as it arrives.
- **Captions:** two utterances are duplicates when their `started_at` values are within three
  seconds and at least 80% of the normalized words of the shorter one appear in the other.
  The one with the earlier `started_at` wins (ties go to the lower `user_id`). Phones hide the
  loser, and the API applies the same test to finals before storing, so a sentence is stored
  and percolated once.
- **Cards:** a phone shows a term at most once per session, whatever utterance it came from.
  A duplicate utterance therefore never produces a second card or a second `card.shown`.

## 6. One matcher behaviour, three implementations

The phone (TypeScript), the glossary checker (Python) and the Elasticsearch percolator must
agree. `fixtures/matcher_cases.json` is the shared test: every implementation runs it in CI.

Normalizer rules, applied in this order to the transcript and to every term and alias:

- lowercase
- hyphens and slashes become spaces (`retrieval-augmented` becomes `retrieval augmented`)
- every other punctuation mark is deleted (`R.R.F.` becomes `rrf`, `user's` becomes `users`)
- join runs of single spelled-out letters (`r r f` becomes `rrf`)
- join letter and number runs, and read number words (`bm 25`, `bm twenty five` become `bm25`)
- match whole words only, longest term first
- a term marked `ambiguous` needs tech context within five words on either side:
  - if it has a `context` list, one of those words
  - if it has none (the case for every ambiguous term in `content/glossary.json`), another
    matched term that is not ambiguous and has the same `category`

## Other decisions

- SM-2 runs on the phone and is saved through `PUT /api/users/{id}/knowledge/{term_id}`.
- Audio goes from the phone straight to the speech-to-text provider as 16 kHz linear PCM,
  which behaves the same on iOS and Android. Audio never touches our servers.
- `content/glossary.json` (200 terms) is what the app serves. `fixtures/glossary.sample.json`
  is a small, stable glossary that exists only so `matcher_cases.json` has fixed term ids.
