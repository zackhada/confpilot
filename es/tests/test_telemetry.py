"""`es_span` must surface Elasticsearch failures as one clear error and leave other errors alone."""

from __future__ import annotations

import pytest
from elastic_transport import ApiResponseMeta, HttpHeaders, NodeConfig
from elastic_transport import ConnectionError as TransportConnectionError
from elasticsearch import ApiError

from confpilot_es.telemetry import EsStoreError, es_span


def api_error(status: int, body: object) -> ApiError:
    node = NodeConfig("https", "localhost", 9200)
    meta = ApiResponseMeta(status=status, http_version="1.1", headers=HttpHeaders(), duration=0.01, node=node)
    return ApiError("request failed", meta=meta, body=body)


def test_span_yields_and_passes_a_clean_block_through() -> None:
    with es_span("es.search", operation="test", room="slc1", skipped=None) as span:
        span.set_attribute("confpilot.hit_count", 3)


def test_api_error_becomes_a_store_error_with_status_and_reason() -> None:
    with (
        pytest.raises(EsStoreError, match=r"es\.search failed: HTTP 400: no such field") as raised,
        es_span("es.search"),
    ):
        raise api_error(400, {"error": {"reason": "no such field"}})
    assert isinstance(raised.value.__cause__, ApiError)


def test_api_error_without_a_json_body_still_reports_the_status() -> None:
    with pytest.raises(EsStoreError, match=r"es\.index failed: HTTP 503"), es_span("es.index"):
        raise api_error(503, "upstream unavailable")


def test_transport_error_becomes_a_store_error() -> None:
    with pytest.raises(EsStoreError, match=r"es\.percolate failed: ConnectionError"), es_span("es.percolate"):
        raise TransportConnectionError("connection refused")


def test_other_exceptions_are_not_rewritten() -> None:
    with pytest.raises(KeyError), es_span("es.search"):
        raise KeyError("hits")
