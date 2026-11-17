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

## Results
(not run)
