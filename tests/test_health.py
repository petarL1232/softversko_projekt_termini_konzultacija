from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_page_returns_static_ui() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Termini konzultacija" in response.text
    assert "/static/style.css" in response.text
    assert "/static/script.js" in response.text
