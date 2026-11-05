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

**Addendum, bilateral contracts (§5.5).** Reading the auction offer at the water left after
each unit's bilateral contracts narrows Iberdrola's gap (1.16 → 1.11; 1.21 → 1.07 in 2025)
but not Naturgy's (1.19 → 1.22) and widens Endesa's (1.13 → 1.35), because those two offer
only part of their capacity in the auction. On 29–31% of Iberdrola's and Naturgy's days
the contracts alone take all the expected water.
That unoffered capacity is not out of service (§5.6): declared outages explain 96% of what
Iberdrola leaves unoffered but 17% of Endesa's and Naturgy's. Nor is most of it offered in
the intraday sessions (§5.7): Endesa 1–4% of the rest, Naturgy 3–42%. REE's per-unit files
for one day a month (§5.9) show 2% of Endesa's and 7% of Naturgy's held as reserve or used
in a later market: about 80% of their unoffered hydro capacity is not used anywhere.

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
  competitive water value when inflows are uncertain, never above. Tested within the month in §5.4:
  under 1%.
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

### 5.4 Option value is under 1%; the horizon matters more (2026-10-07)

`build_water_value_forward.py`, columns `cf_w`, `lam30w`, `lam30o`. λ* assumes the unit
knows how much water the month brings. It does not, and if λ is convex in the running
share, uncertainty raises the expected value of the water. Example: a unit expecting to
run 20% of the hours prices at the 80th percentile; if it may run 10% or 30%, its water
is worth the average of the 90th and 70th percentiles, not the 80th.

Built as the mean of λ over each unit's own forecast errors: realised over forecast
capacity factor on the month's first day, in the other years and calendar months within
±1 (median 18 scenarios), applied to a forecast that adds catchment rain to the fill.

- **Rain adds nothing to fill**: out of sample the month's capacity factor is forecast
  0.7% better (median; 13 of 24 units better). For the four units with no storage series
  it helps TEES (8%) and JUCA (1%) and hurts TAMEGA (−16%).
- **The option value is under 1%**: λ30o over λ30w has median 0.99–1.01 for every group
  and 0.996–1.007 by year 2019–2025 (2026, five months: 1.03). The forecast errors are wide
  (realised over forecast, p10 0.40, p90 1.74), but over that range λ is close to linear in
  the running share: λ at half and at 1.5 times the share average to within 0.3–0.9% of λ
  at the share. On the actual price distributions the 70th and 90th percentiles average to
  about the 80th. **λ*30s stays the cost.**
- **It cannot explain the gap of Iberdrola and Naturgy**. A longer horizon explains more.
  Offer at the expected running share over λ*, storage units, days offered above €1:

| group | unit-days | over λ*30s | over λ*30o | over λ*90s |
|---|---|---|---|---|
| EDP | 14,301 | 0.95 | 0.96 | 0.90 |
| Endesa | 6,065 | 1.14 | 1.12 | 1.09 |
| Iberdrola | 9,619 | 1.21 | 1.22 | 1.12 |
| Naturgy | 5,105 | 1.40 | 1.47 | 1.35 |
| Movhera | 1,281 | 0.95 | 0.99 | 0.91 |

  (Different from §5.3 because days offered at or below €1 are left out here.)
- **The gap opened after 2021.** Over λ*30s: Iberdrola 1.13 (2019), 0.96 (2021), 1.29
  (2023), 1.62 (2025); Naturgy 1.01–1.03 (2019–2021), 1.87 (2022), 2.46 (2023), 1.39 (2025);
  Endesa 0.93–1.04 to 2022, 1.45–2.03 from 2023. EDP 0.81–1.00 throughout.

**Reading.** Uncertain water within the month does not lift the competitive water value
enough to matter. What remains between Iberdrola's, Naturgy's and Endesa's offers and
λ* — opened from 2022 — is either a planning horizon longer than 90 days (large
interannual reservoirs), the cascade's within-day constraints (§5.3), or holding water
back. Leg B (`rq-leg-b-levels.md` §5) finds the last does not move with the firm's
incentive X.

### 5.5 Net of bilateral contracts (2026-10-08)

