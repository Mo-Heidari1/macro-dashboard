"""
Refresh the Treasury yields history with the latest public data.

Usage:
    python scripts/update_yields.py YOUR_FRED_API_KEY

Get a free FRED API key at: https://fred.stlouisfed.org/docs/api/api_key.html

What it does:
1. Pulls the current year's nominal and TIPS (real) par yield curves from Treasury.gov
2. Pulls the effective Fed Funds rate (EFFR) from FRED
3. Merges them and appends any new dates onto data/sample/yields_history.csv
   (or data/local/ if a local copy exists), deduping on Date
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import paths
from src.core.loaders import fetch_fred_series, fetch_treasury_curve
from src.modules.treasury_yields import config as cfg


def build_latest_snapshot(year: int, fred_api_key: str) -> pd.DataFrame:
    """
    Combine nominal + TIPS + Fed Funds into one row-per-date DataFrame,
    matching the shape of the yields history. Merges on Date (outer join,
    since Fed Funds/Treasury.gov updates don't always land on the exact
    same calendar day).
    """
    nom = fetch_treasury_curve(year, cfg.NOMINAL_COL_MAP)
    tips = fetch_treasury_curve(year, cfg.TIPS_COL_MAP, real=True)
    ff = fetch_fred_series(
        cfg.FED_FUNDS_SERIES,
        fred_api_key,
        start_date=f"{year}-01-01",
        value_name="Fed Funds",
    )

    merged = nom.merge(tips, on="Date", how="outer").merge(ff, on="Date", how="outer")
    merged = merged.sort_values("Date").reset_index(drop=True)
    return merged


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/update_yields.py YOUR_FRED_API_KEY")
        sys.exit(1)

    fred_api_key = sys.argv[1]
    year = pd.Timestamp.today().year
    csv_path, _ = paths.resolve_data_file(cfg.HISTORY_FILE)

    print(f"Fetching {year} data from Treasury.gov and FRED...")
    fresh = build_latest_snapshot(year, fred_api_key)
    print(
        f"Got {len(fresh)} rows from live sources, latest date: {fresh['Date'].max()}"
    )

    history = pd.read_csv(csv_path, parse_dates=["Date"])
    print(
        f"Existing history: {len(history)} rows, latest date: {history['Date'].max()}"
    )

    combined = pd.concat([history, fresh], ignore_index=True)
    combined = combined.drop_duplicates(subset="Date", keep="last")
    combined = combined.sort_values("Date").reset_index(drop=True)
    combined.to_csv(csv_path, index=False)

    added = len(combined) - len(history)
    print(
        f"Done. Added {added} new row(s). History now has {len(combined)} rows "
        f"through {combined['Date'].max().strftime('%Y-%m-%d')}."
    )
    print("Restart (or refresh) your Streamlit app to see the new data.")


if __name__ == "__main__":
    main()
