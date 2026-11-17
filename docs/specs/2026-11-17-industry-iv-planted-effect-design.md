# Planted-effect test of the wind-speed IV pipeline (pre-registration)

**Status: registered 2026-11-17, before any run. Nothing below has been run.** Follows `2026-11-17-industry-iv-wind-speed-estimation-design.md` (result: +0.0001 [-0.021, +0.028]). Purpose: show whether the same pipeline can recover a known response, so that the null is read with its power, not at face value.

**In one example.** Take the real industrial load series and add to each hour a response we choose: when the day-ahead price is EUR 10 above its mean (about 11% of 92.41), load is lowered by 0.05 x 11% = 0.55%. Run the identical pipeline on that altered series. If the instrument is good, it returns about -0.05 with an interval that excludes zero. If it returns zero, our earlier zero could hide a real -0.05.

## Construction
Common sample, residualisation, instruments d_pc and d_pc^2, inference exactly as the wind-speed estimation (same seed, 1,000 permutations). For a planted elasticity beta the outcome becomes
**d ln L* = d ln L + (beta / pbar) x d p** (week-on-week differences, pbar = 92.41), i.e. a same-hour, linear-in-price response of ln load to the actual day-ahead price. The double-ML residual of the planted outcome is **refitted** (not obtained by adding residuals), so the cross-fitting sees the planted series. Price and instrument residuals are those of the real run. The unplanted outcome already contains whatever real response there is (about zero), so the expected estimate is beta + 0.0001.

## Plants (closed list)
- **Pooled:** beta = -0.02, -0.03, -0.05, -0.10 on all rows. (-0.03 is the aggregate equivalent of an exposed share of 15% responding with -0.2.)
- **Half-sample (cancellation check):** beta = -0.10 on 2019-21H1 rows only; beta = -0.10 on 2021H2-23 rows only. The share of rows is 0.52 and 0.48, so a pooled estimate should be about -0.052 and -0.048.

## Rules (each says what a failure would tell us)
- **P1 Recovery.** For each pooled plant, the randomization interval contains beta and the point estimate is within max(0.01, 30% of |beta|) of beta. *Fails:* the pipeline (differencing, boosting, instrument) is biased towards zero or away from it; the earlier zero cannot be read as a bound.
- **P2 Detection at -0.05 and -0.10.** Randomization p of the t-rank at most 0.05 and the interval excludes zero. *Fails:* the design cannot detect a response of Hirth's size; the null is uninformative at that size and the bound is stated only as the detectable size.
- **P3 Half-sample.** The pooled estimate for each half plant is within 0.02 of -0.052 / -0.048 respectively. *Fails:* a response concentrated in one regime is not averaged in the pooled estimate, i.e. the pooled null is not informative about regime-specific responses, and the regime split of the bound becomes mandatory.
- **P4 Power report (no pass/fail).** For -0.02 and -0.03: the point estimate, the interval, and whether zero is excluded; the smallest planted value that is detected (p at most 0.05, interval excluding zero) is reported as the **detectable elasticity** of the design.

## What each outcome means
P1-P3 pass: a response of -0.05 would have been found; the null in the real run is credible down to the smallest detected plant, and the bound of -0.021 is a bound the design can deliver. P2 fails: the null is uninformative at Hirth's size. P3 fails: report regime bounds. P1 fails: the pipeline is biased; do not use it for a headline claim.

## Not done here
Script `scripts/analysis/industry_iv_planted_effect.py` (to be written and committed before it runs); output `outputs/tables/industry_iv_planted_effect.csv`. No real-outcome result is recomputed. The C1 x slope scoring (`2026-11-17-industry-iv-wind-speed-slope-design.md`) waits for this test.
