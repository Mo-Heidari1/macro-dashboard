# CLAUDE.md — Macro Dashboard

Instructions for Claude Code. Read this file fully at the start of every session.

## Project purpose

A multi-page Streamlit dashboard that tracks leading, coincident and lagging macroeconomic indicators in the US, Europe and China. It turns them into a single view of the macro regime and what it means for markets.

It is a public portfolio project for trading and research job applications. That means:

- Code quality, correctness and clarity matter as much as features.
- Every number shown must be traceable to a named source.
- The README and page text use **analytical framing** — what the indicator says about the economy and markets. Avoid operational framing ("this script updates a CSV").

## Environment

- Windows + Anaconda base environment (Python 3.12). Run with `python -m streamlit run Home.py` from that environment. Run tests with `python -m pytest`.
- Deployed on Streamlit Community Cloud from the `main` branch. Code must therefore run on Linux too:
  - no Windows-only file paths
  - every dependency listed in `requirements.txt`
- Stack: Python 3.12, pandas, numpy, plotly, streamlit, requests, pytest.
- Before adding any new dependency, explain why the existing stack can't do the job.

## Repository structure

```
Home.py                      # landing page: macro regime scorecard + links to modules
pages/                       # one file per module: N_Module_Name.py (UI only)
src/
  core/
    paths.py                 # all paths, built from __file__
    loaders.py               # shared fetchers: FRED, Treasury.gov, ECB SDMX, CFTC
    transforms.py            # shared maths: YoY, MoM, z-score, diffusion, rolling stats
    charts.py                # shared plotly chart builders and theme
    signals.py               # standard signal schema (see "Signal convention")
  modules/
    <module_name>/
      calculations.py        # pure functions: DataFrame in -> DataFrame out
      config.py              # series IDs, thresholds, labels
data/
  sample/                    # small public-safe samples (committed)
  local/                     # full or proprietary data (git-ignored)
scripts/                     # update scripts (manual entry, batch refresh)
tests/                       # pytest, one test file per module
```

## Engineering rules (non-negotiable)

1. **Storage.** Use CSV only for stored data. Never pickle: it broke on a datetime64 version mismatch in the past.
2. **Paths.** Build every path relative to `os.path.dirname(os.path.abspath(__file__))`, routed through `src/core/paths.py`. Never hardcode absolute paths.
3. **Pure calculations.** Calculation functions take a loaded DataFrame and return a clean DataFrame.
   - No global state.
   - No Streamlit calls inside `src/`.
   - UI code lives only in `pages/` and `Home.py`.
4. **Validation.** Before any new calculation is trusted, validate it number by number against the source Excel cached values (or the official release). Report the comparison table. Never assume.
5. **Data gaps.** Never assume the latest row is complete. Walk backward to the last fully populated row, and show its date ("as of") on the page.
6. **Caching.** Cache every network fetch with `st.cache_data(ttl=...)`: daily data 6h, weekly 24h, monthly 24h. Because of rule 3, the fetchers in `src/core/loaders.py` stay Streamlit-free; apply the cache wrapper where they are called, in `pages/` or `Home.py`. If an API call fails, fall back to the last saved CSV and show a visible warning. The app must never crash because a source is down.
7. **Secrets.** API keys come from `st.secrets` (with `os.environ` as a fallback for scripts).
   - Never print, log or commit keys.
   - `.streamlit/secrets.toml` must stay in `.gitignore`.
8. **Proprietary data stays out of git.** ISM, S&P Global/RatingDog PMI and NFIB history live in `data/local/` (git-ignored). Each such module must:
   - load `data/local/` if it exists, otherwise `data/sample/`
   - show a small "sample data" note when running on the sample.
9. **Behaviour-preserving refactors.** Any refactor must leave calculation outputs unchanged. Prove it with tests or a before/after comparison.

## Signal convention (every module)

Each module's `calculations.py` exposes `get_signal(df) -> dict` with this schema, so `Home.py` can build a regime scorecard across all modules:

```python
{
  "indicator": "ISM Manufacturing PMI",
  "region": "US",                         # US | EU | China | Global
  "type": "leading",                      # leading | coincident | lagging
  "as_of": "2026-09-30",
  "level": 49.1,
  "change": +0.8,                         # vs prior period
  "zscore": -0.4,                         # vs trailing 10y unless noted in config
  "direction": "improving",               # improving | deteriorating | flat, unless config.py sets DIRECTION_LABELS
  "regime": "contraction",                # module-specific label, defined in config.py
  "market_read": "one sentence on the implication for rates/equities/USD",
  "extreme": False,                       # optional: level beyond the module's extreme thresholds
}
```

The schema, allowed values and `validate_signal()` live in `src/core/signals.py`. A module may override the direction labels with `DIRECTION_LABELS = {"up": ..., "down": ..., "flat": ...}` in its `config.py` (e.g. steepening / flattening / flat for the yield curve).

Thresholds and regime labels live in each module's `config.py`. Never hardcode them in calculations.

## Module roadmap

Status: ✅ built · 🔨 in progress · ⬜ planned.
Licence: **P** = public data, can be committed · **R** = restricted/proprietary, local only, sample in repo.

