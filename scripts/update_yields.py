"""
Refresh the Treasury yields history with the latest public data.

Usage:
    python scripts/update_yields.py

Needs a free FRED API key (https://fred.stlouisfed.org/docs/api/api_key.html)
in the FRED_API_KEY environment variable or in .streamlit/secrets.toml as
FRED_API_KEY = "...". Keys are never accepted on the command line, where
they would end up in shell history.

What it does:
1. Pulls the current year's nominal and TIPS (real) par yield curves from Treasury.gov
2. Pulls the effective Fed Funds rate (EFFR) from FRED
3. Merges them and appends any new dates onto data/yields/yields_history.csv
   (or data/local/ if a local copy exists), deduping on Date
"""

import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import paths
from src.core.credentials import MissingSecretError, get_secret
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """No positional arguments: an API key passed here is rejected."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    return parser.parse_args(argv)


def main():
    parse_args()
    try:
        fred_api_key = get_secret("FRED_API_KEY")
    except MissingSecretError as exc:
        print(exc)
        sys.exit(1)
    year = pd.Timestamp.today().year
    csv_path, _ = paths.resolve_data_file(
        cfg.HISTORY_FILE, paths.dataset_dir(cfg.DATA_FOLDER)
    )

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
