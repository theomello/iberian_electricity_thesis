# Clean-dirty nested CES in Iberian generation (proposal)

**Status: proposed 2026-11-16, not yet registered. The rules below become binding when the user confirms and this file is committed; step zero (the noise check) is the first and only run before that.**

**In one example.** On a rainy March day a reservoir plant can sell water at its stored-water value (say €40/MWh) or leave it for later, while a gas plant costs €90/MWh to run. The system needs 20 GW from the two. When gas gets dearer relative to water, more of the 20 GW should come from hydro. How much the hydro/thermal split moves per percent of relative cost is the substitution elasticity between a clean and a dirty input to generation. Wind and solar are not on this margin: they are zero-cost and supply whatever the weather gives, so they change the 20 GW that remains, not the split.

## Question
How strongly does the Iberian system substitute between clean and dirty sources in dispatch when their relative marginal cost changes, holding the output to be served fixed? This is the generation-side (system-wide) analogue of the nested CES of Papageorgiou-Saam-Schulte (2017), with two differences the user asked for: it need not rely on quantities alone, and it is a short-run, operational elasticity, not their long-run technology one (which needs capacity and R&D data this repo does not have).

## Structure
Output to be served on the dispatchable margin, `R_d = demand − wind − solar (PV and thermal) − nuclear − cogeneration − net imports`, is produced by a CES bundle of a **clean input** `C` (reservoir and pumped hydro, run-of-river kept as a control) and a **dirty input** `D` (combined-cycle gas and coal). Inner nest for `D`: coal against gas, which is the fuel-switching design (`2026-11-13-fuel-switching-scope.md`). Wind and solar enter as weather-driven availability that sets `R_d`; nuclear and cogeneration are must-run controls. Net imports are treated as exogenous in the main run and as a third input in a sensitivity.

Prices: `P_D,d` = capacity-weighted bid-time marginal cost of the thermal fleet (step cache `cost`); `P_C,d` = the 30-day water value of the hydro fleet (`hydro_cost_daily`), the opportunity cost at which hydro offers. Both are costs, not market prices, so the clearing price (which both fleets face) does not enter the ratio.

## Estimands (quantities and prices)
- **A, relative demand:** `ln(Q_C/Q_D)_d = a − σ ln(P_C/P_D)_d + γ R_d/K + month effects + u`, with `Q` daily energy and `K` available capacity.
- **B, cost shares (prices and quantities):** `s_C,d = P_C Q_C / (P_C Q_C + P_D Q_D)` on `ln(P_C/P_D)`, slope `1 − σ` (the nested-CES share equation). Estimated jointly with A by seemingly unrelated regressions; the equality of the two σ is the CES restriction.
- **Instruments:** `P_C` is endogenous (the water value is set from expected prices, which depend on gas). Instruments: reservoir level lagged 30 days and rainfall/inflow (MITECO, JRC hydro), as in the hydro cost builder. `P_D` is exogenous at the system level (TTF/MIBGAS gas, EUA, API2 coal). Weather availability enters `R_d` as the D-1 wind and solar forecasts (ESIOS 1777, 1779), which bidders knew.
- **Flexibility:** a spline in `ln(P_C/P_D)` against the linear form (F test); σ is a curve if the linear form is rejected, as in the fuel-switching design.

## Step zero: noise and feasibility check (before anything is estimated)
Pre-outcome numbers only, from costs, availability and instruments:
- **C1 Variation.** The daily `ln(P_C/P_D)` has a standard deviation of at least 0.15 within each window, after month effects.
- **C2 Margin exists.** Hydro and thermal each supply at least 5% of `R_d` on at least 70% of days in the window.
- **C3 Instruments.** The first-stage F of `ln P_C` on the weather and lagged-storage instruments is at least 10 (week-clustered).
- **C4 Detectable σ.** Using the standard deviation of the placebo-window residual of `ln(Q_C/Q_D)` (leave-year-out LASSO as in the ToU work), the detectable σ (2.8 × sd / sd of the ratio) is at most 1.5.
Windows: pre-cap 2019-01-01 → 2022-06-14 excluding 2020-03-01 → 2020-06-30 (lockdown); post-cap 2022-06-15 → 2023-12-31 reported separately because the cap changes `P_D` (use the subsidised cost). If C1-C4 fail in a window, that window is dropped, and if they fail in all of them, stop and report the bound.