`analysis/water_value_forward_check.py`, rows `net of contracts`. Much of Iberdrola's and
Endesa's hydro, and from mid-2022 almost all of Naturgy's (90–100% of UFMI, UFGC and UFTA
output), is delivered under bilateral contracts (PDBF role 4), outside the auction
(`rq-counterfactual-hydro.md` §2). §5.3 read the auction curve at the running share cf_s
of the volume offered, which assumes the auction offer is the unit's whole capacity and
its whole water. Net of contracts, the read point is the water left after the contracts
over what was offered.

Example: a unit expecting 100 MWh of water on a day sells 70 MWh bilaterally and offers
150 MWh in the auction. Its water for the auction is 30 MWh, so the curve is read at
30 / 150 = 20%. Water and contracts are pooled over the month (the cost is a 30-day
value, and contracts move volume between days); the daily version gives the same ratios
to within 0.03.

**The correction moves the read point in both directions.** Subtracting the contracts
lowers it. But Endesa and Naturgy offer only part of their capacity in the auction (Endesa's
Ebro unit, January 2020: 9% of its capacity-hours, the rest sold bilaterally or not
offered), so their water is a larger share of what they offer, and that raises it. Median
read point against cf_s: Iberdrola 0.07 against 0.19, Endesa 0.70 against 0.17, Naturgy 0.25
against 0.13, EDP 0.20 against 0.17. On some days the contracts alone take all the
expected water, and no read point exists: Iberdrola 29% of unit-days, Naturgy 31% (52–59%
from 2022), Endesa 15%. On those days the offers at cf_s are high (Iberdrola 1.37 × λ*,
Naturgy 1.93), consistent with offering water beyond the expected volume at a higher
value.

Offer over λ*30s, storage units, on the days both read points exist and are above €1:

| group | unit-days | at cf_s (§5.3) | net of contracts |
|---|---|---|---|
| EDP | 13,786 | 0.94 | 0.95 |
| Endesa | 4,900 | 1.13 | 1.35 |
| Iberdrola | 6,523 | 1.16 | 1.11 |
| Naturgy | 2,888 | 1.19 | 1.22 |
| Movhera | 1,279 | 0.95 | 0.98 |

By year, at cf_s → net: Iberdrola 1.48 → 1.35 (2023), 1.27 → 1.17 (2024), 1.21 → 1.07
(2025); Naturgy 1.60 → 1.62, 2.72 → 2.82, 1.38 → 1.43, 1.29 → 1.33 (2022–2025); Endesa
2.10 → 2.11, 1.87 → 1.88, 1.51 → 1.61 (2023–2025).

**Reading.**
- **The contracts explain part of Iberdrola's gap, not Naturgy's or Endesa's.** Of
  Iberdrola's 2025 ratio of 1.62 in §5.4, about 0.4 comes from days left out here, mostly
  the 33% of its days on which its contracts take all its expected water; on the remaining
  days the ratio falls from 1.21 to 1.07 once the contracts are subtracted. Naturgy's and
  Endesa's gaps from 2022 stay.
- **The §5.4 ratios mixed in the fully contracted days.** For Naturgy those are half of its
  days from 2022, so its 1.40 is partly the price of water it was not expected to have.
- Reading the expected water against declared capacity (`cab` max power) assumes the whole
  cascade is available. Declared outages explain little of what Endesa and Naturgy leave
  unoffered, and taking them out barely moves the ratios (§5.6); little of it is offered
  intraday (§5.7), held as reserve or used later (§5.8–5.9).

### 5.6 Is the unoffered capacity out of service? Mostly not (2026-10-08)

`analysis/hydro_unoffered_capacity.py`. For each Spanish hydro unit of the six groups and
each hour, 2019-01 → 2025-09: unoffered capacity = `cab` max power − MW offered in the
auction − MW delivered under bilateral contracts. Against it, the MW the unit's generator
groups declared unavailable in OMIE's `indisp` (group capacity minus the available MW
declared). `indisp` names generator groups by their codes in REE's register of physical
units, which links each to the OMIE unit offering it (CLAUDE.md, `indisp` trap).

Example: Endesa's Ebro unit declares 1,899 MW. In an hour it offers 150 MW and delivers
400 MW bilaterally, so 1,349 MW is unoffered. If 900 MW of its groups are declared out of
service, 900 MW of that is explained.

| group | unoffered, share of capacity | of which declared out of service | of which water or authority limits |
|---|---|---|---|
| Iberdrola | 0.18 | **0.96** | 0.14 |
| Endesa | 0.73 | 0.17 | 0.00 |
| Naturgy | 0.54 | 0.17 | 0.02 |
| EDP (Spain, `HCHI` only) | 0.65 | 0.05 | 0.00 |
| Repsol (`VIES`) | 0.37 | 0.29 | 0.03 |

