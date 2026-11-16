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

## Results (run 2026-11-17, `scripts/analysis/tou_randomization_inference.py`; `outputs/tables/tou_randomization_inference{,_summary}.csv`)
109 placebo windows qualified (k = 37 … 178; the COVID block removed k = 52 … 78). **RI0-RI6 all pass.** Nothing else was tried.

| Rule | Result | Verdict |
|---|---|---|
| RI0 enough windows | 109 ≥ 40 | pass |
| RI1 headline, one-sided p | 0.009 (real −0.101; placebo mean +0.003, sd 0.012) | pass |
| RI2 null centred | \|mean placebo\| 0.003 ≤ 0.03 | pass |
| RI3 non-overlapping (N = 8) | p 0.111 (the smallest possible, 1/9: the real estimate is the most extreme of 9) | pass |
| RI4 season-matched (N = 26) | p 0.037 (the smallest possible, 1/27) | pass |
| RI5 consistency | η_RI −0.104 vs two-year −0.090 (difference 0.014) | pass |
| RI6 interval | [−0.122, −0.079], excludes zero | pass |

**Household elasticity.** The real estimate is about eight placebo standard deviations from the placebo mean and more extreme than all 108 placebo windows bar one. The randomization interval ([−0.122, −0.079]) sits around the earlier placebo-adjusted −0.090 and the Wald range. The headline can be quoted with a randomization p-value and interval.

**Other series (descriptive, no pass/fail rule).** The placebo means for the non-household series are positive and large (0.06 to 0.31) and their spread is wide (sd 0.2 to 0.46 in all windows), so these numbers move with the sample:
| Series | real η | p one-sided (all / season-matched) | interval (all) | interval (season-matched) |
|---|---|---|---|---|
| E1+E2 | −0.168 | 0.055 / 0.037 | [−0.66, +0.05] | [−0.25, −0.05] |
| IND | −0.288 | 0.027 / 0.037 | [−0.88, −0.10] | [−0.39, −0.17] |
| 6.2 | −0.080 | 0.345 / 0.630 | [−1.12, +0.33] | [−0.20, +0.32] |
| 6.3 | −0.321 | 0.064 / 0.037 | [−1.14, +0.10] | [−0.61, −0.10] |
| 6.4 | −0.533 | 0.018 / 0.037 | [−1.64, −0.09] | [−1.46, −0.66] |
Reading: the household result is an identified elasticity. For IND, 6.3 and 6.4 the real estimate is more negative than every season-matched placebo, but (i) 0.037 is the smallest p that 26 windows allow and the 26 come from two summers (two clusters in practice), (ii) the placebo means are positive and the adjustment (η_RI = real minus mean) inflates the estimates to −0.37, −0.46 and −0.85, which are not believable magnitudes at doses of 0.04-0.07, and (iii) the earlier registered industry verdict (rules 3-7: placebo years disagree, reduced form, sensitivity) stands. They remain descriptive: the industrial series respond in the predicted direction in 2021 more than in any placebo summer, with a size that this design cannot pin down.
Limits as registered: overlapping windows (about 15 independent), two summers in the season-matched set, Fisher intervals assume a constant additive effect.
