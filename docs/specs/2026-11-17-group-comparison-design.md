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
