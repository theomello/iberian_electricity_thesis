# Hardening the time-of-use replication (after the failed elasticity designs)

**Status: proposed 2026-11-11, written before any run.** Branch `tou-policy-prices`. Continues `2026-11-11-tou-replication-design.md`
§3c, whose verdict was: the magnitudes replicate (peak −10.5%, mid −6.4%, off −4.7%; LASSO −11.6/−6.9/−3.2) but the identification is
thin, because (a) weekend fake peaks fall as much as real peaks (−9.3% against −10.5%), (b) the treated series (ESIOS 352) is a
retailer schedule, not measured load, and its 2019 level drift is mostly migration out of the regulated tariff (CNMC, same section),
(c) the placebo rank passes only after excluding the COVID windows, (d) no elasticity step has been run.

**In one example.** In June 2021 the network charge for a regulated household went from flat to three-part: about +190% at peak
(10–14h, 18–22h on working days), −88% at off-peak (nights and weekends), relative to the new average. If working-day peak load falls
by 10% and weekend load at the *same hours* falls by 9%, the weekend fall says most of the 10% is something other than the peak price.
The test is what is left after that is taken out.

## Steps

1. **Measured demand instead of the schedule.** The same DiD and LASSO prediction errors, the outcome ln E0 (ESIOS 1201, measured
   low-voltage demand, hourly) minus ln Portugal at the same local hour. E0 is measured, covers regulated and free-market
   low-voltage consumers alike (all had the new access tariff, passed through in their contracts), and is not affected by migration
   between the two retail regimes, which removes the 2019 drift of the schedule. Everything else as in `analysis/tou_did.py`.
2. **Triple difference against weekends and holidays.** Working days: peak hours, mid hours, off hours. Weekends and holidays: the
   same clock hours, all off-peak under the policy. The policy-specific effect is the post × peak-hours coefficient on working days
   minus the same on weekends (post × peak-hours × working-day), estimated on the stacked sample with hour, weekday and month
   effects, clustered by week; and the same on LASSO prediction errors.
3. **Migration control** (only for the schedule version): not needed for E0; for 352 the log of 352's share in 351 + 352 as a control.
4. **The elasticity step**, only if step 2 passes: the DiD or DDD effect by period divided by the log change in the regulated price
   by period (`outputs/tables/tou_price_shape.csv`: charges component by period, plus the energy term), as an own-price elasticity for
   peak, with the mid-peak and off-peak as the cross terms.

## Stop rules, set before the run

1. **E0 replication.** The peak effect on E0 is negative and between −1% and −20%; if it is positive or beyond −20% it is read as
   confounding.
2. **Placebo dates.** As before: fake breaks at the 1st of each month 2019-01 → 2020-12, the seven COVID windows (March–June 2020) set
   aside before the run, not after; the real effect outside the placebos' 5th–95th percentile and in the top 5% by size.
3. **Triple difference.** The policy-specific coefficient (peak − off on working days minus the same on weekends) is negative and
   at least 2 standard errors below zero. If it is not, the verdict is that **the time-of-use effect is not separable from a
   level shift**, and no elasticity is run.
4. **Same sign in E0 and in 352.** The DDD on 352 and on E0 agree in sign; if they differ, the schedule is not the load.
5. **Elasticity** (if run): between −0.5 and 0 for peak (the paper: −0.08 to −0.135); outside it is confounding.
6. **Power.** The DDD standard error against the paper's size (about 5 points).

## What would make it a failure even if it runs

The reform coincides with the post-lockdown recovery and the start of the price crisis (Portugal shares the wholesale price but not
the pass-through); weekends and holidays are not a clean control if the policy also changed weekend behaviour (the off-peak charge
applies all weekend, so weekend load may rise, which would bias the DDD towards a larger policy effect); E0 includes consumers above
15 kW whose tariff changed differently (3.0TD has six periods); Portuguese load includes industry, so its weather sensitivity differs.

## Results (2026-11-11, user's go-ahead: "Sounds great")

Scripts `analysis/tou_did.py --e0`, `tou_ddd.py [--e0]`, `tou_elasticity_step.py` → `outputs/tables/tou_did_e0_{estimates,placebo}.csv`,
`tou_ddd{,_e0}{,_placebo}.csv`, `tou_elasticity_step.csv`. Outcome: ln of Spanish load minus ln Portuguese load at the same local hour,
2018-01-01 → 2021-09-30, break 2021-06-01; E0 = ESIOS 1201 measured low-voltage demand, 352 = the retailers' schedule.

**Step 1, measured demand (E0), DiD V1 / LASSO errors, %:**

| | peak | mid | off | peak − off |
|---|---|---|---|---|
| E0, DiD V1 | −5.87 (0.85) | −2.77 (0.89) | **+0.09 (0.81)** | −5.95 (0.59) |
| E0, LASSO errors | −7.36 | −3.82 | +0.79 | |
| 352, DiD V1 (earlier) | −10.5 | −6.4 | −4.7 | −5.8 |
| E0, weekend and holiday fake peaks, DiD V1 | −2.65 (0.95) | +0.62 | +1.86 (1.09) | −4.51 (0.75) |

Placebo breaks (17, the seven COVID windows set aside in advance): peak placebo sd 0.68, 5–95% −1.82 to +0.27; the real −5.87 ranks **1 of
18**; LASSO 1 of 18. **Rule 1 and rule 2 pass.** The off-peak effect on E0 is zero (352: −4.7): the all-hours fall of the schedule, which was
the level shift and drift, is not in the measured demand. What remains is a peak and mid-peak fall against flat off-peak load.

