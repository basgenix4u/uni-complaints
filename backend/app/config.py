"""Application configuration."""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def _database_url() -> str:
    """Normalise the database URL.

    Some hosts still hand out the legacy postgres:// prefix, which
    SQLAlchemy stopped accepting. Rewriting it here avoids a failure that
    only appears on the deployed environment.
    """
    url = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'resolve.db')}")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _origins(raw: str) -> list[str]:
    """Parse the configured allowlist into values a browser can match.

    A browser's Origin header is scheme://host[:port] with no path and no
    trailing slash, so an entry typed as https://example.com/ matches
    nothing and CORS fails silently with no error anywhere in the logs.
    That exact typo cost us a production outage, so the trailing slash is
    stripped rather than trusted.
    """
    origins = []
    for entry in raw.split(","):
        entry = entry.strip().rstrip("/")
        if entry and entry not in origins:
            origins.append(entry)
    return origins


def _engine_options() -> dict:
    """Engine settings appropriate to the database in use."""
    url = _database_url()

    if url.startswith("sqlite"):
        return {"pool_pre_ping": True}

    options = {
        # A dropped connection is common on managed Postgres and on hosts
        # that idle a service to sleep. Without this the first request
        # after an idle period fails.
        "pool_pre_ping": True,
        # Recycle below the usual pooler and load balancer idle timeout.
        "pool_recycle": 280,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "2")),
        "connect_args": {"connect_timeout": 10},
    }

    # Only transaction mode multiplexes connections, and it is identified
    # by the port rather than the host: the same pooler hostname serves
    # session mode on 5432, where prepared statements are fine. Keying on
    # the host would needlessly restrict session mode.
    if ":6543" in url:
        options["connect_args"]["prepare_threshold"] = None
        options["connect_args"]["options"] = "-c statement_timeout=30000"
        # The pooler keeps its own pool; a large client pool on top of it
        # exhausts the tenant connection limit.
        options["pool_size"] = int(os.getenv("DB_POOL_SIZE", "2"))
        options["max_overflow"] = 0

    return options


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-change-me")

    # A dedicated PostgreSQL schema keeps these tables out of `public`,
    # so the same database can host another application without the two
    # colliding on common names such as users or notifications. Empty
    # means `public`, which is right for a database of our own.
    DB_SCHEMA = os.getenv("DB_SCHEMA") or None

    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options()

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "30"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_DAYS", "30"))
    )

    CORS_ORIGINS = _origins(
        os.getenv("CORS_ORIGINS", "http://localhost:5173")
    )

    # Preview deployments get a unique hostname each time, so they cannot
    # be listed individually. A regex allows them without opening the API
    # to any origin. Leave unset in production if previews are not used.
    CORS_ORIGIN_REGEX = os.getenv("CORS_ORIGIN_REGEX")

    # In-process counters are per worker, so a limit of ten is really ten
    # times the worker count. Point this at Redis in production or the
    # protection is largely notional.
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True
    # Escape hatch for end to end runs, which sign in repeatedly against a
    # throwaway database. Never set this on a deployed environment.
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() != "false"

    # Number of proxies between the client and the application, whose
    # X-Forwarded-* headers may be believed. Render puts exactly one in
    # front of us. Zero means trust nothing, which is right when the
    # application is reached directly: a client can set these headers
    # itself, so trusting them unconditionally would let anyone forge a
    # source address and defeat every per-address limit.
    TRUSTED_PROXIES = int(os.getenv("TRUSTED_PROXIES", "0"))

    JSON_SORT_KEYS = False

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    RELEASE = os.getenv("RELEASE")
    # Absent, error reporting is simply off.
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    SENTRY_TRACES_SAMPLE_RATE = os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")

    # Shared secret for the HTTP task trigger. Unset means the endpoint
    # does not exist, so a deployment that forgets it is not left with an
    # open trigger. Needed only where the host has no scheduler.
    TASK_TOKEN = os.getenv("TASK_TOKEN")

    # Uploads live outside the served tree and are returned through an
    # authorised endpoint rather than by static path.
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))

    # Object storage for attachments. Most container hosts give the
    # container an ephemeral filesystem, so anything written to disk is
    # lost on the next deploy. Set these and uploads go to a private
    # bucket instead. The bucket must not be public: files are streamed
    # by the API after the same authorisation checks.
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "attachments")

    # Cloudinary. Takes precedence over Supabase Storage when both are
    # set. Everything is uploaded with the authenticated delivery type,
    # because Cloudinary's default makes assets public on the CDN and
    # these are complaint attachments.
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
    CLOUDINARY_FOLDER = os.getenv("CLOUDINARY_FOLDER", "resolve/attachments")
    MAX_CONTENT_LENGTH = 6 * 1024 * 1024

    # Outbound delivery. Absent configuration leaves messages queued
    # rather than discarded.
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@resolve.ng")

    # Write emails to the log instead of sending them, so a deployment
    # without SMTP can still be used: the confirmation link is readable
    # in the log stream. Refused in production, where it would put
    # account-confirmation links into logs that many people can read.
    MAIL_TO_CONSOLE = os.getenv("MAIL_TO_CONSOLE", "false").lower() == "true"
    # Where reset links point. Must match the deployed front end.
    APP_URL = os.getenv("APP_URL", "http://localhost:5173")
    # One of: termii, africastalking, console. Empty disables SMS.
    SMS_PROVIDER = os.getenv("SMS_PROVIDER")
    SMS_SENDER_ID = os.getenv("SMS_SENDER_ID", "Resolve")
    TERMII_API_KEY = os.getenv("TERMII_API_KEY")
    AFRICASTALKING_API_KEY = os.getenv("AFRICASTALKING_API_KEY")
    AFRICASTALKING_USERNAME = os.getenv("AFRICASTALKING_USERNAME")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads_test")

    # In-memory SQLite by default, because the suite has to be runnable
    # with no infrastructure. TEST_DATABASE_URL points it at a real
    # PostgreSQL instead, which is how CI runs it.
    #
    # This is not a nicety. SQLite serialises writes, so it cannot show a
    # lost update: two concurrency defects reached main because the suite
    # could not express the failure. Anything about locking, isolation or
    # server-side defaults is only meaningfully tested on PostgreSQL.
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL") or "sqlite:///:memory:"

    RATELIMIT_ENABLED = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)

    # A pool per test would exhaust PostgreSQL's connection limit long
    # before the suite finished.
    SQLALCHEMY_ENGINE_OPTIONS = (
        {"pool_pre_ping": True}
        if (os.getenv("TEST_DATABASE_URL") or "sqlite").startswith("sqlite")
        else {"pool_pre_ping": True, "pool_size": 2, "max_overflow": 3}
    )


