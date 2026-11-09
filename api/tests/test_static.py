from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from confpilot.app import create_app


@pytest.fixture
def static_client(tmp_path: Path, make_settings) -> TestClient:
    site = tmp_path / "site"
    (site / "assets").mkdir(parents=True)
    (site / "index.html").write_text("<h1>ConfPilot</h1>", encoding="utf-8")
    (site / "assets" / "app.js").write_text("export {}", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("outside the static dir", encoding="utf-8")
    return TestClient(create_app(make_settings(static_dir=site)))


@pytest.mark.parametrize("path", ["/", "/stage", "/rooms/slc1/recap"])
def test_static_serves_index_for_app_routes(static_client: TestClient, path: str) -> None:
    response = static_client.get(path)

    assert response.status_code == 200
    assert "ConfPilot" in response.text


def test_static_serves_files_and_404s_missing_assets(static_client: TestClient) -> None:
    assert static_client.get("/assets/app.js").text == "export {}"
    assert static_client.get("/assets/missing.js").status_code == 404


@pytest.mark.parametrize("path", ["/api/nope", "/api", "/ws/rooms/x", "/healthz/extra"])
def test_static_never_shadows_reserved_prefixes(static_client: TestClient, path: str) -> None:
    response = static_client.get(path)

    assert response.status_code == 404
    assert "ConfPilot" not in response.text


def test_static_keeps_healthz(static_client: TestClient) -> None:
    assert static_client.get("/healthz").json()["status"] == "ok"
    assert static_client.head("/healthz").status_code == 200


@pytest.mark.parametrize(
    "path", ["/%2e%2e/secret.txt", "/..%2fsecret.txt", "/assets/..%5c..%5csecret.txt"]
)
def test_static_does_not_escape_its_directory(static_client: TestClient, path: str) -> None:
    assert "outside the static dir" not in static_client.get(path).text


def test_static_answers_a_nul_byte_with_404(static_client: TestClient) -> None:
    assert static_client.get("/assets/%00.js").status_code == 404


def test_static_dir_without_index_is_skipped(tmp_path: Path, make_settings) -> None:
    client = TestClient(create_app(make_settings(static_dir=tmp_path)))

    assert client.get("/").status_code == 404
    assert client.get("/healthz").status_code == 200


def test_static_gzips_large_assets(tmp_path: Path, make_settings) -> None:
    site = tmp_path / "site"
    (site / "assets").mkdir(parents=True)
    (site / "index.html").write_text("<h1>ConfPilot</h1>", encoding="utf-8")
    (site / "assets" / "big-abc123.js").write_text("export const x = 1;\n" * 500, encoding="utf-8")
    client = TestClient(create_app(make_settings(static_dir=site)))

    response = client.get("/assets/big-abc123.js", headers={"Accept-Encoding": "gzip"})

    assert response.headers["content-encoding"] == "gzip"
    assert response.text.startswith("export const x")


def test_static_caches_hashed_assets_but_not_the_shell(static_client: TestClient) -> None:
    asset = static_client.get("/assets/app.js").headers["cache-control"]
    assert "immutable" in asset
    assert "max-age=31536000" in asset
    assert static_client.get("/").headers["cache-control"] == "no-cache"
