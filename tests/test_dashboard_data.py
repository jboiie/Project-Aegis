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
    assert summary == {"total": 4, "blocked": 2, "block_rate_pct": 50.0, "avg_latency_ms": 9.0}


def test_compute_summary_empty():
    summary = compute_summary(events_to_df([]))
    assert summary == {"total": 0, "blocked": 0, "block_rate_pct": 0.0, "avg_latency_ms": 0.0}


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
