"""Tests for the Treasury Yields & Curve module."""

import numpy as np
import pandas as pd
import pytest

from src.core.signals import validate_signal
from src.modules.treasury_yields import config as cfg
from src.modules.treasury_yields.calculations import (
    curve_on_date, curve_regime, get_signal, implied_inflation, load_history,
    spread_series, summary_table,
)


@pytest.fixture(scope="module")
def history() -> pd.DataFrame:
    return load_history()


def _frame(dates, **cols) -> pd.DataFrame:
    """Small yields frame with every tenor column, NaN unless given."""
    df = pd.DataFrame({"Date": pd.to_datetime(dates)})
    for col in cfg.TENOR_COLS:
        df[col] = cols.get(col, np.nan)
    return df


# ---------- known values (official release) ----------

@pytest.mark.parametrize("date, tenor, expected", [
    # Treasury.gov daily par yield curve rates, checked against a live pull.
    ("2026-09-11", "2yr", 4.63), ("2026-09-11", "10yr", 4.96), ("2026-09-11", "30yr", 5.35),
    ("2026-09-14", "2yr", 4.65), ("2026-09-14", "10yr", 4.97), ("2026-09-14", "30yr", 5.34),
    # Weekly rows are dated Sunday and carry the prior Friday's close (2024-06-28).
    ("2024-06-30", "2yr", 4.71), ("2024-06-30", "10yr", 4.36),
])
def test_known_values_match_treasury(history, date, tenor, expected):
    row = history.loc[history["Date"] == pd.Timestamp(date)].iloc[0]
    assert row[tenor] == pytest.approx(expected)


def test_known_spread_and_curve(history):
    sp = spread_series(history, "10yr", "2yr").set_index("Date")
    assert sp.loc["2026-09-14", "Spread"] == pytest.approx(4.97 - 4.65)
    curve = curve_on_date(history, date="2026-09-14")
    assert list(curve["Tenor"]) == cfg.NOMINAL_TENORS
    assert curve["Maturity (yrs)"].is_monotonic_increasing


# ---------- calculations ----------

def test_summary_table_row_offsets():
    tenyr = np.arange(60, dtype=float) / 10
    df = _frame(pd.date_range("2020-01-05", periods=60, freq="W-SUN"), **{"10yr": tenyr})
    row = summary_table(df).set_index("Tenor").loc["10yr"]
    assert row["Current Yield %"] == pytest.approx(5.9)
    assert (row["WoW"], row["MoM"], row["QoQ"], row["YoY"]) == pytest.approx((0.1, 0.4, 1.3, 5.2))
    assert pd.isna(summary_table(df).set_index("Tenor").loc["2yr", "WoW"])


def test_implied_inflation_walks_back_past_missing_tips():
    df = _frame(["2026-01-04", "2026-01-11"],
                **{"10yr": [4.0, 4.2], "10yr TIPS": [1.8, np.nan], "5yr": [3.5, 3.6]})
    infl = implied_inflation(df)
    assert list(infl["Maturity"]) == ["10yr"]
    assert infl["Implied Inflation"].iloc[0] == pytest.approx(2.2)
    assert implied_inflation(_frame(["2026-01-04"])).empty


@pytest.mark.parametrize("spread_change, level_change, expected", [
    (0.15, -0.10, "bull steepener"),
    (0.15, 0.10, "bear steepener"),
    (-0.15, -0.10, "bull flattener"),
    (-0.15, 0.10, "bear flattener"),
    (0.05, 0.30, cfg.REGIME_RANGE_BOUND),
    (0.10, 0.30, cfg.REGIME_RANGE_BOUND),    # exactly the band = flat
    (None, None, cfg.REGIME_RANGE_BOUND),
])
def test_curve_regime(spread_change, level_change, expected):
    assert curve_regime(spread_change, level_change, cfg.DIRECTION_BAND_PP) == expected


# ---------- get_signal ----------

def test_signal_uses_calendar_lookback_on_daily_data():
    dates = pd.bdate_range("2026-01-01", "2026-03-31")
    two = np.linspace(4.00, 4.60, len(dates))        # front end sells off faster
    ten = np.linspace(4.50, 4.70, len(dates))
    sig = get_signal(_frame(dates, **{"2yr": two, "10yr": ten}))
    prior = (pd.Series(ten - two, index=dates)).loc[:dates[-1] - pd.Timedelta(days=28)].iloc[-1]
    assert sig["change"] == pytest.approx(round((ten[-1] - two[-1]) - prior, 4))
    assert sig["direction"] == "flattening"
    assert sig["regime"] == "bear flattener"


def test_signal_skips_incomplete_trailing_rows():
    dates = pd.date_range("2025-01-05", periods=60, freq="W-SUN")
    df = _frame(dates, **{"2yr": np.full(60, 4.0), "10yr": np.full(60, 4.5)})
    df.loc[59, "10yr"] = np.nan                      # 2yr posted, 10yr not yet
    df.loc[58, ["2yr", "10yr"]] = np.nan             # holiday row, nothing posted
    sig = get_signal(df)
    assert sig["as_of"] == dates[57].strftime("%Y-%m-%d")
    assert sig["level"] == pytest.approx(0.5)


def test_signal_schema_on_committed_data(history):
    sig = get_signal(history)
    assert validate_signal(sig, cfg.DIRECTION_LABELS, cfg.REGIME_LABELS) == []
    assert sig["market_read"] == cfg.MARKET_READ[sig["regime"]]


def test_signal_raises_without_any_complete_row():
    with pytest.raises(ValueError):
        get_signal(_frame(["2026-01-04"], **{"2yr": [4.0]}))
