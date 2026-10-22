"""
Macro Dashboard — landing page.

Run locally with:
    python -m streamlit run Home.py

This is a multi-page Streamlit app: each indicator lives on its own page
under pages/, reading through its own module in src/modules/. This page is
a cross-indicator summary + entry point.
"""

import pandas as pd
import streamlit as st

from src.core import charts
from src.core.transforms import change_over, last_complete_row, last_valid
from src.modules.ism_manufacturing import config as ism_cfg
from src.modules.ism_manufacturing.calculations import classify, load_ism_history
from src.modules.treasury_yields import config as yields_cfg
from src.modules.treasury_yields.calculations import load_history

st.set_page_config(page_title="Macro Dashboard", layout="wide")
st.title("Macro Dashboard")
st.caption("US Treasury yields + ISM Manufacturing Index — more indicators to come.")

yields_df = load_history()
ism_df = load_ism_history()

# Each figure comes from its series' last populated row, never a blank tail.
ten_date, ten_yield = last_valid(yields_df, "10yr")
curve_row = yields_df.iloc[last_complete_row(yields_df, ["2yr", "10yr"])]
pmi_date, pmi = last_valid(ism_df, "PMI")

col1, col2, col3 = st.columns(3)
col1.metric(
    "10yr Treasury Yield",
    f"{ten_yield:.2f}%",
    f"{change_over(yields_df, '10yr', pd.Timedelta(days=7)):+.2f} pp WoW",
)
col1.caption(f"As of {ten_date:%Y-%m-%d}")
spread_2s10s = curve_row["10yr"] - curve_row["2yr"]
col2.metric("2s10s Spread", f"{spread_2s10s:+.2f} pp")
col2.caption(f"As of {curve_row['Date']:%Y-%m-%d}")
col3.metric("ISM Manufacturing PMI", f"{pmi:.1f}", classify(pmi))
col3.caption(f"As of {pmi_date:%B %Y}")

st.divider()
st.subheader("Leading indicator check: ISM PMI vs. 10yr Treasury yield")
st.caption(
    "ISM PMI is a leading indicator of economic activity; checking it against yields "
    "before acting on either one alone is standard practice."
)

yields_monthly = yields_df[["Date", "10yr"]].dropna().copy()
yields_monthly["Month"] = yields_monthly["Date"].values.astype("datetime64[M]")
yields_monthly = yields_monthly.groupby("Month", as_index=False).last()[
    ["Month", "10yr"]
]

ism_monthly = ism_df[["Date", "PMI"]].dropna().rename(columns={"Date": "Month"})

merged = pd.merge(ism_monthly, yields_monthly, on="Month", how="inner").rename(
    columns={"Month": "Date"}
)

if merged.empty:
    st.info("No overlapping monthly dates between the ISM and yields series yet.")
else:
    fig = charts.dual_axis_chart(
        merged["Date"],
        merged["PMI"],
        "ISM PMI",
        "ISM PMI",
        merged["10yr"],
        "10yr Yield %",
        "10yr Yield %",
        height=420,
        hline_left=50,
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.markdown("**Pages:** use the sidebar to open Treasury Yields or ISM Manufacturing.")
st.caption(f"Sources: {yields_cfg.SOURCE}; {ism_cfg.SOURCE}")
