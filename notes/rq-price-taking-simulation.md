# Price-taking simulation: is the negative β the estimator?

Written 2026-10-08. Code: `step_engine.py --sim SEED` (simulated offers, then the same
resampled clearing), `analysis/price_taking_simulation.py` (the estimates).
Tables: `outputs/tables/price_taking_simulation_{hydro,thermal}.csv`. Ledger and logs:
`.superpowers/sdd/2026-10-08-sim/`.

## 1. The idea, with an example

Before weighing something unknown, put a known weight on the scale. Here the known weight
is a set of offers whose β we wrote ourselves: every firm's hydro steps (gas and coal steps,
for thermal) are moved to cost plus random noise, so the firm ignores its stake in the price
and β = 0. Everything else is the real market: rivals' offers as offered, the same 40
resampled hours, the same at-cost instruments (Zb, Zc) and reactor-outage doses, which do
not depend on the firm's own offer prices. Then the estimator is run exactly as on the
actual offers. If it reads β ≈ 0, the actual estimates are about the firms; if it reads the
actual sign and size, they are about the estimator.

**The noise** (`step_engine.simulate`): cost + μ + δ + ε, where μ is the unit's own mean
gap (offer − cost) in the month, δ a day effect resampled from the unit's day means in the
month, ε a step deviation resampled from its steps less their day mean. So each unit's
simulated offers are as dispersed as its own and split the same way between days and steps,
but independent of the hour they land in. Within an hour the draws are sorted onto the
steps in their order (the ladder stays); flat unit-days stay flat. μ is the unit-month mean,
so only estimates with unit × month or finer effects are a clean null. Prices are not
bounded: holding them at the unit's lowest or highest offer would tie the gap to the cost
(a cap step's gap falls as λ* rises), a second mechanism. 13.6% of hydro and 15.3% of
thermal simulated prices fall outside the unit's own offers that month; dropping those rows
changes nothing (below).

Per-unit medians and standard deviations of the simulated gap match the offers' (January
2019: sd 29.2 both). Simulated hydro steps set the price in at least one draw in 7.0% of
cases against 11.5% for offers (thermal 6.0% against 6.4%): real offers follow the hour,
random ones do not.

## 2. Result: price-takers give the negative sign

Hydro, at-cost instrument (leg B, `rq-leg-b-levels.md` §5), seed 1:

| fixed effects / sample | simulated, β = 0 | actual |
|---|---|---|
| unit × month, Zb | **−0.14** [−0.18, −0.09] | −0.22 [−0.30, −0.15] |
| unit × month, Zc | −0.16 | −0.20 |
| unit × day, Zb | **−0.16** [−0.22, −0.09] | −0.37 [−0.52, −0.25] |
| unit only (not a clean null) | +0.03 | −0.01 |
| 2019 – 2021H1 | −0.08 | +0.14 |
| 2021H2 – 2023 | −0.12 | −0.25 |
| 2024 – 2025-09 | −0.14 | −0.16 |
| net sellers β⁺ / net buyers β⁻ | −0.09 / −0.20 | −0.35 / −0.02 |
| reactor outages, unit × month | −0.40 (F 14, set empty) | −0.26 [−0.72, 0.04] |
| simulated prices inside the unit's offers only | −0.16 | |
| least squares, unit × month | +0.36 | +0.32 |

Thermal, at-cost instrument (`rq-step-estimator.md` §7), seed 1:

| fixed effects / sample | simulated, β = 0 | actual |
|---|---|---|
| main (unit × month, fuel × hour) | **−0.26** [−0.33, −0.20] | −0.27 [−0.37, −0.18] |
| five firms | −0.25 | −0.25 |
| gas | −0.26 | −0.27 |
| own cost (Zc) | −0.21 | −0.23 |
| 2021H2 – 2023 | −0.27 | −0.29 |
| 2019 – 2021H1 | −0.21 | **−0.03** |
| unit × day | −0.11 | −0.08 |
| unit × day, 2019 – 2021H1 | −0.08 | **+0.12** |
| fuel × date + hour | **+0.27** | +0.10 |
| reactor outages (F 7) | −0.59 [−1.60, 0.04] | +0.07 [−0.68, 1.01] |

- **Thermal: the estimator reproduces the actual estimates almost exactly**, including the
  sign flip with fuel × date effects that `rq-step-estimator.md` §7 left open. The at-cost
  thermal estimates carry no information about conduct beyond what price-takers produce,
  except perhaps 2019 – 2021H1 (+0.2 above the null).
- **Hydro: most of the negative sign is the estimator.** Actual minus simulated is −0.09
  within months, −0.22 within days, +0.22 in 2019 – 2021H1, and −0.26 / +0.18 for net
  sellers / net buyers. These differences are not a corrected estimate: the size of the
  artefact depends on how the noise is spread across hours, which differs for real offers.
