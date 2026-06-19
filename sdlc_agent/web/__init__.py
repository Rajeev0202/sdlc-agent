"""Web package — Flask application factory for the SDLC Agent UI."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask

from ..config import ROOT, BaseConfig, get_config

logger = logging.getLogger(__name__)


def _load_dotenv() -> None:
    """Load the project ``.env`` file if python-dotenv is available."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - optional dependency
        logger.warning("python-dotenv not installed; skipping %s", env_path)
        return
    load_dotenv(env_path)
    logger.info("Loaded environment from %s", env_path)


def _force_utf8_streams() -> None:
    """Avoid cp1252 crashes on Windows consoles when logging Unicode."""
    import sys

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):  # pragma: no cover - non-standard stream
            pass


def _configure_logging(level: str) -> None:
    """Configure root logging once, honouring the configured level."""
    _force_utf8_streams()
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )


def create_app(config: type[BaseConfig] | None = None) -> Flask:
    """Build and configure the Flask application.

    Args:
        config: Optional config class. Defaults to the ``APP_ENV`` profile.
    """
    _load_dotenv()
    config = config or get_config()
    _configure_logging(getattr(config, "LOG_LEVEL", "INFO"))

    here = Path(__file__).parent
    app = Flask(
        __name__,
        template_folder=str(here / "templates"),
        static_folder=str(here / "static"),
    )
    app.config.from_object(config)

    # Initialise the harness (registers observability hooks) before serving.
    try:
        from ..bootstrap import ensure_harness

        ensure_harness()
    except Exception:  # pragma: no cover - harness is best-effort
        logger.warning("Harness initialisation failed", exc_info=True)

    from .errors import register_error_handlers, register_request_hooks
    from .routes import bp as main_bp

    app.register_blueprint(main_bp)
    register_request_hooks(app)
    register_error_handlers(app)

    logger.info("SDLC Agent app created (env=%s, debug=%s)", os.getenv("APP_ENV", "development"), app.debug)
    return app


__all__ = ["create_app"]
