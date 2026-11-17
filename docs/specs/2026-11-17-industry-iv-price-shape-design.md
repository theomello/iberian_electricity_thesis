# Price shape: does industrial load move between periods of the day when the price ratio moves? (pre-registration)

**Status: registered 2026-11-17, before any run and before the script exists. Nothing below has been estimated.** Follows the day-level and metered spec (`2026-11-17-industry-iv-day-level-and-metered-design.md`: the whole-day margin matches the same-hour zero and adds no power). This spec moves to the margin the literature says carries the response: **substitution between periods of the day**. Boisvert, Cappers, Neenan and Scott (2004) find about 75% of the response is shifting, with substitution elasticities 0.10-0.18 (0.20-0.27 for customers with more short-term exposure); Patrick and Wolak (2001) find larger own-price responses in the shoulders than at the peak and strong cross-period effects; Niagara Mohawk industrial customers 0.11. Their elasticity is the CES quantity: **σ = -∂ ln(q_k/q_j) / ∂ ln(p_k/p_j)**, as defined in `2026-11-13-ces-substitution-design.md`. A wind-driven fall in the *level* of the price tells us nothing about σ; a move in the *ratio* does.

**In one example.** On a sunny Tuesday in May the midday price falls to EUR 20 while the evening price stays at EUR 90 (a week earlier: 50 and 90). The log of the evening-to-midday price ratio rises from 0.59 to 1.50, a change of 0.91. If a plant shifts load into midday so that the evening-to-midday load ratio falls by 4.5 log points, σ = 0.045 / 0.91 = 0.05. We estimate that number, using the part of the ratio's movement that weather explains and the plant cannot influence.

