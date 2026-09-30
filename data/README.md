# `data/` — what is in each folder

Everything here is **gitignored and fully re-fetchable** from `scripts/fetch/`
and `scripts/build/`. Nothing in this tree is hand-edited; to correct
something, fix the fetcher and re-run it.

Two file kinds appear throughout:

- **raw** — exactly what the source served (OMIE `.1`/`.zip`, REE/REN JSON).
  Never modified. Kept so a parser bug can be fixed without re-downloading.
- **parquet** — the parsed, typed, analysis-ready form. Always derived; safe
  to delete and rebuild.

Study window is **2018-01-01 → 2026-05-31**, except the bid archives — see
the frontier note at the bottom.

---

## `omie/` — the market operator (Spain + Portugal jointly)

OMIE runs MIBEL, the joint Iberian market. Its files cover **both countries**,
because they clear against one merged bid stack.

### `omie/prices/`
Day-ahead marginal price for both zones.

| path | what |
|---|---|
| `omie_day_ahead_prices.parquet` | **the usable file** — 91,247 rows, one per market period |
| `raw/` | 3,074 daily source files (`marginalpdbc_YYYYMMDD.1`) |
| `marginalpdbc_YYYY.zip` | yearly archives for 2018–2022, which OMIE serves *only* as zips |

Columns: `date, period, price_pt, price_es, utc_timestamp, resolution_min`.
Note the source column order is **Portugal first** — see CLAUDE.md.

### `omie/bids/` — day-ahead unit-level offer curves
The reason this setting was chosen: every offer from every unit, **accepted
and rejected**.

| path | what |
|---|---|
| `parquet/bids_YYYYMM.parquet` | 101 monthly files, 354,247,072 rows total |
| `zips/curva_pbc_uof_YYYYMM.zip` | 101 raw monthly archives (2.1 GB) |

Key columns: `unit, side` (V=sell, C=buy), `power_mw, price_eur_mwh`,
`status` (**O**=submitted curve, **C**=cleared portion — *never sum across
both*), `offer_type`, and `period/hour/quarter/resolution_min`.

### `omie/intraday/` — intraday session offer curves
Same structure and format as `bids/`, plus a `session` column. This is where
wind and solar forecast errors get corrected after the day-ahead auction.

| path | what |
|---|---|
| `parquet/intraday_YYYYMM.parquet` | 101 monthly files, 558,797,498 rows — **larger than the day-ahead archive** |
| `zips/curva_pibc_uof_YYYYMM.zip` | 101 raw monthly archives (2.9 GB) |

`session` is **not comparable across 2025-07**: 1–7 before, 1–3 after (the
European IDA auctions), with both regimes present during the 2025-03→06
overlap.

### `omie/registry/`
| path | what |
|---|---|
| `unit_registry.parquet` | 5,049 units — `country`, `role`, `group_tag`, first/last seen |
| `unit_agents.parquet` | 5,049 units — `agent`, `source` (esios/name/prefix), `tech_esios`, `max_power_mw` |

**Derived, not fetched.** Built by `scripts/build/build_unit_registry.py` from
OMIE's `pdbc`/`pdbcpt`/`pdbce` schedules, whose source zips are streamed and
discarded. This is the only reliable way to (a) tell Spanish from Portuguese
units and (b) separate generators from retailers — the `country` column
*inside* the bid files does neither.

### `omie/cab/` — day-ahead offer headers
| path | what |
|---|---|
| `zips/cab_YYYYMM.zip` | raw monthly archives, never modified |
| `parquet/cab_YYYYMM.parquet` | 113 months, 5,954,579 rows, one per unit per day |

Fetched by `scripts/fetch/fetch_omie_cab.py`. Carries the unit's **plant name**
(technology is in the prefix), **max power in MW**, and the **minimum income
condition** (fixed €/day + variable €/MWh). Together these supply the
technology and capacity the registry lacks, and the complex-bid condition that
drives whole-day unit withdrawals. Covers 2017-01, a year before the rest of
the window.

---

## `ree/` — Red Eléctrica, the Spanish TSO

| path | what |
|---|---|
| `ree_realtime_5min.parquet` | **885,085 rows, 5-minute** system state: demand, generation by technology, batteries, pumped storage, and bilateral flows with France, Portugal, Morocco, Andorra. 33 fields, wide format, units are **MW** |
| `ree_generation_daily.parquet` | daily generation, 17 series (one is the aggregate `Total generation` — exclude it) |
| `ree_demand_daily.parquet` | daily demand, one row per day |
| `ree_balance_daily.parquet` | daily balance, 25 series nested under 4 groups |
| `realtime_raw/YYYYMMDD.json` | 3,073 cached JSONP responses |

Timestamps are **local Madrid time** in the source; use `utc_timestamp` for
any join, and `local_date` for calendar-day work.

