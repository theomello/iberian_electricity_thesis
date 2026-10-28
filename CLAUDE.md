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

**A descriptive chapter is under way** — design in
[`docs/specs/2026-08-24-descriptive-price-formation-design.md`](docs/specs/2026-08-24-descriptive-price-formation-design.md),
running note in [`notes/rq-descriptive-price-formation.md`](notes/rq-descriptive-price-formation.md).
Findings live there, not here.

The previous Brazil project remains intact at
`~/Desktop/vre_hydro_thesis` and is not to be modified. Nothing was copied
from it. If something there turns out to be needed, port that one piece
deliberately, restated in Spanish-market terms.

## Environment

Python lives in `.venv` (Python 3.14, pandas 3.0, pyarrow 25). Always use
`.venv/bin/python`, never bare `python3`. Added 2026-10-02 for the rainfall data:
xarray 2026.9.0 and netCDF4 1.7.4 (E-OBS), shapely 2.1.2 and pyshp 3.1.6
(HydroBASINS). Added 2026-10-08: xlrd 2.0.2, to read REE's I90DIA workbooks (.xls).
There is no requirements file.

```bash
.venv/bin/python scripts/fetch/fetch_omie_prices.py
```

Scripts resolve the repo root from their own location — `lib/` modules use
`Path(__file__).resolve().parent.parent.parent`, since they sit two levels
below it. Never hardcode paths. See `scripts/README.md` for the layout and
`data/README.md` for what each output folder holds.

**This repo is at `~/projects/`, deliberately NOT on the Desktop.** The
Desktop is iCloud-synced, which silently evicts large data files to 182-byte
`.<name>.icloud` stubs; reads then fail with a bare "No such file or
directory" even though nothing was deleted. Keep `data/` off iCloud.

## Scripts

`scripts/` is grouped by what a script *does*, and every path below is
relative to it:

```
scripts/
  lib/       shared modules — omie_common (parsing, DST, resolution), config (tokens)
  fetch/     one script per source; each writes raw + parquet under data/
  build/     derived artefacts assembled from fetched data
  qa/        integrity checks that re-derive facts from the files
  analysis/  descriptive statistics and figures (R)
```

| Script | Source | Token | Output |
|---|---|---|---|
| `fetch/fetch_omie_prices.py` | OMIE `marginalpdbc` | no | `data/omie/prices/omie_day_ahead_prices.parquet` |
| `fetch/fetch_omie_bids.py` | OMIE `curva_pbc_uof` | no | `data/omie/bids/parquet/bids_YYYYMM.parquet` |
| `fetch/fetch_omie_intraday.py` | OMIE `curva_pibc_uof` | no | `data/omie/intraday/parquet/intraday_YYYYMM.parquet` |
| `fetch/fetch_omie_intraday_prices.py` | OMIE `marginalpibc` | no | `data/omie/intraday_prices/omie_intraday_prices.parquet` |
| `build/build_unit_registry.py` | OMIE `pdbc`,`pdbcpt`,`pdbce` | no | `data/omie/registry/unit_registry.parquet` |
| `fetch/fetch_omie_cab.py` | OMIE `cab` | no | `data/omie/cab/parquet/cab_YYYYMM.parquet` |
| `fetch/fetch_omie_pdbf.py` | OMIE `pdbf` | no | `data/omie/pdbf/parquet/pdbf_YYYYMM.parquet` |
| `fetch/fetch_esios_units.py` | ESIOS archive 82 | **no** | `data/esios/esios_programming_units.parquet` |
| `build/build_unit_agents.py` | ESIOS + `cab` + prefixes | no | `data/omie/registry/unit_agents.parquet` |
| `build/build_omie_unit_lists.py` | OMIE *Listado de Unidades* PDFs (emailed, **not re-fetchable**) | no | `data/omie/registry/omie_unit_lists.parquet` |
| `build/build_owner_groups.py` | `omie_unit_lists` + ESIOS chain | no | `data/omie/registry/owner_groups.parquet` |
| `fetch/fetch_ree_daily.py` | REE `apidatos` | no | `data/ree/ree_{generation,demand,balance}_daily.parquet` |
| `fetch/fetch_ree_realtime.py` | REE `demanda.ree.es` | no | `data/ree/ree_realtime_5min.parquet` |
| `fetch/fetch_ree_demand_forecast.py` | REE `demanda.ree.es` | no | `data/ree/ree_demand_forecast_5min.parquet` |
| `fetch/fetch_ren_portugal.py` | REN `servicebus.ren.pt` | no | `data/ren/ren_{production_15min,installed_power_monthly,market_prices,consumption_supply_daily}.parquet` |
| `fetch/fetch_esios_spain.py` | ESIOS | **yes** | `data/esios/esios_{id}.parquet`, `esios_installed_capacity.parquet`, `esios_measured_generation_province.parquet` |
| `fetch/fetch_entsoe_spain.py` | ENTSO-E | **yes** | `data/entsoe/entsoe_{series}_{zone}.parquet` |
| `fetch/fetch_hydro_precipitation.py` | Open-Meteo ERA5 | no | `data/weather/precipitation_basins_daily.parquet` |
| `fetch/fetch_eobs_precipitation.py` | E-OBS v33.0e (KNMI) | no | `data/eobs/eobs_rr_iberia_daily.parquet` |
| `fetch/fetch_hydrobasins.py` | HydroBASINS v1c (HydroSHEDS) | no | `data/hydrosheds/hybas_iberia_lev{08,10,12}.parquet` |
| `fetch/fetch_population_temperature.py` | Open-Meteo ERA5 | no | `data/weather/temperature_population_index.parquet` |
| `fetch/fetch_omie_unavailability.py` | OMIE `indisp` | no | `data/omie/indisp/parquet/indisp_YYYYMM.parquet` |
| `fetch/fetch_omie_interconnection.py` | OMIE `capacidad_inter_pbc` | no | `data/omie/interconnection/omie_interconnection_capacity.parquet` |
| `fetch/fetch_omip_forwards.py` | OMIP | no | `data/omip/parquet/omip_forwards_{zone}_{YYYY}.parquet` |
| `fetch/fetch_hydro_reservoirs.py` | MITECO Boletín Hidrológico | no | `data/miteco/embalses_historico.parquet` |
| `fetch/fetch_jrc_ppdb_efficiency.py` | JRC-PPDB-OPEN (Zenodo) | no | `data/jrc_ppdb/jrc_{spain,portugal,italy}_units.parquet` |
| `fetch/fetch_mibgas_prices.py` | MIBGAS | no | `data/mibgas/mibgas_price_index_daily.parquet` |
| `fetch/fetch_eua_carbon_price.py` | investing.com (browser-captured) | no, but not resumable | `data/investing/eua_carbon_price_daily.parquet` |
| `fetch/fetch_coal_price.py` | investing.com (browser-captured) | no, but not resumable | `data/investing/coal_price_daily.parquet` |
| `fetch/fetch_ecb_fx.py` | ECB Statistical Data Warehouse | no | `data/ecb/ecb_usd_eur_daily.parquet` |
| `build/build_jrc_cab_match.py` | JRC + `unit_agents` | no | `data/jrc_ppdb/jrc_cab_match.parquet` |
| `build/build_implied_marginal_cost.py` | MIBGAS + EUA + the match | no | `data/jrc_ppdb/implied_marginal_cost_daily.parquet` |
| `fetch/fetch_jrc_hydro_database.py` | JRC Hydro-power plants database (GitHub) | no | `data/jrc_hydro/jrc_hydro_plants.parquet` |
| `build/build_storage_hours.py` | JRC hydro + `cab` + a hand plant→unit map | no | `data/jrc_hydro/storage_hours.parquet` |
| `fetch/fetch_snirh_reservoirs.py` | APA SNIRH *dados de base* | no, but **LMU eduVPN only** | `data/snirh/snirh_reservoir_series.parquet` |
| `build/build_reactor_outages.py` | PDBF + `cab` + `indisp` + ownership | no | `outputs/tables/reactor_outage_{hours,dose}.parquet`, `reactor_outage_spells.csv` |
| `build/build_outage_events.py` | `indisp` + ESIOS physical units + PDBF + `cab` + ownership | no | `outputs/tables/outage_event_{hours,dose}.parquet`, `outage_event_spells.csv` |
| `build/build_intraday_squeeze_events.py` | `indisp` + reactor outage hours + `curva_pibc_uof` + `marginalpibc` + ownership | no | `outputs/tables/intraday_squeeze_trips.csv`, `intraday_squeeze_cells.parquet` |
| `fetch/fetch_osm_renewables.py` | OpenStreetMap (Overpass API) | no | `data/osm/osm_renewable_plants.parquet`, `osm_wind_turbines.parquet` |
| `fetch/fetch_wri_gppd.py` | WRI Global Power Plant Database v1.3 | no | `data/wri/wri_gppd_iberia.parquet` |
| `fetch/fetch_gisco_nuts.py` | Eurostat GISCO NUTS 2021, 1:1 million | no | `data/gisco/nuts2_iberia.parquet` |
| `build/build_renewable_locations.py` | REE physical units + OSM + WRI | no | `data/osm/renewable_unit_locations.parquet` |
| `build/build_renewable_locations_v2.py` | the first pass + OSM turbine groups | no | `data/osm/renewable_unit_locations_v2.parquet` |
| `build/build_renewable_locations_v3.py` | v2 + MITECO Electra register | no | `data/osm/renewable_unit_locations_v3.parquet` |
| `build/build_water_value_forward.py` | OMIP + day-ahead prices + PDBF + `cab` + MITECO + SNIRH | no | `outputs/tables/water_value_forward.parquet`, `forward_price_quantiles.parquet` |
| `build/build_hydro_cost.py` | `water_value_forward` + step caches + `cab` | no | `outputs/tables/hydro_cost_daily.parquet` |
| `fetch/fetch_esios_i90.py` | ESIOS archive 34 (I90DIA), 15th of each month | **yes** | `data/esios/raw/archives/34/`, `data/esios/i90/i90_sample_hourly.parquet` |
| `fetch/fetch_holidays.py` | BOE holiday resolutions (XML) + Portugal by law | no | `data/holidays/holidays_es_pt.parquet` |
| `fetch/fetch_ree_regional_demand.py` | REE REData, demand by region, monthly | no | `data/ree/ree_demand_ccaa_monthly.parquet` |
| `build/build_holiday_exposure.py` | PDBF retail schedules + holidays + REData | no | `outputs/tables/holiday_retail_days.parquet`, `holiday_exposure*.csv` |
| `fetch/fetch_omie_pdvd.py` | OMIE `pdvd` | no | `data/omie/pdvd/parquet/pdvd_YYYYMM.parquet` |
| `build/build_mic_running.py` | `cab` + bids + step cache | no | `outputs/tables/mic_running.parquet` |
| `fetch/fetch_ember_prices.py` | Ember, European wholesale prices (hourly) | no | `data/ember/ember_prices_hourly.parquet` |
| `fetch/fetch_rte_eco2mix.py` | RTE éCO2mix national (ODRÉ) | no | `data/rte/eco2mix_national.parquet` |
| `fetch/fetch_gme_offers.py` | GME, Italian day-ahead public offers (`OffertePubbliche`) | no, but GME's terms | `data/gme/offers/parquet/offers_YYYYMMDD.parquet` |
| `fetch/fetch_gme_gas_prices.py` | GME, Italian day-ahead gas market (MGP-GAS, PSV) | no, but GME's terms | `data/gme/gas/gme_mgp_gas_daily.parquet` |
| `build/build_italy_marginal_cost.py` | JRC Italy + PSV + EUA | no | `data/jrc_ppdb/italy_implied_marginal_cost_daily.parquet` |
| `fetch/fetch_italy_temperature.py` | Open-Meteo ERA5, 12 Italian cities | no | `data/weather/temperature_population_italy.parquet` |
| `build/build_france_link.py` | OMIE interconnection + Ember + RTE | no | `outputs/tables/france_link_hours.parquet` |
| `fetch/fetch_elexon_bod.py` | Elexon BMRS, balancing offers (BOD) and physical notifications (PN) per unit | no | `data/elexon/{bod,pn}/parquet/<unit>.parquet` |
| `fetch/fetch_ons_gas_sap.py` | ONS, Great Britain gas System Average Price (daily) | no | `data/ons/gas_sap_daily.parquet` |

`lib/omie_common.py` holds shared parsing and DST/resolution logic;
`lib/config.py` loads tokens from a gitignored `.env`; `lib/regions.py` gives a
coordinate its country and region (`locate`); `lib/holidays.py` turns the holiday
table into area × day indicators (`unshared`, `bridges`, `market_wide`); `lib/rd.py` holds the
regression-discontinuity jump and McCrary's density test.

## Data inventory

Window: **2018-01-01 → 2026-05-31**, set by the bid archive's start.
Bids and intraday now run **past** it, to **2026-06-29** (refreshed 2026-09-28;
a ~3-month publication lag — see below), so for June they have no matching
prices, REE or REN yet.
All of `data/` is gitignored — it is large and fully re-fetchable.

### OMIE day-ahead prices — complete
91,247 rows, 3,073 days, zero missing. Columns: `date`, `period`,
`price_pt`, `price_es`, `utc_timestamp`, `resolution_min`.
Spain mean 73.31 €/MWh, range −15.00 to 700.00. ES and PT differ in 6.7% of
periods (market splitting).

### OMIE bid curves — complete to the publication frontier
**102 months 2018-01 → 2026-06, 382,400,912 rows, uniform schema.** Refreshed
2026-09-28; the clearing-identity gap is 0.00% on both new months.

The frontier is **2026-06-29**, 91 days before the refresh — the same
**~3-month publication lag** measured at the first fetch (2026-05-08 on
2026-08-07), as expected for commercially sensitive unit-level offers. No daily
bid files exist (the listing has none, and direct fetches 404); OMIE extends the
frontier month's zip as days are released.

The first fetch left May 2026 at 8 days, and re-running did **not** extend it
until 2026-09-28 — see the frontier-zip trap. Re-running now does. The last ~3
months of any other series will never have matching bids at the time of a
fetch; re-fetch prices, REE and REN before using June 2026.

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

### OMIE unit registry — the key to the bid data
`data/omie/registry/unit_registry.parquet`, built by
`build/build_unit_registry.py` from `pdbc` + `pdbcpt` + `pdbce`. **5,137 units**
over the window (rebuilt with `--full` on 2026-08-12; the earlier 2-day-per-month
sample gave 5,049), columns `unit, country, role_code, role, group_tag,
first_seen, last_seen, days_observed, net_cleared_mwh`.

- **country** — ES 4,960 / PT 150 / 27 unknown. The ES and PT unit sets are
  **disjoint** (zero overlap), so membership is a clean assignment. This is
  the only reliable way to select Portuguese units.
- **role** — generation 3,719, purchase_retail 770, purchase_other 354,
  generation_large 211, storage_mixed 45, pumping 22. Decoded from cleared
  quantity sign/volume, constant within a unit. Separating **generators from
  retailers** is what any supply-curve or bidding work needs.

  **Supply is spread over FOUR roles, and `generation` alone is the wrong
  filter.** `role == "generation"` reads like "keep the generators" and in fact
  drops **all 62 combined-cycle units (29.6 GW), all 7 nuclear (7.2 GW), the 44
  hydro cascade units (14.2 GW) and every pumped-storage unit** — Ascó 1 is
  `generation_large`, not `generation`. What survives is wind and solar, which
  offer at zero, so any bidding measure built on it collapses to a mass point
  at €0 and shows no merit order. Cost a day on 2026-08-18 before it was
  caught. Use `generation`, `generation_large`, `storage_mixed`, `pumping` —
  see `SUPPLY_ROLES` in `scripts/analysis/capacity_quantile_offer.py`.
- **group_tag** — corporate tags (`IB`, `REP`, `GE`, …), 9 distinct,
  populated for only some units.

Validated against Jan-2024 bids: **99.2% of units and 95.1% of cleared volume
match**, `purchase_retail` units never appear on the sell side, and
`storage_mixed` sells a small volume — all consistent with the decoding,
which was derived without reference to those tests.

