"""
ISM Manufacturing Index — headline PMI trend, sub-index heatmap, sub-index
trend selector, sector growth/contraction table, composite sanity-check,
and a monthly manual-update form.

Data: ISM Manufacturing Report On Business, compiled from public monthly
releases (committed in data/sample/; attribution shown on the page).
"""

import pandas as pd
import streamlit as st

from src.core import charts, paths
from src.core.signals import format_zscore
from src.core.transforms import last_complete_row, last_valid
from src.modules.ism_manufacturing import config as cfg
from src.modules.ism_manufacturing.calculations import (
    classify,
    get_signal,
    heatmap_data,
    load_ism_history,
    load_ism_sectors,
    recompute_pmi_from_subindices,
    sector_rankings,
    summary_table,
)

SUBINDEX_COLS = cfg.SUBINDEX_COLS

st.set_page_config(page_title="ISM Manufacturing — Macro Dashboard", layout="wide")
st.title("ISM Manufacturing Index")

df = load_ism_history()
sectors = load_ism_sectors()
latest_date = df["Date"].max()
pmi_date, latest_pmi = last_valid(df, "PMI")
complete_i = last_complete_row(df, SUBINDEX_COLS)
complete_date = df["Date"].iloc[complete_i] if complete_i is not None else pmi_date
st.caption(
    f"As of {complete_date:%B %Y} (latest month with all {len(SUBINDEX_COLS)} series) · "
    f"monthly · {len(df):,} observations since {df['Date'].min():%Y}"
)
st.caption(f"Source: {cfg.SOURCE}")

col1, col2 = st.columns([1, 3])
col1.metric("Headline PMI", f"{latest_pmi:.1f}", classify(latest_pmi))
col1.caption(f"As of {pmi_date:%B %Y}")
sig = get_signal(df)
s1, s2, s3 = col2.columns(3)
s1.metric("Regime", sig["regime"])
s2.metric("Momentum (3m vs prior 3m)", sig["direction"])
s3.metric("Z-score vs 10y", format_zscore(sig["zscore"]))
col2.caption(
    sig["market_read"]
    + (" Extreme reading (above 55 or below 45)." if sig["extreme"] else "")
)

tab_overview, tab_heatmap, tab_sectors, tab_composite, tab_update = st.tabs(
    [
        "Overview",
        "Sub-Index Heatmap",
        "Sector Breakdown",
        "Composite Check",
        "Add This Month's Data",
    ]
)

# ---------- Overview tab ----------
with tab_overview:
    st.subheader("Current sub-index values and changes")
    s = summary_table(df)

    def highlight_status(val):
        color = {
            "Growth": "#c6efce",
            "Contraction": "#ffc7ce",
            "Neutral": "#fff2cc",
        }.get(val, "")
        return f"background-color: {color}" if color else ""

    st.dataframe(
        s.style.format({"Current": "{:.1f}", "MoM": "{:+.1f}", "YoY": "{:+.1f}"}).map(
            highlight_status, subset=["Status"]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("History — pick a sub-index")
    sub_pick = st.selectbox("Sub-Index", SUBINDEX_COLS, index=0)
    hist = df[["Date", sub_pick]].dropna()
    fig = charts.line_chart(
        hist["Date"],
        hist[sub_pick],
        sub_pick,
        height=400,
        yaxis_title=sub_pick,
        hline=cfg.EXPANSION_THRESHOLD,
        hline_annotation="50 = expansion/contraction line",
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------- Sub-Index Heatmap tab ----------
with tab_heatmap:
    st.subheader("Sub-index heatmap")
    n_months = st.slider(
        "Months to show", min_value=12, max_value=min(120, len(df)), value=36, step=12
    )
    hm = heatmap_data(df, n_months)
    fig = charts.heatmap_chart(
        hm.T.values,
        hm.index.strftime("%Y-%m"),
        hm.columns,
        zmid=cfg.EXPANSION_THRESHOLD,
        colorbar_title="Index",
        hovertemplate="%{y} — %{x}: %{z:.1f}<extra></extra>",
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------- Sector Breakdown tab ----------
with tab_sectors:
    st.subheader("Industry growth/contraction by category")
    available_months = sorted(sectors["Date"].unique(), reverse=True)
    st.caption(
        f"As of {pd.Timestamp(available_months[0]):%B %Y} (latest month with sector data)"
    )
    available_categories = sorted(sectors["Category"].unique())
    col_a, col_b = st.columns(2)
    month_pick = col_a.selectbox(
        "Month",
        available_months,
        format_func=lambda d: pd.Timestamp(d).strftime("%B %Y"),
    )
    category_pick = col_b.selectbox(
        "Category",
        available_categories,
        index=available_categories.index("PMI") if "PMI" in available_categories else 0,
    )
    ranked = sector_rankings(sectors, month_pick, category_pick)
    if ranked.empty:
        st.info("No sector data for this month/category combination.")
    else:
        st.dataframe(
            ranked.style.map(highlight_status, subset=["Direction"]),
            use_container_width=True,
            hide_index=True,
        )

# ---------- Composite Check tab ----------
with tab_composite:
    st.subheader("Reconstructing the headline PMI from its components")
    st.caption(
        "ISM's official composite: New Orders 30% + Production 25% + Employment 20% "
        "+ Supplier Deliveries 15% + Inventories 10%. The recomputed value won't match "
        "exactly — ISM applies seasonal adjustment on top of this simple weighted sum — "
        "but it should track closely, which is the point: it shows how the index is built."
    )
    recomp = recompute_pmi_from_subindices(df).tail(24)
    fig = charts.multi_line_chart(
        [
            {"x": recomp["Date"], "y": recomp["PMI"], "name": "Published PMI"},
            {
                "x": recomp["Date"],
                "y": recomp["Recomputed PMI"],
                "name": "Recomputed PMI",
                "dash": "dot",
            },
        ],
        height=400,
        yaxis_title="Index",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        recomp.style.format(
            {"PMI": "{:.1f}", "Recomputed PMI": "{:.1f}", "Diff": "{:+.1f}"}
        ),
        use_container_width=True,
        hide_index=True,
    )

# ---------- Add This Month's Data tab ----------
with tab_update:
    st.subheader("Add this month's ISM report")
    st.caption(
        "ISM publishes no free data API. Type in the figures from the monthly "
        "Report On Business on ismworld.org; they are saved to the committed "
        "data file (data/sample/ism_history.csv), so commit it to publish them."
    )
    with st.form("ism_update_form"):
        next_month = (latest_date + pd.DateOffset(months=1)).replace(day=1)
        report_date = st.date_input("Report month", value=next_month)
        cols = st.columns(3)
        inputs = {}
        for i, sub in enumerate(SUBINDEX_COLS):
            inputs[sub] = cols[i % 3].number_input(
                sub,
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                value=None,
                format="%.1f",
            )
        submitted = st.form_submit_button("Save this month")

    if submitted:
        date = pd.Timestamp(report_date).replace(day=1)
        new_row = {"Date": date, **inputs}
        history = df[df["Date"] != date]
        history = pd.concat([history, pd.DataFrame([new_row])], ignore_index=True)
        history = history.sort_values("Date").reset_index(drop=True)
        history.to_csv(paths.sample_path(cfg.HISTORY_FILE), index=False)
        st.success(
            f"Saved {date.strftime('%B %Y')}. Refresh the page to see it reflected everywhere."
        )
