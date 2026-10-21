"""
Shared time-series maths used by more than one module. Pure functions: no
I/O, no global state, no Streamlit.
"""

import pandas as pd


def change_over(
    df: pd.DataFrame,
    col: str,
    lookback: pd.Timedelta | pd.DateOffset,
    date_col: str = "Date",
) -> float | None:
    """
    Latest value of `col` minus the last value dated on or before
    (latest date - lookback), rounded to 4 dp. Calendar-based, so it means
    the same thing on weekly, daily or mixed-cadence data. The comparison
    value must be less than one further lookback older than that (so a
    missing month can't turn MoM into a 12-month change). None if the
    latest value is missing or no comparison value qualifies.
    """
    if df.empty:
        return None
    latest = df.iloc[-1]
    cur = latest[col]
    if pd.isna(cur):
        return None
    target = latest[date_col] - lookback
    window = (df[date_col] <= target) & (df[date_col] > target - lookback)
    earlier = df.loc[window, col].dropna()
    if earlier.empty:
        return None
    return round(cur - earlier.iloc[-1], 4)


def last_complete_row(df: pd.DataFrame, cols: list[str]) -> int | None:
    """
    Positional index of the most recent row where every column in `cols`
    is populated, walking backward from the end. None if no row qualifies.
    """
    complete = df[cols].notna().all(axis=1).to_numpy()
    for i in range(len(df) - 1, -1, -1):
        if complete[i]:
            return i
    return None


def row_on_or_before(
    df: pd.DataFrame, date: pd.Timestamp, date_col: str = "Date"
) -> pd.Series | None:
    """
    Last row of an ascending `df` dated on or before `date`, for
    calendar-based comparisons that don't depend on row cadence.
    None if every row is later than `date`.
    """
    earlier = df[df[date_col] <= date]
    if earlier.empty:
        return None
    return earlier.iloc[-1]


def zscore_last(series: pd.Series, min_periods: int = 2) -> float | None:
    """
    Z-score of the last value against the whole `series` (sample std).
    None if fewer than `min_periods` non-missing values or zero variance.
    """
    values = series.dropna()
    if len(values) < max(min_periods, 2):
        return None
    std = values.std(ddof=1)
    if std == 0 or pd.isna(std):
        return None
    return float((values.iloc[-1] - values.mean()) / std)


def window_mean_change(series: pd.Series, window: int) -> float | None:
    """
    Mean of the last `window` non-missing values minus the mean of the
    `window` values before them (e.g. 3m average vs prior 3m average).
    None if fewer than 2 * window values.
    """
    values = series.dropna()
    if len(values) < 2 * window:
        return None
    recent = values.iloc[-window:].mean()
    prior = values.iloc[-2 * window : -window].mean()
    return float(recent - prior)