**No fuel or technology, and no nameplate capacity — in the registry.** The
role code separates generation from demand and isolates storage but will not
distinguish a CCGT from a wind farm.

**Both are now available from `cab` instead** (2026-08-11), token-free — see
the OMIE offer-header section below. `cab` publishes a descriptive plant name
whose prefix encodes technology (`C.C.` ciclo combinado, `C.N.` central
nuclear, `C.T.` térmica, `UOF HIDRO`/`C.H.` hydro, `PS`/`FV` solar, `PE` wind)
and a max-power column validated against published figures. ESIOS/ENTSO-E
tokens are **not** needed for this. The registry itself has not yet been
rebuilt on `cab`.

Now built with `--full` (every day). The earlier default was a
**2-day-per-month sample** (1st and 16th), which left ~5% of cleared volume
with unmatched units. The full parse added 88 units and better first/last-seen
dates, but **not** more `group_tag` coverage — still 9 distinct tags. The tag
is sparse at source, not sparse from sampling.

### OMIE `cab` — the offer header, and what unlocks unit attributes
`data/omie/cab/parquet/`, **113 months 2017-01 → 2026-05, 5,954,579 rows**,
fetched 2026-08-11. One record per unit per day. Token-free.

This is the header accompanying the day-ahead offers in `curva_pbc_uof`, and
it carries three things nothing else token-free publishes:

- **Descriptive plant name** — `ESCCC1` → "C.C. ESCOMBRERAS 1". Technology is
  in the prefix (see the registry note above).
- **Max power in MW** — validated: Ascó 1 reads 1028.0 (published ~1032),
  Escombreras 1 reads 408.6 (~400).
- **The minimum income condition**, as a fixed term (€/day) and a variable
  term (€/MWh). This is the complex condition behind the whole-day withdrawals,
  and the primitive Reguant (2014) uses to identify startup costs.

Fixed-width, latin-1, **dot decimal** — unlike `curva_pbc_uof`, which uses a
comma. Do not share a number parser between them. **Two layouts: 169 chars
until 2025-03-18, 94 chars from 2025-03-19** — see the trap below.

**The minimum income variable term ends at 2025-03-18 — because the market
design changed, not because OMIE withheld it.** Resolved 2026-09-03 from
OMIE's own published spec (see below). On 2025-03-19 the old complex condition
was replaced by the **SCO** (*Scalable Complex Order*) for the European single
day-ahead coupling, and the header now publishes **one** lump-sum `Fijoeuro` in
EUR instead of a fixed €/day plus a variable €/MWh term. The variable term no
longer exists as a separately declared parameter; what replaces it is the SCO's
own scalable price tranches in `det`, which from the same date carry a **MAV**
(Minimum Acceptable Volume) per offer.

**The two fixed terms are different quantities and must never be spliced.**
ABO1 (C.T. Aboño 1, 351 MW) declares 24,000 €/day fixed and 127.50 €/MWh
variable on 18 March, and a single 601,620 € on 19 March. Nor is it the same
population: across those two days 19 units declare a wide fixed term and 53 a
variable one, against 31 declaring an SCO fixed term. They are held in separate
columns, `min_income_fixed_eur` and `sco_fixed_eur`. So the conclusion is
unchanged in substance — **declared start-up costs on a consistent basis run
2017-01-01 → 2025-03-18** — but `sco_fixed_eur` is a usable primitive after
that date, not a hole.

Validated on January 2024: units declaring no minimum-income condition
withdraw for a whole day **4.1%** of the time; units declaring one, **81.1%**;
and units whose variable term exceeds the day's *highest* clearing price,
**94.2%**. The condition does what the market rule says it does.

**All nine numeric fields are now named**, from OMIE's own specification —
*Modelo de Ficheros para la distribución pública de Información pública*,
**v1.35** (the last edition describing the wide layout) and **v1.37** (current),
public PDFs at
`https://www.omie.es/sites/default/files/<YYYY-MM>/formato_ficheros_inf_pub_<v>.pdf`.
Of the six previously carried unnamed, **two are documented as unused** (verified
`0.000` on every row) and **four are ramp rates** — `MaxRamSub`, `MaxRamBaj`,
`MaxRamArr`, `MaxRamPar`. Do not get excited about the ramps: on 2025-03-18 only
5 of 2,454 units declare a non-zero up or down ramp and none declare a startup or
shutdown ramp, and **the spec gives no unit of measure**, so they are carried
under OMIE's field names without a unit suffix.

Fetch the spec before touching any OMIE fixed-width parser. Every position in
this repo's `cab` parser was reverse-engineered from the files until 2026-09-03,
and one of those guesses was wrong — see the whitespace-splitting trap below.

#### The minimum income condition is a *declared* start-up cost

Worth stating plainly, because it is the single most unusual thing in this
dataset. `cab` publishes, **per unit per day**, a firm's own statement of what
it needs to earn to run: a fixed term in €/day and a variable term in €/MWh.

The empirical literature treats that quantity as something to be *recovered*:

- Reguant (2014) models the optimal declaration of the condition in order to
  identify start-up costs structurally.
- Jha & Leslie, *Start-up Costs and Market Power: Lessons from the Renewable
  Energy Transition* (SSRN 3603627), build a dynamic competitive benchmark that
  estimates start-up costs from production data, and show that **static markups
  overstate the rents attributable to market power** when start-up costs are
  ignored. Their headline correction depends on a primitive they must estimate.

Here it is published daily. That is a genuine data advantage and it cuts both
ways for our own results: any static Lerner index computed in this repo is
**biased upward** for the same reason Jha & Leslie identify, and this file is
what would let the correction be made with a declared rather than an estimated
number.

**It is not marginal cost, and must not be used as one.** The declaration is a
strategic choice — that is precisely why Reguant models it. What it supports is
a *bound*: a firm that says it needs `fixed + variable × q` will not accept less,
so its avoidable cost is at most that, and `price − (variable + fixed/q)` is a
lower bound on realised markup, revealed by the firm itself.

Three limits on the selection. Only units that *declare* a condition give this
(53 of them on 2024-01-15, 48 of which are combined cycle — the marginal
technology, but a narrow and non-random slice). The condition binds on **daily**
revenue, not per period. And the declaring units are precisely those with
binding start-up costs, so the sample is selected on the variable of interest.

### `cab` names identify the bidding **agent**, not the plant owner
Unit codes carry a 3-character alphabetic mnemonic (`EDP`, `IBE`, `GGN`,
`GRE`, `EGE`) that identifies the market agent. **344 distinct prefixes across
3,940 generation units; 54 prefixes cover 80% of generation volume, 100 cover
94%** — so a hand-built mnemonic→firm dictionary is bounded work.

It cannot be learned from OMIE's own labels: `group_tag` covers 121 units
(18.8% of volume), and propagating it along prefixes reaches only **22.4%**,
because the labelled set excludes the largest players.

Two cautions. Several large prefixes are **traders representing third-party
assets** — `EGV` is Axpo, 394 units and 6.7% of volume — and unit names like
"UOF REPRESENTADA DE ARRUBAL 1" say so explicitly. And the largest units are
**owner-level portfolios**, not plants: `EDPSVD1` "VENTA RE" at 6,500 MW,
`IBEVD11` "EÓLICA HABILITADA" at 5,906 MW. For market power that is arguably
the right object — the agent controlling the bid — but it is *not* plant
ownership, and the two must not be conflated.

### Who controls a unit's bid — 88% of the near margin, rebuilt 2026-08-17
`data/esios/esios_programming_units.parquet` — **3,872 units, 738 agents, 41
technologies, EIC at 100%**, from ESIOS archive 82. **Token-free**, unlike the
ESIOS indicator API; the web page is JS-rendered with no export, the JSON is at
`api.esios.ree.es/archives/82/download_json?locale=es`. It is a **snapshot**
with no entry/exit dates — record the fetch date with anything derived from it.

**OMIE confirmed on 2026-09-03 that no historical unit listing exists for
2021.** They supplied point-in-time listings for 2024, 2025 and 2026 on request
(the 2025 one dated 31/01/2025), but stated plainly that the information is
updated continuously and no complete historical series is kept for all dates.
So every unit→agent attribution in this repo is a **forward or backward
projection from a snapshot**, and the further from the snapshot date, the
weaker it is. That bears directly on the 2021 windfall-levy question in
[`rq-clawback-size-rdd.md`](notes/rq-clawback-size-rdd.md): its treatment varies
at parent-firm level in 2021, five years before the earliest listing, and no
source has been found that would validate the mapping for that year. Check this
before building on it, not after.

`Sujeto del Mercado` is the market agent, the entity that *decides the bid*.
Nothing in the OMIE files publishes it, and it is the grouping every
market-power measure needs: residual demand facing firm *i* requires knowing
which units are *i*'s.

**Four entities, do not conflate them.** A *plant* is physical. A *unit* (UP)
is a market registration — sometimes one plant (`ASC1`), sometimes a whole
cascade (`ADOURO`), sometimes a 6,500 MW portfolio (`EDPSVD1`). An *agent* is
who submits the offer. A *firm* is the group above the agent (`IBEG`, `IGNU`,
`IBGT` are all Iberdrola); ESIOS gives agents, not groups.

ESIOS is REE's **dispatch** registry, so it omits the commercial aggregation
vehicles that exist only to bid — 592 of our codes match. `build_unit_agents.py`
layers three sources (ESIOS exact match; ESIOS agent code appearing inside a
`cab` plant name, e.g. `GREPSC1` = "REPSB GENERICA VENTA"; then a hand-checked
prefix dictionary) to reach **89.1% of near-marginal offered volume** (rerun
2026-08-17 on Jan-2024, after hand-verifying five more prefixes against OMIE's
own published agent list — `REP`→Repsol, `GAS`/`GGA`→Naturgy, `GTG`→
TotalEnergies, `IBG`→Iberdrola; see the trap below on the one wrong guess this
caught before it went in. The prefix dictionary grew substantially during the
gas-cap and levy work too, and an earlier **45.3%** figure recorded here was
stale — left as a dated note rather than silently deleted).

**`agent_owner`, added 2026-09-03, is a second opinion that covers far more.**
`build_unit_agents.py` now also carries OMIE's *published* owner from
`omie_unit_lists.parquet`, alongside the inference chain rather than replacing
it: **4,055 of 5,137 units against 2,441**, and **99.8% of near-marginal
offered volume against 89.1%**. It resolves every prefix `PREFIX_AGENTS`
deliberately left unmapped (`CEV` Energya VM, `IGV` **and** `IGN` both Ignis
Energía, `NEX` Nexus, `VGE` Repsol, `GAL` Galp, `GES` Gesternova, `PEG` Endesa,
`CLI` Holaluz-Clidom) — so three of the hand-researched conclusions recorded
below are wrong, and the `IGN` note is wrong in its reasoning even though it
was right to reject Iberdrola.

**`agent_owner` names legal entities; `build_owner_groups.py` rolls them up.**
`data/omie/registry/owner_groups.parquet` maps **1,451 owner strings to 1,090
groups** (1,096 before the 2026-10-02 merges) on three evidence layers: the independent ESIOS chain's verdict on an
entity's own units (**81.7%** of supply volume), a stem match onto a group that
layer established (2.0%), seven hand-verified cases (0.3%), and **13.3% left
standing as their own group** because no merge evidence was found.

**Two group-level merges: `ENEL` → `ENDESA` (2026-09-29) and `EDP COMERCIAL` →
`EDP` (2026-09-30)** (`GROUP_MERGES` in `build_owner_groups.py`; Enel is 2.1%
of supply volume). Enel Green Power España is 100%
owned by Endesa Generación, which bought the remaining 60% in 2016, so for the
whole window. Layer 1 had grouped it as `ENEL` because ESIOS labels its agent
after the legal name; two of the entity's own units (`ECY*`) carry the ESIOS
agent "Endesa Cogener y Renovables", which the chain assigns to ENDESA. Standing
apart, it made Endesa's residual-demand slope count Endesa's own renewables as a
rival's. The manual layer could not do this: it only fills entities layer 1 left
open, so a merge of two layer-1 *labels* needs its own mechanism. EDP Comercial,
EDP's Portuguese liberalised retailer (100% EDP, Integrated Annual Report 2024),
is merged on the same mechanism; the midday-hydro panels already counted it in
EDP's net position and the firm panel did not. Without the roll-up
`SU ELETRICIDADE` — 7.3% of supply volume, EDP's Portuguese regulated supplier —
reads as a firm in its own right, and Repsol splits across nine entities.

**Seven more merges on 2026-10-02, all renamings** the layers had left apart
(notes/report-ownership-mapping.md): Total → TotalEnergies, Clidom → Holaluz, both
BP entities (the stems had taken "GAS" and "GAS EUROPE"), both PH Energia
entities (the stems had taken the Portuguese legal forms "LDA" and "UNIPESSOAL"),
Aldro → Eni Plenitude. Exactly ten owner strings changed group.

