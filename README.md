# Macro Dashboard

A multi-page Streamlit app tracking macro indicators for the trading course:
US Treasury benchmark yields today, ISM Manufacturing PMI now added, more
indicators later. Each indicator is isolated in its own calculation module
and its own page — matching how the source Excel workbooks are already
separated one-per-indicator — while sharing one running dashboard.

## Structure
- `Home.py` — landing page: cross-indicator summary (current 10yr yield,
  2s10s spread, headline PMI) and a PMI-vs-10yr-yield overlay chart.
- `pages/1_Treasury_Yields.py` — Summary, Curve Analysis, Spread Analysis,
  Implied Inflation tabs (unchanged from the original single-page app).
- `pages/2_ISM_Manufacturing.py` — Overview, Sub-Index Heatmap, Sector
  Breakdown, Composite Check, and a manual monthly-update form.
- `calculations.py` / `ism_calculations.py` — pandas calculation layers,
  one per indicator, both validated line-by-line against their source
  Excel workbooks' cached formula results.
- `live_sources.py` / `update_data.py` — Treasury.gov + FRED fetch
  functions and the CLI that appends fresh yields data.
- `update_ism.py` — CLI for the ISM manual-update workflow (see below).
- `scripts/extract_ism.py` — one-time extraction of
  `ISM_Manufacturing_Index_Updated.xlsx` into `ism_history.csv` /
  `ism_sectors.csv`. Re-run only if the source workbook is replaced.
- `yields_history.csv` / `ism_history.csv` / `ism_sectors.csv` — the
  persisted data the app reads. CSV, not pickle — an earlier pickle-based
  version broke across machines on a numpy/pandas version mismatch when
  unpickling `datetime64[us]` columns.

## Run it
```
pip install -r requirements.txt
streamlit run Home.py
```

## Keeping yields current
`live_sources.py` has working fetch functions for:
- Nominal yields (Treasury.gov daily par yield curve)
- TIPS/real yields (Treasury.gov daily par real yield curve)
- Fed Funds effective rate (FRED API — needs a free key: https://fred.stlouisfed.org/docs/api/api_key.html)

```
python update_data.py YOUR_FRED_API_KEY
```
Pulls current data and appends new rows to `yields_history.csv`, deduping
on Date.

Note: Treasury.gov data is DAILY, but this dashboard tracks WEEKLY
snapshots. The WoW/MoM/QoQ/YoY row-offsets in `calculations.py` (1/4/13/52)
are calibrated to weekly data.

## Keeping ISM current
**There is no free, terms-compliant API for ISM's data** — it's a
proprietary, licensed report (confirmed in the source workbook's own NOTES
sheet, which documents the same manual process). You still have to type in
the numbers yourself each month from ismworld.org's Report on Business —
this dashboard just makes that a 30-second task instead of a multi-sheet
Excel edit. Two ways to do it, pick whichever is more convenient:

1. **In the app** — open the ISM Manufacturing page → "Add This Month's
   Data" tab, fill in whichever sub-indices have been published, submit.
2. **CLI** —
   ```
   python update_ism.py --date 2026-07-01 --pmi 53.9 --new-orders 58.0 \
       --production 54.0 --employment 51.0 --deliveries 55.0 \
       --inventories 50.0 --customer-inventories 44.0 --prices 72.0 \
       --order-backlog 52.0 --exports 49.5 --imports 53.5
   ```
   or run `python update_ism.py` with no args for interactive prompts.

Both paths compute `Change`/MoM automatically, dedupe on Date (re-running
for the same month overwrites rather than duplicates), and leave every
other month untouched.
