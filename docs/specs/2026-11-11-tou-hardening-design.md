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

### Results of the path and the second control (2026-11-11)

`analysis/tou_ddd_robust.py` → `outputs/tables/tou_ddd_{path,path_controls,control}.csv`; blocks in `outputs/tables/tou_ddd_peak_blocks.csv`.

**France control (F1–F3 pass).** DDD peak, DiD V1, 17 placebo breaks (COVID windows out): Portugal **−2.48 (0.54), rank 2 of 18**; France **−3.51
(0.62), t −5.6, rank 1 of 18**; the mean of the two logs **−2.99 (0.52), rank 1 of 18**. Negative with t below −2 (F1), within a factor of
two of the Portuguese figure (F2: 1.4), top 3 (F3). The result does not depend on the Portuguese control.

**Path (P2 fails, P1 fails by one month).** DDD peak by month, Portugal control: Jun 2021 −3.17 (t −3.8), Jul −3.18 (t −3.6), **Aug −0.96 (t −1.1)**,
Sep −3.41 (t −5.3), mean −2.68 (P3 passes). But **before the reform the DDD is already negative: Feb 2021 −5.90, Mar −4.40, Apr −3.92, May −2.92**
(mean −4.3; France −3.4; mean of the two −3.8), against 2019 to January 2021 months with mean −1.2 and sd 1.8. Six pre-June months sit below
−2.5 points, with every control. **So the triple difference does not start in June 2021.** The monthly standard errors are too small
(2019–2020 months reach t of −4 to −5 on noise), so the point is the path, not the t-values.

**Where the pre-reform movement is.** The simple DiD placebo breaks of 2021-01 → 2021-04 on E0 show no peak fall (peak +0.1 to +2.0%;
peak − off −1.3 to −2.8%, the off-peak rising +1.4 to +3.7%), against the real peak −5.7%: the **E0 DiD is specific to June 2021**. The
working-day peak-minus-off series is flat before June (Feb–May 2021: +0.4, +2.4, +0.9, −1.3) and falls at the reform (Jun–Sep: −5.3, −6.7,
−9.8, −5.3). The weekend arm moves before and after: +6.2, +6.8, +4.8, +1.6 in Feb–May 2021, then −2.1, −3.6, −8.8, −1.9. So the pre-trend
in the DDD is in the weekend benchmark, not in the working days.

**Split of the peak: morning (10–13h) against evening (18–21h)** (exploratory: a split I chose after seeing the path, to test one explanation, rooftop solar
self-consumption lowering measured demand in daylight hours on every day; nothing was set in advance). E0, Portugal control, DiD V1, evening-peak or
morning-peak hours against night, with the other block dropped:

| block | working days | weekends | DDD (se) | placebo 5–95%, rank | Feb–May 2021 fake break: DDD (working / weekend) |
|---|---|---|---|---|---|
| morning peak 10–13h (solar hours) | −5.67 | −5.24 | **−0.43 (0.76), t −0.6** | −4.29 to +2.50, rank 16 of 18 | −5.86 (+1.86 / +7.72) |
| evening peak 18–21h (no solar) | −8.42 | −3.48 | **−4.94 (0.71), t −6.9** | −2.42 to +1.15, **rank 1 of 18** | −2.66 (−0.48 / +2.17) |

**Reading.** The morning-peak fall is the same on weekends (−5.7 against −5.2): not policy-specific, as a daylight effect (solar
self-consumption, or any change in daytime load that is common to all days) would predict. The **evening peak carries the policy-specific
effect: −4.9%** (LASSO not run on this split), outside the placebo range and rank 1; its fake break in Feb–May 2021 is −2.7, half the real
size, from the weekend arm rising +2.2 (so about −2.3 net of that pre-movement, a lower bound). With the same price change as the whole
peak (+0.613 in ln relative price), the evening-peak substitution elasticity is about **−0.08** (−4.94 / 61.3; not computed with a
standard error here), at the lower end of the paper's −0.08 to −0.135 own-price range. Treat it as a lead: chosen after the path, not set
before it, and resting on a weekend benchmark that moved before the reform.

**Status.** Step 1 (E0 DiD) passes and is specific to June 2021. Step 2 (DDD) passes on the point estimate and on the France control but
**fails the pre-trend (P2)**; the explanation tested (daylight hours) points to the evening peak as the policy-specific part. The
elasticity step ran on the whole-peak DDD (−0.04, −0.12) and should be read with the evening split (−0.08) in mind.

## Pre-registration: the evening-peak design (2026-11-11, written before any run of it)

**Status: pre-registered, not run.** Everything below was fixed before `analysis/tou_evening_ddd.py` was run; the evening-peak split itself was
found after seeing the path (above), so what is registered is the confirmation test of a lead, on the same data. Anything not listed is
exploratory and will be labelled so.

