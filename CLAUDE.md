# Spanish electricity market — data project

Operational instructions for this repo. Everything below is a **verified fact
about the data**. There is deliberately no research question here yet.

## Status

**Setting:** Spain / MIBEL. Candidate setting for a thesis, adopted
2026-08-07 after retiring an earlier Brazil-based question.

**Research question: none yet — intentionally.** The data came first so that
the question can be chosen against what the data can actually identify,
rather than the reverse. Do not add an RQ section here until one is chosen;
do not import framing from the previous project.

The previous Brazil project remains intact at
`~/Desktop/vre_hydro_thesis` and is not to be modified. Nothing was copied
from it. If something there turns out to be needed, port that one piece
deliberately, restated in Spanish-market terms.

## Environment

Python lives in `.venv` (Python 3.14, pandas 3.0, pyarrow 25). Always use
`.venv/bin/python`, never bare `python3`.

```bash
.venv/bin/python scripts/fetch_omie_prices.py
```

Scripts resolve the repo root via `Path(__file__).resolve().parent.parent`.
Never hardcode paths.

**This repo is at `~/projects/`, deliberately NOT on the Desktop.** The
Desktop is iCloud-synced, which silently evicts large data files to 182-byte
`.<name>.icloud` stubs; reads then fail with a bare "No such file or
directory" even though nothing was deleted. Keep `data/` off iCloud.

## Scripts

| Script | Source | Token | Output |
|---|---|---|---|
| `fetch_omie_prices.py` | OMIE `marginalpdbc` | no | `data/omie/prices/omie_day_ahead_prices.parquet` |
| `fetch_omie_bids.py` | OMIE `curva_pbc_uof` | no | `data/omie/bids/parquet/bids_YYYYMM.parquet` |
| `fetch_ree_daily.py` | REE `apidatos` | no | `data/ree/ree_{generation,demand,balance}_daily.parquet` |
| `fetch_esios_spain.py` | ESIOS | **yes** | `data/esios/esios_{id}.parquet` |
| `fetch_entsoe_spain.py` | ENTSO-E | **yes** | `data/entsoe/entsoe_{series}_{zone}.parquet` |

`omie_common.py` holds shared parsing and DST/resolution logic;
`config.py` loads tokens from a gitignored `.env`.

## Data inventory

Window: **2018-01-01 → 2026-05-31**, set by the bid archive's start.
All of `data/` is gitignored — it is large and fully re-fetchable.

### OMIE day-ahead prices — complete
91,247 rows, 3,073 days, zero missing. Columns: `date`, `period`,
`price_pt`, `price_es`, `utc_timestamp`, `resolution_min`.
Spain mean 73.31 €/MWh, range −15.00 to 700.00. ES and PT differ in 6.7% of
periods (market splitting).

### OMIE bid curves — the reason this setting is interesting
Unit-level day-ahead offers, ~2.3–2.8 M rows per month, ~2,000 units/day.
Columns: `date`, `hour`, `country`, `unit`, `side`, `energy_mwh`,
`price_eur_mwh`, `status`. Both accepted and rejected offers are present.

### REE daily generation / demand / balance — complete
Daily only (see the hourly limitation below), 2018-01-01 → 2026-05-31, no
empty months. Generation 49,201 rows / 17 series (one being the aggregate);
demand 3,073 rows, exactly one per day, matching the price day count;
balance 70,060 rows / 25 series nested under four groups.

Validated: generation components sum to REE's published total at 0.00% gap
every year, and annual output (~260 TWh) matches published figures. Wind +
solar rose from 23.9% of generation in 2018 to 41.8% in 2024.

### ESIOS / ENTSO-E — pending tokens
Hourly generation, hourly demand and installed capacity are **not yet
acquired**. They require tokens that must be requested by a human; see
`config.py`. Both scripts are written but have never been executed.

---

## Traps

Each of these was hit and verified on real files on 2026-08-07. All of them
fail silently rather than raising.

