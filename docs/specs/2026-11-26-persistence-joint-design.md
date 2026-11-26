# Persistence 2022-25 with counterfactual-calendar controls (proposal)

**Status: proposed 2026-11-26, not registered, not committed. Binding when the user confirms and this file is committed; the run
follows that commit.** A robustness check of the registered persistence results
(`2026-11-23-firm-calendar-persistence-design.md`, run 2026-11-24) for the shape drift found in
`2026-11-26-tariff-drift-design.md` and `2026-11-26-joint-regression-design.md`. It does not replace those verdicts; it is reported beside them.

**What is not blind.** The registered Part A results for both groups (medium firms −0.283, p 0.002, R1-R9 all pass; large industry
−0.136, p 0.017, R3, R5 and R8 fail, shift in 6.3 only), the per-year values and the placebo b_Y. Not computed: any regression with the
shifted-calendar controls.

## In one example
In the persistence design each year's summer is reduced to cells (part of the summer × hour), and the hour share of the daily load in a cell
is regressed on the cell's period step d (how many periods dearer the hour became under the new calendar). A shape drift in the firms'
evening-versus-night profile moves hour shares in patterns that look like d, in placebo years as in post years. Adding the steps of calendars
that were *not* introduced (the same calendar shifted by 3-9 hours) to the same regression asks: does the real step explain the hour shares
beyond what dose-like patterns explain? If the effect survives, the persistence result is not a drift artefact.

## Design (Part A, summers, both groups)
- **Cells, years, placebo and post sets, statistic, inference:** exactly as the registered design (medium firms: part × hour, 120 cells,
  placebo summers 2014, 2017, 2018, 2019; large industry 6.2+6.3+6.4: series × month × hour, 288 cells, placebo 2014-2019; post 2022-2025;
  raw b_Y, pooled mean null with √(1/K + 1/S), conservative version, trend null).
- **Counterfactual calendars.** For shift k in ±3…±9 hours, the new period of (date, hour) is the real new period of (date, (hour + k) mod 24)
  (`tou_tariff_schedule.new_period_6` replaced by the shifted version in `firm_persistence_step0.d_table`); the old calendar is unchanged.
  The cell step d_k(c) is built as d(c) is. Screen: a calendar is used if |corr(d_k, d)| ≤ 0.5 over the group's summer cells.
- **Controls.** The principal components of the screened d_k over the group's cells that explain 90% of their variance, at most 5
  (computed once per group, so the controls are the same in every year). Added to every year's regression (placebo and post), with the
  registered hour effects or intercept form: s_Y(c) = α_Y(h) + b_Y·d(c) + Σ_j γ_Yj·PC_j(c). b_Y^joint is the coefficient on d.
- **Large industry per tariff.** Reported separately for 6.2, 6.3 and 6.4 (descriptive, as the registered series-alone results).
- **Part B is not re-run** (its day-type coding makes shifted calendars a different object); Part A is the primary result.

## Rules, set before the run
- **P0 Reproduction (gate).** With no controls the code reproduces the registered Part A numbers to 1e-4: medium firms b̄ − m = −0.283
  (p 0.002, interval [−0.390, −0.177]); large industry −0.136 (p 0.017, [−0.258, −0.015]); the per-year values. Else stop.
- **P1 Feasible.** After the registered effects and the controls, d keeps at least 20% of its variance over the cells, for each group.
- **P2 No drift.** The placebo slope per year of b_Y^joint is not established (|slope| < 1.5 × its se), for each group.
- **P3 Not noisier.** The placebo sd s of b_Y^joint is at most the registered one, for each group.
- **P4 Detection kept.** Pooled mean-null one-sided p ≤ 0.05 (R1) and conservative version p ≤ 0.10 (R2), with b̄ − m < 0.
- **P5 Trend and stability.** Trend-null one-sided p ≤ 0.10 (R8), dropping each post year p ≤ 0.10 (R7), every post year b_Y − m < 0 (R9).
- **P6 Consistent with the registered result.** b̄ − m with controls lies inside the registered pooled 95% interval. If it lies outside, the
  controls move the estimate beyond its own placebo-based uncertainty and the difference is reported as the finding.
- **Reported, no verdict:** R3 (solar-robust cells), R4 (wrong hours), R5 (price control), R6 (no August), each with the controls added;
  per-year effects; the per-tariff effects.
A group is **robust to the drift** if P1, P2, P4, P5 and P6 all pass. Failed rules are recorded and kept; no other control set, shift range or
cell definition is tried after a failure.

## What each outcome means
- Medium firms robust: the −0.025 persistence elasticity is not a drift artefact; reported with its robustness row.
- Medium firms not robust (P4 or P5 fails): the persistence rests on the drift or on dose-like patterns; the registered result stays, with the
  robustness failure stated beside it.
- Large industry robust: the −0.136 shift, concentrated in 6.3, stands against the drift. Not robust: the weak persistence is read as
  consistent with the drift story (and the registered verdict, R5 fail, stays).
- P6 fails for a group: the controls change the estimate materially; both estimates are reported, neither is called the main one.
- P2 fails: the drift is not absorbed in that group (as for 6.3 in the 2021 test); say so, report the effect against both nulls.

## Threats
Medium firms have four placebo years (S = 4): the slope and spread rules have almost no power there, as the registered design already
stated; the cell-level step d is highly collinear across calendars by construction, so P1 may fail (the cells are few: 120 and 288); shifted
steps are patterns, not an independent treatment, so the coefficient is "beyond dose-like shapes" and conservative; the post years
2022-23 are under the Iberian gas cap and crisis prices (R5 limitation unchanged); the 6.2 composition break of October 2018 stays.

## Code and outputs
New script `scripts/analysis/firm_persistence_joint.py` (reuses `firm_persistence_step0` cells and d tables and `firm_persistence.run`/`stats_of`/`trend`,
with the controls added through the regression's extra columns); committed before its single run. Outputs
`outputs/tables/firm_persistence_joint{,_summary}.csv`. No new data and no refits; expected run time minutes.