### US — leading
| # | Module | Status | Source | Lic. | Key outputs |
|---|---|---|---|---|---|
| 1 | Treasury Yields & Curve | ✅ | Treasury.gov, FRED | P | curve snapshot, 2s10s / 3m10y, real yields (DFII10), curve regime (bull/bear steepener/flattener) |
| 2 | ISM Manufacturing | ✅ | manual entry from ISM releases | R | headline + components, new orders − inventories, sector breadth |
| 3 | ISM Services | ⬜ | manual entry from ISM releases | R | same structure as module 2; reuse its code |
| 4 | Credit Spreads | ⬜ | FRED: BAMLC0A0CM (IG OAS), BAMLH0A0HYM2 (HY OAS) | P* | IG/HY OAS level, change, z-score, HY−IG differential |
| 5 | Fed Policy & Liquidity | ⬜ | FRED: DFF, M2SL, WALCL | P | effective Fed Funds rate, M2 YoY, Fed balance sheet change, real policy rate |
| 6 | Consumer Sentiment (UMCSI) | ⬜ | FRED: UMCSENT | P* | level, expectations vs current conditions |
| 7 | Small Business (NFIB SBO) | ⬜ | manual entry from NFIB release | R | optimism index, hiring/capex plans |
| 8 | Housing — Building Permits | ⬜ | FRED: PERMIT | P | level, YoY, 6m momentum |

### US — inflation and the dollar
| # | Module | Status | Source | Lic. | Key outputs |
|---|---|---|---|---|---|
| 9 | CPI / PPI | ⬜ | FRED: CPIAUCSL, CPILFESL, PPIFIS | P | headline/core YoY, 3m annualised, CPI − PPI margin proxy |
| 10 | USD Trade-Weighted Index | ⬜ | FRED: DTWEXBGS | P | level, trend, YoY |

### Europe
| # | Module | Status | Source | Lic. | Key outputs |
|---|---|---|---|---|---|
| 11 | EU Benchmark Yields | ⬜ | ECB SDMX API, SR_* spot-rate series | P | euro-area curve, Bund-equivalent spreads |
| 12 | Economic Sentiment (ESI) | ⬜ | European Commission `main_indicators_nace2.xlsx` | P | ESI by country, MoM movers, divergence table |

### China
| # | Module | Status | Source | Lic. | Key outputs |
|---|---|---|---|---|---|
| 13 | China PMIs | ⬜ | NBS official PMI (P); RatingDog PMI, formerly Caixin (R) | P/R | official vs RatingDog, the large- vs small-firm gap |

### Positioning and markets
| # | Module | Status | Source | Lic. | Key outputs |
|---|---|---|---|---|---|
| 14 | COT Positioning | ⬜ | CFTC annual files, Futures-and-Options-Combined report | P | net speculative position, 3y percentile, extremes flag (metals, energy) |
| 15 | Commodities | ⬜ | FRED and other public price series | P | cyclical basket (copper, oil), copper/gold ratio |

\* FRED serves these under the source's licence terms. Check the history length and redistribution terms before committing raw CSVs (ICE BofA history on FRED is currently truncated). If in doubt, treat as R.

### Build order
Do 4 → 5 → 9 → 10 → 3 → 6 → 8 → 11 → 12 → 14 → 13 → 7 → 15. Then build the Home scorecard once 5 or more modules expose `get_signal`.

### COT-specific rule
Identify CFTC contracts by brute-force exact matching on open interest, longs and shorts together. Do not identify them by name similarity, because names change and typos exist in the source.

## Workflow for adding a module

1. **Plan first.** Before writing code, state:
   - series IDs and their frequency
   - the calculations
   - the regime thresholds
   - the page layout
   Wait for approval.
2. **Write `src/modules/<name>/`:** `config.py` → `calculations.py` (including `get_signal`).
3. **Write `tests/test_<name>.py`** with at least:
   - one known-value check against an official release
   - one data-gap test
   - one schema test for `get_signal`
4. **Validate** against the source and show the comparison table.
5. **Build `pages/N_<Name>.py`.** Each page has:
   - a 2–3 sentence "Why it matters" header
   - KPI cards (level, change, z-score, regime)
   - main chart
   - a component or breadth chart if relevant
   - an "as of" date and the source line
6. **Update the docs:** the README features list, this roadmap's status column, and `data/README.md` (source, licence, update frequency).
7. **Commit** on a branch named `module/<name>`. Use conventional commit messages (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`). Summarise the diff and wait for approval before merging to `main`.

## Style

- Plotly only. Use the shared theme in `src/core/charts.py`.
- Show recession shading (FRED: USREC) on long US time-series charts.
- Number formats: yields and spreads in % with 2 decimals, or bp with 0 decimals; index levels with 1 decimal.
- Type hints and short docstrings on every public function.
- Default to `ruff` formatting.

## Don'ts

1. Don't commit anything in `data/local/`, secrets, notebooks with outputs, or files over 5 MB.
2. Don't put trading-strategy logic or signals from private strategies in this repo.
3. Don't reproduce text from paid course material in page copy. All explanations should be written fresh.
4. Don't silently change a threshold or formula. Flag every change in the summary.
