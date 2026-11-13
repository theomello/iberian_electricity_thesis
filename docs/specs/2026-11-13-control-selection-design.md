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
