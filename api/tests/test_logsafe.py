import logging

import pytest
from fastapi.testclient import TestClient

from confpilot.logsafe import UVICORN_LOGGERS, SessionMaskFilter, mask_session

SESSION = "eyJ1c2VyX2lkIjoidS1hbmEifQ.c2lnbmF0dXJl-_x"


def record(msg: str, args: object) -> logging.LogRecord:
    return logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, msg, args, None)


@pytest.mark.parametrize(
    ("msg", "args"),
    [
        # uvicorn's HTTP access line
        (
            '%s - "%s %s HTTP/%s" %d',
            ("10.0.0.7:5123", "GET", f"/ws/rooms/slc1?session={SESSION}&name=Ana", "1.1", 101),
        ),
        # uvicorn's WebSocket lines
        (
            '%s - "WebSocket %s" [accepted]',
            ("10.0.0.7:5123", f"/ws/rooms/slc1?name=A&session={SESSION}"),
        ),
        ('%s - "WebSocket %s" 403', ("10.0.0.7:5123", f"/ws/rooms/slc1?session={SESSION}")),
        # a pre-formatted message, and dict-style arguments
        (f'connection closed "/ws/rooms/slc1?session={SESSION}&role=speaker"', None),
        ("%(path)s closed", ({"path": f"/ws/rooms/slc1?session={SESSION}"},)),
    ],
)
def test_filter_masks_the_session_in_uvicorn_log_lines(msg: str, args: object) -> None:
    entry = record(msg, args)

    assert SessionMaskFilter().filter(entry) is True

    line = entry.getMessage()
    assert SESSION not in line
    assert "session=***" in line
    assert "/ws/rooms/slc1" in line  # the rest of the line is kept


def test_mask_keeps_other_parameters_and_plain_text() -> None:
    assert mask_session("/ws/rooms/slc1?session=a.b&name=Ana&role=speaker") == (
        "/ws/rooms/slc1?session=***&name=Ana&role=speaker"
    )
    assert mask_session("no secrets here") == "no secrets here"


def test_filter_leaves_other_records_alone() -> None:
    entry = record("%s took %d ms", ("GET /healthz", 3))

    SessionMaskFilter().filter(entry)

    assert entry.getMessage() == "GET /healthz took 3 ms"


def test_the_app_installs_the_filter_once_on_uvicorn_loggers(
    client: TestClient, make_settings
) -> None:
    from confpilot.app import create_app

    create_app(make_settings())  # a second app must not add a second filter

    for name in UVICORN_LOGGERS:
        filters = [f for f in logging.getLogger(name).filters if isinstance(f, SessionMaskFilter)]
        assert len(filters) == 1, name
