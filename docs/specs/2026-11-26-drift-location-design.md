# Where does the placebo drift live? Area split and fixed-effect ladder (proposal)

**Status: proposed 2026-11-26, not registered, not committed. Binding when the user confirms and this file is committed;
the run follows that commit.** Nothing is refitted: every number comes from the cached leave-one-year-out LASSO errors
(`six_summer_errors.parquet`) with the existing estimators (`tou_cross_tariff.Fit`, `tou_industry_regulated_price.pooled_eta`).
Follows `2026-11-26-double-lasso-design.md` (D3 failed: year-specific shifts, not the learner, are the limit),
`2026-11-18-industry-regulated-price-elasticity-design.md` (trend null −0.15, mean null −0.32) and the open item of
`paper/revision.md` on the trend-null range and on why the replication range sits below E0 −0.11.

**What is not blind.** The pooled placebo betas of the industry design (2014 +0.232, 2015 +0.216, 2016 +0.183,
2017 +0.102, 2018 +0.024, 2019 +0.100; slope −0.038 per year) and the E0 placebos are known. A rolling-origin
comparison of trend against mean on those six numbers was computed after the fact (post hoc, 2026-11-26): trend errors
−0.059, −0.054, +0.108 (RMSE 0.077), mean errors −0.108, −0.159, −0.051 (RMSE 0.115). It is not a test and is not
repeated here. What is unknown: which area and which part of the fixed-effect structure the drift comes from.

## In one example
Industry's placebo effect falls from +0.23 in 2014 to about +0.05 in 2018-19 in summers with no reform. The estimator
compares Spain with Portugal inside each month. So the drift is either in Spanish industry's evening-versus-night
profile, in Portugal's, or in something the month fixed effects do not absorb. Which one decides how to read the range:
a real behavioural drift in Spain supports the trend null; a Portuguese control artefact points to a better control.

## Two parts, one script, cached errors only

### Part A: area split
For the pooled 6.2+6.3+6.4 (full dose, as the headline) and for E0, in 2021 and each placebo summer, three betas on the
same stack and fixed effects as the estimator:
- **baseline** η (Spain and Portugal blocks, dose on Spain only: unchanged estimator);
- **β_ES**: Spain's error on its dose, with fixed effects hour×weekend and weekend×month (no area terms, Spain rows only);
- **β_PT**: Portugal's error on the *same dose laid on Portuguese rows*, same fixed effects, Portugal rows only.
β_ES − β_PT is close to, but not the same as, the baseline (the baseline shares hour×weekend×month cells across areas);
all three are reported. Slopes per year over the six placebo summers by OLS.

### Part B: fixed-effect ladder
Starting from the baseline fixed effects (hour×weekend×area, hour×weekend×month, weekend×area×month), change one thing
at a time, for E0 and for the industry pool:
- **L0** baseline (reproduction);
- **L1** coarse level: the weekend×area×month term uses one label for all days inside the evaluated window (the whole
  June-September window is one level cell, other months unchanged);
- **L2** Spain only: Portugal rows dropped (hour×weekend×month cells are then estimated from Spain alone);
- **L3** L1 and L2 together (closest to the double-LASSO structure, learner aside).
Each rung reports η_2021, placebo mean, placebo sd, placebo slope per year.

## Rules, set before the run
- **R0 Reproduction (gate).** L0 reproduces the committed numbers to three decimals: industry pool η_2021 −0.17705,
  placebo mean +0.14286, sd 0.08083; E0 η_2021 −0.11572, placebo mean −0.00491, sd 0.03686. If not, stop and find why.
- **A1 Location of the drift (industry pool, full dose).** With s_ES = slope(β_ES)/slope(baseline) and
  s_PT = −slope(β_PT)/slope(baseline): the drift is *in Spain* if s_ES ≥ 0.75, *in Portugal* if s_PT ≥ 0.75, *shared*
  otherwise. Slope of the baseline must itself be negative and at least 1.5 times its OLS standard error, else the
  trend is not established and the answer is "no trend to locate".
- **B1 Level or shape (industry pool).** The trend is a *shape* drift if the placebo slope under L1 is within ±25% of the
  baseline slope; a *level* drift if it changes by more than 25%.
- **B2 What moves E0.** A rung moves the E0 estimate if |η_2021 − baseline| ≥ 0.018 (half the baseline placebo sd).
  The gap to the double-LASSO −0.082 is reported rung by rung; no rung is called the explanation unless it moves the
  estimate by at least 0.018 toward −0.082 and the later rungs do not reverse it.
No pass or fail is attached to B2 beyond this reading; any other specification is not tried after the run.

## What each outcome means
- A1 Spain and B1 shape: the drift is a real behavioural change in the evening-versus-night profile of industry. The
  trend null is the more defensible baseline, and the range −0.15 to −0.32 is reported as a sensitivity with this cause.
