# Instrument settlement for the industrial impact elasticity (pre-registration)

**Status: registered 2026-11-17, before any run. Nothing below has been estimated.** Purpose: settle which price instrument we use for the industrial impact elasticity (load of voltage bands E3-E6, ESIOS 1204-1207, to the OMIE day-ahead price), once, on grounds that never look at the elasticity, and then stop the instrument discussion.

**In one example.** Suppose an instrument moves the day-ahead price by €10 at 3 pm and has nothing to do with industrial load except through the price. We can check that without ever computing an elasticity: (a) does it move the price strongly (first stage), (b) does it "move" load that cannot respond (load 7 days earlier), (c) does it still move the price in hours when it should not (the zero-first-stage test borrowed from Hirth, Khanna and Ruhnau 2024, Energy Economics 135, 107652, `papers/md/how-aggregate-electricity-demand-responds-to-hourly-wholesale-price-fluctuations.md`). An instrument is chosen on those three things only.

## Why the paper's design works and what we borrow
Their first stage is strong (partial R2 0.46, F 930, 38,448 hours of 2015-19), and they back the exclusion restriction with a zero-first-stage test: in hours when wind speed is too low or too high for turbines to respond, wind output does not move, so the instrument should not move the price and the estimated response must be zero. We have regional hourly wind speed on disk (`data/weather/weather_spain_hourly.parquet` and `raw_*.parquet`: 10 m and 100 m wind speed, UTC hourly), so no download is needed.

## Sample and outcome (unchanged from `2026-11-17-industry-iv-estimation-design.md`)
Non-holiday weekdays, 2019-01-01 to 2023-12-31 (the 2021-23 crisis kept; sub-period 2019-21H1 reported as well), 15-minute periods averaged to the hour, outcome ln(load E3-E6) first-differenced week-on-week as in V3, price at the day-ahead hourly level. Controls and noise reducer: V3 exactly.

## Candidates (all fixed here; no others will be added)
- **C0**: current V3 forecast instruments (D-1 wind and solar forecasts 1777, 1779 and squares). Baseline.
- **C1**: realised capacity-weighted wind speed (100 m) over the located wind farms (location file v3), with a cubic power-curve transform and a squared term; solar radiation as a second instrument only in variant C1s.
- **C2**: bid-curve instrument with hour weights: the existing weight-fixed bid-curve instrument, rescaled by each hour's average price sensitivity of the supply curve, weights estimated on 2018 only.
- **C3**: C2 interacted with the hourly residual-demand slope (price change per GW at the offered curve, lagged one week so that it is predetermined).
- **C4**: planned and unplanned generation outages in the hour (requested by the user on 2026-11-17, who knows earlier outage IVs were run several times and wants one more candidate under the common rules; counted once, not rescued).

## Scores (first stage and placebo only; elasticities are not computed for selection)
For each candidate: **F1** date-clustered first-stage F and partial R2 for the price; **F2** placebo outcome: the same pipeline with ln load of the same hour 7 days earlier as outcome (reduced-form coefficient of the instrument on that outcome, randomization p, 1,000 date permutations, seed 20261117); **F3** zero-first-stage test: hours in which the capacity-weighted wind speed is below 3 m/s or above 22 m/s (turbines idle or shut down), the instrument's first stage on price must be indistinguishable from zero. For C2-C4, where wind is not the driver, F3 is replaced by the same test on hours with extreme low residual demand slope variation (bottom decile of the instrument's own variance), which checks that the instrument has no first stage where it should not move the price. All tests by 2019-21H1 and 2021H2-23 separately.

## Rules (each says what a failure would tell us)
- **S1 Strength.** F1 at least 20 in the full sample and at least 10 in each sub-period. *Failure:* the candidate cannot identify anything in some regime; dropped.
- **S2 Placebo.** F2 randomization p above 0.10 in the full sample and in both sub-periods. *Failure:* the instrument moves load before it can respond; its exclusion restriction fails; dropped.
- **S3 Zero-first-stage.** F3 first-stage coefficient inside the 95% randomization interval around zero, with at least 800 hours in the restricted set. *Failure:* the instrument moves the price where its mechanism says it cannot, so it is picking something else up; dropped. With fewer than 800 hours: not testable, and the candidate is flagged, not passed.
- **S4 Selection.** Among candidates passing S1-S3, choose the one with the largest minimum F1 across the two sub-periods. Ties (within 10%) go to the simpler candidate in the order C1, C0, C2, C3, C4. The chosen instrument is then the only one used for the industrial elasticity.
- **S5 Stop.** If no candidate passes S1-S3, the instrument question is closed with that result: the industrial elasticity is reported as the bound already recorded (-0.03 [-0.055, +0.006], 2019-23 weekdays; `docs/business-demand-evidence.md`), no further candidate is added, and the effort moves to the unit data and to more data. Failed candidates are kept in the record and not rescued.

## After settlement
Only the selected instrument is run through the elasticity estimator (V3 pipeline, randomization inference), under its own rules E1-E5 from the existing spec. That run needs a separate go-ahead.

## Data and code
Weather: `data/weather/weather_spain_hourly.parquet` (verify the timestamp is UTC and the coverage 2019-2023 in the script's first lines; if coverage fails, C1 is reported "not testable", not substituted). Located wind farms: `lib` location v3. Script: `scripts/analysis/industry_iv_instrument_settlement.py` (to be written and committed before it is run). Output: `outputs/tables/industry_iv_instrument_settlement.csv`.
