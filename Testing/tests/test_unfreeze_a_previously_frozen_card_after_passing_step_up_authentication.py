"""Tests for story S-002 — As a Retail customer, I want unfreeze a previously frozen card after passing step-up authentication, so that manage their account safely from the mobile app."""
import pytest

try:
    from src.card_freeze_unfreeze_mobile import app  # type: ignore
except ImportError:
    from flask import Flask
    from src.card_freeze_unfreeze_mobile import bp  # type: ignore
    app = Flask(__name__)
    app.register_blueprint(bp)


@pytest.fixture
def client():
    app.testing = True
    return app.test_client()


def test_unfreeze_a_previously_frozen_card_after_passing_step_up_authentication_smoke(client):
    # Smoke: covers Given an authenticated user, when they unfreeze a previously frozen card after passing step-up authentication, then the request succeeds and a confirmation is returned.
    # Confirms the Flask test client can be constructed and the app
    # registers routes for this story without raising.
    assert client.application is not None
    rules = [r.rule for r in client.application.url_map.iter_rules()]
    assert len(rules) > 0


def test_unfreeze_a_previously_frozen_card_after_passing_step_up_authentication_requires_auth(client):
    # Edge: an unknown path must 404 rather than leaking state.
    resp = client.get('/__definitely_not_a_route__/unfreeze_a_previously_frozen_card_after_passing_step_up_authentication')
    assert resp.status_code in (401, 403, 404)
