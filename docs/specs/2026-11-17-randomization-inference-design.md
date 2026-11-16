# Randomization inference for the time-of-use estimates (proposal)

**Status: proposed 2026-11-17, not registered. Binding when the user confirms and this file is committed; the first run follows that commit. It adds an inference layer to existing estimates; it does not re-judge rules that already failed.**

**In one example.** The household estimate for summer 2021 is −0.09. Is that large for a design that finds "effects" from drift alone? Take the same design and put the same tariff dose on every other 107-day window in 2018-2020 where nothing changed: 8 June 2018, 15 June 2018, and so on, one week apart. Suppose the 100 or so placebo estimates scatter between −0.04 and +0.04. Then −0.09 lies outside all of them, and the chance of a placebo being that extreme is about 1 in 100. If instead the scatter ran to ±0.10, the same −0.09 would be unremarkable. The p-value is the rank of the real estimate in that scatter, and the scatter also gives the interval.

## Why
Two placebo years (2018, 2019) give two numbers, and a pass/fail threshold on two numbers is a coarse test (rule 3 of the industry run). With about a hundred shifted windows the real estimate is compared with a distribution, so the test has a p-value, a size, and an interval, and does not rely on a threshold chosen by us.

## Design
- **Statistic.** `η_am`, the Equation 4 elasticity of `tou_cross_tariff.Fit.eta` (policy-instrumented dose, area×month clusters), for the household series E0 against Portugal (primary). The same statistic for E1+E2, IND, 6.2, 6.3, 6.4, reported with p-values only.
- **Placebo windows.** The real window is 2021-06-01 → 2021-09-15 (107 days, a Tuesday start). Placebo windows start 7k days earlier for k = 1, 2, ... (same weekday alignment) and end 107 days later; kept when the whole window lies in 2018-01-01 → 2020-12-31 and does not overlap the COVID block 2020-03-01 → 2020-06-30. The dose on each placebo date is the real dose structure applied to that date (`old_new_tables(dates)`, `series_dose`), so peak, mid and off-peak hours and day types follow the placebo calendar.
- **Errors.** Cross-fitted: LASSO errors for year Y come from a fit that leaves Y out (2018, 2019 cached; 2020 new, leave-2020-out, COVID excluded). A window spanning two years uses each year's own errors (as the contrast placebo does). New fits go to `data/cache_tou/cross_tariff_ri_errors.parquet`.
- **Sample for each placebo regression.** 2018-01-01 → 2020-12-31 without COVID, the pre-period; no real-window data enter.
- **p-values.** One-sided (negative), `p = (1 + #{η_s ≤ η_real}) / (1 + N)`; two-sided with absolute values. **Interval** (Fisher style, additive constant effect): `η_real − [q97.5, q2.5]` of the placebo `η_s`.
- **Subsets.** (a) All windows (main). (b) Non-overlapping windows spaced at least 107 days (about 8; the conservative p, minimum about 0.11). (c) Season-matched: windows starting within ±45 days of 1 June in 2018 or 2019.
- **Adjusted estimate.** `η_RI = η_real − mean(η_s)`, compared with the two-year adjustment (−0.090).

## Rules, set before the run
- **RI0 Enough windows.** At least 40 placebo windows qualify; otherwise stop and report the count.
- **RI1 Headline.** The household `η_real` has a one-sided p ≤ 0.05 in the all-window set.
- **RI2 Null centred.** |mean placebo η| ≤ 0.03 (a third of the real estimate); otherwise the placebo set is drifted and the adjusted estimate carries the correction.
- **RI3 Non-overlapping.** One-sided p ≤ 0.15 in subset (b).
- **RI4 Season-matched.** One-sided p ≤ 0.10 in subset (c).
- **RI5 Consistency.** `|η_RI − (−0.090)| ≤ 0.02`.
- **RI6 Interval.** The Fisher-style interval excludes zero.
For E1+E2, IND and the 6.x series the p-values and intervals are reported without a pass/fail rule; they inform, they do not re-open the earlier verdicts.
No other specification is tried after a failure.

## What each outcome means
RI0-RI6 pass: the household elasticity stands as a test with a size, not only as an estimate that survived two placebos, and the headline can quote a randomization p-value and interval. RI2 fails: the placebo set drifts, the adjusted estimate and its interval are the result. RI3 or RI4 fails: significance rests on overlapping or off-season windows and is reported as such. For the industrial series a small p with a drifted null is a descriptive finding, not an identified elasticity.

## Threats
Placebo windows overlap heavily (about 15 independent ones), so (a) overstates precision and (b) understates power; seasons outside summer differ in the Spain-minus-Portugal residual (subset (c) addresses it with only about 18 windows); the 2020 H2 months carry post-lockdown behaviour; Fisher intervals assume a constant additive effect; one dose structure (the real one) is reused.

## Data and code
`data/cache_tou/cross_tariff_errors.parquet` plus new leave-2020-out fits. New code: `scripts/analysis/tou_randomization_inference.py`, reusing `tou_cross_tariff`, `tou_industry_adjusted` helpers. Output `outputs/tables/tou_randomization_inference.csv` (one row per window and series) and `..._summary.csv`.
