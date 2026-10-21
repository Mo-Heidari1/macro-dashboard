"""
Build the committed ISM sample in data/sample/ from the full local history.

    python scripts/build_ism_sample.py

ISM data is proprietary, so the public repo carries only:
- ism_history.csv: the last SAMPLE_MONTHS of the real headline PMI (as
  published by ISM), plus SYNTHETIC sub-index columns.
- ism_sectors.csv: SYNTHETIC industry rankings for the last
  SAMPLE_SECTOR_MONTHS months.

The synthetic values are illustrative only. Each sub-index follows the real
headline PMI plus a fixed offset and seeded noise, so the charts behave
plausibly, but none of those numbers is an ISM figure. The page labels them
"illustrative data". Output is deterministic (fixed seed).
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import paths  # noqa: E402
from src.modules.ism_manufacturing import config as cfg  # noqa: E402

# Illustrative offsets from the headline PMI (not estimated from ISM data).
SYNTHETIC_OFFSETS = {
    "New Orders": 1.5, "Production": 1.0, "Employment": -2.0, "Deliveries": 1.0,
    "Inventories": -1.5, "Customer Inventories": -7.0, "Prices": 12.0,
    "Order Backlog": -3.0, "Exports": -2.0, "Imports": 0.5,
}
NOISE_SD = 1.5
SECTOR_SCORE_RANGE = (-17, 17)


def synthetic_history(real: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Real Date + PMI columns, plus seeded synthetic sub-index columns."""
    out = real[["Date"] + cfg.SAMPLE_REAL_COLUMNS].copy()
    for col in cfg.SUBINDEX_COLS:
        if col in cfg.SAMPLE_REAL_COLUMNS:
            continue
        noise = pd.Series(rng.normal(0, NOISE_SD, len(out))).rolling(2, min_periods=1).mean()
        out[col] = (out["PMI"] + SYNTHETIC_OFFSETS[col] + noise.values).clip(0, 100).round(1)
    return out[["Date"] + cfg.SUBINDEX_COLS]


def synthetic_sectors(industries: list[str], categories: list[str], months: list,
                      rng: np.random.Generator) -> pd.DataFrame:
    """Seeded synthetic Category/Date/Industry/Direction/Score rows."""
    records = []
    for category in categories:
        for industry in industries:
            for month in months:
                score = int(rng.integers(SECTOR_SCORE_RANGE[0], SECTOR_SCORE_RANGE[1] + 1))
                direction = "Growth" if score > 0 else "Contraction" if score < 0 else "Neutral"
                records.append((category, month, industry, direction, score))
    return pd.DataFrame(records, columns=["Category", "Date", "Industry", "Direction", "Score"])


def main():
    rng = np.random.default_rng(cfg.SAMPLE_SEED)

    history = pd.read_csv(paths.local_path(cfg.HISTORY_FILE), parse_dates=["Date"])
    history = history.sort_values("Date").dropna(subset=["PMI"]).tail(cfg.SAMPLE_MONTHS)
    sample = synthetic_history(history.reset_index(drop=True), rng)

    sectors = pd.read_csv(paths.local_path(cfg.SECTORS_FILE), parse_dates=["Date"])
    months = list(sample["Date"].tail(cfg.SAMPLE_SECTOR_MONTHS))
    sector_sample = synthetic_sectors(
        sorted(sectors["Industry"].unique()), list(sectors["Category"].unique()), months, rng
    )

    os.makedirs(paths.DATA_SAMPLE, exist_ok=True)
    sample.to_csv(paths.sample_path(cfg.HISTORY_FILE), index=False)
    sector_sample.to_csv(paths.sample_path(cfg.SECTORS_FILE), index=False)
    print(f"Wrote {len(sample)} months ({sample['Date'].min():%Y-%m} to {sample['Date'].max():%Y-%m}) "
          f"and {len(sector_sample)} synthetic sector rows to {paths.DATA_SAMPLE}")


if __name__ == "__main__":
    main()
