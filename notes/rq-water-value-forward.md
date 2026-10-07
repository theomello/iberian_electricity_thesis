# A competitive water value from forward prices

Run 2026-10-07. Script: `build/build_water_value_forward.py`. Output:
`outputs/tables/water_value_forward.parquet` (unit-day λ*), `forward_price_quantiles.parquet`
(the expected price distribution by zone, day and horizon). Framework spec §2.2, leg B.

**In one line.** A water value built only from forward prices, last year's hourly price
shape and each unit's usual capacity factor reproduces the water value EDP reveals in its
offers: for its four big storage cascades the medians agree within 6% (Cávado 102 against
98, Lima 96 against 99, Guadiana 96 against 102, Mondego 104 against 100 €/MWh), with
correlations of 0.81–0.91 over 2019 – May 2026. Iberdrola, Naturgy and Movhera offer well
above it.

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
  Portugal; ESIOS 623 or MITECO for Spain) are the next refinement.
- Forward risk premia move λ* with the forward.
- Unit contents change: EDP moved ~1,000 MW from ACAVADO to ALIMA in March 2024.

## 6. What it enables

- **Leg B in levels**: λ̂ − λ* on the day's markup term, with an instrument.
- **The at-cost instrument on hydro** (`rq-step-estimator.md` §7): λ* is the cost point at
  which to evaluate X. Any function of what was known when offers close is a valid
  instrument, so λ* need only be close to the true cost to be strong, not exact.
