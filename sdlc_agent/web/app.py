"""Backward-compatible entrypoint for the SDLC Agent web app.

Historically callers did ``from sdlc_agent.web.app import app``. The application
is now built by the factory in :mod:`sdlc_agent.web`; this module exposes a
ready-made instance and a ``main()`` dev-server runner.
"""
from __future__ import annotations

from . import create_app

app = create_app()


def main() -> None:
    """Run the Flask development server using the configured host/port."""
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"])


if __name__ == "__main__":
    main()
