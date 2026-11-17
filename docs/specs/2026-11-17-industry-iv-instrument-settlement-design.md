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

## Pre-run amendments (2026-11-17, written after the script and before any run; made after counting rows and reading data layouts, never after seeing a score)
1. **C1 wind speed** uses the existing national mean of the ten wind sites' 100 m speed (`weather_spain_aggregate.parquet`), not a farm-weighted average; the power-curve transform is min(ws/12, 1)^3 and its square, no solar variant (C1s dropped).
2. **C2 hour weights** are 1 / sd of the instrument by hour of day in 2019 (the bid-curve instruments exist only from 2019), not estimated on 2018. They use the instrument's own variance only.
3. **C3** interacts the C2 instruments with the same-hour offer-curve slope of 7 days earlier (standardised); the slope level is not a control.
4. **Common sample and controls.** Every candidate is scored on the rows of the bid-curve sets for which all candidates exist; predictors for the double ML are the V3 set (no realised wind, so as not to absorb C1). The placebo outcome is residualised once with the same predictors; price and instrument residuals are shared with the main outcome.
5. **S3 (zero-first-stage) in practice.** Spain's national mean wind speed never reaches turbine idle (range 1.4-16 m/s; realised wind averages 1.5 GW even below 3 m/s) and only 41 rows have both weeks below 3 m/s. The test therefore uses rows with national mean speed below 5 m/s in both weeks (1,777 rows), a weak form of the paper's test, and applies to the wind component of each candidate (C0 d wind forecast, C1 d power curve, C2/C3 the wind bid-curve instrument). Pass: permutation p above 0.05 **and** |idle coefficient / full-sample coefficient| at most 0.5. Minimum rows 800. **C4 has no wind component: S3 is not applicable and it is judged on S1 and S2 only.**
6. The outage series is `outputs/tables/outage_event_hours.parquet` (planned and fault MW lost, by hour); 43 of 100 `indisp` months are partial at source, which makes C4 noisier, not biased in a known direction.

## Results (run 2026-11-17, script `industry_iv_instrument_settlement.py`, commits 4fc0f4c, fix of a key typo in the F3 step; scores in `outputs/tables/industry_iv_instrument_settlement*.csv`)
First stage F (full / 2019-21H1 / 2021H2-23): C0 85/68/78, C1 93/71/80, C2 2.3/1.7/2.1, C3 4.9/1.4/5.0, C4 0.5/6.0/0.1. S3 (idle-wind rows, 1,598): C0 fails (ratio 0.66, p 0.004), C1 passes narrowly (ratio 0.47, p 0.092), C2/C3 ratio -0.81. Rule outcome as scored: C1 chosen.

**Flaw found after the run, 2026-11-17 (before any elasticity was computed).** The script put the placebo outcome (d ln load 7 days earlier) among the predictors used to residualise that same outcome, so the placebo residual is close to zero and the S2 placebo test, as run, has almost no power. The earlier pipelines excluded that column. **The S2 results above are therefore invalid and are not relied on.** Effect on decisions: C0 (S3), C2, C3 and C4 (S1) were rejected on other grounds, so only C1's S2 needs re-scoring; that is done in the second settlement (`2026-11-17-industry-iv-bid-instrument-second-settlement-design.md`) with the column excluded. The F1 and F3 scores do not involve the placebo and stand.
