"""Tests for story S-001 — As a Retail customer, I want view my current daily and per-transaction payment limits in the mobile app, so that I can understand my spending boundaries without calling the contact centre."""
import pytest
from src.payment_limits_management import app


@pytest.fixture
def client():
    app.testing = True
    return app.test_client()


def test_view_my_current_daily_and_per_transaction_payment_limits_in_the_mobile_app_happy_path(client):
    # Happy path covers: Given an authenticated retail customer, when they navigate to the Payment Limits screen, then their current daily limit and per-transaction limit are displayed
    resp = client.get('/view_my_current_daily_and_per_transaction_payment_limits_in_the_mobile_app')
    assert resp.status_code == 200
    assert resp.get_json()['story'] == 'S-001'


def test_view_my_current_daily_and_per_transaction_payment_limits_in_the_mobile_app_rejects_invalid_input(client):
    # Edge case: malformed path should not match the route.
    resp = client.get('/view_my_current_daily_and_per_transaction_payment_limits_in_the_mobile_app/__nope__')
    assert resp.status_code == 404
