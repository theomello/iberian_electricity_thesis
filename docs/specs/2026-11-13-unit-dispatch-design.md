# Unit-level dispatch logit and the fuel-switching elasticity it implies (pre-registration)

**Status: pre-registered 2026-11-13 (rules U1-U7 confirmed by the user the same day), before any dispatch regression was run.** The sample counts below use no dispatch outcome except the share dispatched, reported for orientation. The rules are binding once this file is committed; the first run happens after that commit. Follows `2026-11-13-fuel-switching-scope.md`, whose fleet-level estimate (σ ≈ 6.5 at the median, a hump) failed its persistence placebo (F3) and its merit-order check (F6), and said the unit-level discrete-choice route is the one to take.

**In one example.** At 14:00 on a day in 2019 the market clears at €45. A gas combined cycle that costs €40 to run is almost surely on; one that costs €60 is almost surely off; a coal unit at €46 is a coin toss. The probability that a unit is on is a smooth function of how far it sits below the clearing price. Estimate that function from the 200,000 unit-hours where units are near the price, and the response of the whole coal and gas fleets to a change in their relative cost follows by adding up the units.

## Question
How steeply does a unit's probability of dispatch rise with its distance below the clearing price, is that slope the same for coal and gas, and what elasticity of substitution between the fuels does it imply at fixed thermal output? Secondary: does the slope hold in the 2021-22 crisis (gas units)?

## Model
Unit `i`, hour `h`, window A 2019-01-01 → 2020-02-29 (main), window B 2021-06-01 → 2022-12-31 (gas stability). `x_ih = ln p*_h − ln c_ih` (`c` the bid-time cost of the cache), `y_ih = 1[cleared_ih > 0]`. A unit is on when `p*_h ≥ c_ih + m_i + ν_ih` (markup `m_i`, shock `ν`): with a logistic shock,
`P(y_ih = 1) = Λ( α_i + β_f x_ih + δ_f y_{i,h−1} + φ(ln p*_h, R_h) + month effects )`, `f` the unit's fuel.
- `α_i` absorbs the unit's markup and constraints; `δ_f` the persistence from start-up and minimum-run costs; `φ` a spline in the clearing price and the residual demand `R_h = F_demand − F_wind − F_solar` over offered thermal capacity (D-1 forecasts, predetermined).
- **Persistence-free spec (Model 2).** Linear probability model with unit effects and **hour effects**: `y_ih = α_i + λ_h + β_f(−ln c_ih) + δ_f y_{i,h−1} + ε`. The hour effects absorb the clearing price, residual demand and every common time pattern, so β is identified from which units are on *within the same hour* given their relative costs. It is not exposed to the persistence of an aggregate series, the failure of F3.
- **Fuel switching at fixed thermal output (closed form).** Let `K_i` be capacity, `P_i` the fitted probability, `Q_f = Σ_{i∈f} K_i P_i`, `S_f = Σ_{i∈f} K_i P_i (1 − P_i)`, `A_f = β_f S_f`. Raise coal's cost by `ε` (log). Holding `Q_c + Q_g` fixed, the clearing price moves by `d ln p* = ε A_c / (A_c + A_g)`, and
  **`σ_fuel(h) = −d ln(Q_c/Q_g)/ε = [A_c A_g / (A_c + A_g)] · (1/Q_c + 1/Q_g)`.**
  It is large when both fleets have units near the margin (`P(1−P)` large) and small when one is far from it: the hump, derived from the units, not assumed. The fleet value is the `Q`-weighted mean of `σ_fuel(h)` over the hours of a bin of the cost ratio `r = ln(c̄_c/c̄_g)`.

## Data and sample (counts, no relationship looked at)
Plant-specific gas and coal units of `outputs/cache/step` (`units_YYYYMM`, `hours_YYYYMM`): offered, not withdrawn that day (`withdrawn` false), `p* > 0`, valid hours, `|x| ≤ 0.75`.
| Window | Unit-hours | Gas | Coal | Units (gas / coal) | Share dispatched (gas / coal) |
|---|---|---|---|---|---|
| A (2019-01 → 2020-02) | 228,437 | 185,211 | 43,226 | 54 / 22 | 0.79 / 0.82 |
| B (2021-06 → 2022-12) | 273,324 | 257,695 | 15,629 | 55 / 6 | 0.77 / 0.56 |

