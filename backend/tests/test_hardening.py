from tests.conftest import auth, login, make_user


def test_security_headers_are_present(client):
    response = client.get("/api/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_personal_data_is_not_cached(client, alpha):
    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    response = client.get("/api/complaints", headers=auth(token))

    assert response.headers["Cache-Control"] == "no-store"


def test_readiness_probe_reports_the_database(client):
    response = client.get("/api/ready")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ready"


def test_errors_are_returned_as_json(client):
    """A client should never have to parse an HTML error page."""
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.is_json
    assert response.get_json()["success"] is False


def test_production_refuses_insecure_defaults(monkeypatch):
    """Booting with a development secret in production must fail loudly."""
    import pytest

    from app.config import ProductionConfig

    monkeypatch.setenv("SECRET_KEY", "dev-secret-change-me")
    monkeypatch.setenv("JWT_SECRET_KEY", "anything")

    with pytest.raises(RuntimeError):
        ProductionConfig()
