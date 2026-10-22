"""
Validate the stored yield history against Treasury.gov, year by year.

    python scripts/validate_yields.py --out <folder> [--start 1990] [--end 2026]
        [--cache <folder>] [--since YYYY-MM-DD]

For every year, downloads the nominal and real (TIPS) par yield curves
(throttled, with retries), aligns them to the history's dates with
align_to_history(), and compares each tenor at 2 dp. Writes to --out:
- validation_yields_by_year.csv    one row per year x curve x tenor
- validation_yields_mismatches.csv every mismatching cell
- validation_yields_summary.txt    totals and mismatches grouped by tenor

Fed Funds (FRED) is not covered: it needs an API key.
"""

import argparse
import io
import os
import sys
import time

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.loaders import (
    TREASURY_NOMINAL_URL,
    TREASURY_TIPS_URL,
    parse_treasury_curve,
)
from src.modules.treasury_yields import config as cfg
from src.modules.treasury_yields.calculations import align_to_history, load_history

PAUSE_SECONDS = 3
RETRIES = 4
TIMEOUT_SECONDS = 60
FIRST_TIPS_YEAR = 2003


def download(url: str, cache_file: str | None) -> pd.DataFrame:
    """GET a Treasury CSV with retries and backoff, optionally cached on disk."""
    if cache_file and os.path.exists(cache_file):
        return pd.read_csv(cache_file)
    for attempt in range(1, RETRIES + 1):
        try:
            resp = requests.get(url, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            break
        except requests.RequestException:
            if attempt == RETRIES:
                raise
            time.sleep(PAUSE_SECONDS * 2**attempt)
    time.sleep(PAUSE_SECONDS)
    if cache_file:
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(resp.text)
    return pd.read_csv(io.StringIO(resp.text))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--start", type=int, default=1990)
    parser.add_argument("--end", type=int, default=pd.Timestamp.today().year)
    parser.add_argument("--cache", default=None)
    parser.add_argument(
        "--since", default=None, help="only check rows dated after this (YYYY-MM-DD)"
    )
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    if args.cache:
        os.makedirs(args.cache, exist_ok=True)

    history = load_history()
    by_year, mismatches = [], []
    previous = {}  # prior year's observations, for early-January Sunday rows
    for year in range(args.start, args.end + 1):
        rows = history[history["Date"].dt.year == year]
        if args.since:
            rows = rows[rows["Date"] > pd.Timestamp(args.since)]
        for curve, url, col_map in (
            ("nominal", TREASURY_NOMINAL_URL, cfg.NOMINAL_COL_MAP),
            ("TIPS", TREASURY_TIPS_URL, cfg.TIPS_COL_MAP),
        ):
            if curve == "TIPS" and year < FIRST_TIPS_YEAR:
                continue
            cache = (
                os.path.join(args.cache, f"{curve}_{year}.csv") if args.cache else None
            )
            try:
                live = parse_treasury_curve(
                    download(url.format(year=year), cache), col_map
                )
            except (
                requests.RequestException,
                ValueError,
                KeyError,
            ) as exc:  # report, carry on
                by_year.append((year, curve, "ERROR", 0, 0, None, str(exc)[:80]))
                continue
            # A Sunday on Jan 1-3 carries the prior year's last close.
            both_years = pd.concat([previous.get(curve, live.iloc[:0]), live])
            previous[curve] = live
            aligned = align_to_history(rows["Date"], both_years).set_index("Date")
            stored = rows.set_index("Date")
            for col in [c for c in col_map.values() if c in aligned.columns]:
                both = aligned[col].notna() & stored[col].notna()
                diff = (stored.loc[both, col] - aligned.loc[both, col]).round(4)
                bad = diff.abs() > 0.005
                by_year.append(
                    (
                        year,
                        curve,
                        col,
                        int(both.sum()),
                        int(bad.sum()),
                        float(diff.abs().max()) if both.any() else None,
                        "",
                    )
                )
                for date in diff[bad].index:
                    mismatches.append(
                        (
                            date.date(),
                            date.day_name(),
                            col,
                            stored.at[date, col],
                            aligned.at[date, col],
                        )
                    )
            print(f"{year} {curve}: done", flush=True)

    table = pd.DataFrame(
        by_year,
        columns=[
            "year",
            "curve",
            "tenor",
            "compared",
            "mismatches",
            "max_abs_diff",
            "error",
        ],
    )
    detail = pd.DataFrame(
        mismatches, columns=["date", "weekday", "tenor", "stored", "treasury"]
    )
    table.to_csv(os.path.join(args.out, "validation_yields_by_year.csv"), index=False)
    detail.to_csv(
        os.path.join(args.out, "validation_yields_mismatches.csv"), index=False
    )

    lines = [
        (
            f"Yields history vs Treasury.gov, {args.start}-{args.end} "
            f"(run {pd.Timestamp.now():%Y-%m-%d %H:%M})"
        ),
        "",
        table.groupby("curve")[["compared", "mismatches"]].sum().to_string(),
        "",
        "Mismatches by tenor:",
        (
            detail.groupby("tenor")
            .agg(cells=("date", "size"), first=("date", "min"), last=("date", "max"))
            .to_string()
            if not detail.empty
            else "none"
        ),
        "",
        "Errors:",
        table[table["error"] != ""].to_string(index=False)
        if (table["error"] != "").any()
        else "none",
    ]
    with open(
        os.path.join(args.out, "validation_yields_summary.txt"), "w", encoding="utf-8"
    ) as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