## Rules, set before the run (confirmed 2026-11-13)
- **U1 Feasibility.** Window A has at least 100,000 unit-hours with `|x| ≤ 0.75` and at least 15 coal units (met: 228,437; 22); window B at least 50,000 gas unit-hours (met: 257,695).
- **U2 Cost matters.** In Model 1 (logit with unit effects, lag, clearing-price and residual-demand controls, month effects), `β_g > 0` and `β_c > 0`, each with |t| ≥ 3, standard errors clustered by day.
- **U3 Within-hour check.** In Model 2 (hour and unit effects), `β_g` and `β_c` are positive with |t| ≥ 3 (clustered by day), and the implied average marginal effects of Model 1 and Model 2 for each fuel are within a factor of 2 of each other.
- **U4 Placebo.** In Model 1, common circular shifts (200 draws, offsets of at least 30 days) of every unit's cost series relative to dispatch: the real |t| of `β_g` and of `β_c` each ranks in the top 5% (at most 10 of 201).
- **U5 One ranking logic.** `β_g = β_c` not rejected at 5% (Model 1). If rejected, coal faces constraints, the fuel-specific values are used, and the fixed-output σ is computed with them (as the formula already does).
- **U6 The implied elasticity.** `σ_fuel` at the median cost ratio of window A, from Model 1, is positive with a 95% interval (cluster bootstrap over weeks, 200 draws) excluding zero and lies in **[2, 20]** (the fleet-level estimate was 6.5 and failed its placebo, so the bounds are wide); and the `Q`-weighted `σ_fuel` in the lowest third of `r` exceeds the highest third's (the hump, as in the fleet spline).
- **U7 Crisis stability.** In window B, `β_g > 0` with |t| ≥ 3 in Model 1; the ratio `β_g(B)/β_g(A)` is reported, not ruled.
No other specification is tried after a failure.

## What each outcome means
U1-U6 pass: the unit-level slopes, not a trending daily series, give a fuel-switching elasticity with its hump and the dependence on the cost gap; the closed form transfers to any system with unit-level dispatch data and feeds the supply slope of the price-effect extension; the dirty-and-clean nest then adds the hydro fleet (water value as its cost, `hydro_cost_daily`) in a further pre-registration. U3 fails: the logit slope is driven by time patterns, not ranking; stop and report. U4 fails: even the unit-level slope is not distinguished from persistence. U5 rejected: coal's dispatch is constrained, reported with its fuel-specific slope.

## Threats
Cost is a lower bound (start-up costs, minimum income, minimum run: gas units priced more than €5 below the clearing price are on 85% of the time), so `x` is mismeasured and β attenuated toward zero; unit effects absorb a constant markup, not a markup that moves with costs; the lag handles persistence of the on/off state but a unit committed for a day (minimum-income days) is on whatever the price; hours with `|x| > 0.75` are dropped (selection on the regressor, not the outcome); the closed form holds the other fleets (hydro, nuclear, cogeneration, imports) as given. The 2022 cap changes which cost matters (subsidised against market) and is a separate question.

## Fixed details for the run
- **Sample.** Unit-hours of the plant-specific gas and coal units of the step cache in valid hours, offered with a known positive capacity, not `withdrawn` that day, `p* > 0`, `cost > 0`, `|x| ≤ 0.75`, and with the unit's previous-hour state present (the lag). **Units with no variation in `y` in the sample are dropped** (under unit effects they carry no information and make the logit diverge). The cost is daily, so a unit's cost series is constant within a day.
- **Controls in Model 1.** Unit dummies (no separate constant); `β_f x` and `δ_f y_{i,h−1}` by fuel; a cubic spline in `ln p*` (truncated-power form, knots at the terciles); `R_h = (F_demand − F_wind − F_solar)` over the hour's offered thermal capacity, linear and quadratic; month dummies. Standard errors clustered by day.
- **Model 2.** Linear probability model with unit and hour effects, estimated by demeaning every column, the unit dummies included, within hour (Frisch-Waugh); `β_f x`, `δ_f y_{i,h−1}`; clustered by day. The average marginal effect of Model 1 for a fuel is the mean of `β_f P(1 − P)` over that fuel's sample unit-hours; **U3** requires the ratio of that to Model 2's `β_f` between 0.5 and 2 for each fuel.
- **U4.** The shift moves every unit's daily cost series along the window's sorted dates by one common random offset (in days, at least 30, circular); unit-hours whose unit has no cost on the shifted date are dropped in that draw; Model 1 is refitted; the statistic is |t| of `β_g` and of `β_c`; 200 draws, seed 20261113.
- **U6 closed form.** `Q_f = Σ K_i P̂_i` over the fuel's sample unit-hours of the hour plus `Σ K_i y_i` over its offered unit-hours outside the sample (far from the margin, probability set to the observed state), `K_i` the offered capacity; `S_f = Σ K_i P̂_i(1 − P̂_i)` over the sample; `σ_fuel(h) = [A_c A_g/(A_c + A_g)](1/Q_c + 1/Q_g)`, `A_f = β̂_f S_f`. Hours with no coal unit in the sample are skipped. "**At the median cost ratio**" is the `(Q_c + Q_g)`-weighted mean of `σ_fuel(h)` over hours whose daily `ln(c̄_c/c̄_g)` lies between the 40th and 60th percentile of the window; "lowest third" and "highest third" are the same mean over the hours below the 33rd and above the 67th percentile. The bootstrap resamples weeks (200 draws), refits Model 1 each time and recomputes the median-ratio `σ_fuel`; the interval is the 2.5th and 97.5th percentiles.
- **U7.** Model 1 on window B, gas units only.
- Code: `scripts/analysis/unit_dispatch.py`; outputs `outputs/tables/unit_dispatch_*.csv`.
