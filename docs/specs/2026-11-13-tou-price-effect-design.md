# What the time-of-use shift did to the day-ahead price (pre-registration)

**Status: pre-registered 2026-11-13, before any price re-clearing with a demand shift.** Branch `tou-policy-prices`. Follows the sketch `2026-11-13-supply-side-extension-sketch.md` and the load replication (`2026-11-11-tou-replication-design.md`, `2026-11-11-tou-hardening-design.md`; area panel `2026-11-12-area-panel-percapita-design.md`, `2026-11-12-area-weather-design.md`). Nothing in this document has been estimated; step 0 (below) is a data check that does not involve the reform effect.

**In one example.** The load model says that on a June 2021 weekday low-voltage customers used about 4% less at 20:00 than they would have, and a little more at night. At 20:00 the day-ahead supply curve is steep (gas combined cycles at the margin), so a few hundred MW less demand takes some euros off the price; at 03:00 the curve is flat, so the same MW adds less. The replication measured the MW. The bid curves give the euros. Because only the shape of the shift across the day is identified, not its level, we fix the level by one stated assumption (the shift moves energy within the day, it does not create or destroy it) and bound it with the data.

## Goal
Measure, in €/MWh and in consumers' euros, the **mechanical** price effect of the estimated evening-to-night load shift in the 2021 reform window, holding each day's offers fixed. Secondary, weaker: whether firms' offers at the margin changed (R5). **Not goals:** a new load elasticity; rescuing any rule of the area panel; the CES / NLS estimator (its own specification, to follow); other countries; the supply-side behaviour beyond R5; anything after 2021-09-14.

## Data (all on disk)
- **Load shift.** The low-voltage (E0, ESIOS 1201) load against Portugal's consumption (REN), paper LASSO per hour, the series of `tou_lasso_paper.errors` used by the evening design; period types as in the replication: peak = hours 10-13 and 18-21, off = hours 0-7, mid = the rest; weekdays that are not holidays only. Effects `b_type` (log points) with their covariance from `tou_did`, post window **2021-06-01 → 2021-09-14**.
- **Curves.** The re-clearable effective curve by hour from `outputs/cache/step/hours_YYYYMM`, `market_YYYYMM` (`scripts/analysis/step_curves.py`; 2019-01 → 2025-09 on disk). Only hours with `valid` true, an unsplit market (ES = PT price) and a holding clearing identity enter; the 61 days of 2025 anomalies are outside the window.
- **Prices:** OMIE day-ahead `price_es`. **Cost for R5:** `implied_marginal_cost_daily` `_bid` columns, units of `units_YYYYMM`.

## Design
1. **Step 0, data check, no reform effect.** Share of weekday hours in the post window and in each placebo window that are `valid`, and the mean absolute error of the re-clear on them. Reported before anything else; rule R1.
2. **Counterfactual demand.** For each valid weekday hour h in type k, the shift is `ΔQ_h = (exp(b_k) − 1) × L̂_h`, with `L̂_h` the load model's counterfactual E0 MW (no reform). The level `c` common to all hours is fixed by the **energy-neutral normalisation**: `c` such that the sum over the 24 hours of a day of `ΔQ_h + c·L̂_h` is zero, with `c` the same constant across the day. Sensitivity: `c` equal to the levels implied by the Portuguese regulated unit per consumer (M) and by REN (F) controls (the two differ by 4.6 points in the weekday off-peak level; `tou_area_panel_pc_effects.csv`).
3. **Re-clearing.** The counterfactual price is the clearing price of the day's effective curve with the buy side moved by `−ΔQ_h` (the demand that would have been there without the reform; household demand is price-insensitive, so the move is horizontal). `Δp_h = p_actual − p_counterfactual`, with the actual price the re-cleared one (so that curve error cancels).
4. **Aggregation.** Mean `Δp` by type, and the **contrast** `Δp_evening − Δp_night` (hours 18-21 minus 0-7) over the post-window weekdays, with 95% intervals from 2,000 draws of `b_k` from their estimated covariance (the curve is treated as known).
5. **Consumers' euros** (reported, not a rule): `Σ_h Δp_h × L_h` over the window for E0.
6. **Placebo.** The identical pipeline in the windows of 106 days starting on the first of each month **2019-01 → 2019-09** (nine windows; the step cache starts in 2019-01, so the 2018 windows of the load placebo are not available; the load errors are the cross-fitted ones of the replication), with the same normalisation.
7. **R5 inputs.** Hours where a combined cycle with a plant-specific efficiency and a bid-time cost is the marginal unit; markup `m = its offer price − its cost (_bid)`; contrast `m_evening − m_night` in the post window less the same in the same calendar days of 2019 and 2020 (outside the lockdown).

