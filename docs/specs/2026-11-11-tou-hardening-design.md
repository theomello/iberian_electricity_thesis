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