On the 73% of days `indisp` holds a snapshot for, the explained shares differ by at most
0.03. By year the explained share is 0.10–0.20 for Endesa and 0.13–0.22 for Naturgy.

- **Iberdrola offers what it has.** What it leaves unoffered is almost exactly its
  declared outages, so the method finds outages where they are.
- **Endesa and Naturgy leave most of their capacity unoffered, and it is not out of
  service.** By unit: Endesa's Ebro 74% unoffered (20% explained), Guadalquivir 88% (3%);
  Naturgy's Miño 41% (24%), Tajo 84% (6%).
- **Neither is it specific to them**: EDP's one Spanish unit leaves 65% unoffered, 5%
  explained.
- **It hardly moves with the hour.** Unexplained unoffered capacity over capacity,
  2023–2025: Naturgy 0.41 at 20:00–22:00 against 0.45 overnight and at midday; Endesa
  0.54 against 0.70. Endesa puts somewhat more capacity in the evening peak, which fits a
  unit spreading limited water over the dearest hours by quantity rather than by price.
- **Taking the outages out barely changes §5.5.** Scaling each unit's expected water by
  its available share (an upper bound, since the historical capacity factor already
  contains average outages), same days: Endesa 1.37 → 1.31, Naturgy 1.21 → 1.21,
  Iberdrola 1.13 → 1.09 (Spanish units).

Groups never named in `indisp` count as available (Endesa's Ebro: 1,025 of 1,858 MW of its
groups appear in `indisp`).

### 5.7 Nor is it offered intraday (2026-10-08)

Same script. What is neither offered day-ahead, contracted nor declared out of service,
against the unit's sell offers in the intraday auction sessions: per hour, the most MW
offered in any one session (sessions re-offer the same capacity, so they are not added),
and the MW sold net over all sessions. An intraday offer may also be capacity offered
day-ahead that did not sell, so the share is bounded: the upper bound counts every
intraday offer against the unoffered capacity, the lower bound only what exceeds the
unsold day-ahead offer.

Example: a unit leaves 290 MW unexplained in an hour, and offered 420 MW day-ahead of which
150 MW sold. If it offers 300 MW in an intraday session, at most 290 MW and at least
300 − 270 = 30 MW of that is the unoffered capacity.

| group | unexplained unoffered, mean MW | offered intraday, share | sold intraday, at most |
|---|---|---|---|
| Endesa | 328 | 0.01–0.04 | 0.01 |
| Naturgy | 255 | 0.03–0.42 | 0.05 |
| EDP (Spain, `HCHI`) | 262 | 0.04–0.10 | 0.05 |
| Repsol | 51 | 0.17–0.48 | 0.11 |
| Iberdrola | 11 | — | — |

- **Endesa does not offer it intraday.** The upper bound is 0.01–0.13 by year (0.13 in 2021,
  0.01–0.02 from 2023) and at most 0.11 by unit. Over the sessions Endesa buys back slightly
  more hydro than it sells (net −3 MW an hour).
- **Naturgy's intraday offers are mostly its unsold day-ahead offer again.** The upper bound
  is 0.30–0.52 by year (Miño 0.74), the lower 0.02–0.05 in every year. It sells at most 5%.
- **So most of what Endesa and Naturgy leave unoffered is neither out of service nor offered
  intraday**: 80–83% of Endesa's unoffered capacity and 48–81% of Naturgy's.

*Corrected 2026-10-08.* The lower bounds first given here (Endesa 0.02, Naturgy 0.16, EDP
0.07, Repsol 0.42, and for Naturgy a fall from 0.25–0.33 to 0.03–0.05 after its contracts
began) counted each hour's day-ahead sales once per offer step: the step cache repeats the
unit-hour total on every step. Taken once, the day-ahead base schedule equals REE's own
(I90DIA26) to the MW on every sample day (§5.9). The upper bounds did not use it and stand.

Not tested: the continuous intraday market (trades between the auction sessions; OMIE's
`pibcic`, one month on disk). Reserves: §5.8.

### 5.8 Reserves cannot hold Endesa's; Naturgy's only if it held most of Spain's (2026-10-08)

