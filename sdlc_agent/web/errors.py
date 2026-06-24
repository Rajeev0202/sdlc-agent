"""Centralised request hooks and JSON error handling for the web app."""
from __future__ import annotations

import logging

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def register_request_hooks(app: Flask) -> None:
    """Attach response headers (caching / CORS) driven by app config."""

    @app.after_request
    def _apply_headers(response):
        if app.config.get("SEND_NO_CACHE_HEADERS"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        if app.config.get("ENABLE_CORS"):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response


def register_error_handlers(app: Flask) -> None:
    """Return structured JSON for HTTP errors and uncaught exceptions."""

    @app.errorhandler(HTTPException)
    def _handle_http_exception(exc: HTTPException):
        # Preserve HTML responses for non-API routes (e.g. the file browser).
        if not request.path.startswith("/api/"):
            return exc
        return (
            jsonify({"error": exc.description, "status": exc.code, "type": exc.name}),
            exc.code,
        )

    @app.errorhandler(Exception)
    def _handle_unexpected(exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.path)
        return jsonify({"error": str(exc), "status": 500, "type": "InternalServerError"}), 500
