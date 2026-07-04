from fastapi.testclient import TestClient

from content_factory.api import app


def test_health_is_public():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_episode_requires_token_when_configured(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "test-secret")
    response = TestClient(app).post("/api/v1/episodes", json={
        "case_id": "AIC-1000", "title": "A verified AI incident",
        "angle": "Professionals remain responsible for verification.",
    })
    assert response.status_code == 401


def test_production_api_is_closed_without_token(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("API_TOKEN", raising=False)
    response = TestClient(app).get("/api/v1/episodes/AIC-1000")
    assert response.status_code == 503


def test_episode_is_accepted(monkeypatch, tmp_path):
    monkeypatch.setenv("CONTENT_FACTORY_ROOT", str(tmp_path))
    monkeypatch.delenv("API_TOKEN", raising=False)
    monkeypatch.setattr("content_factory.api.execute_episode", lambda *args: None)
    response = TestClient(app).post("/api/v1/episodes", json={
        "case_id": "AIC-1001", "title": "A verified AI incident",
        "angle": "Professionals remain responsible for verification.",
        "sources": ["https://example.com/source"]
    })
    assert response.status_code == 202
    assert response.json()["case_id"] == "AIC-1001"


def test_login_creates_http_only_session(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "a-secure-test-token")
    monkeypatch.delenv("ENV", raising=False)
    client = TestClient(app)
    login = client.post("/api/v1/auth/session", json={"api_token": "a-secure-test-token"})
    assert login.status_code == 204
    assert "HttpOnly" in login.headers["set-cookie"]
    assert client.get("/api/v1/auth/session").status_code == 200
