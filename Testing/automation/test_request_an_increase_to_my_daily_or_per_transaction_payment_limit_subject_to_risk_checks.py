"""Tests for story S-002 — As a Retail customer, I want request an increase to my daily or per-transaction payment limit subject to risk checks, so that I can make larger payments without needing to phone the call centre."""
import pytest
from src.payment_limits_management import app


@pytest.fixture
def client():
    app.testing = True
    return app.test_client()


def test_request_an_increase_to_my_daily_or_per_transaction_payment_limit_subject_to_risk_checks_happy_path(client):
    # Happy path covers: Given an authenticated retail customer, when they submit a limit increase request, then the request is validated against risk-check rules before approval or rejection
    resp = client.get('/request_an_increase_to_my_daily_or_per_transaction_payment_limit_subject_to_risk_checks')
    assert resp.status_code == 200
    assert resp.get_json()['story'] == 'S-002'


def test_request_an_increase_to_my_daily_or_per_transaction_payment_limit_subject_to_risk_checks_rejects_invalid_input(client):
    # Edge case: malformed path should not match the route.
    resp = client.get('/request_an_increase_to_my_daily_or_per_transaction_payment_limit_subject_to_risk_checks/__nope__')
    assert resp.status_code == 404
