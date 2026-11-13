# Fuel switching between coal and gas in Iberian generation (pre-registration)

**Status: pre-registered 2026-11-13 (rules F1-F6 confirmed by the user the same day; before the registration F3's permutation, the treatment of zero-coal days and F4's VES slope were amended, see below), before any dispatch outcome was computed.** The feasibility numbers below (fleet size, capacity, cost ratio) use no dispatch outcome. The rules are binding once this file is committed; the first run happens after that commit.

**In one example.** In January 2019 a gas combined cycle cost about €49/MWh to run and a coal unit about €51: nearly equal, and coal supplied 2.8 GW on average. By April 2020 gas had fallen to €20 and coal to €37: gas was cheaper by €17, and coal supplied 13 MW. The fuel mix moved because the *relative* cost moved, with total thermal output set by demand. How much the coal share moves per percent of relative cost is the elasticity of substitution between the two fuels as inputs to generation.

## Question
How strongly do Iberian coal and gas combined-cycle units substitute for each other in dispatch when their relative marginal cost changes, holding the thermal output the system needs fixed? Secondary (feasibility says it is out of reach, see below): did the 2022 gas cap change the switching.

## Theory (what the elasticity is, and why it will not be constant)
- **Unit level.** Offers are cost-based with a markup: unit `i` of fuel `f` is dispatched in hour `h` iff `c_i + m_i ≤ p*_h`, `c_i = w_f / η_i` (fuel and carbon cost `w_f`, thermal efficiency `η_i`). Dispatch is discrete.
- **Fleet level.** With a spread of efficiencies in a fleet, the share of capacity dispatched is smooth: `u_f = 1 − G_f(ln w_f − ln p*)`, `G_f` the distribution of `ln η_i` in the fleet and `u_f` the utilisation (output over available capacity). Both fleets respond to their own cost relative to the *same* price `p*`, and `p*` itself is set by residual demand `R_h` (load net of wind, solar, hydro, nuclear, must-run): `R_h = Σ_f K_f u_f`.
- **Substitution.** For fixed `R`, a rise in coal's cost lowers `u_c` and raises `p*`, which raises `u_g`. The input elasticity of substitution between the fuels is `σ_fuel = −d ln(u_c/u_g) / d ln(c̄_c/c̄_g)` at fixed `R`. **It is a function of the cost ratio and of `R`, not a constant**: huge when the two fleets sit at the margin together, near zero when one is far below. A constant-σ CES is therefore a restriction to be tested, as the single σ was for households; the default estimand is a flexible curve and its local elasticity.
- **Unit-level validation.** If the cost-ranking theory holds, the probability that a unit is dispatched depends on `ln p*_h − ln c_ih` with the same slope for both fuels. A different slope for coal means constraints (operating-hour limits, ramping, must-run), which the fleet estimate must then allow for.

## Data on disk
Hourly unit-level offers, clearing and bid-time cost: `outputs/cache/step/units_YYYYMM` (plant-specific-efficiency gas and coal units, 2019-01 → 2025-09, `cost` is the capped bid-time cost, equal to the market one before June 2022) with `hours_YYYYMM` for `p*`; daily costs `implied_marginal_cost_daily` (`_bid`); residual-demand inputs (REE realtime, ESIOS 1777/1779 wind and solar forecasts, hydro); capacity from `cab`.