## Estimand and data
- **Periods** (local Madrid time): evening **E** = hours 19-22, midday **M** = hours 11-15, night **V** = hours 1-5. Block prices and loads are simple means of the block's hourly values; days with any missing hour of the day are dropped (as the day-level frame).
- **Outcome** y = week-on-week (same weekday) change in **ln(L_E / L_M)**, L = industrial load, ESIOS 1204-1207 (E3-E6). **Endogenous** x = week-on-week change in **ln(p_E / p_M)**, day-ahead price (OMIE). σ = -slope of y on x. One row per day, non-holiday weekdays, COVID months 2020-03 → 2020-06 excluded, partner day (d-7) not a holiday.
- **Primary sample** 2019-02 → 2023-12 (same period as the other designs), **log-ratio form**. **Extension E1** 2024-01 → 2025-09-30 (before the day-ahead market's move to 15-minute periods on 2025-10-01), where midday prices are often near zero or negative and the log ratio is undefined; there the **spread form** is used: y on x_s = week-on-week change in (p_E - p_M) / pbar, pbar the sample's mean price; the coefficient is a **shape semi-elasticity** of the load ratio to the scaled spread, reported as such, **not as σ**. Extending the frame to 2025-09 uses `industry_iv_noise_reducers.build(end=...)`; load (to 2026-04), prices and weather cover it.
- **Pass-through.** Only customers whose price moves with the wholesale hourly price see x: about 32% of industrial energy is on hourly variable prices and about another 17% (half of the 35% mixed) is indexed (CNMC, December 2023). Customers on fixed-by-period tariffs see a constant ratio. The aggregate σ is therefore about the exposed share (0.32-0.50) times the exposed customers' σ, if only they respond; this translation is reported, not estimated.

## Instruments (closed list; the point is a ratio instrument, not a level instrument)
- **W1 wind shape:** week-on-week change in pc_E - pc_M, pc = min(ws/12, 1)^3 (national mean 100 m wind speed, as C1) averaged over each block. Wind moves the evening and the midday price differently when the wind rises or falls during the day.
- **S1 solar:** week-on-week change in the mean solar radiation (`radiation_solar_sites`) over the midday block. Sunshine lowers midday prices (and, through storage and ramping, the evening-to-midday ratio).
- **W1+S1** jointly (two instruments, overidentified).
- Not included: forecast instruments (failed the placebo earlier), the outage instrument, the bid-curve and slope instruments. The bid-curve route is reopened **only** if both W1 and S1 fail Q0 below, with its two earlier failed checks (idle-wind zero first stage; the 2019-21H1 placebo) as hurdles that must be passed first.

**Threats, stated before the run.** (1) **S1 exclusion:** sunshine reduces metered load at midday directly, through behind-the-meter solar self-supply of industrial sites and through cooling load; the predictors include block mean temperatures to absorb cooling but nothing absorbs self-supply. This is why W1 is the primary instrument and S1 is only a candidate. (2) Wind shape correlates with weather fronts that change temperature and cloud; temperatures are controlled. (3) Fixed shift schedules: a plant cannot move load that its schedule fixes; σ is the average over movable load. (4) Weekday-only, one national wind series.

## Residualisation and inference (as the day-level design)
Double ML with time-blocked cross-fitting (10 blocks, 14 days purged), predictors: weekday, month, day of year, week-on-week changes of E and M block temperature and of the demand forecast, the outcome's own lags at 7/14/28 days, the price ratio's lags, the monthly gas price; **without** realised wind and solar when the instrument is built from them (the C1 home-set convention). Inference: 1,000 permutations of the residualised instruments across days within year-month, seed 20261117; p from the rank of |t|, intervals from the permutation Anderson-Rubin set (`industry_iv_estimation.run_sub`, day as the unit). Clustering by date.

## Steps and rules (each says what a failure would tell us)
**Step 0 (no real-outcome slope printed or stored)**
- **Q0 First stage.** W1: first-stage F (clustered by date) at least 10 for x on the primary sample. If W1 fails and S1 passes, S1 is carried with its exposure threat flagged; if both fail: **stop**: "no shape instrument found among the closed list". *Fails:* the ratio cannot be moved by weather in a way we can use; the design is closed, the substitution question rests on the stated-curve and household evidence.
- **Q1 Idle test for S1** (zero-first-stage, after Hirth, Khanna and Ruhnau 2024): the first stage of S1 on ln(p_E / p_V) (two zero-sun blocks) has F below 10. *Fails:* S1 moves prices through channels other than midday supply (storage, ramping); S1 is dropped.
- **Q2 Planted gate.** Plant σ0 in the outcome, y* = y - σ0 x (residual refitted, the planted-effect construction), σ0 = 0.05, 0.10, 0.15, 0.30. Gate: **σ0 = 0.15 detected (p at most 0.05, interval excludes zero) and recovered (interval contains it, point within max(0.02, 30%))**. 0.15 is the household-scale value and the lower end of the Boisvert range. *Fails:* the design cannot detect a response of the size the literature reports for exposed customers; stop, report the smallest detected σ0 as the design's detectable σ. Half-sample plants (σ0 = 0.30 in 2019-21H1 only, in 2021H2-23 only) report the regime weights, as before.

**Step 1 (only if Q0 and Q2 pass; real outcome)**
- **Q3 Placebo outcome** (7-day-lagged difference, residualised without its own lag): p above 0.05 and |σ| below 0.02. *Fails:* the instrument moves the load ratio before it can respond; the result is not interpreted (as A1).
- **Q4 Sign and plausibility:** σ between 0 and 2. *Fails:* positive σ-hat of the wrong sign (load moves toward the higher-priced period) says the instrument identifies something other than price response.
- **Q5 Detection:** p at most 0.05 and interval excluding zero. *Fails with Q3, Q4 passing:* a bounded null in σ, reported with the detectable σ from Q2.
- **Q6 Overidentification (W1+S1 only):** Hansen J p above 0.05 and each single-instrument σ inside the other's interval. *Fails:* the two instruments identify different things; report each separately.
- **Q7 Regimes (mandatory, no pass/fail):** 2019-21H1 and 2021H2-23 with intervals.
- **Q8 Extension E1 (spread form, own gate):** run Q0-Q5 on 2024-01 → 2025-09; reported as a separate result, never pooled with the log-ratio estimate.
- **Q9 Calibration:** leave-one-out share of permutation p below 0.05 between 0.02 and 0.10.
- **Q10 Context (no pass/fail):** next to Boisvert et al. (0.10-0.18; 0.20-0.27), Niagara Mohawk industrial 0.11, Patrick and Wolak (0-0.27), and the exposed-share translation (aggregate σ about s times the exposed σ, s from 0.32 to 0.50); and the arithmetic of what σ implies: a 0.4 log move in the ratio shifts the load ratio by 0.4σ.

## What each outcome means
Q0 and Q2 pass, Q3-Q5 pass: an industrial substitution elasticity identified from weather-driven price shape, to be reported beside the household σ and the literature, with the exposed-share translation. Q5 fails with a tight interval: a bounded null in σ; the industrial response to price level **and** price shape within the day is excluded at the detectable size, which closes the within-day margin. Q0 or Q2 fail: the margin is not reachable with the data on disk; the thread is closed and the write-up states the detectable σ. Q3 fails: no interpretation. Q6 fails: the instruments disagree; the primary (W1) stands alone.

## Not covered
The sustained price level (von Graevenitz and Rottner; Gerster and Lamp), purchases against consumption, and plants' own generation. A result here does not speak to them.

## Data and code
Script `scripts/analysis/industry_iv_price_shape.py` (`--step 0`, `--step 1`; step 1 refuses to run if a step 0 gate failed), to be written and committed before any run, reusing the frame and inference helpers of `industry_iv_day_level.py`. Outputs `outputs/tables/industry_iv_price_shape{_step0,}{,_checks}.csv`. **Running needs the user's go-ahead ('Confirmed, run it').** Proposed order: step 0 on the primary sample (first stage, idle test, planted gate), then step 1; E1 afterwards, with its own step 0.

## Amendment (2026-11-17, script written, before any run)
1. **Blackout exclusion in the extension.** A data build (no estimation) showed the largest week-on-week load-ratio changes of the extension sample on 2025-04-28 (-0.67), 2025-05-05 (+0.65) and 2025-04-29 (+0.22): the Iberian blackout of 28 April 2025 and its restoration, and the partner days a week later. Registered before the run: **the outcome, price and ratio of 2025-04-28 → 2025-04-30 are set missing**, so those days, their partner days (05-05 → 05-07) and the rows whose 7, 14, 21, 28 and 35-day lags touch them drop out. The extension sample is **409 days** (427 without the exclusion). The primary sample is **993 days** (the same days as the day-level design); no exclusions.
2. **Instrument scaling.** W1 and S1 are standardised to unit standard deviation after differencing (scale does not change the estimate).
3. **Gate in the spread form.** Planted σ0 in the extension is a shape semi-elasticity per unit of (spread / mean price); the gate value 0.15 is applied to it as is, and the result is not read as σ.
4. **Log-ratio rows.** Days with p_E or p_M at or below zero are dropped from the primary sample's ratio (the exclusion matters only if such days exist in 2019-2023; the build gave 993 days, the same as the day-level frame).

## Amendment 2 (2026-11-17, registered after the step-0 gate failed on recovery and before any further run)
The first step 0 (nuisance method **N1**, the boosting of the other designs) returned 77-89% of a planted σ and failed Q2 (its result stays below, unaltered). Registered now, **using planted effects only, with no real outcome involved**:
1. **Alternative nuisance learners, chosen by the planted gate alone.** Two more learners for the cross-fitted nuisance step, applied identically to the outcome, the price ratio and the instruments, and to the planted outcome's refit: **N2** = OLS on dummies for weekday and month and linear terms of the E and M temperature and demand-forecast changes, the own lags of y and x at 7/14/28 days and gas; **N3** = regularised boosting (100 iterations, learning rate 0.05, at most 8 leaves, at least 100 observations per leaf, L2 penalty 5). Same blocks, purge and seed.
2. **Selection rule (fixed order, no discretion).** Run step 0 with N2; if Q2 passes, N2 is the learner for step 1. If it fails, run N3 and apply the same rule. If neither passes Q2: **the design is closed on the primary sample** and the stop rule stands. The real outcome is never used to choose among learners; Q0 and Q1 are recomputed under each learner and must also pass.
3. **Diagnostic only (no decision attached):** for each learner the same plants are also added **on the residual scale** (y_res - σ0 x_res, no refit). If these recover while the refit plants do not, the loss arises from refitting the planted outcome's nuisance; if they do not recover, from the instrument step or the inference. It is reported next to the gate and does not replace it.
4. **Same rules afterwards.** Step 1 (Q3-Q10) is unchanged, runs only with the learner that passed, and every result states that the original N1 gate failed. The extension (E1) has its own step 0 and applies the same fixed order. Step 1's `--method` is read from the step-0 files (the first of N1, N2, N3 whose Q2 passed); if none passed it refuses to run.
5. **What the choice means.** A learner that passes the planted gate is calibrated on the design's own noise; a learner that does not is not usable here. This registers a calibration step, not a way to obtain a result: N2 and N3 are not tried against the real outcome.

## Results
### Step 0, primary sample (run 2026-11-17, `industry_iv_price_shape.py --sample primary --step 0`, committed before the run; outputs `outputs/tables/industry_iv_price_shape_primary_step0{,_checks,_choice}.csv`). 993 days, log-ratio form, instrument W1. Planted effects only.
**First stage.** W1 F 22.7; S1 F 17.0; W1+S1 F 22.5. **Q0 passes.** **Q1 passes**: S1 on ln(p_E / p_V) has F 1.1 (idle). S1 is therefore eligible as a second instrument (its midday-load self-supply threat is not tested by Q1).
**Planted sigma (instrument W1).**

| Plant σ0 | Estimate | 95% randomization interval | Detected | Recovered |
|---|---|---|---|---|
| 0.05 | 0.029 | [-0.009, 0.051] | no (p 0.048, interval contains zero) | interval contains 0.05, point 0.021 off |
| 0.10 | 0.077 | [0.039, 0.100] | yes | contains 0.10 (upper end), 23% low |
| **0.15** | **0.118** | **[0.070, 0.142]** | yes | **no: interval excludes 0.15** |
| 0.30 | 0.268 | [0.213, 0.298] | yes | interval excludes 0.30 by 0.002, 11% low |
| 0.30 in 2019-21H1 only | 0.151 (weight 0.50) | [0.081, 0.246] | yes | |
| 0.30 in 2021H2-23 only | 0.105 (weight 0.35) | [-0.033, 0.177] | no | |

**Q2 fails** (planted 0.15 detected but **not recovered**: the interval [0.070, 0.142] excludes 0.15). The pipeline returns about 77-89% of a planted σ: it is **biased towards zero by roughly 10-25%** at these plants, which also means an estimate of σ from the real outcome would be a lower bound on the true response and could not be compared with the literature values without that correction. The smallest detected pooled plant is 0.10. Regime weights 0.50 / 0.35 (the 2021H2-23 half is not detected).
**Per the registered stop rule, step 1 does not run on the primary sample.** The failure is kept and not rescued. The script refuses to run step 1 (`sys.exit`). Not run: the extension step 0, and any real-outcome estimate.
**What this means.** The price ratio can be moved by wind shape (F 22.7), so the design is not closed for lack of an instrument; it fails at calibration. Candidate causes, not tested: attenuation introduced by refitting the planted outcome's double-ML residual (the plant is added on the raw ratio but the residual of the planted outcome is refitted, so part of the plant is predicted by the controls and removed), or by measurement error in the block price ratio. Any diagnostic of that attenuation, and any decision to alter the gate in light of it, would be a new registration.

### Step 0 with learner N2 (run 2026-11-17, `--sample primary --step 0 --method N2`, committed before the run; outputs `industry_iv_price_shape_primary_N2_step0{,_checks,_choice}.csv`)
F: W1 20.5, S1 13.4, W1+S1 16.6 (**Q0 passes**); idle test F 3.0 (**Q1 passes**; S1 eligible). Planted σ (instrument W1):

| Plant σ0 | Estimate | 95% interval | Detected | Recovered |
|---|---|---|---|---|
| 0.05 | 0.0336 | [0.003, 0.055] | yes (p 0.015) | yes |
| 0.10 | 0.0836 | [0.053, 0.105] | yes | yes |
| **0.15** | **0.1336** | **[0.103, 0.155]** | yes | **yes** |
| 0.30 | 0.2836 | [0.253, 0.305] | yes | yes |
| 0.30 in 2019-21H1 only | 0.183 (weight 0.61) | [0.111, 0.364] | yes | |
| 0.30 in 2021H2-23 only | 0.084 (weight 0.28) | [-0.117, 0.162] | no | |

**Q2 passes under N2** (0.15 detected and recovered; smallest detected plant 0.05). Per the registered fixed order, **N2 is the learner for step 1; N3 is not run.** The residual-scale diagnostic gives the same numbers as the refit plants (OLS is exactly linear, so refitting the plant changes nothing).
**Correction of my earlier reading of the N1 failure, recorded here.** Every N2 planted estimate sits at σ0 - 0.0164 (0.0336, 0.0836, 0.1336, 0.2836): the planted estimates contain the real-outcome component (disclosed in the step-0 design), so this offset **is the real-outcome σ under N2, about -0.016**, and was visible in step 0. The same reading of the N1 table gives offsets of -0.02 to -0.03. The N1 "attenuation" was therefore mostly this additive real component, not a proportional bias of the pipeline, and the N1 gate failed because the real component pushed the 0.15 plant's interval below 0.15. The N1 failure stands as recorded and the learner order was applied as registered, but **the planted gate was not blind to the real slope**, contrary to the intent of "no real-outcome slope printed or stored"; step 1 now adds the formal inference (interval, p, placebo, rules) around a number that step 0 already revealed approximately. This is stated before step 1 is run.

### Step 1, primary sample, learner N2 (run 2026-11-17, `--sample primary --step 1`, committed before the run; outputs `industry_iv_price_shape_primary_N2{,_checks}.csv`). Real outcome; σ = -slope of the week-on-week change in ln(L_E / L_M) on the change in ln(p_E / p_M); randomization intervals.
| Estimate | σ | 95% interval | p (t-rank) | F |
|---|---|---|---|---|
| **Primary, W1** | **-0.0164** | **[-0.047, +0.005]** | 0.013 | 20.5 |
| Placebo outcome | +0.0016 | [-0.022, +0.030] | 0.82 | |
| W1, 2019-21H1 | +0.0048 | [-0.025, +0.043] | 0.54 | 22.9 |
| W1, 2021H2-23 | -0.0325 | [-0.187, -0.005] | 0.002 | **8.0 (weak)** |
| S1 only | -0.0647 | [-0.141, -0.030] | 0.001 | 13.4 |
| W1+S1 | -0.0346 | [-0.055, -0.026] | 0.001 | 16.6 |

**Rules.** Q3 passes (placebo p 0.82). **Q4 fails** (σ-hat -0.016 is not in (0, 2]). **Q5 fails** (not a positive σ with an interval excluding zero; the primary interval contains zero). **Q6 fails** (Hansen p 0.029; W1 -0.016, S1 -0.065, both -0.035). Q7 above. Q9 passes (leave-one-out 0.049). Q10: exposed-customer interval if only the exposed share responded: [-0.095, +0.011] (s 0.50) to [-0.148, +0.017] (s 0.32).
**Reading, per the registered rules.** A negative σ-hat means the evening-to-midday load ratio **rises** when the evening-to-midday price ratio rises, the wrong sign for substitution; per Q4 the instrument is then **not read as identifying a price response**, and the result is **not interpreted as a bound on σ** (the pooled interval does exclude σ above about +0.005, but the sign rule has failed). The estimates differ by instrument (W1 -0.016, S1 -0.065, Hansen rejects), and the 2021H2-23 half has a weak first stage (F 8.0), so the pooled F of 20.5 is carried by 2019-21H1 where the estimate is a null around zero (+0.005). **What is consistent with the threats registered in advance:** S1's more negative value is the sign that sunshine lowers *metered* midday load directly (self-supply, cooling), which raises ln(L_E / L_M) on sunny days independently of the price; this is stated as a consistency with the registered exclusion threat, not as a tested mechanism. No substitution elasticity of the Boisvert size (0.10-0.18) is found with either instrument; no substitution is detected. The extension (E1) has not been run.

