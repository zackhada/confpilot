"""A recording stand-in for AsyncElasticsearch, for tests that must run without a cluster."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Response = dict[str, Any] | list[dict[str, Any]] | Callable[..., dict[str, Any]] | Exception


class StubClient:
    """Answers each client method from `responses[method_name]` and records every call.

    A response may be a dict (returned every time), a list (one per call, in order), a callable
    (given the call's keyword arguments) or an exception to raise. `client.indices.x` and
    `client.inference.x` are recorded as plain `x`.
    """

    def __init__(self, **responses: Response) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.indices = self
        self.inference = self

    def options(self, **_: Any) -> StubClient:
        return self

    def calls_to(self, method: str) -> list[dict[str, Any]]:
        return [kwargs for name, kwargs in self.calls if name == method]

    def __getattr__(self, method: str) -> Callable[..., Any]:
        async def call(**kwargs: Any) -> Any:
            self.calls.append((method, kwargs))
            response = self.responses.get(method, {})
            if isinstance(response, list):
                response = response.pop(0)
            if isinstance(response, Exception):
                raise response
            return response(**kwargs) if callable(response) else response

        return call
