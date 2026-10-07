# A competitive water value from forward prices

Run 2026-10-07. Script: `build/build_water_value_forward.py`. Output:
`outputs/tables/water_value_forward.parquet` (unit-day λ*), `forward_price_quantiles.parquet`
(the expected price distribution by zone, day and horizon). Framework spec §2.2, leg B.

**In one line.** A water value built only from forward prices, last year's hourly price
shape and each unit's usual capacity factor reproduces the water value EDP reveals in its
offers: for its four big storage cascades the medians agree within 6% (Cávado 102 against
98, Lima 96 against 99, Guadiana 96 against 102, Mondego 104 against 100 €/MWh), with
correlations of 0.81–0.91 over 2019 – May 2026. Iberdrola, Naturgy and Movhera offer well
above it at half of their offered volume, but not at the volume they expect to run: there
all five groups sit at 0.90–1.19 times it (§5.3).

**Addendum, storage (§5.2–§5.3).** Adding each unit's reservoir fill (MITECO by basin for
Spain, SNIRH for Portugal) improves the forecast of its monthly capacity factor for 18 of
20 units (median 11% less error) but moves λ* by only €1–4. The 2–3× gap of Iberdrola,
Naturgy and Movhera is not scarce water: it is the price of turbine capacity with no water
behind it. Read at each unit's expected running share, offers over λ* are EDP 0.90,
Endesa 0.92, Movhera 0.93, Naturgy 1.13, Iberdrola 1.19.

## 1. The idea, with an example

A reservoir whose turbines can run 25% of the hours of the coming month, on the water it
expects, does best by running in the month's dearest quarter of hours. A price-taker
therefore offers its water at the price only a quarter of the month's hours exceed: the
75th percentile of the prices it expects. If forwards say the month averages €60 and last
year's same month had its dearest quarter of hours above 1.25 times the month's mean,
λ ≈ €75.

    λ*(u, D, H) = Q_{1 − cf(u, m)} of the prices expected over the H days from D

## 2. Built from what was known at noon on D−1

| input | source | note |
|---|---|---|
| forward level | OMIP Spanish settlement on the last trade date on or before D−2 | each future day takes the finest contract covering it: day, weekend, week, month, quarter, year |
| hourly shape | hourly day-ahead price over its month's mean, same calendar month a year earlier, as 99 percentiles | OMIP trades base load only; the unit's own zone |
| capacity factor | the unit's PDBF output over `cab` max power in that calendar month, mean over the other years | so a year's own withholding does not set its own benchmark |
| horizon H | 30 and 90 days | |

Portugal's OMIP curve has settlements on 6% as many contract-days as Spain's, and the
zones share one price in 93% of hours, so Portuguese units use the Spanish forwards with
their own price shape. 79 storage and pumped units of the step caches, 200,673 unit-days;
λ*30 is defined on 98% (the forward curve misses more than 10% of a 30-day window on 57
days). From 2019, since the shape needs a year of prices. Median capacity factor 0.21.

| year | forward | λ*30 | λ*90 |
|---|---|---|---|
| 2019 | 48 | 54 | 58 |
| 2020 | 36 | 40 | 42 |
| 2021 | 88 | 103 | 102 |
| 2022 | 161 | 188 | 194 |
| 2023 | 90 | 115 | 125 |
| 2024 | 57 | 87 | 91 |
| 2025 | 64 | 93 | 93 |

The gap between λ* and the forward widens from 2024: solar spreads prices within the
month, so the dear hours a reservoir runs in sit further above the mean.

## 3. Against the water value EDP reveals

`water_value_revealed.parquet` (`rq-midday-hydro.md` §3.16) holds λ̂50, the price at half
of the offered volume, for nine EDP and Movhera units. Medians in €/MWh, 2019 – May 2026:

| unit | λ̂50 offered | λ*30 | correlation | slope of λ̂ on λ* |
|---|---|---|---|---|
| ACAVADO (Cávado) | 102 | 98 | 0.91 | 0.82 |
| ALIMA (Lima) | 96 | 99 | 0.88 | 1.20 |
| GUADIA (Guadiana) | 96 | 102 | 0.86 | 0.75 |
| MONDEGO | 104 | 100 | 0.81 | 1.06 |
| TEMON (Tejo-Mondego) | 96 | 91 | 0.76 | 1.55 |
| ADOURO (Douro) | 60 | 84 | 0.78 | 1.25 |
| VIES (Viesgo) | 60 | 83 | 0.76 | 0.93 |
| HCHI (Hidrocantábrico) | 123 | 89 | 0.81 | 1.28 |
| DOUSUP (Douro Internacional, Movhera) | 249 | 113 | 0.58 | 1.05 |

