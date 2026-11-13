# Choosing the Portuguese control for the substitution elasticities (pre-registration)

**Status: pre-registered 2026-11-13 (rules C1-C5 confirmed by the user the same day), before any estimation of the loadings or of the six candidates beyond what was already reported.** The rules are binding once this file is committed; the first run happens after that commit. Follows `2026-11-13-nested-ces-design.md`, whose σ_L depended on the control: 0.17 (REN, loading fixed at 1), 0.21 (none), 0.30 (regulated unit, loading fixed at 1); σ_U 0.070-0.077.

**In one example.** The Spanish evening-to-night ratio drifts for reasons unrelated to the reform (EV charging, rooftop solar, teleworking). Portugal's ratio drifts for some of the same reasons and some of its own. Subtracting all of Portugal's drift removes too much if only part is shared, and too little if Portugal is a noisy copy. The right amount to subtract is the *loading*: the slope of Spain's drift on Portugal's, learned before the reform. A noisy control should get a loading below 1.

**Goal.** Make the control a measured, pre-reform choice instead of a fixed one, and report how much of σ_L's dependence survives it. **Not goals:** new data; a new elasticity; rescuing any earlier rule.

## Candidates
1. none (loading 0); 2. REN, loading 1; 3. regulated unit, loading 1 (these three are the earlier ones);
4. **REN with the estimated loading**; 5. **regulated unit with the estimated loading**; 6. **both, with estimated loadings** (the pre-reform best linear predictor of Spain's drift from Portugal's two series).

## Estimation of the loadings (pre-reform data only)
For each ratio `k ∈ {P/V, M/V}`: the leave-year-out LASSO residual of Spain (2018, 2019 and 2020 each left out in turn, lockdown months out) regressed on the same residual of the control(s), no constant, standard errors clustered by week: `κ̂_k`. The loadings enter the share system as `Y0_k = ŷ_k(ES) + Σ_c κ̂_{c,k} e_{c,k}` in place of the fixed 1; nothing else changes (nested CES, same sample, instruments and estimator as the nested run).

## Rules, set before the run (confirmed 2026-11-13)
- **C1 The control carries information.** For REN and for the regulated unit, `κ̂` has |t| ≥ 2 in both ratios; a control that fails is reported as equivalent to none.
- **C2 Selection by placebo, fixed beforehand.** Among the six candidates the control with the smallest **root-mean-square of the nine 2019 placebo σ̂_L** (the fake policy path, cross-fitted tastes, as in the nested run) is **the** control; ties within 5% go to the smaller placebo rms of σ̂_U. The post-reform estimates play no part in the selection.
- **C3 The nested result survives.** Under the selected control: σ̂_U > 0 and σ̂_L > 0, the equality σ_U = σ_L still rejected at 5%, σ̂_L > σ̂_U, and the real σ̂_U and σ̂_L each rank in the top 2 of 10 against the placebo.
- **C4 The dependence narrows.** The range of σ̂_L across the three loading-estimated candidates (4, 5, 6) is at most **0.08** (against 0.13 across the earlier three, 0.17 to 0.30).
- **C5 Report the bounds either way.** σ̂_U and σ̂_L under all six candidates are published with the selected one marked; if C4 fails, the claim is the bound across candidates, not the selected value.
No other specification is tried after a failure.

## What each outcome means
C1-C4 pass: the control is chosen on pre-reform evidence, σ_L is read at the selected control, and the remaining spread is smaller than before. C4 fails: the dependence is a feature of the data (shape drifts that differ between the countries), the claim is the bound, and only a better Portuguese series (the open item) would shrink it. C1 fails for the regulated unit: it adds nothing beyond REN.

