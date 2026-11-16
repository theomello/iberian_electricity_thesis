# Heterogeneity by conditions with a generalized random forest (proposal)

**Status: proposed 2026-11-17, not registered. Binding when the user confirms and this file is committed; the first run follows that commit. Replaces the stopped area-heterogeneity design (`2026-11-17-dose-and-area-design.md`, Part B).** Uses R's `grf` (Athey, Tibshirani and Wager's generalized random forest; version recorded in the run), already installed.

**In one example.** On a mild May day a household turns off nothing when the evening price rises; on a 38 °C August afternoon the air-conditioner is the load that can move, and on a weekend the evening peak is different again. The question is whether the response per unit of price change differs across such conditions, and which conditions matter, without choosing the cells in advance. A forest splits the data on the conditions it finds informative and reports, for each hour, an estimated response with a confidence interval.

## Why this and not areas
The area dimension has five units with placebo noise of 4-5 points each (B0 failed). Conditions vary hour by hour and day by day, so there are thousands of observations, and the tariff dose itself differs by hour and day type, which gives within-day variation to learn from.

## Design
- **Unit of observation.** Household series E0, one row per date and hour; **outcome** `y` = (Spain LASSO error − Portuguese regulated-unit error) at that hour, cross-fitted by year (leave-2018/2019/2020-out) for the pre-period days and the real-window errors for 2021 window days, as in the randomization-inference run; **treatment** `w` = the Equation 4 dose of the paper's convention (E = window mean price, w = 0.69) on window days, 0 elsewhere.
- **Level drift removed.** `y` and `w` are demeaned within each day (across the 24 hours) before the forest, so a year-specific level shift of the Spain-minus-Portugal difference cannot load on the treatment; the forest learns from the within-day contrast of response and dose. The average effect is then the within-day analogue of the contrast results; it is compared with the Equation 4 elasticity (F0), not equated to it.
- **Sample.** Season-matched: days 1 June → 31 October of 2018, 2019, 2020 (COVID block removed) plus the real window 2021-06-01 → 2021-09-15 (about 12,000 rows). Clusters: the ISO week; honest forest, 4,000 trees, tuned (`tune.parameters = "all"`), fixed seed recorded.
- **Covariates (X), fixed now.** Hour; weekend or holiday; month and day of year; day-mean, minimum and maximum temperature, the hour's temperature, heating and cooling degree-hours, the 3-day mean temperature, a heat-wave indicator (3 days with a maximum above 35 °C); the day-ahead price of the hour and the previous day's mean price; D-1 wind, solar and demand forecasts (ESIOS 1777, 1779, 1775); the hour's dose and tariff period (peak, mid, off); the day's position in the window (days since 1 June, set to 0 outside it, to allow learning or fatigue); bridge-day indicator. The price covariates are in because regulated customers see the hourly price; a second run without them is a robustness check.
- **Quantities.** Average treatment effect (`average_treatment_effect`, clustered), the omnibus `test_calibration`, out-of-bag conditional effects `τ(X)`, variable importance (`variable_importance`), partial dependence by covariate (decile bins), best linear projection on the main covariates (`best_linear_projection`).
- **Null distribution.** The same pipeline (forest settings, covariates, demeaning) on the season-matched placebo windows of the randomization-inference run (the 26 windows starting within ±45 days of 1 June in 2018 and 2019), the dose laid on the placebo window and the real window days excluded; the statistic for heterogeneity is the standard deviation of the out-of-bag `τ(X)` over window days, and the placebo set gives its distribution without a reform. Forests use 1,000 trees for the placebo runs.

## Rules, set before the run
- **F0 Feasible and consistent.** The average effect is negative with a clustered t ≤ −2, and `w` has at least 10% of its within-day variance in the window days. (Positivity.)
- **F1 Calibration.** The `differential.forest.prediction` coefficient of `test_calibration` is positive with p ≤ 0.05 (the forest's heterogeneity carries signal).
- **F2 Beyond noise.** The real sd of the out-of-bag `τ(X)` on window days exceeds the 95th percentile of the placebo distribution (26 windows).
- **F3 Stable.** A second forest with another seed, and again without the price covariates: the rank correlation of the out-of-bag `τ` with the main forest is at least 0.7, and the three most important covariates of the main forest stay among the five most important in both.
- **F4 Reported only if F1-F3 pass.** The partial-dependence curves and the best-linear-projection coefficients are interpreted only then; otherwise the forest finds no heterogeneity beyond noise and the average effect stands alone.
No other specification is tried after a failure.

## What each outcome means
F0-F3 pass: the response per unit dose varies with named conditions (for example temperature or the hour within the evening), a heterogeneity result the paper does not report, with a placebo-calibrated test behind it. F1 or F2 fails: the apparent variation is no larger than what the forest finds where nothing changed; we report the average only. F3 fails: the variation is not stable across seeds or covariate sets, so it is not interpreted.

## Threats
Only one reform and one treated country: the forest learns variation in effects, not in assignment; the dose and the hour are tied (the dose differs by hour), so hour effects mix dose and response, which the dose-scaled treatment mitigates but does not remove; the demeaning removes the day level and leaves the within-day contrast (an elasticity of the shape of the day, not of the daily total); the placebo windows are two summers (overlapping); covariates such as price can respond to load (their role is a robustness run).

## Data and code
`data/cache_tou` errors (cross-tariff and RI caches), the temperature, ESIOS forecast and OMIE price files. New code: `scripts/analysis/tou_forest_prep.py` (builds the samples and writes CSVs under `data/cache_tou/forest/`), `scripts/analysis/tou_forest.R` (the forests), outputs `outputs/tables/tou_forest_*.csv`.
