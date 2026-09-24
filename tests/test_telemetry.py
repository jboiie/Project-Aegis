"""Tests for src/telemetry/supabase_client.py - telemetry must fail open,
never break the request path it's logging. See PROJECT_DESC.md's
error-handling audit."""

from unittest.mock import MagicMock

import pytest

from src.telemetry.supabase_client import TelemetryClient


@pytest.mark.asyncio
async def test_log_event_insert_failure_does_not_raise():
    client = TelemetryClient(url="https://example.supabase.co", key="fake-key")
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.side_effect = RuntimeError("column aegis_events.errored does not exist")
    client._client = MagicMock()
    client._client.table.return_value = mock_table

    # Must not raise - a telemetry insert failure is not the caller's problem.
    await client.log_event(
        prompt="hello", blocked=False, blocked_reason="", checks=[], latency_ms=1.0, model="test-model",
    )


@pytest.mark.asyncio
async def test_log_event_success_path_still_inserts():
    client = TelemetryClient(url="https://example.supabase.co", key="fake-key")
    mock_table = MagicMock()
    client._client = MagicMock()
    client._client.table.return_value = mock_table

    await client.log_event(
        prompt="hello", blocked=True, blocked_reason="regex", checks=[], latency_ms=5.0, model="test-model",
        errored=False,
    )

    mock_table.insert.assert_called_once()
    inserted = mock_table.insert.call_args[0][0]
    assert inserted["blocked"] is True
    assert inserted["errored"] is False
