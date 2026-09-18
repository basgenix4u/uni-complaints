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

    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True

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
    SMS_PROVIDER = os.getenv("SMS_PROVIDER")


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


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None):
    name = name or os.getenv("FLASK_ENV", "development")
    config = CONFIGS.get(name, DevelopmentConfig)
    return config() if name == "production" else config
