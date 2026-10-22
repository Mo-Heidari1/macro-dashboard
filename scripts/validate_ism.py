"""
Validate the committed ISM CSVs (data/ism/) against an ISM workbook's cached values.

    python scripts/validate_ism.py --workbook data/local/<file>.xlsx --out <folder>

Reads the workbook with pandas.read_excel (independently of the extraction
code) and compares, at 1 dp:
- every month of every sub-index sheet with data/ism/ism_history.csv
- the Heat Map Summary sheet (months x 11 series) with the same CSV
- every Sectors cell (Direction and Score) from SECTORS_START on with
  data/ism/ism_sectors.csv,
  and lists which months each Sectors block has
Writes validation_ism_series.csv, validation_ism_sectors.csv,
validation_ism_mismatches.csv and validation_ism_summary.txt to --out.
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

# sheet -> value column in that sheet; CSV column names follow cfg.SUBINDEX_COLS
SHEETS = {
    "PMI": "ISM Manufacturing Index",
    "New Orders": "New Orders",
    "Production": "Production",
    "Employment": "Employment",
    "Deliveries": "Deliveries",
    "Inventories": "Inventories",
    "Customer Inventories": "Customers' Inventories",
    "Prices": "Prices",
    "Order Backlog": "Order Backlog",
    "Exports": "Exports",
    "Imports": "Imports",
}
SECTOR_LABELS = {
    "ISM Manufacturing": "PMI",
    "NEW ORDERS": "New Orders",
    "PRODUCTION": "Production",
    "EMPLOYMENT": "Employment",
    "DELIVERIES": "Deliveries",
    "INVENTORIES": "Inventories",
    "CUSTOMER INVENTORIES": "Customer Inventories",
}


def compare_series(xlsx: str, csv: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """One row per sub-index: ranges, counts, compared cells, mismatches."""
    rows, bad = [], []
    for col, value_col in SHEETS.items():
        sheet = pd.read_excel(xlsx, sheet_name=col, usecols=["Date", value_col])
        sheet = sheet.dropna(subset=["Date", value_col])
        wb = sheet.set_index(pd.to_datetime(sheet["Date"]))[value_col].astype(float)
        stored = csv.set_index("Date")[col].dropna()
        both = wb.index.intersection(stored.index)
        diff = wb.loc[both].round(1) != stored.loc[both].round(1)
        bad += [(d.date(), col, stored[d], wb[d]) for d in both[diff.to_numpy()]]
        rows.append(
            {
                "series": col,
                "workbook range": f"{wb.index.min():%Y-%m}..{wb.index.max():%Y-%m}",
                "workbook months": len(wb),
                "csv months": len(stored),
                "compared": len(both),
                "mismatches": int(diff.sum()),
                "only in workbook": len(wb.index.difference(stored.index)),
                "only in csv": len(stored.index.difference(wb.index)),
            }
        )
    return pd.DataFrame(rows), bad


def compare_heatmap(xlsx: str, csv: pd.DataFrame) -> tuple[int, int, str]:
    """(cells compared, mismatches, month range) for the Heat Map Summary sheet."""
    raw = pd.read_excel(xlsx, sheet_name="Heat Map Summary", header=None, skiprows=3)
    hm = raw.iloc[:, 1:13]
    hm.columns = ["Date"] + cfg.SUBINDEX_COLS
    hm = hm.dropna(subset=["Date", "PMI"])
    hm = hm.set_index(pd.to_datetime(hm["Date"]))[cfg.SUBINDEX_COLS].astype(float)
    stored = csv.set_index("Date")[cfg.SUBINDEX_COLS]
    both = hm.index.intersection(stored.index)
    a, b = hm.loc[both], stored.loc[both]
    cells = a.notna() & b.notna()
    bad = (a.round(1) != b.round(1)) & cells
    span = f"{hm.index.min():%Y-%m}..{hm.index.max():%Y-%m}"
    return int(cells.values.sum()), int(bad.values.sum()), span


def read_sectors(xlsx: str) -> tuple[pd.DataFrame, dict]:
    """Every Sectors cell as Category/Date/Industry/Direction/Score, plus months per block."""
    ws = openpyxl.load_workbook(xlsx, data_only=True)["Sectors"]
    starts = [
        r
        for r in range(1, ws.max_row + 1)
        if ws.cell(r, 2).value and isinstance(ws.cell(r, 3).value, datetime.datetime)
    ]
    records, months = [], {}
    for i, start in enumerate(starts):
        end = starts[i + 1] - 1 if i + 1 < len(starts) else ws.max_row
        category = SECTOR_LABELS.get(ws.cell(start, 2).value, ws.cell(start, 2).value)
        cols = [
            c
            for c in range(3, ws.max_column + 1)
            if isinstance(ws.cell(start, c).value, datetime.datetime)
        ]
        months[category] = [pd.Timestamp(ws.cell(start, c).value) for c in cols]
        for r in range(start + 1, end + 1):
            industry = ws.cell(r, 2).value
            if industry is None:
                continue
            for c in cols:
                direction, score = ws.cell(r, c).value, ws.cell(r, c + 1).value
                if direction is None and score is None:
                    continue
                records.append(
                    (
                        category,
                        pd.Timestamp(ws.cell(start, c).value),
                        industry,
                        direction,
                        score,
                    )
                )
    cols = ["Category", "Date", "Industry", "Direction", "Score"]
    return pd.DataFrame(records, columns=cols), months


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--workbook", default=paths.local_path(cfg.SOURCE_WORKBOOK))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    csv = pd.read_csv(
        paths.dataset_path(cfg.DATA_FOLDER, cfg.HISTORY_FILE), parse_dates=["Date"]
    )
    series, bad = compare_series(args.workbook, csv)
    hm_cells, hm_bad, hm_span = compare_heatmap(args.workbook, csv)

    wb_s, months = read_sectors(args.workbook)
    wb_s = wb_s[wb_s["Date"] >= pd.Timestamp(cfg.SECTORS_START)]  # committed range only
    csv_s = pd.read_csv(
        paths.dataset_path(cfg.DATA_FOLDER, cfg.SECTORS_FILE), parse_dates=["Date"]
    )
    key = ["Category", "Date", "Industry"]
    m = wb_s.merge(csv_s, on=key, how="outer", suffixes=("_wb", "_csv"), indicator=True)
    both = m[m["_merge"] == "both"]
    sector_bad = both[
        (both["Direction_wb"] != both["Direction_csv"])
        | (both["Score_wb"] != both["Score_csv"])
    ]
    sector_table = (
        m.assign(month=m["Date"].dt.strftime("%Y-%m"))
        .pivot_table(
            index=["Category", "month"],
            columns="_merge",
            values="Industry",
            aggfunc="count",
            fill_value=0,
            observed=False,
        )
        .rename(columns={"left_only": "workbook only", "right_only": "csv only"})
        .reset_index()
    )
    expected = pd.date_range("2025-01-01", "2026-09-01", freq="MS")
    missing = {
        c: [d.strftime("%Y-%m") for d in expected if d not in set(ms)]
        for c, ms in months.items()
    }

    series.to_csv(os.path.join(args.out, "validation_ism_series.csv"), index=False)
    sector_table.to_csv(
        os.path.join(args.out, "validation_ism_sectors.csv"), index=False
    )
    pd.DataFrame(bad, columns=["date", "series", "csv", "workbook"]).to_csv(
        os.path.join(args.out, "validation_ism_mismatches.csv"), index=False
    )
    lines = [
        f"ISM CSVs vs {os.path.basename(args.workbook)} (run {pd.Timestamp.now():%Y-%m-%d %H:%M})",
        "",
        "Sub-index sheets vs ism_history.csv:",
        series.to_string(index=False),
        f"TOTAL compared {series['compared'].sum()}, mismatches {series['mismatches'].sum()}",
        "",
        f"Heat Map Summary ({hm_span}) vs ism_history.csv: {hm_cells} cells, {hm_bad} mismatches",
        "",
        (
            f"Sectors: {len(both)} rows in both, {len(sector_bad)} mismatching; "
            f"{(m['_merge'] == 'left_only').sum()} workbook-only rows, "
            f"{(m['_merge'] == 'right_only').sum()} csv-only rows"
        ),
        "Sectors months missing from Jan 2025-Sep 2026, by block:",
        *[
            f"  {c:<22} {len(months[c])} months; missing: {', '.join(v) or 'none'}"
            for c, v in missing.items()
        ],
    ]
    with open(
        os.path.join(args.out, "validation_ism_summary.txt"), "w", encoding="utf-8"
    ) as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
