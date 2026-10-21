"""
One-time extraction: ISM_Manufacturing_Index_Updated.xlsx -> CSV files.

Run once (or whenever the source workbook is replaced) with:
    python scripts/extract_ism.py

Produces, in the project root:
- ism_history.csv     wide format, one row per month, one column per
                       sub-index (mirrors the 'Heat Map Summary' sheet shape).
                       This is the file ism_calculations.load_ism_history()
                       reads.
- ism_sectors.csv      long format: Date, Industry, Direction, Score
                       (melted from the wide 'Sectors' sheet).

Every sub-index sheet auto-fills future dates with blank values (autofill
artifact in the source file) — we filter to rows where the value column is
non-null rather than trusting max_row.
"""

import os
import openpyxl
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX_PATH = os.path.join(ROOT, "ISM_Manufacturing_Index_Updated.xlsx")

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
    "Date", "PMI", "New Orders", "Production", "Employment", "Deliveries",
    "Inventories", "Customer Inventories", "Prices", "Order Backlog",
    "Exports", "Imports",
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
    with a header row where column B holds the category label and columns
    C, E, G, ... hold month dates, followed by a blank row, then its
    industry rows, ending at the next header row or a run of blank rows.
    """
    # Find every header row: col B has a label AND col C is a date.
    headers = []  # (row, category, [(date, direction_col, score_col), ...])
    for r in range(1, ws.max_row + 1):
        label = ws.cell(r, 2).value
        first = ws.cell(r, 3).value
        if label is not None and isinstance(first, __import__("datetime").datetime):
            months = []
            c = 3
            while c <= ws.max_column:
                date = ws.cell(r, c).value
                if date is not None:
                    months.append((pd.Timestamp(date), c, c + 1))
                c += 2
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
    out = pd.DataFrame(records, columns=["Category", "Date", "Industry", "Direction", "Score"])
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


def main():
    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)

    merged = None
    for sheet_name, (value_col, out_col) in SUBINDEX_SHEETS.items():
        df = extract_sheet(wb[sheet_name], value_col)
        df = df.rename(columns={value_col: out_col})
        merged = df if merged is None else merged.merge(df, on="Date", how="outer")

    merged = merged.sort_values("Date").reset_index(drop=True)
    merged = merged[COLUMN_ORDER]

    out_path = os.path.join(ROOT, "ism_history.csv")
    merged.to_csv(out_path, index=False)
    print(f"Wrote {out_path}: {len(merged)} rows, "
          f"{merged['Date'].min().date()} to {merged['Date'].max().date()}")

    sectors = extract_sectors(wb["Sectors"])
    sectors_path = os.path.join(ROOT, "ism_sectors.csv")
    sectors.to_csv(sectors_path, index=False)
    print(f"Wrote {sectors_path}: {len(sectors)} rows, "
          f"{sectors['Date'].nunique()} months, {sectors['Industry'].nunique()} industries")


if __name__ == "__main__":
    main()
