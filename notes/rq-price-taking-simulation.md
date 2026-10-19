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

## 7. Are they price-takers? An equivalence test (δ = 0.1, fixed 2026-10-08)

Not rejecting β = 0 does not show β = 0. The test of price-taking fixes in advance the largest
β still called price-taking, δ = 0.1 (a firm adds at most a tenth of the markup a Cournot firm
facing the same residual demand would add: €0.30 if that markup were €3/MWh), and asks whether
β is below it. One-sided: market power means β > 0, and no conduct in the model gives β < 0.
The set for β allows any bias in the null band, [AR low − null max, AR high − null min];
price-taking is accepted when its upper end is below 0.1 (the 95% set's upper end makes this
a 2.5% test). Columns `beta_lo_adj`, `beta_hi_adj`, `price_taking_within_delta` in
`price_taking_simulation_{kind}_reading.csv`.

| | β, bias allowed for | price-taking (β < 0.1) |
|---|---|---|
| thermal, pooled | −0.14 … +0.08 | **accepted** |
| thermal, five firms | −0.14 … +0.05 | **accepted** |
| thermal, 2021H2 – 2023 | −0.20 … +0.04 | **accepted** |
| thermal, fuel × date | −0.19 … −0.04 | accepted (weak specification) |
| thermal, unit × day | −0.07 … +0.20 | not shown |
| thermal, 2019 – 2021H1 | −0.02 … +0.26 | not shown |
| hydro, unit × month | −0.10 … +0.15 | not shown |
| hydro, unit × day | −0.39 … +0.00 | accepted (but the actual sits below price-takers) |
| hydro, 2021H2 – 2023 | −0.20 … +0.11 | not shown (just) |
| hydro, 2019 – 2021H1 | +0.17 … +0.52 | not shown; β = 0 rejected, β above 0.1 |
| hydro, 2024 – 2025-09 | +0.06 … +0.36 | not shown; β = 0 rejected |

Thermal pooled over the window is price-taking to within a tenth of the Cournot markup; within
days and in 2019 – 2021H1 the data cannot say. This tests only the prices of offered steps: a
firm could still withhold quantity, which a separate test would have to look at.

## 8. Which firms carry the hydro departures (2026-10-08)

**Firm by firm the estimator identifies nothing.** Zb is one value per firm and hour (the
firm's X̃ at a common cost point), and the estimator removes class × hour effects; inside one
firm's sample those effects absorb Zb entirely (first-stage F 0.0 for every firm, actual and
simulated). So in the pooled estimate β comes from comparing firms in the same hour: when one
firm has more at stake than another in that hour, does it price its water further above λ*,
relative to its own month? Two consequences: a water-value error common to all firms (the
30- against 90-day horizon) cancels in the hour effects, and only a firm-specific error that
moves with a firm's relative stake can make a spurious β.

Instead, leave one firm out: the pooled specification and the two departing periods without
each of EDP, Endesa, Iberdrola, Movhera, Naturgy and Repsol in turn, against the same
simulated bands (`price_taking_simulation.py --kind hydro --firms`;
`price_taking_simulation_hydro_without_firm{,_reading}.csv`).

Actual β (control `level`) and the price-taker band from the same sample without that firm:

| without | 2019 – 2021H1 | band | 2024 – 2025-09 | band | pooled | band |
|---|---|---|---|---|---|---|
| nobody (§6) | **+0.31** [0.17, 0.46] | −0.06 … 0.00 | **+0.20** [0.10, 0.34] | −0.02 … +0.04 | +0.07 | +0.02 … +0.07 |
| EDP | **+0.20** [0.10, 0.31] | −0.03 … +0.03 | **+0.25** [0.11, 0.41] | +0.03 … +0.08 | +0.04 | 0.00 … +0.07 |
| Endesa | **+0.40** [0.23, 0.58] | −0.06 … +0.03 | +0.15 [0.02, 0.29] | −0.03 … +0.03 | +0.08 | +0.02 … +0.07 |
| Iberdrola | **+0.02** [−0.10, 0.13] | −0.18 … −0.12 | +0.12 [−0.02, 0.26] | −0.10 … +0.08 | +0.06 | −0.01 … +0.06 |
| Movhera | **+0.31** [0.17, 0.46] | −0.06 … 0.00 | **+0.21** [0.11, 0.34] | −0.02 … 0.00 | +0.11 | +0.02 … +0.07 |
| Naturgy | **+0.37** [0.20, 0.54] | −0.04 … +0.04 | **+0.23** [0.12, 0.37] | −0.02 … +0.04 | +0.08 | +0.03 … +0.07 |
| Repsol | **+0.38** [0.20, 0.57] | −0.06 … +0.02 | **+0.19** [0.08, 0.34] | −0.03 … +0.06 | +0.03 | +0.01 … +0.07 |

