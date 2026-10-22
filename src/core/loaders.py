"""
Shared data loaders: CSV readers (with an optional data/local/ override), and
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

import io

import pandas as pd
import requests

from src.core.paths import dataset_dir, resolve_data_file

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


def load_dataset(filename: str, folder: str) -> tuple[pd.DataFrame, bool]:
    """
    Load `filename` from data/local/ if present, otherwise from the dataset's
    committed folder data/<folder>/. Returns (df, is_committed).
    """
    path, is_committed = resolve_data_file(filename, dataset_dir(folder))
    return read_dated_csv(path), is_committed


# ---------- Treasury.gov ----------


def parse_treasury_curve(raw: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    """
    Keep Date plus the columns in `col_map`, renamed by it. Headers are
    matched ignoring case and surrounding spaces: Treasury labels nominal
    tenors "10 Yr" but real (TIPS) tenors "10 YR".
    """
    wanted = {k.strip().upper(): v for k, v in col_map.items()}
    rename = {"Date": "Date"}
    for col in raw.columns:
        key = str(col).strip().upper()
        if key in wanted:
            rename[col] = wanted[key]
    out = raw[list(rename)].rename(columns=rename)
    out["Date"] = pd.to_datetime(out["Date"])
    return out


def fetch_treasury_curve(
    year: int, col_map: dict, real: bool = False, timeout: int = 60
) -> pd.DataFrame:
    """
    Daily par yield curve for `year` from Treasury.gov (nominal, or real/TIPS
    if `real`), keeping Date plus the columns in `col_map`, renamed by it.
    """
    url = (TREASURY_TIPS_URL if real else TREASURY_NOMINAL_URL).format(year=year)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return parse_treasury_curve(pd.read_csv(io.StringIO(resp.text)), col_map)


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
