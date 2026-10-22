"""
Extraction: ISM source workbook (data/local/) -> committed CSVs in data/ism/.

Full rebuild from the configured workbook (SOURCE_WORKBOOK):
    python scripts/extract_ism.py
Import specific months from a newer workbook, keeping everything else:
    python scripts/extract_ism.py --workbook data/local/<file>.xlsx
        --months 2026-07,2026-08,2026-09 --report <folder>

In --months mode the requested months are added (or replaced), revisions the
workbook made to months already stored are applied, and nothing is deleted;
every revision and every difference not applied is printed and, with
--report, saved as CSV.

Produces the committed data files in data/ism/ (sector rankings only from
SECTORS_START on; the workbook itself stays in data/local/, git-ignored):
- ism_history.csv     wide format, one row per month, one column per
                       sub-index (mirrors the 'Heat Map Summary' sheet shape).
                       This is the file load_ism_history()
                       reads.
- ism_sectors.csv      long format: Date, Industry, Direction, Score
                       (melted from the wide 'Sectors' sheet).

Every sub-index sheet auto-fills future dates with blank values (autofill
artifact in the source file) — we filter to rows where the value column is
non-null rather than trusting max_row.
"""

import argparse
import datetime
import os
import sys

import openpyxl
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import paths
from src.modules.ism_manufacturing import config as cfg
from src.modules.ism_manufacturing.calculations import merge_months

XLSX_PATH = paths.local_path(cfg.SOURCE_WORKBOOK)

# sheet name -> (value column name in that sheet, output column name)
SUBINDEX_SHEETS = {
    "PMI": ("ISM Manufacturing Index", "PMI"),
    "New Orders": ("New Orders", "New Orders"),
    "Production": ("Production", "Production"),
    "Employment": ("Employment", "Employment"),
    "Deliveries": ("Deliveries", "Deliveries"),
    "Inventories": ("Inventories", "Inventories"),
    "Customer Inventories": ("Customers' Inventories", "Customer Inventories"),
    "Prices": ("Prices", "Prices"),
    "Order Backlog": ("Order Backlog", "Order Backlog"),
    "Exports": ("Exports", "Exports"),
    "Imports": ("Imports", "Imports"),
}

# Final column order, matching the Heat Map Summary sheet's shape.
COLUMN_ORDER = [
    "Date",
    "PMI",
    "New Orders",
    "Production",
    "Employment",
    "Deliveries",
    "Inventories",
    "Customer Inventories",
    "Prices",
    "Order Backlog",
    "Exports",
    "Imports",
]


def extract_sheet(ws, value_col_name: str) -> pd.DataFrame:
    """Read a Date/value-column sheet, keeping only rows with a real value."""
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    date_idx = headers.index("Date") + 1
    val_idx = headers.index(value_col_name) + 1

    rows = []
    for r in range(2, ws.max_row + 1):
        date = ws.cell(r, date_idx).value
        val = ws.cell(r, val_idx).value
        if date is None or val is None:
            continue
        rows.append((pd.Timestamp(date), float(val)))
    return pd.DataFrame(rows, columns=["Date", value_col_name])


def extract_sectors(ws) -> pd.DataFrame:
    """
    Melt the Sectors sheet into a long DataFrame: Category, Date, Industry,
    Direction, Score.

    The sheet is NOT one flat industry table — it's a stack of sub-tables,
    one per category (headline PMI plus each sub-index that ISM publishes
    an industry breakdown for: New Orders, Production, Employment,
    Deliveries, Inventories, Customer Inventories). Each sub-table starts
    with a header row where column B holds the category label and month
    dates sit above (Direction, Score) column pairs, followed by a blank
    row, then its industry rows, ending at the next header row.

    Month headers are read from every column, not every other column: the
    pairs can shift by one where a spacer column was left (e.g. after a
    gap in the months), and a fixed C, E, G, ... step would skip them.
    """
    # Find every header row: col B has a label AND col C is a date.
    headers = []  # (row, category, [(date, direction_col, score_col), ...])
    for r in range(1, ws.max_row + 1):
        label = ws.cell(r, 2).value
        first = ws.cell(r, 3).value
        if label is not None and isinstance(first, datetime.datetime):
            months = [
                (pd.Timestamp(ws.cell(r, c).value), c, c + 1)
                for c in range(3, ws.max_column + 1)
                if isinstance(ws.cell(r, c).value, datetime.datetime)
            ]
            headers.append((r, label, months))

    records = []
    for i, (start_row, category, months) in enumerate(headers):
        end_row = headers[i + 1][0] - 1 if i + 1 < len(headers) else ws.max_row
        for r in range(start_row + 1, end_row + 1):
            industry = ws.cell(r, 2).value
            if industry is None:
                continue
            for date, dcol, scol in months:
                direction = ws.cell(r, dcol).value
                score = ws.cell(r, scol).value
                if direction is None and score is None:
                    continue
                records.append((category, date, industry, direction, score))
    out = pd.DataFrame(
        records, columns=["Category", "Date", "Industry", "Direction", "Score"]
    )
    out["Category"] = out["Category"].replace(CATEGORY_LABEL_MAP)
    return out


