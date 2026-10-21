"""
Macro Dashboard — landing page.

Run locally with:
    streamlit run Home.py

This is a multi-page Streamlit app: each indicator lives on its own page
under pages/, all reading through their own calculation module
(calculations.py for yields, ism_calculations.py for ISM). This page is
just a cross-indicator summary + entry point.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from calculations import load_history
from ism_calculations import load_ism_history, classify

st.set_page_config(page_title="Macro Dashboard", layout="wide")
st.title("Macro Dashboard")
st.caption("US Treasury yields + ISM Manufacturing Index — more indicators to come.")

yields_df = load_history()
ism_df = load_ism_history()

col1, col2, col3 = st.columns(3)
col1.metric("10yr Treasury Yield", f"{yields_df.iloc[-1]['10yr']:.2f}%",
            f"{yields_df.iloc[-1]['10yr'] - yields_df.iloc[-2]['10yr']:+.2f} pp WoW")
spread_2s10s = yields_df.iloc[-1]["10yr"] - yields_df.iloc[-1]["2yr"]
col2.metric("2s10s Spread", f"{spread_2s10s:+.2f} pp")
col3.metric("ISM Manufacturing PMI", f"{ism_df.iloc[-1]['PMI']:.1f}", classify(ism_df.iloc[-1]["PMI"]))

st.divider()
st.subheader("Leading indicator check: ISM PMI vs. 10yr Treasury yield")
st.caption(
    "ISM PMI is a leading indicator of economic activity; checking it against yields "
    "before acting on either one alone is standard practice."
)

yields_monthly = yields_df[["Date", "10yr"]].dropna().copy()
yields_monthly["Month"] = yields_monthly["Date"].values.astype("datetime64[M]")
yields_monthly = yields_monthly.groupby("Month", as_index=False).last()[["Month", "10yr"]]

ism_monthly = ism_df[["Date", "PMI"]].dropna().rename(columns={"Date": "Month"})

merged = pd.merge(ism_monthly, yields_monthly, on="Month", how="inner").rename(columns={"Month": "Date"})

if merged.empty:
    st.info("No overlapping monthly dates between the ISM and yields series yet.")
else:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=merged["Date"], y=merged["PMI"], name="ISM PMI", yaxis="y1"))
    fig.add_trace(go.Scatter(x=merged["Date"], y=merged["10yr"], name="10yr Yield %", yaxis="y2"))
    fig.add_hline(y=50, line_dash="dash", line_color="gray", yref="y1")
    fig.update_layout(
        height=420, margin=dict(t=20),
        yaxis=dict(title="ISM PMI"),
        yaxis2=dict(title="10yr Yield %", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.markdown("**Pages:** use the sidebar to open Treasury Yields or ISM Manufacturing.")
