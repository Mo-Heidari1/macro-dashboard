"""
ISM Manufacturing — series, constants, thresholds and labels.
Calculations read everything from here; nothing is hardcoded there.
"""

# ---------- data ----------
# Committed files in data/sample/ (real data, compiled from ISM's public
# monthly releases). The source workbook stays in data/local/ (git-ignored).
HISTORY_FILE = "ism_history.csv"
SECTORS_FILE = "ism_sectors.csv"
SOURCE_WORKBOOK = "ISM_Manufacturing_Index_Updated2.xlsx"  # through Sep 2026
LICENCE = "A"  # committed from public releases, with attribution
SOURCE = "ISM Manufacturing Report On Business, compiled from public monthly releases"

# Only sector rankings from this month on are committed; older rows, industry
# comment text and workbooks never are.
SECTORS_START = "2026-04-01"

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
ZSCORE_MIN_PERIODS = 120  # a full 10 years

# Regime quadrant = PMI level vs 50 x momentum trend, with hysteresis:
# - momentum outside ±DIRECTION_BAND: trend = sign of the 3m-vs-prior-3m change
# - momentum inside the band ("momentum stable"): the prior month's trend
#   carries forward, so the regime only changes if the level crosses 50
# - before any month has left the band, a stable month takes the sign of its
#   change (0 counts as rising). A level of exactly 50 counts as "above".
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

# Used instead of MARKET_READ when momentum is inside the band.
MARKET_READ_STABLE = {
    "Expansion": (
        "Momentum stable: factory activity is above 50 and the 3-month average has moved less "
        "than a point, so the expansion read holds without adding a fresh signal for cyclicals "
        "or yields."
    ),
    "Slowdown": (
        "Momentum stable: factory activity is above 50 and the last decisive move was down, so "
        "the late-cycle read holds until momentum turns."
    ),
    "Contraction": (
        "Momentum stable: factory activity is below 50 and the last decisive move was down, so "
        "the defensive read for duration and cyclicals holds until momentum turns."
    ),
    "Recovery": (
        "Momentum stable: factory activity is below 50 and the last decisive move was up, so "
        "the early-cycle read holds while momentum stays positive."
    ),
}

# Prefix to market_read when the latest PMI is at least PEAK_NOTE_MIN_DROP
# points below its high of the last PEAK_WINDOW_MONTHS months (current month
# included). Text only: regime, direction and every threshold above are
# unaffected.
PEAK_WINDOW_MONTHS = 3
PEAK_NOTE_MIN_DROP = 1.0  # matches DIRECTION_BAND; smaller pullbacks get no note
PEAK_NOTES = {
    "rising": "3-month average rising, but off the {month} peak ({peak:.1f}).",
    "falling": "3-month average falling, and off the {month} peak ({peak:.1f}).",
    "stable": "Off the {month} peak ({peak:.1f}).",
}