## Threats
The loadings are estimated on residuals that include the placebo years, so the placebo windows are not wholly out of sample for them (one parameter per ratio; the fake path has no real effect to leak); the leave-year-out residual of 2020 excludes the lockdown months, leaving fewer days; the regulated unit has customer migration (the replication's problem), which a loading cannot remove, only discount.

## Results (run 2026-11-13, `scripts/analysis/tou_control_selection.py`, outputs `outputs/tables/tou_control_selection_{loadings,candidates,placebo}.csv`; registered in 7f847c2)
**C1 fails for the regulated unit and passes for REN; C2 selects "both (estimated)"; C3, C4 pass.**

**Loadings** (Spain's pre-reform residual on Portugal's, 670 weekdays, leave-year-out): REN **0.30** (peak/valley, t 10.9) and **0.26** (mid/valley, t 9.4); regulated unit **0.10** (t 4.3) and **0.02** (t 0.6); with both, REN 0.28 / 0.26 and the regulated unit 0.05 (t 2.4) / −0.01 (t −0.4). The earlier fixed loading of 1 gave REN three to four times too much weight and the regulated unit ten to a hundred times too much.

| Control | σ_U (se) | σ_L (se) | Equality p | Placebo rms σ_U / σ_L | Ranks (of 10) |
|---|---|---|---|---|---|
| none | 0.0703 (0.0033) | 0.2140 (0.0132) | < 0.0001 | 0.0045 / 0.0115 | 1, 1 |
| REN, loading 1 | 0.0738 (0.0034) | 0.1669 (0.0129) | < 0.0001 | 0.0057 / 0.0098 | 1, 1 |
| regulated unit, loading 1 | 0.0770 (0.0079) | 0.3000 (0.0300) | < 0.0001 | 0.0059 / 0.0136 | 1, 1 |
| REN, estimated | 0.0708 (0.0031) | 0.2018 (0.0116) | < 0.0001 | 0.0045 / 0.0094 | 1, 1 |
| regulated unit, estimated | 0.0724 (0.0036) | 0.2157 (0.0133) | < 0.0001 | 0.0042 / 0.0114 | 1, 1 |
| **both, estimated (selected)** | **0.0725 (0.0032)** | **0.2012 (0.0116)** | < 0.0001 | 0.0044 / 0.0094 | 1, 1 |

| Rule | Result | Verdict |
|---|---|---|
| C1 loadings carry information | REN yes (t 9-11); regulated unit no (t 0.6 on the mid/valley ratio): equivalent to none | REN pass, regulated unit **fail** |
| C2 selection | smallest placebo rms of σ̂_L is 0.0094 (REN estimated and both estimated); candidates within 5%: REN (loading 1), REN (estimated), both (estimated); ties go to the smaller σ̂_U rms: **both (estimated)** (by 0.0001 over REN estimated) | selected |
| C3 nested result survives | both positive, equality rejected, σ̂_L > σ̂_U, both rank 1 of 10 | pass |
| C4 dependence narrows | range of σ̂_L across the three estimated candidates **0.014** (bar 0.08); across the earlier three 0.133 | pass |

**What it says.**
- **The control dependence was mostly the fixed loading.** With loadings estimated before the reform, every candidate gives σ_U 0.071-0.073 and σ_L 0.20-0.22; "none" (0.214) sits inside the same band. The earlier 0.17 (REN at loading 1) subtracted too much of a noisy copy, and the earlier 0.30 (regulated unit at loading 1) too much of a series that barely tracks Spain's drift. **The result to quote is σ_U ≈ 0.07 and σ_L ≈ 0.20 (selected control: 0.0725 and 0.2012, se 0.003 and 0.012), replacing 0.074 and 0.167 of the nested run.**
- The nested conclusions stand under every candidate: the margins differ (p < 0.0001), the mid-to-valley margin is about three times the peak one, both far below 1, both rank 1 of 10 against the placebo.
- **The control matters little for noise:** the placebo rms of σ̂_L moves from 0.0115 (none) to 0.0094 (selected), an 18% reduction; the loadings say Portugal's evening-to-night drift tracks Spain's weakly (a coefficient near 0.3). The selection by 0.0001 between "both" and "REN estimated" is a tie; the regulated unit's coefficient in "both" is not distinguishable from zero.

**Limits.** The loadings use residuals that include the placebo years (one parameter per ratio, no real effect to leak); the leave-year-out residuals for 2020 lack the lockdown months; a loading below one can also reflect noise in Portugal's series (attenuation), which would mean the true common drift is larger than the estimate and Spain's remaining drift sits in the residual the placebo spread measures. The Portuguese control for 2018-2021 stays an open item: a cleaner series would sharpen the loading.
