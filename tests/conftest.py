"""Shared test fixtures."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from src.main import app
from src.gateway.schemas import SafetyVerdict, GuardrailCheck


@pytest.fixture
def client():
    """FastAPI test client with app.state pre-populated (no ML models loaded)."""
    # Pre-set app.state so the lifespan startup hook isn't needed in tests
    mock_verdict = SafetyVerdict(
        passed=True,
        checks=[GuardrailCheck(name="test", passed=True, confidence=1.0)],
    )
    mock_engine = MagicMock()
    mock_engine.screen = AsyncMock(return_value=mock_verdict)
    mock_engine.output_guard.screen_output = MagicMock(side_effect=lambda text: (True, text))

    mock_cache = MagicMock()
    mock_cache.connect = AsyncMock()
    mock_cache.disconnect = AsyncMock()

    app.state.guardrail_engine = mock_engine
    app.state.cache = mock_cache

    return TestClient(app)
