"""Structured logging, request correlation and error reporting.

When a registrar reports that a complaint vanished, the question is what
happened to one request among thousands. Unstructured lines on a container
cannot answer that. Every log line here carries a request id, and every
error response returns the same id, so a person can quote it and the logs
can be searched for exactly that request.
"""

import logging
import sys
import time
import uuid

import structlog
from flask import g, request

# Never written to logs, whatever else happens.
REDACTED_FIELDS = {
    "password",
    "new_password",
    "current_password",
    "admin_password",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "api_key",
    "secret",
}

# Bodies are not logged on these routes even in full. They carry
# credentials or a person's account of a grievance.
SENSITIVE_PATHS = ("/api/auth/", "/api/privacy/")


def redact(_logger, _method, event_dict):
    """Strip anything that should never reach a log aggregator."""
    for key in list(event_dict):
        if key.lower() in REDACTED_FIELDS:
            event_dict[key] = "[redacted]"
    return event_dict


def add_request_context(_logger, _method, event_dict):
    """Attach the request id and actor to every line inside a request."""
    request_id = getattr(g, "request_id", None)
    if request_id:
        event_dict["request_id"] = request_id

    user = getattr(g, "current_user", None)
    if user is not None:
        event_dict["user_id"] = user.id
        event_dict["role"] = user.role
        # Recorded so a support question can be scoped to one institution
        # without also naming the person.
        event_dict["institution_id"] = user.institution_id

    return event_dict


def configure_logging(app):
    json_output = not app.debug and not app.testing

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    )

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_request_context,
        redact,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Machine readable where something will collect it, readable by a
    # person while developing.
    processors.append(
        structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()


def configure_sentry(app):
    """Report unhandled errors, if a destination is configured.

    Absent configuration this does nothing, so development and tests are
    unaffected.
    """
    dsn = app.config.get("SENTRY_DSN")
    if not dsn:
        return False

    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration

    def scrub(event, _hint):
        # Request bodies can contain a person's account of a grievance and
        # must not be shipped to a third party.
        request_data = event.get("request", {})
        request_data.pop("data", None)
        request_data.pop("cookies", None)
        headers = request_data.get("headers", {})
        for header in ("Authorization", "Cookie"):
            headers.pop(header, None)
        return event

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        environment=app.config.get("ENVIRONMENT", "production"),
        release=app.config.get("RELEASE"),
        traces_sample_rate=float(app.config.get("SENTRY_TRACES_SAMPLE_RATE", 0.0)),
        # Personal data must not leave the deployment.
        send_default_pii=False,
        before_send=scrub,
    )
    return True


def register_request_logging(app, logger):
    @app.before_request
    def start_request():
        # Honour an id from the load balancer so a request can be followed
        # across services, otherwise mint one.
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        g.request_started = time.perf_counter()

    @app.after_request
    def finish_request(response):
        started = getattr(g, "request_started", None)
        duration_ms = round((time.perf_counter() - started) * 1000, 1) if started else None

        response.headers["X-Request-ID"] = getattr(g, "request_id", "")

        # Health checks run every few seconds and would drown the log.
        if request.path in ("/api/health", "/api/ready"):
            return response

        event = {
            "event": "request",
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "ip": request.remote_addr,
        }

        if response.status_code >= 500:
            logger.error(**event)
        elif response.status_code >= 400:
            logger.warning(**event)
        else:
            logger.info(**event)

        return response

    @app.teardown_request
    def clear_context(_exception=None):
        structlog.contextvars.clear_contextvars()


def request_id() -> str | None:
    return getattr(g, "request_id", None)