# Normalize the sheet's section labels to the same names used elsewhere
# (COLUMN_ORDER / SUBINDEX_SHEETS) so callers can match on one vocabulary.
CATEGORY_LABEL_MAP = {
    "ISM Manufacturing": "PMI",
    "NEW ORDERS": "New Orders",
    "PRODUCTION": "Production",
    "EMPLOYMENT": "Employment",
    "DELIVERIES": "Deliveries",
    "INVENTORIES": "Inventories",
    "CUSTOMER INVENTORIES": "Customer Inventories",
}


def extract_workbook(path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(history, sectors) extracted from an ISM workbook's cached values."""
    wb = openpyxl.load_workbook(path, data_only=True)
    merged = None
    for sheet_name, (value_col, out_col) in SUBINDEX_SHEETS.items():
        df = extract_sheet(wb[sheet_name], value_col)
        df = df.rename(columns={value_col: out_col})
        merged = df if merged is None else merged.merge(df, on="Date", how="outer")
    history = merged.sort_values("Date").reset_index(drop=True)[COLUMN_ORDER]
    return history, extract_sectors(wb["Sectors"])


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--workbook", default=XLSX_PATH)
    parser.add_argument("--months", default=None, help="e.g. 2026-07,2026-08")
    parser.add_argument(
        "--report", default=None, help="folder for the merge report CSVs"
    )
    args = parser.parse_args()

    history, sectors = extract_workbook(args.workbook)
    # Only rankings from SECTORS_START on are ever written (and committed).
    sectors = sectors[sectors["Date"] >= pd.Timestamp(cfg.SECTORS_START)]
    history_path = paths.dataset_path(cfg.DATA_FOLDER, cfg.HISTORY_FILE)
    sectors_path = paths.dataset_path(cfg.DATA_FOLDER, cfg.SECTORS_FILE)

    if args.months:
        months = [pd.Timestamp(m + "-01") for m in args.months.split(",")]
        current_h = pd.read_csv(history_path, parse_dates=["Date"])
        current_s = pd.read_csv(sectors_path, parse_dates=["Date"])
        history, report_h = merge_months(
            current_h, history, ["Date"], COLUMN_ORDER[1:], months
        )
        sectors, report_s = merge_months(
            current_s,
            sectors,
            ["Category", "Industry", "Date"],
            ["Direction", "Score"],
            months,
        )
        for name, rep in (("history", report_h), ("sectors", report_s)):
            counts = rep["kind"].value_counts().items()
            print(f"\n{name}: " + ", ".join(f"{k}={n}" for k, n in counts))
            print(
                rep[rep["kind"] == "revised"].to_string(index=False)
                if (rep["kind"] == "revised").any()
                else "  no revised values"
            )
            if args.report:
                os.makedirs(args.report, exist_ok=True)
                rep.to_csv(
                    os.path.join(args.report, f"ism_import_{name}.csv"), index=False
                )

    os.makedirs(paths.dataset_dir(cfg.DATA_FOLDER), exist_ok=True)
    history.to_csv(history_path, index=False)
    print(
        f"Wrote {history_path}: {len(history)} rows, "
        f"{history['Date'].min().date()} to {history['Date'].max().date()}"
    )
    sectors.to_csv(sectors_path, index=False)
    print(
        f"Wrote {sectors_path}: {len(sectors)} rows, "
        f"{sectors['Date'].nunique()} months, {sectors['Industry'].nunique()} industries"
    )


if __name__ == "__main__":
    main()