**Ownership by date and by share — `lib/unit_ownership.py` (2026-10-02).** Until
then the firm panels gave each unit its latest listed owner for the whole window.
That put each **co-owned nuclear reactor whole with one co-owner, not always the
largest**: Almaraz 1 (Iberdrola 52.7%, Endesa 36.0%, Naturgy 11.3%) and Trillo
(Iberdrola 49%, Naturgy 34.5%, Iberenergía 15.5%, Endesa 1%) went to Naturgy,
Vandellós II (Endesa 72%, Iberdrola 28%) to Iberdrola. Over 2018–2026 that
overstated Naturgy's average net position by about 315 MW, half its mean, and
understated Endesa's by about 268 MW. It also left sold businesses with their
buyer for the whole window: EDP Comercializadora (EDP's Spanish retail, sold to
TotalEnergies on 2020-12-01) and Viesgo (Repsol's only from 2018-11-02).

The module gives the owners in force on any date: each listing's owners from its
date to the next listing naming the unit, shares normalised to 1, spells split at
the dated sales in `ENTITY_CHANGES`, and the inference chain's owner (share 1) for
units no listing names. `attach_owners` splits a row across owners with its volume
times each share. **A dormant registration keeps a stale owner in the listings**, so
a dated unit sale (`UNIT_CHANGES`) takes effect at the first later listing whose group
differs from the seller's, not at the next listing. Castejón's represented units
`CTJON1R`/`CTJON3R` are the case: BAJA and listed under EDP España to 2022-02-08,
TotalEnergies' on 2025-01-31, offering from 2024-02-01. The next-listing rule gave
that year of Castejón to EDP, 120 MW of its mean net position (fixed 2026-10-22). `firm_x.py`, `firm_incentive_rebuild.py` and
`residual_demand_firm.py --tier owner` use it; `qa/check_unit_ownership.py` pins the
reactors' shares, the sale dates, and that January 2024 rebuilt through each of the
three differs from the static attribution by exactly the share changes.
**The stored panels and legs C and D were rebuilt on it on 2026-10-03**
(`.superpowers/sdd/2026-10-02-ownership-rerun/chain.sh`, 19 steps, all checks pass;
old against new in `notes/handoff-2026-10-05.md`). Every builder of the leg C/D panels
and instruments uses it. **Leg A and the descriptive scripts followed on
2026-10-05** (`edp_hydro_panel.py`, `hydro_within_day_probe.py`,
`hydro_schedule_routes.py`, `firm_net_position.py`, `own_demand_in_band.py`,
`firm_shares_hourly.py --tier owner`, `markdown_contract_test.py`,
`iberdrola_contract_trace.py`, `iberdrola_self_supply.py`; old against new in the
running notes). Older designs still read the static owner.
**The listed shares are confirmed by the bilateral flows**: a co-owned reactor's
bilateral output goes to each co-owner's retail arm in about its ownership share
(Almaraz 1, June 2023: 0.557 / 0.330 / 0.113 to Iberdrola / Endesa / Naturgy
against 0.527 / 0.360 / 0.113).
Iberenergía (Trillo's 15.5%) is merged into EDP (`GROUP_MERGES`): a 100% subsidiary
of Hidroeléctrica del Cantábrico (CNMC INF/DE/0178/14). Under dated ownership
Endesa's Energía XXI and Repsol's Regsiti are caught as regulated pass-through
suppliers too (Endesa: −282 MW mean), which the static owner missed.

**Regulated pass-through suppliers are excluded from every firm's net position**
(`is_pass_through` / `exposed_group` in `lib/omie_owner.py`, pinned by
`qa/check_exposed_position.py`). SU Eletricidade (in EDP) and Curenergía (in
Iberdrola) buy and sell volume whose cost is passed through to regulated
tariffs. Left in, they made EDP look like a net seller when it is a net buyer in
72–89% of periods, and they carried the first stage of the withdrawn leg B
(`notes/rq-midday-hydro.md` §3.20). `analysis/firm_x.py` is the one place X is
computed for the five large firms; `firm_incentive_rebuild.py` computes the same
correction for all firms, and the two agree exactly.

Two gates in that script are load-bearing, both learned from real failures.
Layer 1 refuses a modal ESIOS firm supported by too few of an entity's own units
(`GALP ENERGÍA`: 41 units, **one** carrying a firm, reading IGNIS). Layer 2 sets
a higher bar still, because stem propagation *amplifies* thin evidence
(`ENERGYA VM GESTIÓN` reads CENTE on 3 of 25 units; propagating that would
relabel a sibling holding 392 units and 2.3% of supply volume). `VIESGO` →
Repsol survives both, on 6 independently-agreeing units.

**It is not a drop-in replacement for `agent`, because it names a different
entity** — the commercialising entity that submits the offer, where `agent` is
the registered operator. `ABA1` is Barbo Energías Renovables in ESIOS and Wind
to Market in the listing; `ACE4` is Naturgy Ciclos Combinados and Gas Natural
Comercializadora. For market power the listing's entity is usually the one you
want. Companion columns `agent_owner_pct`, `agent_owner_snapshot` and
`agent_owner_changed` come with it; **548 units change owner across snapshots**,
so do not treat the column as static. Full detail in
[`docs/unit-agent-mapping.md`](docs/unit-agent-mapping.md).

**Measure coverage on the near-marginal band, never on total volume.** Price is
set at the margin: a 5 GW unit offering at 0 €/MWh is inframarginal almost
always and contributes nothing to the slope of residual demand, so
total-volume coverage flatters the mapping for the units that matter least.

`build_unit_agents.py` also rolls agents up to a **parent firm** using the
legal names in ESIOS archive 83 (`IBEG`, `IGNU`, `IBGT` are three agents and
one Iberdrola). **68 parent firms, 82.4% of generation volume** (rerun
2026-08-18; an earlier "17 firms, 39.1%" recorded here was stale for the same
reason as above, and 81.9% predates the twin layer below). Top eight: EDP 15.5%, Endesa 13.9%, Naturgy 9.5%, Iberdrola
9.3%, Axpo 6.8%, Acciona 5.2%, Repsol 3.5%, Wind to Market 2.4%. **EDP is now
the largest attributed firm, not Axpo** — an earlier note here naming Axpo as
largest predates the prefix-dictionary expansion.

**Layer 4, the twin layer (added 2026-08-18): a plant registered twice
inherits its own owner.** OMIE registers the pumping leg of a hydro cascade and
the *representada* version of a plant as separate units, and frequently
attributes the owner to one registration and not the other — `ALIMA` "LIMA"
resolves to EDP while `ALIMAB` "BOMBAS DO LIMA" did not. Two rules, each
requiring positive evidence that this is a second registration: the unit code
is a mapped code plus a trailing `B` (*bombagem*) or `R` (*representada*), or
the description contains a pumping/represented marker and matches a mapped
unit's name once that marker is stripped. It fills 12 units and refuses 8
ambiguous names.

**A shared description alone is deliberately NOT a rule.** The first version
allowed it and proposed `SOECC01` "BUY BID UNIT" from `TOECC01` "BUY BID UNIT",
`FENVD03` "EOLICA" from `IBGEVD1` "EÓLICA", and `DCESC01` "UNIDAD DE
COMERCIALIZACION" — boilerplate labels shared by unrelated agents. Every
accepted pairing is printed with both descriptions at build time; read them.

**Measure firm coverage by capacity, not by unit count.** On the 383
dispatchable units the two differ enormously: **62.9% of units but 96.0% of
capacity** (up from 91.3% before the twin layer). The unmapped residual is
almost entirely small cogeneration and micro-hydro.

**Only 32 parent firms own dispatchable plant at all** — 26 with a computable
pre-2021 renewable exposure, 11 above 1,000 GWh. That is the population, not a
sample, and it is a hard ceiling: any design whose treatment varies at
parent-firm level has at most a few dozen clusters. It is why the differential
renewable exposure design was withdrawn (see `a2a8c7a`), and it should be
checked *before* building any further cross-firm design, not after.

**These firm shares are not market shares.** They are the share of *generation*
volume that could be attributed; **18.1% is unattributed** at the firm level
(more once retailers/purchasers are counted). Do not substitute them for s_i
in Lerner = s/eta without saying so. Axpo remains a **representative** trading
third-party assets rather than a producer -- see `agent_type` in archive 83,
which flags 11 of 739 agents as `Representante`.

Prefixes whose owner could not be established *from the data* are left
unmapped on purpose. As of the 2026-08-17 rebuild the largest are `CEV`
(2.4% of generation volume), `IGV` (1.5%), `NEX` (1.4%), `IGN` (1.4%), `VGE`
(0.9%), `GAL` (0.9%), `GES` (0.7%), `PEG` (0.7%) — `GAS`/`GGA`/`GTG`/`IBG`
are now resolved (see above). Several of the rest were tried by hand against
OMIE's own agent list and explicitly **withdrawn** on inspection rather than
left silently unmapped:

- **`IGN` was hypothesised as Iberdrola** ("Iberdrola Generación") and
  withdrawn — its cab names ("UOF XALLAS I", "SOLAR MULA", "GALICIA VENTO")
  never mention Iberdrola, and OMIE's own agent list gives Ignis Energía's
  actual codes as `IGNIS`/`IGNS1`/`MORTE`/`CYDDP`, none of which is `IGN`.
  See `PREFIX_AGENTS` in `build_unit_agents.py`.
- **`IGV`** ("MOLINOS DEL EBRO, S.A.") is genuinely mixed ownership within
  one prefix — some units trace to Grupo Samca, one ("Renovables del
  Cierzo") to Statkraft (post-2023 acquisition of Enerfín) — so a single
  prefix→firm assignment would be wrong for part of the bucket.
- **`GAL`/`CLI` have one verified plant each, not a verified prefix**: `GAL`
  contains Extresol I/II/III (ACS/Cobra Energía per public reporting); `CLI`
  contains SEAT's Martorell cogeneration plant (Cofely España, part of
  ENGIE, per its own filings — but Cofely's actual OMIE code is `ELYM`, not
  `CLI`). Neither generalises to the rest of its prefix's units without
  checking each one, so neither is encoded.

A guess across the rest would silently corrupt every market-share and markup
figure downstream.

`det` (offer detail) was checked and carries **no** agent field — it is
price/quantity steps keyed by the same 7-digit unit id as `cab`.

Full documentation of the mapping — layers, fields, coverage, glossary and the
five ways it can mislead — is in [`docs/unit-agent-mapping.md`](docs/unit-agent-mapping.md).

### OMIE's *Listado de Unidades Ofertantes* — the authoritative registry
`data/omie/registry/omie_unit_lists.parquet`, built by
`build/build_omie_unit_lists.py` from 12 dated PDFs in `data/omie/unit_lists/`.
**51,703 rows, one per unit per snapshot.** Columns: `snapshot`, `unit`,
`descr`, `agent_owner`, `ownership_pct`, `unit_type`, `status`, `zone`,
`technology`.

Obtained by asking OMIE directly (ticket #12541), not scraped. This settles
what the rest of this file spends pages reconstructing: `agent_owner` is the
owning company **published by OMIE with an ownership percentage**, and
`technology` is OMIE's own label. Undocumented here until 2026-09-03 although
eight analysis scripts already read it.

| snapshot | units | technology | agent_owner |
|---|---|---|---|
| 2014-09-24 … 2020-03-09 (8 snapshots) | 3,656–5,102 | **0%** | 100% |
| 2022-02-08 | 5,899 | 93.0% | 100% |
| 2023-05-16 / 2023-12-30 / 2025-01-31 | 2,803 / 2,978 / 3,331 | ~99.4% | 100% |

**They are snapshots, not spells.** A unit's agent between two snapshots is
unobserved; an ownership change is locatable only to the bracketing interval.
The builder prescribes the nearest *preceding* snapshot when attributing a bid,
which is right for **ownership**. For **technology** the rule is the nearest
snapshot in *either* direction, since the first one carrying a technology at all
is 2022-02-08 — see the backward-projection argument below.
`marginal_technology.py` took the latest snapshot for every year until
2026-09-03, which pushed the 2025-01-31 relabelling back onto 2018; it now
labels each period from the nearest snapshot per unit.

**No 2021 snapshot exists and none can be obtained** — see the ESIOS section
above for OMIE's statement that no historical series is kept.

**These 12 PDFs are the only genuinely irreplaceable files in `data/`.** The
gitignore convention rests on `data/` being re-fetchable; that is false here,
because OMIE does not keep history. About 6 MB. Back them up.

### Technology coverage — superseded from 2022 by OMIE's own listings
**Read this before believing the 41.2% figure below.** Everything in this
section describes `unit_agents.parquet`, the hand-built inference chain, and it
is still accurate *about that file*. It is **no longer the repo's ceiling**:
`data/omie/registry/omie_unit_lists.parquet` (see the section above) publishes
OMIE's own technology label, and eight analysis scripts — including
`marginal_technology.py`, the very script that asks which technology sets the
price — already read it instead.

Measured 2026-09-03 on offered sell volume, nearest-preceding snapshot:

| month | cab `tech` | OMIE listing | union |
|---|---|---|---|
| 2018-06 | 81.1% | **0.0%** | 81.1% |
| 2020-01 | 77.4% | **0.0%** | 77.4% |
| 2024-01 | 78.1% | 99.5% | 99.7% |
| 2025-05 | 80.3% | 99.1% | 99.4% |

**The listings carry no technology before 2022-02-08.** All eight snapshots from
2014-09-24 to 2020-03-09 are 0% technology and 100% ownership — OMIE added the
column to the listing format later.

**That gap is closed by projecting the 2022-02-08 label backwards, and unlike
ownership the projection is defensible** — `tech_omie_early` in
`unit_agents.parquet`, added 2026-09-03. Technology changes for 2.07% of units
across the four technology-bearing snapshots against 6.19% for ownership; most
apparent instability is OMIE renaming its own categories; and the projected
class agrees with the independent `cab`-name technology on 93.3% of units, or
**98.7%** once sub-classes differing in granularity rather than kind are
collapsed. Coverage of near-marginal offered sell volume, against `cab` alone:

| year | projected from 2022-02-08 | `cab` names alone |
|---|---|---|
| 2018 | **100.0%** | 94.9% |
| 2019 | 99.9% | 92.4% |
| 2020 | 99.6% | 93.7% |
| 2021 | 94.9% | 77.9% |

**Do not project ownership the same way** — it changes three times as often, and
548 units change owner across the snapshots. The asymmetry is the whole argument;
see `attach_listing_tech` in `build_unit_agents.py` for the full statement,
including the one assumption that cannot be tested.

**The 41.2% and 63.3% figures below do reproduce**, but only on one specific
basis, which was never written down: `abs(net_cleared_mwh)` summed over the four
`SUPPLY_ROLES`, with the share being units carrying `tech` (or `regime`) —
exactly what `build_unit_agents.py` prints. Other readings of "of generation
volume" give materially different answers (positive cleared volume only:
47.7%/74.9%; `role == "generation"` alone: 22.8%/63.6%), so state the filter
when quoting them.

ESIOS is close to exhausted for this: only **128 of our 3,930 generation units**
appear in its programming-unit registry, because REE registers dispatchable
plant and the registry is dominated by retailers (933 of 6,627 physical units
are `Comercializadores mercado libre`). Archive 81 carries a `up` field linking
physical units to programming units, but it inherits the same 128.

So technology comes from `cab` names, in two tiers:

- **`tech`** — a specific technology, from an explicit marker in the name.
  1,474 units, 41.2% of generation volume.
- **`regime`** — *Régimen Especial* (renewables, cogeneration, waste) versus
  *Régimen Ordinario* (conventional thermal, hydro, nuclear), read off names
  like "AXPO VENTA R. ESPECIAL 042". 2,037 units, **63.3% of volume**
  (2026-08-17 rebuild; was 59.9%). A weaker claim than a technology, kept in
  its own column rather than folded into `tech`, but it still rules out half
  the stack for a marginal unit.

**Hydro is named after rivers, not after technology.** `ALIMA` is "LIMA",
`ACAVADO` is "CAVADO", `TEMON` is "SISTEMA TEJO-MONDEGO", `GUADIA` is "BACIA
HID. DO GUADIANA". Matching only `HIDRO`/`C.H.` left the seven largest
Portuguese cascades unclassified — together ~41% of all unidentified marginal
periods — and made hydro look like a declining marginal technology when it is
not. River and basin names are now matched explicitly.

### OMIE `pdbf` — the operating schedule, and the contract position
`data/omie/pdbf/parquet/`, fetched 2026-08-13, token-free. Same field layout as
`pdbce`, so no new parsing was needed. One row per unit per period.

Columns: `date`, `period`, `resolution_min`, `unit`, `unit_id`, `schedule_mw`,
`role_code`, `group_tag`.

**Why it is here.** It publishes the **physical contract position** — energy
committed at a price fixed outside the auction. That is the `theta` term in
Wolak (2000) and Hortaçsu & Puller (2008): volume already sold forward earns
nothing extra when the day-ahead price rises, so a heavily contracted firm has
a weaker incentive to withhold whatever its share. Jha & Leslie spend an
appendix inferring it because Australian contracts are not public.

**`role_code == "4"` is the bilateral contract — read it directly, do not
compute PDBF minus PDBC.** Its sell and buy legs are exactly equal (0.0000 gap
in every month tested 2018–2026), which is the matching identity a bilateral
contract must satisfy and the subtraction cannot check.

| year | scheduled sell | under bilateral contract |
|---|---|---|
| 2018 | 413.6 TWh | **46.5%** |
| 2022 | 416.3 TWh | **48.5%** |
| 2024 | 346.7 TWh | **38.9%** |

**PDBF has several rows per unit-period, one per role code**, so
`(date, period, unit)` is *not* a key — joining cleared volume onto it without
aggregating first fans the auction volume across those rows. That produced a
spurious "36% → 5% collapse" in an early cut; the measured decline is 8pp.
Only role 4 carries a `group_tag`, and on those rows `unit_id` is the contract
id rather than the registration id.

**Still a proxy for theta, not theta.** It captures *physical* bilateral
contracts only and misses **financial** hedges entirely — an OMIP future or a
financially settled PPA fixes revenue while the energy still clears in the
auction. Since what matters is whether *revenue* is fixed rather than whether
electrons flow bilaterally, that omission is the more serious one. Bound it; do
not claim to measure it.

`--verify` re-derives PDBF against the auction per month and flags any month
where PDBF sell falls below cleared sell, which would be a parse failure rather
than a market fact. January 2024 gives **1.73×**, independently reproducing the
figure below.

**`schedule_mw` is average MW, not MWh** — see the trap below.

### CNMC publishes shares on PDBF, not on the day-ahead auction
**PDBF** = *Programa Diario Base de Funcionamiento*, the daily operating
schedule: the day-ahead auction result (**PDBC**, *Programa Diario Base de
Casación*) **plus bilateral physical contracts and self-scheduling**. On
January 2024 the PDBF sell total is **1.73×** day-ahead cleared volume.

Comparing CNMC's shares to day-ahead cleared shares therefore makes firms look
under-mapped when they are not. Measured on PDBF our mapping gives Iberdrola
22.2% against CNMC's 20%, Naturgy 5.2% against 6%, Acciona 4.3% against 4%.

This is economically substantive, not bookkeeping. For market power **in the
day-ahead auction** the relevant share is day-ahead exposure: volume sold
forward at a fixed price earns nothing extra when the day-ahead price rises —
the contract-position term in Wolak (2000) and Hortaçsu & Puller (2008). Using
PDBF-based shares **overstates** the day-ahead markup incentive.

OMIE publishes `pdbf` as its own dataset, same schema as `pdbce`, so a
like-for-like comparison needs no new parsing.

### The intraday session regimes overlap — they did not switch cleanly
MIBEL's own 6-7 intraday sessions and the European IDA auctions **ran in
parallel from 2025-03 to 2025-06**, and the two are distinguished only by the
width of the session digits in the filename: two digits (`01`..`07`) for the
old sessions, one (`1`..`3`) for IDA1-IDA3. Full changeover is 2025-07.

This bites twice. A regex requiring two digits returns **zero rows** for
2025-07 onward — which fails loudly — but during the overlap it silently
parses *part* of a month and reports success: 2025-06 yielded only 22 of 90
files that way, 2025-03 90 of 101, 2025-05 91 of 96. Audit member counts
against the zip rather than trusting a clean exit.

`session` is therefore **not comparable across the boundary**: 1-7 before,
1-3 after, with different meanings and an overlap period where both appear.

**Intraday adopted the 15-minute MTU on 2025-03-19, over six months before
the day-ahead market did (2025-10-01).** Corrected 2026-09-03: an earlier note
here said June 2025 and was simply wrong. Re-derived from `resolution_min` in
the files — 2025-03-18 is the last day carrying any 60-minute rows (it carries
both, the first quarter-hourly intraday auction having been held that afternoon
for delivery on the 19th) and every day from 2025-03-19 is pure 15-minute. The
two markets run at different resolutions for those six months, so read
`resolution_min` per file rather than inferring it from the date.

### OMIE intraday bid curves — complete
**102 months 2018-01 → 2026-06, 588,054,115 rows**, uniform schema — larger than the
day-ahead archive. Unit-level offers for each intraday **session**, where
wind and solar forecast errors get corrected after the day-ahead auction.

Same row format as the day-ahead files, so `parse_member` is shared; the
session index exists **only in the filename**
(`curva_pibc_uof_YYYYMMDD<SS>.1`) and is added as a `session` column. Rows
carry their own delivery date, which can differ from the filename date — the
row date is authoritative.

Cleared intraday sell volume is ~18% of day-ahead (Jan 2024), as expected for
an adjustment market. The frontier is 2026-06-29, the same as the day-ahead
bid frontier (refreshed 2026-09-28; it was 2026-05-11). A few session files are
published **empty** (e.g. session 4 on 2020-04-01) and correctly yield no rows.

Parsing is streamed one row-group per source file: the IDA-era months are
~17 M rows each and buffering a month in memory exhausts it.

### OMIE `marginalpibc` — published intraday prices, and why deriving fails
`data/omie/intraday_prices/omie_intraday_prices.parquet`, fetched 2026-08-21,
token-free. **411,263 rows, 2017-12-31 → 2026-08-20, sessions 1-6.** Columns:
`date`, `session`, `period`, `price_a` (Portugal), `price_b` (Spain).

**`price_a` is Portugal and `price_b` is Spain — the same PT-then-ES order as
`marginalpdbc`, confirmed from the data rather than assumed by analogy.** On the
864 periods of 2018 where *both* markets split, `price_a` sits 3.94 €/MWh from
the day-ahead PT price and 9.19 from ES, while `price_b` sits 2.71 from ES and
7.68 from PT.

**The intraday clearing price cannot be derived accurately from the bid
archive.** In a uniform-price auction it is bracketed by `max(cleared sell) ≤
p* ≤ min(cleared buy)`, but checked against the published files on 1,875
date-session-periods:

| estimator | median abs err | p95 | exact | mean err |
|---|---|---|---|---|
| max cleared sell | 0.010 | 7.802 | 48.8% | **+1.069** |
| min cleared buy | 0.000 | 3.876 | 53.7% | −0.651 |
| bracket midpoint | 0.245 | 7.139 | 22.2% | +0.209 |

The day-ahead/intraday premium is about 1 €/MWh, so a p95 error of 3.9-7.8
swamps it. And `max(cleared sell)` is a *lower* bound whose error should never be
positive — it is positive on 10% of rows, averaging +5.28 there.

**Filenames are `marginalpibc_YYYYMMDD<SS>.1` — date PLUS a two-digit session
index**, not one file per day. A date-only guess 404s on every request and reads
as "the dataset does not exist" rather than "the pattern is wrong". As with
`marginalpdbc`, **2018-2022 exist only as yearly zips** and 2023 onward as daily
files.

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

### Implied CCGT marginal cost — the first real cost primitive, not a declared one
Built 2026-08-18 from three separate fetches plus a matching layer, in
response to CLAUDE.md's own cost section noting that nothing token-free here
gives an actual engineering marginal cost — `cab`'s minimum-income condition
is a *declared*, strategic number (see above), not a fuel cost. This
constructs `gas_price / efficiency + 0.2020 * co2_price / efficiency` per
unit per day — 0.2020 tCO2/MWh(th) being the EU ETS MRR Annex VI default
emission factor for natural gas, a regulatory constant, not fetched data.

**Three inputs, three different fetch problems:**

- **Efficiency** — `data/jrc_ppdb/jrc_spain_units.parquet`, from the JRC's
  open power-plant database (Zenodo, CC-BY, static, no registration).
  **1,827 Spanish generating units, 456 with a non-null efficiency** — but
  only 66 of the underlying generator rows are `OEM_derived` (from real
  equipment specs); most of the rest are `Class_derived`, a technology-class
  *average*, not a measurement — see the trap below. JRC identifies units by
  ENTSO-E EIC code, sharing no key with any OMIE dataset.
- **Gas price** — `data/mibgas/mibgas_price_index_daily.parquet`, MIBGAS's
  own "Market Results" workbook, found by fetching the page's AJAX fragment
  directly (`/es/ajax/node/1184`) since the page itself is a JS SPA with no
  visible static link. **3,152 days, 2018-01-01 → 2026-08-18, 100% coverage,**
  mean 38.75 €/MWh, range 4.17–225.03 (the August 2022 gas crisis).
- **CO2 price** — `data/investing/eua_carbon_price_daily.parquet`. Took
  eight sources to find: CBAM Guide (spot only), Sandbag's "Carbon Price
  Viewer" (a static cropped JPEG, not the interactive chart it looks like),
  ICAP, Ember (real API, wrong quantity — carbon *intensity*, not *price*),
  EEX's free widget (real EUA auction data, but capped to a rolling ~6-week
  window no matter what date range is requested), KRBN (a real proxy, but
  only from 2020-07-31), and EUTL registry data (annual, not a price
  series) were all tried and ruled out before investing.com's own
  historical-data page (ticker `CFI2Z6`, the front-month ICE ECX EUA
  future) turned up the real thing. **2,217 days, 2018-01-02 → 2026-08-18,**
  mean 55.38 €/tCO2, range 8.07–98.01. See the trap below on why this one
  fetcher is not resumable.

**Portugal, added 2026-10-05: `jrc_portugal_units.parquet`, 75 units, 16
thermal, every one with an efficiency** (gas 0.54–0.55 manufacturer-based: Lares,
Ribatejo, Pego and Tapada do Outeiro combined cycles; coal 0.37–0.40 from emissions:
Sines and Pego, both closed in 2021). JRC lists them generator by generator, one for
one with OMIE's units, so they enter the match through a checked hand table
(`PT_GENERATOR_MATCH`: capacity within 6%, same unit number, same fuel), not the
plant aggregation Spain needs. OMIE's Turbogás units are JRC's "T.Outeiro C.C.".

**The match: `data/jrc_ppdb/jrc_cab_match.parquet`, 77 Spanish units plus the 16
Portuguese** (Spanish part rebuilt 2026-08-18, up from an initial 53 — see below). JRC and OMIE share no key at
all, so this is name/capacity matching in the same spirit as
`build_unit_agents.py` — three paths, all requiring positive evidence,
nothing forced: 30 by exact code match (JRC's `name_g` sometimes *is* the
OMIE code, e.g. `ESCCC1`), 36 by capacity-within-6%-plus-name-similarity
(30 outright, 4 by a capacity tiebreak, 2 by a twin-registration-marker
tiebreak — both below), 11 by a hand-verified alias table. Ambiguous or
implausible candidates are printed and left unmapped, not guessed at —
Castejón's real CCGT unit (`CTJON3`, 418.5 MW) matched correctly; OMIE's
*other* Castejón-named codes (3.0 MW test units) correctly did not.

**Coverage, measured on capacity rather than plant count** (JRC's 344
candidates include hundreds of sub-5 MW cogeneration units that barely move
this number either way): of 39,427 MW JRC has an in-window efficiency for,
**32,589 MW now matches an OMIE unit — 82.7%** (80.3% of gas, 90.0% of
coal), up from 54.2% at the first cut. See the two traps below for what
closed most of that gap — one was a real bug, not a coverage limit.

**Of the 77 matches: 54 Fossil Gas, 23 Fossil Hard coal.** Of the gas
units, **46 carry a plant-specific efficiency** (`eff_is_generic ==
False`); the rest match correctly on capacity and name but their efficiency
is a generic technology-class default (see the `eff_is_generic` trap).

**The gas cap is now carried alongside, added 2026-09-04.**
`marginal_cost_capped_eur_mwh` values a gas unit at RDL 10/2022's *reference*
price `PRGN` rather than the market price, with `cap_applies` and `cap_binding`
flags. The path is transcribed from the consolidated decree (BOE-A-2022-7843
art. 3, which incorporates RDL 3/2023): **40 €/MWh from 2022-06-15 through
December 2022**, then 45/50/55 for Jan–Mar 2023 and a linear 56.1 → 65.0 for
Apr–Dec 2023, ending 2023-12-31. Start date from Orden TED/517/2022 (entry into
operation 14 June, first delivery day the 15th).

**Use the capped column for anything spanning mid-2022 to early 2023.** The cap
binds on 43.5% of in-window gas unit-days — every month from 2022-06 to 2023-02,
then never again, because MIBGAS fell below the reference from March 2023 and
the decree makes the adjustment nil in that case. It is not a small correction:
median gas marginal cost in August 2022 reads **317.5 €/MWh uncapped and 107.9
capped**. Valuing a capped plant at the market price makes compliance look like
strategic markdown — it put 53.2% of 2022 offers below cost with a negative
median markup (see `analysis/markdown_contract_test.py`).

**Superseded 2026-10-28 by the decree's own rule: use `marginal_cost_subsidised_*`.** The
mechanism paid every eligible plant, gas and coal alike, the same subsidy per MWh, `subsidy_eur_mwh` =
max(0, PGN − PRGN) / 0.55, with 0.55 fixed in the decree (Commission approval C(2022) 3942, recitals
(36), (39); `docs/gas-cap-sources.md`). The subsidised cost is own cost minus it, with a `_bid` twin. It
is positive on 243 days, 2022-06-15 → 2023-02-25, at most €336/MWh. August 2022 medians: gas €306 →
€113 (the capped column gave €108), coal €232 → €36. The capped columns below are kept so that earlier
results reproduce.

**Coal keeps its uncapped cost and `cap_applies` is False** in the capped columns — wrong, as above. Coal plants were
inside the mechanism, but the decree defines the adjustment on the gas price and
converting it to a coal plant's fuel cost needs a consumption factor the decree
does not give. Not invented here.

**The output: `data/jrc_ppdb/implied_marginal_cost_daily.parquet`, 292,979
unit-days (every calendar day; 242,573 Spanish), `fuel` column distinguishes
gas/coal.** **`marginal_cost_bid_eur_mwh` and `marginal_cost_capped_bid_eur_mwh`
(2026-10-05) use only prices final when offers close at 12:00 on D-1**: each
series' last value dated D-2 or earlier. MIBGAS's index for gas day D averages every
completed session for D, intraday trades on D included, so D-1's is not final at
noon; carbon, coal and the ECB rate settle in the afternoon. Against the delivery-day
cost the gas difference is a median 1.5 €/MWh, 95th percentile 10.5 (22–27 in
2021–2022). Use the `_bid` columns for anything that models the offer decision. Until
2026-10-01 it held 170,402 and **no weekends**: carbon, coal and the exchange rate
are quoted on trading days only and were inner-joined, so every Saturday and Sunday
fell out, and any design reading the file silently dropped weekends. They are now
carried at their last traded value for up to 5 days (`last_traded`); MIBGAS
publishes weekends itself. Every weekday cost is unchanged. Gas (46 trustworthy
units): mean 93.49 €/MWh, range 15.73–466.41 (weekends included) — sits sensibly above OMIE's
73.31 €/MWh mean day-ahead price, consistent with CCGT usually setting the
margin. Coal (22 trustworthy units): mean 101.54 €/MWh, range 30.94–297.58
— close to gas, plausible given coal's lower thermal efficiency (0.29–0.38
vs. gas's 0.52–0.55) offset by cheaper fuel per MWh(th). Coal's price
converts USD/tonne (`fetch_coal_price.py`, Rotterdam API2, ICE ticker
`ATWMc1`) through `data/ecb/ecb_usd_eur_daily.parquet` (ECB's own daily
reference rate — divide, don't multiply, see the FX trap) and a cited
calorific value (API2's own 6,000 kcal/kg NAR spec = 6.978 MWh(th)/tonne,
S&P Global's CIF ARA methodology) onto the same EUR/MWh(th) basis as gas;
treat coal as a **looser** bound than gas on top of the "bound, not a
measurement" caveat both share (it omits O&M, water and startup
amortisation, and uses static full-load efficiency, not the part-load
figure a unit actually runs at) — API2 is the Rotterdam *import* benchmark,
and some plants may have burned domestic Spanish coal at a different price
before the mines closed.

### The hydro cost — a price-taking water value per unit and day (frozen 2026-10-07)
`outputs/tables/hydro_cost_daily.parquet`, built by `build/build_hydro_cost.py` from
`build_water_value_forward.py`: **200,673 unit-days, 79 units (71 storage, 8 pumped),
2019-01-01 → 2026-05-31**, cost defined on 98%. The storage-hydro counterpart of the
implied gas and coal cost, and like it known when offers close (forwards and reservoir
fill as of D−2). Use `cost_eur_mwh` (λ*30s); `cost_90_eur_mwh` is the check.

What it is: the price a price-taker would put on its water, the (1 − running share)
percentile of the prices expected over 30 days (OMIP Spanish settlement × last year's
hourly shape), the running share being the unit's own capacity factor for that calendar
month in the other years, moved by its reservoir fill (MITECO basin for Spain, SNIRH own
reservoirs for Portugal). Detail in `notes/rq-water-value-forward.md`.

- **Validated on the firm that behaves competitively**: EDP's revealed water value on its
  four large cascades is within 6% of it (correlation 0.81–0.91).
- **A lower bound**: no option value beyond the month and no reservoir bounds. Option value
  from uncertain water within the month was tested and is under 1% (§5.4); storage moves
  it by €0–4; catchment rain adds nothing to the fill.
- **Not a measurement of any firm's water value**: the gap between offers and it is what
  leg B tests (`notes/rq-leg-b-levels.md`).

Flags: `pumped` (an arbitrage value, read apart); `zero_share` (offered hydro MW at ≤ €1
that month; above 0.5 the cost does not describe the unit's offers: Endesa's `GDLQ` and
34 mostly small aggregated units); `spell` (a >25% move in `cab` max power; it finds
`ALIMA` 2024-03, `ACAVADO` 2024-04 and `ADOURO` 2021-10); `storage` (miteco, snirh, none:
147,753 of the unit-days have no fill series and keep the unadjusted running share).

### JRC hydro plants and storage-hours — Portugal only, and a lower bound
`data/jrc_hydro/jrc_hydro_plants.parquet`, fetched 2026-09-29, token-free: the
JRC Hydro-power plants database (De Felice, CC-BY 4.0,
`github.com/energy-modelling-toolkit/hydro-power-database`), **387 Spanish and
Portuguese plants** with capacity, type (HDAM reservoir / HPHS pumped / HROR
run-of-river), reservoir volume, dam height and a storage figure.

**Its storage figure is not one quantity.** For high-head reservoir plants it
reflects the true head (Alto Lindoso 224,600 MWh against 88,700 from dam
height × volume); for many pumped-storage plants it looks like the pumping cycle
alone (Alqueva 5,800 MWh on a 4,150 hm³ reservoir; Baixo Sabor 3,400 on 630 hm³).
It is reported for 63–77% of Portuguese reservoir and pumped plants but only
30–42% of Spanish ones.

`build_storage_hours.py` turns it into hours of full output per OMIE cascade,
for EDP's Portuguese units and Movhera, via a hand-checked plant→unit map (river
plus a capacity sum matching `cab`). Every figure is a **lower bound**; see the
script and `notes/rq-midday-hydro.md` §3.17. Spain is not built here; for Spanish
storage over time use MITECO by basin or ESIOS 623 (see the ESIOS section).

### SNIRH — Portuguese reservoirs: weekly volume, hourly level, daily flows
`data/snirh/snirh_reservoir_series.parquet`, fetched 2026-09-30 by
`fetch/fetch_snirh_reservoirs.py`: **1,765,828 rows, 39 reservoir gauges,
2018-01-01 → 2026-09-30**, long format (`station_code, site_id, station, basin,
parameter, time_local, time_utc, date, value, suspect`). The stations are EDP's
and Movhera's cascades plus Iberdrola's Tâmega scheme. SNIRH is APA's
water-resources system, the Portuguese counterpart of MITECO's bulletin.

**It runs from one address only.** SNIRH blocks every request from outside
Portugal (a security control on software APA cannot patch). On 2026-09-30 APA
whitelisted **194.95.236.6**, the exit of LMU's eduVPN, after being told it is
shared (`notes/email-apa-reservoir-data.md`). The fetcher checks the exit
address and refuses to run from any other; it sends one request per station,
5 s apart. **Keep `data/snirh/raw/` (39 CSVs, 54 MB)**: unlike the rest of
`data/`, it cannot be re-fetched from an arbitrary network. Never route around
the block with a Portuguese VPN.

Per station, eight parameters, each as the station reports it:

| parameter | resolution | note |
|---|---|---|
| `volume_dam3` | weekly | dam³ = 10³ m³; stamped 23:00 |
| `volume_month_end_dam3` | monthly | matches SNIRH's monthly bulletin to a median 0.009 hm³ |
| `level_m` | hourly in some years | the bulk of the rows |
| `inflow_m3s`, `turbined_m3s`, `pumped_m3s`, `spilled_m3s`, `outflow_m3s` | daily | outflow = turbined + spilled on 99.4% of station-days |

Validated against the market: daily turbined flow correlates **0.86** with
PDBF scheduled energy of `ALIMA` (Alto Lindoso) and **0.88** of `TEMON` (Castelo
do Bode), and energy per m³ at Alto Lindoso implies a **284 m** head, that
plant's real head. `GUADIA` against Alqueva is weaker (0.42).

**Inflow is computed, not measured, and carries source glitches.** It is never
negative and exactly zero on 10–34% of days at several stations, which suggests
SNIRH derives it from the water balance and clips it at zero; that clipping
biases it slightly upward. `suspect` flags two faults found on the first fetch;
values are never changed, following ResOpsUS (Steyaert et al. 2022):

- **Pumped flow in the wrong units**: about 1,000× too large at Alto Rabagão,
  Venda Nova, Torrão and Aguieira on 2023-04-01 → 08-01 and in January 2026,
  with every other flow at those stations reading 0. All flows on those
  station-days are flagged.
- **One-day inflow spikes**: 15 above 500 m³/s, e.g. Castelo do Bode
  2022-01-20 at 5,497 m³/s from a single hourly level reading of 79.00 m in a
  series at ~107.2 m. A spike that passes through the dam (outflow ≥ half of
  inflow) is a real flood and is not flagged.

**How to use it.** Weekly volume is the water value's state variable; use it as
is. Turbined flow as is. Inflow: drop `suspect`, and use it weekly, not daily;
a cleaner weekly inflow is outflow plus the change in weekly volume. Pumped
flow: missing in the two windows, and not to be rescaled by 1,000 without a
check against OMIE pumping schedules. Timestamps are **Lisbon** local time; the
autumn repeated hour appears once. Pumped flow is recorded at only five of the
pumped-storage stations (not Baixo Sabor, Foz Tua, Frades II or Gouvães).

### E-OBS — gridded daily rainfall over the whole peninsula
`data/eobs/eobs_rr_iberia_daily.parquet`, fetched 2026-10-02 by
`fetch/fetch_eobs_precipitation.py`: **14,685,316 cell-days, 1,130 land cells at
0.25°, 1991-01-01 → 2026-07-31, no day missing**. Columns `date, lat, lon, rr`
(mm/day). E-OBS v33.0e is the European gridded dataset interpolated from weather
stations (ECA&D, KNMI; Cornes et al. 2018): the 1950–2025 file (738 MB) plus KNMI's
2026 file (68 MB, extended month by month and re-fetched when its size changes),
both kept in `data/eobs/raw/`. Non-commercial research use only; cite it.
Mean annual rainfall over the cells, 1991–2020: 616 mm.

It replaces the single ERA5 points of `fetch_hydro_precipitation.py` for anything
needing coverage: Open-Meteo's free tier counts every two weeks of data per point
as a call, about 220 calls per point for 2018–2026 against 10,000 a day, so a grid
is out of reach there. Starting in 1991 gives 1991–2020 normals to measure
anomalies against. **No snowfall**: E-OBS rr is total precipitation.

### HydroBASINS — sub-basins and the river network
`data/hydrosheds/hybas_iberia_lev{08,10,12}.parquet`, fetched 2026-10-02 by
`fetch/fetch_hydrobasins.py` from HydroSHEDS' `hybas_eu_lev01-12_v1c.zip` (361 MB,
kept in `data/hydrosheds/raw/`; free licence, cite Lehner & Grill 2013). Level 12:
**4,952 sub-basins, 647,959 km²** inside 35.8–44.0 N, 9.6 W–3.4 E (so a little of
France and Morocco). Columns `HYBAS_ID, NEXT_DOWN, MAIN_BAS, SUB_AREA, UP_AREA,
PFAF_ID, ORDER, wkb` (shapely geometry). `NEXT_DOWN` is the sub-basin each drains
into, so a dam's upstream catchment is its sub-basin plus everything draining into
it. 20 level-12 sub-basins drain outside the box (French and Moroccan rivers); no
Spanish or Portuguese river does.

