"""Tests for the ISM Manufacturing module. Run on the committed sample; the
local-vs-sample check runs only where the licensed full history exists."""

import numpy as np
import pandas as pd
import pytest

from src.core import paths
from src.core.signals import validate_signal
from src.modules.ism_manufacturing import config as cfg
from src.modules.ism_manufacturing.calculations import (
    classify,
    get_signal,
    heatmap_data,
    load_ism_history,
    load_ism_sectors,
    pmi_regime,
    recompute_pmi_from_subindices,
    sector_rankings,
    summary_table,
)


@pytest.fixture(scope="module")
def sample() -> pd.DataFrame:
    return load_ism_history(paths.sample_path(cfg.HISTORY_FILE))


def _pmi_frame(values, start="2024-01-01") -> pd.DataFrame:
    df = pd.DataFrame({"Date": pd.date_range(start, periods=len(values), freq="MS")})
    for col in cfg.SUBINDEX_COLS:
        df[col] = np.nan
    df["PMI"] = values
    return df


# ---------- known values (official release) ----------


@pytest.mark.parametrize(
    "month, expected",
    [
        # Headline PMI as published in ISM's Manufacturing Report On Business;
        # matched against the source workbook's cached values.
        ("2026-06-01", 53.3),
        ("2026-05-01", 54.0),
        ("2026-04-01", 52.7),
        ("2026-01-01", 52.6),
        ("2025-12-01", 47.9),
    ],
)
def test_known_headline_pmi(sample, month, expected):
    assert sample.set_index("Date").loc[month, "PMI"] == pytest.approx(expected)


def test_sample_pmi_matches_local_history(sample, has_local_ism):
    if not has_local_ism:
        pytest.skip("licensed full ISM history not present")
    full = load_ism_history(paths.local_path(cfg.HISTORY_FILE)).set_index("Date")
    s = sample.set_index("Date")
    pd.testing.assert_series_equal(s["PMI"], full.loc[s.index, "PMI"])


def test_sample_shape(sample):
    assert len(sample) == cfg.SAMPLE_MONTHS
    assert list(sample.columns) == ["Date"] + cfg.SUBINDEX_COLS


# ---------- calculations ----------


@pytest.mark.parametrize(
    "value, expected",
    [
        (50.1, "Growth"),
        (50.0, "Neutral"),
        (49.9, "Contraction"),
        (np.nan, "N/A"),
    ],
)
def test_classify_threshold(value, expected):
    assert classify(value) == expected


def test_pmi_weights_sum_to_one():
    assert sum(cfg.PMI_WEIGHTS.values()) == pytest.approx(1.0)


def test_recompute_pmi_known_value():
    df = _pmi_frame([53.0])
    df[["New Orders", "Production", "Employment", "Deliveries", "Inventories"]] = [
        [60, 50, 50, 50, 50]
    ]
    out = recompute_pmi_from_subindices(df).iloc[0]
    assert out["Recomputed PMI"] == pytest.approx(0.30 * 60 + 0.70 * 50)
    assert out["Diff"] == pytest.approx(0.0)


def test_summary_table_mom_yoy():
    df = _pmi_frame(np.arange(48.0, 61.0))  # 13 months, +1 per month
    row = summary_table(df).set_index("Sub-Index").loc["PMI"]
    assert (row["Current"], row["Status"], row["MoM"], row["YoY"]) == (
        60.0,
        "Growth",
        1.0,
        12.0,
    )


def test_heatmap_and_sectors_on_sample(sample):
    assert heatmap_data(sample, 12).shape == (12, len(cfg.SUBINDEX_COLS))
    sectors = load_ism_sectors(paths.sample_path(cfg.SECTORS_FILE))
    ranked = sector_rankings(sectors, sectors["Date"].max(), "PMI")
    assert not ranked.empty and ranked["Score"].is_monotonic_decreasing


# ---------- get_signal ----------


@pytest.mark.parametrize(
    "values, regime, direction",
    [
        ([52, 52, 52, 54, 55, 56], "Expansion", "improving"),
        ([56, 55, 54, 52, 52, 51], "Slowdown", "deteriorating"),
        ([49, 49, 48, 46, 45.5, 45.5], "Contraction", "deteriorating"),
        ([45, 45, 46, 47, 48, 49], "Recovery", "improving"),
        (
            [52, 52, 52, 52.5, 52.5, 52.5],
            "Expansion",
            "flat",
        ),  # within ±1.0: flat, but rising
        (
            [48, 48, 48, 47.6, 47.6, 47.6],
            "Contraction",
            "flat",
        ),  # within ±1.0: flat, but falling
    ],
)
def test_signal_quadrants(values, regime, direction):
    sig = get_signal(_pmi_frame(values))
    assert (sig["regime"], sig["direction"]) == (regime, direction)


@pytest.mark.parametrize(
    "level, extreme", [(55.1, True), (55.0, False), (45.0, False), (44.9, True)]
)
def test_signal_extreme_flag(level, extreme):
    assert get_signal(_pmi_frame([50, 50, 50, 50, 50, level]))["extreme"] is extreme


def test_pmi_regime_edges():
    assert pmi_regime(50.0, -0.5) == "Slowdown"  # exactly 50 counts as above
    assert pmi_regime(49.9, 0.0) == "Recovery"  # zero momentum counts as rising


def test_signal_skips_month_without_headline():
    df = _pmi_frame([50.0, 51.0, 52.0, np.nan])  # sub-indices typed, PMI not yet
    df.loc[3, "New Orders"] = 55.0
    sig = get_signal(df)
    assert sig["as_of"] == "2024-03-01"
    assert sig["level"] == 52.0 and sig["change"] == 1.0


def test_signal_schema_on_sample(sample):
    sig = get_signal(sample)
    assert validate_signal(sig, cfg.DIRECTION_LABELS, cfg.REGIME_LABELS) == []
    assert sig["as_of"] == "2026-06-01" and sig["level"] == 53.3
