"""
Backfill or correct yield columns in the history from Treasury.gov.

    python scripts/backfill_treasury.py --columns tips --start 2026-01-01 --mode fill
    python scripts/backfill_treasury.py --columns 3mo --start 2024-01-01 \
        --end 2025-12-31 --mode overwrite --weekend-only

--mode fill       only fills cells that are currently empty
--mode overwrite  replaces existing values with Treasury.gov's
--weekend-only    restrict to the Sunday-dated weekly rows

Rows are matched with align_to_history(): weekday rows use that day's
Treasury.gov observation; Sunday weekly rows use the prior Friday's close.
Only existing rows are touched; no dates are added. Prints every change
count by column before saving.
"""

import argparse
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import paths
from src.core.loaders import fetch_treasury_curve
from src.modules.treasury_yields import config as cfg
from src.modules.treasury_yields.calculations import align_to_history, backfill_columns

COLUMN_GROUPS = {
    "tips": list(cfg.TIPS_COL_MAP.values()),
    "nominal": list(cfg.NOMINAL_COL_MAP.values()),
}
REQUEST_PAUSE_SECONDS = 2


def fetch_years(years: range, columns: list[str]) -> pd.DataFrame:
    """Treasury.gov observations for `columns` across `years` (throttled)."""
    frames = []
    for real, col_map in ((False, cfg.NOMINAL_COL_MAP), (True, cfg.TIPS_COL_MAP)):
        wanted = {k: v for k, v in col_map.items() if v in columns}
        if not wanted:
            continue
        per_year = []
        for year in years:
            per_year.append(fetch_treasury_curve(year, wanted, real=real))
            time.sleep(REQUEST_PAUSE_SECONDS)
        frames.append(pd.concat(per_year, ignore_index=True))
    live = frames[0]
    for f in frames[1:]:
        live = live.merge(f, on="Date", how="outer")
    return live.drop_duplicates("Date").sort_values("Date")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--columns",
        required=True,
        help="tips, nominal, or tenor names, comma-separated",
    )
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", default=None)
    parser.add_argument("--mode", choices=["fill", "overwrite"], default="fill")
    parser.add_argument("--weekend-only", action="store_true")
    args = parser.parse_args()

    columns = []
    for item in args.columns.split(","):
        columns += COLUMN_GROUPS.get(item.strip().lower(), [item.strip()])

    csv_path, _ = paths.resolve_data_file(cfg.HISTORY_FILE)
    history = (
        pd.read_csv(csv_path, parse_dates=["Date"])
        .sort_values("Date")
        .reset_index(drop=True)
    )
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end) if args.end else history["Date"].max()
    rows = history[(history["Date"] >= start) & (history["Date"] <= end)]
    if args.weekend_only:
        rows = rows[rows["Date"].dt.dayofweek >= 5]

    # Start a week early so a Sunday on Jan 1-3 can use the prior year's close.
    first_year = (start - pd.Timedelta(days=7)).year
    live = fetch_years(range(first_year, end.year + 1), columns)
    aligned = align_to_history(rows["Date"], live)
    updated, changes = backfill_columns(history, aligned, columns, args.mode)

    for col, n in changes.items():
        print(
            f"{col:<12}{n:>6} cell(s) {'filled' if args.mode == 'fill' else 'overwritten'}"
        )
    updated.to_csv(csv_path, index=False)
    print(f"Saved {csv_path}")


if __name__ == "__main__":
    main()
