# Industrial spot-price IV: can the noise be cut enough? Step zero with four noise reducers (proposal)

**Status: proposed 2026-11-17, not registered. Binding when the user confirms and this file is committed; the first run follows that commit.** Follows `2026-11-16-industry-spot-iv-noise.md` (first stage F 296, standard error of the elasticity 1.59, detectable 4.46 against a bar of 0.25; stopped).

**In one example.** Industrial load at 3 pm last Tuesday was 4,100 MW; this Tuesday at 3 pm it was 4,320 MW. Most of the 220 MW gap is the plant schedule, the week's orders, the weather, things unrelated to the price. A model of load that knows last week's load, the calendar and the weather leaves a smaller leftover; the leftover is what the price can explain. The smaller the leftover noise relative to what the wind-forecast instrument moves, the smaller the standard error of the elasticity. The question is how much smaller the four reducers below can make it.

## Setting (unchanged from the first step zero)
Non-holiday weekdays 2019-01-01 → 2023-12-31 without the lockdown block (2020-03-01 → 2020-06-30); outcome hourly ln of ESIOS 1204-1207 (E3-E6); endogenous variable the day-ahead price (OMIE, €/MWh); instruments D-1 wind and solar forecasts (ESIOS 1777, 1779) and their squares; mean price €98/MWh to convert the slope into an elasticity. **The elasticity this identifies is a short-run, impact elasticity: the response of hourly industrial load to the price surprise carried by the forecast, not a long-run elasticity.**

## The four variants
- **V0 Baseline.** As before: year-month and hour-by-weekday effects, temperature terms; SE 1.59 (to be reproduced).
- **V1 Week-on-week difference.** Outcome, price and instruments are each differenced against the same hour one week earlier (t − 168 hours); effects: hour and year-month; temperature difference.
- **V2 Double ML with gradient boosting.** Outcome, price and each instrument are residualised on the pre-determined predictors by `HistGradientBoostingRegressor` (`max_iter` 300, `learning_rate` 0.05, `max_leaf_nodes` 31, `min_samples_leaf` 50, `l2_regularization` 1, no early stopping), and 2SLS is run on the residuals. Predictors: hour, weekday, month, day of year, temperature (hour, day mean, minimum, maximum), D-1 demand forecast (ESIOS 1775), the same hour's industrial load and day-ahead price **7, 14 and 28 days earlier** (no shorter lags, so they are not mechanically affected by the current forecast surprise), and the monthly gas price (MIBGAS) if available. Cross-fitting in time: 10 contiguous blocks, each block predicted by a model trained on the others with **14 days removed on either side** of the held-out block.
- **V3 Both.** V1's differenced variables residualised as in V2 (same learner and folds, predictors differenced accordingly).
Standard errors: clustered by date.

## Rules, set before the run (no slope is printed; only first-stage strength, standard error and size)
- **I1 First stage.** The date-clustered first-stage F of the price on the instruments, after the variant's residualisation, is at least 10.
- **I2 Noise.** Detectable elasticity (2.8 × SE of the elasticity at the mean price) is at most **0.25**.
- **I3 Size.** With the instrument permuted across days within each year-month (200 draws), the share of draws with |t| > 2 is at most 10%, so the standard error is not too small. (Only for variants passing I1 and I2.)
- **I4 Decision.** If any variant passes I1-I3, a further spec registers the estimation (rules for sign, placebo, robustness) before any slope is computed; the variant with the smallest SE among those passing is the primary one, chosen now by SE alone. If none passes, the industrial IV is closed and the detectable elasticities of all four variants are recorded.
No other specification is tried after a failure.

## What each outcome means
A variant passes: an impact elasticity of industrial load to the hourly price becomes estimable, to be compared with the household one on the same footing (both short-run), with its own registered estimation spec. None passes: industrial demand elasticity is not identifiable from hourly data with these instruments and learners, and the bound (the smallest detectable elasticity of the best variant) is what we can report.

## Threats
Differencing against last week assumes no break in the weekly pattern across the two weeks (holidays and plant shutdowns near the difference weeks are dropped); gradient boosting cannot extrapolate beyond the price and temperature range seen in training (2022 prices); the exclusion restriction (wind and solar forecasts move industrial load only through price) is plausible but not tested here, and forecasts correlate with weather that affects some plants; weekly lags of load may contain the response to last week's price (hence 7 days or more); time-blocked cross-fitting still shares information through the long-run level.

## Data and code
`data/esios` (1204-1207, 1775, 1777, 1779), OMIE prices, temperature files, MIBGAS (`data/mibgas`). New code: `scripts/analysis/industry_iv_noise_reducers.py`; outputs `outputs/tables/industry_iv_noise_reducers.csv`.
