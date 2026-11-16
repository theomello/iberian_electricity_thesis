# Industrial short-run price elasticity: estimation spec (proposal)

**Status: proposed 2026-11-16, not registered. Binding when the user confirms and this file is committed; the first slope is computed after that commit.** Follows `2026-11-17-industry-iv-noise-reducers-design.md` (step zero: V1, V2, V3 pass I1-I3, V3 primary with detectable elasticity 0.016) and the erratum in `2026-11-16-industry-spot-iv-noise.md` (the first 'noise fails' result was a standard-error bug). **No slope has been computed for any variant.**

**In one example.** On a Tuesday in March 2022 the day-ahead price at 3 pm is €30/MWh above what last week, the calendar and the weather predict, only because the wind forecast for that hour came in 4 GW lower than usual. If industrial plants (voltage bands E3-E6) cut that hour's load by 0.6% relative to what their own history predicts, the impact elasticity is 0.006 / (30/98) ≈ -0.02. The estimate is that cut, scaled by the price surprise, averaged over hours; the spec below fixes in advance how we judge whether it is believable.

## Estimand and data (unchanged from step zero)
Impact (same-hour) elasticity of industrial load, ESIOS 1204-1207, to the OMIE day-ahead price, instruments D-1 wind and solar forecasts (1777, 1779) and their squares, non-holiday weekdays 2019-01-01 -> 2023-12-31 without 2020-03-01 -> 2020-06-30. The slope on ln load per €/MWh is multiplied by the mean price (€98) to give an elasticity at the mean. **Short-run only**; plants that respond within the day (shifting shifts, interruptible loads) are what it captures, not annual capacity decisions.