## Rules, set before the run
- **R1 The curve is valid.** At least **70%** of post-window weekday hours are `valid`, and the re-clear's mean absolute error on them is at most **€0.50/MWh**. Fail: stop; the mechanical effect is not reported as a result, only as an exploration.
- **R2 Sign and size.** The contrast `Δp_evening − Δp_night` is **negative, its 95% interval excludes zero, and its magnitude lies between €0.50 and €20/MWh**. Both the evening and night means are reported; the evening one must be negative.
- **R3 Placebo.** The real contrast ranks in the **top 2 of the 10** windows (nine placebo plus real) by absolute size, and its absolute value is at least **1.5 times the standard deviation** of the nine placebo contrasts.
- **R4 Level robustness.** The sign of the contrast is the same under the energy-neutral normalisation, the M level, the F level, excluding July (the offer limits changed on 2021-07-07: −€500 to €3,000 against €0 to €180.30) and excluding the first week of June.
- **R5 Behavioural (secondary).** The change in the evening-minus-night markup of the marginal combined cycle exceeds in absolute value the largest of the nine placebo changes, computed as in step 7. Not passing means **no detectable behavioural response**, not no response. Failing or passing says nothing about causes: the clawback announcement of 2021-06-01 falls on the reform date (the hydro offer departure stops then) and cannot be separated here.

## What each outcome means
R1-R4 pass: the reform lowered the evening price relative to the night by the estimated amount through the wholesale market, holding offers fixed, and the thesis can quote €/MWh and consumers' euros next to the paper's load elasticity; the offer-curve data become the extension's contribution. R1 passes, R3 fails: the load shift is too noisy in the placebo to be priced; report the point estimate with the placebo band and do not claim it. R4 fails on one normalisation: the sign depends on the unidentified level; report the range across the three levels and say so. R1 fails: stop and report the data limit. R5 is reported whatever happens. **No other specification is tried after a failure.**

