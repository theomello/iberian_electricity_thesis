# A better prediction model for the six-summer industry test (pre-registration)

**Status: registered 2026-11-23 (user chose six candidates with the stability guard). Binding from this commit;
nothing was fitted before it. 2021 stays sealed until the selection in step 2 is done and written below.** Follows
`2026-11-18-industry-six-summer-ri-design.md` (statistic, windows, inference) and
`2026-11-18-industry-regulated-price-elasticity-design.md` (results and amendment A). **Their registered verdicts
stand and are not re-judged.** This file only changes the first step (the prediction model) and asks one question:
does a better first step make the placebo summers scatter less?

## In one example
The placebo summers are summers with no reform. In each, the test measures a "fake elasticity" of large industry
(6.2–6.4 pooled). If prediction were perfect these would all be zero. They are not: +0.23, +0.22, +0.18, +0.10, +0.02,
+0.10 (2014 to 2019). Around a straight line they still miss by about 0.044 (`s_e`). The 2021 effect against that
line is −0.151, and with a miss of 0.044 per summer the 95% interval is [−0.34, +0.04]: zero is just inside.
If a better model cut the miss to 0.035, the same −0.151 would have an interval that excludes zero. Part of each
miss is foreseeable: an August bridge day, a hot week, a cold spring in Portugal. A model that predicts those leaves
less in the placebo errors. The test is whether it does, judged on the placebo summers alone.

## What does not change
Statistic `η_am` (`tou_cross_tariff.Fit.eta`), Spanish series minus Portugal (REN), Equation 4 fixed effects; pooled
6.2+6.3+6.4 with series-specific fixed effects (`tou_industry_regulated_price.pooled_eta`), **full dose** (energy +
power term); aligned 107-day windows; placebo summers 2014–2019 (S = 6); training years 2014–2020 without COVID
(2020-03-01 → 06-30), leave-one-year-out; prediction t-test and rank, mean null (S − 1 df) and trend null (S − 2 df).
E0 runs alongside as the machinery check. The second step is untouched; only the errors fed into it change.

## No more summers are available (checked 2026-11-23)
ESIOS monthly totals for 1193 (demand), 10269, 1201 (E0), 1202, 1216–1218 (6.2–6.4), queried 2009-01 → 2014-01,
return **January 2014 only**; an hourly day in July 2013 returns no points for 1201, 1216, 1218. The series start
2014-01-01. S stays 6, the extrapolation factor 1.524 and t(0.975, 4) = 2.776 stay as they are. Only `s_e` and `s`
can move.

## How much is needed (MDE)
MDE = (z_{1−α/2} + z_{1−β}) · SE, with α = 0.05 two-sided, power 0.80 (2.80).
- Trend null: SE = s_e · sqrt(1 + 1/S + (2021 − x̄)² / Σ(x − x̄)²) = s_e · 1.524. Now s_e 0.044 → SE 0.067,
  **MDE 0.188** (0.249 with t(4) quantiles in place of z).
- Mean null: SE = s · sqrt(1 + 1/S) = s · 1.080. Now s 0.081 → SE 0.087, **MDE 0.245** (0.305 with t(5)).
- For the two-sided 95% trend-null interval to exclude zero at the current effect (−0.151): SE < 0.151 / 2.776 =
  0.054, i.e. **s_e < 0.036, a 19% cut**. The same 0.035 makes the z-MDE equal to 0.151.

## Candidate models (all per area and hour, as the paper's Equation 3; Portugal gets the same model)
- **M0, baseline.** The paper's LASSO as now (`tou_lasso_paper.area_errors`): month, weekend, national holiday,
  hour's temperature, day's min and max, all pairwise interactions and squares; 10-fold CV, one-standard-error rule.
  Recomputed in the new harness; it must reproduce the registered placebo values (gate G0).
- **M1, calendar.** M0 plus: bridge day (`lib/holidays.bridges`), day before and after a national holiday, Holy Week
  Monday–Wednesday, 24 December → 6 January, and week of August (five dummies). *Why:* large plants schedule
  shutdowns around holidays and in August; the paper's calendar has one holiday dummy and the month.
- **M2, weather memory.** M0 plus: yesterday's mean temperature, the three-day mean of daily maxima, cooling
  degree-hours above 24 °C and heating degree-hours below 15 °C over the day. *Why:* heat builds over days in
  buildings and processes, and Portugal's whole-system load is weather-driven; its errors enter every Spanish
  estimate. From the temperature already on disk. Humidity is not added (needs a new fetch; small expected gain).
