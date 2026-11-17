# Why do the offer-curve instruments fail the 2019-21H1 placebo? (descriptive diagnostic, pre-registration)

**Status: registered 2026-11-17, before any run. Descriptive only: no elasticity, no new instrument, no pass/fail on an estimate.** Background: B1, B2 and X1 (offer-curve information) fail the placebo (load of the same hour 7 days earlier) in 2019-21H1 with p 0.008, 0.023, 0.015; B0 narrowly (0.073); C1 alone passes (0.12). The question is what drives it, because a driver we can name is a validity problem we could control for in a future, separately registered instrument.

**In one example.** The placebo regresses last week's load on this week's instrument. A clean instrument cannot predict last week's load. If it does in spring 2021, say, that points to something that moves both: a plant outage in that season, or a demand pattern the lagged curve shape reflects.

## What is computed (common sample of the first settlement, residuals in X1's home set: V3 predictors plus the lagged slope level)
For instruments C1 (d_pc), X1 interaction (d_pc x s), B0 (d_dpw, d_dps), B1 (hour-weighted), B2 interactions: residualised instruments and the residualised placebo outcome (without its own lag).
1. **Reduced form on the placebo, by regime and cell.** Slope of the residual placebo outcome on each residual instrument (date-clustered t), by regime (2019-21H1, 2021H2-23), then within 2019-21H1 by year (2019, 2021H1), season (DJF, MAM, JJA, SON), and hour block (night 0-7, day 8-17, evening 18-23).
2. **Correlation of each (raw, week-on-week differenced) instrument with candidate drivers**, by regime: d demand forecast, d temperature, d planned outage MW, d fault outage MW, and the lagged slope s itself. Also the standard deviation of each instrument by regime.
3. **Leave-driver-out:** the same placebo reduced form with the instrument residualised additionally on the one candidate driver most correlated with it in 2019-21H1 (reported next to the unadjusted one).

## Reading rules (set now)
- **A driver is named only if** (i) the placebo reduced form is concentrated: one cell (year, season or hour block) has |t| at least 2.5 and is at least twice the |t| of the others, and (ii) the instrument's correlation with a candidate driver in that regime is at least 0.2 in absolute value, and (iii) residualising on that driver cuts the full-regime placebo |t| by at least half. All three: that driver is reported as the likely validity problem.
- **Otherwise** the report says no single driver was found (the failure is diffuse or reflects regime-specific persistence), and the offer-curve route stays closed with that statement.
- All cells are reported; with about 15 cells, a lone |t| near 2.5 is suggestive only and is labelled so. Nothing here changes the closed status of B0-B2 and X1; using a named driver would need a new registration.

## Data and code
Script `scripts/analysis/industry_iv_placebo_diagnostic.py` (committed before it runs); reuses `industry_iv_instrument_settlement.build_frame` and `industry_iv_second_settlement` helpers. Outputs `outputs/tables/industry_iv_placebo_diagnostic{,_corr}.csv`.
