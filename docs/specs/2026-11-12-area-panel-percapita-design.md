# Area-panel replication per consumer, with the CNMC counts

**Status: pre-registered 2026-11-12, before any estimation with the counts.** Branch `tou-policy-prices`. Follows `2026-11-12-area-panel-design.md` (results section: rules 2, 3, 4 and 7 failed in levels because the Portuguese regulated unit drifts without per-capita counts; peak minus off-peak was -6.9 points post hoc). Counts: `outputs/tables/cnmc_regulated_points_quarterly.csv` (CNMC retailer-switching reports, read by hand; `docs/tou-policy-sources.md`).

**In one example.** Endesa's regulated retailer bought 1,086 MW on average in June 2019, but its regulated customers fell from 5.19 million (March 2018) to 4.37 million (December 2021). A fall in load of 16% over that time would be consumers leaving, not use per household. The paper divides by the number of regulated consumers; we can now do the same for the five Spanish areas.

**Goal.** Rerun the area-panel replication with log load per regulated domestic supply point, so that migration out of the regulated tariff no longer enters the errors. **Not goals:** industry; a new elasticity target; anything after 2021-09-14.

## Data
- Spanish areas: P48 hourly load (`regulated_area_p48_hourly.parquet`) divided by the area's regulated domestic supply points. Counts: quarter-end values 2018-03-31 → 2021-09-30 (Q4 2021 not needed), interpolated to daily with a monotone cubic (PCHIP, the paper's Fritsch-Butland family), no extrapolation: **the sample starts 2018-04-01**.
- Portugal: the paper uses ERSE's monthly bulletins (consumers in the regulated and liberalised segments). **Not on disk.** Two versions: **(M) main, if the Portuguese counts are obtained before the run:** Portuguese regulated unit per consumer; **(F) fallback, run now:** Portuguese national consumption (REN) with no counts (migration does not move a national total), reported as the main version only if (M) is unavailable.
- Weights: the area's mean regulated supply points over the pre-window (the paper weights by consumers); unweighted beside.

## Design
As the area-panel design: per-area-hour paper LASSO (`tou_lasso_paper.area_errors`) on log load per consumer, trained 2018-04-01 → 2020-12-31 without March-June 2020; errors on post x Spain x period type (weekday peak, mid, off; weekend fake types) with area x hour x weekend and month-of-sample x weekend effects, area x month-of-sample clusters; post window 2021-06-01 → 2021-09-14; 21 placebo windows of 106 days with cross-fitted errors (2018 sample starts 2018-04-01, so placebo window starts run 2018-05 → 2019-09, **19 windows**); the paper's Equation 4 with columns 1 to 4.

## Stop rules, set before the run
1. **Counts valid.** The six groups' counts sum to at least 99% of the CNMC's regulated total in each Q1 (checked: 99.1%, 99.5%, 99.9%, 99.9%) and load per consumer shows no break larger than 10% between consecutive quarter-ends in any area outside the reform months.
2. **Period effects (weekday, area-weighted).** Peak negative, t <= -2, between -3% and -15%; mid-peak negative, t <= -2; off-peak absolute effect below 3%.
3. **Placebo.** The real weekday peak effect ranks in the top 3 of the 19 placebo windows by absolute size; the elasticity placebo has t > -2.
4. **Areas.** Weekday peak negative in at least four of five Spanish areas.
5. **Elasticity.** Column 4: negative, t <= -2, in [-0.20, -0.05], first-stage F >= 10.
6. **Consistency with 352.** The pooled evening-versus-night triple difference is within 1.5 points of the 352 value, as in the previous design (unchanged by counts: a level cancels in a contrast).
7. **Robustness.** Dropping Endesa, unweighted weights, the PDBF stage, and the control swap (regulated unit versus REN) each move the weekday peak effect by less than 2 points; **counts shifted by plus or minus 0.5 points of regulated share in 2018 and 2019 (the rounding of those reports)** move it by less than 1 point; **dropping the Q3 2019 counts (a figure that looks carried forward) and interpolating across it** moves it by less than 1 point.
8. **The counts do what they are for.** The standard deviation of the weekday off-peak (level) effect across the 19 placebo windows falls by at least half relative to the version without counts (that version: placebo weekday off-peak effects ran from -8.2 to +8.9 points).

