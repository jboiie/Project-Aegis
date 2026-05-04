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

import streamlit as st

st.set_page_config(
    page_title="Aegis Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    st.title("🛡️ Project Aegis — Security Dashboard")
    st.markdown("Real-time telemetry from the LLM security proxy.")

    # ── Metrics row ──────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Requests", "—", help="Total prompts processed")
    with col2:
        st.metric("Attacks Blocked", "—", delta_color="inverse")
    with col3:
        st.metric("Attack Success Rate", "—%")
    with col4:
        st.metric("Avg Latency", "— ms")

    st.divider()

    # ── Charts ───────────────────────────────────────────────
    left, right = st.columns(2)

    with left:
        st.subheader("📊 Attacks Over Time")
        st.info("Connect to Supabase to see live data.")
        # TODO: Query Supabase and plot time series
        # df = query_supabase("SELECT * FROM aegis_events ORDER BY timestamp DESC")
        # st.line_chart(df, x="timestamp", y="blocked")

    with right:
        st.subheader("🔍 Guardrail Check Breakdown")
        st.info("Shows which guardrails catch the most attacks.")
        # TODO: Pie chart of blocked_reason distribution

    st.divider()

    # ── Recent events table ──────────────────────────────────
    st.subheader("📋 Recent Events")
    st.info("Attack log will appear here once Supabase is connected.")
    # TODO: st.dataframe(df[["timestamp", "prompt_hash", "blocked", "blocked_reason", "latency_ms"]])


if __name__ == "__main__":
    main()
