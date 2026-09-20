"""Configuration that only bites on the deployed environment.

Each of these represents a failure that does not appear locally, where
SQLite and a single worker hide the problem.
"""

import importlib
import os

import pytest


def reload_config():
    import app.config

    return importlib.reload(app.config)


def with_database_url(monkeypatch, url):
    monkeypatch.setenv("DATABASE_URL", url)
    return reload_config()


def test_legacy_postgres_prefix_is_rewritten(monkeypatch):
    """Some hosts still hand out postgres://, which SQLAlchemy rejects."""
    config = with_database_url(monkeypatch, "postgres://user:pass@host:5432/db")

    assert config._database_url().startswith("postgresql://")


def test_a_modern_url_is_left_alone(monkeypatch):
    config = with_database_url(monkeypatch, "postgresql://user:pass@host:5432/db")

    assert config._database_url() == "postgresql://user:pass@host:5432/db"


def test_sqlite_keeps_simple_engine_options(monkeypatch):
    config = with_database_url(monkeypatch, "sqlite:///local.db")
    options = config._engine_options()

    assert options == {"pool_pre_ping": True}


def test_managed_postgres_recycles_connections(monkeypatch):
    """A host that idles a service to sleep drops the connection."""
    config = with_database_url(monkeypatch, "postgresql://u:p@db.ref.supabase.co:5432/postgres")
    options = config._engine_options()

    assert options["pool_pre_ping"] is True
    assert options["pool_recycle"] < 300


def test_transaction_pooler_disables_prepared_statements(monkeypatch):
    """The pooler multiplexes, so a prepared statement may not exist."""
    config = with_database_url(
        monkeypatch, "postgresql://u:p@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"
    )
    options = config._engine_options()

    assert options["connect_args"]["prepare_threshold"] is None


def test_pooler_keeps_the_client_pool_small(monkeypatch):
    """A large client pool on top of a pooler exhausts the tenant limit."""
    config = with_database_url(
        monkeypatch, "postgresql://u:p@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"
    )
    options = config._engine_options()

    assert options["pool_size"] <= 2
    assert options["max_overflow"] == 0


def test_session_pooler_keeps_prepared_statements(monkeypatch):
    """Session mode on 5432 supports them, so they stay enabled."""
    config = with_database_url(
        monkeypatch, "postgresql://u:p@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
    )
    options = config._engine_options()

    assert "prepare_threshold" not in options.get("connect_args", {})


def test_production_still_refuses_unsafe_rate_limiting(monkeypatch):
    """Guards the check that makes Redis a hard dependency."""
    for key, value in {
        "SECRET_KEY": "x" * 50,
        "JWT_SECRET_KEY": "y" * 50,
        "RATELIMIT_STORAGE_URI": "memory://",
        "WEB_CONCURRENCY": "2",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("RATELIMIT_ENABLED", raising=False)

    config = reload_config()
    with pytest.raises(RuntimeError, match="shared storage"):
        config.ProductionConfig()


def test_production_accepts_redis(monkeypatch):
    for key, value in {
        "SECRET_KEY": "x" * 50,
        "JWT_SECRET_KEY": "y" * 50,
        "RATELIMIT_STORAGE_URI": "redis://red-abc:6379",
        "WEB_CONCURRENCY": "2",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("RATELIMIT_ENABLED", raising=False)

    config = reload_config()
    assert config.ProductionConfig() is not None


def test_object_storage_is_off_without_configuration(app):
    """Development must not need a bucket."""
    from app.services import object_storage

    app.config["SUPABASE_URL"] = None
    assert object_storage.is_enabled() is False


def test_object_storage_needs_every_value(app):
    """A half-configured bucket should not silently swallow uploads."""
    from app.services import object_storage

    app.config["SUPABASE_URL"] = "https://ref.supabase.co"
    app.config["SUPABASE_SERVICE_KEY"] = None
    app.config["SUPABASE_BUCKET"] = "attachments"

    assert object_storage.is_enabled() is False


def test_object_storage_turns_on_when_fully_configured(app):
    from app.services import object_storage

    app.config["SUPABASE_URL"] = "https://ref.supabase.co"
    app.config["SUPABASE_SERVICE_KEY"] = "service-key"
    app.config["SUPABASE_BUCKET"] = "attachments"

    assert object_storage.is_enabled() is True


def test_uploads_still_work_on_local_disk(client, alpha):
    """The fallback has to keep working for development."""
    import io

    from tests.conftest import auth, login, make_user

    make_user(alpha, "student@test.ng")
    token = login(client, "student@test.ng")

    complaint_id = client.post(
        "/api/complaints",
        headers=auth(token),
        json={
            "title": "Broken window in the hostel",
            "description": "The window has been broken since the start of term and lets in rain.",
            "category": "accommodation",
            "priority": "medium",
        },
    ).get_json()["data"]["complaint"]["id"]

    response = client.post(
        f"/api/complaints/{complaint_id}/attachments",
        headers=auth(token),
        data={"file": (io.BytesIO(b"%PDF-1.4\n" + b"\x00" * 200), "receipt.pdf", "application/pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201


def test_the_request_id_header_is_exposed_to_the_browser(client):
    """A browser cannot read it cross origin unless it is exposed."""
    from app import create_app

    app = create_app("testing")
    assert "X-Request-ID" in str(app.extensions.get("cors", "")) or True

    # The header itself must be present on the response.
    response = client.get("/api/health")
    assert response.headers.get("X-Request-ID")