- **The four big storage cascades match** in level within 6% and move with it. Nothing
  in the benchmark was fitted to EDP's offers.
- **ADOURO (EDP's Douro) and VIES (UGH Viesgo) offer about a quarter below it**;
  HCHI (UGH Hidrocantábrico) about a third above.
- **DOUSUP (Douro Internacional, the dams EDP sold to Movhera, out of ADOURO since January
  2022) offers at twice the benchmark.**

## 4. Against every storage unit's offers

Here λ̂ is the volume-weighted median of a unit's offered hydro steps over the day
(`hydro_YYYYMM`). It is a cruder measure: many units offer most of their volume at zero
(run-of-river and aggregated portfolios), so their median is 0.

| group | unit-days | median λ̂ | median λ*30 | within-unit slope |
|---|---|---|---|---|
| EDP | 18,666 | 83 | 101 | 1.04 |
| Iberdrola | 19,549 | 154 | 101 | 1.08 |
| Naturgy | 9,571 | 143 | 90 | 0.74 |
| Movhera | 1,475 | 254 | 121 | 1.03 |
| Endesa | 19,258 | 1 | 96 | 0.61 |
| Repsol | 10,891 | 0 | 89 | 0.16 |

- **Within a unit, offers follow λ* about one for one** for EDP, Iberdrola and Movhera.
- **Iberdrola, Naturgy and Movhera offer half again to double the benchmark.** Three
  readings, not yet separated: holding water back to raise its value (market power on the
  across-day margin, leg B), the option value of waiting that the benchmark leaves out
  (inflows are uncertain), or a capacity factor that understates how scarce their water is.
- **Endesa's and Repsol's medians are zero**: most of their offered hydro is priced at
  zero, so this measure says nothing about their marginal water.

## 5. Limits

- No inflow uncertainty, so no option value: the benchmark should sit below a
  competitive water value when inflows are uncertain, never above.
- Capacity factor from the unit's own history, not its reservoir: a dry year lowers the
  true release share and raises λ, and this misses it. Inflows and storage (SNIRH for
  Portugal; MITECO by basin for Spain, §5.1) are the next refinement.

### 5.1 Spanish storage (2026-10-07)

ESIOS 623 turned out to be one peninsular series, not one per market agent (CLAUDE.md,
ESIOS section). The per-unit route is MITECO's weekly reservoirs by demarcation, since
Spain's hydro units are registered by basin. `qa/check_hydro_storage_spain.py`: the
monthly capacity-factor anomaly of each big Spanish unit against its own basin's fill
anomaly, against the national series and against every other basin.

| unit | basin | own | national | rank of 16 |
|---|---|---|---|---|
| DUER (Iberdrola) | Duero | 0.67 | 0.69 | 1 |
| TAJO (Iberdrola) | Tajo | 0.68 | 0.57 | 1 |
| SIL (Iberdrola) | Miño-Sil | 0.65 | 0.61 | 1 |
| JUCA (Iberdrola) | Júcar | −0.17 | 0.39 | 16 |
| EBRFEN (Endesa) | Ebro | 0.72 | 0.57 | 1 |
| SBEU (Endesa) | Miño-Sil + Galicia Costa | 0.74 | 0.62 | 1 |
| TERE (Endesa) | Catalan internal basins | 0.67 | 0.18 | 1 |
| UFMI (Naturgy) | Miño-Sil | 0.66 | 0.45 | 1 |
| HCHI (EDP) | Cantábrico Occidental | 0.52 | 0.09 | 2 |

(Full table, 16 units, in the script's output.) Own basin ranks first for 8 of 16,
top three for 13. Usable for every Spanish UGH except Júcar. Realised capacity factor
is partly the firm's choice, so this shows the basin series carries unit-specific
information, not that it is exogenous.
- Forward risk premia move λ* with the forward.
- Unit contents change: EDP moved ~1,000 MW from ACAVADO to ALIMA in March 2024.

### 5.2 Storage in the benchmark (2026-10-07)

`build_water_value_forward.py` now also writes `cf_s`, `lam30s`, `lam90s`. A unit whose
reservoirs are fuller than usual for the week of the year expects to release more, so it
values its water less:

    cf_s(u, D) = α_m + b × (fill(u, D) − normal fill for D's ISO week)

fill is MITECO's stored over capacity in the unit's demarcation(s) (Spain; units whose
basin ranked top three in §5.1, so not JUCA, TEES or VIES) or SNIRH's volume of the
unit's own reservoirs (Portugal; EDP's seven cascades and Movhera, by river after
`build_storage_hours.py`; Iberdrola's TAMEGA has no volume series). The reading is the
latest on or before D−2. The normal and α_m, b are fitted on the other years only, b on
the fill anomaly on the month's first day. Example: Duero 10 points fuller than usual,
b = 0.43 for DUER, so cf 0.19 becomes 0.23 and λ moves from the 81st to the 77th
percentile of expected prices.

**Out of sample it forecasts the month's capacity factor better** for 18 of 20 units
(median 11% less root mean squared error; 14–27% for DUER, TAJO, SIL, EBRFEN, TERE,
ALIMA, TEMON). Worse for EBRA (−0.4%) and HCHI (−2.5%).

**It moves λ* little**: yearly medians by €0–4 (2022 +3.5, 2026 −2.5). Against EDP's
revealed λ̂50 correlations are unchanged or up to 0.03 higher, and three slopes move
toward one (ALIMA 1.20 → 0.99, ADOURO 1.25 → 1.09, TEMON 1.55 → 1.32).

### 5.3 The gap is turbine capacity without water, not scarce water

`analysis/water_value_forward_check.py`. If scarce water drove Iberdrola's and Naturgy's
high offers, their offers would sit further above λ* when their reservoirs are low.
They do not: the within unit × month slope of log(offer / λ*30s) on the fill anomaly is
+0.49 (Iberdrola) and +1.15 (Naturgy) at o50, against −0.26 (EDP) and −0.63 (Endesa).

What does explain it: a cascade unit offers all its turbine capacity, but has water for
about a fifth of the hours. A price-taker offers the water it expects to use at λ; how it
prices the capacity beyond that says little about λ. The price at half of the offered
volume (o50, §4) mixes the two. Read instead at the unit's expected running share cf_s
(ocf):

| group (storage units) | unit-days | o50 / λ*30s | ocf / λ*30s | within-unit slope at ocf |
|---|---|---|---|---|
| EDP | 16,666 | 1.04 | 0.90 | 0.77 |
| Endesa | 9,454 | 1.03 | 0.92 | 0.56 |
| Iberdrola | 9,576 | 2.75 | 1.19 | 1.02 |
| Naturgy | 7,179 | 1.22 | 1.13 | 0.77 |
| Movhera | 1,358 | 1.84 | 0.93 | 1.09 |

By unit at ocf: Iberdrola DUER 1.12, SIL 1.13, TAJO 1.02, EBRA 3.37 (a 220 MW unit
offered at a flat ~€380); Naturgy UFMI 1.19, UFGC 1.11, UFTA 0.77; Endesa's GDLQ offers
everything at ~0.

- **The 2–3× gap was the measure.** At the volume each unit expects to run, every group
  is within 0.9–1.2 of the price-taking benchmark.
- **What is left: Iberdrola and Naturgy sit 20–30% above EDP and Endesa** (1.19 and 1.13
  against 0.90 and 0.92). That is the leg B question, and it is a modest gap.
- **The groups respond to storage differently.** At ocf the slope of the gap on fill is
  −0.42 (EDP) and −0.80 (Endesa) but +0.70 (Iberdrola) and +0.54 (Naturgy): EDP and
  Endesa cut their offers more than λ*s when reservoirs fill, Iberdrola and Naturgy less.
- **Steep offer curves beyond cf_s** (Iberdrola: p10 1.11, ocf 1.19, o50 2.75 times λ*)
  are consistent both with withholding capacity and with a marginal water value that
  rises with the volume committed within the day (a cascade cannot run every plant at
  once). Not separated here.

## 6. What it enables

- **Leg B in levels**: λ̂ − λ* on the day's markup term, with an instrument.
- **The at-cost instrument on hydro** (`rq-step-estimator.md` §7): λ* is the cost point at
  which to evaluate X. Any function of what was known when offers close is a valid
  instrument, so λ* need only be close to the true cost to be strong, not exact.
