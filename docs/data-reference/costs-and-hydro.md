# Marginal costs, hydro cost, reservoirs, rainfall

_Implied CCGT/coal cost, hydro cost, JRC hydro, SNIRH, E-OBS, HydroBASINS. Moved verbatim from `CLAUDE.md` on 2026-11-12; see `docs/data-reference/README.md`._

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