---

## `ren/` — Redes Energéticas Nacionais, the Portuguese TSO

Portugal is **inside** MIBEL, not a neighbour — these belong to the same
market object as the Spanish series.

| path | what |
|---|---|
| `ren_production_15min.parquet` | 3,801,736 rows, **15-minute**, 15 series (hydro, wind, solar, gas, coal, biomass, wave, batteries, pumping, import/export). Long format, **MW** |
| `ren_market_prices.parquet` | hourly ES and PT prices as republished by REN — the independent cross-check on the OMIE parse |
| `ren_consumption_supply_daily.parquet` | daily energy balance, 28 types |
| `ren_installed_power_monthly.parquet` | **installed capacity by technology** — the one series with no token-free *Spanish* source |
| `raw/{prod,price,bal,cap}_*.json` | 9,320 cached API responses |

**REN mixes two clocks**: production is Lisbon local time, market prices are
Madrid/MIBEL time. Both are already resolved to `utc_timestamp` in the
parquet — do not re-derive them from `local_date`.

---

## `esios/` — programming-unit registry

| path | what |
|---|---|
| `esios_programming_units.parquet` | archive 82 — 3,873 bidding units: `agent`, `tech`, `eic`, `max_power_mw` |
| `esios_physical_units.parquet` | archive 81 — 6,627 physical units, linked to both agent and bidding unit |
| `esios_market_subjects.parquet` | archive 83 — 739 agents: legal `name` and `type` (Productor / Comercializador / **Representante**) |

REE's registry of *unidades de programación*, from archive 82. **Token-free**,
unlike the ESIOS indicator API. `agent` (Sujeto del Mercado) is the entity that
submits offers — the grouping any market-power measure needs, published nowhere
in the OMIE files.

A **snapshot**: no entry/exit dates, so re-fetching silently changes it. Record
the fetch date with anything derived from it. It covers the physical fleet REE
dispatches, so the commercial aggregation vehicles in OMIE's bid files
(`EDPSVD1`, `IBEVD11`) are absent — 592 of our unit codes match. See
`omie/registry/unit_agents.parquet` for how the remainder is handled.

## `weather/` — ERA5 reanalysis, the instrument

| path | what |
|---|---|
| `weather_spain_hourly.parquet` | 737,520 rows — 10 points x hourly, wind speed 100 m/10 m, temperature, radiation |
| `weather_spain_aggregate.parquet` | 73,752 hours — wind-site mean speed, solar-site mean radiation, mean temperature |
| `raw_<point>.parquet` | per-point cache, so a re-run costs nothing |

Open-Meteo ERA5 archive, free and keyless, **UTC throughout**. Fetched to
instrument renewable output, which is not randomly assigned. First stage:
wind speed correlates +0.83 with REE wind output and radiation +0.87 with
solar. Temperature is a **control, not an instrument** — it moves demand
directly (+0.16) and so violates the exclusion restriction.

Representative sites, not capacity-weighted; a capacity-weighted index needs
installed capacity by province, which this project still lacks.

## `snirh/` — Portuguese reservoirs (APA)

| path | what |
|---|---|
| `snirh_reservoir_series.parquet` | 1,765,828 rows, 39 reservoir gauges, 2018-01 → 2026-09: weekly volume, hourly level, daily inflow/turbined/pumped/spilled/outflow, with a `suspect` flag |
| `raw/<code>.csv` | 39 SNIRH CSV exports, one per station — **not re-fetchable from an arbitrary network** |
| `reservoirs_wayback.parquet` | the earlier, sparse Wayback Machine reconstruction (`fetch_snirh_reservoirs_wayback.py`) |

**The exception to "fully re-fetchable".** SNIRH answers only APA's whitelisted
address, LMU eduVPN's exit 194.95.236.6, so `raw/` must be kept. See CLAUDE.md.

## `entsoe/` — empty

**Token-gated** and nothing fetched. The only series still missing anywhere in
this project is **Spanish installed capacity**; Portugal's is covered by REN
above. Note ESIOS above no longer needs a token for the unit registry, though
`fetch_esios_spain.py` still does for indicator series. See `.env.example`.

---

## Coverage frontiers — they are not all the same

| dataset | ends |
|---|---|
| day-ahead bids | **2026-05-08** |
| intraday bids | **2026-05-11** |
| everything else | 2026-05-31 |

OMIE publishes unit-level offers on a **~3-month lag** because they are
commercially sensitive. So the newest ~3 months of prices, REE and REN will
never have matching bids. Re-running the fetchers later moves that frontier
forward rather than filling it in.

Three intraday days are absent at source (2021-07-30, 2025-04-29,
2026-02-28): the monthly zips contain zero members for those dates.

Run `.venv/bin/python scripts/qa/audit_data.py` to re-verify all of the above
from the files themselves.