## Rules, set before the run
- **S1 Sign and size.** σ from A, IV, is positive (hydro rises when relative cost of thermal rises) with t ≥ 2 (week clusters) and lies in [0.1, 10].
- **S2 Placebo.** The following 30 days' ratio is insignificant (|t| < 2) with today's in; and the real ratio's |t| ranks in the top 5% among 200 circular shifts of at least 30 days.
- **S3 Consistency of A and B.** The σ from B is within the 95% interval of A's σ.
- **S4 Restriction.** Constant σ is rejected if the spline test or a quadratic term rejects at 5%; then the curve, its local value at the median and at parity, are the result.
- **S5 Robustness.** Sign and |t| ≥ 2 hold with: net imports as a third input; run-of-river included in `C`; without `R_d`; OLS instead of IV (sign only); each year dropped in turn (sign only).
- **S6 Instrument check.** Weather instruments excluded from the equation in a reduced form of `ln(Q_C/Q_D)` on the instruments given `P_D`: the reduced form has the sign implied by σ.
No other specification is tried after a failure.

## What each outcome means
All pass: a measured operational clean-dirty elasticity, with its dependence on the cost gap, usable as the supply-side input in the unified model and comparable with the ToU demand elasticities. S1 fails: relative cost does not drive the hydro/thermal split at daily resolution (water is allocated by storage and inflow, not by this cost), reported with its bound. S3 fails: prices and quantities disagree, so the CES shape itself is wrong. Not a technology elasticity: a high σ here says dispatch re-ranks quickly, not that the investment mix would.

## Threats
Hydro dispatch also responds to storage limits, environmental flows and irrigation (the water value is a model, `λ*`, matched to EDP's but not observed for the other firms); net imports and pumped storage move with prices; the thermal cost is a bound (CLAUDE.md); markups move dispatch independently of cost; in 2021-22 hydro offered above its water value (hydro departure results), so the cost ranking may not hold at the margin and the windows are reported separately; Q_C and Q_D are jointly determined with R_d (R_d uses forecasts, not realised VRE).

## Data (on disk)
`outputs/cache/step` (units, hours), `outputs/tables/hydro_cost_daily.parquet`, `implied_mc` series, `data/ree/ree_realtime_5min.parquet` (generation by technology), ESIOS 1775/1777/1779, MITECO reservoirs, JRC hydro, MIBGAS, EUA, coal (investing). New code: `scripts/analysis/clean_dirty_noise.py` (step zero), then `clean_dirty_ces.py` only after step zero is recorded.

## Step zero result (run 2026-11-16, `scripts/analysis/clean_dirty_noise.py`, `outputs/tables/clean_dirty_noise.csv`)
No slope was printed. The rule was: a window that fails C1-C4 is dropped; if all fail, stop.

| Window | Days | C1 sd ln(P_C/P_D) ≥ 0.15 | C2 both ≥ 5% of R on ≥ 70% of days | C3 first-stage F ≥ 10 | C4 detectable σ ≤ 1.5 |
|---|---|---|---|---|---|
| pre-cap 2019-01-01 → 2022-06-14 (lockdown out) | 1,070 | 0.116 **fail** | 99.4% pass | 7.1 **fail** | 6.7 **fail** |
| post-cap 2022-06-15 → 2023-12-31 | 542 | 0.145 **fail** (by 0.005) | 96.7% pass | 138.6 pass | 0.98 pass |

**Outcome: STOP under the registered rule; the clean-dirty CES is not estimated.** The pre-cap window has too little variation in the relative cost, a weak first stage (rainfall and lagged storage do not move the water value enough) and a detectable σ of 6.7. The post-cap window is a near miss on C1 only (0.145 against 0.15), with a strong first stage and a detectable σ of 0.98; it is not rescued by lowering the threshold. Because the cap subsidises the gas cost in that window, `P_D` there is the bid-time cost, which already includes the subsidy, so the variation in the ratio is partly the cap itself.
Deviations as run: C4 uses the equation's own controls (month effects, spline in ln R) and 2.8 times the week-clustered IV standard error instead of a LASSO residual window sd. `R` excludes exports, so after 2022 hydro plus thermal exceeds `R` (thermal share 1.03); exports belong in the controls of any later run.
