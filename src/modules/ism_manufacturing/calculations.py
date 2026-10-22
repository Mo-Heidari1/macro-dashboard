"""
ISM Manufacturing — calculation layer.

Replicates the logic from ISM_Manufacturing_Index_Updated.xlsx:
- Summary: current value + MoM/YoY change per sub-index
- classify(): growth (>50) / contraction (<50) / neutral (=50) — the
  expansion/contraction convention that applies to every diffusion index
  in this workbook, not just the headline PMI.
- heatmap_data(): the Heat Map Summary sheet's shape (months x sub-indices),
  ready for a diverging-colorscale Plotly heatmap centered on 50.
- sector_rankings(): growth/contraction/score per industry for a given
  month and category, from the Sectors sheet.
- recompute_pmi_from_subindices(): reconstructs headline PMI from its five
  weighted components, as a validation + "how the composite works" check.
and adds get_signal(): the headline PMI reading in the shared scorecard schema.

Data cadence: MONTHLY (one row per month) — unlike the weekly yields data,
there's no WoW/QoQ distinction here, so only MoM and YoY are computed.
"""

import pandas as pd

from src.core import paths
from src.core.signals import direction_label
from src.core.transforms import (
    change_over,
    last_complete_row,
    last_valid,
    rolling_mean_change,
    zscore_last,
)
from src.modules.ism_manufacturing import config as cfg