**Hypothesis.** The policy-specific effect of the June 2021 reform on measured low-voltage demand is a fall in working-day evening-peak
(18–21h) load relative to night (0–7h), over and above the same clock hours on weekends and holidays, relative to Portugal and France.

**Design (primary: Portugal control, E0 = ESIOS 1201, break 2021-06-01, post window to 2021-09-30).**
- **V1** DiD triple difference, evening-peak and night hours only (other hours dropped), hour, weekday and month effects, clustered by week;
  pre-window every day from 2018-01-01 except March–June 2020.
- **V2** as V1 with **January–May 2021 also dropped from the pre-window** (the months where the weekend arm moves; a pre-set exclusion, not
  a choice from the result: it is the window in which the pandemic restrictions of Spain, Portugal and France differed most).
- **V3** LASSO prediction errors (`tou_did.lasso_errors`: day-type × hour, month, trend, temperature), trained on 2018-01 → 2020-12 without
  March–June 2020, evaluated June–September 2021; the DDD on the errors by the same cells, clustered by week.
- **Controls:** Portugal (primary), France and the mean of the two logs (secondary), V2 and V3 for each.
- **Dose-response blocks**, each against night hours with the other blocks dropped, V2, Portugal: evening peak 18–21h, late mid-peak 22–23h,
  afternoon mid-peak 14–17h, morning mid-peak 8–9h, morning peak 10–13h. The change in ln relative price (block against night) is computed
  day by day from ESIOS 1001 minus 1876 (energy), 1876 (new charges) and the old flat 44.0, as in `analysis/tou_elasticity_step.py` but for the
  block's own hours; elasticity of substitution = DDD / that change.
- **Placebo breaks:** the 1st of each month 2019-01 → 2020-12 whose 4-month window misses March–June 2020 (17), V1, evening peak.

**Stop rules, in order.**
1. **V2 on E0, Portugal:** DDD evening peak negative with t below −2. **France and the mean control:** same sign, t below −2. If either fails,
   the evening-peak lead is dropped and the whole-peak result stays flagged as not separable from a level shift.
2. **V3 (LASSO):** negative, t below −2, and within a factor of two of V2's size. If not, the effect is estimator-dependent and is not quoted
   as the policy effect.
3. **Placebo breaks:** the real V1 effect outside the placebos' 5th–95th percentile and in the top 2 of 18 by size.
4. **Dose-response:** the elasticities of the four non-peak-morning blocks (evening peak, late mid, afternoon mid, morning mid) are each within a
   factor of two of the evening peak's, with the same sign; blocks with DDD standard error larger than half the effect are listed and not counted.
   **The morning peak (10–13h) is reported but is not part of this rule**: the policy gives it the same price rise as the evening peak, so a
   zero there is heterogeneity by time of day (people at work, small businesses in E0) or a confounder I have not identified, and either
   reading is stated, not resolved.
5. **Sign and size:** the evening-peak elasticity between −0.5 and 0 (the paper: −0.08 to −0.135 own price).
6. **Power:** the DDD standard error of the evening peak below 1 point; reported against the effect.

**What each outcome means.** All six pass: the evening-peak effect is the quotable policy-specific result, with the morning-peak heterogeneity
and the weekend-arm pre-movement as stated caveats. Rule 1 or 2 fails: no policy-specific effect is claimed. Rule 3 fails: the effect is in the
range of the monthly noise of the weekday-weekend gap. Rule 4 fails: the pattern is not price-proportional, and the evening effect is read as
a time-of-day change that the policy does not predict (for instance a change in evening routines).

**Threats that remain even if all six pass.** (a) The June 2021 evening wholesale price spread rose as solar depressed midday prices and gas rose;
PVPC households see it on the energy term. Weekends share it, so the DDD removes it if households respond to the energy price on weekends as on
working days; if they do not (they use more evening load on weekends anyway), part of the effect is the energy price, not the charge.
(b) E0 includes small businesses and free-market contracts. (c) One summer. (d) Spain and Portugal ended the pandemic restrictions on different
dates, which moves working-day against weekend patterns; V2 drops the months in which it moves most but not the whole of 2020.

### Results of the pre-registered evening-peak design (2026-11-11)

`analysis/tou_evening_ddd.py` → `outputs/tables/tou_evening_ddd_{main,blocks,placebo}.csv` (the helper `tou_ddd.contrasts` now returns NaN for an absent cell).
E0, break 2021-06-01, post window to 2021-09-30; evening peak 18–21h against night 0–7h; DDD = (working-day contrast) − (weekend contrast), %.

| control | spec | DDD (se), t | working days | weekends |
|---|---|---|---|---|
| Portugal | V1 | −4.94 (0.71), t −6.9 | −8.42 | −3.48 |
| Portugal | **V2** (no Jan–May 2021) | **−5.25 (0.71), t −7.4** | −8.55 | −3.30 |
| Portugal | V3 LASSO errors | −4.96 (0.67), t −7.4 | | |
| France | V2 | −4.34 (0.70), t −6.2 | −15.84 | −11.50 |
| mean of Portugal and France | V2 | −4.79 (0.65), t −7.4 | −12.19 | −7.40 |