A cascade unit can keep turbine capacity free for upward reserve without offering its
energy. Per-unit reserve allocations are in REE's I90DIA workbook (sheet I90DIA05), not
on disk (`continuous-intraday-data.md` §4). A bound needs only the system total: the
upward secondary regulation band REE allocated to the whole peninsula each hour (ESIOS
632, every technology and firm). If that is smaller than a group's unoffered capacity left
after outages and the intraday upper bound, reserves cannot explain the rest even if every
MW of the band came from that group's hydro.

Example: in an hour Endesa's units leave 1,800 MW unoffered that no outage or intraday
offer accounts for, and REE allocates 760 MW of upward band to the whole system. Reserves
can explain at most 760 MW, 42%.

| | left unexplained, mean MW | whole system's upward band, mean MW | band over what is left | hours the band covers it |
|---|---|---|---|---|
| Endesa | 1,789 | 758 | 0.42 (0.30–0.61 by year) | 7% |
| Naturgy | 442 | 759 | 1.72 (1.19–2.53) | 91% |
| Endesa + Naturgy | 2,206 | 759 | 0.34 (0.25–0.48) | 4% |

- **Reserves cannot explain most of Endesa's unoffered capacity.** Even if Endesa's hydro
  supplied all of Spain's upward secondary band, at least 58% would remain.
- **They could explain Naturgy's, but only if its three units held about 60% of the whole
  peninsula's upward band** on average, alongside every combined cycle and every other
  firm's hydro. Not ruled out without per-unit data.
- The additional upward reserve (ESIOS 627) was allocated in 602 hours, all between
  January and November 2019, and changes nothing. Tertiary regulation is energy offered
  from capacity already free, not capacity held back, so it is not counted.

