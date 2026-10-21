"""
US Treasury Benchmark Yields — Summary / Curve Analysis / Spread Analysis /
Implied Inflation. Unchanged from the original single-page app.py, just
moved onto its own page.
"""

import streamlit as st
import plotly.graph_objects as go

from calculations import (
    load_history, summary_table, implied_inflation, curve_on_date,
    spread_series, NOMINAL_TENORS, TENOR_COLS,
)

st.set_page_config(page_title="Treasury Yields — US", layout="wide")
st.title("US Treasury Benchmark Yields")

df = load_history()
latest_date = df["Date"].max()
st.caption(f"Data through {latest_date.strftime('%Y-%m-%d')} · weekly snapshots · "
           f"{len(df):,} observations since {df['Date'].min().strftime('%Y')}")

tab_summary, tab_curve, tab_spread, tab_inflation = st.tabs(
    ["Summary", "Curve Analysis", "Spread Analysis", "Implied Inflation"]
)

# ---------- Summary tab ----------
with tab_summary:
    st.subheader("Current yields and changes")
    s = summary_table(df)
    st.dataframe(
        s.style.format({
            "Current Yield %": "{:.2f}",
            "WoW": "{:+.2f}", "MoM": "{:+.2f}",
            "QoQ": "{:+.2f}", "YoY": "{:+.2f}",
        }).background_gradient(subset=["WoW", "MoM", "QoQ", "YoY"], cmap="RdYlGn", vmin=-0.5, vmax=0.5),
        use_container_width=True, hide_index=True,
    )

    st.subheader("History — pick a tenor")
    tenor_pick = st.selectbox("Tenor", TENOR_COLS, index=TENOR_COLS.index("10yr"))
    hist = df[["Date", tenor_pick]].dropna()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["Date"], y=hist[tenor_pick], mode="lines", name=tenor_pick))
    fig.update_layout(height=400, yaxis_title="Yield %", margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

# ---------- Curve Analysis tab ----------
with tab_curve:
    st.subheader("Yield curve comparison")
    available_dates = df["Date"].sort_values(ascending=False)
    default_dates = [available_dates.iloc[0], available_dates.iloc[13], available_dates.iloc[52]]
    picked = st.multiselect(
        "Compare snapshot dates", options=list(available_dates.dt.strftime("%Y-%m-%d")),
        default=[d.strftime("%Y-%m-%d") for d in default_dates],
    )
    fig = go.Figure()
    for d in picked:
        curve = curve_on_date(df, date=d)
        fig.add_trace(go.Scatter(x=curve["Maturity (yrs)"], y=curve["Yield %"],
                                  mode="lines+markers", name=d))
    fig.update_layout(height=450, xaxis_title="Maturity (years)", yaxis_title="Yield %",
                       xaxis_type="log", margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

# ---------- Spread Analysis tab ----------
with tab_spread:
    st.subheader("Spread between two tenors")
    col1, col2 = st.columns(2)
    tenor_a = col1.selectbox("Maturity A", TENOR_COLS, index=TENOR_COLS.index("10yr"))
    tenor_b = col2.selectbox("Maturity B", TENOR_COLS, index=TENOR_COLS.index("1yr"))
    sp = spread_series(df, tenor_a, tenor_b)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sp["Date"], y=sp["Spread"], mode="lines",
                              name=f"{tenor_a} - {tenor_b}"))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(height=400, yaxis_title="Spread (pp)",
                       title=f"{tenor_a} - {tenor_b} Spread", margin=dict(t=40))
    st.plotly_chart(fig, use_container_width=True)
    st.metric(f"Current {tenor_a} - {tenor_b} spread", f"{sp['Spread'].iloc[-1]:+.2f} pp")

# ---------- Implied Inflation tab ----------
with tab_inflation:
    st.subheader("Implied inflation (breakeven)")
    st.caption("Nominal yield minus matching-maturity TIPS yield")
    infl = implied_inflation(df)
    if infl.empty:
        st.warning("No dates in the current history have both nominal and TIPS yields available yet.")
    else:
        st.dataframe(infl.style.format({"Nominal": "{:.2f}", "TIPS": "{:.2f}",
                                         "Implied Inflation": "{:.2f}"}),
                     use_container_width=True, hide_index=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=infl["Maturity"], y=infl["Implied Inflation"]))
        fig.update_layout(height=350, yaxis_title="Implied Inflation %", margin=dict(t=20))
        st.plotly_chart(fig, use_container_width=True)
