# Hydro and levy simulation: reform, levy and tariff-ratio scenarios in one re-clear (pre-registration)

**Status: pre-registered 2026-11-16 (the user confirmed the interpretation and the seven rules; one change, below). Nothing below has been run.** Branch `tou-replication-closure`. Follows `2026-11-13-tou-price-effect-design.md` (the mechanical price effect of the load shift, R1-R5 passed except R5) and `2026-11-13-nested-ces-design.md` (σ_U 0.074, σ_L 0.167; **at registration the selected-control values of `2026-11-13-control-selection-design.md` replace them: σ_U 0.0725, σ_L 0.2012**), and uses the hydro counterfactual machinery of `scripts/analysis/counterfactual_hydro.py`.

**Interpretation (confirmed by the user 2026-11-16).** "The hydro simulation for the levy" is read as: re-clear the day-ahead of the reform window with hydro offered as it was *before* the clawback announcement (1 June 2021), against as it was actually offered, so that the reform's price effect and the levy's can be separated and then combined. If the user meant something else, this document changes before any code is written.

**What was seen before this draft (disclosed).** The reform price effect: evening-minus-night contrast −€2.39/MWh (range −1.7 to −2.4 across level assumptions), placebo rank 1 of 10. The hydro counterfactual to water value over 2019-2025 ("same water": −€0.83 on average, −€2.2 in 2025 evenings). The repo's finding that the hydro offer departure above water value (+0.25 in 2019-2021H1) **stops in June 2021, at the clawback announcement** (`thesis-framework-adopted` memory). Not seen: any re-clear of the 2021 window with hydro moved, or any tariff-ratio scenario.

**In one example.** A June 2021 weekday, 20:00. Two things move the price at once: households shift load away from 20:00 (the reform), and hydro owners stop offering above water value (the announced clawback). Re-clear four times on that hour's curve: actual; reform removed; hydro put back at its pre-announcement offer pattern; both. The reform's effect is the difference between the first two, the levy's the difference between the first and third, and the interaction is how much the reform's effect depends on what hydro is doing. Then replace the actual load shift by what the nested CES says a different tariff ratio would do, and read the same four numbers.

## Questions
1. **Decomposition.** In the reform window (2021-06-01 → 2021-09-14, weekdays), how much of the evening and night price change belongs to the reform's load shift, how much to the hydro offer change at the clawback announcement, and how much to their interaction?
2. **Scenarios.** Using the nested CES (σ_U, σ_L), what would the evening-minus-night price contrast and consumers' euros have been at tariff ratios other than the actual one, under actual hydro and under pre-announcement hydro?
**Not goals:** a new σ or load effect; the legal incidence of the levy (the levy became law on 2021-09-14, the announcement was 2021-06-01: the simulation measures the offer change, not its legal cause); rival firms' reactions; the gas-cap period; industry.

## The four states (per valid weekday hour h)
Curve: the day's effective offer curve (`outputs/cache/step`, `step_curves.reclear` identity). Load: the actual buy side `D`, or `D + ΔQ_h` with the reform removed (`ΔQ_h` as in the price-effect design: period-type DiD effect, energy-neutral level).
- `p_AA` actual curve, actual load (the re-clear of the actual price).
- `p_AR` actual curve, reform removed. Reform effect with actual hydro: `Δ_R^A = p_AA − p_AR`.
- `p_HA` hydro put back at its pre-announcement pattern, actual load. Levy (hydro offer) effect: `Δ_H = p_AA − p_HA`.
- `p_HR` hydro put back, reform removed. Reform effect with pre-announcement hydro: `Δ_R^H = p_HA − p_HR`. Interaction `I = Δ_R^A − Δ_R^H`.

