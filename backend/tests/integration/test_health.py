from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_is_degraded_without_fonts(client: TestClient) -> None:
    """The test container points at an empty fonts dir: not ready."""
    response = client.get("/api/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["environment"] == "test"
    assert body["fonts"] == 0


def test_health_is_ok_with_real_fonts_and_filaments(api: TestClient) -> None:
    response = api.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["fonts"] == 2
    assert body["filaments"] > 2000
    assert set(body["cache"]) == {"entries", "size_bytes", "hits", "misses"}
    assert response.headers["X-Request-ID"]