Bold: the AR set misses the band. (Movhera has no rows before its 2022 purchase, so 2019 – 2021H1
without it is the full sample.)

- **2019 – 2021H1 survives every leave-out.** Iberdrola carries about half of it: without it the
  gap to price-takers falls from +0.34 to +0.16 (the band moves down too) and only just clears it.
- **2024 – 2025 rests on Iberdrola and Endesa together**: without either the estimate falls to
  +0.12 – 0.15 and its set touches the band; without any other firm it stands.
- **Pooled, no single firm changes the reading.**
- Iberdrola and Endesa are also the firms whose offers sit furthest above λ* in level (§5.5 of
  `rq-water-value-forward.md`: 1.11 and 1.35 at the expected running share, net of contracts),
  so a firm-specific water value is the alternative to rule out next. §9 does: it is not it.

Computation: the unit slopes are absorbed with the unit × month (day) effect
(`step_estimator.slope_step`, exact) with Irons–Tuck acceleration (`accelerated`); on 27,550
rows the IV estimate equals the one with explicit unit × P_rel columns to 12 digits.

## 9. A firm-specific water value does not make the departures (2026-10-08)

**The test.** Plant the alternative in the simulation and see whether the estimator turns it
into a positive β. The simulated price-takers value water at m × λ*30s, with m the firm's
offers over λ* at the expected running share, net of contracts (§5.5 of
`rq-water-value-forward.md`): EDP 0.95, Iberdrola 1.11, Naturgy 1.22, Endesa 1.35, Movhera
0.93 (gross); every other firm 1. The estimator still takes λ* as the cost, so it mistakes the
firm's own water value for a markup. Example: on a day with λ* at €60, Endesa's water is worth
€81, and its price-taking offer of €81 reads as €21 above cost.

Everything else is seed 1 (same random draws), so planted minus plain is the effect of the water
value alone. Check on 202401: firms with m = 1 get identical offers; for the others the offers
differ by a mean of about 0 (the unit-month mean gap is matched to the offers, as before) and an
sd of €14.4 (Endesa), 6.7 (Naturgy), 3.9 (Iberdrola), 1.2 (Movhera), 1.0 (EDP): a firm with
m > 1 now moves its offers m times as much as λ* from day to day.
(`step_engine.py --sim 1 --sim-scale` → `hsimw1_*`; `price_taking_sim.sh` with `SCALE=1`;
`price_taking_simulation.py --kind hydro --planted --seeds 1` →
`price_taking_simulation_hydro_planted.csv`.)

β, unit × month, control `level`:

| | 2019 – 2021H1 | 2024 – 2025-09 |
|---|---|---|
| actual offers | **+0.314** [0.17, 0.46] | **+0.203** [0.10, 0.34] |
| price-takers at λ* (seeds 1, 2, 3) | −0.058, +0.004 | +0.037, −0.021, +0.039 |
| price-takers at m × λ* (seed 1's draws) | −0.071 [−0.16, 0.01] | −0.012 [−0.09, 0.08] |
| planted minus plain, same draws | −0.013 | −0.049 |

Without the control the planted β is −0.086 (plain −0.080) and −0.171 (plain −0.143).

**The planted water value moves β by −0.01 and −0.05: the wrong sign, and small against
departures of +0.3 and +0.2.** So the firm water values the offers show, held as a fixed multiple
of λ*, explain none of the departures. The reason is in §8. The level of a firm's water value
within a month goes into its unit × month effect. What is left is that its offers move more
with λ* from day to day, and that is the same for all of the firm's hours. β compares firms within
the hour, so it reads only a gap that rises with the firm's stake against its rivals in that hour.

Still not excluded: a firm-specific error that changes with the hour or with the firm's own
stake, for example a firm that saves water for the evening hours in which it also has more at
stake. The 90-day horizon error is common to all firms and cancels in the hour effects (§8);
reservoir bounds are untested.

## 10. The departures hold within each part of the day (2026-10-08)

**The test.** The same three specifications within each six-hour block of the Madrid clock
(hour the period starts: 00–05, 06–11, 12–17, 18–23; blocks fixed before the split was read),
actual offers against seeds 1 and 2 (and 3 on 2024 – 25), control `level`
(`price_taking_simulation.py --kind hydro --hours`; `price_taking_simulation_hydro_by_hour{,_reading}.csv`).
Within a block the unit × month effect is the unit's own mean over that block's hours that
month. So if a firm keeps water for the evening and values it more there, that premium is a
constant inside the evening block and goes into the effect. Rule, fixed before the run: if the
departure holds within blocks, such a water value is ruled out too; if it vanishes in every
block, it came from differences between blocks, which a water value by block and market power
by block would both produce.

Actual β and the price-taker band (seeds' min … max), unit × month:

| hours | 2019 – 2021H1 | band | 2024 – 2025-09 | band | pooled | band |
|---|---|---|---|---|---|---|
| 00–05 | **+0.56** [0.20, 0.89] | −0.17 … +0.03 | +0.41 [0.14, 0.91] | +0.15 … +0.24 | +0.20 [0.00, 0.40] | +0.07 … +0.15 |
| 06–11 | **+0.27** [0.01, 0.56] | −0.08 … −0.06 | **+0.20** [0.10, 0.31] | 0.00 … +0.08 | +0.11 [0.00, 0.21] | +0.06 … +0.07 |
| 12–17 | +0.48 [−0.03, 1.01] | −0.19 … −0.03 | +0.33 [0.16, 0.53] | −0.07 … +0.18 | +0.22 [0.06, 0.38] | +0.04 … +0.19 |
| 18–23 | **+0.40** [0.13, 0.68] | −0.19 … +0.02 | **+0.21** [0.07, 0.36] | −0.02 … +0.01 | +0.05 [−0.10, 0.17] | −0.05 … +0.01 |
| whole day (§6) | **+0.31** [0.17, 0.46] | −0.06 … 0.00 | **+0.20** [0.10, 0.34] | −0.02 … +0.04 | +0.07 [−0.03, 0.17] | +0.02 … +0.07 |

Bold: the AR set misses the band. Actual minus the band's mean: 2019 – 2021H1 +0.63, +0.34,
+0.59, +0.48 by block against +0.34 over the whole day; 2024 – 2025 +0.22, +0.17, +0.27, +0.21
against +0.19.

- **The departures do not come from differences between blocks.** Inside every block the gap
  to price-takers is as large as over the whole day, or larger. By the rule, a firm water value
  that differs between parts of the day and is steady over the month is ruled out as well.
- **2019 – 2021H1 differs in three blocks.** At midday the set is wide (0 just inside), but the
  estimate is as far above its band as the others.
- **2024 – 2025 differs in the morning and the evening**, the blocks either side of the solar
  hours. At night and at midday it does not: fewer rows (14k at midday, where hydro rarely sets
  the price; first-stage F 14 at night), and at night the price-takers themselves give
  +0.15 … +0.24.
- **Pooled over the window no block differs**, as over the whole day.
- These are eight tests in the two periods; the reading rests on the pattern (every estimate
  above its band), not on any one of them. β = 1 is rejected in every block but 2019 – 2021H1
  at midday.

**What is left after §8 – §10.** The departures sit in Iberdrola and Endesa (2024 – 25) and
mostly Iberdrola (2019 – 21H1); they are not a water value that is a fixed multiple of λ*, nor a
fixed premium in some hours. What would still produce them is a firm-specific water value that
moves within the month with the firm's own stake (a constraint that binds on the same days the
firm has much at stake), or reservoir bounds. Short of that, the data fit firms that price their
water further above λ* when they have more at stake, in these two periods, at a fraction of the
Cournot markup.

## 11. Reservoir bounds: ruled out for 2019 – 2021H1, open for 2024 – 2025 (2026-10-09)

**The test.** λ* moves with the fill but not with its bounds: a full reservoir must spill and an
empty one must ration, so near a bound a price-taker's water value can leave λ*. Only units with
a fill series (MITECO basin for Spain, SNIRH own reservoirs for Portugal; 20 units, 72% of the
price-setting rows). A unit-day is near a bound when its fill is in the unit's own bottom or top
10% over 2019-01 → 2025-09, read from the water-value table so actual and simulated rows split
alike (`price_taking_simulation.py --kind hydro --bounds`;
`price_taking_simulation_hydro_by_fill{,_reading}.csv`). Rule, fixed before the run: if the
departures hold on interior days, the bounds are ruled out; if they appear only near the bounds,
the bounds explain them. Interior days are compared with all days of the same units, so leaving
out the units without a fill series is not read as a bound effect.

| days | 2019 – 2021H1 | band | 2024 – 2025-09 | band | pooled | band |
|---|---|---|---|---|---|---|
| with a fill series | **+0.44** [0.23, 0.65] | −0.08 … +0.04 | +0.26 [0.05, 0.49] | −0.04 … +0.11 | +0.09 | +0.02 … +0.10 |
| interior | **+0.45** [0.23, 0.67] | −0.08 … +0.06 | +0.09 [−0.11, 0.27] | −0.15 … +0.06 | +0.11 | −0.01 … +0.10 |
| near a bound | **+0.35** [0.06, 0.80] | −0.32 … −0.22 | **+0.67** [0.24, 1.19] | +0.06 … +0.23 | **+0.39** [0.13, 0.73] | +0.01 … +0.09 |

Near-bound days are mostly near full: 2024 – 2025, 19.6k of 20.4k rows. First-stage F near a
bound is 13 – 44 (one seed 5 in 2019 – 2021H1), against 78 – 330 elsewhere.

**Who the fill series cover.** 2019 – 2021H1: EDP 100% of its rows, Naturgy 86%, Iberdrola 61%,
Endesa 39%, Repsol 0. 2024 – 2025: EDP 99%, Movhera 100%, Naturgy 64%, Iberdrola 38%,
**Endesa 20%**, Repsol 0. Near-full rows in 2024 – 25 are EDP's ACAVADO, ALIMA, GUADIA, MONDEGO,
TEMON, ADOURO, Iberdrola's DUER, TAJO, SIL and Movhera's DOUSUP.

- **2019 – 2021H1: bounds ruled out.** On interior days the departure is as large as on all days
  of the same units (+0.45 against +0.44), and the sample covers most of Iberdrola, the firm
  carrying half of it (§8).
- **2024 – 2025: not settled.** The fill series miss most of Iberdrola's rows and almost all of
  Endesa's, the two firms the departure rests on (§8), so the test hardly reaches them. On the
  units it does reach, the departure is not clear to begin with (+0.26, the set touches the
  band); interior days give +0.09, inside the band, and near-full days +0.67, above it. Interior
  against near-full differ by 0.58, about 2.4 standard errors. The rows the series miss are
  mostly pumped storage, which no basin series can reach (§13).
- Not tested, only reasoned: a spill bound makes a price-taker offer below λ* on wet days, when its
  output and so its stake are high, which pushes β down rather than up. So the near-full excess
  need not be the bound; a firm with plenty of water and much at stake has the most room to
  price above λ*.

## 12. The departures in €/MWh (2026-10-09)

**The idea, with an example.** In the model a step's markup over its water value is β·X̃, where
X̃ = n / |RD′| is the markup a Cournot firm would add (€/MWh). Say Iberdrola sells a net 500 MW
in an hour and rivals add 100 MW per €1 of price: X̃ = €5. With β = 0.34 it prices that step
€1.70 above where a price-taker would. If it were a net buyer of 500 MW, it would price €1.70
below.

**Method** (`price_taking_simulation.py --kind hydro --size`; `price_taking_simulation_hydro_size.csv`).
β is the bias-adjusted estimate of each departing period: actual minus the price-takers' mean,
with the range [AR low − null max, AR high − null min] (§7): **2019 – 2021H1 0.34 [0.17, 0.52],
2024 – 2025-09 0.18 [0.06, 0.36]**. The rows and weights are the estimate's own: each
price-setting step weighted by the draws in which it sets the price. Price effect: per hour,
Σ over a firm's steps of (share of draws it sets the price) × β·X̃, averaged over every hour of
the period, 0 where the firm's hydro never sets it. That is an upper bound: a step priced €1
higher raises the price by €1 only if no rival step lies within €1 of it. It counts only the part
of the markup that rises with the firm's stake; the level within each month is in the unit ×
month effect and is not counted.

Per price-setting step (weighted by the draws in which it sets the price):

| | net seller | X̃ when net seller: mean (median, p90) | markup when net seller | markdown when net buyer |
|---|---|---|---|---|
| **2019 – 2021H1**, all firms | 50% | €3.7 (2.2, 8.2) | **€1.26** [0.61, 1.91] | −€1.16 |
| Iberdrola | 60% | €5.1 (3.1, 11.6) | €1.74 [0.85, 2.64] | −€0.74 |
| EDP | 54% | €3.6 (2.4, 7.5) | €1.23 [0.60, 1.87] | −€1.19 |
| Endesa | 0.2% | — | — | −€1.80 |
| **2024 – 2025-09**, all firms | 52% | €12.1 (6.8, 29.1) | **€2.24** [0.74, 4.38] | −€1.83 |
| Iberdrola | 70% | €16.3 (11.2, 35.6) | €3.01 [0.99, 5.89] | −€1.75 |
| EDP | 40% | €11.5 (6.0, 28.0) | €2.12 [0.70, 4.15] | −€1.75 |
| Endesa | 0.5% | — | — | −€3.06 |

Effect on the market price, every hour of the period counted (upper bound):

| | share of hours the firm's hydro sets the price | 2019 – 2021H1 | share | 2024 – 2025-09 |
|---|---|---|---|---|
| all firms | 37% | **+€0.01** [0.01, 0.02] | 35% | **+€0.10** [0.03, 0.20] |
| Iberdrola | 9% | +€0.07 | 13% | +€0.20 [0.07, 0.40] |
| Endesa | 4% | −€0.07 | 3% | −€0.09 |
| EDP | 19% | +€0.02 | 12% | −€0.03 |

- **On the steps, the departure is €1 – 3/MWh**: about €1.3 when a firm is a net seller in
  2019 – 2021H1 and €2.2 in 2024 – 2025, Iberdrola €1.7 and €3.0. X̃ is three times larger in
  2024 – 2025 (larger net positions, or rivals adding fewer MW per € around the price; not
  separated here), so a smaller β gives a larger markup.
- **Endesa's hydro sets the price almost only when Endesa is a net buyer** (its retail demand
  exceeds what it sells in the auction), so its part is a markdown: €1.8 and €3.1 below where a
  price-taker would offer. A net buyer gains from a lower price.
