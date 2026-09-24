"""Tests for dashboard aggregation math — pure pandas, no Supabase/Streamlit."""

import pandas as pd

from dashboard.data import (
    events_to_df,
    compute_summary,
    requests_over_time,
    blocked_reason_breakdown,
)

ROWS = [
    {"timestamp": "2026-08-02T10:00:00+00:00", "blocked": True, "blocked_reason": "regex", "latency_ms": 5.0},
    {"timestamp": "2026-08-02T10:05:00+00:00", "blocked": False, "blocked_reason": "", "latency_ms": 15.0},
    {"timestamp": "2026-08-02T11:00:00+00:00", "blocked": True, "blocked_reason": "regex", "latency_ms": 7.0},
    {"timestamp": "2026-08-02T11:10:00+00:00", "blocked": False, "blocked_reason": "", "latency_ms": 9.0},
]


def test_events_to_df_parses_timestamp():
    df = events_to_df(ROWS)
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
    assert len(df) == 4


def test_events_to_df_empty():
    df = events_to_df([])
    assert df.empty


def test_compute_summary():
    df = events_to_df(ROWS)
    summary = compute_summary(df)
    assert summary["total"] == 4
    assert summary["blocked"] == 2
    assert summary["block_rate_pct"] == 50.0
    assert summary["avg_latency_ms"] == 9.0
    # ROWS predate the `errored` column (see setup_supabase.sql's idempotent
    # ADD COLUMN) - missing column must be treated as 0 errors, not raise.
    assert summary["errored"] == 0
    # Most recent non-blocked row, 2026-08-02T11:10:00.
    assert summary["last_successful_request"] == pd.Timestamp("2026-08-02T11:10:00+00:00")


def test_compute_summary_empty():
    summary = compute_summary(events_to_df([]))
    assert summary["total"] == 0
    assert summary["blocked"] == 0
    assert summary["block_rate_pct"] == 0.0
    assert summary["avg_latency_ms"] == 0.0
    assert summary["errored"] == 0
    assert summary["last_successful_request"] is None


def test_compute_summary_excludes_errored_from_last_successful():
    # A request/API failure is a separate outcome from blocked/allowed - see
    # PROJECT_DESC.md's error-handling audit. An errored row has
    # blocked=False (no real verdict either way) so it must not count as
    # the "last successful request", and must be surfaced in its own count.
    rows = [
        {"timestamp": "2026-08-02T10:00:00+00:00", "blocked": False, "blocked_reason": "", "latency_ms": 5.0, "errored": False},
        {"timestamp": "2026-08-02T12:00:00+00:00", "blocked": False, "blocked_reason": "[ERROR] boom", "latency_ms": 0.0, "errored": True},
    ]
    summary = compute_summary(events_to_df(rows))
    assert summary["errored"] == 1
    assert summary["last_successful_request"] == pd.Timestamp("2026-08-02T10:00:00+00:00")


def test_requests_over_time_buckets_by_hour():
    df = events_to_df(ROWS)
    ts = requests_over_time(df, freq="h")
    assert list(ts["total"]) == [2, 2]
    assert list(ts["blocked"]) == [1, 1]


def test_blocked_reason_breakdown():
    df = events_to_df(ROWS)
    breakdown = blocked_reason_breakdown(df)
    assert breakdown["regex"] == 2


def test_blocked_reason_breakdown_no_blocks():
    rows = [{"timestamp": "2026-08-02T10:00:00+00:00", "blocked": False, "blocked_reason": "", "latency_ms": 5.0}]
    breakdown = blocked_reason_breakdown(events_to_df(rows))
    assert breakdown.empty