## Threats
- The level of the load shift is not identified (control dependence); the contrast uses an assumption (energy neutrality) that rules R4 test but cannot prove.
- Counterfactual demand moves the buy curve horizontally: if part of the household demand is price-sensitive the shift is mis-sized; the effective curve contains a few price-sensitive bids, small in 2021 (direct consumers' stated sensitivity was 27-37% per €50 in 2018-2021 but they are about 6 TWh a year).
- Feedback through PVPC (the energy term is the day-ahead price) is ignored; its sign dampens the shift.
- Offers are held fixed by construction; R5 is the only check on that and is confounded.
- 106-day placebo windows overlap; nine windows give a coarse rank (top 2 of 10 is a 20% bar, as the 3 of 19 before).
- The post window ends 2021-09-14, before the gas crisis and before the levy decree of 14 September; hours after it are not used.
- Only the peninsula; Portugal's prices are separate in split hours, which are dropped.

## Outputs and scripts (written when run)
`scripts/analysis/tou_price_effect.py`; `outputs/tables/tou_price_effect_{hours,summary,placebo,markup}.csv`. The script reads the existing load-error series and the step cache and changes neither.

## Step 0 result (run 2026-11-13, a data check; no reform effect involved)
**R1 passes.** Post window 2021-06-01 → 2021-09-14, weekdays that are not holidays: **1,824 hours, 1,761 valid (96.5%)** against the bar of 70%. By block: evening 18-21 97.4%, night 0-7 96.5%, peak 10-13 98.7%. Excluding July 96.5%, excluding the first week of June 96.4%. The nine placebo windows (2019-01 → 2019-09) are 91.2% to 98.7% valid. Re-clearing over **all** 1,824 hours: 97.4% within €0.50 of the published price, median error 0.00, 95th percentile €0.27, largest €26.7; of the 63 invalid hours, 48 miss by more than €0.50 and 15 fail for another reason (a split market or the clearing identity).

**A flaw in the registration, found at this step, stated rather than hidden.** `valid` in `step_curves.py` is defined to include an error of at most `VALID_ERR` = €0.50, so "mean absolute error on valid hours is at most €0.50" is true by construction and carries no information (reported value €0.019). The informative figures are the share valid (96.5%) and the unconditional error above. The R1 bar is therefore read as **share valid at least 70%**, as passed; the MAE clause is vacuous and is dropped. This changes no other rule and is made before any price effect is computed.

Step 0 also fixes the sample: 1,761 valid weekday hours in the post window (304 evening, 608 night before excluding invalid ones). The placebo windows each have 1,752-1,800 weekday hours.

## Results (run 2026-11-13, `scripts/analysis/tou_price_effect.py`, outputs `outputs/tables/tou_price_effect_{summary,hours,placebo,markup}.csv`)
**R1-R4 pass; R5 (secondary) finds no detectable behavioural response.**

Load effects used (E0 against Portugal's consumption, weekday, window 2021-06-01 → 2021-09-14, 1,761 valid hours on 76 weekdays): peak −5.28%, mid −3.64%, off +1.43% (se 0.19-0.27 points). Gap between the regulated-unit (M) and REN (F) controls in the replication: −4.57 points.

| Level of the shift | Evening 18-21 | Night 0-7 | Contrast (evening − night) |
|---|---|---|---|
| energy-neutral (main) | −0.65 | +1.74 | **−2.39** [−2.60, −2.19] |
| REN level (F) | −1.50 | +0.55 | −2.05 [−2.26, −1.85] |
| regulated-unit level (M) | −2.81 | −1.12 | −1.69 [−1.86, −1.51] |
| excluding July | | | −2.41 |
| excluding the first week of June | | | −2.45 |

All in €/MWh, price actual minus price without the reform, weekdays. By hour (main level): night hours 0-4 about +2.0, hours 5-7 +1.6 to +1.0, daytime hours 8-9 about −0.2, the midday peak 10-13 −0.7 to −0.9, afternoon 14-17 about −0.3, evening 18-21 −0.6 to −0.8, late evening −0.2.

| Rule | Result | Verdict |
|---|---|---|
| R1 curve valid | 96.5% of weekday hours valid (bar 70%) | pass |
| R2 sign and size | contrast −2.39, interval excludes zero, evening −0.65, between 0.5 and 20 | pass |
| R3 placebo | real contrast ranks 1 of 10; placebo contrasts range −0.19 to +0.17 (sd 0.14); real is 17 times that sd (bar 1.5) | pass |
| R4 level robustness | contrast negative under the three levels, without July, without the first week of June | pass |
| R5 markup (secondary) | the evening-minus-night markup of the marginal gas unit is +5.31 in the window against +4.30 (2019 same days) and +4.81 (2020, July-14 September); the registered change is +0.75. Against the nine placebo windows (range 1.8 to 8.8): the real value departs from their mean by 0.51, the largest placebo departure is 3.97 | no detectable response |

**What it says.** The estimated shift moved the price by a few euros, not tens: the night price rose by about €1.7-2.0 and the daytime and evening prices fell by €0.2-0.9, so the evening fell relative to the night by €1.7-2.4 depending on the unidentified level. Net over the window, E0 energy times the price effect is **+€1.47 million (+€0.07/MWh)**: the shift moves cost from the evening and daytime to the night and nets to about zero in the wholesale market. The evening effect is not larger than the midday one, because the peak effect applies to both blocks.

**Limits and departures from the registration, stated.**
- **The intervals carry only the load-effect uncertainty** (se 0.2-0.3 points); they do not carry the level. The honest range for the contrast is the spread across the three levels, **−1.7 to −2.4**. The sign does not depend on it; the evening effect alone does (−0.65 to −2.81).
- **R5 as registered cannot be computed for the placebo windows**: the comparison years for a 2019 window are 2018 (not on the curve cache), 2020 (lockdown) or 2021 (after the reform). The decision uses the outlier test among windows, with the registered real-window change (+0.75) reported beside it. R5 is secondary and confounded by the clawback announcement of 2021-06-01; it says nothing about causes.
- **The load is E0 as measured at consumption, moved horizontally on the buy side at the market's hour**; network losses (a few per cent) are ignored, which understates the MW slightly.
- **The effective curve's top-priced buys are assumed to cover the removed demand** (in the night hours, where the counterfactual has less demand).
- 2,403 LASSO convergence warnings (duality gaps near 1e-3), of the kind the earlier runs gave; the errors are the paper's per-hour LASSO as before.
- The cache holds only days with 24 periods, so DST days are absent; none fall in the window (no DST change between 1 June and 14 September). Of 1,824 weekday hours, 63 are not valid; the other 1,761 are used.
