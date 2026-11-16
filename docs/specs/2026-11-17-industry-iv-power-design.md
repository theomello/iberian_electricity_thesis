# Industrial IV: more power for the bid-curve instrument (proposal)

**Status: proposed 2026-11-16, not registered. Binding when the user confirms and this file is committed; the run follows that commit.** Follows `2026-11-17-industry-iv-bid-curve-design.md`: first stage F 19.7, placebo and balance pass, V3 elasticity -0.036 [-0.080, +0.010], but the rank-of-t p (0.010) and the permutation Anderson-Rubin p (0.178) disagree and the interval includes zero (B6 fails on the interval); wind-only instrument weak (F 8.5). This spec changes **power**, not identification: same instrument, same pipeline (week-on-week difference, boosted double ML with realised wind and PV, curve slope and zero-price block as controls), same placebo.

**In one example.** Two coins are tossed 1,000 times: if one comes up heads 53% of the time, you cannot tell it is biased; with 5,000 tosses you can. Our estimate of -0.036 has a standard error of about 0.015, and the 'detectable' size is 0.042, so it sits just inside the zone we cannot resolve. Adding hours (weekends, 2024-2025) and using one well-weighted instrument instead of two, one of them weak, lowers the standard error and the AR test's price for having two instruments. Whether the answer becomes clearer, or stays 'small', is then the finding.

## Changes (the three, fixed in advance)
1. **More hours.** (a) Weekends and national holidays are included (day-of-week and a holiday flag enter the learner; the lockdown block 2020-03-01 -> 2020-06-30 stays out); (b) the window runs 2019-01-01 -> **2025-09-30** (curve cache and all inputs exist; ESIOS industrial load to 2026-04). Hours on days with a broken clearing identity or `valid` false are dropped by the gate below; days with 23 or 25 periods are dropped. 2025 resolution changes (intraday and PDBF 2025-03-19; day-ahead 15-minute from 2025-10-01) do not touch the day-ahead hourly series used up to 2025-09.
2. **One instrument, weights fixed on the other half.** The two simulated price effects `dp_w` and `dp_s` are combined into one instrument `dp_c = b_w dp_w + b_s dp_s` (residualised), where (b_w, b_s) are the first-stage coefficients of the residualised price on the two residualised effects **estimated on the other half of the sample** (halves: odd and even ISO weeks of the year, so both are spread over every year and regime). Rows of even weeks use weights fitted on odd weeks and vice versa. The estimate is then a just-identified 2SLS with one instrument; inference by the rank of |t| and the one-degree-of-freedom permutation Anderson-Rubin set (1,000 permutations across days within year-month, hour matched, grid ±40 SE), as before. Wind-only and solar-only slopes (own instruments, no combination) are reported for the J-type check.
3. **ML first stage (robustness).** The optimal instrument is the cross-fitted prediction of the residualised price from `[dp_w, dp_s]`, the curve slope, the zero-price block, hour and month, by `HistGradientBoostingRegressor` (same settings as the learner, 10 time blocks, 14 days purged each side); the elasticity with this instrument is compared with the main one.

## Rules, set before the run
- **P1 Curve check (gate).** Re-cleared price within €0.50 of OMIE in at least 95% of valid hours of the extended sample. *Fails:* no estimation.
- **P2 First stage (stop rule).** Date-clustered first-stage F of the price on the combined instrument is at least 10 and the detectable elasticity (2.8 × SE) at most 0.25. *If P2 fails, no slope is computed* and the industrial IV is closed with the bid-curve bound.
- **P3 Placebo outcome.** Lag-7 load: randomization p above 0.05 and absolute 'elasticity' below 0.01. *Fails:* the extension added a weather or regime channel (2024-25 curtailment, weekend patterns); named after the split below.
- **P4 Balance.** Temperature does not predict the residualised combined instrument (Bonferroni, cluster-robust, p above 0.05).
- **P5 Estimate.** Elasticity negative, absolute value at most 1, **and both** the rank-of-t p and the permutation-AR p at most 0.05, interval excluding zero. *Fails with P3 passing:* a bounded small response; the two tests disagreeing again is itself reported (it points to weak-instrument behaviour).
- **P6 Consistency with the earlier sample.** The same pipeline on the original sample (weekdays 2019-2023) with the combined instrument gives an elasticity inside the bid-curve interval [-0.080, +0.010] and with first-stage F reported. *Fails:* the combination, not the added hours, changed the answer.
- **P7 Where the new hours change things (description).** Elasticities for: original weekdays 2019-23 (P6), weekends and holidays only, 2024-2025 only; each with F; a subset with F below 10 is reported as weak and not interpreted.
- **P8 Stability.** Slopes by year 2019-2025 (2020 outside the lockdown block): equality test over the years with F at least 10, the rest described.
- **P9 ML first stage.** The elasticity with the ML instrument lies inside the P5 randomization interval and its F is at least 10.
- **P10 Hour blocks (exploratory, no pass/fail).**

A failed rule is recorded and kept; nothing else (other instruments, other learners, other windows) is tried after a failure.

## What each outcome means
P1-P5 pass: a detected industrial impact elasticity, placebo-clean, comparable with the household one, from a design that spent its power on data, not on specification search. P5 fails with the others passing: the response is bounded small; with the detectable size now smaller, that bound is the contrast with households. P3 fails: the added hours bring a channel the earlier sample did not have; P7 shows which block does it. P2 fails: the combined instrument is not strong enough and the industrial IV closes.