**Step 2, triple difference** (stacked working days and weekends, clock classes, hour, weekday and month effects, clustered by week):

| | peak − off, working days | same hours, weekends | **DDD peak** | DDD mid |
|---|---|---|---|---|
| E0, DiD V1 | −6.99 (0.58) | −4.52 (0.75) | **−2.48 (0.54), t −4.6** | −2.64 (0.59) |
| E0, LASSO errors | −10.01 | −7.38 | **−2.63 (0.51), t −5.2** | −2.86 (0.53) |
| 352, DiD V1 | −8.14 (1.03) | −7.81 (1.18) | **−0.33 (0.77)**, t −0.4 | +0.18 (0.77) |
| 352, LASSO errors | −11.50 | −11.00 | −0.50 (0.68) | +0.10 (0.70) |

**Rule 3 passes on E0** (−2.48, 4.6 standard errors below zero; LASSO the same), **fails on 352** (−0.3, nothing). Rule 4 (same sign in
E0 and 352): the signs agree but 352's DDD is zero, so **the schedule does not carry the policy-specific effect that measured demand
shows**. About a third of the working-day peak-minus-off fall (−2.5 of −7.0; LASSO −2.6 of −10.0, a quarter) is specific to the policy;
the rest is a fall in those clock hours that weekends share. The DDD's own placebo breaks (17): peak DDD placebo sd 0.94, 5–95% −2.47 to
+0.23, the real −2.48 sits on the 5th percentile and ranks **2 of 18**: borderline, no rule was set for it.

**Step 4, elasticity** (run because step 2 passed on E0). Relative price of a period against off-peak, before and after, on the same
wholesale energy cost (ESIOS 1001 minus the charges 1876, working days June–September 2021): the system charges are **not constant in
the window** (peak 133.1 June–August, 82.3 September, 31.5 October–December; off-peak 6.0, 3.5, 0.9), so the 3b average of 83.7 / 31.9 /
3.4 (June–December) understated the summer shape. Mean change in ln(p_peak / p_off) is **+0.613**, in ln(p_mid / p_off) +0.230. Elasticity of
substitution between a period and off-peak = DDD effect / change in ln relative price:

| period against off-peak | Δ ln relative price | DDD effect | elasticity (DiD V1) | elasticity (LASSO) |
|---|---|---|---|---|
| peak | +0.613 | −2.48% (0.54) | **−0.040 (0.009)** | −0.043 (0.008) |
| mid-peak | +0.230 | −2.64% (0.59) | **−0.115 (0.026)** | −0.125 (0.023) |

Rule 5 (between −0.5 and 0): passes for all. The paper's own-price elasticity is −0.08 to −0.135, a different object (own price, not
relative to off-peak); the mid-peak figure falls in that range, the peak figure is a third of it. Without the weekend correction the
peak-minus-off contrast (−5.95, step 1, off-peak including weekends) over the same price change gives about −0.10: in the paper's range,
but it contains the level shift. **The policy-specific substitution is smaller: −0.04 peak, −0.12 mid-peak.** Rule 6 (power): the DDD
standard error is 0.5 points against the paper's about 5: the DDD can detect about 1 point, so the −2.5 is well measured.

**Correction to section 3b of the replication spec** (same day): I wrote that the paper's "+200% and −86%" looked relative to the new
average, not the old flat charge. Against the old flat €44.0 the charges component of June–August 2021 (133.1 / 41.8 / 6.0) is **+202%,
−5% and −86%**, exactly the paper's numbers: the paper's percentages are against the old flat charge, and the shape check holds with
the actual summer charges. The system charges were cut in September and October 2021, which the June–December average hid.

**Caveats still open.** The weekend control assumes weekend behaviour was not itself changed by the reform (off-peak applies all weekend,
so weekend load could rise, which would make the DDD too large); E0 includes consumers above 15 kW (different tariff structure) and
free-market contracts whose energy price is flat; the post window (June–September) is one summer and the price rise of autumn 2021 is
outside it; the DDD placebo is borderline; Portugal's load includes industry. Not done: the month-by-month path of the DDD (does it start
in June 2021?), a second control (France), a falsification on a group with no time-of-use charge.

## Month-by-month path and a second control (2026-11-11, user's go-ahead: "Yes, run both"; rules set before the run)

**Path.** The measured-demand triple difference (E0, DiD V1, working-day peak minus off, less the same hours on weekends) for each calendar
month from 2019-01 to 2021-09, each month a one-month post window against everything before it from 2018-01 (March–June 2020, the
COVID months, out of the pre-window and not estimated). Rules: (P1) the DDD in each of June, July and August 2021 is negative with t below
−2; (P2) before June 2021 it is flat: of the monthly DDDs 2019-01 → 2021-05 (COVID months out), no more than two outside ±2 standard
errors and none below −2.5 points; (P3) the average of the 2021-06 → 2021-09 months is within 1 standard error of the quarter-sample DDD
of −2.48. A failure of P2 reads as a trend in the weekday-weekend gap, not a policy effect.

**France.** The same DDD with France's consumption (RTE éCO2mix, hourly, French clock) in place of Portugal's, and with the mean of the two
logs as control. Rules: (F1) the France-controlled DDD peak is negative with t below −2; (F2) its size within a factor of two of the
Portuguese-control −2.48; (F3) the same placebo breaks (17, COVID windows out) rank the real effect in the top 3 of 18. If F1 fails, the
Portugal-controlled result rests on that control and is not reported as the policy effect.