- **M3, combined.** M1 + M2, the LASSO choosing among them.
- **M4, random forest.** M3's raw features (no interactions), `RandomForestRegressor` (500 trees, min leaf 5,
  `random_state` 0), one per hour. *Why:* the paper's appendix (footnote 23) found the forest predicts seasonal
  patterns better and gives more precise second-step estimates.
- **M5, scaled control.** M3 errors, with the Portugal block multiplied by b_k, the OLS slope of series k's errors
  on Portugal's errors in that model's training years (one b per series and leave-out). *Why:* if Portugal's errors
  are only loosely related to large Spanish industry's, subtracting them one-for-one adds noise.
- **Not candidates:** a per-hour time trend in the first step (the paper has none, and it would remove the drift that
  the trend null already handles, so the two nulls would no longer be comparable); same-year spring anchoring (E1+E2
  moved January–May 2021, so the anchor would absorb a pre-reform 2021 change into the baseline); industrial
  production indices (monthly levels; the month-of-sample × hour fixed effects already absorb them).

## Step 1: selection, on placebo summers only, 2021 sealed
- Before any feature is built, rows dated 2021-01-01 or later are dropped (asserted in the code). Only the six
  leave-one-year-out models are fitted per series and candidate; the all-years model (the one that predicts 2021) is
  not fitted. No dose, error or estimate for 2021 exists after step 1.
- **G0 (gate).** M0 in the new harness reproduces the registered pooled placebo values (+0.232 … +0.100, full dose, in
  `outputs/tables/tou_industry_regulated_price_summary.csv`) to 1e-4.
  Fails: a harness bug; fixed and rerun before anything is read. Not a choice.
- For each candidate: the six pooled placebo η, their mean and sd `s`, the trend line's slope and residual sd `s_e`;
  the same for E0.
- **Selection rule.** The candidate with the smallest pooled `s_e` is the challenger. If two are within 5% of each
  other on `s_e`, the one with the smaller `s` wins.
- **Adoption rule (all three needed).** (a) `s_e` at least **20% below M0's** (about 0.044 → 0.035, the level at
  which the current effect would be excluded); (b) `s` not more than 10% above M0's; (c) **stable**: dropping each
  placebo summer in turn, the challenger's `s_e` on the other five is below M0's in all six cases. (c) guards
  against picking the luckiest of six candidates on six summers.
- If no candidate passes, **M0 stays**, the headline is unchanged, and the attempt is recorded as failed. No 2021
  number is computed for any new model.

## Step 2: the 2021 run (only after step 1 is written into this file and committed, and the user says yes)
For the adopted model only: the all-years fit, the 2021 pooled η, both nulls, p, 95% interval, rank; E0 likewise;
leave-one-summer-out p. **Reported whichever way it comes out**, side by side:

| | η_2021 | mean null: effect, p, 95% interval | trend null: effect, p, 95% interval | s | s_e |
|---|---|---|---|---|---|
| M0 (registered) | −0.177 | −0.320, 0.007, [−0.544, −0.096] | −0.151, 0.044, [−0.337, +0.036] | 0.081 | 0.044 |
| adopted model | | | | | |

The headline cites the adopted model's numbers only if step 1 adopted it, with "prediction model chosen on placebo
summers before 2021 was computed (registered 2026-11-23)" and M0 beside it. A smaller or positive 2021 effect under
the adopted model is reported as the result; M0 is not brought back because it looks better.

## Stop rules
One selection run, one 2021 run. No candidate, feature, hyperparameter, window or control is added after step 1's
table is seen. If the adopted model's 2021 run raises a bug, the fix is recorded and the run repeated once.

## Threats
- Six summers estimate a spread poorly (4 degrees of freedom for `s_e`); a 20% cut is within what chance can give
  one of six candidates. Rule (c) and the 20% bar limit this; they do not remove it.
- The forest (M4) and the scaled control (M5) change more than the features; if one wins, the reason is reported.
- 2021 remains a post-COVID summer with a rising wholesale price; a better first step does not address that.
- The 2021 point estimates under M0 are known; the selection cannot see them, but the person choosing the candidate
  list could. The list above was written before any candidate was fitted.

## Code and outputs
`scripts/analysis/tou_prediction_models.py` (features M1–M2, forest, scaling; reuses `tou_lasso_paper.fit_one_se`,
`tou_industry_six_summer.build/aligned`, `tou_industry_regulated_price.pooled_eta`). `--select` runs step 1 only and
writes `outputs/tables/tou_prediction_model_selection.csv`; `--final <model>` runs step 2. Error caches per model
under `data/cache_tou/`. Deterministic. Committed before each run.