### OMIE bids: `O` and `C` rows are NOT additive
The last field flags each row Ofertada (`O`) or Casada (`C`). These are two
parallel views of the same auction, not disjoint parts of it: `O` is the
**full submitted curve**, `C` is the **cleared portion**. On 2024-01-01 h12,
offered sell was 63,599 MWh and matched sell 24,872 MWh, with matched buy
also exactly 24,872 MWh — the market-clearing identity.

Filter to `status == 'O'` for supply/demand functions and `status == 'C'`
for cleared quantities. **Summing across both double-counts every accepted
bid.** `fetch_omie_bids.py --verify` re-checks the identity per month.

### The 15-minute switch on 2025-10-01
OMIE moved from hourly to **15-minute market time units** on 2025-10-01 (the
EU-wide MTU change). Days have 96 periods from that date, 24 before. Any
code assuming 24 periods per day is wrong for every day after it. The price
parquet carries `resolution_min` (60 or 15) to make the break explicit.

### DST days have 23 or 25 periods
OMIE indexes periods 1..N within the *local* Madrid day, so N is 23 on the
March spring-forward day and 25 in October — and 92/100 in the 15-minute
era. `day_periods_utc()` derives the step from the actual local-day span,
which handles all six cases. Never assume a fixed step.

### `marginalpdbc` column order is PT then ES
Fields are `year;month;day;period;price_pt;price_es` — **Portugal first**.
Verified on 2024-01-01 h12, a splitting hour reading `29.8;3.9`: Spanish
units' highest matched sell bid was 3.90 and Portuguese units' 29.80.

### The two OMIE files use different decimal separators
`marginalpdbc` uses a **dot** (`77.7`). `curva_pbc_uof` uses a **comma**
decimal with a **dot** thousands separator (`1.500,00` = 1500.0). Do not
share a number parser between them. Both files are **latin-1**, not UTF-8.

### OMIE splits this dataset by age
Prices for 2018–2022 exist **only as yearly zips**; 2023+ are daily files.
Assuming the daily pattern throughout silently loses every pre-2023 day.
A few days also carry `.2`/`.3` revision suffixes instead of `.1`.

### REE `apidatos` hourly and capacity endpoints are broken
`time_trunc=hour` returns HTTP 400 "data currently unavailable" on every
endpoint, for windows from one day to one month, in both 2014 and 2024.
`potencia-instalada` returns HTTP 500 regardless. `time_trunc=day` works
back to at least 2014. Hourly and capacity must come from ESIOS/ENTSO-E.

### REE timestamps are local, not UTC
`apidatos` returns e.g. `2024-01-01T00:00:00.000+01:00`. Converting to UTC
before taking the date relabels 1 January as 31 December. Use the
`local_date` column for calendar-day work.

### REE generation includes `Total generation` as a *series*
`estructura-generacion` returns 17 series, one of which is the aggregate
`Total generation`. Summing all series double-counts, roughly halving any
share computed from it. Exclude it, then verify: the components sum to the
published total at 0.00% gap in every year 2018–2026, which is a good check
that a filter has not dropped something.

Values are in **MWh**, not GWh. Spain runs ~260 TWh/year of generation and
~700 GWh/day of demand; a "700,000" daily figure is MWh.

### REE `balance-electrico` nests its series
Unlike the other endpoints, balance returns four groups (Renewable,
Non-renewable, Almacenamiento, Demand) whose real series sit one level down
under `attributes.content`. Reading `attributes.values` at the top level
yields zero rows.

## Known source-data anomaly

**2018-06-14** violates the clearing identity in all 24 hours, with buy
exceeding sell by a constant ~2,900 MWh. Thirteen sell units present on both
06-13 and 06-15 — including the `MIEU` interconnection pseudo-unit — are
absent that day. The source file is 99% of median size and parses cleanly,
so this is a gap in OMIE's publication, not a parsing artifact. It is one
day in 3,073 (0.03%) and has been left as-is rather than patched.

## Conventions

- Raw downloads are never modified; re-fetch instead.
- Derived outputs go to `outputs/`; raw and parsed data to `data/`.
- Fetchers are resumable — they skip what is already on disk.
- Commit messages: imperative, present tense, ≤72-char subject.
- Never commit `.env` or anything under `data/`.