def load_ism_history(path: str | None = None) -> pd.DataFrame:
    """Load the monthly ISM sub-index series (data/local, else data/sample), sorted by date."""
    if path is None:
        path, _ = paths.resolve_data_file(cfg.HISTORY_FILE)
    df = pd.read_csv(path, parse_dates=["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def load_ism_sectors(path: str | None = None) -> pd.DataFrame:
    """Load the long-format sector growth/contraction data (Category, Date, Industry, Direction, Score)."""
    if path is None:
        path, _ = paths.resolve_data_file(cfg.SECTORS_FILE)
    return pd.read_csv(path, parse_dates=["Date"])


def classify(value) -> str:
    """50.0 is the expansion/contraction threshold for every diffusion index here."""
    if pd.isna(value):
        return cfg.STATUS_LABELS["missing"]
    if value > cfg.EXPANSION_THRESHOLD:
        return cfg.STATUS_LABELS["above"]
    if value < cfg.EXPANSION_THRESHOLD:
        return cfg.STATUS_LABELS["below"]
    return cfg.STATUS_LABELS["at"]


def summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Current value, classification, and MoM/YoY change for every sub-index,
    each from its own last published month (dated in "As of").
    """
    out = []
    for col in cfg.SUBINDEX_COLS:
        last = last_valid(df, col)
        cur = last[1] if last else None
        out.append(
            {
                "Sub-Index": col,
                "As of": last[0].strftime("%Y-%m-%d") if last else None,
                "Current": cur,
                "Status": classify(cur),
                **{
                    label: change_over(df, col, pd.DateOffset(months=months))
                    for label, months in cfg.SUMMARY_LOOKBACK_MONTHS.items()
                },
            }
        )
    return pd.DataFrame(out)


def heatmap_data(df: pd.DataFrame, n_months: int | None = None) -> pd.DataFrame:
    """
    Months x sub-indices matrix (Date-indexed), matching the Heat Map
    Summary sheet's shape. Feed straight into a Plotly go.Heatmap with a
    diverging colorscale centered on 50. Pass n_months to limit to the
    most recent N months (default: all).
    """
    out = df.set_index("Date")[cfg.SUBINDEX_COLS]
    if n_months is not None:
        out = out.tail(n_months)
    return out


def sector_rankings(
    sectors_df: pd.DataFrame, date, category: str = "PMI"
) -> pd.DataFrame:
    """
    Growth/contraction/score per industry for a given month and category
    (headline 'PMI' or one of the sub-indices ISM publishes a breakdown
    for: New Orders, Production, Employment, Deliveries, Inventories,
    Customer Inventories). Sorted by Score descending (strongest growth first),
    ties broken alphabetically by Industry so the order is deterministic.
    """
    date = pd.Timestamp(date)
    out = sectors_df[
        (sectors_df["Date"] == date) & (sectors_df["Category"] == category)
    ]
    return (
        out[["Industry", "Direction", "Score"]]
        .sort_values(["Score", "Industry"], ascending=[False, True], kind="stable")
        .reset_index(drop=True)
    )


def recompute_pmi_from_subindices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reconstructs headline PMI from its five weighted components
    (New Orders 30%, Production 25%, Employment 20%, Supplier Deliveries
    15%, Inventories 10%) and compares to the published headline PMI.

    This won't match exactly — ISM applies seasonal adjustment on top of
    the simple weighted sum — but it's close, and shows how the composite
    is built.
    """
    out = df[["Date", "PMI"]].copy()
    out["Recomputed PMI"] = sum(df[col] * w for col, w in cfg.PMI_WEIGHTS.items())
    out["Recomputed PMI"] = out["Recomputed PMI"].round(2)
    out["Diff"] = (out["PMI"] - out["Recomputed PMI"]).round(2)
    return out


def pmi_regime(level: float, trend: str) -> str:
    """Quadrant regime from the PMI level vs 50 and the momentum trend."""
    side = "above" if level >= cfg.REGIME_LEVEL else "below"
    return cfg.REGIMES[(side, trend)]


def regime_history(df: pd.DataFrame) -> pd.DataFrame:
    """
    Month-by-month PMI regime with hysteresis: Date, level, momentum (3m
    average vs prior 3m average), stable (momentum inside ±DIRECTION_BAND),
    trend and regime. A stable month keeps the prior month's trend.
    """
    col = cfg.SIGNAL_COL
    out = df[["Date", col]].dropna().reset_index(drop=True)
    out = out.rename(columns={col: "level"})
    out["momentum"] = rolling_mean_change(out["level"], cfg.DIRECTION_WINDOW).round(4)
    stables, trends, prior = [], [], None
    for m in out["momentum"]:
        stable = bool(pd.isna(m) or abs(m) <= cfg.DIRECTION_BAND)
        if not stable:
            trend = "rising" if m > 0 else "falling"
        elif prior is not None:
            trend = prior
        else:
            trend = "rising" if pd.isna(m) or m >= 0 else "falling"
        stables.append(stable)
        trends.append(trend)
        if not pd.isna(m):  # months before momentum exists don't set a trend
            prior = trend
    out["stable"] = stables
    out["trend"] = trends
    out["regime"] = [pmi_regime(lv, t) for lv, t in zip(out["level"], out["trend"])]
    return out


def peak_note(
    dates: pd.Series, values: pd.Series, trend: str, stable: bool
) -> str | None:
    """
    Sentence noting that the latest value is at least PEAK_NOTE_MIN_DROP
    below its high of the last PEAK_WINDOW_MONTHS observations (e.g.
    "3-month average rising, but off the July peak (55.6)."). None for a
    new high or a smaller pullback.
    """
    window = pd.Series(values.to_numpy(), index=pd.to_datetime(dates.to_numpy()))
    window = window.dropna().tail(cfg.PEAK_WINDOW_MONTHS)
    if window.empty:
        return None
    peak = window.max()
    drop = round(peak - window.iloc[-1], 6)  # avoid float noise at the cut
    if drop < cfg.PEAK_NOTE_MIN_DROP:
        return None
    peak_date = window[window == peak].index[-1]  # most recent if tied
    as_of = window.index[-1]
    month = f"{peak_date:%B}" if peak_date.year == as_of.year else f"{peak_date:%B %Y}"
    template = cfg.PEAK_NOTES["stable" if stable else trend]
    return template.format(month=month, peak=peak)


def get_signal(df: pd.DataFrame) -> dict:
    """
    Headline PMI reading in the shared signal schema, as of the last month
    with PMI populated. Change is MoM; direction and regime use the 3-month
    average vs the prior 3-month average, and inside the ±1.0 band the
    regime keeps the prior month's trend (see regime_history); z-score is
    vs the trailing ZSCORE_WINDOW_MONTHS. market_read is prefixed with
    peak_note() when the PMI is below its recent high.
    """
    col = cfg.SIGNAL_COL
    i = last_complete_row(df, [col])
    if i is None:
        raise ValueError(f"No row has {col} populated")
    history = df.iloc[: i + 1]
    series = history[col].dropna()
    level = float(series.iloc[-1])

    change = round(level - float(series.iloc[-2]), 4) if len(series) > 1 else None
    latest = regime_history(history).iloc[-1]
    momentum = None if pd.isna(latest["momentum"]) else float(latest["momentum"])
    z = zscore_last(series.tail(cfg.ZSCORE_WINDOW_MONTHS), cfg.ZSCORE_MIN_PERIODS)

    regime = latest["regime"]
    reads = cfg.MARKET_READ_STABLE if latest["stable"] else cfg.MARKET_READ
    note = peak_note(history["Date"], history[col], latest["trend"], latest["stable"])
    market_read = reads[regime] if note is None else f"{note} {reads[regime]}"
    return {
        "indicator": cfg.INDICATOR,
        "region": cfg.REGION,
        "type": cfg.TYPE,
        "as_of": history["Date"].iloc[-1].strftime("%Y-%m-%d"),
        "level": level,
        "change": change,
        "zscore": None if z is None else round(z, 2),
        "direction": direction_label(
            momentum, cfg.DIRECTION_BAND, cfg.DIRECTION_LABELS
        ),
        "regime": regime,
        "market_read": market_read,
        "extreme": level > cfg.EXTREME_HIGH or level < cfg.EXTREME_LOW,
    }


def merge_months(
    current: pd.DataFrame,
    incoming: pd.DataFrame,
    keys: list[str],
    value_cols: list[str],
    months: list[pd.Timestamp],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Merge a fresh workbook extract into the stored CSV.

    - rows dated in `months` are taken from `incoming` (new or replaced)
    - rows in both: cells the workbook revised (value -> different value,
      or empty -> value) are applied; cells the workbook left empty are kept
    - rows only in `current` are kept; earlier rows only in `incoming` are
      not imported

    Returns (merged, report). The report lists every applied revision and
    every difference not applied: kind is one of "imported", "revised",
    "kept: empty in workbook", "kept: not in workbook",
    "skipped: earlier month not in CSV".
    """
    months = {pd.Timestamp(m) for m in months}
    cur = current.set_index(keys)
    inc = incoming.set_index(keys)
    in_months = inc.index.get_level_values("Date").isin(list(months))
    report = []

    def key_dict(k):
        return dict(zip(keys, k if isinstance(k, tuple) else (k,)))

    for k in inc.index[in_months]:
        report.append(
            {
                **key_dict(k),
                "kind": "imported",
                "column": None,
                "csv": None,
                "workbook": None,
            }
        )

    merged = cur[~cur.index.get_level_values("Date").isin(list(months))].copy()
    for k in merged.index.intersection(inc.index):
        for col in value_cols:
            old, new = merged.at[k, col], inc.at[k, col]
            if pd.isna(new) and pd.isna(old):
                continue
            if pd.isna(new):
                kind = "kept: empty in workbook"
            elif pd.isna(old) or old != new:
                kind = "revised"
                merged.at[k, col] = new
            else:
                continue
            report.append(
                {
                    **key_dict(k),
                    "kind": kind,
                    "column": col,
                    "csv": old,
                    "workbook": new,
                }
            )
    for k in merged.index.difference(inc.index):
        report.append(
            {
                **key_dict(k),
                "kind": "kept: not in workbook",
                "column": None,
                "csv": None,
                "workbook": None,
            }
        )
    earlier_only = inc.index[~in_months].difference(cur.index)
    for k in earlier_only:
        report.append(
            {
                **key_dict(k),
                "kind": "skipped: earlier month not in CSV",
                "column": None,
                "csv": None,
                "workbook": None,
            }
        )

    merged = pd.concat([merged, inc[in_months]]).reset_index()
    # Keep the stored order: non-date keys in order of first appearance
    # (sheet order), then by date.
    rank = {
        col: {
            v: i
            for i, v in enumerate(pd.unique(pd.concat([current[col], incoming[col]])))
        }
        for col in keys
        if col != "Date"
    }
    merged = merged.sort_values(
        keys, key=lambda s: s.map(rank[s.name]) if s.name in rank else s, kind="stable"
    )
    merged = merged[current.columns].reset_index(drop=True)
    cols = keys + ["kind", "column", "csv", "workbook"]
    return merged, pd.DataFrame(report, columns=cols)
