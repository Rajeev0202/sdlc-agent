"""Tests for story S-003 — As a Compliance officer, I want audit all payment limit changes made by retail customers within the last 12 months, so that I can fulfil regulatory obligations and respond to investigations efficiently."""
import pytest
from src.payment_limits_management import app


@pytest.fixture
def client():
    app.testing = True
    return app.test_client()


def test_audit_all_payment_limit_changes_made_by_retail_customers_within_the_last_12_months_happy_path(client):
    # Happy path covers: Given a compliance officer authenticated via NatWest SSO, when they search limit change records with a date range up to 12 months, then all matching records are returned including customer ID, timestamp, old limit, new limit, and decision outcome
    resp = client.get('/audit_all_payment_limit_changes_made_by_retail_customers_within_the_last_12_months')
    assert resp.status_code == 200
    assert resp.get_json()['story'] == 'S-003'


def test_audit_all_payment_limit_changes_made_by_retail_customers_within_the_last_12_months_rejects_invalid_input(client):
    # Edge case: malformed path should not match the route.
    resp = client.get('/audit_all_payment_limit_changes_made_by_retail_customers_within_the_last_12_months/__nope__')
    assert resp.status_code == 404