Placebo breaks (17, V1): real −4.94; placebo sd 1.16, 5–95% −2.43 to +1.15; **rank 1 of 18**.

Dose-response blocks (V2, Portugal, each against night, price change from ESIOS 1001 / 1876 and the old flat 44.0):

| block | DDD (se) | working days | weekends | Δ ln relative price | elasticity (se) |
|---|---|---|---|---|---|
| evening peak 18–21h | −5.25 (0.71) | −8.55 | −3.30 | +0.607 | **−0.086 (0.012)** |
| late mid-peak 22–23h | −1.94 (0.71) | −3.58 | −1.64 | +0.230 | −0.084 (0.031) |
| afternoon mid-peak 14–17h | −3.82 (0.84) | **−0.56** | **+3.26** | +0.228 | −0.167 (0.037) |
| morning mid-peak 8–9h | −3.73 (0.47) | −10.32 | −6.59 | +0.231 | −0.162 (0.020) |
| morning peak 10–13h (reported, not in rule 4) | −1.11 (0.76) | −5.48 | −4.37 | +0.619 | −0.018 (0.012) |

**Stop rules, in order.** (1) V2, t below −2 under Portugal (−7.4), France (−6.2) and the mean (−7.4): **pass**. (2) LASSO V3 −4.96, t −7.4, within a
factor of two of V2: **pass**. (3) placebo breaks outside the 5–95% range and rank 1 of 18: **pass**. (4) the four blocks' elasticities within a factor of
two of the evening peak's (−0.086): late mid-peak 0.98×, morning mid-peak 1.88×, afternoon mid-peak 1.94×, same sign, none excluded by the standard-error
clause: **pass, by the letter and barely for two blocks**. (5) evening-peak elasticity −0.086, inside −0.5 to 0: **pass**. (6) standard error 0.71 < 1: **pass**.
**All six rules pass.**

**Verdict: the evening-peak effect is the quotable policy-specific result.** On measured low-voltage demand the June 2021 reform lowered working-day
evening-peak (18–21h) load by about 5% relative to night, over and above weekends, relative to Portugal, France and their mean, in three estimators, with the real
effect ranked first among 18 breaks. The elasticity of substitution between the evening peak and night is **−0.086** (standard error 0.012 treating the price
change as known), at the lower end of the paper's −0.08 to −0.135 own-price range (a different object).

**Caveats the numbers themselves show (not new tests):** (i) the **afternoon mid-peak block's DDD is built from the weekend arm** (working days −0.56, weekends +3.26),
so its pass on rule 4 does not say working-day load fell in proportion to the price; the dose-response is therefore weaker than the table's elasticities look;
(ii) the **morning peak (10–13h)** has the same price rise as the evening peak and shows about none (−1.1, elasticity −0.018): the effect is concentrated in
the evening (heterogeneity by time of day, not resolved); (iii) the working-day and weekend arms both fall under France (−15.8 / −11.5) because France's
control moves a lot in 2021; only the contrast between the arms is stable; (iv) the threats listed in the pre-registration (the evening energy price, small
businesses, one summer, restriction dates) are untested. **Next test, not run: the charge fell in September and October 2021 (peak 133 → 82 → 32 EUR/MWh), so the
same hours should show a smaller effect then, in proportion to the smaller price change; extending the post window to December would test the
charge, separately from the energy price, and needs registering first.**

## Pre-registration: the charge-cut dose-response (2026-11-11, written before any run of it)

**Status: pre-registered, not run.** The question the evening-peak result leaves: is the response to the *charge* the reform introduced, or to the
evening *energy* price, which also rose in 2021? The system charges changed inside the post period, which separates them.

**The natural experiment.** ESIOS 1876 (charges component, EUR/MWh) for working-day peak hours: **133.1 from June to 15 September 2021, 31.5 from 16
September to 31 December** (off-peak 6.0 → 0.9, mid-peak 41.8 → 21.4), the government's cut of the system charges (RDL 17/2021, in force 16 September, the same date
as the electricity-tax cut, which scales every price alike and moves no relative price). The old flat charge was 44.0, so the evening peak's price relative to night
rose by about +0.61 in ln points before 16 September and by about +0.2 after. The wholesale evening price spread was larger in the autumn, not smaller.
**If households respond to the charge, the effect should be about a third as large in the second window. If they respond to the evening energy price
(or anything else that grew in the autumn), it should not shrink, and may grow.**

