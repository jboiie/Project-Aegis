"""Tests for the optional shared-key auth on /v1 routes."""

import pytest

from src.config import settings

PAYLOAD = {"messages": [{"role": "user", "content": "hi"}]}


@pytest.fixture(autouse=True)
def _restore_api_key():
    original = settings.AEGIS_API_KEY
    yield
    settings.AEGIS_API_KEY = original


def test_no_auth_required_when_key_unset(client):
    settings.AEGIS_API_KEY = ""
    resp = client.post("/v1/chat/completions", json=PAYLOAD)
    assert resp.status_code == 200


def test_missing_header_rejected_when_key_set(client):
    settings.AEGIS_API_KEY = "secret"
    resp = client.post("/v1/chat/completions", json=PAYLOAD)
    assert resp.status_code == 401


def test_wrong_key_rejected(client):
    settings.AEGIS_API_KEY = "secret"
    resp = client.post(
        "/v1/chat/completions", json=PAYLOAD, headers={"Authorization": "Bearer wrong"}
    )
    assert resp.status_code == 401


def test_correct_key_accepted(client):
    settings.AEGIS_API_KEY = "secret"
    resp = client.post(
        "/v1/chat/completions", json=PAYLOAD, headers={"Authorization": "Bearer secret"}
    )
    assert resp.status_code == 200
