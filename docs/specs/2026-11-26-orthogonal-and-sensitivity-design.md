# An orthogonal-score version of the estimator, a drift-sensitivity band, and a 2020 placebo summer (proposal)

**Status: proposed 2026-11-26, not registered, not committed. Binding when the user confirms and this file is committed; each part has
its own gate.** Follows `2026-11-26-double-lasso-design.md` (the learner and a double LASSO change nothing),
`2026-11-26-joint-regression-design.md` and `2026-11-26-persistence-joint-design.md`.

**The point in one sentence.** Neyman orthogonality protects an estimate against error in *estimating* the counterfactual load model; our
risk is that the no-reform path itself drifts (a violation of the identifying assumption), which no orthogonal score can remove. This design
(A) writes down the orthogonal version and checks that it changes nothing, (B) measures how much drift would be needed to overturn each
result, and (C) adds the placebo summer next to 2021.

**What is not blind.** All estimates this design touches (E0 −0.116; 6.2, 6.3, 6.4 baseline and joint-regression betas for 2014-2019 and 2021).
Not computed: any pooled orthogonal-score estimate, any sensitivity band, any 2020 placebo.

## Part A: the orthogonal-score (double machine learning) version
### Why the baseline is already nearly orthogonal, and where it is not
The baseline regresses the leave-one-year-out prediction error on the dose. Written as a partially linear model, Y = θ·D + g(W) + ε, with D the
dose laid on one summer's window only and W the calendar, temperature and Portugal's load, the baseline is the orthogonal moment with the
dose's own conditional mean estimated as m̂(W) = 0 (the other years have no dose). The fully orthogonal version estimates both nuisances:
ℓ(W) = E[Y | W] and m(W) = E[D | W], with D = dose × 1{treated window}, on all other years, and regresses the residuals. The two differ when the
treated window is present in the training years of the nuisance fits.

