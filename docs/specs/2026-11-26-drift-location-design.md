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