**Pre-announcement hydro.** For each storage-hydro unit with a cost that day (`hydro_cost_daily`, the 30-day water value) and offers in 2021-01-01 → 2021-05-31, the ratio of its movable offered steps' price to its cost, by hour of day (the pre-announcement `k_{u,hod}`); in the window, the unit's movable steps are re-priced at `k_{u,hod} × cost`, the same MW (the "same water" logic: the MW offered are as actually offered, only the price pattern changes). Units without a pre-announcement ratio keep their actual offers. The sample months, the movable-step definition and the iteration are those of `counterfactual_hydro.py` ("same water", main variant). Rivals' offers are held as offered.

## Scenario module (question 2)
For a log tariff-ratio path `z_k = ln(p_k / p̄_k)` other than the actual one (grid below), the load shift by period is the nested-CES share response at the estimated parameters (σ_U, σ_L, with the taste path and the control loadings of the selected control), converted to MW on the day's counterfactual load, energy-neutral by day, and re-cleared in the four states. Grid: the actual ratio times {0, 0.5, 1, 1.5, 2} (0 is the no-reform state). Wholesale feedback to PVPC households is **not** included in the main run (reported as a bound with the factor `1/(1+σΦ)`).

## Uncertainty
2,000 draws: `b_k` from the load model's covariance (as in the price-effect run) and, for scenarios, `(σ_U, σ_L)` from their estimated covariance; the curve and the pre-announcement ratios are taken as known. Week-block resampling of hours for the hydro effect.

## Placebo
The same four-state pipeline in the nine 106-day windows starting 2019-01 → 2019-09 with the fake policy path of the price-effect run, and with the pre-announcement ratios estimated on the 105 days before each placebo window (so the hydro counterfactual is a re-clear with hydro held at its recent pattern: expected effect near zero where no offer change occurs).

## Rules, set before the run
- **H1 The curve is valid.** At least **70%** of post-window weekday hours are `valid` and the re-clear's mean absolute error on them is at most **€0.50/MWh** (the price-effect R1), and with no step moved the hydro module reproduces the cached re-clear in every valid hour (the identity check of `counterfactual_hydro.py`).
- **H2 The levy channel is visible.** `Δ_H` (all valid weekday hours of the window) is **negative with a 95% interval excluding zero and lies in [−€10, −€0.10]/MWh**: hydro offered as before the announcement would have given a higher price than the one observed.
- **H3 The reform effect survives.** The evening-minus-night contrast under actual hydro (`Δ_R^A`) keeps its sign and stays within the range of the price-effect run (−€1.7 to −€2.4), and the same contrast under pre-announcement hydro (`Δ_R^H`) has the same sign.
- **H4 Additivity.** `|I| ≤ 25%` of `|Δ_R^A|` for the evening-minus-night contrast. Pass: reform and levy effects add, and the decomposition is reported as additive. Fail: both are reported and the interaction is the finding.
- **H5 Placebo.** The real `Δ_R^A` contrast ranks in the top 2 of 10 against the nine placebo windows, and the placebo `Δ_H` (hydro held at its recent pattern) has mean absolute value at most **a third** of the real `|Δ_H|`.
- **H6 Scenario closure.** At the actual ratio (multiplier 1) the CES-simulated shift reproduces the estimated period shifts (peak, mid, valley) within the interval of the DiD effects, and the contrast is monotone in the multiplier over {0, 0.5, 1, 1.5, 2} under both hydro regimes.
- **H7 Robust to σ and control.** The sign of the contrast at every multiplier is unchanged with σ_U and σ_L moved by plus or minus the placebo spread of the nested run (σ_U ± 0.011, σ_L ± 0.02, around 0.0725 and 0.2012) and under the three controls of the control-selection run (none, REN, the selected one).
No other specification is tried after a failure.

## What each outcome means
H1-H7 pass: the reform's effect on the wholesale price and the levy's offer change are separated, the scenario module is a usable simulator of other tariff ratios on the actual bid curves, and the unified model is the same module with the demand block replaced. H2 fails: the hydro offer change at the announcement left no visible price trace once everything else is held fixed, and the reform price effect stands alone (the confound flagged in R5 is then small in euros). H4 fails: the reform's price effect depends on the hydro regime, and a single reform number is misleading. H1 fails: stop; the simulation is not reported as a result.

