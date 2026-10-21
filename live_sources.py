"""
Live data fetchers — NOT runnable in this sandbox (network is restricted to
package repos here). Run this on your own machine or after deployment,
where normal internet access applies.

Design: each function returns a DataFrame with the same column names as
yields_history.pkl (Date + the 17 tenor columns), so the output can be
concatenated straight onto the historical DataFrame from calculations.py.

Sources:
- Nominal yields:  https://home.treasury.gov/resource-center/data-chart-center/
    interest-rates/daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve
- TIPS (real) yields: same endpoint, type=daily_treasury_real_yield_curve
- Fed Funds effective rate: FRED series EFFR (requires a free API key from
    https://fred.stlouisfed.org/docs/api/api_key.html)
"""

import pandas as pd
import requests

TREASURY_NOMINAL_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve&"
    "field_tdr_date_value={year}&page&_format=csv"
)
TREASURY_TIPS_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{year}/all?type=daily_treasury_real_yield_curve&"
    "field_tdr_date_value={year}&page&_format=csv"
)
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"

# Treasury.gov column names -> your workbook's tenor names.
# Verified against a live pull on 2026-09-03 - Treasury's CSV headers are
# exactly: "1 Mo","1.5 Month","2 Mo","3 Mo","4 Mo","6 Mo","1 Yr","2 Yr",
# "3 Yr","5 Yr","7 Yr","10 Yr","20 Yr","30 Yr" (note "1.5 Month", not "1.5 Mo").
NOMINAL_COL_MAP = {
    "1 Mo": "1mo", "3 Mo": "3mo", "6 Mo": "6mo", "1 Yr": "1yr", "2 Yr": "2yr",
    "3 Yr": "3yr", "5 Yr": "5yr", "7 Yr": "7yr", "10 Yr": "10yr",
    "20 Yr": "20yr", "30 Yr": "30yr",
}
TIPS_COL_MAP = {
    "5 Yr": "5yr TIPS", "7 Yr": "7yr TIPS", "10 Yr": "10yr TIPS",
    "20 Yr": "20yr TIPS", "30 Yr": "30yr TIPS",
}


def fetch_nominal_yields(year: int) -> pd.DataFrame:
    """Daily par nominal yield curve rates for a given year."""
    url = TREASURY_NOMINAL_URL.format(year=year)
    raw = pd.read_csv(url)
    raw["Date"] = pd.to_datetime(raw["Date"])
    keep = {"Date": "Date", **NOMINAL_COL_MAP}
    return raw[[c for c in keep if c in raw.columns]].rename(columns=keep)


def fetch_tips_yields(year: int) -> pd.DataFrame:
    """Daily par real (TIPS) yield curve rates for a given year."""
    url = TREASURY_TIPS_URL.format(year=year)
    raw = pd.read_csv(url)
    raw["Date"] = pd.to_datetime(raw["Date"])
    keep = {"Date": "Date", **TIPS_COL_MAP}
    return raw[[c for c in keep if c in raw.columns]].rename(columns=keep)


def fetch_fed_funds(api_key: str, start_date: str = "1954-01-01") -> pd.DataFrame:
    """Effective Fed Funds rate (FRED series EFFR) from start_date to today."""
    params = {
        "series_id": "EFFR",
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start_date,
    }
    resp = requests.get(FRED_URL, params=params, timeout=30)
    resp.raise_for_status()
    obs = resp.json()["observations"]
    df = pd.DataFrame(obs)[["date", "value"]]
    df["Date"] = pd.to_datetime(df["date"])
    df["Fed Funds"] = pd.to_numeric(df["value"], errors="coerce")
    return df[["Date", "Fed Funds"]]


def build_latest_snapshot(year: int, fred_api_key: str) -> pd.DataFrame:
    """
    Combine nominal + TIPS + Fed Funds into one row-per-date DataFrame,
    matching the shape of yields_history.pkl. Merges on Date (outer join,
    since Fed Funds/Treasury.gov updates don't always land on the exact
    same calendar day).
    """
    nom = fetch_nominal_yields(year)
    tips = fetch_tips_yields(year)
    ff = fetch_fed_funds(fred_api_key, start_date=f"{year}-01-01")

    merged = nom.merge(tips, on="Date", how="outer").merge(ff, on="Date", how="outer")
    merged = merged.sort_values("Date").reset_index(drop=True)
    return merged


def append_to_history(history_path: str, new_rows: pd.DataFrame, save_path: str = None):
    """
    Append freshly fetched rows onto the existing historical pickle,
    dedupe on Date, and save. This is the function you'd call on a
    schedule (e.g. weekly) to keep the dashboard current.
    """
    history = pd.read_pickle(history_path)
    combined = pd.concat([history, new_rows], ignore_index=True)
    combined = combined.drop_duplicates(subset="Date", keep="last")
    combined = combined.sort_values("Date").reset_index(drop=True)
    combined.to_pickle(save_path or history_path)
    return combined