**Design.** E0 (ESIOS 1201), evening peak 18–21h against night 0–7h, working days against weekends and holidays, hour, weekday and month effects, clustered by
week, **V2 pre-window** (2018-01-01 → 2020-12-31 without March–June 2020; January–May 2021 out). Two post windows, each estimated against that same pre-window with
the other window's days removed: **A = 2021-06-01 → 2021-09-15** (high charge), **B = 2021-09-16 → 2021-12-31** (low charge). Controls: Portugal (primary) and France. Also the LASSO
prediction errors (V3 of the evening-peak design, Portugal), trained on the same pre-window. The change in ln relative price in each window is computed day by day from
ESIOS 1001 and 1876 for the evening-peak hours against night, as in `analysis/tou_evening_ddd.py`, over the window's working days; elasticity = DDD / that change. Monthly
DDDs inside the windows (Jun, Jul, Aug, 1–15 Sep, 16–30 Sep, Oct, Nov, Dec) reported for the path.

**Stop rules, in order.**
1. **Sign.** The DDD is negative in A and in B under Portugal and under France (a positive or zero B means the effect is not there in the autumn, and the evening-peak
   result is read as summer-specific).
2. **Smaller in B.** |DDD_B| is smaller than |DDD_A| by at least two standard errors of the difference (independent windows). If not, the effect does not scale down
   with the charge.
3. **Proportional to the price change.** DDD_B / DDD_A lies within a factor of two of the ratio of the two windows' price changes (Δ_B / Δ_A, expected about 0.3).
4. **Elasticity stable.** The elasticity in B is negative and within a factor of two of the elasticity in A.
5. **LASSO agrees.** The LASSO version has the same sign in both windows and the same ordering |B| < |A|.
6. **No month in B above A's mean.** No monthly DDD in B exceeds in absolute size the mean of A's monthly DDDs.

**What each outcome means.** All six pass: the evening-peak response tracks the charge, not the energy price, and the elasticity of about −0.09 is a response to the
policy's price. Rule 2 fails with B as large as A or larger: the response is not to the charge (the evening energy price, or something that grew in the autumn of 2021
such as the pandemic recovery of evening activity, explains it). Rule 1 fails: summer-specific. Rules 3 or 4 fail with 2 passing: the effect shrinks but not in proportion
(partly habit, partly price).

**Threats that remain even if all pass.** (a) Autumn is not summer: the month effects come from 2018–2020, so a change in the seasonal shape of Spain relative to the control in
2021 is not removed; (b) the autumn 2021 price crisis changes behaviour through the energy bill generally; (c) the December holidays are only partly in the holiday indicator
(national holidays only); (d) two windows, one year; (e) the 16 September cut also reduced the system charges for every other period, so the whole structure shifts, not only
the peak.

## Planned follow-ups, written down 2026-11-11 before the charge-cut run (not run, not pre-registered in detail)

Order agreed with the user: charge-cut test first (registered above), then these. One thread at a time.

1. **Extended window, two channels at once (answers the energy-price-versus-charge question).** After 16 September 2021 the system charges stay fixed while the evening
   energy-price spread varies widely (2022 crisis, 2023–24 normalisation). Regress the monthly evening DDD on (a) the evening-versus-night charge gap and (b) the
   evening-versus-night energy-price gap (ESIOS 1001), both in ln of the relative price. Window capped at 2024 (the 2025 blackout and price changes are out); same V2
   pre-window; Portugal and France controls and LASSO. New confounds to state in the rules: the gas cap (June 2022), tax cuts, drift from rooftop solar and migration.
   Detailed stop rules to be written before the run.
2. **Seasonal-shape threat, bounded not removed.** (a) Industry E1–E6 evening-versus-night with the same design as a placebo (not on the new tariff); (b) the same
   calendar dates in 2018, 2019 and 2020 as fake reforms (partly in the placebo ranking already); (c) 2021 restriction and curfew dates as indicators. A new Spain-only
   change in evening habits cannot be fully removed; this triangulates it.
3. **Afternoon and morning blocks.** Afternoon: the weekend arm moves before the reform, so detrend it on its own pre-period, or drop it and use Portugal and France
   only for that block, and see whether the effect survives. Morning peak: near zero is read as a finding (people at work, little room to shift), reported with the
   evening block as a "who can shift" result, not as a defect.

## Results of the charge-cut dose-response (2026-11-11, run after the user's go-ahead; `analysis/tou_charge_dose.py`, `outputs/tables/tou_charge_dose_{main,path}.csv`)

DDD of the evening peak (18–21h against night, working days against weekends), E0, V2 pre-window. A = 2021-06-01 → 09-15 (high charge), B = 2021-09-16 → 12-31 (low charge).