**Test day, 2023-06-15 (REE's I90DIA workbook, sheet I90DIA05, upward band by unit).**
Summed over units the sheet equals ESIOS 632 in every hour (difference 0.0 MW), so it is
the same band. That day Endesa's units held 56 MW of upward band against about 2,400 MW
unoffered and unexplained (Ebro 42 MW against 1,201, 3%), and **Naturgy's held none**.
The band was mostly combined cycles; the 21 hydro units here held 21% of it, Iberdrola
most (Duero 76 MW). One day, so a sample of days is the next step, not a result.

### 5.9 REE's per-unit files: neither held as reserve nor used later (2026-10-08)

REE's I90DIA workbook (ESIOS archive 34) for the 15th of every month, 2019-01 → 2025-09:
81 days, about 450 MB (`fetch/fetch_esios_i90.py`; formats in CLAUDE.md). Per unit and
hour it gives the upward secondary band allocated (to 2024-11-15; by market participant
after it) and the schedule at each stage: the day-ahead base (PDBF), the final intraday
(PHFC, the auction sessions and continuous trading) and the final one after REE's
balancing and real-time processes (P48). So it shows what happened to the unoffered
capacity after the day-ahead market, continuous trading included.

Example: a unit leaves 1,200 MW unoffered that outages do not explain. If REE's files show
40 MW of upward band and its final schedule 20 MW above its day-ahead schedule, at most 60
MW of the 1,200, 5%, was held or used later. The rest was not used in any market.

Against the unoffered capacity outages do not explain (§5.6), sample days:

| group | unexplained, mean MW per unit-hour | held as upward band (71 days) | energy added after day-ahead | both (71 days) |
|---|---|---|---|---|
| Endesa | 349 | 0.02 | 0.01 | **0.02** |
| Naturgy | 258 | 0.00 | 0.07 | **0.07** |
| EDP (Spain, `HCHI`) | 265 | 0.04 | 0.05 | 0.08 |
| Repsol | 53 | 0.11 | 0.05 | 0.16 |
| Iberdrola | 7 | 0.29 | 0.08 | 0.36 |

Energy added after the day-ahead market splits into intraday (auctions and continuous)
and balancing: Endesa 0.01 and 0.00, Naturgy 0.05 and 0.02. The day-ahead base schedule in
REE's files equals ours (day-ahead sales plus bilateral contracts) to 0.0 MW on average.

- **Endesa: 0.02–0.04 in every year 2019–2024.** Its units held a mean 5 MW of upward band
  each.
- **Naturgy: 0.02–0.11 by year, almost all of it energy sold later**; its band share is
  0.00 in every year but 2024 (0.01).
- **From December 2024 the band is reported by market participant**, so only a firm-level
  bound is possible: Endesa's whole upward band, every technology included (277 MW), would
  cover at most 15% of its hydro's unexplained unoffered capacity (1,909 MW, group total);
  Naturgy's (93 MW) at most 12%, 17% with energy added later.
- **Put together**: outages explain 17% of what Endesa and Naturgy leave unoffered (§5.6);
  of the rest, reserves and every later market account for 2% (Endesa) and 7% (Naturgy).
  About 80% of their unoffered hydro capacity is neither out of service, nor held as
  reserve, nor used in any market after the day-ahead.

**Reading.** Unused turbine capacity is normal for storage hydro: a unit with water for a
fifth of the hours leaves its turbines idle most of the time. What these tests show is how
Endesa and Naturgy ration their water: by offering only part of their capacity, not by
offering all of it at a price. EDP's Spanish unit does the same; Iberdrola offers all it
has. Whether the water they hold back is water a price-taker would have used is what §5.5's
read point measures, and there the gap stays (Endesa 1.35, Naturgy 1.22). Limits: one day
a month; the 15th is never a DST day; the band after 2024-11 is not by unit.

## 6. What it enables

- **Leg B in levels**: λ̂ − λ* on the day's markup term, with an instrument.
- **The at-cost instrument on hydro** (`rq-step-estimator.md` §7): λ* is the cost point at
  which to evaluate X. Any function of what was known when offers close is a valid
  instrument, so λ* need only be close to the true cost to be strong, not exact.

### 5.10 Does the unoffered share follow the price incentive? (2026-11-05)

`analysis/hydro_unoffered_incentive.py`. **Rules written 2026-11-05 before the regressions
were run**; the panel had been built and only its sample sizes looked at.

**The question, with an example.** §5.6 – §5.9 left about 80% of Endesa's and Naturgy's
unoffered hydro capacity unexplained by outages, intraday sales, reserves or later use.
Take Endesa's Ebro unit at 20:00 on a Tuesday. Endesa is a net seller of 6,000 MW in the
auction and rivals offer 300 MW per €/MWh around the price, so its incentive is
X = 6,000 / 300 = €20/MWh: each MW of hydro it keeps out of the auction lifts the price on
all its other output. At 04:00 it is a net buyer, X is negative, and keeping hydro out
would raise the price it pays. If the unoffered capacity is a quantity-margin use of market
power, the share G/C (unoffered over capacity) is higher at 20:00 than at 04:00 and on
high-X days than on low-X days. If it is water- or contract-driven, G/C follows the
reservoir's fill and the bilateral position and X adds nothing once they are held fixed.

**Data.** Unit-hour panel of the four groups' Spanish storage hydro, 2019-01 → 2025-09:
16 units (EDP 1, Endesa 7, Iberdrola 5, Naturgy 3), 857,496 unit-hours on 24-period days
with a firm X (clean, price above €1, slope ≥ 5). G = max(C − O − B, 0) as in §5.6;
E = min(declared unavailable, G); R = G − E, so G/C = E/C + R/C and the coefficients add.
Repsol is left out: its unit has no MITECO series. Main sample: the 13 units with a MITECO
basin fill series (93% of capacity; JUCA, TEES and EBRERZ out).

**The incentive.** X̃ = (n − own storage hydro cleared in the auction) / slope, with n and
slope from `firm_x.parquet` (exposed basis), by hour, winsorised at its pooled 1st and 99th
percentile. The own-hydro sale is taken out because it is part of n and falls when more
capacity is left unoffered: with it in, X would be mechanically lower exactly when G/C is
higher. X as built (own hydro in) is run as the check and must come out lower than X̃. The
firms are mostly net buyers (mean X −4 to −13 €/MWh), so the test is on how far X is
negative or positive, not on its sign.

**Specifications.** Dependent variable G/C (also E/C and R/C). Weights C. Linear, fixed
effects absorbed by alternating projections. Standard errors clustered by ISO week.
Coefficients are per €1/MWh of X̃, in points of capacity (pp), and as the effect of one
within-fixed-effects standard deviation of X̃ ("per sd").

| | fixed effects | controls | sample |
|---|---|---|---|
| P1 | unit × month, hour of day, day of week | fill anomaly (D−2), cf_s, log C | main |
| P2 | as P1 | P1 + B/C and B/C a day earlier | main |
| P3 | unit × month, hour of sample (firms compared in the same hour) | as P2 | main, pooled only |
| P4 | as P2 | as P2 | days `indisp` holds a snapshot for |
| P5 | as P1 | cf_s, log C, B/C, B/C lagged (no fill) | all 16 units |

Each is run pooled and per firm (P3 pooled only: within one firm an hour effect would
absorb X̃). Checks, on P2: X̃ lagged one day (known at D−1), X̃ led one day (placebo), X as
built, no winsorising, leave-one-firm-out, unit × month-of-year-instead-of-sample months.
**Few firms**: four firms give no valid firm-clustered inference, so the pooled interval
treats the four as fixed and says only what holds for them; per-firm rows are reported
beside it and a count of positive firms is description, not a test.
**No instrument.** Reactor outages would shift n, but a trip also obliges the owner to
cover its bilateral contracts, partly from hydro, so the exclusion fails, and EDP has no
reactor. Realised X̃ is simultaneous with the offers through the price band; the
D−1 version is the predetermined check.

**What each story predicts.**

| | quantity-margin market power | water constraint | contract position |
|---|---|---|---|
| β on X̃ (G/C) | > 0, in P1, P2 and P3 | ≈ 0 once fill and cf_s are in | ≈ 0 once B/C is in |
| fill anomaly, cf_s | small next to X̃ | negative and large: fuller reservoir, less G | irrelevant |
| B/C | negative (mechanical) | irrelevant | G/C follows B/C and its lag |
| E/C against R/C | the increase is in R/C | R/C | R/C |
| lag of X̃ | positive, as the contemporaneous | 0 | 0 |
| lead of X̃ (placebo) | smaller than the contemporaneous | 0 | 0 |

**Pass (the unoffered share follows the incentive).** All of: (a) pooled P1, P2, P3 have
β > 0 with 95% intervals excluding zero; (b) in P2 at least three of four firms have a
positive point estimate and none a significantly negative one; (c) the D−1 X̃ has the
same sign and a significant positive coefficient, and the lead's coefficient is below
the contemporaneous one; (d) X as built has a lower β than X̃ (the direction of the
mechanical bias; if not, the correction did not do what it is for and nothing is read);
(e) the per-sd effect in P2 is at least 1 pp of capacity, otherwise the result is
"positive and economically small"; (f) R/C carries at least 80% of the G/C coefficient.
If E/C carries half or more, outage timing follows the incentive (maintenance scheduled
by price) and the pass is withdrawn.

**Fail for quantity market power.** P1 and P2 pooled have intervals whose per-sd upper end is
below 1 pp: an informative zero, read as water or contracts, with fill, cf_s and B/C
coefficients reported to say which. A significantly negative pooled β in P2 is read as the
incentive's contract-routing correlates (a firm that supplies its own retail bilaterally
buys less in the auction, raising n, while B takes capacity out of G), not withholding.

