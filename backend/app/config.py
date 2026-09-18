"""Application configuration."""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-change-me")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'resolve.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "30"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_DAYS", "30"))
    )

    CORS_ORIGINS = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if o.strip()
    ]

    # In-process counters are per worker, so a limit of ten is really ten
    # times the worker count. Point this at Redis in production or the
    # protection is largely notional.
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True
    # Escape hatch for end to end runs, which sign in repeatedly against a
    # throwaway database. Never set this on a deployed environment.
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() != "false"

    JSON_SORT_KEYS = False

    # Uploads live outside the served tree and are returned through an
    # authorised endpoint rather than by static path.
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))
    MAX_CONTENT_LENGTH = 6 * 1024 * 1024

    # Outbound delivery. Absent configuration leaves messages queued
    # rather than discarded.
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@resolve.ng")
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
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_ENABLED = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


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


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None):
    name = name or os.getenv("FLASK_ENV", "development")
    config = CONFIGS.get(name, DevelopmentConfig)
    return config() if name == "production" else config
