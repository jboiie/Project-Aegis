"""
Dashboard data layer — Supabase queries + pandas aggregation.

Split from app.py so the aggregation math (compute_summary,
requests_over_time, blocked_reason_breakdown) is unit-testable without a
live Supabase connection or Streamlit runtime. Only get_client/fetch_events
touch the network.

Note: aegis_events logs ALL traffic (attacks and benign mixed), not a
labeled red-team run, so "blocked / total" here is a live block rate, not
the Attack Success Rate reported in README Tables 1-4 (which comes from
redteam/evaluation/metrics.py against a known attack corpus).
"""

import pandas as pd
from supabase import create_client, Client


def get_client(url: str, key: str) -> Client:
    return create_client(url, key)


def fetch_events(client: Client, table: str = "aegis_events", limit: int = 500) -> list[dict]:
    resp = client.table(table).select("*").order("timestamp", desc=True).limit(limit).execute()
    return resp.data


def events_to_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def compute_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"total": 0, "blocked": 0, "block_rate_pct": 0.0, "avg_latency_ms": 0.0}
    total = len(df)
    blocked = int(df["blocked"].sum())
    return {
        "total": total,
        "blocked": blocked,
        "block_rate_pct": 100.0 * blocked / total,
        "avg_latency_ms": float(df["latency_ms"].mean()),
    }


def requests_over_time(df: pd.DataFrame, freq: str = "h") -> pd.DataFrame:
    """Bucket requests by time; returns columns [total, blocked] indexed by bucket start."""
    if df.empty:
        return pd.DataFrame(columns=["total", "blocked"])
    bucket = df.set_index("timestamp").sort_index()
    total = bucket["blocked"].resample(freq).count().rename("total")
    blocked = bucket["blocked"].resample(freq).sum().rename("blocked")
    return pd.concat([total, blocked], axis=1)


def blocked_reason_breakdown(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=int)
    blocked = df[df["blocked"] == True]  # noqa: E712 (pandas boolean mask, not identity check)
    if blocked.empty:
        return pd.Series(dtype=int)
    return blocked["blocked_reason"].value_counts()
