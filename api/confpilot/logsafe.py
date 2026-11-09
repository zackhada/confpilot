"""Keep sessions out of logs.

The room WebSocket carries the session as a query parameter, and uvicorn writes the full
request path in its access log and in the WebSocket "accepted" and "closed" lines. This filter
masks ``session=<value>`` in those records before any handler sees them.
"""

import logging
import re

MASK = "session=***"
UVICORN_LOGGERS = ("uvicorn", "uvicorn.access", "uvicorn.error")
_SESSION = re.compile(r"session=[^&\s\"'#]*")


def mask_session(text: str) -> str:
    return _SESSION.sub(MASK, text)


class SessionMaskFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_session(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(mask_session(a) if isinstance(a, str) else a for a in record.args)
        elif isinstance(record.args, dict):
            record.args = {
                k: mask_session(v) if isinstance(v, str) else v for k, v in record.args.items()
            }
        return True


def install_session_masking() -> None:
    """Attach the filter to uvicorn's loggers. Safe to call more than once."""
    for name in UVICORN_LOGGERS:
        logger = logging.getLogger(name)
        if not any(isinstance(f, SessionMaskFilter) for f in logger.filters):
            logger.addFilter(SessionMaskFilter())