### Design
- **Estimator.** For each target summer T (2021 and the placebo summers 2014-2019), per series (E0 with the toll-and-charge dose; 6.2, 6.3,
  6.4 with the full regulated-price dose): sample = all clean years 2014-2020 (without March-June 2020) plus the 2021 window rows when T = 2021;
  Y = log load of the series (Spain) and, as a second outcome run, Spain's minus Portugal's log load (as the baseline's error difference);
  D = dose × 1{date in T's aligned window}. **Cross-fitting by calendar year** (the fold is the year; the 2021 window rows form their own fold):
  ℓ̂ and m̂ are fitted on the other folds with the paper's per-hour LASSO (10-fold one-standard-error, calendar-temperature interactions,
  no trend; the same learner as the baseline) and also with ridge as a second learner. θ̂_T = Σ D̃·Ỹ / Σ D̃², D̃ = D − m̂, Ỹ = Y − ℓ̂.
- **Inference.** Not the orthogonal-score standard error (one treated cluster per target). The six placebo θ̂_Y give the no-reform distribution
  (prediction t-test, S − 1 d.f.; trend null as Amendment A), exactly as the baseline.

### Rules, set before the run
- **O0 Reproduction (gate).** With m̂ set to 0 and the baseline's fixed effects the code reproduces the committed baseline η_2021 and placebo mean and
  sd for E0, 6.2, 6.3 and 6.4 to 0.0015 (E0 −0.11572 / −0.00491 / 0.03686; 6.2, 6.3, 6.4 as in `2026-11-26-tariff-drift-design.md`). Else stop.
- **O1 Agreement.** |θ̂_2021(orthogonal) − η_2021(baseline)| ≤ one baseline placebo sd, for each series.
- **O2 Same verdict.** Detection of the effect against the mean null (one-sided p ≤ 0.05) has the same outcome as the baseline for each series.
- **O3 Spread.** The orthogonal version's placebo sd is at most 1.5 times the baseline's (it is not claimed to be smaller).
- **O4 Learner.** The ridge and LASSO versions of θ̂_2021 agree within 0.02.
No claim of improvement is attached. If O1-O4 pass, the thesis states: the estimator is orthogonal-score equivalent to first order and the first-step
learner does not matter; the remaining risk is drift (Part B). If O1 fails for a series, report both and say which assumption differs
(the dose's conditional mean).

## Part B: how much drift would overturn each result (sensitivity band)
Placebo betas b_Y (Y = 2014-2019) are the bias of the estimator in years with no reform; the 2021 estimate is τ + δ_2021, with δ_2021 unobserved.
The sensitivity band reports the effects consistent with restrictions on how the bias path can move, instead of choosing one null.
(After Rambachan and Roth's honest sensitivity analysis; a deterministic version, since six placebo betas carry no covariance estimate.
Sampling noise of the betas is treated as part of the path's movement.)
- **Second-difference restriction.** With the path δ_2014…δ_2019 = the placebo betas, δ_2020 and δ_2021 free, require |second difference| ≤ M at 2019
  (δ_2018, δ_2019, δ_2020) and 2020 (δ_2019, δ_2020, δ_2021). Set M = m × M_obs, M_obs = the largest absolute second difference among the observed
  placebo betas (2014-2019), m in {1, 1.5, 2, 3}. The effect is in [b_2021 − δ_max(M), b_2021 − δ_min(M)] (a linear program in two variables;
  with Part C's 2020 point, δ_2020 is fixed and only δ_2021 is free).
- **Relative-magnitude restriction.** |δ_2021 − δ_2019| ≤ M̄ × 2 × (largest absolute year-to-year change among the observed betas), M̄ in {0.5, 1, 1.5, 2}.
- **Series.** E0, 6.2, 6.3 and 6.4 for both the baseline betas and the joint-regression betas (the main specification for 6.4).
### Rules, set before the run (descriptive; classification only)
- **B1 Breakdown.** For each series and restriction, the smallest m (or M̄) at which the band includes zero (the breakdown value), reported.
- **B2 Robust to the drift** if the band excludes zero at m = 1 under the second-difference restriction **and** at M̄ = 1 under the relative-magnitude one
  (the bias may move as erratically as the observed placebo years do). **Fragile** if it includes zero at m = 1 or M̄ = 1.
- **B3 Consistency with the earlier nulls.** The mean-null and trend-null effects of `2026-11-26-tariff-drift-design.md` are reported inside the band
  or outside it. No other null is introduced.
The classification enters the thesis table as one column ("robust to drift" or "fragile"); it is not a new estimate.

## Part C: the 2020 summer as a seventh placebo (optional; gated)
- **What.** LASSO refits that leave 2020 out (keys `(2020,)` for E0, 6.2, 6.3, 6.4 and Portugal: five series of 24 hourly models), then the baseline
  estimate (and the joint-regression estimate) on the aligned 2020 window with the dose laid on it.
- **COVID caveat, stated now.** 1 March to 30 June 2020 is excluded from the data, so the usual window (1 June to 15 September) loses June and covers
  1 July to 15 September (77 days of 107); industrial load in the second half of 2020 was still recovering. The 2020 beta is therefore **not an equal
  draw**: it is reported, used in Part B as the observed 2020 anchor (δ_2020 fixed), and **not added to the placebo set of any registered test**.
- **C1 Gate.** Z0-type check: at least 99% of the hours of the shortened window present for each series. Else Part C is dropped.
- **C2 Reading.** Report b_2020 against the line through 2014-2019; if |b_2020 − extrapolated| exceeds the largest observed year-to-year change, the
  2020 point is flagged as COVID-affected and Part B is run twice (with and without it).

## What each outcome means
Part A pass: the orthogonality argument can be stated in chapter 5 with evidence that the estimator is insensitive to first-step error. Part B: a result
is called robust to drift only if its band excludes zero at the observed erratic-ness; expected, from the earlier work: 6.4 robust, 6.3 fragile at
the second-difference restriction (its path falls steeply and then rebounds), 6.2 fragile, E0 robust. Part C: tells whether the series was still
falling or already rebounding next to 2021.

## Threats
Six placebo betas give a coarse measure of how erratic the bias path is (M_obs is itself noisy); the sensitivity band is conservative because
sampling noise is folded into the path; the relative-magnitude bound uses the largest observed change, which is one draw; the second-difference
restriction with two missing years (2020 unless Part C is used) is an extrapolation by construction; Part A assumes the dose's conditional mean is
estimable from the other years (it is zero there for single-year doses).

## Data and code
Cached errors for Parts A (a refit is needed only for the orthogonal-score nuisance fits: per series two outcomes × per target year,
about 7 × 5 LASSO sets, expected 20-40 minutes in parallel) and B (seconds); Part C needs five refit sets (about 5 minutes each). New scripts
`scripts/analysis/tou_dml_pooled.py` (A), `tou_drift_sensitivity.py` (B), `tou_placebo_2020.py` (C); outputs
`outputs/tables/tou_dml_pooled*.csv`, `tou_drift_sensitivity*.csv`, `tou_placebo_2020*.csv`.
