"""
Shared data loaders: CSV readers with the local -> sample fallback, and
network fetchers for public sources.

Fetchers here are plain functions with no Streamlit dependency (engineering
rule 3). Pages wrap them in st.cache_data and handle the fall-back-to-CSV
warning themselves (rule 6).

Sources:
- Treasury.gov daily par yield curves (nominal and real/TIPS):
    https://home.treasury.gov/resource-center/data-chart-center/interest-rates/
- FRED (St. Louis Fed) series observations API; needs a free key:
    https://fred.stlouisfed.org/docs/api/api_key.html
"""

import pandas as pd
import requests

from src.core.paths import resolve_data_file

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


# ---------- stored CSVs ----------


def read_dated_csv(path: str, date_col: str = "Date") -> pd.DataFrame:
    """Read a CSV with `date_col` parsed as datetime."""
    return pd.read_csv(path, parse_dates=[date_col])


def load_dataset(filename: str) -> tuple[pd.DataFrame, bool]:
    """
    Load `filename` from data/local/ if present, otherwise data/sample/.
    Returns (df, is_sample) so the page can show a sample-data note.
    """
    path, is_sample = resolve_data_file(filename)
    return read_dated_csv(path), is_sample


# ---------- Treasury.gov ----------


def fetch_treasury_curve(year: int, col_map: dict, real: bool = False) -> pd.DataFrame:
    """
    Daily par yield curve for `year` from Treasury.gov (nominal, or real/TIPS
    if `real`), keeping Date plus the columns in `col_map`, renamed by it.
    """
    url = (TREASURY_TIPS_URL if real else TREASURY_NOMINAL_URL).format(year=year)
    raw = pd.read_csv(url)
    raw["Date"] = pd.to_datetime(raw["Date"])
    keep = {"Date": "Date", **col_map}
    return raw[[c for c in keep if c in raw.columns]].rename(columns=keep)


# ---------- FRED ----------


def fetch_fred_series(
    series_id: str, api_key: str, start_date: str, value_name: str | None = None
) -> pd.DataFrame:
    """FRED series observations from start_date to today, as Date + one value column."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start_date,
    }
    resp = requests.get(FRED_URL, params=params, timeout=30)
    resp.raise_for_status()
    obs = resp.json()["observations"]
    df = pd.DataFrame(obs)[["date", "value"]]
    name = value_name or series_id
    df["Date"] = pd.to_datetime(df["date"])
    df[name] = pd.to_numeric(df["value"], errors="coerce")
    return df[["Date", name]]


# ---------- legacy ----------


def append_to_history(
    history_path: str, new_rows: pd.DataFrame, save_path: str | None = None
):
    """
    Legacy pickle-based append, carried over unchanged from live_sources.py.
    Unused; scheduled for removal on fix/data-integrity (engineering rule 1).
    """
    history = pd.read_pickle(history_path)
    combined = pd.concat([history, new_rows], ignore_index=True)
    combined = combined.drop_duplicates(subset="Date", keep="last")
    combined = combined.sort_values("Date").reset_index(drop=True)
    combined.to_pickle(save_path or history_path)
    return combined