### Reactor outages by cause — the instrument for n (2026-10-05)
`build/build_reactor_outages.py`: lost output of the seven reactors hour by hour
(`cab` max power minus the PDBF schedule), each hour's cause from the `indisp`
declaration covering it, and each owner's dose by its share that day. **A
declaration explains at most the capacity it takes away**: a summer-long cooling
limit to 960 MW does not explain a cut to 400 MW at low prices, which first made such
cuts look like weather. 49 unplanned and 51 planned spells; unplanned outages follow
ordinary prices. **Undeclared lost output rose to 5–8 TWh a year from 2024** and
follows low prices: reactors now cut output at low prices, which is a choice and not
an instrument. Detail and first stage in `notes/rq-reactor-outages.md`.
Used in the §9.2 offer regression (`analysis/outage_offer_test.py`, 2026-10-05):
β −0.9, 95% set [−4.2, 0.7], unit-level first stage F ≈ 10. With own-catchment rain as
a second instrument on thermal units (`analysis/outage_rain_offer_test.py`): β −0.85,
[−4.0, 1.8]. Event study of 21 trips: `analysis/outage_event_study.py`. With the
firm's own wind above the national rate, by region, as a third instrument
(`analysis/regional_wind_offer_test.py`, ESIOS output by province × located farms):
first stage F 22–28, β +0.9 [−2.6, 4.5]; with the outages −1.6 [−4.3, 1.5]. On the
third location pass (78.5% of wind, the main specification since 2026-10-06): F 27–33,
β +1.5 [−1.6, 5.0]; with the outages −1.0 [−3.1, 1.5].

