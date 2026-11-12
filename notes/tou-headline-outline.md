# Time-of-use thread: headline and results outline (draft, 2026-11-12)

Branch `tou-policy-prices`. Every number below is in `docs/specs/2026-11-11-tou-hardening-design.md` with its script and csv in `outputs/tables/tou_*`.

## Headline

**Spain's June 2021 time-of-use reform cut evening electricity demand by about 4–5% relative to night. On the method of Enrich, Li, Mizrahi and Reguant this is a within-day price elasticity of about −0.1 for aggregate low-voltage demand. It is a response to the reform as a whole, not a clean price slope: it does not scale with later charge changes.**

One-sentence claim: *the reform worked, the implied elasticity is in the paper's range, and what the reform changed is not only the price.*

## What we did (method)

- Replication of the paper's design: difference-in-differences on LASSO prediction errors (Burlig et al. 2020), E0 (measured demand below 1 kV, ESIOS 1201) against Portugal, with France as a second control.
- The paper's first step as the guiding estimator: one LASSO per area and hour, month/weekend/holiday dummies, hourly, daily-minimum and daily-maximum temperature with all interactions, 10-fold cross-validation with the one-standard-error rule, no trend (`tou_lasso_paper.py`). Our earlier pooled LASSO is reported beside it.
- Triple difference: evening peak 18–21h against night, working days against weekends and holidays.
- The paper's elasticity regression: policy-instrumented price, Equation (4), Table 6 format (`tou_elasticity_paper.py`).
- **Every test had its stop rules written and committed before the run, and failures are kept** (ledger below).

## Results

1. **The reform effect.** Evening-versus-night demand fell 5.25% (se 0.71, t −7.4) in June–September 2021 (triple difference, Portugal). France as control −4.34%, mean of the two −4.79%, pooled LASSO −4.96%, **paper's per-hour LASSO −3.79% (se 0.39)**. The real date ranks first of 18 placebo break dates; the paper-LASSO errors show no effect in the pre-reform years (0.14%, se 0.19).
2. **The elasticity.** Effect divided by the change in ln relative price (+0.61): −0.086 (DDD), −0.062 (paper LASSO). The paper's own regression, column 4 (the within-day comparison): **−0.100 (se 0.012; first-stage F 80)**, inside the paper's −0.082 to −0.135.
3. **Who responds.** Regulated (PVPC) customers, 23–30% of E0: −3.9% (DDD), elasticity −0.064; the rest of E0 about −5.7%. The response is not concentrated among customers who see the hourly regulated price.
4. **What it is not.**
   - Not a dose-response to the charge. When the evening charge was cut on 16 September 2021 the effect shrank (−5.5% → −1.6%), but the same calendar windows move by +2.75 points in 2019 with no reform. The January 2022 charge rise (energy gap flat) did not deepen the effect beyond the seasonal baseline. Placebo-adjusted charge elasticity +0.02 (se 0.02), band about −0.05 to +0.07.
   - Not stable across the paper's fixed-effect columns: columns 1–3 have weak instruments and near-zero estimates; only column 4 identifies the within-day variation.
   - Not constant in the energy price: the response weakens at high energy prices (−0.066 → about −0.054 above the 90th percentile); the paper found no such effect.

## Rules ledger (pre-registered, outcome as registered)

| test | outcome |
|---|---|
| evening-peak design (six rules) | all pass |
| charge-cut dose-response (six rules) | all pass on the pooled LASSO; B/A proportionality and elasticity stability would fail under the paper's LASSO |
| extended two-channel regression (seven rules) | all pass as written (OLS DDD); under the paper's LASSO the charge coefficient halves (t −1.4) and the energy channel appears |
| charge-change events against the seasonal baseline (six rules) | rules 2–6 fail: the autumn fade is seasonal |
| paper-style elasticity regression (seven rules) | rules 1–6 fail as registered (columns 1–3); column 4 −0.100, placebo passes |

## Limits to state

- Aggregate low-voltage demand: households and small businesses together, regulated and free-market. Not a household elasticity; Fabra et al. (2021) study regulated households and are not directly comparable.
- Identified from one reform in one year; the reform bundles the price change with awareness and the new tariff structure.
- Portugal is the only untreated area with weather data; France enters without weather.
- Industry was also treated by the same reform (six-period tariffs), so it is not a placebo; the 2.0TD charge series stops us from running an industry elasticity without hand-building charges.
- Seasonal shape changes specific to Spain in 2021 are bounded by the cross-fitted placebo years (which swing by about 2 points), not removed.
- The post-hoc reading of column 4 is not a registered result.

## Open items before writing

1. Confirm the start date of the new tolls for the larger tariffs (CNMC resolution or BOE).
2. Decide whether column 4 is the headline elasticity or the pooled Wald range −0.06 to −0.10.
3. Optional designs: industry as a treated group (needs a hand-built 3.0TD/6.xTD charge table); a regulated-only version of column 4 on ESIOS 352; a longer placebo window.
