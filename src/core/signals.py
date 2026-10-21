"""
Standard signal schema shared by every module's get_signal(), so Home.py can
build one regime scorecard across modules (see CLAUDE.md, "Signal
convention").

Direction labels default to improving / deteriorating / flat; a module may
override them in its config.py (e.g. steepening / flattening / flat for the
yield curve) via DIRECTION_LABELS = {"up": ..., "down": ..., "flat": ...}.
"""

from typing import TypedDict

REGIONS = ("US", "EU", "China", "Global")
TYPES = ("leading", "coincident", "lagging")
DEFAULT_DIRECTION_LABELS = {"up": "improving", "down": "deteriorating", "flat": "flat"}

ZSCORE_NA_LABEL = "n/a: needs 10y history"

REQUIRED_KEYS = (
    "indicator",
    "region",
    "type",
    "as_of",
    "level",
    "change",
    "zscore",
    "direction",
    "regime",
    "market_read",
)
OPTIONAL_KEYS = ("extreme",)


class Signal(TypedDict, total=False):
    """One module's current reading, in the shared scorecard format."""

    indicator: str
    region: str
    type: str
    as_of: str
    level: float
    change: float | None
    zscore: float | None
    direction: str
    regime: str
    market_read: str
    extreme: bool


def direction_label(
    change: float | None, band: float, labels: dict | None = None
) -> str:
    """
    Map a change onto up / down / flat labels. Moves strictly larger than
    `band` in either direction count; anything within ±band is flat.
    """
    labels = labels or DEFAULT_DIRECTION_LABELS
    if change is None:
        return labels["flat"]
    change = round(change, 6)  # avoid float noise deciding a band edge
    if change > band:
        return labels["up"]
    if change < -band:
        return labels["down"]
    return labels["flat"]


def format_zscore(zscore: float | None) -> str:
    """Z-score for display: 2 dp with sign, or ZSCORE_NA_LABEL when the
    module had too little history to compute one (e.g. on sample data)."""
    return ZSCORE_NA_LABEL if zscore is None else f"{zscore:+.2f}"


def validate_signal(
    signal: dict,
    direction_labels: dict | None = None,
    regime_labels: list | None = None,
) -> list[str]:
    """Return a list of schema problems with `signal` (empty list = valid)."""
    problems = []
    missing = [k for k in REQUIRED_KEYS if k not in signal]
    if missing:
        problems.append(f"missing keys: {missing}")
    extra = [k for k in signal if k not in REQUIRED_KEYS + OPTIONAL_KEYS]
    if extra:
        problems.append(f"unexpected keys: {extra}")
    if missing:
        return problems

    if signal["region"] not in REGIONS:
        problems.append(f"region {signal['region']!r} not in {REGIONS}")
    if signal["type"] not in TYPES:
        problems.append(f"type {signal['type']!r} not in {TYPES}")
    labels = (direction_labels or DEFAULT_DIRECTION_LABELS).values()
    if signal["direction"] not in labels:
        problems.append(f"direction {signal['direction']!r} not in {list(labels)}")
    if regime_labels is not None and signal["regime"] not in regime_labels:
        problems.append(f"regime {signal['regime']!r} not in {regime_labels}")
    if not isinstance(signal["as_of"], str) or len(signal["as_of"]) != 10:
        problems.append("as_of must be an ISO date string (YYYY-MM-DD)")
    if not isinstance(signal["level"], float):
        problems.append("level must be a float")
    for key in ("change", "zscore"):
        if signal[key] is not None and not isinstance(signal[key], float):
            problems.append(f"{key} must be a float or None")
    for key in ("indicator", "regime", "market_read"):
        if not isinstance(signal[key], str) or not signal[key]:
            problems.append(f"{key} must be a non-empty string")
    if "extreme" in signal and not isinstance(signal["extreme"], bool):
        problems.append("extreme must be a bool")
    return problems
