"""
Run this once a month to add the latest ISM Manufacturing Report on
Business numbers to the dashboard.

There is no free, terms-compliant API for ISM's data (it's a proprietary,
licensed report) — you still have to type in the published numbers by
hand, same as the source Excel workbook required. This script just makes
that a 30-second CLI prompt instead of a multi-sheet Excel edit.

Get the numbers from ismworld.org's monthly Report on Business (headline
PMI + the 10 sub-indices).

Usage:
    python update_ism.py                    interactive prompts
    python update_ism.py --date 2026-07-01 --pmi 53.5 --new-orders 57.0 \\
        --production 53.0 --employment 50.0 --deliveries 56.0 \\
        --inventories 51.0 --customer-inventories 43.0 --prices 70.0 \\
        --order-backlog 51.0 --exports 49.0 --imports 53.0
"""

import argparse
import os
import sys
import pandas as pd

from ism_calculations import SUBINDEX_COLS

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ism_history.csv")

# CLI flag name -> ism_history.csv column name
ARG_TO_COL = {
    "pmi": "PMI",
    "new_orders": "New Orders",
    "production": "Production",
    "employment": "Employment",
    "deliveries": "Deliveries",
    "inventories": "Inventories",
    "customer_inventories": "Customer Inventories",
    "prices": "Prices",
    "order_backlog": "Order Backlog",
    "exports": "Exports",
    "imports": "Imports",
}


def prompt_for_values() -> dict:
    print("Enter this month's ISM Manufacturing Report on Business values.")
    print("(Leave blank and press Enter to skip a sub-index that hasn't been published yet.)\n")
    date_str = input("Report month (YYYY-MM-01): ").strip()
    values = {"Date": date_str}
    for col in SUBINDEX_COLS:
        raw = input(f"{col}: ").strip()
        values[col] = float(raw) if raw else None
    return values


def values_from_args(args) -> dict:
    values = {"Date": args.date}
    for arg_name, col in ARG_TO_COL.items():
        val = getattr(args, arg_name)
        values[col] = val
    return values


def update(values: dict):
    date = pd.Timestamp(values["Date"])
    history = pd.read_csv(CSV_PATH, parse_dates=["Date"])

    new_row = {"Date": date}
    for col in SUBINDEX_COLS:
        new_row[col] = values.get(col)

    history = history[history["Date"] != date]  # dedupe: drop existing row for this month, if any
    history = pd.concat([history, pd.DataFrame([new_row])], ignore_index=True)
    history = history.sort_values("Date").reset_index(drop=True)
    history.to_csv(CSV_PATH, index=False)

    # Report MoM change vs the prior month, for confirmation.
    history_sorted = history.sort_values("Date").reset_index(drop=True)
    idx = history_sorted.index[history_sorted["Date"] == date][0]
    print(f"\nSaved {date.strftime('%Y-%m-%d')} to {CSV_PATH}")
    if idx > 0:
        prior = history_sorted.iloc[idx - 1]
        print(f"{'Sub-Index':<22}{'New':>8}{'Prior':>8}{'Change':>9}")
        for col in SUBINDEX_COLS:
            cur, prev = new_row.get(col), prior[col]
            if cur is None or pd.isna(cur):
                continue
            change = f"{cur - prev:+.1f}" if pd.notna(prev) else "n/a"
            prev_disp = f"{prev:.1f}" if pd.notna(prev) else "n/a"
            print(f"{col:<22}{cur:>8.1f}{prev_disp:>8}{change:>9}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", help="Report month, e.g. 2026-07-01")
    for arg_name in ARG_TO_COL:
        parser.add_argument(f"--{arg_name.replace('_', '-')}", type=float, default=None)
    args = parser.parse_args()

    if args.date:
        values = values_from_args(args)
    else:
        values = prompt_for_values()

    if not values.get("Date"):
        print("A report month (--date or interactive prompt) is required.")
        sys.exit(1)

    update(values)


if __name__ == "__main__":
    main()