- **On the market price it is cents.** Upper bound +€0.01/MWh in 2019 – 2021H1 and +€0.10 in
  2024 – 2025 (at most €0.20). Three reasons: these steps set the price in about a third of the
  hours; when they do, the firm is a net buyer about half the time and marks down; and Endesa's
  markdowns offset part of Iberdrola's markups.
- **For scale**: offering all hydro at λ* with the same water lowers the price by €1.03 in 2024
  and €2.17 in 2025 (`rq-counterfactual-hydro.md`). The part that rises with a firm's stake is
  a tenth of that or less. Most of the gap between hydro offers and λ* is in the level (when the
  water is offered), not in a markup that follows the stake. The two numbers come from different
  methods (draws here, re-clearing the actual hours there), so compare their size only.

## 13. Pumped against conventional storage (2026-10-09)

**Why not the basin link.** §11 left 2024 – 2025 open because the fill series cover little of
Iberdrola and Endesa. The rows they miss are mostly pumped storage: Iberdrola's La Muela (`MUEL`,
19.7k rows in 2024 – 25) and Tâmega (`TAMEGA`, 13.2k; Gouvães, pumped, is about 880 of its
1,158 MW), Endesa's Moralets, Sallente, Tajo de la Encantada and Guillena (8.9k together), about
60% of Iberdrola's rows and 80% of Endesa's. A basin's fill says nothing about a pumped plant,
whose bound is its own upper reservoir, filled and emptied within the day or week; no public
series gives that per plant (MITECO and ESIOS are by basin or national, SNIRH has only month-end
volumes for Tâmega). So instead: does the departure come from pumped storage, where λ* is an
arbitrage value and the weakest benchmark?

