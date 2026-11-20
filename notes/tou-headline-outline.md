# Time-of-use thread: headline and results outline (draft, updated 2026-11-16)

Branches `tou-policy-prices` (merged, PR #9) and `tou-replication-closure` (per-capita, weather, contrast placebo, industry). Every number below is in `docs/specs/2026-11-11-tou-hardening-design.md` with its script and csv in `outputs/tables/tou_*`.

## Headline — decided 2026-11-20 (supersedes the household-only headline below)

**One table, one estimator (six-summer prediction test, regulated per-period price as the dose):**
- **Large industry (tariffs 6.2–6.4 pooled): −0.15 to −0.32.** Trend null (line through the six placebo summers)
  −0.15, p 0.044; mean null (registered) −0.32, p 0.007. The price-free reduced form, −1.0 point of daily load share
  per one-step dearer period (p 0.0001), does not depend on the null. Source:
  `docs/specs/2026-11-18-industry-regulated-price-elasticity-design.md` (results + amendment A).
- **Households and small business (E0): −0.11** [−0.21, −0.01], p 0.019, placebos centred on zero (mean −0.005), so
  trend vs mean does not arise. Source: `docs/specs/2026-11-18-industry-six-summer-ri-design.md`.
- **Industry's same-hour response to the wholesale price: a precise zero** (wind-speed IV).
- **Replication beside it:** the paper's design (Portugal control) gives −0.06 to −0.09 for E0 (paper: −0.082 to −0.135).

Sentence: *large industry responds one and a half to three times as strongly as households to the regulated period
price, and not at all to the hourly market price: it responds to the price schedule it signs up for in advance.*
Heterogeneity (6.2 −0.06, 6.3 −0.23, 6.4 −0.34; series alone are noisy) is reported as a finding, not a test.
To prepare: why the replication range is smaller and narrower than E0's −0.11 [−0.21, −0.01]; an appendix table of
every headline result against its placebos, failures (E3, E5) included.

## Earlier headline (households only, 2026-11-12/16)

**Spain's June 2021 time-of-use reform cut evening electricity demand by about 4–5% relative to night. On the method of Enrich, Li, Mizrahi and Reguant this is a within-day price elasticity of about −0.06 to −0.09 for aggregate low-voltage demand (evening-versus-night Wald ratios; decision 2026-11-12, reversing the earlier choice of column 4 to lead). The paper's column-4 regression gives −0.10 (se 0.012) and corroborates it; on the rebuilt regulated-area panel column 4 gives −0.085. It is a response to the reform as a whole, not a clean price slope: it does not scale with later charge changes.**

*Status 2026-11-16: the headline stays the Wald range. The per-capita consumer counts are in (CNMC for Spain, ERSE for Portugal) and the area panel was rerun with them and with area weather (MERRA-2): rules 1-6 pass, rules 7 and 8 fail (the level of the weekday peak effect depends on the control: about -8% against the Portuguese regulated unit, -3% against REN). The contrast (peak minus off-peak, -6.9 points) and column 4 (-0.086) do not depend on the control. Details in the "Replication closure" section.*

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

## Replication closure (2026-11-12 to 2026-11-16)

Specs: `docs/specs/2026-11-12-area-panel-percapita-design.md`, `2026-11-12-area-weather-design.md`, `2026-11-16-industry-adjusted-design.md`.

- **Per-capita area panel (counts, version M, Portuguese regulated unit as control).** Rules 1-6 pass: weekday peak -7.76% (t -7.6), mid -5.59%, off-peak -0.86% (ns); 5 of 5 areas negative; column 4 -0.086 (se 0.014, F 872); within 0.3 points of the ESIOS 352 evening-versus-night DDD. **Rule 7 fails** (control swap to REN moves the peak effect by 4.6 points) and **rule 8 fails** (the placebo spread of the off-peak level does not fall: 6.23 against 4.68 without counts).
- **Area weather (MERRA-2, the paper's source; ERA5 stand-in earlier, correlation 0.94-0.99).** Rules W1, W2, W5 pass; **W3 fails** (placebo spread 6.37) and **W4 fails** (control gap 4.62). Weather is not the cause; no further rescue.
- **Why the level drifts (descriptive, post hoc).** Not the counts (steps of 0.3-1.1% a month; Portuguese unit tracks its count over 2018-21), not the weather. Load per consumer in the same month differs by several percent between years by area (Endesa -7% to -8% 2018 to 2019, Portuguese unit +5%), which two training years per month cannot absorb. A limit of the 2018 start, not a defect in the counts. The registered bar (half of the no-counts spread) was too optimistic.
- **Contrast placebo (registered after seeing the earlier placebos, six non-overlapping windows).** Real peak-minus-off-peak -6.90 against placebo contrasts between -4.45 and +3.70 (rms 3.00); C1-C3 pass under both controls. Supporting evidence, not a clean test (six windows; C2 margin 0.9 points).
- **Industry (placebo-adjusted, 2018 and 2019 placebo years).** E0 adjusted -0.090 [-0.119, -0.061] reproduces the household anchor. E1+E2: -0.082 [-0.252, +0.088], placebo years agree but no detectable response. Pooled industry E1-E6: adjusted -0.265 [-0.408, -0.122] but **its placebo years disagree in sign, so no point estimate is reported**. 6.2-6.4: noise. **No industrial elasticity is identified.** The adjusted evening-versus-night effect is about the same for households (-4.4%), E1+E2 (-4.1%) and pooled industry (-3.1%) although the doses are 0.64, 0.16 and 0.12: industry's response is not proportional to the price change.
- **Further extensions run on 2026-11-13 (see memory and specs):** price effect of the load shift (re-clearing the day-ahead curve), CES and nested CES substitution (sigma_U 0.07, sigma_L 0.20 after control selection), fuel-switching and unit-dispatch logits (no fuel-switching elasticity). Pointers: `docs/specs/2026-11-13-*.md`.

## Limits to state

- Aggregate low-voltage demand: households and small businesses together, regulated and free-market. Not a household elasticity; Fabra et al. (2021) study regulated households and are not directly comparable.
- Identified from one reform in one year; the reform bundles the price change with awareness and the new tariff structure.
- Portugal is the only untreated area with weather data; France enters without weather.
- Industry was also treated by the same reform (six-period tariffs), so it is not a placebo; the toll tables were built and the industry elasticity is **not identified** (placebo years disagree; see Replication closure).
- The level of the weekday peak effect on the area panel is control-dependent (-8% against the Portuguese unit, -3% against REN); only the contrast and column 4 are claimed.
- Seasonal shape changes specific to Spain in 2021 are bounded by the cross-fitted placebo years (which swing by about 2 points), not removed.
- The post-hoc reading of column 4 is not a registered result.

## Open items before writing

1. Confirm the start date of the new tolls for the larger tariffs (CNMC resolution or BOE).
2. ~~Decide whether column 4 or the Wald range leads~~ Decided 2026-11-12 (first column 4, then reversed the same day): **the Wald range −0.06 to −0.09 leads** until the per-capita counts are in; column 4 (−0.100, se 0.012, F 80; −0.085 on the area panel) corroborates. Keep stating that columns 1–3 fail the registered rules on the national series and that the reading of column 4 was made after the run. Revisit when the CNMC counts arrive.
3. Optional: a regulated-only version of column 4 on ESIOS 352 (partly redundant: regulated households respond less than the rest); extending the regulated-retailer series back to 2015-2017 would add training years and could shrink the level drift (not pursued; the level is not a claim).
