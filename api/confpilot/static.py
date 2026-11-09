"""Serve the built web app at / with a single-page-app fallback to index.html."""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

RESERVED_PREFIXES = frozenset({"api", "ws", "healthz"})

_log = logging.getLogger(__name__)


def add_static_routes(app: FastAPI, static_dir: Path) -> bool:
    """Register the catch-all route. Call this last so real routes win."""
    root = static_dir.resolve()
    index = root / "index.html"
    if not index.is_file():
        _log.warning("STATIC_DIR has no index.html, not serving the web app: %s", root)
        return False

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def web_app(path: str) -> FileResponse:
        if path.split("/", 1)[0] in RESERVED_PREFIXES:
            raise HTTPException(status_code=404, detail="Not found")
        try:
            candidate = (root / path).resolve()
            is_file = bool(path) and candidate.is_relative_to(root) and candidate.is_file()
        except (OSError, ValueError):  # for example a NUL byte in the path
            raise HTTPException(status_code=404, detail="Not found") from None
        if is_file:
            return FileResponse(candidate)
        if "." in path.rsplit("/", 1)[-1]:
            # A missing asset is a 404, not a page: never answer app.js with HTML.
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return True
