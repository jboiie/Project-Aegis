"""
Streamlit Dashboard — Real-time telemetry visualization.

Connects to Supabase to display:
  - Attacks blocked vs. allowed (live counter)
  - Attack success rate over time
  - Latency distribution
  - Guardrail check breakdown
  - Recent attack log

Run with:
    streamlit run dashboard/app.py
"""

import os

import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

from data import (
    get_client,
    fetch_events,
    events_to_df,
    compute_summary,
    requests_over_time,
    blocked_reason_breakdown,
)

load_dotenv()

st.set_page_config(
    page_title="Aegis Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")


@st.cache_resource
def _client():
    return get_client(SUPABASE_URL, SUPABASE_KEY)


@st.cache_data(ttl=30)
def _load_df(limit: int = 500):
    rows = fetch_events(_client(), limit=limit)
    return events_to_df(rows)


def main():
    st.title("🛡️ Project Aegis — Security Dashboard")
    st.markdown("Real-time telemetry from the LLM security proxy.")

    configured = bool(SUPABASE_URL) and bool(SUPABASE_KEY) and "your-project" not in SUPABASE_URL
    if not configured:
        st.warning("SUPABASE_URL / SUPABASE_KEY not configured — set them in .env.")
        return

    df = _load_df()
    if df.empty:
        st.info("No events logged yet. Fire some requests at the sandbox.")
        return

    summary = compute_summary(df)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Requests", summary["total"])
    with col2:
        st.metric("Blocked", summary["blocked"])
    with col3:
        st.metric("Block Rate", f"{summary['block_rate_pct']:.2f}%")
    with col4:
        st.metric("Avg Latency", f"{summary['avg_latency_ms']:.1f} ms")

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("📊 Requests Over Time")
        ts = requests_over_time(df)
        st.line_chart(ts)

    with right:
        st.subheader("🔍 Blocked Reason Breakdown")
        breakdown = blocked_reason_breakdown(df)
        if breakdown.empty:
            st.info("No blocked requests yet.")
        else:
            fig = px.pie(values=breakdown.values, names=breakdown.index)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("📋 Recent Events")
    st.dataframe(
        df[["timestamp", "prompt_hash", "blocked", "blocked_reason", "latency_ms", "model"]]
    )


if __name__ == "__main__":
    main()
