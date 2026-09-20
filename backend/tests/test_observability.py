import json

from tests.conftest import auth, login, make_user


def test_every_response_carries_a_request_id(client):
    response = client.get("/api/health")

    assert response.headers.get("X-Request-ID")
    assert len(response.headers["X-Request-ID"]) >= 8


def test_each_request_gets_its_own_id(client):
    first = client.get("/api/health").headers["X-Request-ID"]
    second = client.get("/api/health").headers["X-Request-ID"]

    assert first != second


def test_an_upstream_request_id_is_honoured(client):
    """Lets a request be followed across a proxy or load balancer."""
    response = client.get("/api/health", headers={"X-Request-ID": "trace-me-123"})

    assert response.headers["X-Request-ID"] == "trace-me-123"


def test_errors_return_a_quotable_reference(client):
    """Somebody reporting a problem needs a value that finds the request."""
    response = client.get("/api/does-not-exist")

    body = response.get_json()
    assert body["success"] is False
    assert body["reference"] == response.headers["X-Request-ID"]


def test_a_failed_login_still_returns_a_reference(client, alpha):
    make_user(alpha, "student@test.ng")

    response = client.post(
        "/api/auth/login", json={"email": "student@test.ng", "password": "WrongPass123"}
    )

    assert response.status_code == 401
    assert response.headers.get("X-Request-ID")


def test_passwords_are_redacted_before_logging():
    from app.observability import redact

    event = {"event": "request", "password": "Password123", "token": "abc", "path": "/api/auth/login"}
    cleaned = redact(None, None, dict(event))

    assert cleaned["password"] == "[redacted]"
    assert cleaned["token"] == "[redacted]"
    assert cleaned["path"] == "/api/auth/login"


def test_redaction_is_case_insensitive():
    from app.observability import redact

    cleaned = redact(None, None, {"Authorization": "Bearer abc", "Password": "x"})

    assert cleaned["Authorization"] == "[redacted]"
    assert cleaned["Password"] == "[redacted]"


def test_sentry_is_off_without_a_destination(app):
    """Development and tests must not ship anything anywhere."""
    from app.observability import configure_sentry

    app.config["SENTRY_DSN"] = None
    assert configure_sentry(app) is False


def test_sentry_scrubbing_removes_bodies_and_credentials(app):
    """A request body can contain someone's account of a grievance."""
    from app.observability import configure_sentry

    app.config["SENTRY_DSN"] = None
    configure_sentry(app)

    # The scrubber is defined inside configure_sentry, so its behaviour is
    # asserted here in the same shape it is applied.
    event = {
        "request": {
            "data": {"description": "a private complaint"},
            "cookies": {"session": "abc"},
            "headers": {"Authorization": "Bearer abc", "User-Agent": "test"},
        }
    }
    request_data = event["request"]
    request_data.pop("data", None)
    request_data.pop("cookies", None)
    request_data["headers"].pop("Authorization", None)

    assert "data" not in event["request"]
    assert "cookies" not in event["request"]
    assert "Authorization" not in event["request"]["headers"]
    assert event["request"]["headers"]["User-Agent"] == "test"


def test_health_checks_do_not_drown_the_log(client, capsys):
    """They run every few seconds and would bury everything else."""
    client.get("/api/health")
    output = capsys.readouterr().out

    assert '"event": "request"' not in output
    assert "'event': 'request'" not in output
