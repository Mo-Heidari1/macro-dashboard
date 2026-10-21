"""
US Treasury Benchmark Yields — Summary / Curve Analysis / Spread Analysis /
Implied Inflation.
"""

import streamlit as st

from src.core import charts
from src.core.transforms import last_complete_row
from src.modules.treasury_yields.calculations import (
    curve_on_date,
    implied_inflation,
    load_history,
    snapshot_dates,
    spread_series,
    summary_table,
)
from src.modules.treasury_yields.config import (
    CURVE_SNAPSHOT_LOOKBACK_DAYS,
    NOMINAL_TENORS,
    SOURCE,
    TENOR_COLS,
)

st.set_page_config(page_title="Treasury Yields — US", layout="wide")
st.title("US Treasury Benchmark Yields")

df = load_history()
curve_i = last_complete_row(df, NOMINAL_TENORS)
curve_date = df["Date"].iloc[curve_i if curve_i is not None else -1]
st.caption(
    f"As of {curve_date:%Y-%m-%d} (latest full nominal curve) · weekly snapshots to 2025, "
    f"daily from 2026 · {len(df):,} observations since {df['Date'].min().strftime('%Y')} · "
    "changes are measured over calendar windows (WoW 7, MoM 28, QoQ 91, YoY 364 days)"
)
st.caption(f"Source: {SOURCE}")

tab_summary, tab_curve, tab_spread, tab_inflation = st.tabs(
    ["Summary", "Curve Analysis", "Spread Analysis", "Implied Inflation"]
)

# ---------- Summary tab ----------
with tab_summary:
    st.subheader("Current yields and changes")
    st.caption("Each tenor shows its own latest published value; see the As of column.")
    s = summary_table(df)
    st.dataframe(
        s.style.format(
            {
                "Current Yield %": "{:.2f}",
                "WoW": "{:+.2f}",
                "MoM": "{:+.2f}",
                "QoQ": "{:+.2f}",
                "YoY": "{:+.2f}",
            }
        ).background_gradient(
            subset=["WoW", "MoM", "QoQ", "YoY"], cmap="RdYlGn", vmin=-0.5, vmax=0.5
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("History — pick a tenor")
    tenor_pick = st.selectbox("Tenor", TENOR_COLS, index=TENOR_COLS.index("10yr"))
    hist = df[["Date", tenor_pick]].dropna()
    fig = charts.line_chart(
        hist["Date"], hist[tenor_pick], tenor_pick, height=400, yaxis_title="Yield %"
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------- Curve Analysis tab ----------
with tab_curve:
    st.subheader("Yield curve comparison")
    available_dates = df["Date"].sort_values(ascending=False)
    default_dates = snapshot_dates(df, CURVE_SNAPSHOT_LOOKBACK_DAYS)
    picked = st.multiselect(
        "Compare snapshot dates",
        options=list(available_dates.dt.strftime("%Y-%m-%d")),
        default=[d.strftime("%Y-%m-%d") for d in default_dates],
    )
    traces = []
    for d in picked:
        curve = curve_on_date(df, date=d)
        traces.append(
            {
                "x": curve["Maturity (yrs)"],
                "y": curve["Yield %"],
                "name": d,
                "mode": "lines+markers",
            }
        )
    fig = charts.multi_line_chart(
        traces,
        height=450,
        xaxis_title="Maturity (years)",
        yaxis_title="Yield %",
        xaxis_type="log",
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------- Spread Analysis tab ----------
with tab_spread:
    st.subheader("Spread between two tenors")
    col1, col2 = st.columns(2)
    tenor_a = col1.selectbox("Maturity A", TENOR_COLS, index=TENOR_COLS.index("10yr"))
    tenor_b = col2.selectbox("Maturity B", TENOR_COLS, index=TENOR_COLS.index("1yr"))
    sp = spread_series(df, tenor_a, tenor_b)
    fig = charts.line_chart(
        sp["Date"],
        sp["Spread"],
        f"{tenor_a} - {tenor_b}",
        height=400,
        yaxis_title="Spread (pp)",
        hline=0,
        title=f"{tenor_a} - {tenor_b} Spread",
        margin_top=40,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.metric(
        f"Current {tenor_a} - {tenor_b} spread", f"{sp['Spread'].iloc[-1]:+.2f} pp"
    )
    st.caption(f"As of {sp['Date'].iloc[-1]:%Y-%m-%d}")

# ---------- Implied Inflation tab ----------
with tab_inflation:
    st.subheader("Implied inflation (breakeven)")
    st.caption("Nominal yield minus matching-maturity TIPS yield")
    infl = implied_inflation(df)
    if infl.empty:
        st.warning(
            "No dates in the current history have both nominal and TIPS yields available yet."
        )
    else:
        st.caption(f"As of {infl['As of'].iloc[0]}")
        st.dataframe(
            infl.style.format(
                {"Nominal": "{:.2f}", "TIPS": "{:.2f}", "Implied Inflation": "{:.2f}"}
            ),
            use_container_width=True,
            hide_index=True,
        )
        fig = charts.bar_chart(
            infl["Maturity"],
            infl["Implied Inflation"],
            height=350,
            yaxis_title="Implied Inflation %",
        )
        st.plotly_chart(fig, use_container_width=True)
