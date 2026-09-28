from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_reports_environment_and_fonts(client: TestClient, settings) -> None:
    settings.fonts_dir.mkdir()
    (settings.fonts_dir / "Example.ttf").write_bytes(b"")

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert body["fonts"] == 1
