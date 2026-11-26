# Counterfactual-calendar controls in the main regression (proposal)

**Status: proposed 2026-11-26, not registered, not committed. Binding when the user confirms and this file is committed; the
run follows that commit.** Cached errors only; no refits. Follows `2026-11-26-calendar-randomization-design.md` (the contrast
Δ = real-calendar beta minus the mean of shifted-calendar betas) and `2026-11-26-tariff-drift-design.md`.

**What is not blind.** The separate betas for the real and the 14/13/14 shifted calendars, and the Δ results: 6.4 contrast −0.55,
6.3 −0.26 (mean null) to −0.13 (trend null), 6.2 −0.03 (not detected). Not computed: any regression with the real and shifted doses together.

## In one example
The contrast subtracts the shifted calendars' betas from the real one. A shifted calendar that shares half of the real pattern
carries half of a real effect, so subtraction understates it. A joint regression puts the real dose and summaries of the shifted doses in
the same model: the real coefficient is then the part of the load pattern explained by the real calendar and *not* by any dose-like pattern,
with one standard error and no subtraction.

## Estimator (one regression per tariff and summer)
- Stack, errors and fixed effects exactly as the baseline (Spain and Portugal blocks, `fe3`, series-specific).
- Regressors: the real dose d₀ (laid on the summer's aligned window) and J controls built from the counterfactual doses d_k, k in
  ±3…±9 hours (the shifted calendars of the calendar-randomization design, same 0.5 screen).
- **Controls (main): principal components** of the screened counterfactual doses after partialling out the fixed effects (Spain rows),
  recomputed in every summer; J = the smallest number of components that explain 90% of their variance, at most 5.
- Variants, reported beside the main: **S1** one control, the mean of the screened counterfactual doses; **S2** all screened
  counterfactual doses entered individually (OLS).
- Statistic: β_joint(Y) = the coefficient on d₀, for 2021 and the six aligned placebo summers 2014-2019 (same procedure, sample and window as the six-summer test).
- Inference: the six placebo β_joint give the no-reform distribution (prediction t-test, S − 1 d.f.; effect = β_joint(2021) − placebo
  mean); trend null as Amendment A (S − 2 d.f.) where a trend is established. No clustered standard error is used for the verdicts.

## Rules, set before the run
- **J0 Reproduction (gate).** With no controls the estimator reproduces the committed baseline rows (6.2 −0.06369 / +0.01955 / 0.01684;
  6.3 −0.23291 / +0.19751 / 0.1808; 6.4 −0.33676 / +0.32562 / 0.0830) to 0.0015. Else stop.
- **J1 Feasible.** After the fixed effects and the controls, the real dose keeps at least 20% of its variance in every summer
  (all three tariffs). If not, the controls span the real dose and that tariff is not estimated (reported as such).
- **J2 No drift.** The placebo slope per year of β_joint is not established (|slope| < 1.5 × its se).
- **J3 Not noisier.** The placebo sd of β_joint is at most the baseline's (6.2 0.0168, 6.3 0.1808, 6.4 0.0830).
- **J4 Detection.** Effect against the mean null negative with one-sided p ≤ 0.05; if J2 fails, also against the trend null.
- **J5 Stable.** (a) leaving out each placebo summer, the effect keeps its sign and stays within 0.10; (b) with J − 1 and J + 1
  components (J ≥ 2 only), the effect stays within 0.05 of the main value.
- **J6 Tariff "works".** J1, J2 and J4 pass. A tariff that fails J4 is reported with its one-sided 95% bound: the effect is no more
  negative than the lower end of its one-sided interval (so 6.2 can be reported as a bound if it does not detect).

## What each outcome means
J2 passes for a tariff: the shifted-calendar controls absorb the shape drift in the main specification; the joint estimate is the
tariff's headline and replaces the mean-null and trend-null range. J2 fails: the drift is specific to the real calendar's shape; report
the joint estimate beside the earlier ranges and keep the range. J1 fails: the real calendar is not separable from shifted patterns for that
tariff. J4 fails for 6.2: report a bound, not a detection; do not search for another specification. The agreement with the contrast Δ is reported
(descriptive: 6.2 −0.03, 6.3 −0.26, 6.4 −0.55).

## Threats
The span of 14 shifted calendars may reproduce much of the real dose (J1 checks it); the controls are patterns, not a treatment, so
the coefficient is "the effect of the real calendar beyond dose-like shapes" and is conservative where a real effect lies in the shared
part of the pattern; PCs change by summer (a different window); six placebo summers per tariff keep every slope imprecise; shifts keep the
real calendar's structure (same hour blocks, months, prices).

## Data and code
Cached errors; the shifted doses are rebuilt as in `tou_calendar_randomization.py` (about 15 doses × 7 summers × 3 tariffs; residualisation
dominates, expected 15-20 minutes per tariff in parallel). New script `scripts/analysis/tou_joint_regression.py`; outputs
`outputs/tables/tou_joint_regression_*.csv`.

## Results (run 2026-11-26; `scripts/analysis/tou_joint_regression.py`, `..._rules.py`; `outputs/tables/tou_joint_regression_*.csv`)
Screened calendars: 14 (6.2), 13 (6.3), 14 (6.4). J = 3 principal components (90-91% of the variance) in every summer and tariff.
Registration and script were committed before the run (dffb3b1, 6650cf4).

| rule | 6.2 | 6.3 | 6.4 |
|---|---|---|---|
| J0 reproduction (no controls = baseline) | pass | pass | pass |
| J1 real-dose variance left (min over summers) | 0.88 pass | 0.85 pass | 0.88 pass |
| J2 placebo slope not established | +0.0115 (se 0.0074), 1.55 se: **fail** (marginal) | −0.0423 (se 0.0082): **fail** | −0.0076 (se 0.0168): **pass** |
| J3 placebo sd ≤ baseline | 0.0349 vs 0.0168: **fail** | 0.0849 vs 0.1808: pass | 0.0645 vs 0.0830: pass |
| J4 detection, mean null (effect, p) | −0.026, p 0.26: no | −0.329, p 0.008: yes | −0.641, p 0.0001: yes |
| J4 trend null (effect, p), where J2 fails | −0.077, p 0.088: no | −0.139, p 0.029: yes | −0.607, p 0.002: yes |
| J5 stable (leave-one-placebo-out; J−1, J+1) | pass, pass | pass, pass | pass, pass |
| **J6 tariff works (J1, J2, J4)** | **no** | **no** (J2 fails) | **yes** |

Main betas: 6.4 2021 −0.341, placebos +0.285, +0.331, +0.394, +0.233, +0.226, +0.327; 6.3 2021 −0.171, placebos +0.253, +0.234, +0.213,
+0.104, +0.059, +0.084; 6.2 2021 −0.019, placebos −0.009, −0.005, −0.013, +0.008, −0.019, +0.075.
Effects with 95% prediction intervals: **6.4 −0.641 [−0.820, −0.462]** (trend null −0.607 [−0.904, −0.309]);
**6.3 −0.329 [−0.565, −0.094]** (mean null) and **−0.139 [−0.285, +0.007]** (trend null); **6.2 −0.026 [−0.122, +0.071]**, one-sided 95% lower bound −0.102.
Variants: S1 (mean of shifted doses) effects 6.2 −0.044, 6.3 −0.335, 6.4 −0.649; S2 (all shifted doses, dose variance left 0.47-0.60)
6.2 −0.015, 6.3 −0.294, 6.4 −0.577.

**Reading.**
- **6.4 works.** The shape drift is absorbed (flat placebo slope), the placebo spread falls from 0.083 to 0.065, and the effect −0.64
  matches the baseline mean null (−0.66) and the earlier trend null (−0.57); the contrast Δ (−0.55) understated it, as the leakage
  argument predicted. It is the tariff's headline.
- **6.3 is narrower, not settled.** Controls halve the placebo spread (0.085 against 0.181) and both nulls now detect (−0.33 and −0.14,
  the latter's interval just reaching zero), but the drift remains (slope −0.042 per year, 5 se). Registered reading: the joint estimate is
  reported beside the earlier ranges; the range −0.14 to −0.33 replaces −0.43 to −0.02.
- **6.2 is not detected.** The joint estimate is −0.03 with an interval spanning zero and a noisier placebo set than the baseline (2019 is
  +0.075 again). Reported as a bound: no effect more negative than −0.10. No other specification is tried.
- **J1 is comfortable (85-89%), so the shifted patterns do not span the real dose**; S2 (all shifted doses) leaves 47-60%, as expected.