**Stop (the data cannot answer).** Any of: the lead's coefficient is at least the
contemporaneous one in P2 (a slow confound, not an hourly incentive); the per-sd interval
in P2 is wider than 4 pp; P1 and P3 have opposite signs or differ by more than their
combined standard errors; the share of X̃'s variance left after the fixed effects is under
0.1%. P1 positive but P2 not is reported as "does not survive the contract position", not
as a pass.

**What would change the reading.** A different sign for X as built than for X̃ in the way
the mechanical story says confirms the correction; the same size means the removal was too
small to matter. A pass concentrated in one firm is reported as that firm's.
Not tested: the incentive that was expected when offers closed (X̃ is realised); the
continuous intraday market; a water value that varies across the hours of a day.

*Addendum, written 2026-11-05 after the first run and before the run it describes.* The first
run (P1 – P5, below) used unit × month effects, which hold fixed everything that differs
between months, including the water state itself, and so test only the variation within a
month. The task that set this test asked for **unit and month effects** (additive), which
lets the incentive, the reservoir fill and cf_s vary across months. That is **P6**: unit,
month-of-sample, hour-of-day and day-of-week effects; controls as P2; main sample; pooled
and per firm; with the lag, lead and as-built checks. The same pass, fail and stop rules apply
to P6 as written for P2, with one addition: if P6 pooled and at least three of four firms
have β > 0 with intervals excluding zero and a per-sd effect of 1 pp or more, the answer
becomes a pass on the incentive across months (lead placebo applied); if P6 has the sign
and size of P2, the main reading stands; if it differs from P2 in sign with intervals
excluding zero in both, the within-month and across-month answers are reported as different
and nothing is pooled across them. Also added, descriptive: the share of the weighted
variance of G/C that lies within unit-months (what P1 – P5 can use).
**Post hoc, added after the first run**: P2f and P3f repeat P2 and P3 with the hour-of-day,
weekday and control coefficients specific to each firm, because the pooled P2 (positive) and
all four per-firm P2 (negative) disagree. Also, `logC` is dropped when a firm's capacity does
not change within a unit-month (it was numerically collinear for Endesa; the estimates
did not move).

