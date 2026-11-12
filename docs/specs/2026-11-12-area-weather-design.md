# Area-weather rerun of the per-capita area panel (pre-registration)

**Status: pre-registered 2026-11-12, before any estimation with the area weather.** Branch `tou-policy-prices`. Follows `2026-11-12-area-panel-percapita-design.md`, whose results section records rules 1-6 passing and **rules 7 and 8 failing**: the level of the weekday peak effect moved by 4.6 points when the Portuguese regulated unit was swapped for REN national consumption, and the placebo spread of weekday off-peak effects was 6.23 points per consumer (M) and 3.66 (F) against 4.68 without counts (needed: at most 2.34).

**In one example.** Naturgy's regulated customers in A Coruña and Vigo face a different temperature from Endesa's in Seville, but every area's load model was trained on one national temperature series. If Seville has a hot week while the national series is mild, Endesa's load looks unexplained and appears as a drifting off-peak "effect" in the placebo windows. The paper gives each area its own population-weighted MERRA-2 temperature. We now have it.

**Goal.** Test one explanation for the level drift: area-specific weather. **Not goals:** a new elasticity; rescuing rule 7 or 8 by any other change; anything after 2021-09-14.

## Change (the only one)
Everything is as the per-capita design (`tou_area_panel_pc.py`: same counts, PCHIP, weights, sample from 2018-04-01, paper LASSO with 10-fold one-SE, post window 2021-06-01 → 2021-09-14, 18 placebo windows 2018-04 → 2019-09, Equation 4 columns 1-4), except the temperature fed to each area's LASSO (hourly, daily minimum and maximum, with the paper's interactions):
- Spanish area *a* and its variants (PDBF, up/down, no-Q3-2019): MERRA-2 temperature of area *a* (`area_temperature_merra2_hourly.parquet`);
- Portuguese regulated unit (M) and REN national (F): MERRA-2 temperature of the Portuguese area;
- ESIOS 352 (the national check): the load-weighted mean of the five Spanish areas' MERRA-2 temperatures.
Hours are joined on the UTC hour start (MERRA-2's HH:30 stamp labelled by its hour). Holidays unchanged. The run is a new script, `scripts/analysis/tou_area_panel_pc_weather.py`, writing `tou_area_panel_pcw_{effects,placebo,elasticity,ddd}.csv` and a separate error cache; the existing outputs are not touched.

## Stop rules, set before the run
1. **Weather valid.** The MERRA-2 area series has no missing hour in 2018-04-01 → 2021-09-30 and correlates at least 0.9 with the ERA5 area series (checked at build: 0.94-0.99, no gaps).
2. **No regression.** Rules 2-6 of the per-capita design hold unchanged on version M: weekday peak negative, t <= -2, between -3% and -15%; mid negative, t <= -2; off-peak |effect| < 3%; real peak effect in the top 3 of the 19 windows; elasticity placebo t > -2; all five areas negative; column 4 negative, t <= -2, in [-0.20, -0.05], F >= 10; pooled DDD within 1.5 points of the 352 value.
3. **The drift falls (the test).** Standard deviation of the weekday off-peak (level) effect across the 18 placebo windows, version M: **pass if at most 2.34** (half of the no-counts 4.68, as registered before); **partial if above 2.34 but at most 4.15** (a fall of at least a third from the per-capita run's 6.23); **fail otherwise**. Version F reported with the same bars.
4. **The control gap closes.** Swapping the Portuguese regulated unit for REN moves the weekday peak effect by less than 2 points (previously 4.57).
5. **Peak effect stable.** The version-M weekday peak effect stays within 2 points of the previous -7.76%.
Diagnostics, not rules: pre-window residual sd of each area's LASSO against the national-temperature run; per-area placebo sd.

## What each outcome means
Rules 3 and 4 pass (rule 2 holding): area weather was the missing piece; the area-panel replication then stands on its own units, with the level no longer control-dependent, and the headline can cite it beside the Wald range. Rule 3 partial or rule 4 fails: weather explains part of the drift, the rest is the Portuguese unit or the schedule data; the contrast (evening versus night, column 4) remains the claim, as now. Rules 3 and 4 both fail: the drift is not weather; stop here and report the level as control-dependent, with the contrast and column 4 as the result. Rule 5 fails: the effect depends on the weather source, reported as a limit. **No further rescue is run under any outcome.**

## Threats
Weather per area is a few city points weighted by population with a hand-set assignment, not the paper's gridded areas (rule 1 bounds nothing about the assignment); MERRA-2 is a reanalysis; Madrid's split between Iberdrola and Naturgy (70/30) is approximate; 41 LASSO tasks again, so the run is as long as the previous one; the placebo windows overlap the training years as before (cross-fitted).