## Feasibility (no dispatch outcome; `outputs/cache/step`, plant-specific units only)
| Quarter | Coal units | Coal capacity (MW) | Gas units | Gas capacity (MW) | Cost coal / gas (€/MWh) |
|---|---|---|---|---|---|
| 2019Q1 | 25 | 8,854 | 55 | 25,822 | 51 / 49 |
| 2019Q3 | 25 | 8,854 | 54 | 25,173 | 49 / 34 |
| 2020Q1 | 24 | 8,530 | 54 | 24,445 | 41 / 28 |
| 2020Q3 | 13 | 4,625 | 52 | 24,515 | 43 / 27 |
| 2021Q3 | 7 | 1,530 | 52 | 24,968 | 98 / 110 |
| 2021Q4 | 4 | 1,344 | 53 | 24,980 | 120 / 203 |
| 2022Q3 | 1 | 346 | 52 | 24,562 | 213 / 105 |
| 2023Q1 | 2 | 697 | 52 | 24,866 | 142 / 119 |
| 2024Q1 | 1 | 346 | 52 | 23,767 | 94 / 74 |
**The coal fleet collapses just as the gas shock arrives.** Window A (**2019-01-01 → 2020-02-29**, before the lockdown): 24-25 coal units, 8.3-8.9 GW, 425 days, daily `ln(coal/gas)` cost ratio mean 0.27, sd 0.15, range −0.10 to 0.66: a large coal fleet with real variation in the ratio. Window B (2021-06 → 2022-12): 1-7 coal units, at most 1.5 GW, a ratio with sd 0.26-0.29 and a range of −0.98 to 0.91: strong variation but a fleet too thin to estimate a fleet response (and the gas cap's effect on switching, which needs this window, cannot be read from one to three units). 2020-07 → 2020-12: 13 units, 4.6 GW, ratio sd 0.20: a second, smaller window.
Window A's weakness: it is the pre-crisis regime, with coal's operating-hour limits (environmental derogations) and a COVID-free but eventful 2019 (a CO2 price rise); and its identification is the common fall of the gas price, so the ratio moves with the gas market, not independently.

## Estimation (proposed)
1. **Fleet:** daily capacity-adjusted utilisations `u_c, u_g` (cleared MWh over available MW-hours, excluding units out of service); `ln(u_c/u_g) = f(ln(c̄_c/c̄_g)) + γ R_d/K + month effects + wind, solar, hydro availability`, `f` a spline; HAC by week.
2. **Unit-hour:** logit of `cleared > 0` on `ln p*_h − ln c_ih`, by fuel, with unit effects and residual demand; the equality of the slopes across fuels.
3. **CES restriction:** `f` linear in the log ratio against the spline (F-test).

## Rules, set before the run (confirmed 2026-11-13)
- **F1 Feasibility.** Window A has at least 15 coal units, 5 GW of coal capacity and a daily ln cost-ratio sd of at least 0.10 (met: 24-25 units, 8.3-8.9 GW, 0.15).
- **F2 Sign and size.** The coefficient of `ln(u_c/u_g)` on `ln(c̄_c/c̄_g)` at the sample median is negative with t ≤ −2 (weekly clusters) and has a magnitude between 0.2 and 10.
- **F3 Placebo.** The cost ratio of the *following* 30 days (not known to the unit) has a coefficient with |t| < 2 once today's ratio is in; and the real ratio's |t| ranks in the top 5% (rank at most 10 of 200) among 200 circular shifts of the cost-ratio series by random offsets of at least 30 days. *(Amended before registration: the draft permuted the ratio across years within calendar month, which cannot be done in a window that holds one full year and two months of another.)*
- **F4 Restriction.** Constant σ (CES) against variable σ (VES). Two tests on the same curve: (i) the spline against the linear `f` (Wald, 4 restrictions); (ii) the **VES slope**: `σ(r) = σ0 + σ1 r` in the log cost ratio `r`, i.e. `f(r) = a − σ0 r − σ1 r²/2`, `H0: σ1 = 0`. **The constant-σ restriction is rejected if either test rejects at 5%**; the flexible curve is then the result, with the local elasticity at parity (`r = 0`) and at the median reported, and `σ1` as its parametric summary.
- **F5 Robustness.** F2's sign holds with MW instead of utilisation, without the residual-demand control, excluding the 10% of days with the lowest offered capacity, on the days with positive coal output only (log-linear OLS), and in the 2020-07 → 2020-12 window.
- **F6 Merit-order consistency.** At least 90% of unit-hours with `c_ih + 5 < p*_h` and the unit available are dispatched, for each fuel, and the logit slopes of the two fuels are equal at 5%; if not, constraints bind and the fleet estimate is read as an effective, constrained elasticity.

## What each outcome means
F1-F5 pass: a measured fuel-switching elasticity of the Iberian thermal fleet before the crisis, with its dependence on the cost gap; it feeds the supply-slope used in the price-effect extension (`ψ`) and is transferable to other systems with a coal fleet. F4 rejected: the elasticity is a curve, which is the expected result. F6 fails for coal: constraints, not costs, govern coal dispatch; the elasticity is reported as an effective one and says nothing about cost-driven switching. F2 fails: the cost ratio does not move dispatch at this resolution; reported with its bound.

## Threats
Residual demand and the clearing price are jointly determined with dispatch (control and instrument with REE's day-ahead wind, solar and demand forecasts, available as ESIOS 1775-1779); fuel costs are exogenous at the system level. Coal units had limited annual operating hours under the environmental regime (derogation), which breaks the cost ranking late in a year; cogeneration and must-run output are not in the plant-specific fleet (residual demand must be net of them); the cost is a bound, not a measurement (CLAUDE.md); markups in offers move dispatch independently of cost; 22 matched coal units may omit plants whose efficiency JRC does not give plant-specifically. The 2022 gas-cap switching question and Portugal's 2021 coal closures cannot be read from one to three units.

## Fixed details for the run
- **Window A** (the main): 2019-01-01 → 2020-02-29, all days, valid hours (`valid` true in `hours_YYYYMM`) only; window 2020-07-01 → 2020-12-31 for F5. Lockdown months out.
- **Fleets:** the plant-specific gas and coal units of the step cache (`units_YYYYMM`, `fuel` gas / coal); a unit is *available* in an hour if it has an offered step that hour and its `cap_mw` is known.
- **Utilisation** `u_{f,d}`: over the day, the sum of `cleared_mw` of the fleet's available units over the sum of their `cap_mw`, both over unit-hours in which the unit is available. **Cost** `c̄_{f,d}`: capacity-weighted mean of the bid-time `cost` over the fleet's available units that day. Ratio `ln(c̄_c/c̄_g)`.
- **Residual demand** `R_d`: the daily mean of `F_demand − F_wind − F_solar` from the step cache (REE's D-1 forecasts), over total offered thermal capacity; entered as a control, no instrument (it is predetermined). Month effects.
- **Estimating equation (fleet):** `ln(u_c/u_g) = f(ln(c̄_c/c̄_g)) + γ R_d + month effects + u`, `f` a B-spline with 4 degrees of freedom on the ratio (knots at the terciles), against the linear `f` (F-test, week-clustered covariance, **F4**); standard errors clustered by week. **F2** reads `−f'` at the median ratio of the window.
- **F6 sample:** unit-hours with `|ln p*_h − ln c_ih| ≤ 0.5`, `p* > 0`, available and not `withdrawn` that day; logit of `cleared > 0` on `ln p* − ln c`, by fuel, equality of the two slopes by Wald (unit-clustered).
- **F2 magnitude** is on `σ̂ = −f'(median)`: between 0.2 and 10. **F5** variants as listed; each must keep the sign and |t| ≥ 2 except the 2020-H2 window, which must keep the sign only.
- Code: `scripts/analysis/fuel_switching.py`, outputs `outputs/tables/fuel_switching_*.csv`.

## Amendments before the registration (2026-11-13)
- **Zero-coal days.** Counting days (no relationship looked at): coal supplies nothing on **79 of 423 days (18.7%)** of window A, gas on none. `ln(u_c/u_g)` is undefined on those days, and dropping them would select on the outcome (it removes exactly the days with the least coal, biasing the response toward zero). **The main estimator is Poisson pseudo-maximum likelihood (PPML) of the coal utilisation `u_c` (zeros kept) with offset `ln u_g`: `E[u_c | ·] = u_g · exp(f(r) + γ R + months)`**, the same ratio equation `ln(u_c/u_g) = f(r) + …` without taking the log of zero; standard errors clustered by week. The log-linear OLS on positive-coal days is the F5 variant that shows the truncation.
- **Spline.** Cubic spline with interior knots at the terciles of `r`, in the truncated-power form `[z, z², z³, (z − k1)³₊, (z − k2)³₊]`, `z` the standardised ratio (5 degrees of freedom; the draft said 4, the knots at the terciles fix it at 5). The linear restriction is the four non-linear coefficients equal to zero.
- **F5's "lowest availability"** is implemented as the 10% of days with the lowest total offered thermal capacity (unit-hours have no availability measure beyond being offered).
- **F3b's statistic** is |t| of `σ̂ = −f'(median)` from the spline model.
