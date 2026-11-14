# Traps, source anomalies and auditing

_Every silent-failure trap found in the data, the whole-day dropouts, and the audit exceptions. Moved verbatim from `CLAUDE.md` on 2026-11-12; see `docs/data-reference/README.md`._

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

### Offer prices were capped at €0–180.30 until 2021-07-06
Verified 2026-10-28 on `curva_pbc_uof` (status `O`). Until delivery day 2021-07-06 every day-ahead
offer and bid lies between €0 and €180.30. From **2021-07-07** the limits are **−€500 and €3,000**,
the European coupling's harmonised limits, set by the CNMC resolution of 6 May 2021 (BOE-A-2021-8362,
which names the old limits as €0 and €180); the first negative sell offer is that day, the first sell
offer above €180.30 on 2021-07-10. **Any count of offers far above cost or below zero is zero by rule
before that date**: read a rise in high-priced blocks across mid-2021 as the limits moving, not conduct.
The clearing price itself never came near either limit (Spanish maximum €700, minimum −€15).
**The comparison countries' limits did not move the same way** (checked 2026-10-28, offered sell side): GME's Italian offers already reach €3,000 in June 2021 (11% of rows above €180.30), the ceiling rises to €4,000 from May 2022 and the floor goes €0 → −€500 in September 2021; Iberia's ceiling stays €3,000 through 2022 (floor −€300 in practice). British balancing offers run to £9,999 throughout, no change. So only Iberia gained room to post high prices inside the gas-cap comparison's pre-period.

### Cleared rows of SCO offers carry −500, not their step price
Found 2026-11-05. From 2025-03-19 a unit offering a Scalable Complex Order (a `cab` `sco_fixed_eur` > 0) gets
**−500 €/MWh on every cleared (`C`) row** of `curva_pbc_uof` (100% of 7,423 rows of declaring thermal units in July 2025;
19–36% of non-declaring ones). Before the switch cleared rows carry the step price. Anything reading offer prices off
`C` rows in the SCO era is wrong: fill the cleared quantity up the offered (`O`) curve in price order instead
(`startup_cost_correction.py --sco`). `offer_type` is empty until 2025-12 and filled from 2026-01 (`C02` = SCO).

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