- **The reactor-outage instrument is affected too** (hydro −0.40 under the null).
- **Least squares is biased upward** (+0.36 hydro, +0.25 thermal), as the other owners'
  +0.51 already suggested (`rq-step-estimator.md` §3).

## 3. Why: a step enters only where the price reaches it

A price-taker offers at λ* plus noise. Its step enters the rows only in hours where some
draw's price reaches it. In a dear hour only its high steps get there; in a cheap hour only
its low ones. So among the kept steps the gap over λ* rises with how high the hour's prices
sit above λ*, for reasons that have nothing to do with the firm's stake. On 24 simulated
months, after unit × month, class × hour and class × position effects (weights as in the
estimator):

| correlation with (draws' mean price − λ*) | |
|---|---|
| kept steps' gap | +0.17 |
| Zb (the at-cost instrument) | −0.20 |
| X̃ | −0.20 |

That alone gives IV −0.15. With a slope per unit on (draws' mean price − λ*) as a control,
the same rows give +0.05. (That check took the draws' mean price from the actual curve,
which carries the firm's own offers; the correction below reads it with the firm at cost.)

## 4. What changes

- **The negative sign is no longer a fact to explain.** §6.1 of `rq-leg-b-levels.md` and
  §7.1 of `rq-step-estimator.md` (water, own zero-priced output, start-up cost) looked for
  causes of a sign the estimator produces by itself.
- **"Full market power rejected" probably survives** (the artefact is 0.1 – 0.3, the upper
  bounds were 0.12 – 0.26 below 1 by far), but every bound moves.
- Legs A and D used other estimators (within-day offers, signs of n) and are not covered by
  this check; leg D's forecast design is a candidate for the same test.

## 5. The correction: most of the artefact goes, the rule is not met

Control for the selection index, read where the firm's own offers cannot enter: the same
draws with the firm at cost (`step_engine.py --comp-price` → `(h)compcostprice_YYYYMM`),
P_rel = draws' mean price − the unit's cost, with a slope per unit; variants add P_rel² or
the draws' price spread, or let the slope change by year or month. The rule, fixed before any
actual estimate is read: the simplest control that brings the simulated β within ±0.03 of zero
with zero in the Anderson–Rubin set, for both seeds, within months and within days, hydro and
thermal. Only then is it run on the actual offers. Table:
`outputs/tables/price_taking_simulation_{hydro,thermal}_corrected.csv`.

Simulated β (true β = 0), seed 1 / seed 2:

| | none | level | level, spread | level, by year |
|---|---|---|---|---|
| hydro, unit × month | −0.14 / −0.18 | +0.07 / +0.02 | +0.06 / +0.01 | |
| hydro, unit × day | −0.16 / −0.16 | −0.06 / −0.06 | −0.05 / −0.04 | |
| thermal, unit × month | −0.26 / −0.21 | +0.02 / +0.06 | +0.04 / +0.08 | +0.02 / +0.06 |
| thermal, unit × day | −0.11 / −0.07 | −0.00 / +0.04 | +0.01 / +0.05 | −0.01 / +0.03 |
| thermal, 2019 – 2021H1 | −0.21 / −0.25 | −0.18 / −0.21 | −0.16 / −0.16 | −0.13 / −0.16 |
| thermal, fuel × date | +0.27 / +0.31 | +0.08 / +0.12 | +0.07 / +0.12 | +0.07 / +0.11 |
| hydro, β⁺ / β⁻ | | +0.16 / −0.06, +0.09 / −0.08 | | |

- **The controls remove most of the artefact**, from −0.14 … −0.26 to about ±0.06.
- **No control meets the rule**, so none was run on the actual offers. What is left is partly
  noise and partly not. Noise: the two seeds of the plain estimate differ by up to 0.05, and the
  standard errors are 0.03 – 0.05, so the ±0.03 tolerance was set below what one seed can show.
  Not noise: thermal 2019 – 2021H1 stays at −0.13 … −0.21 under every control in both seeds, and
  fuel × date at +0.07 … +0.12; hydro within days stays at −0.04 … −0.06; the net-seller /
  net-buyer split reads β⁺ > 0 and β⁻ < 0 under the null.
- Slopes that change by year or month change nothing, so the remainder is not the slope
  drifting with the price level; P_rel misses part of the selection.

**Reading rule for the actual offers, fixed 2026-10-08 before they were run** (the ±0.03 rule
was dropped by decision, not met). Control: `level` (one slope per unit on P_rel). For each
specification the *null band* is [min, max] of the two simulated `level` estimates. The
actual offers differ from price-takers only if the actual Anderson–Rubin set does not touch
the null band; actual minus the mean of the two simulated estimates is shown as an indicative
point, not an estimate. The test of full market power (β = 1) is read from the actual AR set
as before. The `none` rows of the actual run must reproduce the published estimates.
Known weakness, found before the actual run: two seeds make a narrow band. Seed 1 read as if
it were actual against seed 2 already "differs" on fuel × date (+0.077 [0.04, 0.11] against
+0.122). A "differs" on a precise specification is weak until more seeds widen the band.

## 6. The actual offers under the reading rule (2026-10-08)

`price_taking_simulation.py --corrected --seeds 0 --controls none level`; the `none` rows
reproduce the published estimates exactly (hydro −0.224, −0.374, β⁺ −0.354 / β⁻ −0.021;
thermal −0.272, −0.081, +0.103). Table: `outputs/tables/price_taking_simulation_{kind}_reading.csv`.

| specification, control `level` | actual | AR set | null band | differs |
|---|---|---|---|---|
| hydro, unit × month | +0.07 | [−0.03, 0.17] | +0.02 … +0.07 | no |
| hydro, unit × day | −0.23 | [−0.45, −0.06] | −0.06 … −0.06 | no (touches) |
| hydro, reactor outages | +0.13 | [−0.39, 0.49] | −0.20 … +0.28 | no |
| hydro, 2019 – 2021H1 | **+0.31** | [0.17, 0.46] | −0.06 … 0.00 | **yes** |
| hydro, 2021H2 – 2023 | +0.01 | [−0.12, 0.13] | +0.02 … +0.08 | no |
| hydro, 2024 – 2025-09 | **+0.20** | [0.10, 0.34] | −0.02 … +0.04 | **yes** |
| thermal, unit × month | +0.01 | [−0.08, 0.10] | +0.02 … +0.06 | no |
| thermal, unit × day | +0.09 | [−0.03, 0.20] | −0.00 … +0.04 | no |
| thermal, fuel × date | −0.01 | [−0.07, 0.04] | +0.08 … +0.12 | yes (weak, see §5) |
| thermal, 2019 – 2021H1 | −0.06 | [−0.16, 0.05] | −0.21 … −0.18 | **yes** |
| thermal, 2021H2 – 2023 | −0.03 | [−0.13, 0.06] | +0.03 … +0.07 | no |
| thermal, five firms | −0.03 | [−0.12, 0.06] | +0.01 … +0.02 | no |
| thermal, reactor outages (F 1–10) | +0.60 | [−0.36, 2.99] | −0.50 … −0.30 | no |

Hydro net sellers / net buyers (no AR set; indicative): actual β⁺ +0.02, β⁻ +0.14 against
null β⁺ +0.09 … +0.16, β⁻ −0.08 … −0.06.

- **Pooled, the firms are indistinguishable from price-takers**, hydro and thermal, within
  months and within days. The negative sign of §2 was the estimator.
- **Hydro departs in 2019 – 2021H1** (actual above the null by about +0.34; before the
  correction too, §2: +0.22) **and in 2024 – 2025** (about +0.20). The 2021H2 – 2023 crisis does
  not. Thermal 2019 – 2021H1 looked like a departure (+0.13) on two seeds but not on three (below).
- **Full market power (β = 1) is rejected in every specification** with a strong instrument
  (AR p(1) < 1e-25); the reactor-outage specifications cannot reject it.
- Two seeds only: the bands are narrow, and thermal 2019 – 2021H1 is where the correction
  works worst (null −0.18 … −0.21). Option 2 (more seeds) would test whether the departures
  survive a wider band.

**A third seed on the two doubtful periods (2026-10-08)**: seed 3 simulated only for thermal
2019-01 → 2021-06 and hydro 2024-01 → 2025-09 (`price_taking_sim.sh KIND 3 FROM TO`;
`price_taking_simulation.py --corrected --seeds 3 --controls none level --only …`).

| | seeds 1, 2, 3 (level) | null band | actual | differs | gap ÷ seed sd |
|---|---|---|---|---|---|
| hydro 2024 – 2025-09 | +0.037, −0.021, +0.039 | −0.02 … +0.04 | +0.20 [0.10, 0.34] | **yes** | 5.4 |
| thermal 2019 – 2021H1 | −0.175, −0.206, −0.141 | −0.21 … −0.14 | −0.06 [−0.16, 0.05] | **no** (now touches) | 3.6 |
| hydro 2019 – 2021H1 (two seeds) | −0.058, +0.004 | −0.06 … 0.00 | +0.31 [0.17, 0.46] | **yes** | 7.8 |

So the thermal departure does not survive the rule: thermal offers are indistinguishable from
price-takers in every period. Both hydro departures stand. More seeds can only widen a band, so
they cannot bring the thermal departure back; for the hydro ones the AR sets clear the band by
0.06 (2024 – 25) and 0.17 (2019 – 21H1), about 2 and 4 seed standard deviations, so further seeds
are unlikely to change either verdict (for 2024 – 25, three more seeds would each have to exceed
the band by 2.4 sd; chance about 2%).

Computation: the unit slopes are absorbed with the unit × month (day) effect
(`step_estimator.slope_step`, exact) with Irons–Tuck acceleration (`accelerated`); on 27,550
rows the IV estimate equals the one with explicit unit × P_rel columns to 12 digits.
