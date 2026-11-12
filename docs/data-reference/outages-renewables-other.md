# Outages, renewables locations and other sources

_Reactor and plant outages, wind/solar locations, holidays, PDVD, France, Italy, GB, GIE, NUTS, temperature, `indisp`, interconnection. Moved verbatim from `CLAUDE.md` on 2026-11-12; see `docs/data-reference/README.md`._

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
published NBP average of about 200 p/therm (£68). NBP day-ahead quotes are not free. Carbon: the UK ETS allowance future
from investing.com ("UK Emissions Allowances Energy c1", captured by hand 2026-10-28 into
`data/investing/raw/uka_carbon_historical.csv`, 2021-05-20 →; 2022 mean £78/t), plus the £18/t Carbon
Price Support. `build/build_gb_marginal_cost.py` costs 91 British gas units (75 plant-specific, 68 with
an Elexon id) in pounds and in euros (ECB GBP rate, `data/ecb/ecb_gbp_eur_daily.parquet`); 2022 median
£181/MWh. Its ceiling is £1,000: small peaking turbines at efficiencies of 0.25–0.29 reach £868.

### Iberian gas storage and LNG send-out — GIE (2026-11-05)
`fetch/fetch_gie_gas.py`: Gas Infrastructure Europe's AGSI+ (storage) and ALSI (LNG terminals), country
level, **every gas day 2018-01-01 → 2026-11-03 for ES, PT and IT** (3,229 days each; IT added the same day for the Italian control), raw answers kept in
`data/gie/raw/`. A free personal key (`GIE_API_KEY`, `x-key` header; registered by the user 2026-11-05)
serves both platforms. Cite GIE as the source. Fields keep GIE's names: storage `gasInStorage` (TWh),
`injection`/`withdrawal` (GWh/d), `workingGasVolume`, `full` (%); LNG `sendOut` (GWh/d into the grid),
`inventory.gwh`, `dtrs` (declared send-out capacity). `status` E marks GIE's estimated days (LNG 157,
storage 40). Checks: Spanish send-out 189 TWh in 2021 and 281 TWh in 2022, the jump after the
Maghreb–Europe pipeline closed (November 2021); working gas ~35 TWh in Spain, 3.57 TWh in Portugal
(Carriço). Exists for the one confound the gas-cap control tests left open: Iberian offers responding
to physical gas supply rather than the price (`notes/rq-gas-cap-control.md`).

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
