# Data

Loaders read `data/local/<file>` if it exists, otherwise `data/sample/<file>`
(`src/core/paths.py`). All stored data is CSV.

| File | Folder | Source | Licence | Frequency | Notes |
|---|---|---|---|---|---|
| `yields_history.csv` | `sample/` (committed, full history) | U.S. Department of the Treasury, daily par yield curve rates (nominal and real); FRED series EFFR (effective Fed Funds rate) | Public | Weekly (Sunday-dated, carrying the prior Friday's close) to 2025; daily from 2026-01-01 | Refreshed with `scripts/update_yields.py`. Nominal values checked against Treasury.gov. |
| `ism_history.csv` | `local/` (git-ignored) | Institute for Supply Management, Manufacturing ISM Report On Business: headline PMI and 10 sub-indices | Restricted | Monthly, 1948 onwards (sub-index start dates vary) | Built from the source workbook by `scripts/extract_ism.py`; new months added by hand with `scripts/update_ism.py` or the page form. |
| `ism_sectors.csv` | `local/` (git-ignored) | ISM Report On Business, industries reporting growth/contraction | Restricted | Monthly, from Dec 2025 | Long format: Category, Date, Industry, Direction, Score. |
| `ISM_Manufacturing_Index_Updated.xlsx` | `local/` (git-ignored) | Source workbook for the ISM CSVs | Restricted | — | Never committed. |
| `ism_history.csv` | `sample/` (committed) | **PMI column:** ISM, as published. **All other columns:** synthetic | PMI: restricted, short excerpt; others: illustrative | Monthly, last 36 months | Built by `scripts/build_ism_sample.py` (fixed seed). Sub-index values are synthetic, not ISM figures; the page labels them "illustrative data". |
| `ism_sectors.csv` | `sample/` (committed) | Synthetic | Illustrative | Monthly, last 3 months | Synthetic industry rankings over ISM's published industry categories; labelled "illustrative data" on the page. |
