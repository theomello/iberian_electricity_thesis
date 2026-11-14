# REE, REN, ESIOS and MITECO data

_REE daily, realtime and forecast series, REN Portugal, ESIOS indicators and archives, MITECO reservoirs. Moved verbatim from `CLAUDE.md` on 2026-11-12; see `docs/data-reference/README.md`._

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

**The per-country flow fields are empty before 2024**, found 2026-10-01:
`export_*` and `import_*` are zero on every instant 2018-2023 and filled only on
part of 2024-2026 (`interconnection_balance`, the total, is filled throughout).
For border flows before 2024 use REN's `Import`/`Export` (Portugal) or OMIE's
scheduled interconnection occupation (below). REE records exports as negative.

Records per day: 288 normally, 276 on the 9 spring DST days, 300 on the 8
autumn ones — matching the transitions in the window exactly.

This is the primary sub-hourly source and is strictly better than the hourly
series originally sought.

### REE demand forecast — the anticipated/unanticipated split
`data/ree/ree_demand_forecast_5min.parquet`, fetched 2026-08-21, token-free.
**884,880 instants, 3,072 of 3,073 days**, 5-minute, from `prevProgPeninsula`.
Columns: `demand_forecast_mw` (*prevista*), `demand_scheduled_mw`
(*programada*), `utc_timestamp`, `local_date`.

Exists because every weather design in this repo treated a **realisation** as a
surprise, when day-ahead offers are submitted at noon on D-1 against a forecast.
This is the first forecast series here.

Full-sample error: mean −147.6 MW, sd 798.1, MAE 404.6 (1.39% of demand). **On
the clean quarters the sd is 200-490 MW** — comparable to, not larger than, a
one-sd heat shock (537 MW).

**Three periods must be excluded** (see the trap below): from 2025-12-12 (the
documented realtime contract change breaks comparability of the *actuals*, MAE
336 → 1,569), 2025Q2 (the 28 April 2025 blackout, sd 2,394), and 2023Q1 (mean
error −1,204 MW, **unexplained**).

**It is NOT a wind forecast**, which is what the day-ahead/intraday premium
design needs. No token-free route exists: `demanda.ree.es` publishes no
renewable-forecast endpoint (`prevProgRenovablePeninsula`,
`prevRenovablePeninsula`, `prevProgEolicaPeninsula`, `eolicaPeninsula` all 404),
and ESIOS indicator 541 **and `/archives` itself** return HTTP 403 without a
token — so the token-free archive route that works for archives 82 and 83 does
not extend to indicators. See [`notes/email-esios-token.md`](notes/email-esios-token.md).

**Resolved 2026-10-02**: the ESIOS token arrived, and REE's day-ahead wind, solar
and demand forecasts are on disk — see the ESIOS section below. Prefer ESIOS 1775
to this file for demand: its publication time (before 11:00 on D-1) is stated,
this one's is not.

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