class ProductionConfig(Config):
    DEBUG = False

    def __init__(self) -> None:
        # Refuse to boot with development defaults in production.
        for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
            value = os.getenv(key, "")
            if not value or "change-me" in value or value.startswith("dev-"):
                raise RuntimeError(f"{key} must be set to a secure value in production")

        # Rate limits held in process memory are counted per worker, so the
        # configured limit is multiplied by the number of workers. With more
        # than one worker that is not a limit worth relying on.
        storage = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
        workers = int(os.getenv("WEB_CONCURRENCY", "0"))
        if storage.startswith("memory://") and workers != 1:
            raise RuntimeError(
                "RATELIMIT_STORAGE_URI must point at shared storage such as Redis "
                "when running more than one worker, otherwise each worker counts "
                "separately and the login limit does not hold. Set WEB_CONCURRENCY=1 "
                "only for a single process deployment."
            )

        if os.getenv("RATELIMIT_ENABLED", "true").lower() == "false":
            raise RuntimeError("RATELIMIT_ENABLED must not be disabled in production")

        # A confirmation link is a credential. Writing it to the log is a
        # convenience for local work and never acceptable in production.
        if os.getenv("MAIL_TO_CONSOLE", "false").lower() == "true":
            raise RuntimeError(
                "MAIL_TO_CONSOLE writes confirmation links to the log and must not be "
                "enabled in production. Configure SMTP_HOST instead."
            )

        # An unset allowlist falls back to localhost, which every browser
        # request from the real site then fails. The API stays healthy and
        # the logs stay clean, so the only symptom is a site that cannot
        # log in. Fail at boot instead, where the cause is legible.
        configured = _origins(os.getenv("CORS_ORIGINS", ""))
        if not configured or all(
            o.startswith(("http://localhost", "http://127.0.0.1")) for o in configured
        ):
            raise RuntimeError(
                "CORS_ORIGINS must list the browser origin of the deployed frontend, "
                "for example https://uni-complaints.vercel.app. Without it every "
                "browser request is blocked while the API itself appears healthy."
            )

        # Every managed host puts a proxy in front of the container. Left
        # at zero, every caller shares one apparent address: the login
        # limit becomes global, so one person's failed attempts lock out
        # everyone, and the access log records the load balancer instead
        # of the person who read the complaint. Both fail quietly, which
        # is why this is checked rather than left to a deployment note.
        if int(os.getenv("TRUSTED_PROXIES", "0")) < 1:
            raise RuntimeError(
                "TRUSTED_PROXIES must be set to the number of proxies in front of "
                "this service, normally 1 on a managed host. Without it every "
                "request appears to come from the load balancer, so rate limits "
                "are shared between all users and the access log records the "
                "wrong address."
            )


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None):
    name = name or os.getenv("FLASK_ENV", "development")
    config = CONFIGS.get(name, DevelopmentConfig)
    return config() if name == "production" else config
