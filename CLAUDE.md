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
| `fetch_ree_realtime.py` | REE `demanda.ree.es` | no | `data/ree/ree_realtime_5min.parquet` |
| `fetch_ren_portugal.py` | REN `servicebus.ren.pt` | no | `data/ren/ren_{production_15min,installed_power_monthly,market_prices,consumption_supply_daily}.parquet` |
| `fetch_esios_spain.py` | ESIOS | **yes** | `data/esios/esios_{id}.parquet` |
| `fetch_entsoe_spain.py` | ENTSO-E | **yes** | `data/entsoe/entsoe_{series}_{zone}.parquet` |

`omie_common.py` holds shared parsing and DST/resolution logic;
`config.py` loads tokens from a gitignored `.env`.

## Data inventory

Window: **2018-01-01 → 2026-05-31**, set by the bid archive's start.
Bids alone stop at **2026-05-08** (a ~3-month publication lag — see below).
All of `data/` is gitignored — it is large and fully re-fetchable.

### OMIE day-ahead prices — complete
91,247 rows, 3,073 days, zero missing. Columns: `date`, `period`,
`price_pt`, `price_es`, `utc_timestamp`, `resolution_min`.
Spain mean 73.31 €/MWh, range −15.00 to 700.00. ES and PT differ in 6.7% of
periods (market splitting).

### OMIE bid curves — complete to the publication frontier
**101/101 months, 354,247,072 rows, uniform schema.**

The bid archive ends **2026-05-08**, not 2026-05-31 like every other dataset.
This is not a fetch failure: OMIE's May 2026 zip contains only 8 days, no
daily bid files exist (the listing has none, and direct fetches 404), and the
frontier sits 91 days before the fetch date of 2026-08-07 — a **~3-month
publication lag**, as expected for commercially sensitive unit-level offers.

So the bid window is 2018-01-01 → 2026-05-08 while prices, REE and REN run to
2026-05-31. Re-running the fetcher later extends the frontier; the last ~3
months of any other series will never have matching bids.


Unit-level day-ahead offers for **both** Spanish and Portuguese units, since
MIBEL clears jointly. ~2.3–3.6 M rows/month in the hourly era, ~14 M/month
from 2025-10 when the 15-minute MTU quadrupled the period count.

Columns: `date`, `period`, `hour`, `quarter`, `resolution_min`, `country`,
`unit`, `side`, `power_mw`, `price_eur_mwh`, `status`, `offer_type`.

Both accepted and rejected offers are present — that is the point. In a
single hour (2024-01-01 h12) 63,599 MWh was offered against 24,872 MWh
cleared; the gap is the unaccepted supply.

`power_mw` unifies the two eras: hourly files publish MWh over one hour,
numerically identical to average MW. Derive energy as
`power_mw * resolution_min / 60`.

### REE daily generation / demand / balance — complete
Daily only (see the hourly limitation below), 2018-01-01 → 2026-05-31, no
empty months. Generation 49,201 rows / 17 series (one being the aggregate);
demand 3,073 rows, exactly one per day, matching the price day count;
balance 70,060 rows / 25 series nested under four groups.

Validated: generation components sum to REE's published total at 0.00% gap
every year, and annual output (~260 TWh) matches published figures. Wind +
solar rose from 23.9% of generation in 2018 to 41.8% in 2024.

### REE realtime — 5-minute generation, demand and flows — complete
`demanda.ree.es`, token-free. **885,085 rows, all 3,073 days present**, zero
duplicate instants, monotonic in UTC. 33 fields: demand, generation by
technology (PV and thermal solar separately), batteries, pumped storage, and
**bilateral** flows with France, Portugal, Morocco and Andorra. Units are
**MW** (instantaneous power), not MWh.

Records per day: 288 normally, 276 on the 9 spring DST days, 300 on the 8
autumn ones — matching the transitions in the window exactly.

This is the primary sub-hourly source and is strictly better than the hourly
series originally sought.