**The test.** The same three specifications on pumped and on conventional storage
(`price_taking_simulation.py --kind hydro --pumped`; `price_taking_simulation_hydro_by_kind{,_reading}.csv`).
Main: Tâmega counted as pumped (its class moved with it, so that its steps meet the other pumped
units' in the class × hour effects); check: the classes as coded, Tâmega conventional. Rule,
fixed before the run: if the departure appears only in pumped storage, it is a pumped-storage
finding; if also in conventional storage, pumped storage does not explain it. Pumped storage
has 5 firms, conventional 9 – 11.

| | 2019 – 2021H1 | band | 2024 – 2025-09 | band |
|---|---|---|---|---|
| pumped, Tâmega in | −0.02 [−0.29, 0.24] | −0.22 … +0.29 | **+0.19** [0.01, 0.39] | −0.22 … −0.11 |
| conventional, Tâmega out | **+0.36** [0.19, 0.54] | −0.09 … +0.03 | +0.25 [0.07, 0.46] | −0.04 … +0.10 |
| pumped, as coded | (same: Tâmega opened in 2022) | | +0.25 [0.07, 0.44] | −0.08 … +0.11 |
| conventional, as coded | | | +0.18 [0.04, 0.34] | −0.05 … +0.07 |
| all (§6) | **+0.31** [0.17, 0.46] | −0.06 … 0.00 | **+0.20** [0.10, 0.34] | −0.02 … +0.04 |

Actual minus the band's mean, 2024 – 2025: pumped +0.37 and conventional +0.20 (main), +0.23 and
+0.16 (as coded).

- **2019 – 2021H1 is conventional storage.** +0.36 there, clear of its band; pumped storage
  gives nothing (−0.02, with a band so wide, −0.22 … +0.29, that it could not show anything).
- **2024 – 2025 is in both kinds, and in neither alone clearly.** The gap to price-takers is
  positive in all four halves (+0.16 to +0.37); only pumped storage with Tâmega clears its band,
  the other three sets touch theirs. Splitting halves the rows and the sets widen (standard
  errors 0.075 – 0.10 against 0.062). So pumped storage is not needed for the estimate, but the
  conventional part alone is not significant either.

**Where §6 – §13 leave the two departures.**
- **2019 – 2021H1 is robust.** It survives leaving out any one firm (§8), a firm water value
  (§9), every part of the day (§10), the reservoir bounds (§11, interior days) and pumped storage
  (§13, it is in conventional storage). About half of it is Iberdrola. On the steps it is
  about €1.3/MWh when a firm is a net seller; on the market price about a cent (§12).
- **2024 – 2025 is fragile.** It rests on Iberdrola and Endesa together (§8), sits in the
  morning and evening (§10), on near-full days where the fill series reach (§11), and spreads
  over pumped and conventional storage without being clear in either (§13). Its bounds cannot
  be tested for the pumped part. On the steps €2.2/MWh, on the price at most €0.10 – 0.20 (§12).
