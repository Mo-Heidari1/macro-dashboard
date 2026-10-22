# Data

Loaders read `data/local/<file>` if it exists, otherwise `data/sample/<file>`
(`src/core/paths.py`). All stored data is CSV.

| File | Folder | Source | Licence | Frequency | Notes |
|---|---|---|---|---|---|
| `yields_history.csv` | `sample/` (committed, full history) | U.S. Department of the Treasury, daily par yield curve rates (nominal and real); FRED series EFFR (effective Fed Funds rate) | Public | Weekly (Sunday-dated, carrying the prior Friday's close) to 2025; daily from 2026-01-01 | Refreshed with `scripts/update_yields.py`. Validated cell by cell against Treasury.gov for 1990–2026 (rows added through 2026-10-21 also checked against FRED for Fed Funds) with `scripts/validate_yields.py` (nominal and TIPS; Fed Funds not covered). Corrected from Treasury.gov: 2026 weekday TIPS (were missing), the 3mo column on Sunday rows 2021-12-26 to 2026-06-28 (held a lower, T-bill-style rate), and the stale 2021-01-03 row. |
| `ism_history.csv` | `local/` (git-ignored) | Institute for Supply Management, Manufacturing ISM Report On Business: headline PMI and 10 sub-indices | Restricted | Monthly, 1948 to Sep 2026 (sub-index start dates vary) | Built from the source workbook by `scripts/extract_ism.py`; new months added by hand with `scripts/update_ism.py` or the page form. |
| `ism_sectors.csv` | `local/` (git-ignored) | ISM Report On Business, industries reporting growth/contraction | Restricted | Monthly: Dec 2025 to Sep 2026 (all 7 categories) | Long format: Category, Date, Industry, Direction, Score. Jul-Sep 2026 imported from the Sep-2026 workbook, whose Sectors sheet lacks Sep-Nov 2025 for every category and Dec 2025-Jun 2026 for the six sub-index categories (those rows are kept from the earlier workbook); its Jan-Aug 2025 rows are not imported. |
| `ISM_Manufacturing_Index_Updated2.xlsx` | `local/` (git-ignored) | Source workbook for the ISM CSVs (through Sep 2026; replaces `ISM_Manufacturing_Index_Updated.xlsx`) | Restricted | — | Never committed. |
| `ism_history.csv` | `sample/` (committed) | **PMI column:** ISM, as published. **All other columns:** synthetic | PMI: restricted, short excerpt; others: illustrative | Monthly, last 36 months | Built by `scripts/build_ism_sample.py` (fixed seed). Sub-index values are synthetic, not ISM figures; the page labels them "illustrative data". |
| `ism_sectors.csv` | `sample/` (committed) | Synthetic | Illustrative | Monthly, last 3 months | Synthetic industry rankings over ISM's published industry categories; labelled "illustrative data" on the page. |
