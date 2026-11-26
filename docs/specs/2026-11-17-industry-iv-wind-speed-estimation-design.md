# Industrial impact elasticity with the wind-speed instrument (pre-registration)

**Status: registered 2026-11-17, before any run. No elasticity on the real outcome has been computed with this instrument.** The instrument was chosen on first stage, placebo and the zero-first-stage test only (`2026-11-17-industry-iv-instrument-settlement-design.md`, `...-bid-instrument-second-settlement-design.md`): C1, realised national mean 100 m wind speed through a power-curve transform. Following Hirth, Khanna and Ruhnau (2024, `literature/md/how-aggregate-electricity-demand-responds-to-hourly-wholesale-price-fluctuations.md`), who find about -0.05 for German aggregate demand with a wind instrument.

**In one example.** On a Tuesday the wind is stronger than a week earlier; the price at 3 pm is lower, for that reason only. If industrial load in that hour is also a little higher than a week earlier, after removing what the calendar, the weather and recent weeks predict, the ratio of the load change to the price change is the elasticity (times the mean price, 98.7 EUR/MWh).

## Estimand and data (as the first settlement)
Impact (same-hour) elasticity of industrial load, ESIOS 1204-1207 (voltage bands E3-E6), to the OMIE day-ahead price. Common sample: 19,388 non-holiday weekday hours 2019-2023 (COVID months excluded), week-on-week differences, double ML with 10 time blocks and 14 days purged, predictors **without** realised wind (C1's home set in `industry_iv_second_settlement.py`). Instruments d_pc and d_pc^2, d_pc = week-on-week change of min(ws/12, 1)^3. Elasticity = slope x mean price of the sample. Inference: randomization (1,000 permutations of the residualised instruments across days within year-month, hour matched, seed 20261117): p from the rank of |t|, interval = slopes not rejected by the permutation Anderson-Rubin statistic (as `industry_iv_estimation.py`). Normal and chi-square sets alongside.

## Variants and subsets
- **Primary:** double-ML week-on-week differences (as above).
- **V1 agreement variant:** week-on-week differences with year-month and hour effects and a temperature quadratic, no machine learning.
- **Subsets (primary):** instrument d_pc alone; years 2019, 2021, 2022, 2023 separately; hour blocks night 0-7, day 8-17, evening 18-23; 2019-21H1 and 2021H2-23.
- **Placebo outcome:** d ln load 7 days earlier, residualised without its own lag.

## Rules, set before the run (each says what a failure would tell us)
- **E1 Sign and plausibility.** Elasticity negative and at most 1 in absolute value. *Fails:* the instrument identifies something other than price response (a positive value would be load rising with prices).
- **E2 Detected.** Randomization p of the primary at most 0.05 **and** the randomization interval excludes zero. *Fails (with E1 passing):* an elasticity too small to separate from zero at our precision; reported as a bound, not as a point.
- **E3 Placebo outcome.** The same pipeline on the placebo outcome gives p above 0.05 and |elasticity| below 0.01. *Fails:* the instrument moves load before it can respond (exclusion restriction).
- **E4 Overidentification.** Hansen J (date-clustered) p above 0.05 for {d_pc, d_pc^2}, and the single-instrument d_pc slope lies inside the primary's randomization interval. *Fails:* the nonlinearity of the power curve is carrying the estimate.
- **E5 Stability.** The four single-year elasticities share a sign and an equality test of the slopes has p above 0.05. *Fails:* the estimate is a mix of regimes; the sub-period figures are reported instead.
- **E6 Hour blocks (exploratory, no pass/fail).** Elasticities by hour block with randomization intervals.
- **E7 Variant agreement.** V1's elasticity lies inside the primary's randomization interval. *Fails:* the answer depends on the noise reducer.
- **E8 Calibration of the permutation test (diagnostic).** Share of leave-one-out permutation draws with p below 0.05 between 0.02 and 0.10; also the share of permutation |t| above 1.96, reported.
- **E9 Context, no pass/fail.** The result is printed next to the earlier industry estimates (forecast instruments +0.005, bid-curve -0.036 [-0.080, +0.010], weekday bound -0.03 [-0.055, +0.006]) and to Hirth et al. (about -0.05 aggregate, -0.2 to -0.5 for the exposed share).

## What each outcome means
E1-E5 and E7 pass: an industrial impact elasticity identified from wind-driven price variation, detected, to be reported with the household one (short-run, same-hour). E2 fails with a tight interval: a bounded null, reported as the bound with its detectable size. E3 or E5 fail: the instrument does not give a clean estimate either; the instrument question is then closed with "no valid instrument found" and the business side rests on the stated-curve and bound results.

## Threats
Wind speed correlates with temperature and cloud, which affect load directly (controlled through temperature terms but only on one national series); wind output and prices share seasonal and diurnal patterns (absorbed by month/hour/weekday predictors); the national mean of ten sites is a coarse proxy for generation; load response may be to the day-ahead price signal only through exposed consumers, so the figure is an aggregate over E3-E6, not a firm elasticity.

## Data and code
Script `scripts/analysis/industry_iv_wind_speed_estimation.py` (to be written and committed before it is run); reuses `industry_iv_instrument_settlement.build_frame`, `industry_iv_second_settlement.residualise` and `industry_iv_estimation.run_sub`. Outputs `outputs/tables/industry_iv_wind_speed{,_checks}.csv`. Running it needs a go-ahead.

## Results (run 2026-11-17, script `industry_iv_wind_speed_estimation.py`, committed before the run; outputs `outputs/tables/industry_iv_wind_speed{,_checks}.csv`)
Mean price of the sample used to scale the slope is **92.41 EUR/MWh** (the common 19,388 rows), not the 98.7 named above (that was the earlier, larger sample's mean). Elasticity of industrial load to the day-ahead price, randomization intervals:

| Estimate | Elasticity | 95% randomization interval | p (t-rank) |
|---|---|---|---|
| **Primary, full (F 93)** | **+0.0001** | **[-0.021, +0.028]** | 0.99 |
| d_pc only (F 182) | -0.0002 | [-0.012, +0.024] | 0.98 |
| V1 FE, no ML | -0.0000 | [-0.022, +0.029] | 1.00 |
| 2019-21H1 | +0.038 | [-0.013, +0.107] | 0.011 (AR 0.23) |
| 2021H2-23 | -0.014 | [-0.029, +0.009] | 0.12 |
| 2019 / 2021 / 2022 / 2023 | +0.033 / +0.019 / **-0.037** / -0.007 | 2022: [-0.079, -0.005] | 2022: 0.002 (AR 0.024) |
| night / day / evening | +0.000 / -0.001 / +0.001 | each about [-0.02, +0.04] | 0.95-0.97 |
| Placebo outcome | -0.008 | [-0.052, +0.021] | 0.38 |

**Rules.** E1 fails (the point estimate is +0.0001, a precise zero, not negative). E2 fails (p 0.99; the interval contains zero). E3 passes (placebo p 0.38). E4 passes (Hansen J p 0.83; single instrument inside the interval). E5 fails (signs differ across years; equality p 0.10). E6 exploratory, above. E7 passes. E8 passes (0.049; share |t|>1.96 0.032).

**Reading, per the pre-registered rule for E2 failing with a tight interval: a bounded null.** The data rule out industrial impact elasticities more negative than about **-0.021** (and above +0.028) at the 95% level, which excludes Hirth et al.'s aggregate -0.05 for this load. The year pattern is unstable (2019-21H1 positive, 2022 negative); the 2022 interval excluding zero is one of four year cuts, flagged as exploratory, not a finding, and not rescued. The result does not say individual firms are inelastic: it says aggregate same-hour response of E3-E6 load to the day-ahead price is small, consistent with exposed share being small and with the 91% offset between procurement channels.
