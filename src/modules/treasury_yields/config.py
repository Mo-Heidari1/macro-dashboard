"""
Treasury Yields & Curve — series, constants, thresholds and labels.
Calculations read everything from here; nothing is hardcoded there.
"""

# ---------- data ----------
HISTORY_FILE = "yields_history.csv"
LICENCE = "P"  # public data: the committed file is the full history, not a sample
SOURCE = (
    "U.S. Department of the Treasury, daily par yield curve rates (nominal and real); "
    "Federal Reserve Bank of St. Louis, FRED series EFFR (effective Fed Funds rate)"
)

TENOR_COLS = [
    "Fed Funds", "1mo", "3mo", "6mo", "1yr", "2yr", "3yr", "5yr", "7yr",
    "10yr", "20yr", "30yr", "5yr TIPS", "7yr TIPS", "10yr TIPS",
    "20yr TIPS", "30yr TIPS",
]

NOMINAL_TENORS = ["1mo", "3mo", "6mo", "1yr", "2yr", "3yr", "5yr", "7yr",
                  "10yr", "20yr", "30yr"]
TIPS_TENORS = ["5yr TIPS", "7yr TIPS", "10yr TIPS", "20yr TIPS", "30yr TIPS"]

# Maturity (in years) used for x-axis positioning on the curve chart
MATURITY_YEARS = {
    "1mo": 1/12, "3mo": 3/12, "6mo": 6/12, "1yr": 1, "2yr": 2, "3yr": 3,
    "5yr": 5, "7yr": 7, "10yr": 10, "20yr": 20, "30yr": 30,
    "5yr TIPS": 5, "7yr TIPS": 7, "10yr TIPS": 10, "20yr TIPS": 20,
    "30yr TIPS": 30,
}

# Nominal/TIPS pairs used for breakeven (implied) inflation
BREAKEVEN_PAIRS = [("5yr", "5yr TIPS"), ("7yr", "7yr TIPS"),
                   ("10yr", "10yr TIPS"), ("20yr", "20yr TIPS")]

# Row offsets matching the source workbook's HLOOKUP column indices.
# Calibrated for WEEKLY rows (1/4/13/52 weeks).
OFFSET_WOW = 1
OFFSET_MOM = 4
OFFSET_QOQ = 13
OFFSET_YOY = 52

# ---------- live sources ----------
# Treasury.gov CSV headers -> tenor names. Verified against a live pull on
# 2026-09-03 (headers include "1.5 Month", which isn't tracked here).
NOMINAL_COL_MAP = {
    "1 Mo": "1mo", "3 Mo": "3mo", "6 Mo": "6mo", "1 Yr": "1yr", "2 Yr": "2yr",
    "3 Yr": "3yr", "5 Yr": "5yr", "7 Yr": "7yr", "10 Yr": "10yr",
    "20 Yr": "20yr", "30 Yr": "30yr",
}
TIPS_COL_MAP = {
    "5 Yr": "5yr TIPS", "7 Yr": "7yr TIPS", "10 Yr": "10yr TIPS",
    "20 Yr": "20yr TIPS", "30 Yr": "30yr TIPS",
}
FED_FUNDS_SERIES = "EFFR"
FED_FUNDS_START = "1954-01-01"

# ---------- signal ----------
INDICATOR = "US Treasury 2s10s Curve"
REGION = "US"
TYPE = "leading"
SIGNAL_SHORT = "2yr"
SIGNAL_LONG = "10yr"

CHANGE_LOOKBACK_DAYS = 28       # change measured vs the last reading on or before as_of - 28d
DIRECTION_BAND_PP = 0.10        # 2s10s moves within ±10bp over the lookback count as flat
DIRECTION_LABELS = {"up": "steepening", "down": "flattening", "flat": "flat"}

ZSCORE_YEARS = 10               # trailing window for the z-score
ZSCORE_RESAMPLE = "W-SUN"       # weekly, matching the historical Sunday-dated rows
ZSCORE_MIN_PERIODS = 52

# Curve regime = direction of the 2s10s move x direction of the overall
# yield level (mean change of the 2yr and 10yr). "bull" = yields falling,
# "bear" = yields rising.
REGIME_RANGE_BOUND = "range-bound"
REGIME_LABELS = ["bull steepener", "bear steepener", "bull flattener", "bear flattener",
                 REGIME_RANGE_BOUND]

MARKET_READ = {
    "bull steepener": (
        "Front-end yields are falling faster than the long end, usually as markets price Fed "
        "easing: supportive for duration, and typically accompanied by a softer USD and a "
        "weaker growth outlook."
    ),
    "bear steepener": (
        "Long-end yields are rising faster than the front end, pointing to higher term premium "
        "or inflation and supply concerns: a headwind for long-duration bonds and equities."
    ),
    "bull flattener": (
        "Long-end yields are falling faster than the front end, consistent with lower growth or "
        "inflation expectations: supportive for duration, a caution flag for cyclicals."
    ),
    "bear flattener": (
        "Front-end yields are rising faster than the long end, usually as markets price a more "
        "hawkish Fed: tighter financial conditions that tend to support the USD."
    ),
    REGIME_RANGE_BOUND: (
        "The 2s10s spread has moved less than 10bp over four weeks, so the curve is giving no "
        "fresh directional signal for rates or equities."
    ),
}