### REN Portugal — complete
`servicebus.ren.pt/datahubapi/electricity`, token-free, documented at
https://datahub.ren.pt/pt/instrucoes-api/. Portugal is **inside** MIBEL, not
a neighbour: it clears jointly with Spain against one merged bid stack, so
the Portuguese series belong to the same market object as the Spanish ones.

| file | rows | content |
|---|---|---|
| `ren_production_15min.parquet` | 3,801,736 | 15 series, **15-min**, all 3,073 days |
| `ren_market_prices.parquet` | 147,502 | hourly ES and PT |
| `ren_consumption_supply_daily.parquet` | 77,834 | 28 balance types |
| `ren_installed_power_monthly.parquet` | 887 | capacity by technology |

Points per day 92/96/100 — the 9 spring and 8 autumn DST days match Spain's
counts exactly, which cross-validates both timezone implementations.

Validated: annual generation 44–55 TWh matches published figures; coal runs
11.2 TWh (2018) → **0.0 from 2022**, matching the closure of Pego, the last
Portuguese coal plant, in late 2021. Solar capacity 577 → 5,028 MW and solar
generation 0.8 → 6.1 TWh over the window; VRE share 23.8% → 41.6%.

`ElectricityInstalledPowerMonthly` matters disproportionately: installed
capacity has **no token-free Spanish source**, but Portugal publishes it.

The price series is also the independent check on the OMIE parse — see the
trap below.

### ESIOS / ENTSO-E — installed capacity only
Only **installed capacity** still lacks a source: REE's `potencia-instalada`
returns HTTP 500 under every parameter combination tried. Tokens are needed
for that alone; see `config.py`. Both scripts are written but never executed.

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

Confirmed independently against REN, which labels its two price series
explicitly: over **67,919 hourly instants the match is 100.0000% exact** for
both. The decisive part is the 3,568 splitting instants where the two prices
genuinely differ — REN's `PT` still matches `price_pt` at 0.0000, while the
crossed comparison is off by up to 122 €/MWh. Getting this backwards would
silently swap the two countries in every price-based result.

### The two OMIE files use different decimal separators
`marginalpdbc` uses a **dot** (`77.7`). `curva_pbc_uof` uses a **comma**
decimal with a **dot** thousands separator (`1.500,00` = 1500.0). Do not
share a number parser between them. Both files are **latin-1**, not UTF-8.

### OMIE splits this dataset by age
Prices for 2018–2022 exist **only as yearly zips**; 2023+ are daily files.
Assuming the daily pattern throughout silently loses every pre-2023 day.
A few days also carry `.2`/`.3` revision suffixes instead of `.1`.

### REE `apidatos` hourly needs `geo_trunc`; generation is broken regardless
`demanda/evolucion` at `time_trunc=hour` returns HTTP 400 **unless** the full
geo triplet is supplied — `geo_trunc=electric_system&geo_limit=peninsular&
geo_ids=8741`. With it, hourly demand works.

Generation is a different matter: `estructura-generacion`,
`balance-electrico`, `estructura-renovables` and
`evolucion-renovable-no-renovable` all return HTTP 400 at `time_trunc=hour`
with or without geo parameters, while working at `time_trunc=day`. Use
`fetch_ree_realtime.py` instead — it is finer-grained anyway.

`potencia-instalada` returns HTTP 500 under every combination tried. That is
the one series with no token-free source.

### REE realtime is JSONP with a letter-coded DST hour
The body is wrapped as ``null({...});`` and must have the wrapper stripped
before JSON parsing. Timestamps are **local Madrid time**, and the repeated
hour on the autumn DST day is written ``2A`` (first pass, CEST) and ``2B``
(second pass, CET) — 25 distinct hour tokens, with no plain ``02``. The
spring day omits ``02`` entirely, giving 23. `strptime` raises on ``2A``, so
this fails loudly, but it must be handled; `parse_local_ts()` maps the
suffixes onto `fold`.

