# Modelling the industry placebo drift: by tariff, then a trend term, then an observable (proposal)

**Status: proposed 2026-11-26, not registered, not committed. Binding for Step 3 when the user confirms and this file is
committed; Steps 1 and 2 are conditional (gates below) and each needs its own go-ahead.** Cached errors only
(`six_summer_errors.parquet`); nothing is refitted. Follows `2026-11-26-drift-location-design.md` (the pooled drift is a
*shape* drift, about three quarters in Spain's own profile) and `2026-11-18-industry-regulated-price-elasticity-design.md`.

**Relation to an earlier stop rule.** Amendment A of the regulated-price design ended with "stop after this: no further dose
components or null models". That was the rule for that design. This is a new design, approved by the user on 2026-11-26
("do 3 then 1 and then 2"); the 2026-11-18 verdicts stand and are not re-judged. Its results are reported beside them.

**What is not blind.** The per-tariff placebo betas have been seen (`tou_industry_regulated_price_summary.csv`):
6.2 +0.023, +0.028, +0.010, +0.031, −0.010, +0.035; 6.3 +0.418, +0.339, +0.304, +0.114, −0.028, +0.038;
6.4 +0.360, +0.419, +0.354, +0.247, +0.202, +0.372 (2014-2019). The reading "the pooled trend is mostly 6.3" is therefore
post hoc. What has not been computed: the slope uncertainty per tariff, the per-tariff effect against a trend null, and
anything in Steps 1 and 2.

## In one example
Industry's placebo effect falls from +0.42 to +0.04 for tariff 6.3 between 2014 and 2019, while 6.2 sits at about +0.02
every year. If the "no reform" value for 6.2 is +0.02 whichever null we use, its reform effect needs no trend
assumption. If it falls for 6.3, the effect depends on whether the fall would have continued to 2021. The range
(−0.15 to −0.32) may then be mostly a 6.3 question.

## Step 3: the drift by tariff (binding on commit)
For each of 6.2, 6.3, 6.4 separately (full regulated-price dose, series-specific fixed effects as `pooled_eta` with one
name), 2021 and the six aligned placebo summers:
- **Mean null:** effect = η_2021 − mean of the placebos; prediction t-test as the six-summer test (S − 1 d.f.).
- **Trend null:** effect = η_2021 − ŷ_2021 from a straight line in year through the six placebos; prediction t-test with
  S − 2 d.f. and the Amendment-A standard error (se_pred = s_e·sqrt(1 + 1/S + (2021 − ȳear)² / Σ(year − ȳear)²)).
- Report slope per year with its OLS standard error, both effects with one-sided p and the 95% interval.

### Rules, set before the run
- **T1 Reproduction (gate).** Single-series η_2021, placebo mean and sd reproduce the committed rows to 0.0015:
  6.2 (−0.06369, +0.01955, 0.01684); 6.3 (−0.23291, +0.19751, 0.1808); 6.4 (−0.33676, +0.32562, 0.083). Else stop.
- **T2 Established trend.** A tariff has an established trend if its slope is negative and at least 1.5 times its standard
  error (the A1 threshold of the drift-location design).
- **T3 Range settled.** A tariff's range is *settled* if its mean-null and trend-null effects differ by at most 0.10
  (about the pooled placebo sd, 0.08). Tariffs without an established trend (T2 fails) are settled by construction and
  the mean null is their estimate; the trend null is reported beside it, not used.
- **T4 Detection.** Per tariff and per null, one-sided p ≤ 0.05 (reported as detected or not; no tariff is dropped).
- **T5 Aggregation.** If any tariff is settled and the others are not, the thesis reports the tariffs separately in the
  table and the pooled −0.15 to −0.32 as the unsettled aggregate, with the diagnosis.

### What each outcome means
- 6.2 and 6.4 settled, 6.3 not: the range is a 6.3 problem; the headline for large industry can be stated per tariff with
  the range attached to 6.3 only.
- None settled: the drift is in all tariffs; the range stands as it is and Step 1 is the next route.
- All settled: the range was an artefact of pooling a drifting tariff with flat ones; report per tariff.

## Step 1: a trend term in the regression (conditional on T2 holding for at least one tariff; needs a separate go)
One restricted regression instead of a second-stage line. Stack the cross-fitted errors: for each placebo year Y the rows of
year Y from `errs[(series, "(Y,)")]` (the model that left Y out), for 2021 the window rows from `errs[(series, "()")]`.
Fixed effects as the baseline. Regressors laid on each year's aligned window: dose × 1, dose × (year − 2021), and dose × 1{2021}.
- α = the 2021 no-reform value of the drifting effect; γ = trend per year; **θ = the reform effect against the trend null**,
  with week-clustered standard errors that include the sampling error of the 2021 term (the second-stage line ignores it).
- **J1 Reduction.** With γ fixed at 0, θ is within 0.01 of the Step 3 mean-null effect for the same tariff.
- **J2 Agreement.** θ with the trend is within 0.03 of the Step 3 trend-null effect; a larger gap means the second-stage line
  was understating or overstating its uncertainty and both are reported.
- **J3 Not one summer.** Leaving out each placebo summer in turn, θ keeps its sign and stays within 0.10 of its full value.

## Step 2: an observable for the drift (conditional on Step 1; needs a separate go)
With six summers the drift can be tied to at most **two** pre-named candidates, chosen now: (a) the summer's mean OMIE
price spread, evening hours (18-21) minus night (0-7), from the OMIE files already on disk; (b) none other. No
selection among candidates. The covariate replaces the year trend in the Step 1 regression (dose × covariate).
- **K1 Fit.** The covariate explains at least 70% of the variance of the six placebo betas (R² on six points) and has the
  sign that matches the drift.
- **K2 Out of sample.** Predicting 2017, 2018 and 2019 from the earlier years, its RMSE is below the trend's (0.077 on the
  pooled series; computed per tariff).
