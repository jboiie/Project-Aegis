"""Tests for the gateway health check and basic routing."""

from unittest.mock import AsyncMock, patch

from src.config import settings
from src.main import app


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_endpoint_exists(client):
    response = client.post("/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "hello"}]
    })
    assert response.status_code == 200


def test_target_llm_failure_returns_502_not_200(client):
    # Previously forward_to_llm had no try/except in router.py at all - an
    # exception (dead model, timeout, target 500) crashed past this point
    # unhandled, returning a raw 500 with no telemetry row ever written.
    #
    # A first fix returned 200 with "[ERROR]" in the body - but
    # template.py/encoding.py detect a failure via
    # response.raise_for_status(), which never fires on a 200, so that
    # response would get parsed as a normal (refused) completion and
    # counted as blocked. Same bug class as pair.py's "[ERROR]" marker
    # matching is_blocked, one layer up. 502 is required so
    # raise_for_status() actually raises. See PROJECT_DESC.md's
    # error-handling audit.
    with patch("src.gateway.router.forward_to_llm", AsyncMock(side_effect=RuntimeError("boom"))):
        response = client.post("/v1/chat/completions", json={
            "messages": [{"role": "user", "content": "hello"}]
        })

    assert response.status_code == 502
    body = response.json()
    assert body["error"]["type"] == "target_llm_error"
    assert "boom" in body["error"]["message"]

    # Logged as its own explicit outcome, not folded into blocked=True/False.
    log_call = app.state.telemetry.log_event.call_args
    assert log_call.kwargs["errored"] is True
    assert log_call.kwargs["blocked"] is False


def test_campaign_mode_header_skips_guardrails_only_with_matching_token(client):
    # CAMPAIGN_MODE_TOKEN empty by default (see src/config.py) - normal
    # requests are completely unaffected regardless of any header sent.
    # Only a request carrying the exact matching token skips screen()
    # entirely. See PROJECT_DESC.md's guardrails-off-ablation design.
    assert settings.CAMPAIGN_MODE_TOKEN == ""

    with patch("src.gateway.router.settings.CAMPAIGN_MODE_TOKEN", "secret-token-123"):
        # Wrong/missing token -> full stack still runs (mock_engine.screen called).
        client.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "hello"}]},
                    headers={"X-Campaign-Mode": "wrong-token"})
        assert app.state.guardrail_engine.screen.called

        app.state.guardrail_engine.screen.reset_mock()

        # Matching token -> screen() never called at all.
        response = client.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "hello"}]},
                               headers={"X-Campaign-Mode": "secret-token-123"})
        assert response.status_code == 200
        assert not app.state.guardrail_engine.screen.called
