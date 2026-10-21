"""
ISM Manufacturing Index — headline PMI trend, sub-index heatmap, sub-index
trend selector, sector growth/contraction table, composite sanity-check,
and a monthly manual-update form.

There is no free API for ISM's data (it's a proprietary, licensed report),
so this page includes a form for typing in each month's published numbers
by hand — same as the source Excel workbook required, just faster.
"""

import os

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from ism_calculations import (
    load_ism_history, load_ism_sectors, summary_table, heatmap_data,
    classify, sector_rankings, recompute_pmi_from_subindices, SUBINDEX_COLS,
)

st.set_page_config(page_title="ISM Manufacturing — Macro Dashboard", layout="wide")
st.title("ISM Manufacturing Index")

df = load_ism_history()
sectors = load_ism_sectors()
latest_date = df["Date"].max()
latest_pmi = df.iloc[-1]["PMI"]
st.caption(f"Data through {latest_date.strftime('%B %Y')} · monthly · "
           f"{len(df):,} observations since {df['Date'].min().strftime('%Y')}")

col1, col2 = st.columns([1, 3])
col1.metric("Headline PMI", f"{latest_pmi:.1f}", classify(latest_pmi))

tab_overview, tab_heatmap, tab_sectors, tab_composite, tab_update = st.tabs(
    ["Overview", "Sub-Index Heatmap", "Sector Breakdown", "Composite Check", "Add This Month's Data"]
)

# ---------- Overview tab ----------
with tab_overview:
    st.subheader("Current sub-index values and changes")
    s = summary_table(df)

    def highlight_status(val):
        color = {"Growth": "#c6efce", "Contraction": "#ffc7ce", "Neutral": "#fff2cc"}.get(val, "")
        return f"background-color: {color}" if color else ""

    st.dataframe(
        s.style.format({"Current": "{:.1f}", "MoM": "{:+.1f}", "YoY": "{:+.1f}"})
         .map(highlight_status, subset=["Status"]),
        use_container_width=True, hide_index=True,
    )

    st.subheader("History — pick a sub-index")
    sub_pick = st.selectbox("Sub-Index", SUBINDEX_COLS, index=0)
    hist = df[["Date", sub_pick]].dropna()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["Date"], y=hist[sub_pick], mode="lines", name=sub_pick))
    fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="50 = expansion/contraction line")
    fig.update_layout(height=400, yaxis_title=sub_pick, margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

# ---------- Sub-Index Heatmap tab ----------
with tab_heatmap:
    st.subheader("Sub-index heatmap")
    n_months = st.slider("Months to show", min_value=12, max_value=min(120, len(df)), value=36, step=12)
    hm = heatmap_data(df, n_months)
    fig = go.Figure(data=go.Heatmap(
        z=hm.T.values,
        x=hm.index.strftime("%Y-%m"),
        y=hm.columns,
        colorscale="RdYlGn",
        zmid=50,
        colorbar=dict(title="Index"),
        hovertemplate="%{y} — %{x}: %{z:.1f}<extra></extra>",
    ))
    fig.update_layout(height=500, margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

# ---------- Sector Breakdown tab ----------
with tab_sectors:
    st.subheader("Industry growth/contraction by category")
    available_months = sorted(sectors["Date"].unique(), reverse=True)
    available_categories = sorted(sectors["Category"].unique())
    col_a, col_b = st.columns(2)
    month_pick = col_a.selectbox(
        "Month", available_months,
        format_func=lambda d: pd.Timestamp(d).strftime("%B %Y"),
    )
    category_pick = col_b.selectbox("Category", available_categories,
                                     index=available_categories.index("PMI") if "PMI" in available_categories else 0)
    ranked = sector_rankings(sectors, month_pick, category_pick)
    if ranked.empty:
        st.info("No sector data for this month/category combination.")
    else:
        st.dataframe(
            ranked.style.map(highlight_status, subset=["Direction"]),
            use_container_width=True, hide_index=True,
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
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=recomp["Date"], y=recomp["PMI"], mode="lines", name="Published PMI"))
    fig.add_trace(go.Scatter(x=recomp["Date"], y=recomp["Recomputed PMI"], mode="lines",
                              name="Recomputed PMI", line=dict(dash="dot")))
    fig.update_layout(height=400, yaxis_title="Index", margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        recomp.style.format({"PMI": "{:.1f}", "Recomputed PMI": "{:.1f}", "Diff": "{:+.1f}"}),
        use_container_width=True, hide_index=True,
    )

# ---------- Add This Month's Data tab ----------
with tab_update:
    st.subheader("Add this month's ISM report")
    st.caption(
        "No free API exists for ISM's data — it's a proprietary, licensed report. "
        "Type in the numbers from ismworld.org's monthly Report on Business, same as "
        "you would in the source Excel workbook. This just makes it a form instead of "
        "a multi-sheet edit."
    )
    with st.form("ism_update_form"):
        next_month = (latest_date + pd.DateOffset(months=1)).replace(day=1)
        report_date = st.date_input("Report month", value=next_month)
        cols = st.columns(3)
        inputs = {}
        for i, sub in enumerate(SUBINDEX_COLS):
            inputs[sub] = cols[i % 3].number_input(sub, min_value=0.0, max_value=100.0, step=0.1, value=None,
                                                     format="%.1f")
        submitted = st.form_submit_button("Save this month")

    if submitted:
        date = pd.Timestamp(report_date).replace(day=1)
        new_row = {"Date": date, **inputs}
        history = df[df["Date"] != date]
        history = pd.concat([history, pd.DataFrame([new_row])], ignore_index=True)
        history = history.sort_values("Date").reset_index(drop=True)
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ism_history.csv")
        history.to_csv(csv_path, index=False)
        st.success(f"Saved {date.strftime('%B %Y')}. Refresh the page to see it reflected everywhere.")
