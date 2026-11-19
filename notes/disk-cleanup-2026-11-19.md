# Disk clean-up of gitignored data and outputs (2026-11-19)

**Why:** disk 88% full (12 GiB free of 113). Estimation is wrapping up; the thesis keeps the supply side only in the
descriptive chapter (`supply-side-summary-2026-11-19.md` §2). This note lists what could go, what reads it, and
how it would come back. Each deletion is decided by the user item by item (§3).

**No real backup target.** `~/projects/vre_spain_backup_staging/` is on the same disk, and no external volume is
mounted, so "move to staging" frees nothing. Items that are hard to get back are therefore marked *keep*, not
*move*. To reclaim those, copy them to an external drive or cloud storage first.

**Re-fetch caveat (OMIE, REE realtime).** The fetchers skip a month or day only if its *raw* file is on disk. With
the raw zips gone, a plain re-run downloads everything again. To add a month later, pass it explicitly
(`--months 202606`); the parsed parquets stay untouched.

## 1. Candidates: proposed for deletion

Total if all are approved: **≈ 10.7 GB**.

| # | Path | Size | What reads it | How to get it back | Recommendation |
|---|---|---|---|---|---|
| 1 | `data/omie/intraday/zips/` | 3.0 G | nothing outside the fetcher; analysis reads `intraday/parquet/` (1.6 G, kept, 102 months) | `fetch_omie_intraday.py` (public OMIE archive) | **delete**: intraday is out of the thesis |
| 2 | `data/omie/bids/zips/` | 2.3 G | nothing outside the fetcher; all analysis reads `bids/parquet/` (1.1 G, kept, 102 months) | `fetch_omie_bids.py` (public OMIE archive since 2018) | **delete**: only needed to re-parse after a parser fix |
| 3 | `data/omie/indisp/zips/` | 0.42 G | nothing outside the fetcher; analysis reads `indisp/parquet/` (3.6 M, kept) | `fetch_omie_unavailability.py` (public) | **delete** |
| 4 | `data/gme/raw/` | 1.8 G | only `fetch_gme_offers.py --parse-only` | `fetch_gme_offers.py` (public; GME terms cookie, accepted 2026-10-28) | **delete**: Italy is a closed, failed control |
| 5 | `data/gme/offers/parquet/` | 1.1 G | `build_italy_demand.py`, `gas_cap_offer_panel.py`, `gas_plants_at_cap_iberia_italy.py` (Italy designs, closed). `italy_demand_placebo.py` reads `italy_demand_hourly.parquet` and `gme/gas/`, which are **kept** | `fetch_gme_offers.py` (≈ 760 days, hours) | **delete**: Italy is only an appendix paragraph, and its tables are already in `outputs/tables/` |
| 6 | `data/elexon/` (raw, bod, pn, bmunits) | 0.21 G | `gas_cap_gb.py`, `build_gb_marginal_cost.py` (GB closed) | `fetch_elexon_bod.py` (free API, no key) | **delete** |
| 7 | `data/eobs/raw/` (two `.nc` grids) | 0.77 G | only the fetcher; `build_catchment_rain.py` and the analysis read the built `eobs_rr_iberia_daily.parquet` and `catchment_rain_daily.parquet` (kept) | `fetch_eobs_precipitation.py`. KNMI versions the file (v33.0e); a later re-fetch may get a newer version | **delete** |
| 8 | `data/ree/realtime_raw/` (3,073 daily JSON) | 0.45 G | only the fetcher; analysis and the audit read `ree_realtime_5min.parquet` (kept) | `fetch_ree_realtime.py` (public; one request per day) | **delete** |
| 9 | `data/hydrosheds/raw/hybas_eu_lev01-12_v1c.zip` | 0.34 G | only the fetcher; `hybas_iberia_lev*.parquet` kept | `fetch_hydrobasins.py` (public) | **delete** |
| 10 | `outputs/tables/firm_residual_demand_full.parquet` | 0.33 G | no reader; `residual_demand_firm.py` writes it next to the `_owner` version that everything downstream reads | `residual_demand_firm.py` | **delete**: superseded by `firm_residual_demand_full_owner.parquet` |

## 2. Large items to keep (and why)

| Path | Size | Why it stays |
|---|---|---|
| `data/esios/raw/archives/34/` (I90DIA, 1,860 days) | 7.2 G | REE issues `ESIOS_TOKEN` on condition that data already downloaded is not requested again (`fetch_esios_i90.py`), so in practice **not re-fetchable**. The parsed `i90/` parquet keeps only 4 of ~37 sheets. To reclaim this, copy it to an external drive first |
| `data/esios/raw/<indicator>/` | 1.8 G | same token condition (`fetch_esios_spain.py`) |
| `outputs/cache/step/` | 3.6 G | the core of the price-taker benchmark (ten simulated seeds, step estimator, fixed-step design) behind chapter 2's "offers sit near cost" and the hydro departure. Also read by `tou_price_effect.py` (chapter 6). Rebuilding takes many hours |
| inputs of the planned rerun (hydro price-taking simulation, step estimator, fixed-step design; request from the linked session, 2026-11-19): `outputs/cache/step/`, `data/omie/bids/parquet/`, hydro water-value tables (`hydro_cost_daily`, λ* forwards), `outputs/tables/price_taking_simulation_*` and `fixed_step_*` | — | **never propose deleting these.** The rerun reads bids only through `step_curves.py` → `omie/bids/parquet/`; it does not read `bids/zips/` (item 2) |
| `outputs/tables/firm_incentive_net.parquet` | 1.3 G | read by `tou_reform_market_power.py` (T2, chapter 6) |
| `outputs/tables/firm_residual_demand_full_owner.parquet` | 0.78 G | input to `firm_incentive_rebuild.py`, which rebuilds the file above |
| `outputs/tables/step_estimator_*rows.parquet` | 0.22 G | hydro departure (chapter 2) |
| `data/omie/{bids,intraday,pdbf,cab,…}/parquet` | ≈ 3.6 G | the parsed market data everything reads |
| `data/goiener/raw/` | 1.2 G | demand side, fetched by hand 2026-11-17 (Zenodo 7362094, no script). `build_goiener_daily.py` re-streams it if the household selection changes |
| `data/cache_tou/` | 0.28 G | demand-side caches, work in progress |
| stopped-design panels in `outputs/tables/` (self-supply, intraday, own-wind, Iberdrola quantity) | ≈ 0.25 G | small. They back appendix numbers if a rerun is ever asked for |
| `data/omie/unit_lists/`, `data/snirh/raw/`, `data/investing/raw/*.csv` | small | not re-fetchable (`CLAUDE.md`) |

## 3. Decisions (user)

| # | Item | Decision (2026-11-19) | Done |
|---|---|---|---|
| 4 | `data/gme/raw/` | delete | deleted (25 month folders) |
| 5 | `data/gme/offers/` | delete | deleted (760 daily parquets) |
| 6 | `data/elexon/` | delete | deleted |
| 1 | `data/omie/intraday/zips/` | user wants to discuss | — |
| 2 | `data/omie/bids/zips/` | user wants to discuss | — |
| 3 | `data/omie/indisp/zips/` | user wants to discuss | — |
| 7 | `data/eobs/raw/` | user wants to discuss | — |
| 8, 9 | `data/ree/realtime_raw/`, `data/hydrosheds/raw/` | user wants to discuss | — |
| 10 | `outputs/tables/firm_residual_demand_full.parquet` | not yet asked | — |

Freed so far: ≈ 3.1 GB (disk 88% → 84% used, 16 GiB free).