- A1 Portugal: the trend is a control artefact. Reopens the Portuguese control (memory: "Portuguese control open") with a
  concrete target: a control whose evening-versus-night profile does not trend.
- A1 shared or B1 level: the range cannot be narrowed by this route; report the range with the diagnosis.
- B2 answers the owed question (gap between E0 −0.116, the double LASSO −0.082 and the replication −0.06…−0.09), as a
  statement of which design choice moves the number, not as a claim that one is correct.

## Threats
Six placebo summers (three for E1+E2): slopes are imprecise and a rebound (2019) already bends the line; Spain-only
rungs drop the differencing that the headline relies on, so they locate sources of variation, not better estimates;
β_PT puts a Spanish dose on Portuguese hours as a placebo, so its level is not an elasticity.

## Data and code
Cached errors only; no new data. New script `scripts/analysis/tou_drift_location.py` (reuses `Fit`, `fe3`, `pooled_eta`);
outputs `outputs/tables/tou_drift_location_*.csv`. Expected run time minutes.

## Results (run 2026-11-26, `scripts/analysis/tou_drift_location.py`; `outputs/tables/tou_drift_location_*.csv`)
**R0 passes** (pool −0.1771 / +0.1429 / 0.0808; E0 −0.1157 / −0.0049 / 0.0369). Cached errors only. The log line "E0-E6 /
1193 in 2014: FAIL" is the existing data gate of the six-summer script (unchanged: 2014 stays clean for E0 and the 6.x series).

| set | rung | η 2021 | placebo mean | placebo sd | slope per year (se) |
|---|---|---|---|---|---|
| pool 6.2-6.4 | baseline | −0.1771 | +0.1429 | 0.0808 | −0.0377 (0.0106) |
| | ES (Spain's error) | −0.1747 | +0.1048 | 0.0626 | −0.0271 (0.0098) |
| | PT (Portugal's error, same dose) | +0.0417 | −0.0293 | 0.0299 | +0.0092 (0.0065) |
| | L1 coarse level | −0.3032 | +0.0922 | 0.0938 | −0.0424 (0.0134) |
| | L2 Spain only | +0.0391 | +0.2866 | 0.1192 | −0.0437 (0.0232) |
| | L3 L1 and L2 | +0.0391 | +0.2900 | 0.1271 | −0.0457 (0.0252) |
| E0 | baseline | −0.1157 | −0.0049 | 0.0369 | −0.0038 (0.0097) |
| | ES | −0.1196 | −0.0005 | 0.0370 | −0.0057 (0.0095) |
| | PT | −0.0016 | +0.0012 | 0.0027 | −0.0001 (0.0007) |
| | L1 | −0.1149 | −0.0037 | 0.0369 | −0.0065 (0.0093) |
| | L2 | +0.2252 | −0.0272 | 0.0165 | +0.0039 (0.0040) |
| | L3 | +0.2654 | −0.0219 | 0.0088 | +0.0003 (0.0023) |

**Rules.**
- **A1:** baseline slope −0.0377 (3.6 se), established. s_ES = 0.72, s_PT = 0.24. Spain misses the 0.75 line by 0.03, so the
  registered label is **shared**. Spain's own slope is established (2.8 se); Portugal's (+0.0092, 1.4 se) is not.
  The slopes add up: ES − PT = −0.0271 − 0.0092 = −0.0363, against the baseline −0.0377.
- **B1:** L1 slope −0.0424, +13% against the baseline: **shape drift** (within ±25%). Coarsening the level absorption does not
  change the trend, so it is not a month-level drift.
- **B2 (E0):** L1 changes η_2021 by +0.0008, not moving. L2 and L3 move it by +0.34 and +0.38, in the wrong direction and
  far from the double LASSO (−0.0816). **No rung moves the estimate toward −0.082, so none of the three registered design
  choices explains the gap.**

**Reading.** The industry drift sits mostly in Spain's own evening-versus-night profile (about three quarters), and is a
shape drift. Portugal's share is small and not established. By the registered mapping "shared" means this route cannot
narrow the range; the weight of the evidence nonetheless leans to a real Spanish drift, which favours the trend null as
the baseline without proving it. L2 and L3 drop the differencing the headline relies on and put the hour-by-month cells of
Spain alone against the dose; the +0.23 to +0.27 for E0 is not an estimate of anything and is not read. It does show that
for E0 in 2021, Portugal's differencing removes a large common component.

**Post hoc, not registered.** Effect against the null at each rung (η_2021 minus the placebo mean, or minus the trend
extrapolated to 2021): baseline −0.32 (mean) / −0.15 (trend); ES −0.28 / −0.16; L1 −0.40 / −0.21; L2 −0.25 / −0.05;
L3 −0.25 / −0.05 (trend value = mean + slope x 4.5 years). The mean-null effects span −0.25 to −0.40 and the trend-null
effects −0.05 to −0.21 (−0.15 to −0.21 without the two Spain-only rungs, which drop the differencing), so the design choice
moves the range by about as much as the trend question itself.