**How reactors cut (2026-10-19, `analysis/nuclear_cuts_describe.py`,
`notes/rq-nuclear-cuts.md`).** The Iberdrola-run reactors (Almaraz 1 and 2 and Trillo
through CNAT, plus Cofrentes) cut through the **bilateral** leg. PDBF role 4 to the co-owners'
retailers falls (Trillo 849 → 298 MW on cut days), and part of the energy is offered in
the auction at a prohibitive €250–427 and not accepted. The Endesa-run reactors (Ascó
and Vandellós II through ANAV) offer the cut capacity at a **reservation price**: €35
almost every day from 2024 (CNAT's is €22–23). Of positive-price MW offered by reactors,
82% are at €20–40 and 12% above €300, so €200 separates the two cleanly. **Whole-day
stops in 2024–2026 fall mostly on days `indisp` has no snapshot for** (2.2 of 2.7 TWh in
2024), so they may be outages the register missed. **After a trip the reactor buys its own day-ahead schedule
back in the intraday auctions** (`build_intraday_squeeze_events.py`): a median 65% over
the hours the day-ahead schedule still counts it, usually with bids at €180.30 or €500,
the top of the range. Owners' other plants cover part of it, so their net take from
rivals is a median 34% of that schedule. `indisp` gives each declaration's own `start`:
use it for the trip time, since `reactor_outage_hours` starts a spell at 00:00 of the
first day the next schedule shows it.

### Outage events — every large non-nuclear fault, and what it cost the owner (2026-10-19)
`build/build_outage_events.py` (`--verify`): 17,268 `indisp` declarations of gas, coal,
hydro and pumped-storage generator groups, linked to OMIE units through ESIOS archive 81,
classed by reason with the default **out** (the reactor classifier defaults unknown text
to "unplanned", which would admit "INDISPONIBILIDAD OPERACIONAL", cold-start lead times
and reservoir-level limits). Kept: 1,678 faults (≥ 100 MW, ≥ 6 h, declared < 24 h ahead)
and 1,574 planned stops. Dose = owner's share of max(0, lost − (capacity − expected
output)), the first 14 days of a spell. Three traps found building it:
- **Twelve combined cycles register their steam turbine as a `Vapor` group.** Classed
  group by group, one plant has two kinds and its outages split into one-hour spells.
  Class the OMIE unit, not the group.
- **Hydro faults never bind**: a cascade unit runs far below capacity, so a group fault
  leaves the rest able to carry the schedule (142 spells, 0 GWh bound).
- **Some faults last a year** (Castelnou from May 2019, 9,720 hours), which a dose from
  the week before cannot describe.

A binding gas fault reaches the owner's n at only 40% (se 21%, F 3.7), against 77–86% for
a reactor, so **the faults are not an instrument** (the design's stop rule; joint F 15.8,
carried by implausible coal and pumped-storage coefficients). They do not follow the
owner's stake either: the daily fault rate does not move with the owner's X the day
before (p 0.86, 370 starts). Detail in `notes/rq-outage-events.md`.

### Wind and solar farm locations — 54% of wind located, 16% of solar (2026-10-05)
`data/osm/renewable_unit_locations.parquet`, built by `build/build_renewable_locations.py`:
REE's farms (ESIOS archive 81, a 2026-08-12 snapshot: 1,173 onshore wind farms, 32.3 GW;
2,025 PV, 40.7 GW) matched by name to OpenStreetMap plants, then to WRI's Global Power
Plant Database (v1.3, 2021) for what OSM leaves. **723 farms: 17.5 GW of wind (54%),
6.5 GW of PV (16%)**. Matched capacities agree: REE over OSM has median 1.00, 5–95%
0.76–1.16. Solar is low because most OSM solar plants carry no name (983 of 3,357 in
Spain).

**REE's programming units for wind and solar are not OMIE units**: 0 of 455 wind `up`
codes appear in OMIE. Farms sell through their agents' aggregated units ("eólica
habilitada"). So a farm's firm comes from its REE `agent`, mapped to the modal firm of
that agent's OMIE units in `unit_agents.parquet`: 97.6% of wind MW, 94.9% of PV. That
is the 2026 snapshot, not dated, and for representatives (Nexus, Ignis, Gesternova)
it names the agent that bids, not the owner. Located wind by firm: Iberdrola 75%,
Endesa 65%, EDP 63%, Acciona 58%, Naturgy 55%, Repsol 28%.

**The public Overpass servers answer 504 under load**, even to tiny tiles. The fetcher
declares a 90 s timeout and 64 MiB (admitted where the defaults are refused), splits
a failing tile into quarters, skips what still fails (listed in
`data/osm/missing_tiles.json`, exit code 2) and fetches only what is missing on a
re-run. OSM is ODbL 1.0, GPPD CC BY 4.0: cite both.
**Two further passes raise located onshore wind to 78.5% (2026-10-06)**, onshore
wind only; each keeps the previous file's rows and writes a new one. `_v2` (better
REE-side names, unused OSM/GPPD plants, OSM turbines grouped into farms) reaches 745
farms, 22.4 GW (69.5%). `_v3` places farms by **autonomous community only**, from
MITECO's Electra producer register (`data/miteco/electra/raw/ElectraExp.csv`, 71,727
rows of name, regime and community; no coordinates or capacity): 877 farms, 25.4 GW.
Its rows have no lat/lon. Tested on farms already located, Electra's community agrees
98.4% (543 of 552); the disagreements are border farms and three earlier-pass errors,
two corrected and one dropped in `_v3`. By firm: Iberdrola 91%, EDP 88%, Acciona 83%,
Endesa 82%, Naturgy 81%, Repsol 29%. **The instruments read `_v3` since 2026-10-06**
(`LOCATIONS` in `regional_wind_offer_test.py`; `--locations=v1` for the first pass,
outputs suffixed `_v1loc`). What is left (6.9 GW) is mostly farms named only by a code (4.45 GW, Repsol's
among them), which no name register can place.
`osm_wind_turbines.parquet` holds **25,494 single turbines with coordinates** (17% named),
not yet used; turbine clusters could place the wind farms that have no name to match.
Ask Overpass for `out body` on nodes: `out tags` returns no coordinates.

**Country and region come from Eurostat's NUTS polygons (2026-10-05), not from a
longitude cut.** The fetcher first tagged everything west of 6.2° W between 37° and
42.2° N as Portuguese. Against the polygons that put 708 Spanish turbines in Portugal
(Castilla y León 327, Andalucía 241, Galicia 128, Extremadura 12) and 844 turbines in
France, Morocco and Algeria in Spain. Now: **Spain 21,845, Portugal 2,801, 848 outside
both** (`country` blank, including WindFloat Atlantic offshore). Turbines per region
correlate 0.96 with ESIOS's wind capacity per region (1.0–2.0 MW a turbine; Portugal
5.5 GW over 2,801, 2.0); the Canaries are outside the tiles. All 723 located farms fall
in Spain. Located wind as a share of ESIOS's August 2026 capacity: Castilla y León
63%, Aragón 49%, Castilla-La Mancha 49%, Galicia 52%, Andalucía 70%, Cataluña 15%.

**OSM's capacity tag is sometimes a bare number in kW**: `parse_mw` reads a number
without a unit as MW, so La Robla I and II, 5 MW solar plants, read 5,000 MW. Only 8 of
5,215 tags are bare numbers. The matcher's capacity gate rejects a pair with such a
capacity, so the error can cost a match but cannot create one.

