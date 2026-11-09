# ConfPilot API

FastAPI service: the room WebSocket hub, glossary, user knowledge, recap, search, the
speech-to-text token and the knowledge probe. Shapes mirror `contracts/types.ts`.

The room hub is in memory, so **run exactly one replica** (see `contracts/README.md`).

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

## Configuration

All settings come from environment variables. A `.env` file in the working directory is also
read. Blank values count as unset.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_VERSION` | package version | Reported by `/healthz` |
| `STATIC_DIR` | unset | Built web app, served at `/` with fallback to `index.html`. Never shadows `/api`, `/ws` or `/healthz`. |
| `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_SERVICE_NAME` | unset | Standard OpenTelemetry variables. Traces, metrics and logs go out over OTLP/HTTP. With no endpoint set, telemetry is a no-op. |
