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

## Results (run 2026-11-17, script `industry_iv_planted_effect.py`, committed before the run; outputs `outputs/tables/industry_iv_planted_effect{,_checks}.csv`)
| Plant | Expected | Estimate | 95% randomization interval | Detected (p <= 0.05, zero excluded) |
|---|---|---|---|---|
| pooled -0.02 | -0.020 | -0.0197 | [-0.035, +0.009] | no (p 0.10) |
| pooled -0.03 | -0.030 | -0.0298 | [-0.047, -0.001] | yes (p 0.008) |
| pooled -0.05 | -0.050 | -0.0503 | [-0.068, -0.020] | yes |
| pooled -0.10 | -0.100 | -0.1049 | [-0.118, -0.079] | yes |
| -0.10 in 2019-21H1 only | -0.052 | **-0.0296** | [-0.050, -0.005] | yes |
| -0.10 in 2021H2-23 only | -0.048 | **-0.0723** | [-0.087, -0.038] | yes |

**P1 pass** (all four pooled plants recovered, within 0.005). **P2 pass** (-0.05 and -0.10 detected). **P3 fails**: the half-sample plants are not averaged by row share. P4: smallest detected pooled plant **-0.03**; the design's detectable elasticity is about -0.03.

**Reading.** The pipeline is unbiased for a uniform response and would have found Hirth-sized (-0.05) or smaller (-0.03) pooled responses; the pooled null is therefore a real bound, about -0.02 on the negative side. P3 shows the pooled estimate is a **first-stage-weighted average of the regimes**, about **30% 2019-21H1 and 72% 2021H2-23** (0.0296/0.10 and 0.0723/0.10): the wind-driven price variation is larger in the crisis period. Applied to the real run, 0.30 x (+0.0376) + 0.72 x (-0.0137) = +0.001, consistent with the pooled +0.0001. Consequence under P3's rule: the pooled null is dominated by 2021H2-23 and **regime bounds are mandatory**: 2019-21H1 [-0.013, +0.107] and 2021H2-23 [-0.029, +0.009] from the real run; both rule out responses more negative than about -0.03, but the pre-crisis regime is imprecise on the positive side and says little beyond that.
