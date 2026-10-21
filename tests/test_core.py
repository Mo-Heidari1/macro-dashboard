"""Tests for src/core: paths, transforms, signals, charts."""

import math
import os

import numpy as np
import pandas as pd
import pytest

from src.core import charts, paths
from src.core.loaders import parse_treasury_curve
from src.core.signals import DEFAULT_DIRECTION_LABELS, direction_label, validate_signal
from src.core.transforms import (
    change_over,
    last_complete_row,
    rolling_mean_change,
    row_on_or_before,
    zscore_last,
)

# ---------- paths ----------


def test_paths_are_built_from_repo_root():
    assert paths.DATA_LOCAL.startswith(paths.ROOT)
    assert paths.DATA_SAMPLE.startswith(paths.ROOT)
    assert paths.local_path("x.csv") == os.path.join(
        paths.ROOT, "data", "local", "x.csv"
    )


def test_resolve_prefers_local_then_sample(tmp_path):
    local, sample = tmp_path / "local", tmp_path / "sample"
    local.mkdir()
    sample.mkdir()
    (sample / "a.csv").write_text("Date\n")
    assert paths.resolve_data_file("a.csv", str(local), str(sample)) == (
        str(sample / "a.csv"),
        True,
    )
    (local / "a.csv").write_text("Date\n")
    assert paths.resolve_data_file("a.csv", str(local), str(sample)) == (
        str(local / "a.csv"),
        False,
    )


def test_resolve_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        paths.resolve_data_file("nope.csv", str(tmp_path), str(tmp_path))


# ---------- transforms ----------


def test_change_over_calendar_window():
    weekly = pd.DataFrame(
        {
            "Date": pd.date_range("2026-01-04", periods=5, freq="W-SUN"),
            "x": [1.0, 2.0, 4.5, np.nan, 7.123456],
        }
    )
    assert change_over(weekly, "x", pd.Timedelta(days=14)) == round(7.123456 - 4.5, 4)
    # prior week missing: nothing within one further window, so no change
    assert change_over(weekly, "x", pd.Timedelta(days=7)) is None
    assert change_over(weekly, "x", pd.Timedelta(days=60)) is None  # nothing old enough


def test_change_over_mixed_cadence():
    # weekly rows, then daily rows: a 7-day window is still one week
    dates = pd.to_datetime(
        [
            "2025-12-21",
            "2025-12-28",
            "2026-01-02",
            "2026-01-05",
            "2026-01-06",
            "2026-01-07",
            "2026-01-08",
            "2026-01-09",
        ]
    )
    df = pd.DataFrame({"Date": dates, "x": [1, 2, 3, 4, 5, 6, 7, 8.0]})
    assert change_over(df, "x", pd.Timedelta(days=7)) == 8.0 - 3.0  # vs 2026-01-02
    df.loc[7, "x"] = np.nan
    # latest row missing: walk back to 2026-01-08 (7) and compare with 2025-12-28 (2)
    assert change_over(df, "x", pd.Timedelta(days=7)) == 5.0


def test_change_over_months():
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2025-06-01", "2025-08-01", "2026-06-01"]),
            "x": [50.0, 51.0, 53.3],
        }
    )  # July 2025 missing
    assert change_over(df, "x", pd.DateOffset(months=12)) == pytest.approx(3.3)
    assert change_over(df, "x", pd.DateOffset(months=1)) is None  # May 2026 missing
    # stale comparison: the only older value is beyond one extra window
    assert change_over(df.iloc[[0, 2]], "x", pd.DateOffset(months=6)) is None


def test_last_complete_row_walks_back():
    df = pd.DataFrame({"a": [1, 2, 3, np.nan], "b": [1, 2, np.nan, 4]})
    assert last_complete_row(df, ["a", "b"]) == 1
    assert last_complete_row(df, ["b"]) == 3
    assert last_complete_row(df.iloc[2:], ["a", "b"]) is None


def test_row_on_or_before():
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-01", "2026-01-08", "2026-01-15"]),
            "v": [1, 2, 3],
        }
    )
    assert row_on_or_before(df, pd.Timestamp("2026-01-10"))["v"] == 2
    assert row_on_or_before(df, pd.Timestamp("2026-01-08"))["v"] == 2
    assert row_on_or_before(df, pd.Timestamp("2025-12-31")) is None


def test_zscore_last_known_value():
    # mean 3, sample std sqrt(2.5): (5 - 3) / 1.5811 = 1.2649
    assert zscore_last(pd.Series([1, 2, 3, 4, 5])) == pytest.approx(2 / math.sqrt(2.5))
    assert zscore_last(pd.Series([1, 2, 3]), min_periods=4) is None
    assert zscore_last(pd.Series([2.0, 2.0, 2.0])) is None  # zero variance


