"""
Treasury Yields & Curve — calculation layer.

Replicates the logic from Benchmark_Yields_US-updated.xlsm:
- Summary: current yield + WoW/MoM/QoQ/YoY change per tenor
- Curve Analysis: yield curve (yield vs. maturity) on a given date
- Spread Analysis: spread between two selected tenors over time
- Implied inflation (breakeven): nominal yield minus matching TIPS yield
and adds get_signal(): the 2s10s curve reading in the shared scorecard schema.

Data cadence: WEEKLY snapshots (one row per week) in the source workbook,
so WoW/MoM/QoQ/YoY are offsets of 1/4/13/52 rows, not calendar days.
get_signal() uses calendar-day lookbacks instead, so it is cadence-agnostic.
"""

import pandas as pd

from src.core import paths
from src.core.signals import direction_label
from src.core.transforms import (
    change_at_offset,
    last_complete_row,
    row_on_or_before,
    zscore_last,
)
from src.modules.treasury_yields import config as cfg


def load_history(path: str | None = None) -> pd.DataFrame:
    """Load the historical yield series (data/local, else data/sample), sorted by date."""
    if path is None:
        path, _ = paths.resolve_data_file(cfg.HISTORY_FILE)
    df = pd.read_csv(path, parse_dates=["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Replicates the 'Summary' sheet: current yield and WoW/MoM/QoQ/YoY
    change (in percentage points) for every tenor.
    """
    latest = df.iloc[-1]
    out = []
    for tenor in cfg.TENOR_COLS:
        out.append(
            {
                "Tenor": tenor,
                "Current Yield %": latest[tenor],
                "WoW": change_at_offset(df, tenor, cfg.OFFSET_WOW),
                "MoM": change_at_offset(df, tenor, cfg.OFFSET_MOM),
                "QoQ": change_at_offset(df, tenor, cfg.OFFSET_QOQ),
                "YoY": change_at_offset(df, tenor, cfg.OFFSET_YOY),
            }
        )
    return pd.DataFrame(out)


def implied_inflation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Breakeven inflation = nominal yield - matching-maturity TIPS yield,
    for the tenors where both exist (5/7/10/20yr).

    TIPS data on Treasury.gov sometimes posts a day or more behind nominal
    yields, so the very latest row may have nominal but not-yet-published
    TIPS values. To avoid returning an empty table, this walks backward
    from the latest row until it finds one with at least one complete
    nominal/TIPS pair.
    """
    for i in range(len(df) - 1, -1, -1):
        row = df.iloc[i]
        out = []
        for nom, tips in cfg.BREAKEVEN_PAIRS:
            if pd.notna(row[nom]) and pd.notna(row[tips]):
                out.append(
                    {
                        "Maturity": nom,
                        "Nominal": row[nom],
                        "TIPS": row[tips],
                        "Implied Inflation": round(row[nom] - row[tips], 4),
                    }
                )
        if out:
            return pd.DataFrame(out)

    # No row anywhere has a complete nominal/TIPS pair
    return pd.DataFrame(columns=["Maturity", "Nominal", "TIPS", "Implied Inflation"])


def curve_on_date(
    df: pd.DataFrame, date=None, tenors: list[str] | None = None
) -> pd.DataFrame:
    """
    Yield curve snapshot: yield vs. maturity (years) for a given date
    (defaults to latest). Used to feed the Curve Analysis chart.
    """
    tenors = tenors or cfg.NOMINAL_TENORS
    row = (
        df.iloc[-1]
        if date is None
        else df.loc[df["Date"] == pd.Timestamp(date)].iloc[0]
    )
    out = pd.DataFrame(
        {
            "Tenor": tenors,
            "Maturity (yrs)": [cfg.MATURITY_YEARS[t] for t in tenors],
            "Yield %": [row[t] for t in tenors],
        }
    ).dropna(subset=["Yield %"])
    return out.sort_values("Maturity (yrs)")


def spread_series(df: pd.DataFrame, tenor_a: str, tenor_b: str) -> pd.DataFrame:
    """
    Time series of (tenor_a - tenor_b), e.g. '10yr' vs '1yr' for the
    classic recession-signal spread. Mirrors the Spread Analysis sheet's
    dropdown-driven comparison.
    """
    out = df[["Date", tenor_a, tenor_b]].dropna().copy()
    out["Spread"] = out[tenor_a] - out[tenor_b]
    out = out.rename(columns={tenor_a: f"{tenor_a} Yield", tenor_b: f"{tenor_b} Yield"})
    return out


def curve_regime(
    spread_change: float | None, level_change: float | None, band: float
) -> str:
    """
    Bull/bear steepener/flattener from the change in the curve spread and
    in the overall yield level. Spread moves within ±band are range-bound.
    """
    labels = cfg.DIRECTION_LABELS
    shape = direction_label(spread_change, band, labels)
    if shape == labels["flat"] or level_change is None:
        return cfg.REGIME_RANGE_BOUND
    side = "bear" if level_change > 0 else "bull"
    kind = "steepener" if shape == labels["up"] else "flattener"
    return f"{side} {kind}"


def get_signal(df: pd.DataFrame) -> dict:
    """
    2s10s curve reading in the shared signal schema, as of the last row with
    both the 2yr and 10yr populated. Change is vs the last reading on or
    before as_of - CHANGE_LOOKBACK_DAYS; z-score is vs the trailing
    ZSCORE_YEARS of weekly readings.
    """
    short, long_ = cfg.SIGNAL_SHORT, cfg.SIGNAL_LONG
    i = last_complete_row(df, [short, long_])
    if i is None:
        raise ValueError(f"No row has both {short} and {long_} populated")
    pair = df[["Date", short, long_]].iloc[: i + 1].dropna()
    now = pair.iloc[-1]
    as_of = now["Date"]
    level = float(now[long_] - now[short])

    prior = row_on_or_before(pair, as_of - pd.Timedelta(days=cfg.CHANGE_LOOKBACK_DAYS))
    if prior is None:
        change = level_change = None
    else:
        change = round(level - float(prior[long_] - prior[short]), 4)
        level_change = ((now[short] - prior[short]) + (now[long_] - prior[long_])) / 2

    spread = pair.set_index("Date")[long_] - pair.set_index("Date")[short]
    window = spread.loc[as_of - pd.DateOffset(years=cfg.ZSCORE_YEARS) : as_of]
    weekly = window.resample(cfg.ZSCORE_RESAMPLE).last()
    z = zscore_last(weekly, cfg.ZSCORE_MIN_PERIODS)

    regime = curve_regime(change, level_change, cfg.DIRECTION_BAND_PP)
    return {
        "indicator": cfg.INDICATOR,
        "region": cfg.REGION,
        "type": cfg.TYPE,
        "as_of": as_of.strftime("%Y-%m-%d"),
        "level": round(level, 4),
        "change": change,
        "zscore": None if z is None else round(z, 2),
        "direction": direction_label(
            change, cfg.DIRECTION_BAND_PP, cfg.DIRECTION_LABELS
        ),
        "regime": regime,
        "market_read": cfg.MARKET_READ[regime],
    }
