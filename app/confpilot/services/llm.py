"""OpenAI-compatible LLM client with custom OpenTelemetry spans + token attributes."""
from __future__ import annotations

import logging
import time

import httpx
from opentelemetry import metrics, trace

from .. import config

log = logging.getLogger("confpilot.llm")

tracer = trace.get_tracer("confpilot.llm")
meter = metrics.get_meter("confpilot.llm")

tokens_hist = meter.create_histogram("confpilot.llm.tokens", "1", "LLM token usage")
duration_hist = meter.create_histogram("confpilot.llm.duration", "s", "LLM call latency")


class LLMUnavailable(RuntimeError):
    """Raised when the LLM backend is not configured or reachable."""


def llm_available() -> bool:
    return bool(config.LLM_BASE_URL)


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if config.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {config.LLM_API_KEY}"
    return headers


def chat(messages: list[dict], temperature: float = 0.2, max_tokens: int = 800) -> tuple[str, dict]:
    """Call the chat-completions endpoint and return (content, usage)."""
    if not config.LLM_BASE_URL:
        raise LLMUnavailable("LLM_BASE_URL is not configured")

    url = config.LLM_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    started = time.perf_counter()

    with tracer.start_as_current_span("llm.chat.completions", kind=trace.SpanKind.CLIENT) as span:
        span.set_attributes(
            {
                "gen_ai.system": "openai",
                "gen_ai.operation.name": "chat",
                "gen_ai.request.model": config.LLM_MODEL,
                "llm.model": config.LLM_MODEL,
                "llm.temperature": temperature,
                "llm.request.max_tokens": max_tokens,
            }
        )
        try:
            with httpx.Client(timeout=config.LLM_TIMEOUT) as client:
                resp = client.post(url, json=payload, headers=_headers())
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001 - surface as domain error
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            log.warning("LLM chat call failed: %s", exc)
            raise LLMUnavailable(f"LLM call failed: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "malformed response"))
            raise LLMUnavailable("LLM returned an unexpected response shape") from exc

        usage = data.get("usage", {}) or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens))

        span.set_attributes(
            {
                "gen_ai.response.id": data.get("id"),
                "llm.model": data.get("model", config.LLM_MODEL),
                "llm.usage.prompt_tokens": prompt_tokens,
                "llm.usage.completion_tokens": completion_tokens,
                "llm.usage.total_tokens": total_tokens,
            }
        )
        span.add_event("gen_ai.content.completion", {"content": content[:500]})

        duration = time.perf_counter() - started
        model = config.LLM_MODEL
        tokens_hist.record(total_tokens, {"type": "total", "model": model})
        tokens_hist.record(prompt_tokens, {"type": "prompt", "model": model})
        tokens_hist.record(completion_tokens, {"type": "completion", "model": model})
        duration_hist.record(duration, {"model": model})

        return content, usage


def embed(text: str) -> list[float] | None:
    """Request a text embedding; returns ``None`` when unavailable so callers degrade."""
    if not config.LLM_BASE_URL:
        return None

    url = config.LLM_BASE_URL.rstrip("/") + "/embeddings"
    payload = {"model": config.LLM_EMBED_MODEL, "input": text}

    with tracer.start_as_current_span("llm.embeddings", kind=trace.SpanKind.CLIENT) as span:
        span.set_attributes(
            {
                "gen_ai.system": "openai",
                "gen_ai.operation.name": "embeddings",
                "gen_ai.request.model": config.LLM_EMBED_MODEL,
                "llm.model": config.LLM_EMBED_MODEL,
            }
        )
        try:
            with httpx.Client(timeout=config.LLM_TIMEOUT) as client:
                resp = client.post(url, json=payload, headers=_headers())
                resp.raise_for_status()
                data = resp.json()
            vec = data["data"][0]["embedding"]
            span.set_attribute("llm.embedding.dimensions", len(vec))
            return vec
        except Exception as exc:  # noqa: BLE001 - degrade to BM25-only
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            log.warning("Embedding call failed (%s); falling back to BM25", exc)
            return None