### ESIOS — REE's day-ahead forecasts (token, from 2026-10-02)
`data/esios/esios_{1775,1777,1779}.parquet`, fetched 2026-10-02 by
`fetch/fetch_esios_spain.py --forecasts`: **67,967 hours each, 2019-01-01 →
2026-10-02, every day present**, peninsular, hourly energy in MWh — still hourly
after the day-ahead market's 15-minute switch. Columns: `indicator_id,
indicator_name, value, datetime` (local) `, utc_timestamp, geo_id, geo_name`.

| id | forecast | hourly corr. with REE realtime | mean forecast ÷ realised |
|---|---|---|---|
| 1775 | demand | 0.990 | 0.94 |
| 1777 | wind | 0.965 | 0.98 |
| 1779 | photovoltaic solar | 0.992 | 0.98 |

Compared with `ree_realtime_5min.parquet` to 2025-12-11. The 6% demand gap is
not explained; the realtime series may cover more than the peninsula (not checked).

**These are what bidders knew**: REE publishes them before 11:00 on D-1, an hour
before day-ahead offers close at 12:00 (the catalogue's own description). This is
the instrument the step-offer design needs (`docs/specs/2026-10-01-step-offer-design.md`
§5.1). **There is no 2018**: the series start 2019-01-01. ENTSO-E's Spanish
forecast covers 2018 but is due only by 18:00 on D-1, so it fills the gap only if
it matches 1777/1779 from 2019 on — check before using it.

**The token** sits in the gitignored `.env` as `ESIOS_TOKEN`, sent as the
`x-api-key` header. It is personal, and REE asks that data already downloaded is
not requested again, so the fetcher caches every month as returned in
`data/esios/raw/<id>/` and never re-requests a complete one. New
tokens: the form at https://www.esios.ree.es/es/token. The catalogue (1,983
indicators) is cached in `data/esios/indicator_catalogue.parquet`; search it
offline with `--search`.

**Installed capacity — `data/esios/esios_installed_capacity.parquet`**, fetched
2026-10-02 by `--capacity`: **26,709 rows, 19 indicators, monthly, 2015-01 →
2026-10, per autonomous community** (19 regions). It is the one series REE's
`potencia-instalada` never delivered (HTTP 500 under every parameter combination).
The 19: 17 technologies (1475–1491), the total (10300) and self-consumption
(10413). They need `time_trunc=month`; without it the API answers HTTP 500.

Peninsular capacity, GW:

| | 2018-01 | 2022-01 | 2026-10 |
|---|---|---|---|
| wind (1485) | 22.9 | 28.1 | 32.9 |
| photovoltaic (1486) | 4.4 | 16.2 | 55.1 |
| combined cycle (1483) | 24.9 | 24.6 | 24.6 |
| coal (1478) | 9.6 | 3.5 | 1.3 |
| nuclear (1477) | 7.1 | 7.1 | 7.1 |
| self-consumption (10413) | 1.2 | 3.3 | 11.3 |

**Peninsular = every region except `NON_PENINSULAR`** in the fetcher: the Balearic
and Canary Islands, Ceuta and Melilla, four separate electrical systems.

**Pure pumped storage (1476, 3,331 MW) is outside both hydro (1475) and the
total (10300)**: REE counts it as storage. The other 16 technologies sum to the
total to the megawatt in every month; add 1476 and the sum overshoots by 3,331 MW.

Validated against REE's realtime output (`qa/check_esios.py`): the highest hourly
nuclear output equals nuclear capacity to within 0.3% in every year 2018–2026,
which fixes the units (MW, not summed over days). For solar the same ratio falls
from 0.89 (2018) to 0.54 (2025); midday curtailment fits that, so it does not
test whether capacity is overstated. Not compared with REE's annual reports.

Uses: dividing a forecast by capacity separates weather from the firms' own
investment (step-offer design §5.1); it is the denominator of each firm's
capacity share; the regions allow regional weather × regional capacity.

**Measured wind and solar output by province — `data/esios/esios_measured_generation_province.parquet`**,
fetched 2026-10-05 by `--provinces`: ESIOS 1159 (onshore wind) and 1161 (photovoltaic),
**hourly MWh, 2018-01-01 → 2026-09-22, 5,853,962 rows**; 44 provinces carry wind, 47
solar, none on the islands. Every hour is present, and it stays hourly after the
15-minute switch. Requested a month at a time with **no region filter**, which returns
one series per province (the catalogue says the indicator "can be broken down by
provinces"). Published from M+1, so the last month is partial. Against REE's realtime
peninsular output (to 2025-12-11): wind hourly correlation **0.999**, level 98.9%
(0.98–1.00 every year); solar 0.999, level 98.1% (0.92–0.94 in 2018–2020, 0.99–1.00
from 2022). `lib/regions.py` `province_nuts2` gives each province its autonomous
community; ESIOS's capacity for Madrid is ~0 MW against some wind output there, so a
capacity factor for Madrid is meaningless. **Zero output is omitted, not reported**:
at night PV comes from fewer than 30 provinces or none (2019 – 2025 Q1: 38% of hours,
whose D-1 forecast averages 0.1 MWh), so a missing PV province-hour is zero output, not
a gap. A minimum-province rule written for wind drops every night hour of PV.

Two fetcher rules came from this fetch. A month is about 5 MB of JSON, so these chunks
are cached gzipped (`<YYYYMM>.json.gz`, 230 KB). And REE's API now and then answers
**HTTP 404 `NoSuchKey`** for a large request (1161, February 2018): the answer is staged
in a temporary file on REE's storage that was gone when served. The fetcher retries
that error three times; a month still growing is asked for again on a later day, never
twice on the same day.

**Stored hydro energy — `data/esios/esios_623.parquet`**, fetched 2026-10-07 by
`--ids 623 --geo 0 --start 2018-01-01 --end <today>`: **454 weeks, 2018-01-01 →
2026-09-28, MWh, stamped on Mondays**; the weeks of 2025-01-20, 2025-01-27 and
2025-05-26 are absent. Median 6.9 TWh in 2022 (the drought), 14.1 in 2026. **One
peninsular series, not one per agent**, although the catalogue describes it as the
storage "of each market agent": the API answers `disaggregated: False`, a request with
no region filter returns only `Península`, and no other ESIOS indicator carries
storage. It tracks MITECO's weekly total (below), which is dated one day later: level
correlation 0.92, weekly change 0.91 (0.67 and 0.77 a week either side). Published on
the third working day of the following week, so a week stamped Monday M is known for
offers from about M + 10 days.

**Per firm, Spanish storage comes from MITECO by basin** (`qa/check_hydro_storage_spain.py`).
The large Spanish hydro units are registered by basin (`DUER` "UGH. DUERO", `UFMI`
"UGH. UF-MIÑO", `TERE` "UGH. TER"), and a unit's monthly capacity factor moves with
its own demarcation's fill (all reservoirs; `hydro_flag` misses Guadiana): correlation
0.52–0.74 for 12 of 16 units, own basin first of 16 for 8 and top three for 13, above
the national series for 11 (Ter 0.67 against 0.18, Hidrocantábrico 0.52 against 0.09).
**Iberdrola's `JUCA` fails** (−0.17; the Júcar's large reservoirs serve irrigation),
and `TEES`, `VIES` and `GDNA` are weak. It is the basin's fill, not the firm's own
reservoirs: shared with other owners and with the state's irrigation and supply dams.

**Upward reserve allocated, whole system — `data/esios/esios_{632,627}.parquet`**,
fetched 2026-10-08 by `--ids 632 627 --geo 0 --start 2019-01-01 --end 2025-09-30` (27 MB of
raw JSON). 632 is the upward secondary regulation band (aFRR) allocated, MW, `Península`
only: **147,263 values, hourly to 2022-05-24 and quarter-hourly from 2022-05-25**; mean
594 MW (2019) rising to 1,180 (2025). 627, the additional upward reserve, holds **602
hours, all 2019-01-02 → 2019-11-08**, and nothing after. **Neither is by unit or firm**:
no reserve indicator in the catalogue is. Per-unit allocations are in REE's I90DIA
workbook (ESIOS archive 34, sheet I90DIA05; `notes/continuous-intraday-data.md` §4).
**REE's I90DIA workbooks, a sample: the 15th of every month, 2019-01 → 2025-09** (81 days,
about 450 MB, `data/esios/raw/archives/34/I90DIA_YYYYMMDD.zip`; fetched 2026-10-08 by
`fetch/fetch_esios_i90.py`, token). Per programming unit and hour: every schedule stage
(PDBF, the PHF sessions, PHFC, P48), the reserve and balancing results and offers, and
unavailability; the 2023 sheet list is in `notes/continuous-intraday-data.md` §4. Route:
`/archives/34/download?date=<day>T23:59:59+02:00&locale=es` with `Accept: */*`; `date` is the
**data** day, and the archive is published 90 days late. `--parse` writes
`data/esios/i90/i90_sample_hourly.parquet` (10.7 M rows: band, PDBF, PHFC, P48, every unit,
hourly). Checks: sheet I90DIA05 summed over units equals ESIOS 632 in every hour of
2023-06-15; its PDBF equals OMIE's day-ahead sales plus bilateral contracts to 0.0 MW on the
six groups' hydro. REE's UP codes for hydro are OMIE's (`DUER`, `EBRFEN`).

Three format changes, all silent:
- **To July 2025 one .xls of 37 sheets (4 MB zipped in 2019, 11 MB in 2025); from August
  2025 one CSV per sheet**, 43 sheets (`I90DIA00_YYYYMMDD.csv` …), semicolon-separated,
  **comma decimal**, UTF-8 with a byte-order mark. Sheet numbers 02, 05, 26, 36 keep their
  meaning; 29 was additional upward reserve in 2019 and is declared start-up times by 2023.
- **Periods follow the sheet and the year**: hourly columns `00-01` or quarter-hours `1..96`
  (P48 quarter-hourly in 2023 while PDBF and PHFC were still hourly). Schedules are MWh per
  period (sum quarters to the hour); the band is MW (average them).
- **The secondary band (I90DIA05) is by programming unit to 2024-11-15 and by market
  participant from 2024-12-15** (`END` Endesa, `GN` Naturgy, `HC` Hidrocantábrico, …): per-unit
  reserve ends there.

**Demand by segment — voltage level, access tariff, retailer type (fetched 2026-11-08/09)** by `--ids … --geo 0 --start
2018-01-01`, all `Península`, hourly to 2025-09-30 and quarter-hourly after for the PBF series, MWh per period (sum,
do not average).
- **Measured demand by voltage level, 1201–1207 (E0 low voltage < 1 kV … E6 ≥ 220 kV) and total 10269**: 2018-01-01 →
  2026-04-30 (published with a ~6-month lag). **E0–E6 sum to 10269 to the MWh in every hour.** 10269 is 207–229 TWh a
  year and equals 1193 *Demanda en consumo* (within 1.5%). E0 is ~100 TWh a year (households, small business), E1–E6
  110–125 TWh (industry, services, large consumers). **This is the household/industrial proxy**: it splits by
  connection voltage, not by consumer type, and E0 includes shops and small offices.
- **By access tariff, 1209 (2.0TD), 1216–1218 (6.2–6.4), 1369 (6.1), 2531–2534 (3.0TD(VE), 6.1/6.2 TDVE) and
  "total" 10268: do not use as a split before 2024.** 10268 is not total demand: it is exactly the sum of the tariff
  series ESIOS publishes, 100–114 TWh in 2018–2023, because the low-voltage tariffs (2.0, 3.0) are empty until 2024
  (1209 from 2024, 2532 from mid-2024 and **not** included in 10268). 1200 and 1208 return no data at all.
- **Scheduled demand (PBF) by retailer type, 351 free-market retailers, 352 reference (regulated, PVPC) retailers,
  353 direct market consumers**: 2018-01-01 → present, no lag. 2018: 213 / 28 / 3 TWh; 2025: 208 / 19 / 7. **352 matches
  the PDBF schedules of our regulated-supplier purchase units** (`is_pass_through`, Spanish, purchase roles) at
  0.97–1.00 of volume in Jan 2020, Jun 2022, Jan 2024, Mar 2025.

**France-line congestion rents — `data/esios/esios_{1117,1118}.parquet`**, fetched 2026-11-05 by `--ids 1117 1118 --geo 0
--start 2021-06-01 --end 2023-12-31`: day-ahead implicit (SDAC) rent, import and export direction, € per hour, `Península`. **Gross for
both systems** (split 50/50 under Reg. 1222/2015), and below (French − Spanish price) × PBF scheduled export (€1.11 bn against €1.97 bn,
2022-06-15 → 2023-02; hourly corr 0.94), since PBF exports include long-term-rights nominations. Used in `notes/rq-crisis-quantity.md` I1c.

ENTSO-E's token is still pending (ticket #9472601); `fetch/fetch_entsoe_spain.py`
is written but never executed.

### MITECO reservoir levels — the missing water-value state variable
`data/miteco/embalses_historico.parquet`, fetched 2026-08-18, token-free.
**720,099 rows, 401 reservoirs, 16 hydrographic demarcations, weekly,
1987-10-06 → present.** Source: MITECO's Boletín Hidrológico Semanal, the
same weekly bulletin published since 1988; the only downloadable
distribution is a zipped Access database
(`BD-Embalses.zip` → one table, `T_Datos Embalses 1988-2026`), not a
CSV/API — confirmed against the `datos.gob.es` catalogue entry too. Parsed
with `access_parser` (pure-Python MDB reader) rather than `mdbtools`, to
avoid a slow from-source Homebrew build chain.

Columns: `date`, `ambito` (demarcation), `embalse` (reservoir name),
`capacity_hm3`, `stored_hm3`, `hydro_flag`. Exists to supply `Vol` in the
hydro opportunity-cost function `c(pf, Vol, Snow)` that
[`hydro-water-value-design.md`](notes/hydro-water-value-design.md) argues is
necessary for the 2021 windfall-levy question — `pf` (OMIP forwards) and
`Snow` (ERA5) were already fetched; this was the missing piece. MITECO's own
label is "provisional, unvalidated."

**`ELECTRICO_FLAG` is not a reliable hydroelectric marker — do not filter on
it without checking coverage first.** It flags 0% of Guadiana's reservoirs
despite `GDNA` ("UGH. GUADIANA") being a real storage cascade in
`unit_agents.parquet`, and under 20% in Guadalquivir, Segura and Tajo, all
baskets that plainly contain generating reservoirs. Whatever it actually
encodes at MITECO, it under-covers real hydro storage; basin-level analysis
should aggregate all reservoirs in a demarcation, not just flagged ones.

A first probe against bidding data is in
[`hydro-water-value-design.md`](notes/hydro-water-value-design.md#2026-08-18-the-actual-state-variable-was-tried-and-its-a-different-kind-of-failure--sign-not-power):
basin-aggregate fill level (seasonally de-meaned) shows a real basin-specific
relationship with hydro storage units' offers — own-basin beats a
placebo-basin rotation at t = 2.00 on the median offer — but with a
**positive** sign, opposite the simple cost-shifter prediction. Read there,
not as a green light for a reduced-form regression: the sign is consistent
with reverse causality through storage strategy (a plant conserving water
bids high and stays fuller for the same reason), which is exactly why the
opportunity-cost function needs joint, not single-equation, estimation.