### REE realtime changed its contract on 2025-12-12
Until 2025-12-11 the request **requires** ``curva=NACIONAL``. From 2025-12-12
that value is rejected with ``curva NACIONAL no valida`` and the parameter
must be **omitted** instead. No single form works for both eras, so
`fetch_day()` tries the named curve then falls back to the bare request.
Missing this silently truncates the series at 2025-12-11 — a 171-day hole at
the end of the window, which is exactly what happened on the first run.

Three fields also change at that boundary: ``die``, ``gas`` and ``genAux``
disappear; ``aut``, ``gf`` and ``icb`` appear. Both eras carry 33 fields.
Coverage is therefore ~94% / ~6% split for the two sets, and **all six are
null on the wrong side of the boundary** — do not treat them as continuous
series. The three new names are carried through unrenamed; confirm their
meaning against REE documentation before using them.

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

### Portugal runs one hour behind Spain — and REN mixes two clocks
Portugal is WET/WEST (UTC+0/+1); Spain is CET/CEST (UTC+1/+2). They share a
market but not a clock, so any PT↔ES join must go through UTC.

Worse, **REN uses different clocks for different endpoints**:

- `ElectricityProductionBreakdownDaily` → **Lisbon** local time
- `ElectricityMarketPricesDaily` → **Madrid** (MIBEL/CET), because the price
  is a market object shared with Spain rather than a Portuguese measurement

Both were established empirically, not assumed. Production: under the Lisbon
reading PT and ES solar noon coincide at 12:22 UTC on 2024-06-15, whereas a
Madrid reading puts Portugal 60 minutes *earlier* than Spain — impossible for
a country lying further west. Prices: mapping them as Lisbon reproduced
OMIE's value one hour late; under Madrid, REN and OMIE agree to **0.0000**
on both `PT` and `ES`.

That price agreement is also the independent confirmation that
`marginalpdbc` is PT-then-ES — REN labels its two series explicitly.

### REN point counts encode DST, but the labels do not
92 points on the spring day, 100 in autumn, 96 otherwise. The x-axis labels
still read `00:00`..`23:45` in every case, so the labels alone are useless
for DST; the **count** carries the information. `day_periods_utc(d, n, tz)`
derives the step from the local-day span, which handles it.

### `country` in the bid files does NOT identify a unit's country
Only ~4.7% of matched rows carry `ES` or `PT`; the rest are tagged `MI` for
the joint MIBEL market. That share tracks the ~6.7% market-splitting rate, so
the tag appears mainly **when the market splits**, not as a unit attribute.
Do not use it to select Portuguese units — a unit-level registry is needed
for that, and OMIE does not expose one under the obvious dataset names
(`unidades`, `agentes`, `unidades_fisicas` all 404).

## Known source-data anomaly: whole-day unit dropouts

A recurring class of gap in OMIE's publication — **not** a parsing artifact.
On an affected day, a block of units is simply absent from the file for all
24 hours, so matched buy no longer equals matched sell and the imbalance is a
near-constant MW offset across the day. Affected files are normal size and
parse cleanly.

Confirmed so far (~0.1% of days):

| date | direction | offset | missing units |
|---|---|---|---|
| 2018-06-14 | buy > sell | ~2,900 MWh/h | 13 sell units, incl. the `MIEU` interconnection pseudo-unit |
| 2022-10-12 | sell > buy | ~3,098 MWh/h | 16 buy + 24 sell units |

The direction varies with which side loses more. Left as-is rather than
patched — imputing bids would be inventing data.

**Always run `fetch_omie_bids.py --verify`**, which re-checks the
market-clearing identity per month and prints the maximum gap; a non-zero
value flags exactly this. Filter these days out of any design that relies on
market-wide aggregates. Analyses of individual units' bidding are unaffected
except for the units actually missing.

## Conventions

- Raw downloads are never modified; re-fetch instead.
- Derived outputs go to `outputs/`; raw and parsed data to `data/`.
- Fetchers are resumable — they skip what is already on disk.
- Commit messages: imperative, present tense, ≤72-char subject.
- Never commit `.env` or anything under `data/`.
