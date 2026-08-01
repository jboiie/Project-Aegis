"""
Supabase Telemetry Client — Ships events to the cloud database.

Logs every request (blocked or allowed) as a row in Supabase
for the Streamlit dashboard to query and visualize.

Table schema (create via scripts/setup_supabase.sql):
  - id (uuid, auto)
  - timestamp (timestamptz)
  - prompt_hash (text) — SHA256 of the prompt (privacy-safe)
  - blocked (boolean)
  - blocked_reason (text)
  - guardrail_checks (jsonb) — array of check results
  - latency_ms (float)
  - model (text) — target LLM model name
"""

from datetime import datetime, timezone
import hashlib
import json

import structlog

logger = structlog.get_logger()


class TelemetryClient:
    """Async telemetry client for Supabase."""

    def __init__(self, url: str, key: str, table: str = "aegis_events"):
        self.url = url
        self.key = key
        self.table = table
        self._client = None

    async def connect(self):
        """Initialize Supabase client. Falls back to local logging if unconfigured."""
        placeholder = not self.url or not self.key or "your-project" in self.url or self.key == "your_anon_key_here"
        if placeholder:
            logger.info("telemetry_client_dev_mode", table=self.table, reason="SUPABASE_URL/KEY not configured")
            return

        try:
            from supabase import create_client
            self._client = create_client(self.url, self.key)
            logger.info("telemetry_client_connected", table=self.table)
        except Exception as exc:
            logger.warning("telemetry_connect_failed", error=str(exc), action="using_local_logging")

    async def log_event(
        self,
        prompt: str,
        blocked: bool,
        blocked_reason: str,
        checks: list[dict],
        latency_ms: float,
        model: str,
    ):
        """
        Log a proxy event to Supabase.

        Args:
            prompt: Raw prompt text (hashed for privacy).
            blocked: Whether the request was blocked.
            blocked_reason: Human-readable block reason.
            checks: List of guardrail check results.
            latency_ms: Total processing latency.
            model: Target LLM model name.
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
            "blocked": blocked,
            "blocked_reason": blocked_reason,
            "guardrail_checks": json.dumps(checks),
            "latency_ms": latency_ms,
            "model": model,
        }

        if self._client:
            self._client.table(self.table).insert(event).execute()
        else:
            # Dev mode — just log locally
            logger.info("telemetry_event", **event)