| control | window | DDD % (se) | t | Δ ln relative price | elasticity | LASSO DDD % (se) |
|---|---|---|---|---|---|---|
| Portugal | A | −5.46 (0.77) | −7.1 | +0.673 | −0.081 | −5.22 (0.72) |
| Portugal | B | −1.55 (0.73) | −2.1 | +0.135 | −0.115 | −1.07 (0.73) |
| France | A | −4.78 (0.72) | −6.6 | +0.673 | −0.071 | not run |
| France | B | −0.51 (1.13) | −0.5 | +0.135 | −0.038 | not run |

Monthly path (Portugal, DDD %): Jun −4.3, Jul −7.3, Aug −5.0, Sep 1–15 −5.2, Sep 16–30 −3.8, Oct −2.2, Nov −1.7, Dec 0.0 (se 1.9).

**Stop rules, in order.** (1) Sign: negative in A and B under both controls, **pass** by the letter (France B is −0.51, t −0.5, statistically zero). (2) Smaller in B: Portugal
3.91 points smaller, se of the difference 1.06 (3.7 se), France 4.27 against 1.34 (3.2 se): **pass**. (3) Proportional: Portugal B/A 0.284 against Δ ratio 0.201 (ratio 1.4), France 0.106
(ratio 0.53): **pass**, France at the edge of the factor-of-two band. (4) Elasticity stable: Portugal −0.115 against −0.081 (ratio 1.4), France −0.038 against −0.071 (0.53): **pass**, same edge for France.
(5) LASSO: same sign, |B| 1.07 < |A| 5.22: **pass**. (6) No month in B above A's mean (5.46): largest B month is 3.83: **pass**. **All six pass.**

**Reading.** The effect shrinks when the charge is cut, about in proportion (ratio 0.28 against 0.20 expected), so the evening response tracks the charge, not the autumn
energy-price spread, which was larger. The elasticity is about −0.08 to −0.12 in both windows. **Caveats:** the B window's price change is small (0.135), so B's elasticity is
imprecise (−0.115, se about 0.054) and the proportionality test has little power to reject other shrinkage; France's B effect is zero and its elasticity is at the edge of the band; the
fall is gradual, not a step at 16 September (Sep 16–30 is −3.8, above the −1.6 a proportional drop would give, and it keeps falling through December), which is also what a
fading summer habit, autumn seasonality or the shifting seasonal shape (threat a) would produce; France's working-day and weekend arms are individually large (−16%, −12%) and only their
difference is read. The extended two-channel regression (follow-up 1) is the test that separates these.

## Pre-registration: the extended two-channel regression (written 2026-11-11 before any run; follow-up 1)

**Status: proposed, not run.** The charge-cut test (above) showed the evening effect shrinks when the charge falls, but only two windows from one year, and the fall was gradual.
After 2021 the charge schedule is fixed while the evening energy-price spread swings (2022 crisis, 2023 normalisation), so the two channels can be told apart on a longer panel.

**In one example.** Suppose in July 2022 the evening energy price is three times the night price but the charge gap is the same as in November 2021. If the evening effect is bigger in
July 2022 than in November 2021, households are responding to the energy price. If it stays at the November size, they respond to the charge. Doing this for every month and
asking which of the two price gaps the monthly effects follow is the test.

**Design.** Monthly DDD (evening 18–21h against night, working days against weekends and holidays, E0 against Portugal, V2 pre-window 2018-01-01 → 2020-12-31 without March–June
2020), one estimate per month **2021-06 → 2023-12 (31 months)**, each month estimated against the pre-window alone, as in `analysis/tou_charge_dose.py` (`estimate`). 2024 is out
(PVPC energy term partly forward-priced, price-triggered tax steps), and so are 2025–26 (blackout, quarter-hour prices). ESIOS 1876 (charges) must cover the window; if it does not, the window
is cut at its last day and that is stated.
Two regressors per month, from ESIOS 1001 and 1876 over the month's working days, evening against night, each a change in ln relative price against the old flat charge of €44/MWh:
- **x_charge** moves with the charges only: the ln relative price with the day's actual charges and the energy terms held at their whole-window means, minus the same with the old flat charge.
- **x_energy** moves with the energy term only: the ln relative price with the day's actual energy terms and the charges held at their October–December 2021 means, minus the same with the old flat charge.

Regression: DDD_m = a + ε_c · x_charge,m + ε_e · x_energy,m + u_m, OLS with Newey–West standard errors (3 lags); the version weighted by 1/se_m² reported beside it. Same regression with France as the
control. LASSO errors (Portugal) as a third version, same regressors. **Placebo outcome:** industry (E1–E6) − Portugal with the same design and regressors.

**Stop rules, in order.**
1. **Identification.** The correlation between x_charge and x_energy is below 0.7 in absolute value and each regressor's standard deviation over the 31 months is at least 0.05 (ln points). If not, that
   channel is not identified and the extension stops with that statement.
