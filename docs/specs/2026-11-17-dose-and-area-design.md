# Data-driven dose and area heterogeneity (proposal)

**Status: proposed 2026-11-17, not registered. Binding when the user confirms and this file is committed; the first run follows that commit. Part A runs first; Part B only if its own step-zero check passes.** Follows `2026-11-17-randomization-inference-design.md` (RI0-RI6 passed: household η −0.101, randomization interval [−0.122, −0.079]).

**In one example.** The elasticity is the response of load to the change in price, and the price change depends on what households pay for energy besides the tariff. If energy costs €60/MWh, moving the evening tariff from 90 to 110 is a 12% price rise; at €150/MWh it is 8%. The same load response then reads as a different elasticity: the elasticity is the load response divided by the dose, so a smaller dose means a bigger elasticity for the same response. The dose depends on two things we assumed: the energy price and the share of customers on the 2.0 tariff. But the *shape* of the response across the day (evening down, night up) also depends on those two numbers. If the data prefer a particular energy price and mix by the shape of the response, we can estimate them instead of assuming them.

## Part A: estimate the dose parameters from the response shape
- **Dose.** `dp_h(E, w) = w ln[(E + T2_new,h)/(E + T2_old,h)] + (1−w) ln[(E + T3_new,h)/(E + T3_old,h)]`, E the energy price (€/MWh), w the weight of the 2.0 tariff. Central: E = window mean (about €100, the paper's convention), w = 0.69.
- **Grid.** E ∈ {40, 60, 80, 100, 120, 150} × w ∈ {0.5, 0.6, 0.69, 0.8, 0.9}, plus the hourly-price variant (E_h) at the same weights: 35 points.
- **Fit criterion.** For each grid point, the residual sum of squares `RSS(E,w)` of the Equation 4 regression of household E0 against Portugal on the dose (η free), with the same fixed effects and cross-fitted errors as the randomization-inference run. The data-selected dose is `argmin RSS`. Noise in the search is handled by repeating it in every placebo window.
- **Search gain.** `G = RSS(paper convention) − RSS_min` (fit improvement the search finds). Compared with the same `G_s` in each of the 109 placebo windows, where the search is re-run with the placebo window's dose. The data identify the dose only if the real `G` exceeds what the search finds from noise.
- **Rules, set before the run.**
  - **A0 Windows.** The same 109 placebo windows as the RI run (reuse the cached errors).
  - **A1 Dose identified.** The minimiser is interior in E (not 40 or 150) and the real `G` is above the 95th percentile of the placebo `G_s`.
  - **A2 Elasticity at the selected dose.** If A1 passes: η at the selected dose lies in [−0.15, −0.05] with a one-sided randomization p ≤ 0.05, the placebo η_s re-estimated at each window's own selected dose.
  - **A3 Narrowing.** If A1 passes: the set of grid points whose `G` is within the placebo 95th percentile of the best fit (the 'confidence set' of dose parameters) gives an η range narrower than the current −0.066 to −0.099 (width less than 0.033).
  - **A4 If A1 fails:** the dose is not identified by this data; the paper's convention stays primary, the sensitivity range −0.07 to −0.10 is the reported uncertainty, and nothing further is tried.
- **What it means.** A1-A3 pass: the dose parameters are estimated, not assumed, and the elasticity's range is data-narrowed; the headline can quote the data-selected η with its randomization interval. A1 fails: the response shape across the day does not distinguish the dose variants, so the size remains model-dependent and the headline reports the range.

## Part B: area heterogeneity (only if A completes; uses the per-capita area panel)
- **Statistic.** The weekday-peak effect of each of the five Spanish regulated areas (Endesa, Iberdrola, Naturgy, EDP, Repsol) against the Portuguese control, per supply point, and the area-specific column-4 elasticities, at the dose chosen in Part A (the paper's convention if A fails).
- **Test.** Heterogeneity beyond noise: the cross-area variance of the five peak effects in the real window against the same variance in the 19 existing placebo windows of the area panel.
- **Rules.**
  - **B0 Step zero (no outcome):** per area, the number of supply points and the placebo standard deviation of its peak effect; an area with placebo sd above 3 points is dropped from the heterogeneity test.
  - **B1 Heterogeneity exists.** The real cross-area variance exceeds the 95th percentile of the 19 placebo variances.
  - **B2 Sign.** The peak effect is negative in at least four of five areas.
  - **B3 If B1 fails:** the areas cannot be told apart from noise; report the pooled estimate only and the five area estimates descriptively.
  - **B4 Mix check (step zero):** whether CNMC or retailer data give a tariff mix or PVPC share by area. If not, skip a dose-response by mix and say so.
- **What it means.** B1 passes: elasticities differ across areas beyond noise, a heterogeneity result the paper does not report; the areas' climate and consumer counts are described (not regressed: five points). B1 fails: no heterogeneity can be claimed with five areas.

## Threats
The dose parameters and η are only weakly separated by one summer; the fit criterion uses the response shape that both the elasticity and the dose determine, so a flat RSS is a plausible outcome (A4). The area panel has five treated units and 19 placebo windows. Regulated retailers' customers are not the same as all households, and mix and price are common to all areas in the dose. The area effects carry the level-drift caveat of the Portuguese regulated unit.

## Data and code
`data/cache_tou/cross_tariff_errors.parquet`, `cross_tariff_ri_errors.parquet`, the regulated area panel (`outputs/tables/regulated_area_panel`, `tou_area_panel_pc_*`). New code: `scripts/analysis/tou_dose_search.py` (A), `scripts/analysis/tou_area_heterogeneity.py` (B). Outputs `outputs/tables/tou_dose_search*.csv`, `tou_area_heterogeneity*.csv`.

## Part A results (run 2026-11-17, `scripts/analysis/tou_dose_search.py`; `outputs/tables/tou_dose_search{_grid,_placebo,_summary}.csv`)
**A1, A2 and A3 fail; A4 applies: the dose is not identified by the response shape.** Nothing further was tried.

| Rule | Result | Verdict |
|---|---|---|
| A0 windows | 109, as the RI run | ok |
| A1 dose identified | minimiser at the grid edge (E = 40, w = 0.9, η −0.051); real search gain 2.6e-4 against a placebo 95th percentile of 5.7e-4 (rank p 0.255) | **fail** |
| A2 η at the selected dose | −0.051 (inside the −0.15 … −0.05 band) with randomization p 0.009, but A2 applies only if A1 passes | **fail** (A1 fails) |
| A3 narrowing | 30 of 35 grid points are inside the placebo noise band; their η range is [−0.158, −0.051], width 0.107 | **fail** |

η over the grid (real window, Portugal control) is almost proportional to the dose scale: from −0.051 (E = 40, w = 0.9) to −0.158 (E = 150, w = 0.5), −0.100 at the paper's convention, −0.084 at the hourly price with w = 0.69. The residual sum of squares is nearly flat across the grid: the data cannot tell the energy price from the tariff mix, because both rescale the dose and change its shape only slightly.
Under A4 the paper's convention stays primary and the −0.07 to −0.10 range (the dose sensitivities already reported) is the uncertainty to quote; the wider grid here (E up to €150, w down to 0.5) is a bound, not a result.
**One thing the placebo windows show:** in 75 of the 109 placebo windows the search picks the hourly-price dose (E_h) as best, against 19 for E = 40 and 15 for E = 150. In windows where nothing happened, the hourly dose fits best, which means its shape tracks something that is not the reform: the wholesale price itself follows the load pattern, so a dose built from it correlates with demand by construction. That is a reason not to prefer the hourly variant as the primary dose, and it settles the earlier question: the hourly −0.079 is not a better-identified number than the fixed-price ones, and the choice stays with the paper's convention.
Part B (area heterogeneity) is not blocked by A; its step zero (B0) is the next run, with the dose fixed at the paper's convention.