*Addendum 2, written 2026-11-05 after the P6 run and before the run it describes.* The
example at the top of this section (20:00 against 04:00) is a difference across hours of
the day, and **hour-of-day effects remove it**: they take out the average intraday profile
of the incentive, and P1 – P6 use only how the incentive at a given hour differs from day
to day. **P7** keeps the profile: unit × month and day-of-week effects, no hour-of-day
effects, controls as P2, main sample, pooled and per firm. The rules for P2 apply. A
profile in G/C that has other causes (turbine availability by hour, ramping limits) would
load on X̃ here, so a P7 that differs from P2 in sign with intervals excluding zero in both
is reported as "the intraday profile and the day-to-day deviations answer differently",
and P7 alone is not a pass.

**Results (2026-11-05).** `outputs/tables/hydro_unoffered_incentive.csv` (estimates),
`_checks.csv`, `_controls.csv`. 635,717 unit-hours in P2 (353 week clusters); G/C averages
38% of capacity (EDP 65%, Endesa 73%, Iberdrola 19%, Naturgy 54%). **Only 5.3% of the
variance of G/C lies within a unit-month**: the unoffered share is mostly a slow level, and
P1 – P5 test whether the incentive moves it around that level.

Effect on G/C of **one within-fixed-effects standard deviation of X̃** (about 12 €/MWh;
Naturgy 8), in points of capacity, with 95% interval (week-clustered):

| | pooled | EDP | Iberdrola | Endesa | Naturgy |
|---|---|---|---|---|---|
| P1 unit × month, hour, weekday; fill, cf_s | −0.21 [−0.30, −0.12] | −1.08 [−1.31, −0.86] | −0.13 [−0.26, −0.01] | −0.77 [−0.94, −0.61] | −0.34 [−0.47, −0.20] |
| P2 + bilateral share | +0.15 [+0.05, +0.25] | −0.36 [−0.49, −0.24] | −0.03 [−0.16, +0.10] | −0.11 [−0.24, +0.02] | −0.28 [−0.41, −0.15] |
| P3 hour of sample (firms in the same hour) | +0.45 [+0.35, +0.55] | — | — | — | — |
| P4 P2 on days `indisp` covers | +0.03 [−0.09, +0.15] | −0.37 [−0.53, −0.22] | −0.10 [−0.27, +0.07] | −0.04 [−0.15, +0.06] | −0.22 [−0.38, −0.07] |
| P5 P2 on all 16 units, no fill | +0.16 [+0.07, +0.26] | −0.36 [−0.49, −0.24] | −0.02 [−0.14, +0.10] | −0.12 [−0.25, +0.01] | −0.28 [−0.41, −0.15] |
| P6 unit and month effects (additive) | +0.19 [+0.03, +0.36] | −0.36 [−0.49, −0.24] | +0.01 [−0.14, +0.15] | −0.08 [−0.21, +0.05] | −0.28 [−0.41, −0.15] |
| P7 as P2, no hour-of-day effects | +0.12 [+0.02, +0.22] | −0.26 [−0.37, −0.15] | −0.04 [−0.16, +0.09] | −0.15 [−0.29, −0.01] | −0.32 [−0.46, −0.19] |
| post hoc P2f, firm-specific nuisance | −0.09 [−0.17, +0.00] | | | | |
| post hoc P3f | +0.14 [+0.07, +0.22] | | | | |

**Rules, as written.**
- **Pass: no.** (a) fails, P1 is negative; (b) fails, no firm is positive in P2 and EDP and
  Naturgy are significantly negative; (e) fails, the P2 pooled effect is 0.15 pp per sd, not
  1 pp. (c) holds pooled (lag +0.16, lead +0.08), (d) holds (as built is lower, below), and
  (f) holds (R carries 106% of the pooled coefficient, E −6%).