## What each outcome means
Rules 2, 3, 4, 7 and 8 pass: the paper's design reproduces on its own unit of observation with its own normalisation; the area-panel result becomes the main replication and E0 the extension to all low-voltage customers. Rule 8 fails or is partial: the level drift is not only migration (Portuguese unit, hours or weather), stated as such. Rules 2 or 3 still fail with rule 8 passing: the replication does not hold on schedule data and E0 remains the headline. Version (F) alone cannot show that the Portuguese unit is fixed; rule 8 is then read for the Spanish areas against REN, and the claim is limited to that.

## Threats
The counts are domestic regulated points of each group, rounded to a whole percent in 2018-19 and to a decimal from Q4 2019 (rule 7 bounds this); the Q3 2019 figure may be carried forward; the CNMC counts supply points, the paper's counts consumers (the same unit here, one supply point per consumer for domestic customers); quarter-end counts interpolated to daily smooth the real path, which is faster in the second half of 2021 (Endesa regulated points fall 4% in Q3 and 4% in Q4 2021); the group's regulated points include its PYME and industrial points (under 1%); weather is national (as before); schedule data, not metered load.

## Results (run 2026-11-12, `scripts/analysis/tou_area_panel_pc.py`)

Outputs: `outputs/tables/tou_area_panel_pc_{effects,placebo,elasticity,ddd}.csv`. Version M (Portuguese regulated unit per consumer, ERSE counts) is the main one; F (REN national, no counts) beside it. Deviations from the registration: there are **18** placebo windows (starts 2018-04 to 2019-09), not 19; "rank 2 of 19" counts the real window among them. Portuguese gaps (Jul-Dec 2020, Mar-Apr 2021) are bridged by PCHIP interpolation.

| rule | outcome |
|---|---|
| 1 counts valid | **pass** (largest quarterly change 5.0%; sums 99.1-99.9%) |
| 2 period effects (M, weighted) | **pass**: weekday peak -7.76% (t -7.6), mid -5.59% (t -5.5), off-peak -0.86% (t -0.6) |
| 3 placebo | **pass**: real peak effect ranks 2 of 19; elasticity placebo eta +0.022 (t 1.36) |
| 4 areas | **pass**: 5 of 5 negative |
| 5 elasticity, column 4 | **pass**: -0.086 (se 0.014, t -6.3, F 872). Columns 1-3: -0.013, -0.021, -0.018 (t > -1), as on the national series |
| 6 consistency with 352 | **pass**: 0.32 points |
| 7 robustness | **FAIL**: drop Endesa 0.55, unweighted 0.11, PDBF 0.49, share ±0.5: 0.90/0.92, drop Q3 2019: 0.06 all within bounds; **the control swap to REN moves the peak effect by 4.57 points** (-7.76 to -3.19) |
| 8 counts fix the level drift | **FAIL**: placebo sd of weekday off-peak effect 4.68 pts without counts, 6.23 (M), 3.66 (F); needed at most 2.34 |

Reading. The replication now reproduces in its own units: rules 1-6 pass, peak-minus-off-peak is -6.9 points under either control, and column 4 gives -0.086, the same as on the national series. What does not hold is the level: against REN the peak effect is -3.2% with off-peak +3.7%, against the Portuguese regulated unit -7.8% with off-peak -0.9%, so the *level* of the effect depends on the control while the contrast (peak minus off-peak, evening versus night) does not. Rule 8 fails: dividing by counts did not reduce the placebo spread of level effects for the Portuguese-unit version (it rose); the level drift is therefore not mainly migration. The F version's sd of 3.66 is smaller than without counts but not by half. Not rescued. Consequence: the elasticity from the contrast (evening versus night; column 4) is supported on three data sets; any statement about the level of the weekday peak effect is not. The headline stays the Wald range with column 4 beside it.