## Threats
Static re-clear: no firm reacts, so effects are first-round; the water budget (lower offers clear in more hours; the "same water" variant holds released water but the 2021 bilateral share is large and held as it was); the pre-announcement pattern is estimated on five months and may not describe June-September hydro conditions (seasonal water values); the announcement and the reform share a date, so the hydro offer change cannot be attributed to the clawback with certainty, only measured; offer limits changed on 2021-07-07 (exclude July as a sensitivity); one regime for the CES parameters; the load effects carry the replication's level caveat (the contrast is robust, the level is not).

## Data (all on disk)
`outputs/cache/step` (hours, market, units, hydro, 2019-01 → 2025-09), `outputs/tables/hydro_cost_daily.parquet`, the load-model errors (`data/cache_tou/price_effect_e0_errors.parquet`), the nested-CES estimates and control loadings (`outputs/tables/tou_nested_ces_*.csv`, `tou_control_selection_*.csv`). New code: `scripts/analysis/hydro_levy_simulation.py`, importing `tou_price_effect` and `counterfactual_hydro`. Outputs `outputs/tables/hydro_levy_simulation_*.csv`.

## Results (run 2026-11-16, `scripts/analysis/hydro_levy_simulation.py`, seed 20261116)

Rules H1, H2, H3, H5 and H7 pass. H4 and H6 fail. Nothing was tried after the failures.

| Rule | Result | Verdict |
|---|---|---|
| H1 curve valid | 96.5% valid hours (bar 70%), identity 100%, 1,761 hours | pass |
| H2 levy channel | Δ_H −€5.63 [−6.47, −4.91]/MWh (actual price 102.94; hydro at pre-announcement pattern 108.57) | pass |
| H3 reform effect | evening-minus-night contrast −2.39 [−2.59, −2.19] under actual hydro; −3.01 under pre-announcement hydro | pass |
| H4 additivity | interaction +0.62 = 26% of the reform contrast (bar 25%) | **fail by a hair** |
| H5 placebo | reform contrast ranks 1 of 10; placebo mean \|Δ_H\| 0.74 vs a third of the real 1.88 | pass |
| H6 closure | model period shifts peak/mid/valley −3.54 / −1.14 / +7.43 against DiD intervals (−2.38,−2.10) / (−0.80,−0.42) / (4.02,4.88): all three outside; monotone in the multiplier under both regimes: yes | **fail** (closure) |
| H7 robustness | contrast negative at every multiplier > 0 in all 3 controls × 5 σ corners × 2 regimes | pass |

Scenario contrasts (selected control, central σ, evening minus night, €/MWh): actual hydro 0 / −2.10 / −4.04 / −5.91 / −7.66 and pre-announcement hydro 0 / −2.47 / −4.93 / −7.27 / −9.58 at multipliers 0, 0.5, 1, 1.5, 2.

Reading. The levy's offer change lowered the price by about €5.6/MWh, and the reform's evening-minus-night effect (−€2.4) stays when hydro is held fixed; the two do not add exactly (the reform effect is 0.6 larger in magnitude if hydro offered as before the announcement). H4 fails by 26% against 25%, so the interaction is reported rather than rounded away.

H6 is the finding that limits use of the scenario module. At the actual ratio the nested CES reproduces the sign pattern but over-shoots the DiD period shifts (peak −3.5 vs about −2.2; valley +7.4 vs about +4.5). The module is therefore a monotone, sign-correct simulator whose **level at multiplier 1 is about 1.6 times the estimated shifts**; scenario euros are upper bounds, and the contrast at multiplier 1 (−4.04) is nearly twice the re-clear of the actual shift (−2.39). Do not quote the scenario table as a level.

Deviations from the spec, as run: no same-water iteration of k; hydro placebo only in windows with at least 56 pre-announcement days (six of nine, Δ_H between −0.15 and −1.68); scenario σ draws are independent; the hydro-effect interval is a week-block bootstrap.
