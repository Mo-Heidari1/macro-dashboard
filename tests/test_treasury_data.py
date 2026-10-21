"""Integrity checks on the stored Treasury history (validated against Treasury.gov)."""

import pandas as pd
import pytest

from src.modules.treasury_yields import config as cfg
from src.modules.treasury_yields.calculations import load_history

TENORS = cfg.NOMINAL_TENORS + cfg.TIPS_TENORS


@pytest.fixture(scope="module")
def history() -> pd.DataFrame:
    return load_history()


@pytest.mark.parametrize(
    "date, expected",
    [
        # Treasury.gov par yield curve "3 Mo", prior trading day's close.
        ("2022-06-26", 1.73),  # was 1.66 (T-bill discount basis)
        ("2023-01-01", 4.42),  # prior close is 2022-12-30
        ("2024-01-07", 5.47),  # was 5.24
        ("2025-01-05", 4.34),  # was 4.20
        ("2026-06-28", 3.83),  # was 3.67
    ],
)
def test_weekly_3mo_is_treasury_par_yield(history, date, expected):
    row = history.loc[history["Date"] == pd.Timestamp(date)].iloc[0]
    assert row["3mo"] == pytest.approx(expected)


def test_sunday_rows_match_prior_trading_day(history):
    # Where weekly (Sunday) and daily rows overlap, a Sunday snapshot must
    # carry the prior trading day's close for every tenor.
    h = history.set_index("Date")
    daily = h[h.index.dayofweek < 5]
    sundays = h[(h.index.dayofweek == 6) & (h.index >= daily.index.min())]
    assert len(sundays) > 0
    for date, row in sundays.iterrows():
        prior = daily.loc[:date].dropna(subset=["10yr"]).iloc[-1]
        for tenor in TENORS:
            if pd.notna(row[tenor]) and pd.notna(prior[tenor]):
                assert row[tenor] == pytest.approx(prior[tenor]), (date.date(), tenor)


def test_2021_01_03_carries_the_2020_12_31_close(history):
    # The workbook's snapshot held 2020-12-30's values; Treasury.gov's last
    # 2020 close is 2020-12-31.
    row = history.loc[history["Date"] == pd.Timestamp("2021-01-03")].iloc[0]
    expected = {
        "1mo": 0.08,
        "3mo": 0.09,
        "2yr": 0.13,
        "10yr": 0.93,
        "30yr": 1.65,
        "5yr TIPS": -1.59,
        "10yr TIPS": -1.06,
    }
    for tenor, value in expected.items():
        assert row[tenor] == pytest.approx(value), tenor
