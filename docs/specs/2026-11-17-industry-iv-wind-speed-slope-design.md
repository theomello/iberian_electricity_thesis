# Wind-speed instrument interacted with the offer-curve slope (pre-registration)

**Status: registered 2026-11-17, before any run. Nothing below has been scored or estimated.** Follows `2026-11-17-industry-iv-wind-speed-estimation-design.md`, whose result is a bounded null for industrial load: +0.0001 [-0.021, +0.028] (F 93). This is the **ninth** instrument set tried in this thread (C0-C4, B0-B2, and this one); the count goes into any statement about the result.

**Why this variant.** The bid-curve instrument (forecast miss scaled by the day's offer curve) failed because the forecast miss comes after the day-ahead price is set. The wind level does move the day-ahead price (C1, F 93). What C1 lacks and the bid instrument had is how much each hour's price moves per GW of wind: steep where the offer curve is steep, flat where it is flat. Multiplying C1 by the offer-curve slope from the same hour a week earlier (predetermined) gives that scaling without the forecast miss.

**In one example.** At 3 pm the offer curve is steep (a GW of wind moves the price by EUR 8) and at 4 am it is flat (EUR 1). The same wind change is then a bigger price shock at 3 pm; the interaction lets the first stage use that, so the estimate leans on the hours where wind actually moves the price.

## Candidate (closed; no further variants in this registration)
**X1**: instruments d_pc and d_pc x s, with d_pc the week-on-week change of min(ws/12, 1)^3 (national mean 100 m wind speed) and s the offer-curve slope of the same hour 7 days earlier, standardised on the common sample (`slope7z` of the first settlement). **The slope level s is added to the predictors** of the double ML, so the instrument cannot work through the slope's own effect. Everything else as C1's home set (common sample 19,388 hours, week-on-week differences, no realised wind among the predictors, placebo residualised without its own lag).

## Scoring (first stage and placebo only; same thresholds as the settlements)
- **S1** F at least 20 full sample, at least 10 in 2019-21H1 and in 2021H2-23.
- **S2** placebo p above 0.10 in the three blocks (1,000 permutations, seed 20261117).
- **S3** idle-wind test on the wind component d_pc (rows with national mean speed below 5 m/s in both weeks, at least 800 rows, p above 0.05 and |ratio| at most 0.5), and the same test on the interaction component, which should also have no first stage in those hours.
- **S4 Comparison with C1** (first stage only): the incremental F of d_pc x s over d_pc alone, date-clustered. At least 10: the slope scaling adds price variation.

## Use, if X1 passes S1-S3
Then (separate go-ahead) the elasticity is estimated with X1 under the same rules E1-E8 as the C1 run, and **replaces C1 as primary only if** (i) its randomization interval is at least 15% narrower than C1's [-0.021, +0.028] and (ii) its elasticity lies inside C1's interval; otherwise it is reported as a robustness estimate next to C1. **If X1 fails S1-S3, the bid-curve and slope routes are closed for good and the instrument question has no further candidates.**

## Not done here
No elasticity is computed. Script `scripts/analysis/industry_iv_wind_speed_slope_settlement.py` (to be written and committed before it runs); outputs `outputs/tables/industry_iv_wind_speed_slope{,_rules}.csv`.

## Results (run 2026-11-17, script `industry_iv_wind_speed_slope_settlement.py`, committed before the run; outputs `outputs/tables/industry_iv_wind_speed_slope{,_rules,_f3}.csv`)
First stage F (full / 2019-21H1 / 2021H2-23): 107 / 55 / 84 (S1 pass). Placebo p: 0.19 / **0.015** / 0.92 (S2 **fails** in 2019-21H1). Idle-wind rows 1,598: wind component d_pc ratio 0.54, p 0.095 (limit 0.5: **fails narrowly**); interaction ratio -1.10, p 0.34 (**fails**). S3 fails. S4: incremental F of the interaction over d_pc alone is 35, so the slope scaling does add price variation, but the added variation does not pass the validity checks.

**Outcome.** X1 fails S2 and S3 and is **not used**. Per the registration, the bid-curve and slope routes are closed for good; no further instrument candidates. C1 alone remains the primary instrument. Pattern across the thread: every instrument carrying offer-curve information (B1, B2, X1) fails the placebo in 2019-21H1 (p 0.008, 0.023, 0.015), which suggests the lagged curve shape is correlated with how load evolves in that period; not investigated further. Instrument sets tried in this thread: nine (C0-C4, B0-B2, X1); one passes.
