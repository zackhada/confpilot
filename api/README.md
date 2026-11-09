# ConfPilot API

FastAPI service: the room WebSocket hub, glossary, user knowledge, recap, search, the
speech-to-text token and the knowledge probe. Every shape mirrors `contracts/types.ts`.

The room hub and the store are in memory, so **run exactly one replica** (see
`contracts/README.md`). Data is lost on restart until the Elasticsearch store replaces
`MemoryStore`.

## Run

```powershell
cd api
uv sync
uv run uvicorn confpilot.main:app --host 0.0.0.0 --port 8000 --ws-ping-interval 20 --ws-ping-timeout 20
```

## Test and lint

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Endpoints

| Route | Returns |
| --- | --- |
| `GET /healthz` | `Health` |
| `GET /api/glossary` | `Glossary` |
| `GET /api/users/{user_id}/knowledge` | `{ items: Knowledge[] }` |
| `PUT /api/users/{user_id}/knowledge/{term_id}` | `Knowledge` (body: `KnowledgePatch`) |
| `GET /api/rooms/{room}/recap?user_id=` | `Recap` |
| `GET /api/search?q=&room=&user_id=&limit=` | `SearchResponse`; `highlight` is HTML-escaped with `<mark>` |
| `POST /api/token` | `TokenResponse`; 503 if `DEEPGRAM_API_KEY` is unset, 502 if Deepgram fails |
| `POST /api/probe` | `ProbeResponse`; uses the LLM when configured, otherwise a heuristic |
| `WS /ws/rooms/{room}?session=&name=&role=` | `ClientEvent` in, `ServerEvent` out |

`room`, `user_id` and `term_id` must match `^[A-Za-z0-9_-]{1,64}$`.

### Connecting to Deepgram from the browser

`POST /api/token` returns a short-lived `token` and a complete `ws_url`. Browsers cannot set
an `Authorization` header on a WebSocket, so pass the token as a subprotocol:

```ts
const { token, ws_url } = await (await fetch("/api/token", { method: "POST", ... })).json();
const stt = new WebSocket(ws_url, ["bearer", token]); // not ["token", ...]: that form is for API keys
```

The token only has to be valid when the socket opens (60 s by default). Fetch a new one for
every connection, including reconnects. Send 16 kHz mono 16-bit PCM as binary frames.

### Room WebSocket behaviour

- A `transcript` is relayed to everyone else at once with `speaker` set. Only `role=speaker`
  may send one. Finals are then matched and stored, unless they repeat another speaker's final
  from the last 3 s.
- `card.shown` is relayed to everyone else with `user` set, and recorded in the histogram
  `confpilot.card.word_to_card_ms` (attributes `confpilot.card.tier`, `confpilot.room`) when it
  is between 0 and 60 000 ms.
- Bad input gets an `error` event (`unauthorized`, `bad_event`, `forbidden`, `store_unavailable`, `internal`).
  The socket stays open except for an unauthorized session, which closes with code 1008. Bad join
  parameters get `bad_request`, then close code 1008.
- The server resends `room.state` every 20 s as a heartbeat, on top of uvicorn's ping frames.

## Configuration

All settings come from environment variables. A `.env` file in the working directory is also
read. Blank values count as unset.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_VERSION` | package version | Reported by `/healthz` |
| `STATIC_DIR` | unset | Built web app, served at `/` with fallback to `index.html`. Never shadows `/api`, `/ws` or `/healthz`. |
| `GLOSSARY_PATH` | unset | Glossary file. Otherwise `content/glossary.json`, then `contracts/fixtures/glossary.sample.json`. |
| `DEEPGRAM_API_KEY` | unset | Server-side key used to mint tokens. Needs Member rights or higher. |
| `DEEPGRAM_TOKEN_TTL_S` | `60` | Lifetime of a minted token |
| `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | unset, `https://api.openai.com/v1`, `gpt-4o-mini` | OpenAI-compatible chat completions for `/api/probe` |
| `PROBE_TIMEOUT_S` | `6` | Time box for the probe's LLM call |
| `WS_HEARTBEAT_S` | `20` | Interval of the `room.state` heartbeat |
| `ALLOWED_ORIGINS` | unset | Comma-separated extra origins (CORS and the room WebSocket Origin check); the API's own host is always allowed |
| `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_SERVICE_NAME` | unset | Standard OpenTelemetry variables. Traces, metrics and logs go out over OTLP/HTTP. With no endpoint set, telemetry is a no-op. |

## Swapping in Elasticsearch

Implement the seven async methods of `confpilot.store.Store` and pass the instance to
`create_app(store=...)`. To push tier 2 or 3 cards, call
`app.state.hub.broadcast(room, ServerCardEvent(...))`.