### Holidays by region, and regional demand (2026-10-20)
`data/holidays/holidays_es_pt.parquet`, built by `fetch/fetch_holidays.py`: **2,134 rows,
2018–2026, one per date and area** (ISO 3166-2:ES region codes, Ceuta, Melilla, and `PT`).
Spain from the Dirección General de Trabajo's yearly BOE resolution (*relación de fiestas
laborales*), read as the BOE's own XML (raw kept in `data/holidays/raw/`); `mark` says whether
a day is national (`*`), national kept by the region (`**`) or the region's own (`***`).
Portugal's national holidays by law (Código do Trabalho, art. 234). Municipal holidays and
each Canary island's own day are left out, so the Canaries list 11 a year and every mainland
region 12–13. Used by the regional-holiday design (`notes/rq-regional-holidays.md`).

**The BOE table's layout changes by year**: 2018 marks regions `axis="comunidad"` and dates
`id="headerDDMM"`, later years `axis="CA"` and `id="fDDMM"`, and a date with two named rows
carries a letter suffix (`f2304a` San Jorge for Aragón, `f2304b` Villalar for Castilla y León;
`header0906R`). A pattern without the suffix skipped those rows silently, losing a day in
eight regions in some years (Aragón's and Castilla y León's 23 April among them). The parser
now refuses a year with any unread date row.

`data/ree/ree_demand_ccaa_monthly.parquet`, by `fetch/fetch_ree_regional_demand.py`: REE's
REData `demanda/evolucion` per autonomous community, **monthly only** (daily and hourly by
region answer HTTP 400; checked 2026-10-20), 2018-01 → 2026-08. The geo ids are not on REE's
page; identified from 2023 totals and checked: the 15 mainland regions sum to the peninsular
total to 0.00% in every year 2018–2025. The current year's months are provisional (2026:
5.8% above). REData answers 400/502 to valid requests now and then; the fetcher retries.

**Retail purchases are PDBF, not auction purchases.** A retailer's load is its retail units'
whole schedule, auction plus bilateral (role 4): on the Diada 2024 Endesa's auction purchases
fell 674 MW but its schedule 457, and Iberdrola's auction purchases rose while its schedule
fell. The regulated suppliers' units (Energía XXI, Curenergía, …) are registry role
`purchase_other`, not `purchase_retail`.

### OMIE `pdvd` — the schedule after REE's technical constraints (2026-10-20)
`data/omie/pdvd/parquet/`, fetched by `fetch/fetch_omie_pdvd.py`: **2019-01 → 2025-03, 75 months,
104 M rows**, token-free (OMIE lists monthly zips from 2018-01; `--all` fetches them). PDVD
(*Programa Diario Viable Definitivo*) is PDBF after REE has switched plants on to secure the grid
and cut others to rebalance; it comes before the first intraday session. **Seven fields, not
PDBF's nine**: `year;month;day;period;unit;MW;code;` (no unit id, no group tag); `code` takes 1
and 4 like PDBF's role code. A combined cycle withdrawn in the auction can run here: Sagunto 1 on
2019-01-03, out of the auction, is scheduled at 51.7 MW on average. Within €2/MWh of the
minimum-income threshold REE schedules 40% of withdrawn plants (`notes/rq-mic-near-miss.md`).

### French prices and system data — Ember and RTE (2026-10-20)
`data/ember/ember_prices_hourly.parquet` (`fetch/fetch_ember_prices.py`): Ember's hourly
day-ahead prices for Spain (ESP), France (FRA) and Portugal (PRT), 2015-01-01 → 2026-10-07,
compiled from ENTSO-E (CC BY 4.0, cite Ember); one zip of per-country CSVs with UTC and local
times, kept in `data/ember/raw/`. **Spain's equals OMIE's `price_es` within €0.01 on 100% of
67,919 hours**, so it is the published price, and the UTC join holds through DST. It stays
hourly after the day-ahead's 15-minute switch. No token, unlike ENTSO-E's API.

`data/rte/eco2mix_national.parquet` (`fetch/fetch_rte_eco2mix.py`): RTE's éCO2mix national
consolidated data from ODRÉ (`eco2mix-national-cons-def`, Etalab licence, no token), hourly UTC
means of quarter- and half-hourly rows, 2017-12-01 → 2026-08-31: demand, **RTE's D-1 forecast
(`prevision_j1`)**, nuclear, wind, solar, and the commercial exchange with Spain (positive when
Spain exports to France: corr +0.963 with OMIE's scheduled flow). On ODRÉ `date` is text; filter
on `date_heure` with a `date'…'` literal. Realised output is filled only on half-hours.

**The France line's state by hour** (`build/build_france_link.py`): open in 31% of hours
2018-01 → 2025-09, import-full 41%, export-full 28%; Spanish and French prices are equal in
99.7% of open hours and differ in 99.8% of full ones (`notes/rq-france-link.md`).

### Italy — GME unit-level offers, PSV gas price, JRC units (2026-10-28)
The control group for the gas-cap design: Italian gas plants, which had no cap, against
Iberian ones around 2022-06-15. Italy is not coupled to Iberia, so unlike France it did not
receive the capped Iberian power.

**`data/gme/offers/parquet/`** (`fetch/fetch_gme_offers.py`): every offer and bid in GME's
day-ahead market (MGP), **760 days, 2021-06-01 → 2023-06-30, 32.3 M offered sell rows, 1,822
selling units, 154 operators**, one parquet per day. Raw zips kept as served in
`data/gme/raw/YYYYMM/` (1.8 GB; one XML of ~100 MB a day inside). GME keeps offers
confidential for 7 days (DM 29 April 2009), then publishes them with the **unit code and the
operator** (`OPERATORE`; bilateral positions read "Bilateralista", so take a unit's operator
from its other rows). Hourly to 2023-06, CET local day. History goes back to 2004.
Access needs GME's **terms of use**, accepted by the user in a browser on 2026-10-28; the
download API then checks only the cookie that acceptance sets (`GmePolicy_en=true`), no login.
The fetcher pauses 3 s between days.

- **Curves:** keep status ACC/REJ/PREJ for the offered curve (like OMIE's `O`) and ACC for
  cleared volume. **REP (replaced) and REV (revoked) repeat quantities**; summing them
  double-counts.
- **Accepted buy exceeds accepted sell, by design**: imports over the coupled borders
  (France, Austria, Slovenia, Greece) clear implicitly and appear in no offer, like OMIE's
  `MIEU`. On 2022-09-15 the gap is 4.4 GW at night and 0.5 GW at midday. Switzerland and
  Montenegro are explicit zones (`SVIZ`, `MONT`) inside the offers. `--verify` checks the hour
  count and that the gap stays within ±12 GW: all 760 days pass.
- **Zonal**: `zone` is GME's bidding zone (NORD, CNOR, CSUD, SUD, CALA, SICI, SARD); the
  national purchase price (PUN) is not in this file.

**`data/jrc_ppdb/jrc_italy_units.parquet`**: JRC-PPDB-OPEN's Italian units, from the zip already
kept for Spain. **JRC's `name_g` is GME's own unit code** (`UP_TAVAZZANO_5`), so the two join
exactly, unlike Spain's name matching. 104 gas units of 100 MW or more; **88 offer in the window
(36.0 GW), 73 with a plant-specific efficiency** (`best_source` not `Class_derived`), 84 both
before and after 2022-06-15. **15 operators**: Enel 18 units (5.5 GW), A2A 9 (4.8), Eni 14
(4.6), Edison 9 (4.2), EP Produzione 7 (3.3), Sorgenia 4 (3.2), Tirreno Power 4 (2.3), Axpo 6
(2.3), Iren 5 (2.3), Engie 4 (1.5) and five small ones. Against Iberia: 56 gas units (25 GW)
and 12 owning firms.

**`data/gme/gas/gme_mgp_gas_daily.parquet`** (`fetch/fetch_gme_gas_prices.py`): GME's
day-ahead gas market at the PSV (*Punto di Scambio Virtuale*, the Italian hub), the counterpart
of MIBGAS. **9,594 rows, every gas day 2018-01-02 → 2026-10-03**, one row per session and
product (`MGP-YYYY-MM-DD`): volume-weighted mean, GME's reference price, auction price from
2019-12-31. A product trades on several sessions, so (session, product) is the key; **for an
offer for day D use sessions up to D-2**, as the Spanish `_bid` costs do. Against MIBGAS:
correlation 0.97, yearly means within €1–3 except in the crisis (2022: PSV 124, MIBGAS 99;
August 2022: 232 against 164), so compare offers net of each plant's own cost, not levels.
**`data/jrc_ppdb/italy_implied_marginal_cost_daily.parquet`** (`build/build_italy_marginal_cost.py`):
Spain's cost rule on Italian gas units, PSV in place of MIBGAS, same EUA and emission factor, `_bid`
twins on prices final at 12:00 on D-1. 102 units with an efficiency (82 plant-specific), 2018-01-02 →
2026-08-23; median plant-specific cost €239.7/MWh in 2022, €111.8 in 2023. On every GME day **46–57
plant-specific units of 100 MW or more both offer and have a bid-time cost** (median 57), 67 on at least
half the days. Two Termini Imerese units have an efficiency of 0.33 and a cost of €1,008 on 2022-08-26:
real arithmetic.

In the download API the gas prices are `Settore=SintesiScambio` (`Prezzi` answers HTTP 417
`InvalidFilter`), with the gas page's own `ModuleId`/`TabId` headers.

### Great Britain — balancing offers per unit, gas price (2026-10-28)
A second comparison for the gas-cap design, besides Italy: uncapped, and outside the European coupling
since 2021-01-01. **Great Britain has no day-ahead pool**, so its unit-level offers are
balancing-mechanism offers: `fetch/fetch_elexon_bod.py` (Elexon Insights API, free, no key, at most 7
days per unit per request) keeps BOD, up to ten MW bands per half-hour relative to the plant's final
physical notification with an offer (to raise output) and a bid (to lower it), and PN, the notified MW
level itself. Window 2021-06-01 → 2023-06-30; units are the register's CCGT and COAL (`fuelType`,
`/reference/bmunits/all`, a snapshot saved with its date: 71 units with an Elexon id). **JRC-PPDB-OPEN's
`name_g` for British units is National Grid's unit name** (`PEMB-11`, `DAMC-1`), so efficiencies join
exactly, as for Italy. A period can carry several PN segments (a ramp within the half-hour): the key is
the segment start, not the period.

Gas: `fetch/fetch_ons_gas_sap.py`, the ONS's daily System Average Price (National Gas Transmission's
On-the-Day Commodity Market average), 2018-01-01 →, p/kWh ×10 = £/MWh; 2022 mean £71.2 against a
published NBP average of about 200 p/therm (£68). NBP day-ahead quotes are not free. **Carbon is not on
disk**: UK ETS allowances from 2021-05-19 (ICE auctions, no free series found) plus the £18/t Carbon
Price Support.

