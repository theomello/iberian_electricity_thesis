# Double LASSO for the E0 reform effect (proposal, step zero only)

**Status: proposed 2026-11-26, not registered, not committed. Step zero below is a feasibility check with a rule set
before it is run; estimation (steps 1-3) needs its own go-ahead.** Context: the `ML/` course (deck 10, double LASSO and
Neyman orthogonality). The learner-swap check (scratch, 2026-11-26) showed that replacing the per-hour LASSO by ridge,
elastic net, post-LASSO or boosting changes neither the E0 estimate nor the placebo spread, so prediction quality is not
the limit.

## In one example
Today we predict summer-2021 load from earlier years and read the gap. Any 2021-specific shift unrelated to the reform
lands in the estimate. In a pooled regression of log load on the dose, with calendar, temperature, year and Portugal's
load as candidate controls, double LASSO removes each control's effect from both the load and the dose and regresses
residual on residual. The question for step zero: after removing the controls, does the dose still vary?

## Set-up (pooled over hours)
- Unit: date x hour, E0 (ESIOS 1201), Spain, hours pooled. Sample: clean pre years 2014-2020 without 2020-03-01 ->
  2020-06-30, plus the 2021 window (R0..R1). Dose: `tou_cross_tariff.series_dose("E0", ...)` as in the six-summer script,
  nonzero only inside the window.
- Controls W (version b): hour x weekday x month dummies, hour x (temperature, min, max, squares), year dummies, a
  window-day dummy (absorbs a 2021 level shift), holiday. Version a: the same without the window-day dummy.
- Identification in version b: the shape of the response across hours within window days (evening against night),
  which is the paper's DDD variation; the window-day dummy takes the level.

## Step zero (feasibility, no estimation)
Regress the dose on W by OLS and report the share of dose variance left (1 - R^2) and the residual sd, for versions a
and b, for the real 2021 window and the 2018 placebo window laid on the same pipeline.
**Rule, set before the run:** go if, in version b, the share left is at least 0.10 in both the 2021 and 2018 windows.
Below 0.10 the dose is essentially a function of the controls and double LASSO would be estimating from noise: stop.

## If step zero passes (not yet proposed in detail)
1. Double LASSO with Portugal's log load (and its calendar interactions) among the candidates, one-SE penalty, folds by
   year (leave-one-year-out).
2. The same pipeline on the six placebo summers (2014-2019); inference by the six-summer rank/prediction test, not by
   the pooled standard error.
3. Compare the 2021 estimate and placebo spread with -0.116 and 0.037.

## Step zero result (run 2026-11-26, scratch `dl_step0.py`)
Share of dose variance left after OLS on the controls: 2021 window 0.873, 2018 window 0.860 (rule: at least 0.10) -> **pass**.
Note: in the 2021 sample the year-2021 dummy equals the window dummy (no 2021 days outside the window), so versions a and
b coincided. Year effects therefore absorb the level in 2021, and the dose is identified from the shape across hours.

## Step 1: registered 2026-11-26 (binding once this file is committed; the run follows the commit)

**Estimator (pooled over hours, one regression per summer).** y = log E0 load (Spain), d = dose. Controls W: hour x
weekday-type x month dummies; hour x (temperature, daily min, daily max) with squares; national holiday; **Portugal's log
load and its hour interactions** (candidate control with estimated loading, replaces subtracting Portugal with loading 1).
Unpenalised and partialled out exactly first: year dummies (and so the window level). Then double LASSO on the rest: LASSO of
y on W and of d on W, penalty by 10-fold cross-validation with the one-standard-error rule, folds are blocks of ISO weeks
(serial correlation); beta = OLS of the y residual on the d residual; standard error clustered by ISO week. Variant
**P0** drops the Portugal terms (sensitivity).

**Samples, identical in every summer.** Clean pre years 2014-2020 without 2020-03-01 -> 2020-06-30. For the treated summer
2021: all pre years plus the 2021 window rows. For each placebo summer Y in 2014-2019: all clean pre years with, for year
Y, **only its aligned window days kept** (so Y's year dummy equals its window dummy, as in 2021), and the dose laid on
that window with the same procedure as the six-summer script (`aligned`, `series_dose`). Each placebo summer is fitted as
its own run on the 2021 sample's pre years minus nothing else; 2021 rows are excluded from placebo runs.

**Statistic and inference.** As in the six-summer test: S = 6 placebo betas, prediction t-test
t = (beta_2021 - m) / (s * sqrt(1 + 1/S)), one-sided p from Student t with S-1 d.f.; rank p; the 95% prediction interval.
Baseline to beat (E0, per-hour LASSO, subtract Portugal): beta_2021 -0.1157, placebo mean -0.0049, placebo sd 0.0369.

**Rules, set before the run.**
- **D1 Feasible.** Residual dose sd after partialling out is at least 20% of the raw dose sd in every summer.
- **D2 Placebos centred.** |placebo mean| <= |beta_2021| / 3 (same as R3 of the six-summer test).
- **D3 Spread.** Placebo sd of beta is at most 0.8 x 0.0369 = 0.0295 (a 20% reduction). Failing D3 means double LASSO
  adds nothing on noise; the baseline estimator stands.
- **D4 Detection.** beta_2021 < 0 and prediction-t p <= 0.05.
- **D5 Agreement.** beta_2021 within [-0.116 - 0.0369, -0.116 + 0.0369] of the baseline (one baseline placebo sd), else
  the two estimators identify different things and no replacement is claimed.
- **D6 Portugal.** Report P0 beside the main run; the Portugal terms are kept only if the placebo sd with them is below
  the P0 value (reported either way).
Any failure is recorded, not rescued: no other specification is tried after a failure.

## What each outcome means
D1-D5 pass and D3 holds: double LASSO is a bias-robust way to select the drift controls and gives a tighter placebo
distribution; it supports the method chapter's cross-fitting argument and is reported beside the baseline. D3 fails:
the controls were never the issue (consistent with the learner swap), and the section says so. D5 fails: the shape-only
estimate differs from the level estimate; report both and do not mix them.
