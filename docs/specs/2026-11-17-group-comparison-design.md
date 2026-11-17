# Do industrial and commercial customers respond like households? A randomization test of the difference (proposal)

**Status: proposed 2026-11-17, not registered. Binding when the user confirms and this file is committed; the run follows that commit. It uses only the window-level estimates already written by `tou_randomization_inference.py` (no new model fits).**

**In one example.** In the summer 2021 window, households' elasticity is −0.10 and the industrial series (E3-E6) shows −0.29. The gap is −0.19. But in the 109 placebo windows, where nothing happened, the industrial-minus-household gap itself wanders: its standard deviation is about 0.2 because the industrial series is so much noisier. If a gap of −0.19 is a common value of that wandering, the data cannot say industry responds more than households; if it lies far outside, they do. The test ranks the real gap among the placebo gaps.

## Statistic
For each group `g` ∈ {E1+E2, IND} (6.2, 6.3, 6.4 descriptive) and each window `s` (real, and the 109 placebo windows of the RI run): `D_g,s = η_g,s − η_E0,s`, the elasticity of the group minus the household one for the same window. Both are Equation 4 elasticities per unit of their own dose, so the difference is a difference in elasticities, not in doses.
- **Null distribution:** the placebo gaps `D_g,s` (drift of the group relative to households).
- **Adjusted gap:** `D_g,real − mean(D_g,s)`; **Fisher-style interval:** `D_g,real − [q97.5, q2.5]` of the placebo gaps.
- **p-value (two-sided):** `p = (1 + #{|D_g,s − m| ≥ |D_g,real − m|}) / (1 + N)` with `m = mean(D_g,s)`; one-sided (group more negative) reported beside it.
- **Subsets:** all 109 windows; non-overlapping (8, spaced at least 107 days); season-matched (26), as in the RI run.
- **Detectable gap:** `2.8 × sd(D_g,s)` over the 109 placebo windows.

## Rules, set before the run
- **C0 Windows.** The same 109 placebo windows (same cached estimates); stop if the file is missing windows.
- **C1 Classification of each comparison (E1+E2, IND), fixed now.**
  - *Distinguishable from households:* two-sided p ≤ 0.10 in the all-window set **and** in the season-matched set, **and** the detectable gap is below the real |gap|.
  - *Uninformative (insufficient power):* the detectable gap exceeds the household elasticity in absolute value (0.10), whatever the p-value.
  - *Not distinguishable:* otherwise.
- **C2 Non-overlapping check.** The classification in C1 is unchanged when p is computed from the non-overlapping subset with the threshold 0.15 (the smallest possible p with 9 windows is 0.11); reported as consistent or not.
- **C3 Direction.** If a group is *distinguishable*, the sign of the adjusted gap is reported (more or less elastic than households); no claim is made about a point elasticity for the group.
No other specification is tried after a failure.

## What each outcome means
Distinguishable: an industrial or commercial response different from the household one is shown with a randomization p-value and a gap interval, which would be the comparison the extension set out to make (the elasticity itself stays descriptive, since the group's own placebo spread is wide). Uninformative: the comparison is reported as such, with the detectable gap, so no claim of equality or difference is made. Not distinguishable: the group could respond like households or differently; the data cannot say.

## Threats
Both elasticities share the same placebo windows and the same Portuguese control, so the difference removes common control noise but not group-specific drift; the industrial placebo means are positive and large (0.06 to 0.31), so the adjusted gap inherits that drift correction; the windows overlap (about 15 independent); the doses of the groups are small and differ (0.04 to 0.16 against 0.64 for households).

## Data and code
`outputs/tables/tou_randomization_inference.csv` and `..._summary.csv`. New code: `scripts/analysis/tou_group_comparison.py`, output `outputs/tables/tou_group_comparison.csv`.

## Results (run 2026-11-17, `scripts/analysis/tou_group_comparison.py`; `outputs/tables/tou_group_comparison.csv`)
C0 passes (109 windows for each series). **C1 classifies both comparisons as uninformative; C2 confirms; C3 does not apply.** Nothing else was tried.

| Group vs households | Real gap | Placebo sd of the gap (all / season-matched) | Detectable gap (all / season-matched) | p two-sided (all / season / non-overlapping) | Classification |
|---|---|---|---|---|---|
| E1+E2 | −0.068 | 0.193 / 0.056 | 0.540 / 0.158 | 0.418 / 0.444 / 0.556 | uninformative |
| IND (E3-E6) | −0.187 | 0.206 / 0.068 | 0.578 / 0.189 | 0.164 / 0.037 / 0.111 | uninformative |
Descriptive (6.2, 6.3, 6.4): gaps +0.02, −0.22, −0.43 with detectable gaps 0.5 to 1.3; no classification.

**Reading.** The registered rule says the design cannot separate a gap from noise: the smallest detectable gap (0.54 and 0.58 in the all-window set, 0.16 and 0.19 in the season-matched set) exceeds the household elasticity itself (0.10). For industry the season-matched p-value is the smallest 27 windows allow (0.037) and the adjusted gap is −0.188 [−0.279, −0.069], in the direction of a stronger response than households, but its size is the same as the detectable gap (0.189), and the season-matched set is two summers. It is not distinguishable by the rule and is recorded as leaning, not as a finding.
**What the rules show about the problem.** The binding constraint is the ratio of dose to noise, not the method. The industrial dose is 0.04-0.07 against 0.64 for households, and the placebo window mean sd is 0.013 to 0.019; an elasticity of 0.1 needs a dose of about 2.8 × 0.0125 / 0.1 ≈ 0.35 to be detected. No tariff series other than households meets that. The off-season windows inflate the placebo spread by a factor of about three (sd 0.19-0.21 across all windows against 0.056-0.068 in the season-matched ones), so most of the noise is seasonal drift of the group relative to households.

## Follow-up check: can E1 and E2 be separated? (2026-11-17, no outcome used)
ESIOS 1202 (E1, ≥ 1 kV and < 14 kV) and 1203 (E2, ≥ 14 kV and < 36 kV) are **voltage bands, not customer sizes or tariffs**; both are populated by 6.1-type customers (with some 3.1 → 6.1). The reform dose depends on the tariff, so splitting by voltage does not give different doses. Doses (evening-minus-night triple difference of the log price change, window mean energy price €100.8/MWh):

| Tariff mix | Dose |
|---|---|
| E1+E2 as assumed (20% 3.1→6.1, 80% 6.1) | 0.163 |
| all customers 3.1→6.1 (upper bound) | 0.229 |
| all customers 6.1 | 0.146 |
| households E0 as assumed (69% 2.0, 31% 3.0) | 0.637 |
| households all 2.0 / all 3.0 | 0.784 / 0.311 |
With a window-mean noise of 0.0186 for E1+E2 (industry noise check), the smallest elasticity detectable is 2.8 × 0.0186 / 0.229 ≈ 0.23 even at the upper-bound dose, above the household 0.10. **The voltage split cannot make the commercial comparison informative; this route is closed.** A pure 6.1 tariff series exists (ESIOS 1369, 6.1A ≥ 1 kV < 30 kV, 2018-2026) but its dose is 0.146, no better. ESIOS 1209 (2.0 tariff alone) is empty before 2024 (`ree-ren-esios-miteco.md`), so there is no pure household tariff series for 2021.
The household dose itself depends on the 2.0 share: 0.784 if all households were on 2.0 against 0.311 if all on 3.0. Household-level data with each customer's tariff type (the GoiEner metadata field `contracted_tariff`) would put that dose ratio of about 2.5 to work as a dose-response across customers.