### Eurostat NUTS 2021 regions — country and autonomous community of a coordinate
`data/gisco/nuts2_iberia.parquet`, fetched 2026-10-05 by `fetch/fetch_gisco_nuts.py`:
the **19 Spanish and 7 Portuguese NUTS level-2 regions** (autonomous communities, Ceuta
and Melilla included; Portugal's five mainland regions plus Açores and Madeira), as
shapely geometry (WGS84). Eurostat GISCO, 1:1 million, so a border or coastline is
within about a kilometre; the European file (18 MB) is kept in `data/gisco/raw/`.
Attribution: "© EuroGeographics for the administrative boundaries". `lib/regions.py`
`locate(lat, lon)` gives `nuts_id, country, region, esios_geo_id, how`: a point within
0.05° of a coastline gets the nearest region (`near`), anything farther stays blank.
`esios_geo_id` maps each Spanish region onto ESIOS's installed capacity by region.

### Combined cycles declare their cost daily; Turbogás left on 2024-03-30
Measured 2026-10-06 on the 54 combined cycles with a plant-specific efficiency,
2023-04 → 2025-03-18 (`analysis/ivpee_tax_test.py`). The minimum-income variable term
in `cab` changes on 96% of Spanish and 88% of Portuguese unit-days, and sits at a
median 1.3× (Spain) and 1.1× (Portugal) the implied cost (`_bid`). It is not
proportional to fuel cost: within a unit it moves 0.95% (Spain) and 0.70% (Portugal)
per 1% of implied cost. 999 means "never" (94 unit-days, mostly Turbogás).
**Turbogás (`RTG01`–`RTG03`, Tapada do Outeiro) offered for the last time on
2024-03-30**, and in February and March declared a quarter of its cost. In 2024
Portuguese combined cycles offered most of their volume at 0 €/MWh, so for them the
declared term, not the offer price, carries the cost.

### EDP moved ~1,000 MW from `ACAVADO` to `ALIMA` in March 2024
`cab` max power goes 1,632 → 632 MW for `ACAVADO` ("CAVADO") and 652 → 1,652
for `ALIMA` ("LIMA"), and offered volume moves between them from February to
April 2024. The unit codes and names did not change, so **a per-unit series for
either spans two plant sets**. Which plants moved is not published. The same
thing happened to `ADOURO` on 2021-09-09, when the six dams EDP sold to Movhera
on 2020-12-17 left it (2,849 → 1,147 MW) and became `DOUSUP` (1,709 MW). Until
then they were offered inside `ADOURO`; `lib/unit_ownership.py` gives Movhera 60%
of `ADOURO` over that window (`UNIT_SHARES`). An earlier note here said January
2022; the `cab` break is 2021-09-09. A cascade unit's contents are
not fixed; check `cab` max power for breaks before reading a unit's series
across years.

### Population-weighted temperature — the demand-side weather index
`data/weather/temperature_population_index.parquet`, fetched 2026-08-21,
token-free (Open-Meteo ERA5, same source as `fetch_weather.py`). **21 cities,
1,548,792 city-hours, 73,752 hours**, 2018-01-01 → 2026-05-31. Columns:
`temp_pop_es`, `temp_pop_iberia`, `temp_es_unweighted`, `cdh_es`, `hdh_es`
(cooling and heating degree hours, base 18 C).

Exists because `fetch_weather.py`'s ten points were chosen to span the regions
where **wind and solar capacity** sit — Tarifa, La Mancha, Badajoz — which is
the right frame for an instrument for renewable output and the wrong one for
demand. Peninsular only: the Canaries and Balearics are separate electrical
systems and do not clear in MIBEL. Portugal is included and tagged, so an
Iberian index is available for market-total work.

**It barely matters empirically, and that is worth recording rather than
hiding.** The population-weighted series correlates **+0.993** with the
renewable-sited mean and **+0.996** with an unweighted city mean; even in the
top 1% of hours the two read 34.1 C and 34.3 C. It runs 1.27 C warmer on
average with essentially the same standard deviation. So it is the right series
on principle and will not rescue a weak first stage. Weights are approximate
municipal populations, adequate because temperature is strongly spatially
correlated at national scale; replace with INE series by year if a design ever
turns on the weights themselves.

### OMIE `indisp` — declared unit unavailability, with cause and lead time
`data/omie/indisp/parquet/`, fetched 2026-08-21, token-free. **100 months
2018-01 → 2026-05, 44,636 distinct outage records, 1,529 units.**
Semicolon-delimited, **not fixed-width** — none of this repo's fixed-width
parsers apply. Latin-1, dot decimal.

Columns: `snapshot`, `outage_id`, `start`, `end`, `unit`, `available_mw`,
`reason` (free text, Spanish, inconsistently cased), `declared`, `country`.

Two things nothing else here publishes. The **cause** (top reasons:
`INDISPONIBILIDAD OPERACIONAL` 3,655, `MANTENIMIENTO` 1,413, `PARADA
PROGRAMADA` 890), and the **declaration timestamp** — so `start - declared`
gives lead time: median **0.11 days**, and **74.6% declared under 24 hours
ahead**. That short-lead tail is where economic withholding would hide, and it
is the reason to hold this dataset at all.

OMIE republishes the whole forward register ~30 times a day; each revision is a
full snapshot (checked: rev 1 and rev 2 of 2024-01-01 are 144 and 146 lines at
the same file size), so the fetcher keeps the **last snapshot per calendar day**.

**43 of the 100 monthly zips are partial AT SOURCE**, found 2026-09-28. 40 of
them fall from 2023-02 on, and 37 of those run contiguously from day 1 and stop
short: 202401 holds 20 days, 202403 one, 202605 two. The exceptions are 202506
and 202508 (internal gaps) and 202509 (day 1 missing). Before 2023 there are
only 201809 (last day missing), and 202105 and 202107, both rewritten in one go
on 2021-08-25; 202105 is missing days 1–25. The full table is in
[`notes/email-omie-indisp-gaps.md`](notes/email-omie-indisp-gaps.md).
Re-fetched that day they were identical to the 2026-08-21 copies, and OMIE's
listing holds zips only, so there are no daily files to fill in from. Because
each snapshot is the full forward register, planned outages are still seen from
the first day of a month. What is lost is the **short-lead tail** — exactly the
<24h declarations that are this dataset's reason to exist — for the uncovered
days. **So the 74.6% short-lead share and any post-2023 withholding measure are
computed on a thinning, non-random subset of days.** Check day coverage per
month before using either.

**Why, from 2023 on: OMIE's nightly append job stops mid-month.** Zip member
timestamps show each day's revisions appended overnight, around 00:40–02:15
depending on the period. In the 37 day-1-contiguous months the appends simply
stop (202401's last write is 2024-01-21 01:39, adding the 20th), and a fresh zip
starts working again at the next month.
The trigger is not a three-digit revision suffix — complete months hold days up
to revision 123 — but failures track register churn: the median day in a partial
month has 65 revisions against 34 in a complete one, and churn roughly doubled
from 2023. The exact mechanism is inside OMIE.

**Not recoverable from any public copy** (checked 2026-09-28): OMIE serves no
daily `indisp` files, even for days inside a zip; its `comunzip` folder 404s;
the one Wayback capture of a partial month is zero bytes. The next available
snapshot recovers only outages still running when it was taken — about 24% of
those declared in a simulated gap on complete months, 20% of the short-lead ones.
Routes left: ask OMIE, or ENTSO-E Transparency Article 15.1 (units ≥100 MW,
every version timestamped, token required).

**The unit codes are a PHYSICAL namespace, not the market registry's** — see
the trap below. And **`indisppt` does not exist**: checked against OMIE, it and
two spelling variants return a valid page with zero zips. The
`pdbc`/`pdbcpt` analogy does not extend here.

### OMIE interconnection capacity — what each border could carry after the day-ahead market
`data/omie/interconnection/omie_interconnection_capacity.parquet`, fetched
2026-10-01 by `fetch/fetch_omie_interconnection.py`, token-free. **364,988 rows,
all 3,073 days 2018-01-01 → 2026-05-31, four borders every day.** Source: OMIE
`capacidad_inter_pbc` ("tras la casación del mercado diario"); 2018-2022 as yearly
zips, daily files from 2023. A day's file is published the day before delivery, so
there is **no publication lag** (the listing runs to the day after the fetch).

Columns: `date, period, resolution_min, border, import_capacity_mw,
import_occupied_mw, import_free_mw, export_capacity_mw, export_occupied_mw,
export_free_mw`. **Import figures are negative, as published.** Free capacity nets
the counter-flow (a scheduled export frees import room), so free import can exceed
the import capacity.

**The border codes are not documented in the file; they were identified from the
data.** OMIE's `Frontera` 2 is Portugal: its scheduled net export correlates 0.904
with REN's measured Portuguese net import (January 2024) and 0.908 with REE's flow
(November 2025). 3 is France (0.884), 5 Morocco (0.985), 4 Andorra (by elimination,
about 135 MW). These correlations come from a one-week scratch check, not a committed
script; an independent rebuild on November 2025 gave 0.925 / 0.932 / 0.971 — the
mapping holds, the exact figures depend on the week and the aggregation. The check `qa/check_omie_interconnection.py` confirms it a second way:
in **all 6,111 periods where the Spanish and Portuguese prices differ, the Portugal
link has no free capacity left in one direction** (100.00%).

**Three layouts, and the header does not tell the resolution — the period labels
do.** `Hora` 1..25 to 2025-03-18; `Periodo` with integer hours from 2025-03-19
(OMIE's platform migration); `Periodo` with `HhQq` labels from 2025-10-01, when the
day-ahead market went quarter-hourly. **One file inside the hourly era, 2025-07-15,
is published in quarter-hours (96 periods)**: OMIE re-emitted it on 18/12/2025 in the
new format, and its four quarters are identical within each hour. The fetcher
collapses it to hours (`to_market_resolution`, which raises if quarters ever differ),
so every row joins prices on `(date, period)` at the market's own resolution; the
check confirms all 91,247 priced periods join.

Exists to give leg D an instrument that moves the elasticity of each firm's residual
demand (|RD′|) for grid reasons: capacity is set by the system operators before the
auction. Occupation is an auction outcome and is not exogenous.

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

### Four OMIE datasets change on 2025-03-19 — and OMIE documents why
Found piecemeal 2026-08-13, explained 2026-09-03. It is one platform migration,
not a coincidence: OMIE went live on **18 March 2025** with the new day-ahead
offer typology for the European single day-ahead coupling (SDAC) *and*
quarter-hourly products in both intraday markets under SIDC, first delivery day
**19 March**. Their press release is
[250318_sco_15mtu_vf-es_0.pdf](https://www.omie.es/sites/default/files/2025-03/250318_sco_15mtu_vf-es_0.pdf);
the field-level consequences are in the *Modelo de Ficheros* spec, v1.36 and
v1.37.

- **`cab`** switches fixed-width layout, 169 chars to 94 (trap below), because
  the offer typology it describes changed.
- **`pdbf`** adopts the **15-minute MTU** — 24 periods a day through
  2025-03-18, 96 from 2025-03-19. The operating schedule had to follow intraday.
- **Intraday (`curva_pibc_uof`)** adopts the 15-minute MTU on the same day.
- **The 61-day bid clearing-identity anomaly cluster** begins on this exact
  day and runs to 2025-06-09.

**The day-ahead auction is the one that did *not* move with the others.** OMIE's
own press release announced quarter-hourly day-ahead products for 11 June 2025,
delivery 12 June; the data says it actually happened **2025-10-01**. So the
published plan slipped by nearly four months — do not date the day-ahead switch
from OMIE's announcements.

**Every dataset still has its own resolution date.** Intraday and PDBF
2025-03-19, day-ahead 2025-10-01. Read `resolution_min` per file; never infer
one dataset's resolution from another's.

### PDBF `schedule_mw` is average MW, not MWh per period
Confirmed on Ascó 1 (1,028 MW nameplate): it reads 995.8 in the hourly era and
1,003.0 at 15 minutes. Had the field been MWh per quarter it would read ~250.
Summing the raw column across the 15-minute era therefore overstates energy
**fourfold** — April 2025 sums to 119.29 "TWh" against ~27 TWh in neighbouring
years, which is how this was caught. Derive energy exactly as for the bid
files: `schedule_mw * resolution_min / 60`.

### `cab` changed its fixed-width layout on 2025-03-19, mid-month
Found 2026-08-13, after 14 months of silently corrupt output. The file went
from **169 characters to 94**, and every field moved:

Positions below are OMIE's own, from the *Modelo de Ficheros* spec (v1.35 for
the wide layout, v1.37 for the narrow), not reverse-engineered. The spec counts
from 1; these slices are 0-based.

| field | OMIE name | wide (to 2025-03-18) | narrow (from 2025-03-19) |
|---|---|---|---|
| offer_id | CodOferta | `[0:7]` | `[0:10]` |
| version | Version | `[7:10]` | `[10:15]` |
| unit | Código | `[10:17]` | `[15:22]` |
| descr | Descripción | `[17:47]` | `[22:52]` |
| side | CV | `[47:48]` | `[52:53]` |
| ofer_plazo | OferPlazo | `[49:50]` | `[53:54]` |
| max_ramp_up / _down | MaxRamSub / MaxRamBaj | `[84:91]` / `[91:98]` | — |
| min_income_fixed_eur | Fijoeuro | `[98:115]` | — |
| min_income_var_eur_mwh | Vareuro | `[115:132]` | — |
| sco_fixed_eur | Fijoeuro | — | `[54:71]` |
| max_power_mw | MaxPot | `[132:139]` | `[71:78]` |
| max_ramp_startup / _shutdown | MaxRamArr / MaxRamPar | `[139:146]` / `[146:153]` | — |
| cod_int | CodInt | `[153:155]` | `[78:80]` |
| declared_at | — | `[155:169]` | `[80:94]` |
| numerics | | nine | **two** |

`offer_id` is the code of the *offer*, not a unit registration id — it changes
day to day (ABO1 is 9497313 on 14 March, 9512371 on 18 March) and does **not**
join to `pdbce`. It was called `unit_id` here until 2026-09-03, which was wrong.
Join on `unit`.

The old parser did not fail. Its guard tested that `line[:7]` was all digits,
and in the narrow layout `[0:7]` is leading spaces plus digits, so it passed
and emitted unit codes `0AB`, `0AC`, `0AD` — plausible-looking, joining to
nothing. Every `cab`-derived attribute was therefore missing for 2025-03-19
onward, which is why marginal-technology coverage looked as if it collapsed in
2026: 100% of 2026 marginal units appeared to have no `cab` name.

**Dispatch on the observed line width, never on the date** — the change lands
mid-month, so a date rule mis-slices 18 days of March 2025. The parser now
raises on any unrecognised width.

`max_power_mw` is **confirmed** across the boundary: of the 2,390 units present
on both 2025-03-18 and 2025-03-19, 100% reproduce the same capacity. The other
narrow numeric, carried as `narrow_numeric_0` until 2026-09-03, is **`Fijoeuro`,
the lump-sum fixed term of the SCO** — now `sco_fixed_eur`. See the `cab`
section above for why it is not comparable with the old fixed term.

### Splitting a fixed-width line on whitespace works until a value fills its column
Found 2026-09-03, while rewriting the `cab` parser onto OMIE's published field
positions. The parser had been reading the numeric fields by splitting the line
on whitespace and indexing the resulting tokens. That is not the same thing as
slicing at fixed positions, and it silently failed whenever a value was as wide
as its column: `Vareuro` (`F17.3`) and `MaxPot` (`F7.1`) are adjacent, so a unit
with a 12,000 MW capacity emits `0.00012000.0` with no separator. The merged
token is not a valid float, the tokeniser stopped there, and the row came back
with **null `max_power_mw` and null on both minimum-income terms**.

It hit exactly the biggest units — `ICLIC01` "IBERDROLA CLIENTES COMPRA" at
12,000 MW and `ENDE01` "ENDESA ENERGIA (ESP)" at 10,200 MW on 2024-01-15, and a
handful per day throughout the archive. Since `build_unit_agents.py` and
`capacity_quantile_offer.py` both filter on `max_power_mw > 0`, those units were
being dropped from capacity-weighted coverage figures altogether rather than
counted as unknown.

**Slice fixed-width files by position, and get the positions from the
publisher's spec.** The fix was verified on eight days spanning both layouts and
2017–2026: every difference is a value the old parser had left null, and zero
values it had already read were changed.

**This is the same date the 61-day clearing-identity anomaly cluster begins**
(2025-03-19 → 2025-06-09), which was recorded as unexplained because it
predates the April blackout by five weeks. As of 2026-09-03 the explanation for
the March onset is no longer a guess about a publication-system change: OMIE
replaced the **day-ahead offer typology itself** on that date (see the
platform-migration section above), so the bid files record a different set of
offer types on either side of it. That is a far better lead than a header-format
change — but still a lead, not a demonstration. Nobody has shown the mechanism
by which the new typology breaks the market-clearing identity, and it does not
explain why the cluster *ends* on 2025-06-09.

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

### A frontier-month zip is a snapshot, and used to be kept forever
Found 2026-09-28. OMIE publishes the month at the publication frontier as a zip
that **grows** as days are released: `curva_pbc_uof_202605.zip` fetched on
2026-08-07 held 8 days. The fetchers treated any valid zip on disk as final, so
re-running them — even with `--force`, which only re-parses — kept that
truncated copy forever and never extended the frontier.

`month_may_grow()` in `lib/omie_common.py` now decides from the data itself,
since OMIE sends neither `Content-Length` nor `Last-Modified`: a month is final
once it reaches its last calendar day, or once it was fetched more than 180 days
after it closed (a day can be absent at source for good — intraday 2026-02-28).
A re-fetched zip whose member list changed is re-parsed automatically.

Applied to bids, intraday, `cab` and the registry build on the zip, and to
`pdbf` on the **parquet**, because `pdbf` deletes its zips once parsed. The
2026-09-28 refresh it enabled recovered bids May (8 → 31 days), intraday May
(11 → 31), `cab` May (13 → 31) and June (5 → 29), and `pdbf` May (15 → 31).

**`indisp` deliberately keeps the old rule** — its short months are short at
source, not frontier snapshots. See the `indisp` section.

### OMIE's offered curves do not re-clear to the published price
Found 2026-10-06 (`analysis/step_curves.py`). Crossing the offered supply and demand
(status `O`) of an hour gives a price €13 too low in June 2019, for two reasons:

- **Units withdrawn by their minimum-income condition stay in the offered curve.**
  About 9 GW an hour of sell offers priced below the price are not accepted; 93% come
  from units accepted in no hour that day, and every one of those declares the condition.
- **The flow with France under market coupling (unit `MIEU`) appears only among the
  accepted rows** (status `C`), sold at −500 / −300 €/MWh or bought at high bid prices,
  with no offered row at all.

**Re-clear on the effective curve:** on each side, the accepted rows on the accepted
side of the price and the offered rows at and beyond it (sell: `C` below p*, `O` at or
above; buy: `C` above p*, `O` at or below). Over 2019–2023 that reproduces the price
exactly in 61–97% of hours a month and within €0.50 in 80–99.6%. Any counterfactual
clearing (resampled residual demand, a competitive benchmark) must start from it.

### The two OMIE files use different decimal separators
`marginalpdbc` uses a **dot** (`77.7`). `curva_pbc_uof` uses a **comma**
decimal with a **dot** thousands separator (`1.500,00` = 1500.0). Do not
share a number parser between them. Both files are **latin-1**, not UTF-8.

### MITECO's reservoir file uses a comma decimal too — same trap, third source
`AGUA_TOTAL`/`AGUA_ACTUAL` in the historical reservoir database are strings
like `"38,00"`. `fetch_hydro_reservoirs.py`'s `parse_comma_decimal()` handles
it the same way `curva_pbc_uof` is handled; do not reuse `marginalpdbc`'s
dot-decimal parser here either.

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
`fetch/fetch_ree_realtime.py` instead — it is finer-grained anyway.

`potencia-instalada` returns HTTP 500 under every combination tried. That is
the one series with no token-free source.

### ESIOS 541 and 542 are not the day-ahead forecasts
Found 2026-10-02, before the first fetch. Indicator 541 *Previsión de la
producción eólica peninsular* and 542 *Generación prevista Solar fotovoltaica*
read like the day-ahead forecasts, and this repo's notes and the token request
named them. Their catalogue descriptions say REE **republishes them every hour**
up to the end of D+1, so the value stored for an hour is a late update holding
information bidders did not have at noon on D-1. Used as an instrument, it would
carry part of the forecast surprise back in. The day-ahead vintage is 1777
(wind), 1779 (solar) and 1775 (demand), published before 11:00 on D-1.
**Read an ESIOS indicator's description for its publication time before using
it as a forecast.**

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

### The demand-forecast series has three unusable periods, one unexplained
`ree_demand_forecast_5min.parquet` looks clean on a spot check and is not:

| period | error sd | MAE | corr | cause |
|---|---|---|---|---|
| before 2025-12-12 | 694 | 336 | 0.990 | usable |
| from 2025-12-12 | 1,737 | 1,569 | 0.938 | the documented realtime contract change — the *actuals* changed, not the forecast |
| 2025Q2 | 2,394 | — | — | the 28 April 2025 Iberian blackout |
| 2023Q1 | 819 (mean −1,204) | — | — | **unexplained** |

A spot check on one day gave an error sd of 1,023 MW and a claim that this
"nearly doubles" the heat shock; on the full series the clean-quarter sd is
200-490 MW and the claim is wrong. **Compute dispersion on the whole series, not
a sampled day** — the sampled day happened to fall in a contaminated stretch.

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

### The intraday market splits independently of the day-ahead market
ES and PT intraday prices differ on **3.4% of periods in 2018 and ~13% in
2022+** — and *not* on the same periods the day-ahead market splits (day-ahead
2018: 5.2%). Filtering a design on day-ahead splitting alone therefore leaves
intraday-split periods in.

This bites hardest on anything derived from `curva_pibc_uof`, because the bid
archive tags almost every unit `MI` rather than by zone (see the trap below), so
pooling both zones' units in a split period picks up whichever side's price is
higher. That is the mechanism behind the 10% of derived intraday prices that
exceed the published clearing price, which the bracket inequality says is
impossible.

### `country` in the bid files does NOT identify a unit's country
Only ~4.7% of matched rows carry `ES` or `PT`; the rest are tagged `MI` for
the joint MIBEL market. That share tracks the ~6.7% market-splitting rate, so
the tag appears mainly **when the market splits**, not as a unit attribute.
Use `data/omie/registry/unit_registry.parquet` instead — see below.

### OMIE's file catalogue is larger than the guessable dataset names
Guessing dataset codes (`unidades`, `agentes`, `unidades_fisicas`) returns a
200-status HTML 404 page, which looks like success. The real catalogue is
AJAX-loaded and holds **59 datasets**; every directory page embeds the full
label→code map in its sidebar, reachable as::

    /es/file-access-list?parents=<path>&dir=<label>     -> page carries realdir=<code>
    /es/file-access-list?parents%5B0%5D=<code>&realdir=<code>   -> file listing

Codes worth knowing beyond the ones already fetched: `pdbc`/`pdbcpt`/`pdbce`
(cleared schedule: Spanish / Portuguese / by company), `indisp`
(unit unavailability — **`indisppt` does not exist**, see below),
`capacidad_inter_*` (interconnection capacity and occupation; `capacidad_inter_pbc`
is now fetched, see the inventory), `trades`/`orders`/`precios_pibcic` (continuous intraday),
`cab`/`det` (offer header and detail).

### JRC's `eff` is not one kind of number — most of it is a class average, not a measurement
`JRC_OPEN_PERFORMANCE.csv` carries a `best_source` field easy to miss on a
first pass (a first cut of `fetch_jrc_ppdb_efficiency.py` didn't check it,
and looked done). For Spain's Fossil Gas units it splits: 66 generator rows
`OEM_derived` (mean eff 0.53, range 0.52–0.55 — a real CCGT), 620
`Class_derived` (mean eff 0.31, clustering at suspiciously round values
0.23/0.35/0.36 — a technology-class default JRC fills in when it has no
plant figure), plus 2 `emissions_*_derived` (plant-specific, back-calculated
from that plant's own reported emissions). `eff_is_generic` in
`jrc_cab_match.parquet` and `implied_marginal_cost_daily.parquet` flags the
`Class_derived`-only rows explicitly — filter on it, not just on `eff` being
non-null, or a small cogeneration plant's generic 0.23 efficiency will
divide the 2022 gas-price spike into an implied cost over 1,000 €/MWh.

### `indisp` unit codes are a physical namespace — 4.9% join the registry
Of 1,529 distinct codes in the unavailability file, only **75 join
`unit_registry.parquet`**. The rest are wind farms, micro-hydro and
cogeneration named `AEROGEN`, `AGBAENA`, `98D-481` — plant identifiers that
never appear as OMIE programming units. Stripping a trailing `B` recovers none,
so it is a genuine namespace difference and not a suffix convention.

That is not fatal, because of *which* 75 match: the large conventional units,
`ASC1` (Ascó 1), `ABO1`, `ARCOS1`, `BES3`. Coverage therefore depends entirely
on which fleet is being asked about:

| population | covered |
|---|---|
| all 1,529 `indisp` codes | 75 (4.9%) |
| the 68 plant-specific-efficiency marginal-cost units | **55 (80.9%)** |
| top 200 units by cleared volume | 41 (20.5%) |

**Measure coverage on the fleet you are using, not on the file.** The 4.9%
headline is the wrong number for every design that would reach for this
dataset, and the 80.9% is the right one for a thermal markup design.

**The namespace is REE's physical units, and that register links them to OMIE
units** (found 2026-10-08). **1,342 of the 1,529 codes (87.8%) are `uf` codes in
`esios_physical_units.parquet`** (ESIOS archive 81), whose `up` names the OMIE unit
that offers each one: 503 reach a unit in the registry that way, against 75
directly. For hydro this is the route: a cascade unit's outages are declared group
by group (`DUER`'s 57 generator groups, 46 of them in `indisp`, 3,513 of its
3,533 MW). Lost MW = the group's `max_power_mw` minus the declared `available_mw`.
The register is a 2026-08-12 snapshot applied to the whole window.
`analysis/hydro_unoffered_capacity.py` uses it.

### JRC's `eic_g` is not always a valid join key
A handful of Spanish units (La Muela's pumped-storage generators among
them) are registered twice in JRC's own source data — once under a
pumping-plant `eic_p`, once under a generation-plant `eic_p` — sharing the
same `eic_g`. A merge naive to this fans out into duplicate rows. Worse:
many renewable units carry a **blank** `eic_g`, and a join that treats `""`
as a valid key silently matches every Spanish blank-`eic_g` row against
every *other country's* blank-`eic_g` row — caught by hand when a first pass
returned German- and Polish-looking EIC codes on nominally-Spanish rows.
`fetch_jrc_ppdb_efficiency.py` drops blank keys before joining and
deduplicates on `eic_g` (preferring a row with a real `eff`) before merging.

### `build_jrc_cab_match.py`'s digit gate was silently inverted by a pandas coercion
Found 2026-08-18, after a first pass already looked complete (53 matches) and
was reported as done. `root_and_digit()` returns `None` for a name with no
trailing unit number, but assigning that into a DataFrame column via
`zip(*series.map(root_and_digit))` silently coerces every `None` to
`float('nan')` — confirmed on this data: 3,882 of 4,945 cab rows, 306 of 344
JRC rows. The gate meant to fire only when *both* sides carry a digit and
disagree was written as `c.digit is not None and j.digit is not None and
c.digit != j.digit` — but `nan is not None` is `True`, and `nan != nan` is
*also* always `True` in Python, so the gate fired on every pair where both
sides genuinely had **no** digit, rejecting them as if they disagreed.
Single-block plants with no trailing number in their name — Meirama,
Castelnou, Los Barrios — were silently absent from the matched set entirely,
not showing up even as a near-miss. Fixed with `has_digit()`, which checks
`isinstance(x, str)` instead of `is not None`, immune to the coercion either
way. This alone recovered several large plants; two further issues below
compounded with it.

### JRC glues a unit number onto the last word; cab always spaces it
`root_and_digit()` originally only split a name at whitespace, so "SOTO 4" (cab)
correctly gave digit `"4"`, but "SOTO5" (JRC, no space) fell through the
digit-less branch entirely, becoming a digit-less name that skirts the digit
gate above rather than a name with digit `5`. This isn't hypothetical
either: Soto de Ribera has both a unit 4 and unit 5 at similar capacity, and
the digit-less "SOTO5" briefly out-competed the *correct* "SOTORIBE 4" pairing
for OMIE's `SRI4R` (unit 4) once a capacity tiebreak was added, purely
because SOTO5's capacity happened to be closer. `root_and_digit()` now
splits a trailing digit off the last token whether or not it's glued on.

### Two Castilian plant names can be closer than they look, and capacity is the tiebreaker
"CASTELLÓN" (a city) and "CASTELNOU" (a specific plant) share enough
characters that `SequenceMatcher` rates them 0.78 similar — comfortably
over this matcher's 0.6 threshold — and with neither JRC nor cab name
carrying a digit to disambiguate (see the trap above), `CTN3`/`CTN4`
(Castellón 3/4) and `CTNU` (Castelnou) all passed the gate against *each
other's* JRC plant as well as their own, correctly reported as ambiguous
rather than guessed at. Capacity resolves it cleanly (Castellón 3 is 782.0
MW against `CTN3`'s 782.0 MW; Castelnou is 790.6 against `CTNU`'s 797.8) —
`build_jrc_cab_match.py`'s capacity tiebreak accepts a pairing only when it
is *mutually* the closest-capacity candidate on both sides, with a 1.5x
margin over the runner-up, precisely to resolve cases like this without
opening the door to a coincidental capacity match with an unrelated plant.

### Building a hand-verified alias table recovered 2.4 GW no gate combination would find
`P.G.RODR 5` (JRC) and `PGR5` "C.C. PUENTES 5" (cab) are the same 855.6 MW
plant, capacities matching to the decimal — but `P G RODR` and `PUENTES`
share almost no characters (JRC abbreviates the plant's full name, cab uses
one word from it), so no similarity threshold that also accepts genuine
spelling variants (`ESCATRÓN`/`ESCAT`, `SOTORIBE`/`SOTO`) can also reject
this one. Same story for `ESC IBER 6`/`ESC6` (Escombreras), `ESC CART
1-3`/`CTGN1-3` (Cartagena), and `CAMPGIB1/2`/`CAMGI10/CAMGI20` (Campo de
Gibraltar, which additionally uses different internal unit numbering
between the two sources). `MANUAL_ALIASES` in `build_jrc_cab_match.py`
encodes these 11 pairings by hand, each checked against capacity before
being added — the same discipline `PREFIX_AGENTS` in `build_unit_agents.py`
already uses for ownership. Combined with the two fixes above, matched
capacity went 54.2% → 82.7% without loosening either automatic gate.

### MIBGAS reshaped its own workbook twice — three layouts, not one
Checked year-by-year rather than assumed: 2018–2020 uses sheet `Indices`,
one row/day, price in `MIBGAS-ES Index`; 2021–2022 keeps the sheet name but
goes **long** — two rows/day, `Area` in `{ES, PT}`, price renamed to
`MIBGAS Index`; 2023 onward renames the sheet to `MIBGAS Indexes` (plural),
back to one row/day, with several new PVB/VTP columns alongside the old
price. `fetch_mibgas_prices.py` dispatches on the sheet name and column set
actually present per year, not on a hardcoded date, the same discipline
`cab`'s 2025-03-19 layout change already required.

### The EUA and coal price fetchers are the two non-resumable sources in this repo
`api.investing.com`'s historical-data endpoint (the only free source found
with full 2018–2026 daily coverage — see the data-inventory section above)
returns HTTP 403 to a plain `requests`/`curl` client even with a complete,
realistic browser header set (Origin, Referer, `sec-fetch-*`, `sec-ch-ua`,
a real Chrome UA) — this is TLS/behavioural fingerprinting, not a missing
header, and it only succeeds from an authenticated browser session.
`fetch_eua_carbon_price.py` (and `fetch_coal_price.py`, same instrument
family, ticker `ATWMc1`, id `1112838`) therefore do not fetch anything
themselves; they parse an already-captured raw CSV
(`data/investing/raw/eua_carbon_emissions_historical.csv` and
`coal_rotterdam_historical.csv` respectively) and exit with instructions
rather than a stack trace if that raw file is missing. Refreshing either
series needs a human (or a browser-automation session) to repeat the
capture — every other fetcher in this repo is a `requests`-only script that
re-runs unattended; these two are not.

### The ECB FX field name inverts the obvious reading
`ecb_usd_eur_daily.parquet`'s `usd_per_eur` column sits under a series keyed
`D.USD.EUR.SP00.A` (`CURRENCY=USD`, `CURRENCY_DENOM=EUR`) — read naively
that looks like "how many EUR per USD," the opposite of what it is. The
published number is USD needed to buy 1 EUR (1.2065 on 2018-01-02, correct
for that date), so converting a USD amount to EUR **divides** by it, not
multiplies. `build_implied_marginal_cost.py`'s coal-price conversion divides;
getting this backwards would move the coal-side marginal cost the wrong
direction by the square of the true adjustment.

## Known source-data anomaly: whole-day unit dropouts

A recurring class of gap in OMIE's publication — **not** a parsing artifact.
On an affected day, a block of units is simply absent from the file for all
24 hours, so matched buy no longer equals matched sell and the imbalance is a
near-constant MW offset across the day. Affected files are normal size and
parse cleanly.

A full scan of the archive on 2026-08-11 — re-deriving the market-clearing
identity for every one of the 89,039 day-ahead periods rather than spot-checking
— found **63 affected days (0.70% of periods), not the 2 previously recorded.**
They are two distinct phenomena:

**Whole-day dropouts** — all 24 periods affected, a block of units simply
absent. These are the originally documented cases:

| date | direction | offset | missing units |
|---|---|---|---|
| 2018-06-14 | buy > sell | ~2,900 MWh/h | 13 sell units, incl. the `MIEU` interconnection pseudo-unit |
| 2022-10-12 | sell > buy | ~3,098 MWh/h | 16 buy + 24 sell units |

**A 2025 cluster** — 61 days from **2025-03-19 to 2025-06-09**, *partial*-day
(1–23 periods, not all 24). Sporadic through late March and April, then every
single day of May at 10–23 periods each, decaying through early June. The
ramp-up follows the **28 April 2025 Iberian blackout** and the weeks of
reinforced grid operation after it, but the onset predates the blackout by five
weeks. Do not assume one cause.

The March start is no longer wholly unexplained: **`cab` changed its
fixed-width layout on exactly 2025-03-19** (see the trap below), so OMIE
altered something in its publication chain that day. That does not
mechanically explain a clearing-identity gap in a different dataset, but a
coincidence of exact dates across two files is worth pursuing before
attributing the cluster to the blackout.

The direction varies with which side loses more. Left as-is rather than
patched — imputing bids would be inventing data.

**Detect these from the clearing identity, never from a hardcoded date list.**
That is how the 61 new days surfaced; a date list would have silently passed
them. Note the practical consequence: they are **not randomly distributed**,
so dropping them thins 2025 in a correlated way — any 2025 result computed on
the surviving periods carries that selection.

**Always run `fetch_omie_bids.py --verify`**, which re-checks the
market-clearing identity per month and prints the maximum gap; a non-zero
value flags exactly this. Filter these days out of any design that relies on
market-wide aggregates. Analyses of individual units' bidding are unaffected
except for the units actually missing.

## Auditing

`audit_data.py` re-derives coverage, duplicates, schema uniformity and value
ranges **from the files themselves** rather than trusting fetch logs. Run it
after any re-fetch:

```bash
.venv/bin/python scripts/qa/audit_data.py
```

It exits non-zero on any problem. As of 2026-08-11 it reports **no problems**,
with four documented notes (see below). Two things it exists to catch, both of
which actually happened here: a fetcher exiting 0 after parsing a fraction of
a month, and a timestamp column silently full of NaT.

### Known, verified exceptions

- **Intraday: 2021-07-30, 2025-04-29, 2026-02-28 are absent at source.** The
  monthly zips contain *zero* members named for those dates. Listed explicitly
  in `KNOWN_ABSENT` so a genuinely new gap still fails the audit.
- **One row dated 2017-12-31** sits in the January 2018 intraday zip: session
  files carry their own delivery date, which can precede the filename date.
- **20 registry units have no country and 13 no role** — they appear in
  `pdbce` but not in the sampled `pdbc`/`pdbcpt` days. A `--full` registry
  build resolves them.

## Conventions

- Raw downloads are never modified; re-fetch instead.
- Derived outputs go to `outputs/`; raw and parsed data to `data/`.
- Fetchers are resumable — they skip what is already on disk.
  **Exception: `fetch_eua_carbon_price.py` and `fetch_coal_price.py`** —
  see the trap above.
  `fetch_snirh_reservoirs.py` is resumable but runs **only through LMU
  eduVPN**, the one address APA whitelisted; see the SNIRH section.
- Commit messages: imperative, present tense, ≤72-char subject.
- Never commit `.env` or anything under `data/`.