- **Fail for quantity market power, as an informative zero: yes.** The upper end of the
  per-sd interval is 0.25 pp in P2 and below 0 in P1. Every pooled interval in the table
  ends below 0.55 pp. P6 and P7 have the sign and size of P2, so the main reading stands.
  The significantly negative pooled P2 does not arise (it is positive).
- **Stop on the pooled sign: yes.** P1 is −0.21 and P3 +0.45; P2 +0.15 and the firm-specific
  P2f −0.09. The pooled sign depends on how firms are compared (common against
  firm-specific hour and control effects; within against across firms) and is not read.
  The per-firm rows do not depend on that and are what the reading rests on.

**Other results.**
- **Within a firm the coefficient is zero or negative in every specification** (Iberdrola
  −0.13 to +0.01, never significantly positive; EDP −0.26 to −1.08; Endesa −0.77 to −0.04;
  Naturgy −0.22 to −0.34). The sign is opposite to the prediction.
- **The negative within-firm coefficients are not an hourly incentive.** Next day's X̃ has
  as large a coefficient as today's (EDP −0.34 against −0.36, Naturgy −0.23 against −0.28,
  Endesa −0.16 against −0.11), and yesterday's the same. They come from slow co-movement
  of the unoffered share with the firm's position over days, which the controls leave.
- **The correction for own hydro does what it is for.** X as built is lower than X̃ for
  Endesa (−0.42 against −0.11 per sd in P2), Naturgy (−0.35 against −0.28) and EDP (−0.39
  against −0.36); Iberdrola, with almost no unexplained unoffered capacity, is unchanged.
  Pooled it is hardly different (+0.15 against +0.15).
- **E and R.** Outages explain none of the movement: E/C is within ±0.05 pp per sd for every
  firm in P2 and P6 (Iberdrola's unoffered capacity is 98% outages by level, so its test
  has little R to move). In P6 pooled, E is −0.21 and R +0.41, a cross-firm composition
  effect that no single firm shows.
- **Water and contracts.** The bilateral share enters with −12 pp of G/C per unit of B/C
  (−100 would be the identity, G = C − O − B, if O did not adjust): −1.2 to −1.7 pp per sd
  pooled, −6.7 for EDP. cf_s is −0.5 pp per sd in P1 – P2 (not significant) and **−2.1 pp
  per sd in P6** (se 0.2), where it varies across months; the basin fill anomaly is
  about zero in every specification (−0.16 pp per sd in P6). So across months the unoffered
  share falls where the model expects more running hours, which is a water-use signal,
  and the fill itself adds nothing.
- **Leave one firm out** (P2): without Iberdrola −0.20, without Endesa +0.01, without EDP
  or Naturgy +0.16. Unit × calendar month and unit × year effects instead of unit × month
  (the check as run): +0.39 pooled, with E +0.19 and R +0.21, so half moves with outages.
- **Not winsorising:** +0.12 pooled, EDP −0.23, Naturgy −0.22; the signs do not change.

**Plain reading (5 lines).**
1. The share of hydro capacity Endesa, Naturgy and EDP leave unoffered does not rise with their incentive to raise the price: within each firm it is flat (Iberdrola) or slightly lower.
2. The largest effect any pooled specification allows is 0.55 pp of capacity per standard deviation of the incentive, against 38% unoffered on average; the pooled sign flips with how firms are compared, so it is not read.
3. The small negative within-firm links are as strong for tomorrow's incentive as today's, so they are slow co-movement and not hour-by-hour withholding.
4. 95% of the variation is between unit-months and is not explained by the incentive across months either (P6); cf_s, the expected running share, moves it (−2.1 pp per sd), the fill anomaly does not, and the bilateral share mostly moves it by identity.
5. This is a stop for "quantity market power explains the unexplained 80%": it is not found, and not rejected for a response too slow or too small to see here. Nor does the test show that water or contracts explain it.

**Limits.** X̃ is realised, not expected, and enters the price band it is read in; the lag
is the predetermined check and agrees. No instrument (reactor outages fail the exclusion
and EDP has none). Four firms, EDP one unit: the pooled interval is conditional on these
four and is not a population statement. Units without a MITECO fill series are in P5 only.
The 23- and 25-hour days are out. The first run's Endesa `logC` coefficient was numerically
collinear and is now dropped (the estimates for X̃ did not change).
