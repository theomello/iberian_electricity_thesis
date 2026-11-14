# Script table

_Every fetch, build and QA script with its source, token need and output. Moved out of CLAUDE.md 2026-11-12. Moved verbatim from `CLAUDE.md` on 2026-11-12; see `docs/data-reference/README.md`._

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
| `build/build_direct_consumers.py` | unit lists + ESIOS + `cab` + PDBF + ownership | no | `data/omie/registry/direct_consumers.parquet` |
| `build/build_direct_consumer_panel.py` | bids + prices + `direct_consumers` | no | `outputs/tables/direct_consumer_panel/panel_YYYYMM.parquet` |
| `build/build_cogeneration_units.py` | unit lists + `cab` + PDBF + ESIOS physical units | no | `data/omie/registry/cogeneration_units.parquet` |
| `build/build_cogeneration_panel.py` | PDBF + `cab` + bids + prices + `cogeneration_units` | no | `outputs/tables/cogeneration_panel/panel_YYYYMM.parquet` |
| `build/build_cogeneration_ree_panel.py` | I90DIA workbooks + ESIOS programming and physical units | no | `outputs/tables/cogeneration_ree/days/ree_YYYYMMDD.parquet`, `ree_units.parquet` |
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
| `fetch/fetch_esios_i90.py` | ESIOS archive 34 (I90DIA), 15th of each month, and every day of 2021 and 2022-04-01 → 2023-03-31 | **yes** | `data/esios/raw/archives/34/`, `data/esios/i90/i90_sample_hourly.parquet` |
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
| `fetch/fetch_uka_carbon_price.py` | investing.com UKA futures (browser-captured) | no, but not resumable | `data/investing/uka_carbon_price_daily.parquet` |
| `build/build_gb_marginal_cost.py` | JRC UK + ONS SAP + UKA + CPS + ECB GBP | no | `data/jrc_ppdb/gb_implied_marginal_cost_daily.parquet` |
| `fetch/fetch_gie_gas.py` | GIE AGSI+ (gas storage) and ALSI (LNG terminals), Spain, Portugal and Italy | **yes** (`GIE_API_KEY`) | `data/gie/gie_{storage,lng}_daily.parquet` |

`lib/omie_common.py` holds shared parsing and DST/resolution logic;
`lib/config.py` loads tokens from a gitignored `.env`; `lib/regions.py` gives a
coordinate its country and region (`locate`); `lib/holidays.py` turns the holiday
table into area × day indicators (`unshared`, `bridges`, `market_wide`); `lib/rd.py` holds the
regression-discontinuity jump and McCrary's density test.
