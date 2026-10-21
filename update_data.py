"""
Run this whenever you want to refresh the dashboard with the latest yields.

Usage:
    python update_data.py YOUR_FRED_API_KEY

Get a free FRED API key at: https://fred.stlouisfed.org/docs/api/api_key.html
(takes about 2 minutes, no approval wait)

What it does:
1. Pulls the current year's nominal yields + TIPS yields from Treasury.gov
2. Pulls the Fed Funds effective rate from FRED
3. Merges them and appends any new dates onto yields_history.csv
4. Leaves everything else (calculations.py, app.py) untouched -- they'll
   just pick up the new rows automatically next time you run the dashboard
"""

import sys
import os
import pandas as pd
from live_sources import build_latest_snapshot

def main():
    if len(sys.argv) < 2:
        print("Usage: python update_data.py YOUR_FRED_API_KEY")
        sys.exit(1)

    fred_api_key = sys.argv[1]
    year = pd.Timestamp.today().year
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yields_history.csv")

    print(f"Fetching {year} data from Treasury.gov and FRED...")
    fresh = build_latest_snapshot(year, fred_api_key)
    print(f"Got {len(fresh)} rows from live sources, latest date: {fresh['Date'].max()}")

    history = pd.read_csv(csv_path, parse_dates=["Date"])
    print(f"Existing history: {len(history)} rows, latest date: {history['Date'].max()}")

    combined = pd.concat([history, fresh], ignore_index=True)
    combined = combined.drop_duplicates(subset="Date", keep="last")
    combined = combined.sort_values("Date").reset_index(drop=True)
    combined.to_csv(csv_path, index=False)

    added = len(combined) - len(history)
    print(f"Done. Added {added} new row(s). History now has {len(combined)} rows "
          f"through {combined['Date'].max().strftime('%Y-%m-%d')}.")
    print("Restart (or refresh) your Streamlit app to see the new data.")

if __name__ == "__main__":
    main()