2. **Charge channel.** ε_c is negative with t ≤ −2 (Portugal, OLS, Newey–West) and lies within a factor of two of the charge-cut test's elasticity, between −0.18 and −0.045.
3. **Energy channel does not carry it.** Not (ε_e negative with t ≤ −2 and |ε_e| ≥ |ε_c|). If it is, the response is to the energy price, and the charge-cut result was a correlation.
4. **Controls agree.** The France version and the LASSO version have ε_c ≤ 0, and the weighted version has ε_c negative.
5. **Placebo.** Industry's ε_c has |t| < 2. If not, ε_c is read as a shape change shared with industry, and rules 2 to 4 are not read.
6. **Drift.** With a linear time trend (months since June 2021) added, ε_c keeps its sign and stays below −0.02. If it flips or vanishes, the charge channel cannot be separated from slow drift
   (rooftop solar, migration, habit), and that is the stated conclusion.
7. **High energy spread without a large effect.** No month in the top quartile of x_energy that is also past the charge cut (from 2021-10) has a DDD larger in absolute size than the
   summer-2021 mean (5.46%, charge-cut test window A).

**What each outcome means.** All seven pass: the evening response follows the charge, not the energy price, over three years, and the elasticity is about −0.1. Rule 3 fails: the energy price
drives it. Rule 6 fails alone: the sign agrees but the extension cannot rule out drift. Rule 1 fails: not identified, and the charge-cut test stays the only evidence.

**Threats that remain even if all pass.** (a) The 2022 energy crisis changes household behaviour through the bill in general (saving), not only through the evening gap; (b) E0's regulated share fell as customers
migrated to the free market, and free-market contracts may carry their own time structure, so the exposed share is not constant over three years; (c) rooftop solar and self-consumption grow in the window;
(d) the gas cap (June 2022) and the VAT and electricity-tax steps move price levels, not the relative price, but change the bill; (e) the pre-window is still 2018–2020, so a changing seasonal shape is not removed
(follow-up 2 bounds it); (f) 31 monthly points with regressors that move in few episodes.

## Results of the extended two-channel regression (2026-11-11, run after the user's go-ahead; `analysis/tou_extended.py`, `analysis/tou_lasso_paper.py`, `outputs/tables/tou_extended_{months,coef}.csv`)

**Data fix first.** ESIOS 1876 (charges) stopped at 2021-12-31 on disk; fetched 2022-01 → 2023-12 and merged (backup kept; the fetcher overwrites the parquet with the requested range, as before). **The pre-registration's premise
that the charge schedule is fixed after 2021 was wrong:** the peninsular evening-peak charge was 31.5 in Oct–Dec 2021, **100.8 in Jan–Mar 2022, 74.4 in Apr–Dec 2022 and 73.0 in 2023**. So x_charge moves after 2021 as well, but by little: the
monthly x_charge is 0.46 (summer 2021), 0.31 (Sep), 0.14 (Oct–Dec 2021), 0.36–0.38 (Q1 2022), 0.28–0.30 (rest of 2022–23); its standard deviation over 31 months is 0.077, and **0.030 from 2022 onward**. Industry's 2021-06 estimate is missing; that month drops out of
the industry regressions.

**Pre-registered rules, as written (OLS on the monthly DDD, Portugal):** correlation of the regressors 0.08, sd 0.077 and 0.074: rule 1 pass. ε_charge −0.119 (t −2.94), within −0.18 to −0.045: rule 2 pass. ε_energy −0.010 (t −0.44): rule 3 pass.
France ε_c −0.148 (t −4.0), pooled-LASSO ε_c −0.126 (t −3.4), weighted −0.092 (t −2.3): rule 4 pass. Industry ε_c −0.137 (t −1.31): rule 5 pass by the letter. Trend added: ε_c −0.097 (t −4.4): rule 6 pass. High-energy-spread months after the cut have |DDD| of
1.2–3.3% against 5.46%: rule 7 pass. **All seven pass as written.**

**But three things weaken it, found after the run:**
1. **The paper's LASSO.** The user set the paper's first step as the guiding method after the registration. `tou_lasso_paper.py` follows it: one model per area and hour, month/weekend/holiday dummies, the hour's, daily-minimum and daily-maximum temperature and all
   their interactions, 10-fold cross-validation with the one-standard-error rule, no trend, trained 2018–2020 without March–June 2020. The earlier "LASSO" was one pooled model with a trend and 4-fold time-series cross-validation. Pre-reform in-sample DDD of the errors is
   0.14% (se 0.19), so the first step is clean. Evening-peak DDD of the errors: Jun–Sep 2021 **−3.79%** (se 0.39; pooled version −4.96, DDD −5.25); window A **−3.94%**, window B **−2.46%** (se 0.60). So B/A is 0.62 against a price-change ratio of 0.20, and the elasticity is
   −0.06 in A and −0.18 in B: **the charge-cut test's proportionality and stable-elasticity rules (3 and 4) would fail under the paper's LASSO** (a factor of three). In the extension, ε_charge is **−0.052 (t −1.44)** (weighted −0.063, t −1.69; with trend
   −0.020, t −1.67) and **ε_energy −0.053 (t −2.23)**, −0.103 (t −5.1) with the trend. Under the paper's LASSO rule 2 fails on t, rule 3 fails by a hair (ε_energy negative, t ≤ −2, |ε_e| ≥ |ε_c|), and rule 6 is borderline. The industry placebo's paper-LASSO
   coefficients are not significant (−0.046, −0.061).
