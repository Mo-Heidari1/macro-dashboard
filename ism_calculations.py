"""
ISM Manufacturing Index — calculation layer.

Replicates the logic from ISM_Manufacturing_Index_Updated.xlsx:
- Summary: current value + MoM/YoY change per sub-index
- classify(): growth (>50) / contraction (<50) / neutral (=50) — the
  expansion/contraction convention that applies to every diffusion index
  in this workbook, not just the headline PMI.
- heatmap_data(): the Heat Map Summary sheet's shape (months x sub-indices),
  ready for a diverging-colorscale Plotly heatmap centered on 50.
- sector_rankings(): growth/contraction/score per industry for a given
  month and category, from the Sectors sheet.
- recompute_pmi_from_subindices(): reconstructs headline PMI from its five
  weighted components, as a validation + "how the composite works" check.

Data cadence: MONTHLY (one row per month) — unlike the weekly yields data,
there's no WoW/QoQ distinction here, so only MoM and YoY are computed.
"""

import os
import pandas as pd

# All 11 published series, headline first, in the same order as the
# workbook's Heat Map Summary sheet.
SUBINDEX_COLS = [
    "PMI", "New Orders", "Production", "Employment", "Deliveries",
    "Inventories", "Customer Inventories", "Prices", "Order Backlog",
    "Exports", "Imports",
]

# ISM's official headline PMI composite weights.
PMI_WEIGHTS = {
    "New Orders": 0.30,
    "Production": 0.25,
    "Employment": 0.20,
    "Deliveries": 0.15,
    "Inventories": 0.10,
}

OFFSET_MOM = 1
OFFSET_YOY = 12


def load_ism_history(path=None) -> pd.DataFrame:
    """Load the historical monthly ISM sub-index series, sorted ascending by date."""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ism_history.csv")
    df = pd.read_csv(path, parse_dates=["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def load_ism_sectors(path=None) -> pd.DataFrame:
    """Load the long-format sector growth/contraction data (Category, Date, Industry, Direction, Score)."""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ism_sectors.csv")
    return pd.read_csv(path, parse_dates=["Date"])


def classify(value) -> str:
    """50.0 is the expansion/contraction threshold for every diffusion index here."""
    if pd.isna(value):
        return "N/A"
    if value > 50:
        return "Growth"
    if value < 50:
        return "Contraction"
    return "Neutral"


def summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """Current value, classification, and MoM/YoY change for every sub-index."""
    latest = df.iloc[-1]
    out = []
    for col in SUBINDEX_COLS:
        cur = latest[col]

        def chg(offset):
            if len(df) <= offset:
                return None
            prior = df.iloc[-1 - offset][col]
            if pd.isna(cur) or pd.isna(prior):
                return None
            return round(cur - prior, 4)

        out.append({
            "Sub-Index": col,
            "Current": cur,
            "Status": classify(cur),
            "MoM": chg(OFFSET_MOM),
            "YoY": chg(OFFSET_YOY),
        })
    return pd.DataFrame(out)


def heatmap_data(df: pd.DataFrame, n_months: int = None) -> pd.DataFrame:
    """
    Months x sub-indices matrix (Date-indexed), matching the Heat Map
    Summary sheet's shape. Feed straight into a Plotly go.Heatmap with a
    diverging colorscale centered on 50. Pass n_months to limit to the
    most recent N months (default: all).
    """
    out = df.set_index("Date")[SUBINDEX_COLS]
    if n_months is not None:
        out = out.tail(n_months)
    return out


def sector_rankings(sectors_df: pd.DataFrame, date, category: str = "PMI") -> pd.DataFrame:
    """
    Growth/contraction/score per industry for a given month and category
    (headline 'PMI' or one of the sub-indices ISM publishes a breakdown
    for: New Orders, Production, Employment, Deliveries, Inventories,
    Customer Inventories). Sorted by Score descending (strongest growth first).
    """
    date = pd.Timestamp(date)
    out = sectors_df[(sectors_df["Date"] == date) & (sectors_df["Category"] == category)]
    return out[["Industry", "Direction", "Score"]].sort_values("Score", ascending=False).reset_index(drop=True)


def recompute_pmi_from_subindices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstructs headline PMI from its five weighted components
    (New Orders 30%, Production 25%, Employment 20%, Supplier Deliveries
    15%, Inventories 10%) and compares to the published headline PMI.

    This won't match exactly — ISM applies seasonal adjustment on top of
    the simple weighted sum — but it's close, and shows how the composite
    is built.
    """
    out = df[["Date", "PMI"]].copy()
    out["Recomputed PMI"] = sum(df[col] * w for col, w in PMI_WEIGHTS.items())
    out["Recomputed PMI"] = out["Recomputed PMI"].round(2)
    out["Diff"] = (out["PMI"] - out["Recomputed PMI"]).round(2)
    return out
