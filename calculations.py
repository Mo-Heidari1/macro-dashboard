"""
Benchmark Yields US — calculation layer.

Replicates the logic from Benchmark_Yields_US-updated.xlsm:
- Summary: current yield + WoW/MoM/QoQ/YoY change per tenor
- Curve Analysis: yield curve (yield vs. maturity) on a given date
- Spread Analysis: spread between two selected tenors over time
- Implied inflation (breakeven): nominal yield minus matching TIPS yield

Data cadence: WEEKLY snapshots (one row per week), consistent with the
source workbook. WoW/MoM/QoQ/YoY are therefore offsets of 1/4/13/52 rows,
not calendar days.
"""

import os
import pandas as pd

TENOR_COLS = [
    "Fed Funds", "1mo", "3mo", "6mo", "1yr", "2yr", "3yr", "5yr", "7yr",
    "10yr", "20yr", "30yr", "5yr TIPS", "7yr TIPS", "10yr TIPS",
    "20yr TIPS", "30yr TIPS",
]

NOMINAL_TENORS = ["1mo", "3mo", "6mo", "1yr", "2yr", "3yr", "5yr", "7yr",
                   "10yr", "20yr", "30yr"]
TIPS_TENORS = ["5yr TIPS", "7yr TIPS", "10yr TIPS", "20yr TIPS", "30yr TIPS"]

# Maturity (in years) used for x-axis positioning on the curve chart
MATURITY_YEARS = {
    "1mo": 1/12, "3mo": 3/12, "6mo": 6/12, "1yr": 1, "2yr": 2, "3yr": 3,
    "5yr": 5, "7yr": 7, "10yr": 10, "20yr": 20, "30yr": 30,
    "5yr TIPS": 5, "7yr TIPS": 7, "10yr TIPS": 10, "20yr TIPS": 20,
    "30yr TIPS": 30,
}

# Row offsets matching the workbook's HLOOKUP column indices (weekly data)
OFFSET_WOW = 1
OFFSET_MOM = 4
OFFSET_QOQ = 13
OFFSET_YOY = 52


def load_history(path=None) -> pd.DataFrame:
    """Load the historical weekly yield series, sorted ascending by date."""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yields_history.csv")
    df = pd.read_csv(path, parse_dates=["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Replicates the 'Summary' sheet: current yield and WoW/MoM/QoQ/YoY
    change (in percentage points) for every tenor.
    """
    latest = df.iloc[-1]
    out = []
    for tenor in TENOR_COLS:
        cur = latest[tenor]

        def chg(offset):
            if len(df) <= offset:
                return None
            prior = df.iloc[-1 - offset][tenor]
            if pd.isna(cur) or pd.isna(prior):
                return None
            return round(cur - prior, 4)

        out.append({
            "Tenor": tenor,
            "Current Yield %": cur,
            "WoW": chg(OFFSET_WOW),
            "MoM": chg(OFFSET_MOM),
            "QoQ": chg(OFFSET_QOQ),
            "YoY": chg(OFFSET_YOY),
        })
    return pd.DataFrame(out)


def implied_inflation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Breakeven inflation = nominal yield - matching-maturity TIPS yield,
    for the tenors where both exist (5/7/10/20yr).

    TIPS data on Treasury.gov sometimes posts a day or more behind nominal
    yields, so the very latest row may have nominal but not-yet-published
    TIPS values. To avoid returning an empty table, this walks backward
    from the latest row until it finds one with at least one complete
    nominal/TIPS pair.
    """
    pairs = [("5yr", "5yr TIPS"), ("7yr", "7yr TIPS"),
              ("10yr", "10yr TIPS"), ("20yr", "20yr TIPS")]

    for i in range(len(df) - 1, -1, -1):
        row = df.iloc[i]
        out = []
        for nom, tips in pairs:
            if pd.notna(row[nom]) and pd.notna(row[tips]):
                out.append({
                    "Maturity": nom,
                    "Nominal": row[nom],
                    "TIPS": row[tips],
                    "Implied Inflation": round(row[nom] - row[tips], 4),
                })
        if out:
            return pd.DataFrame(out)

    # No row anywhere has a complete nominal/TIPS pair
    return pd.DataFrame(columns=["Maturity", "Nominal", "TIPS", "Implied Inflation"])


def curve_on_date(df: pd.DataFrame, date=None, tenors=None) -> pd.DataFrame:
    """
    Yield curve snapshot: yield vs. maturity (years) for a given date
    (defaults to latest). Used to feed the Curve Analysis chart.
    """
    tenors = tenors or NOMINAL_TENORS
    row = df.iloc[-1] if date is None else df.loc[df["Date"] == pd.Timestamp(date)].iloc[0]
    out = pd.DataFrame({
        "Tenor": tenors,
        "Maturity (yrs)": [MATURITY_YEARS[t] for t in tenors],
        "Yield %": [row[t] for t in tenors],
    }).dropna(subset=["Yield %"])
    return out.sort_values("Maturity (yrs)")


def spread_series(df: pd.DataFrame, tenor_a: str, tenor_b: str) -> pd.DataFrame:
    """
    Time series of (tenor_a - tenor_b), e.g. '10yr' vs '1yr' for the
    classic recession-signal spread. Mirrors the Spread Analysis sheet's
    dropdown-driven comparison.
    """
    out = df[["Date", tenor_a, tenor_b]].dropna().copy()
    out["Spread"] = out[tenor_a] - out[tenor_b]
    out = out.rename(columns={tenor_a: f"{tenor_a} Yield", tenor_b: f"{tenor_b} Yield"})
    return out
