# Macro Dashboard

A multi-page Streamlit dashboard that tracks leading, coincident and lagging
macroeconomic indicators and turns them into a read on the macro regime and
what it implies for rates, equities and the dollar. Every number on the page
is traceable to a named source.

## Indicators

**US Treasury Yields & Curve** (Treasury.gov, FRED). The yield curve is one
of the most reliable leading indicators of the US cycle: the 2s10s spread
compresses or inverts as markets price policy tightening and slower growth,
and re-steepens ahead of easing. The page shows current yields and changes by
tenor, curve snapshots across dates, any tenor-vs-tenor spread over time, and
breakeven (implied) inflation from nominal minus TIPS yields. The module's
signal classifies the latest four-week curve move as a bull/bear steepener or
flattener.

**ISM Manufacturing PMI** (Institute for Supply Management). A diffusion
index where 50 separates expansion from contraction; it leads industrial
production and corporate earnings, and its New Orders and Prices components
are closely watched for growth and inflation turns. The page shows the
headline and all ten sub-indices, a sub-index heatmap, industry-level
growth/contraction rankings, and a reconstruction of the headline from its
weighted components. The module's signal places the PMI in one of four
regimes (Expansion, Slowdown, Contraction, Recovery) from its level versus 50
and its three-month momentum.

*Source: ISM Manufacturing Report On Business (Institute for Supply Management). 1948–Sep 2026: ISM monthly releases (ismworld.org), with historical data via Investing.com and Quandl.*

The landing page sets the PMI against the 10-year yield as a cross-check
between the growth signal and the rates market.

## Signals

Every module exposes `get_signal(df)` returning one record in a shared
schema (level, change, z-score, direction, regime, a one-line market read,
and the "as of" date of the last complete observation). Thresholds and
labels live in each module's `config.py`. These records will feed a
cross-indicator regime scorecard on the landing page.

## Data and licensing

Each dataset has its own folder. Public series (Treasury.gov, FRED) are
committed in full under `data/yields/`. ISM data is committed under
`data/ism/`: the headline PMI and all
ten sub-indices since 1948, and industry growth/contraction rankings from
April 2026, attributed as follows: "Source: ISM Manufacturing Report On Business (Institute for Supply Management). 1948–Sep 2026: ISM monthly releases (ismworld.org), with historical data via Investing.com and Quandl." ISM industry comment text and the source
workbooks are never committed. See [`data/README.md`](data/README.md) for
each file's source, licence and update frequency.

## Structure

```
Home.py                      landing page: cross-indicator summary
pages/                       one page per indicator (UI only)
src/core/                    shared paths, loaders, transforms, charts, signal schema
src/modules/<indicator>/     config.py (series, thresholds, labels) + calculations.py (pure functions)
data/yields/                 Treasury yields history (committed)
data/ism/                    ISM history and sector rankings (committed, attributed)
data/local/                  restricted data and source workbooks (git-ignored)
scripts/                     data refresh and manual-entry tools
tests/                       pytest suite
```

## Run it

```
pip install -r requirements.txt
python -m streamlit run Home.py
python -m pytest
```

Dependencies are pinned for Python 3.12 (`requirements.txt`). On Streamlit
Community Cloud, select Python 3.12 under the app's advanced settings.

## Keeping the data current

- **Treasury yields:** `python scripts/update_yields.py` appends the latest
  Treasury.gov curves and the FRED effective Fed Funds rate. It reads a free
  FRED key (https://fred.stlouisfed.org/docs/api/api_key.html) from the
  `FRED_API_KEY` environment variable or `.streamlit/secrets.toml`; keys are
  never passed on the command line.
- **ISM Manufacturing:** ISM publishes no free data API, so each month's
  Report On Business figures are entered by hand — in the ISM page's "Add
  This Month's Data" tab or with `python scripts/update_ism.py` (interactive,
  or pass the values as flags). Both write the committed
  `data/ism/ism_history.csv`. `scripts/extract_ism.py --months` imports
  months from the local source workbook, and `scripts/validate_ism.py`
  checks the committed files against it.

Stored data is CSV only. An earlier pickle-based version broke across
machines on a pandas/numpy version mismatch when unpickling `datetime64`
columns.
