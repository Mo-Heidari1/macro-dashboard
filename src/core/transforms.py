"""
Shared time-series maths used by more than one module. Pure functions: no
I/O, no global state, no Streamlit.
"""

import pandas as pd


def change_at_offset(df: pd.DataFrame, col: str, offset: int) -> float | None:
    """
    Latest value of `col` minus its value `offset` rows earlier, rounded to
    4 dp. None if there aren't enough rows or either value is missing.
    Offsets are in rows, so their meaning depends on the data's cadence.
    """
    if len(df) <= offset:
        return None
    cur = df.iloc[-1][col]
    prior = df.iloc[-1 - offset][col]
    if pd.isna(cur) or pd.isna(prior):
        return None
    return round(cur - prior, 4)


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
