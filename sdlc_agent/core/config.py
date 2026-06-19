"""Application configuration.

Config is environment-driven so the same image runs in dev, test, and prod.
Select the active profile with the ``APP_ENV`` (or ``FLASK_ENV``) variable;
``development`` is the default.
"""
from __future__ import annotations

import os
from pathlib import Path

#: Repository root (…/sdlc-agent), used to anchor runtime artifact folders.
#: This file lives at sdlc_agent/core/config.py, so the root is three levels up.
ROOT = Path(__file__).resolve().parents[2]


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class BaseConfig:
    """Settings shared by every environment."""

    ROOT = ROOT
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-change-me")

    # Preserve insertion order of JSON keys in responses.
    JSON_SORT_KEYS = False

    # Quality gate threshold surfaced to the harness / UI.
    COVERAGE_THRESHOLD = int(os.getenv("COVERAGE_THRESHOLD", "80"))

    # Cross-origin access — enabled by default for local UI development.
    ENABLE_CORS = _as_bool(os.getenv("ENABLE_CORS"), default=True)

    # Send no-cache headers (handy in dev so UI changes show immediately).
    SEND_NO_CACHE_HEADERS = True

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5002"))
    DEBUG = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True
    SEND_NO_CACHE_HEADERS = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    SEND_NO_CACHE_HEADERS = False
    ENABLE_CORS = _as_bool(os.getenv("ENABLE_CORS"), default=False)


_PROFILES = {
    "development": DevelopmentConfig,
    "dev": DevelopmentConfig,
    "testing": TestingConfig,
    "test": TestingConfig,
    "production": ProductionConfig,
    "prod": ProductionConfig,
}


def get_config(name: str | None = None) -> type[BaseConfig]:
    """Resolve the config class for ``name`` (or the environment default)."""
    profile = (name or os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "development").lower()
    return _PROFILES.get(profile, DevelopmentConfig)
