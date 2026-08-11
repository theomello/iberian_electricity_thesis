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

**Derived, not fetched.** Built by `scripts/build/build_unit_registry.py` from
OMIE's `pdbc`/`pdbcpt`/`pdbce` schedules, whose source zips are streamed and
discarded. This is the only reliable way to (a) tell Spanish from Portuguese
units and (b) separate generators from retailers — the `country` column
*inside* the bid files does neither.

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

## `esios/` and `entsoe/` — empty

Both are **token-gated** and nothing has been fetched. They exist so the
fetchers have somewhere to write. The only series still missing anywhere in
this project is **Spanish installed capacity**; Portugal's is covered by REN
above. See `.env.example`.

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