Both must hold to use it; otherwise Step 2 is dropped and the thesis reports the Step 3 and Step 1 ranges. A covariate that
only fits six points is not evidence of a mechanism and is described as such.

## Threats
Six placebo summers per tariff: per-tariff slopes are imprecise (the pooled slope has 3.6 se; single tariffs will have less);
2020 is missing (COVID), so the trend extrapolates two years past 2019; tariff-level placebos mix industries; 6.2's dose is
small (placebo sd 0.017 on a −0.064 effect), so its result is precise but rests on a small dose; Step 2 has almost no
degrees of freedom and can only fail or weakly succeed.

## Data and code
Cached errors, committed dose tables; no new data. New script `scripts/analysis/tou_tariff_drift.py` (Step 3 first; Steps 1 and
2 in the same file behind flags, not run until their gates and go-ahead), outputs `outputs/tables/tou_tariff_drift_*.csv`.

## Step 3 results (run 2026-11-26, `scripts/analysis/tou_tariff_drift.py`; `outputs/tables/tou_tariff_drift_step3.csv`)
**T1 passes** for 6.2, 6.3 and 6.4 (η_2021, placebo mean and sd equal the committed rows to five decimals). Sanity: the pool's
trend null reproduces Amendment A (ŷ −0.027, effect −0.150, p 0.045, [−0.338, +0.037]; committed −0.026, −0.151, 0.044).

| tariff | η 2021 | placebo mean (sd) | slope per year (se) | mean null: effect, p, 95% interval | trend null: ŷ 2021, effect, p, 95% interval |
|---|---|---|---|---|---|
| 6.2 | −0.064 | +0.020 (0.017) | −0.0009 (0.0045) | −0.083, 0.003, [−0.130, −0.037] | +0.016, −0.079, 0.025, [−0.159, +0.000] |
| 6.3 | −0.233 | +0.198 (0.181) | −0.0912 (0.0159) | −0.430, 0.039, [−0.932, +0.072] | −0.213, −0.020, 0.427, [−0.302, +0.262] |
| 6.4 | −0.337 | +0.326 (0.083) | −0.0201 (0.0198) | −0.662, 0.0004, [−0.893, −0.432] | +0.235, −0.572, 0.005, [−0.922, −0.222] |
| pool | −0.177 | +0.143 (0.081) | −0.0377 (0.0106) | −0.320, 0.007, [−0.544, −0.096] | −0.027, −0.150, 0.045, [−0.338, +0.037] |

**Rules.**
- **T2:** established trend only for **6.3** (slope −0.091, 5.7 se). 6.2 (0.2 se) and 6.4 (1.0 se) have none.
- **T3:** 6.2 settled (gap 0.004) and 6.4 settled (gap 0.090, no established trend, so the mean null stands); **6.3 not settled**
  (mean-null effect −0.430, trend-null effect −0.020, gap 0.41).
- **T4:** detected under both nulls for 6.2 (p 0.003, 0.025) and 6.4 (p 0.0004, 0.005); 6.3 detected only under the mean
  null (p 0.039; trend null p 0.43, interval spans zero).
- **T5:** the tariffs are reported separately; the pooled −0.15 to −0.32 is the unsettled aggregate and **the whole width of
  the range comes from 6.3**.

**Reading.** The industry effect is not one number: 6.2 −0.08 (both nulls), 6.3 between −0.43 and −0.02 depending on the
null, 6.4 about −0.57 to −0.66. It rises steeply with voltage, which the pooled figure hides (the earlier E5 rule, that series
estimates scale with the new dose, already failed). 6.3's placebo falls from +0.42 to +0.04 in six summers while the other
two do not trend, so 6.3 is the tariff whose drift needs a model. Step 1 runs on 6.3 only (the only tariff passing T2).

## Step 1 results (run 2026-11-26, tariff 6.3 only, `scripts/analysis/tou_tariff_drift_step1.py`; `outputs/tables/tou_tariff_drift_step1.csv`)
Restricted regression on the stacked cross-fitted errors (330 week clusters). α (no-reform drift value at 2021) −0.187
(se 0.065); γ (trend per year) −0.090 (se 0.014); **θ (reform effect against the trend null) −0.024 (se 0.071, one-sided
p 0.37, 95% [−0.163, +0.114])**. With γ fixed at 0, θ = −0.431.

| rule | result | verdict |
|---|---|---|
| J1 reduction (γ = 0 equals the Step 3 mean null, within 0.01) | −0.4306 against −0.4304 | pass |
| J2 agreement (θ within 0.03 of the Step 3 trend null) | −0.0242 against −0.0198 | pass |
| J3 not one summer (leave-one-summer-out keeps sign, within 0.10 of θ) | dropping 2014…2019: −0.016, −0.025, −0.021, −0.038, −0.092, **+0.086** | **fail** |

**Reading.** The joint regression confirms the second-stage line: against the trend null the 6.3 effect is about −0.02 and not
distinguishable from zero, and against the mean null it is −0.43. It adds the sampling error of the 2021 estimate, so its
interval is similar but not tighter. But the trend null is fragile: dropping the 2019 summer (the rebound from −0.028 to
+0.038) steepens the line and θ becomes +0.086, a sign change; dropping 2018 gives −0.092. One summer decides whether the
extrapolated no-reform value sits at −0.21 or lower. J3 failed as registered and is not rescued. For 6.3, the data support
neither null over the other; the thesis should report 6.3 as unresolved between −0.43 and about zero, and rely on 6.2 and 6.4.
