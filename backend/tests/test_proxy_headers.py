"""Identifying the caller behind a proxy.

Two things read the client address: the rate limits that protect sign in,
and the access log the record of processing depends on. Behind a proxy
both were reading the proxy, which fails quietly in opposite directions —
one limit shared by every user, and an audit trail naming the load
balancer.
"""

import importlib

import pytest

from flask import request
from flask_limiter.util import get_remote_address

PROXY = "10.0.0.7"
CLIENT = "197.210.55.12"


def build(monkeypatch, hops):
    monkeypatch.setenv("TRUSTED_PROXIES", str(hops))
    import app.config

    importlib.reload(app.config)
    import app as app_package

    importlib.reload(app_package)
    return app_package.create_app("testing")


def seen_by(application, caller=CLIENT):
    """What the application sees for a request arriving through the proxy.

    Deliberately routed through the test client rather than
    test_request_context: the latter builds the environ directly and so
    skips the WSGI middleware that is the whole subject here.
    """
    seen = application.extensions.setdefault("_whoami", {})

    if "/__whoami" not in {r.rule for r in application.url_map.iter_rules()}:

        @application.route("/__whoami")
        def whoami():
            seen["remote_addr"] = request.remote_addr
            seen["limiter_key"] = get_remote_address()
            return "", 204

    application.test_client().get(
        "/__whoami",
        environ_base={"REMOTE_ADDR": PROXY},
        headers={"X-Forwarded-For": caller},
    )
    return seen["remote_addr"], seen["limiter_key"]


def test_the_real_client_is_seen_through_one_proxy(monkeypatch):
    application = build(monkeypatch, 1)

    remote_addr, limiter_key = seen_by(application)

    assert remote_addr == CLIENT
    assert limiter_key == CLIENT


def test_a_forwarded_header_is_ignored_when_no_proxy_is_declared(monkeypatch):
    """The header is client-settable.

    Believing it on a directly reachable service would let anyone forge a
    source address and sidestep every per-address limit, so the default
    has to be to distrust it.
    """
    application = build(monkeypatch, 0)

    remote_addr, limiter_key = seen_by(application)

    assert remote_addr == PROXY
    assert limiter_key == PROXY


def test_two_callers_behind_one_proxy_are_limited_separately(monkeypatch):
    """The failure that prompted this.

    One person's failed sign ins were exhausting the limit for everybody,
    because every request counted against the proxy's address.
    """
    application = build(monkeypatch, 1)
    application.config["RATELIMIT_ENABLED"] = True

    keys = {seen_by(application, caller)[1] for caller in (CLIENT, "102.89.1.4")}

    assert keys == {CLIENT, "102.89.1.4"}


def test_the_access_log_records_the_person_not_the_load_balancer(monkeypatch):
    """The record of processing has to name who read a complaint."""
    application = build(monkeypatch, 1)

    recorded, _ = seen_by(application)

    assert recorded == CLIENT


def test_production_refuses_to_boot_without_declaring_its_proxies(monkeypatch):
    for key, value in {
        "SECRET_KEY": "x" * 50,
        "JWT_SECRET_KEY": "y" * 50,
        "RATELIMIT_STORAGE_URI": "redis://red-abc:6379",
        "WEB_CONCURRENCY": "2",
        "CORS_ORIGINS": "https://uni-complaints.vercel.app",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("RATELIMIT_ENABLED", raising=False)
    monkeypatch.delenv("MAIL_TO_CONSOLE", raising=False)
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)

    import app.config

    config = importlib.reload(app.config)

    with pytest.raises(RuntimeError, match="TRUSTED_PROXIES"):
        config.ProductionConfig()


def test_production_boots_once_they_are_declared(monkeypatch):
    for key, value in {
        "SECRET_KEY": "x" * 50,
        "JWT_SECRET_KEY": "y" * 50,
        "RATELIMIT_STORAGE_URI": "redis://red-abc:6379",
        "WEB_CONCURRENCY": "2",
        "CORS_ORIGINS": "https://uni-complaints.vercel.app",
        "TRUSTED_PROXIES": "1",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("RATELIMIT_ENABLED", raising=False)
    monkeypatch.delenv("MAIL_TO_CONSOLE", raising=False)

    import app.config

    config = importlib.reload(app.config)

    assert config.ProductionConfig() is not None
