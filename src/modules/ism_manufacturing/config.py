"""
ISM Manufacturing — series, constants, thresholds and labels.
Calculations read everything from here; nothing is hardcoded there.
"""

# ---------- data ----------
HISTORY_FILE = "ism_history.csv"
SECTORS_FILE = "ism_sectors.csv"
SOURCE_WORKBOOK = "ISM_Manufacturing_Index_Updated.xlsx"
LICENCE = "R"  # proprietary: full history in data/local/, sample in data/sample/
SOURCE = "Institute for Supply Management (ISM), Manufacturing ISM Report On Business"

# Columns in the committed sample that are real ISM figures. Every other
# sample column (and the whole sectors sample) is synthetic, illustrative data.
SAMPLE_REAL_COLUMNS = ["PMI"]
SAMPLE_MONTHS = 36
SAMPLE_SECTOR_MONTHS = 3
SAMPLE_SEED = 20260630

# All 11 published series, headline first, in the same order as the
# workbook's Heat Map Summary sheet.
SUBINDEX_COLS = [
    "PMI",
    "New Orders",
    "Production",
    "Employment",
    "Deliveries",
    "Inventories",
    "Customer Inventories",
    "Prices",
    "Order Backlog",
    "Exports",
    "Imports",
]

# ISM's official headline PMI composite weights.
PMI_WEIGHTS = {
    "New Orders": 0.30,
    "Production": 0.25,
    "Employment": 0.20,
    "Deliveries": 0.15,
    "Inventories": 0.10,
}

# 50.0 separates expansion from contraction for every ISM diffusion index.
EXPANSION_THRESHOLD = 50.0
STATUS_LABELS = {
    "above": "Growth",
    "below": "Contraction",
    "at": "Neutral",
    "missing": "N/A",
}

# Summary-table change windows in calendar months.
SUMMARY_LOOKBACK_MONTHS = {"MoM": 1, "YoY": 12}

# ---------- signal ----------
INDICATOR = "ISM Manufacturing PMI"
REGION = "US"
TYPE = "leading"
SIGNAL_COL = "PMI"

DIRECTION_WINDOW = 3  # 3-month average vs the prior 3-month average
DIRECTION_BAND = 1.0  # averages within ±1.0 point of each other count as flat
DIRECTION_LABELS = {"up": "improving", "down": "deteriorating", "flat": "flat"}

ZSCORE_WINDOW_MONTHS = 120  # trailing 10 years
ZSCORE_MIN_PERIODS = 36

# Regime quadrant = PMI level vs 50 x momentum (sign of the 3m-vs-prior-3m
# change; the ±1.0 band applies only to the direction label). A level of
# exactly 50 and a change of exactly 0 count as "above" and "rising".
REGIME_LEVEL = 50.0
REGIMES = {
    ("above", "rising"): "Expansion",
    ("above", "falling"): "Slowdown",
    ("below", "falling"): "Contraction",
    ("below", "rising"): "Recovery",
}
REGIME_LABELS = list(REGIMES.values())

EXTREME_HIGH = 55.0  # extreme = level strictly above 55 or below 45
EXTREME_LOW = 45.0

MARKET_READ = {
    "Expansion": (
        "Factory activity is growing and gaining momentum: supportive for cyclical equities and "
        "industrial commodities, and a source of upward pressure on yields."
    ),
    "Slowdown": (
        "Factory activity is still growing but losing momentum, a late-cycle mix in which "
        "yields tend to peak and defensives start to outperform cyclicals."
    ),
    "Contraction": (
        "Factory activity is shrinking and momentum is still worsening: supportive for duration "
        "and defensives, a headwind for cyclicals and commodities."
    ),
    "Recovery": (
        "Factory activity is still contracting but momentum has turned up, an early-cycle signal "
        "that tends to favour cyclicals and a steeper yield curve."
    ),
}