def test_rolling_mean_change():
    s = pd.Series([50, 51, 52, 54, 55, 56, 57.0])
    out = rolling_mean_change(s, 3)
    assert out.iloc[:5].isna().all()
    assert out.iloc[5] == pytest.approx(55 - 51)  # (54,55,56) vs (50,51,52)
    assert out.iloc[6] == pytest.approx(56 - 52.333333)


# ---------- signals ----------


def test_direction_label_band_is_exclusive():
    assert direction_label(1.0, 1.0) == "flat"
    assert direction_label(1.01, 1.0) == "improving"
    assert direction_label(-1.01, 1.0) == "deteriorating"
    assert direction_label(None, 1.0) == "flat"
    assert direction_label(0.1 + 0.2 - 0.2, 0.1) == "flat"  # float noise at the edge
    labels = {"up": "steepening", "down": "flattening", "flat": "flat"}
    assert direction_label(0.2, 0.1, labels) == "steepening"


def _valid_signal(**overrides) -> dict:
    sig = {
        "indicator": "Test",
        "region": "US",
        "type": "leading",
        "as_of": "2026-06-01",
        "level": 50.0,
        "change": 0.5,
        "zscore": None,
        "direction": "improving",
        "regime": "Expansion",
        "market_read": "One sentence.",
    }
    sig.update(overrides)
    return sig


def test_validate_signal_accepts_valid_and_optional_extreme():
    assert validate_signal(_valid_signal()) == []
    assert validate_signal(_valid_signal(extreme=True)) == []


@pytest.mark.parametrize(
    "override, fragment",
    [
        ({"region": "Mars"}, "region"),
        ({"type": "sideways"}, "type"),
        ({"direction": "steepening"}, "direction"),
        ({"as_of": "June 2026"}, "as_of"),
        ({"level": 50}, "level"),
        ({"extreme": "no"}, "extreme"),
        ({"bogus": 1}, "unexpected"),
    ],
)
def test_validate_signal_flags_problems(override, fragment):
    problems = validate_signal(_valid_signal(**override))
    assert any(fragment in p for p in problems)


def test_validate_signal_missing_key():
    sig = _valid_signal()
    del sig["market_read"]
    assert any("missing" in p for p in validate_signal(sig))


def test_validate_signal_custom_labels():
    labels = {"up": "steepening", "down": "flattening", "flat": "flat"}
    assert validate_signal(_valid_signal(direction="steepening"), labels) == []
    assert (
        validate_signal(_valid_signal(direction="improving"), DEFAULT_DIRECTION_LABELS)
        == []
    )


# ---------- charts ----------


def test_line_chart_with_reference_line():
    fig = charts.line_chart(
        [1, 2],
        [3, 4],
        "s",
        height=400,
        yaxis_title="Y",
        hline=50,
        hline_annotation="note",
    )
    assert fig.data[0].mode == "lines" and fig.data[0].name == "s"
    assert fig.layout.height == 400 and fig.layout.shapes[0].y0 == 50
    assert fig.layout.annotations[0].text == "note"
    assert fig.layout.title.text is None


def test_multi_line_chart_dash_and_mode():
    fig = charts.multi_line_chart(
        [
            {"x": [1], "y": [1], "name": "a", "mode": "lines+markers"},
            {"x": [1], "y": [2], "name": "b", "dash": "dot"},
        ],
        height=300,
        yaxis_title="Y",
        xaxis_type="log",
    )
    assert [t.mode for t in fig.data] == ["lines+markers", "lines"]
    assert fig.data[1].line.dash == "dot" and fig.layout.xaxis.type == "log"


# ---------- loaders ----------


def test_parse_treasury_curve_ignores_header_case():
    # Treasury's real-yield CSV uses "10 YR"; the nominal CSV uses "10 Yr".
    raw = pd.DataFrame(
        {"Date": ["10/20/2026"], "5 YR": [2.55], "10 YR": [2.77], "1.5 Month": [3.9]}
    )
    out = parse_treasury_curve(raw, {"5 Yr": "5yr TIPS", "10 Yr": "10yr TIPS"})
    assert list(out.columns) == ["Date", "5yr TIPS", "10yr TIPS"]
    assert out["Date"].iloc[0] == pd.Timestamp("2026-10-20")
    assert out["10yr TIPS"].iloc[0] == 2.77