## Estimates (three variants, same code as step zero, now with slopes)
- **Primary: V3** (week-on-week difference + boosted double ML), chosen at step zero by smallest SE. Date-clustered SE and a 95% Anderson-Rubin set (inverting the test of beta = b0 over a grid of 2,001 slopes) next to the normal interval.
- **Robustness: V1 and V2**, same outputs.
- **Inference rule (replaces normal critical values).** Because the size check at step zero did not return about 5% (0% for V1/V2, 100% for V0), the p-value is **randomization-based**: the real |t| is ranked among the |t| of 1,000 permutations of the residualised instruments across dates within year-month (hour matched), p = (1 + #{|t_perm| >= |t_real|}) / 1001; the Fisher-style interval is the set of slopes not rejected. The normal and Anderson-Rubin intervals are reported beside it. If the three disagree, the randomization one is the headline and the disagreement is itself recorded.

## Rules, set before the run (each says what a failure would tell us)
- **E1 Sign and plausibility.** The V3 impact elasticity is negative and its absolute value is at most 1. *Fails:* a positive or implausibly large elasticity points at a broken exclusion restriction (forecasts move load through weather or the plant calendar, not through price), not at behaviour; go to E3 and E5 to see where.
- **E2 Detected.** The randomization p-value of V3 is at most 0.05 and the randomization interval excludes zero. *Fails (with E1 passing):* an elasticity too small to detect at the 0.016 bound is the result: report 'between zero and the interval', not zero.
- **E3 Placebo outcome (exclusion check).** The same V3 pipeline with the outcome replaced by the pre-determined ln load of the same hour **7 days earlier** (so the current price cannot have caused it): randomization p above 0.05 and absolute 'elasticity' below 0.01. *Fails:* the instruments predict load that the price could not have affected, so the forecasts carry non-price information about industrial load; the main estimate cannot be read as price response, and the next step is to add the offending channel (temperature extremes, holidays, outages) to the residualisation.
- **E4 Overidentification.** Hansen J test (date-clustered) of the four instruments against the first variant: p above 0.05; and the wind-only and solar-only slopes lie inside each other's 95% randomization intervals. *Fails:* one source of forecast variation behaves differently from the other, which is information about which one is valid (for example, solar moves load through the hour of the day, which would show in E6).
- **E5 Stability over years.** Slopes estimated separately for 2019, 2021, 2022 and 2023 (2020 has too little data after dropping the lockdown): all have the same sign and the equality test across years has p above 0.05. *Fails:* different regimes (the 2022 price crisis, gas cap from June 2022, the June 2021 reform itself) have different responses; this is then the finding, reported by year with the pooled value as an average, not a single elasticity.
- **E6 Hour pattern (exploratory, no pass/fail).** Slopes for night (0-7), day (8-17) and evening (18-23) blocks, with the same randomization intervals. Purpose: compare with the household evening response and with the paper's industrial group; anything seen is labelled exploratory.
- **E7 Variant agreement.** V1 and V2 elasticities each lie inside V3's 95% randomization interval. *Fails:* the answer depends on the noise reducer, which is a statement about how much of the estimate is the learner and how much is the data; both are reported and V3 is not preferred without a reason.
- **E8 Calibration of the permutation test (diagnostic).** The share of permutation draws with randomization p below 0.05 is between 0.02 and 0.10 when the permutation test is applied to the permuted draws themselves (leave-one-out ranks). *Fails:* the randomization test is not well sized for this statistic; the normal and Anderson-Rubin intervals are then the headline and the failure is reported.

Not run in this spec and not available after a failure: other instruments, other outcomes, other learners. A failed rule is recorded and kept; the next step is the one named under it, registered separately.

## What each outcome means
All of E1-E5 and E7 pass: an industrial impact elasticity, identified from forecast-driven price surprises and statistically detected, to be reported next to the household one (both short-run, both with randomization intervals), and the candidate for the thesis headline's industrial half. E1 or E2 fail with the others passing: a bounded 'small or zero' industrial response, which is itself the contrast with households. E3 or E4 fail: the identification is in doubt and the number is not reported as an elasticity.

## Threats
Exclusion restriction (forecast errors correlate with weather and the generation mix, which affect some plants); the price instrument also moves gas-fired thermal generation and so the cost of self-generating plants (cogeneration); lagged load as a predictor may contain last week's price response (hence 7+ days); boosted learners cannot extrapolate beyond the training price range (the 2022 prices); time-blocked cross-fitting still shares long-run information; the aggregate E3-E6 load mixes plants with very different flexibility, so the elasticity is a load-weighted average; hourly load is metered at the voltage band, not by industry; the bound 0.016 is a detectability bound for V3 under correct standard errors and does not say what elasticity to expect.

## Data and code
Same files as step zero. New code: `scripts/analysis/industry_iv_estimation.py` (imports the builders and `iv()` from `industry_iv_noise_reducers.py`); outputs `outputs/tables/industry_iv_estimation.csv` (variant, block, slope, elasticity, SE, normal/AR/randomization intervals, p) and `industry_iv_estimation_checks.csv` (E3-E5, E7, E8). Seed 20261117.

## Results (run 2026-11-16; script `industry_iv_estimation.py`, committed before the run; outputs `industry_iv_estimation{,_checks}.csv`)

Impact elasticity of industrial load (E3-E6 voltage bands) to the day-ahead price, randomization intervals (1,000 permutations), at mean price €98:

| Variant | First-stage F | Elasticity | Randomization interval | p (rank of abs t) |
|---|---|---|---|---|
| **V3 (primary)** | 94 | **+0.005** | [-0.005, +0.023] | 0.66 |
| V1 | 112 | +0.003 | [-0.010, +0.029] | 0.69 |
| V2 | 32 | -0.008 | [-0.043, +0.040] | 0.28 |

| Rule | Result | Detail |
|---|---|---|
| E1 sign and plausibility | **fail** | elasticity +0.005, wrong sign (tiny) |
| E2 detected | **fail** | p 0.66; interval includes zero |
| E3 placebo outcome | **fail** | lag-7-day load 'elasticity' -0.022, p 0.002 |
| E4 overidentification | **fail** | Hansen J p 0.083 (pass) but wind-only +0.001 [-0.012, 0.017] excludes solar-only +0.052 (solar-only F 7.3, weak) |
| E5 stability over years | **fail** | 2019 +0.054, 2021 +0.022, 2022 -0.026, 2023 -0.008; equality p 0.006 |
| E6 hour blocks (exploratory) | | night -0.003, day +0.013 [-0.005, 0.037], evening -0.001 [-0.010, 0.020] |
| E7 variant agreement | **fail** | V1 +0.003 and V2 -0.008 vs V3 interval: V2 is inside, V1 outside the upper... see CSV; rule as registered fails |
| E8 permutation calibration | pass (near-tautological) | leave-one-out share 0.049; share abs(t)>1.96 is 0.12 for V3 |

**Reading.** The design is now sharp (SE 0.006) and the central estimate is a precise near-zero: with V3 the data rule out industrial impact elasticities more negative than about -0.005 and less than +0.023 at 95%. By the registered rules this is **not reported as an identified elasticity**: the placebo (E3) fails, so the instruments carry information about lagged load that price cannot have caused, at a size (-0.022) as large as the interval itself; the response drifts across years (E5; 2019 positive, 2022 negative), which suggests the pooled number averages regimes; solar-only is weak (F 7). What survives is a bounded statement: no detectable hourly price response of industrial load larger than about 2% per 100% price change, with the exclusion caveat. Two implementation notes: the 2023 randomization interval is empty (the permutation AR test rejects every slope on the grid, p_AR0 0.007), recorded as an unreliable subset, not interpreted; the V2 normal AR set is empty for the same reason.

**What the diagnostics suggest next (not run).** The placebo failure localises the problem: the same-hour lag-7 load is correlated with the forecast instruments after residualisation, which points to weather/mix channels (wind forecast correlates with weather regimes that persist over a week). A candidate fix is to residualise on lagged forecasts or to use the forecast *error* (forecast minus realised wind), which is a cleaner surprise; needs its own registered spec.
