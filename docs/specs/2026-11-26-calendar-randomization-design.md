# Counterfactual calendars within each year, and a local-level model for the drift (proposal)

**Status: proposed 2026-11-26, not registered, not committed. Binding when the user confirms and this file is committed;
the run follows that commit.** Cached errors only; no refits (the errors do not depend on the dose). Follows
`2026-11-26-tariff-drift-design.md` (Steps 3, 1, 2), `2026-11-26-offset-stability-design.md` and `2026-11-26-drift-location-design.md`.

**What is not blind.** Real-calendar betas for every tariff and summer (6.4: +0.36, +0.42, +0.35, +0.25, +0.20, +0.37; 6.3 falling
from +0.42 to +0.04; 6.2 flat), the spring betas of 6.4 and the fact that spring and summer betas are uncorrelated across the six
years (r = 0.06, computed after the fact, 2026-11-26: the spring cannot calibrate the summer, so no spec uses it). Not computed:
any beta for a counterfactual calendar, and any local-level fit.

## Part 1: counterfactual calendars inside the same summer

### In one example
The reform's new calendar makes weekday hours 9-14 and 18-22 dearer. A 6.4 plant's load profile is, in any year, correlated
with such a pattern, which is why the placebo summers give +0.33. Ask a different question inside one summer: what would the
estimator give if the dearer hours were 12-17 and 21-01 instead (the same pattern shifted by three hours)? If shifted calendars also
give about +0.3 in a no-reform summer, the offset is generic to dose-like patterns; the reform's effect is then the *difference
between the real calendar and the shifted ones in the same year*, and a drift that moves all such patterns together cancels.

### Design
- **Counterfactual calendars.** For shift k in {±3, ±4, ±5, ±6, ±7, ±8, ±9} hours, the new period of (date, hour) is the real new
  period of (date, (hour + k) mod 24) with the same day types, months and period prices; the old calendar stays as it is.
  Dose = ln[(E + T_new + W_new)/(E + T_old + W_old)] with the shifted new periods (same code as the real dose,
  `tou_industry_regulated_price.tables` with `tou_tariff_schedule.new_period_6` replaced by the shifted version).
- **Screen.** Over the post window (working days, all hours) a counterfactual calendar is used only if the correlation of its dose
  with the real dose is at most 0.5 in absolute value. The kept set is reported; a stricter set (at most 0.3) is a sensitivity.
- **Estimator.** The baseline for each of 6.2, 6.3, 6.4 separately (`tou_drift_location.eta_variant`), for each calendar, for 2021
  and each aligned placebo summer 2014-2019. Statistic per summer Y and tariff: β_real(Y), β_cf(Y, k), their mean
  m_cf(Y), and the **within-year contrast Δ(Y) = β_real(Y) − m_cf(Y)**.
- **Inference.** The six placebo Δ(Y) give the no-reform distribution of the contrast: prediction t-test (S − 1 d.f.) of Δ(2021),
  as the six-summer test, one-sided.

### Rules, set before the run
- **C0 Reproduction (gate).** The real-calendar betas reproduce the committed rows (6.2 −0.06369 / +0.01955 / 0.01684;
  6.3 −0.23291 / +0.19751 / 0.1808; 6.4 −0.33676 / +0.32562 / 0.0830) to 0.0015.
- **C1 Enough counterfactuals.** At least 6 calendars pass the 0.5 screen for each tariff, else the design is not run for it.
- **C2 The key assumption (6.4's offset in 2021).** The mean counterfactual beta in 2021, m_cf(2021), is within the placebo range of
  m_cf(Y): prediction t-test with 5 d.f., |t| ≤ 2.57. A pass means the generic offset did not move in summer 2021, tested on calendars
  that are not the reform. A fail means it did.
- **C3 The drift cancels.** The placebo sd of Δ(Y) is at most 0.8 times the placebo sd of β_real(Y) for the same tariff, and the
  slope of Δ(Y) is not established (|slope| < 1.5 × its se). Both hold: the contrast is a drift-free estimate. Else the drift is
  specific to the real calendar's shape and the contrast does not remove it.
- **C4 Detection.** Δ(2021) is negative with one-sided p ≤ 0.05 (reported per tariff whatever C3 says).
- **C5 Not one calendar.** Dropping each counterfactual calendar in turn, m_cf(2021) and Δ(2021) keep their sign and stay within
  0.05 of their values.

### What each outcome means
C2 pass and C3 pass: the offset is generic, stable in 2021, and the contrast Δ is the reform effect without the drift; it replaces
the mean-null and trend-null range for that tariff. C2 pass, C3 fail: the offset is stable but the drift is real and specific
to the calendar's shape; report Δ beside the earlier ranges. C2 fail: the offset moved in 2021; the 6.4 placebo-based effect cannot be
trusted and is reported as a raw −0.34. C1 fail: no estimate.

### Threats
Shifted calendars share part of the real pattern (screened at 0.5, sensitivity 0.3); they are patterns, not an independent
treatment, so Δ is an effect *relative to dose-like patterns* and is read as such; the contrast answers the drift question
only if the drift acts on the patterns together, which C3 tests; the shifts keep the calendar's structure (same hours blocks,
months, prices), so structure-specific features of the real calendar are in the contrast.

## Part 2: a local-level model for the placebo betas (descriptive)
A random-walk-plus-noise model per tariff, β_Y = μ_Y + ε_Y, μ_Y = μ_(Y−1) + η_Y (years 2014-2019; 2020 missing, so 2021 is two steps
past 2019). Variance ratio q = σ_η²/σ_ε² by maximum likelihood on a grid (0 to 10, six points of data, so weakly identified; the
likelihood profile is reported). Predictive distribution of the no-reform value in 2021 at the ML q and at q = 0 (the mean null) and
q = the boundary where the filtered level follows the last observation. Effect = η_2021 − predicted value, with a 95% interval
including the 2021 estimate's se.
- **L1 Report.** q̂, the profile, the predicted value and the effect interval for each tariff.
- **L2 Reading rule.** The model is used to state a range without choosing between the nulls: if the interval at q̂ contains both the
  mean-null and the trend-null effect for 6.3, "unresolved" is the statement; if it excludes zero, the effect is detected under the
  local-level reading. No further model of the drift is tried.

## Data and code
Cached errors, committed tariff and period tables; no new data. New scripts `scripts/analysis/tou_calendar_randomization.py` (Part 1;
about 15 calendars × 7 summers × 3 tariffs ≈ 300 fits, expected run time 30-50 minutes) and `scripts/analysis/tou_local_level.py`
(Part 2, seconds). Outputs `outputs/tables/tou_calendar_randomization_*.csv`, `tou_local_level.csv`.