2. **The charge channel rests on summer-to-autumn 2021.** Exploratory, not pre-registered (months from 2022-01 only, 24 points, DDD version): ε_charge **+0.015 (t 0.26)**; from 2021-10: −0.035 (t −2.0). Where the charge moved after 2021 (Jan 2022 up, Apr 2022 down) the evening
   effect did not follow. The extension is therefore not independent of the charge-cut test: it re-uses the same seasonal transition.
3. **The industry placebo is weak.** Its ε_charge (−0.137) is as large as E0's (−0.119) and insignificant only because it is noisy; its energy coefficient is +0.196 (t 3.1) on the DDD, so the evening/night shape of other demand does move with these prices.

**Verdict.** The reform lowered evening relative demand in summer 2021: −4% (paper's LASSO) to −5.5% (DDD), t above 6 under every estimator and control. That the response is to the **charge** price (an elasticity near −0.09) is not established: the dose-response rests on one
seasonal transition, the longer panel gives no independent support, and the paper's LASSO halves the charge coefficient and brings in the energy channel. Read the elasticity as an upper bound of about −0.1 pending better separation of the autumn habit and season effects.

## Pre-registration: charge-change events against the seasonal baseline (written 2026-11-11 before any run; the cleaner test promised after the extension)

**Status: proposed, not run.** Aim: separate the response to the charge from the season and habit changes that move with it. The extension's charge coefficient rested on summer-to-autumn 2021, where season and charge move together.

**In one example.** On 1 January 2022 the evening-peak charge rose from €31.5 to €100.8/MWh, while the evening-versus-night energy-price gap stayed about where it was (monthly x_energy 0.12–0.14 in Q4 2021, 0.09–0.12 in Q1 2022; x_charge 0.14 → 0.36). If households respond to the charge, the evening
effect should deepen at that date by about ε × 0.22 (about −1.3% to −2.6% for ε between −0.06 and −0.12). If the earlier fade in autumn 2021 was season or habit, nothing of the sort happens in January, and the autumn comparison in earlier years shows what the season alone does.

**Estimator: the paper's LASSO** (`analysis/tou_lasso_paper.py`: one model per area and hour, month/weekend/holiday dummies, hourly, daily-minimum and daily-maximum temperature and all interactions, 10-fold cross-validation with the one-standard-error rule, no trend), Portugal as the control area, DDD of the prediction errors: evening peak 18–21h against night 0–7h, working days against weekends and holidays, standard errors clustered by week. Real events use the model trained on 2018-01-01 → 2020-12-31 without March–June 2020.

**Events (each is a change in the DDD between two windows):**
- **E1, the cut:** pre 2021-07-16 → 2021-09-15, post 2021-09-16 → 2021-11-15. Expected: the effect shrinks (change positive); expected Δx_charge about −0.3.
- **E2, the rise (the clean one):** pre 2021-10-01 → 2021-12-31, post 2022-01-01 → 2022-03-31. Expected: the effect deepens (change negative); expected Δx_charge about +0.22.
- **E3, the partial cut of 1 April 2022:** pre 2022-01-01 → 2022-03-31, post 2022-04-01 → 2022-06-30. Reported only (Δx_charge about −0.07, too small to read).
Daily x_charge and x_energy are computed as in `tou_extended.regressors` (working days, evening against night), averaged over each window.

**Seasonal baseline (placebo calendars).** The same calendar windows in 2018 and 2019 for E1 (pre 07-16 → 09-15, post 09-16 → 11-15), and for E2 Q4 2018 → Q1 2019 and Q4 2019 → Jan–Feb 2020 (March 2020 and later are COVID). Their prediction errors are **cross-fitted**: the errors of year Y come from the models trained on the other years of 2018–2020 (without March–June 2020), so each placebo year is out of sample; the placebo year's data enter no model that predicts it. This gives placebo models two years of training data against three for the real events (stated).

**Stop rules, in order.**
1. **Eligibility.** For each event, |Δx_charge| ≥ 3 × |Δx_energy| (window means). An event that fails it is not read (a charge event that moves the energy gap as much is not a charge-only event). E2 must pass; if it does not, the test stops with that statement.
2. **Sign and size of E2.** The E2 change is negative with t ≤ −2 (se = the two windows' standard errors combined, independent windows).
3. **Beyond the season, E2.** The real E2 change is more negative than both placebo E2 changes.
4. **E1 in the opposite direction.** The E1 change is positive with t ≥ 2 and above both placebo E1 changes.
5. **Same elasticity from both events.** Placebo-adjusted implied elasticity = (real change − mean placebo change) / Δx_charge. The E1 and E2 values both negative and within a factor of two of each other.
6. **Pooled.** The inverse-variance pooled implied elasticity is negative with t ≤ −2.

**What each outcome means.** All pass: two opposite charge moves, each against its own seasonal baseline, move the evening effect the way the charge channel predicts, and the elasticity is the pooled value. Rule 2 or 3 fails while E1 passes: the autumn fade was season or habit, and the elasticity is not identified from
the charge. Rule 1 fails for E2: not testable. E1 passes and E2 fails: the response is asymmetric (habits formed in summer persist when the charge rises) or the January change is too small to see; stated, not resolved.

**Power and threats.** E2's predicted change (−1.3 to −2.6%) is near what three-month windows can detect (standard error of the change about 0.7); a non-rejection may be low power, which the pooled value (rule 6) reports. Only two readable events. E2 falls in winter, with Q1-specific weather and the 2022 energy-price and tax measures; the placebo calendars share the season but not 2022's circumstances; the cross-fitted models are trained on two years, not three; autumn 2021 is also the return of
evening activity after the restrictions, which the placebo years do not have. The conclusion is about direction and rough size, not a precise elasticity.

## Results of the charge-change events test (2026-11-11, run after the user's go-ahead; `analysis/tou_events.py`, `outputs/tables/tou_events.csv`)

Paper-style LASSO errors, E0 minus Portugal, DDD of the errors (evening 18–21h against night, working days against weekends and holidays). Change = DDD after minus DDD before, percentage points; placebo years cross-fitted (leave-year-out).

| event | DDD before | DDD after | change (se), t | Δx_charge | Δx_energy | placebo changes 2018, 2019 |
|---|---|---|---|---|---|---|
| E1 cut, 2021-09-16 | −3.56 | −2.44 | **+1.12 (0.58), t 1.9** | −0.32 | −0.06 | +0.92, **+2.75** |
| E2 rise, 2022-01-01 | −2.43 | −2.98 | **−0.55 (1.09), t −0.5** | +0.23 | −0.02 | −1.28, −0.46 |
| E3 partial cut, 2022-04-01 | −2.98 | −1.79 | +1.19 (1.07), t 1.1 | −0.07 | −0.00 | not run (reported only) |

Stop rules. (1) Eligibility: |Δx_charge| ≥ 3 × |Δx_energy| holds for E1 and E2 (E2: 0.23 against 0.02): **pass**. (2) E2 negative with t ≤ −2: **fail** (−0.55, t −0.5). (3) E2 below both placebo years: **fail** (placebos −1.28 and −0.46). (4) E1 positive, t ≥ 2, above both
placebos: **fail** (+1.12, t 1.9; the 2019 placebo is +2.75). (5) Both implied elasticities negative within a factor of two: **fail** (placebo-adjusted +0.022 (se 0.027) and +0.014 (se 0.057)). (6) Pooled elasticity negative with t ≤ −2: **fail** (+0.021, se 0.024, t 0.9). **Rules 2 to 6 fail.**

**Reading.** The autumn fade of the evening effect is what the season does anyway: the same calendar windows in 2019 move by +2.75 points with no reform (2018: +0.92), more than the real +1.12. And when the charge rose by 0.23 in January 2022 with the energy gap flat (the cleanest event), the evening effect
did not deepen by more than the seasonal change in earlier years does (−0.55 against placebos −1.28 and −0.46). Placebo-adjusted, the charge elasticity is statistically zero (+0.02, se 0.02) with a one-standard-error band of about −0.03 to +0.05 under this design. **The dose-response of the charge-cut test (A against B) is a seasonal pattern, not evidence for the charge channel.**
The June 2021 reform effect itself (−4% in summer 2021 under the paper's LASSO) is not tested by this and stays, but it cannot be attributed to the charge price.

**Cautions.** (a) The cross-fitted placebo windows show large swings of their own (DDD levels from −1.2 to +2.6 in the same summer windows; models trained on two years, not three), so the summer-2021 effect of −3.6 is 1.4 to 6 points below the placebos' summer levels, within about two of their spread; (b) power: E2's se of 1.1 points cannot rule out the −1.3 to −2.6 predicted at ε between −0.06 and −0.12 (t −0.5 here, the 2019 placebo of −0.46 is similar), so E2 alone is uninformative and the pooled band is what bounds ε; (c) only two readable events.
(d) **The industry placebo of the extension is flawed by design:** the June 2021 access-tariff reform changed the period structure for all consumers (2.0TD low voltage, 3.0TD and 6.xTD above), so industry is also treated, not a control. This is to be confirmed against the CNMC circular before it is cited.