## Expected power (stated before the run so the result can be read against it)
The earlier SE of the elasticity was 0.015 (detectable 0.042) with 21,636 weekday hours. Weekends, holidays and 2024-25 raise the hours to about 50,000-55,000, which on a root-n rule gives an SE of about 0.010 (detectable about 0.028). An elasticity of -0.036 would then be detectable at roughly 80% power; a true value near zero or below -0.02 would remain hard to tell from zero.

## Threats
Weekends and holidays have different industrial load, different flexibility and different curves (more zero-price hours); 2024-25 has more negative-price hours, batteries and curtailment, so the curve slope and the simulated effect behave differently; the weights fitted on the other half are two numbers, so overfitting is minimal, but halves of adjacent weeks share regimes; the combined instrument inherits the bid-curve instrument's assumption that the day-ahead price channel works through the curve (B3: raw pass-through was 0.13); realised wind and PV are REE real-time (peninsular); the 2025 months with a broken clearing identity (2025-03-19 -> 2025-06-09) are dropped, which thins the sample.

## Data and code
Same as the bid-curve spec, window extended to 2025-09-30. New code `scripts/analysis/industry_iv_power.py` (imports from `industry_iv_bid_curve.py`, `industry_iv_estimation.py`, `industry_iv_noise_reducers.py`); outputs `outputs/tables/industry_iv_power{,_checks}.csv`. Seed 20261117.

## Results (run 2026-11-16; `industry_iv_power.py`, committed before the run; outputs `industry_iv_power{,_checks}.csv`)

Combined bid-curve instrument, weights fitted on the other half (odd/even ISO weeks), impact elasticity at the mean price.

| Sample | n (hours) | F | Elasticity | Randomization interval | p (t-rank / AR) |
|---|---|---|---|---|---|
| **Extended, 2019-01 -> 2025-09, all days (main)** | 41,150 | 114 | **+0.017** | [-0.063, +0.175] | 0.56 / 0.56 |
| Original sample (weekdays 2019-23), combined instrument (P6) | 21,636 | 38 | -0.031 | [-0.055, +0.006] | 0.010 / 0.114 |
| Earlier two-instrument result (bid-curve spec) | 21,636 | 19.7 | -0.036 | [-0.080, +0.010] | 0.010 / 0.178 |
| Weekends and holidays only | 11,438 | 45 | -0.028 | [-0.064, +0.010] | 0.033 / 0.133 |
| 2024-25 only | 11,366 | 160 | +0.091 | [-0.446, +0.483] | 0.32 / 0.37 |
| Placebo outcome (lag-7 load), extended | 41,150 | 111 | -0.003 | [-0.019, +0.021] | 0.71 / 0.72 |

| Rule | Result |
|---|---|
| P1 curve check | pass (100.0% of 53,273 valid hours) |
| P2 first stage (stop) | pass: F 114; detectable elasticity **0.091** |
| P3 placebo | pass: -0.003, p 0.71 |
| P4 balance | pass: p 0.43 |
| P5 estimate | **fail**: +0.017, wrong sign, p 0.56 / 0.56, interval wide |
| P6 consistency | pass: original sample -0.031 inside the earlier interval; the single combined instrument narrowed the interval (width 0.061 against 0.089) |
| P7 (description) | weekends and holidays -0.028, consistent with the weekday result; 2024-25 +0.091 with SE 0.070: uninformative |
| P8 stability | pass on years with F >= 10 (equality p 0.33): 2019 +0.042, 2020 -0.033, 2022 -0.036, 2023 -0.015, 2024 +0.006, 2025 +0.185 (2021 F 1.0 excluded) |
| P9 ML first stage | **fail**: F 3.2 (the boosted first stage is weaker than the linear combination), elasticity +0.163, interval unbounded |
| P10 hour blocks (exploratory) | night +0.019, day +0.007, evening +0.032; all intervals include zero |

**Reading.** The power expectation registered before the run did not come true: the extended sample's standard error is 0.032 (detectable **0.091**), about three times the expected 0.010, so more hours made the interval wider, not narrower. The weekday and weekend results up to 2023 agree (about -0.03), and the combined instrument improved the original sample slightly (interval width 0.061 against 0.089, F 38 against 19.7). The widening comes from 2024-25: in 2025 the elasticity is +0.185 with SE 0.14, and the pooled 2024-25 slope has a larger SE than 2024 alone (0.070 against 0.015). A single slope fitted across subperiods with different responses inflates the sandwich residuals; that is consistent with a regime break after 2023 but does not prove one. A hypothesis, **not tested**: the April 2025 blackout and the reinforced-operation regime that followed, more zero- and negative-price hours, and batteries changed how the offer curve and industrial load relate. The 2025 months with a broken clearing identity (2025-03-19 -> 06-09) also thin the 2025 sample (valid hours 43% in May 2025).

**Statement that stands.** Industrial impact elasticity near zero and small in absolute value: -0.03 (2019-23, weekdays and weekends) with 95% randomization interval about [-0.06, +0.006]; not detected under the registered both-tests rule (t-rank p 0.010 against AR p 0.11); the full 2019-2025 window cannot narrow it. The industrial IV is closed by the registered rules.
