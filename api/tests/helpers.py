"""Shared test helpers: sessions signed by the app under test, for a chosen user id."""

from urllib.parse import quote

from fastapi.testclient import TestClient


def session_for(client: TestClient, user_id: str) -> str:
    _, session, _ = client.app.state.signer.issue(user_id)
    return session


def bearer(client: TestClient, user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {session_for(client, user_id)}"}


def room_url(
    client: TestClient, user_id: str, name: str, role: str = "speaker", room: str = "slc1"
) -> str:
    session = quote(session_for(client, user_id))
    return f"/ws/rooms/{room}?session={session}&name={quote(name)}&role={role}"
