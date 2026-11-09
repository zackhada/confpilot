# Observability (Dash0)

ConfPilot sends traces, metrics and logs to Dash0 (region `us-west-2`, dataset `default`).
The product promise is speed: a card is on screen within 800 ms of the word being spoken.
The histogram `confpilot.card.word_to_card_ms` (attribute `confpilot.card.tier`) measures it.

| File | What it is |
| --- | --- |
| `dash0/slo.json` | SLO "Cards on screen within 800 ms": 95% of cards within 800 ms. OpenSLO v1, origin `confpilot-word-to-card-slo`. The SLI is good / total cards, computed from the native histogram with `histogram_fraction(0, 800, ...)`. Dash0 only allows a rolling 28-day window. |
| `dash0/dashboard.json` | Dashboard "ConfPilot: word to card" (id `confpilot-word-to-card`): share of cards within 800 ms, p95, card volume, latency by tier, and the API's operations, errors and logs. |

## Apply

Both calls are idempotent upserts. `DASH0_TOKEN` is a Dash0 auth token with the
**All permissions** option. Keep it in your environment, never in a file.

```sh
DASH0_API=https://api.us-west-2.aws.dash0.com

# SLO (upsert by origin)
curl -sS -X PUT "$DASH0_API/api/slos/confpilot-word-to-card-slo?dataset=default" \
  -H "Authorization: Bearer $DASH0_TOKEN" \
  -H "Content-Type: application/json" \
  --data @observability/dash0/slo.json

# Dashboard (upsert by id)
curl -sS -X PUT "$DASH0_API/api/dashboards/confpilot-word-to-card?dataset=default" \
  -H "Authorization: Bearer $DASH0_TOKEN" \
  -H "Content-Type: application/json" \
  --data @observability/dash0/dashboard.json
```

The SLO is read-only in the Dash0 UI because it is managed from this file. Change it here and
apply it again.
