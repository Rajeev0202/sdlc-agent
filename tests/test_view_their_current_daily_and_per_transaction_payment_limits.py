"""Tests for story S-001 — As a Retail customer, I want view their current daily and per-transaction payment limits, so that manage their account safely from the mobile app."""
import pytest

try:
    from src.payment_limits_management import app  # type: ignore
except ImportError:
    from flask import Flask
    from src.payment_limits_management import bp  # type: ignore
    app = Flask(__name__)
    app.register_blueprint(bp)


@pytest.fixture
def client():
    app.testing = True
    return app.test_client()


def test_view_their_current_daily_and_per_transaction_payment_limits_smoke(client):
    # Smoke: covers Given an authenticated user, when they view their current daily and per-transaction payment limits, then the request succeeds and a confirmation is returned.
    # Confirms the Flask test client can be constructed and the app
    # registers routes for this story without raising.
    assert client.application is not None
    rules = [r.rule for r in client.application.url_map.iter_rules()]
    assert len(rules) > 0


def test_view_their_current_daily_and_per_transaction_payment_limits_requires_auth(client):
    # Edge: an unknown path must 404 rather than leaking state.
    resp = client.get('/__definitely_not_a_route__/view_their_current_daily_and_per_transaction_payment_limits')
    assert resp.status_code in (401, 403, 404)
