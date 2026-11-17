# Day-level, cross-day and metered-consumption tests of the industrial response (pre-registration)

**Status: registered 2026-11-17, before any run. Nothing below has been estimated.** Follows the wind-speed IV (`2026-11-17-industry-iv-wind-speed-estimation-design.md`: +0.0001 [-0.021, +0.028]), its planted-effect test (detectable about -0.03, regimes weighted about 30/72) and the exposed subgroups (`...-exposed-subgroup-design.md`: bounds -0.12 to -0.16 on purchases). Instrument, inference and the project's rules are unchanged: C1 only, no new instrument, no outage instrument, no bid-curve or slope route. Designs are not chosen by the sign of their interval; each is gated on power first.

## What the two full texts change
**Patrick and Wolak (NBER 8213, 2001; read in full).** Customers on England and Wales' pool-price contract pay the half-hourly price; four fiscal years, one regional company, five industries. Own-price elasticities are heterogeneous (water supply the most responsive, steel tubes small), **uniformly small in the peak periods and larger (above 0.2, up to 0.27 for water supply) in the shoulders**, and the cross-price pattern shows within-day substitution and complementarity. They name a weekly horizon as unfinished work. Three consequences for us: (1) the response they measure is that of customers who *face* the real-time price, whereas E3-E6 load is mostly bought on fixed or indexed contracts; (2) their response is **intertemporal substitution**, so a same-hour regression, whose wind-driven price moves last the whole day, mixes own-price and cross-price effects; a day-level outcome nets the within-day shifting out, and a next-day price tests the anticipation margin; (3) elasticities at the mean are small (0.0-0.3), the size our designs can just detect.

**von Graevenitz and Rottner (ZEW DP 22-038, 2024; read in full).** German manufacturing plants, annual panel, plant fixed effects, network-charge changes as the instrument: own-price elasticity of **electricity procurement** -0.4 to -0.6, larger for small procurers, falling from 2009 to 2017, with plants **replacing procurement by onsite generation**; energy is about 2% of revenue. Consequences: their margin is the *sustained price level*, procurement not consumption, so it is not comparable with an hourly, wind-driven impact elasticity and does not contradict our null; and the onsite-generation channel is the same as our 91% offset finding. We cannot test their margin with data on disk (no plant panel, no network-charge variation); it is recorded as the **margin this thread does not cover**.

## Not chosen, and why
- **Cogeneration as an exposure channel.** Load is not observed at cogenerating sites: OMIE's 1,313 units are representatives' numbered units, 12.9% of capacity linked to a plant; REE's plant units are in the I90 sample only for 2022-04-01 → 2023-03-31 (`docs/data-reference/ownership-and-units.md`). It stays in its own design (`2026-11-10-cogeneration-design.md`, supply side). Not run here.
- **Weekly or longer horizon.** About 230 weekly observations in the sample; the planted-effect gate (below) would fail by construction. Closed without a run.
- **Interruptibility service as a *price-response* channel.** The service is called by REE, not by price. It is used below only as a **data source** (metered consumption of the largest consumers), not as a mechanism.

## Part A: day-level and cross-day response, aggregate E3-E6
**In one example.** On a Tuesday the whole day is windy, so every hour is cheaper than a week earlier. A plant that moves its shift into the cheap hours does not change its daily total; one that runs more because the day is cheap does. Taking the day's total load against the day's mean price measures the second, not the first. If tomorrow is also windy (known from about 13:00 today), a plant may run more tomorrow and less today: that shows as a positive effect of tomorrow's price on today's load.

**Frame.** The common sample of the wind-speed estimation, collapsed to days: non-holiday weekdays 2019-2023 without 2020-03 → 2020-06, only days (and their lag-7 days) with all 24 hours (no DST days). Outcome **d ln L_day** (week-on-week, same weekday, log of the 24-hour mean of ESIOS 1204-1207). Price **d P_day** (24-hour mean day-ahead price, week-on-week). Instruments: the 24-hour mean of d_pc and of its square (C1). Residualisation as before in spirit: double ML (time-blocked cross-fitting, 10 blocks, 14 days purged) on calendar terms, daily mean temperature and its square, and the daily series' own lags 7/14/28 days, **without** realised wind. Elasticity = slope x the sample's mean daily price. Inference: 1,000 permutations of the residualised instruments across days within year-month, seed 20261117, p from the rank of |t|, interval from the permutation Anderson-Rubin set (`industry_iv_estimation.py` logic, day as the unit).

**Estimands (closed list).**
- **A1 same-day:** ln L_d on P_d.
- **A2 cross-day:** ln L_d on {P_{d-1}, P_d, P_{d+1}} (week-on-week differences each), instruments the matching three d_pc means; P_{d+1} is public at about 13:00 on d, so shifting load into or out of tomorrow is feasible. Reports the three elasticities, their sum (the level response to a price rise that lasts three days) and the **conditional first-stage F of each price** given the others.

**Step 0 (power gate, no real-outcome slope printed or stored).** Plant beta = -0.02, -0.03, -0.05, -0.10 as `d ln L* = d ln L + (beta / pbar) x d P_day`, refit the residual, run A1 with the same seeds; and half-sample plants (-0.10 in 2019-21H1 only, in 2021H2-23 only) to report the regime weights at day level. Same construction as `2026-11-17-industry-iv-planted-effect-design.md`.

**Rules (each says what a failure would tell us).**
- **A0 Power.** Planted -0.05 detected (randomization p at most 0.05, interval excludes zero) and recovered (interval contains it; point within max(0.01, 30% of |beta|)). *Fails:* day-level aggregation loses more first-stage variation than it saves in noise; stop, report nothing about the real outcome, and record that the hourly bound stands alone.
- **A0b Sharper than hourly.** The smallest detected pooled plant is smaller in absolute value than -0.03 (the hourly design's detectable elasticity). *Fails:* the day-level result is reported but is **not** presented as a new or tighter bound; it is a check on the margin only.
- **A1 Placebo outcome.** Same pipeline on the 7-day-lagged difference: p above 0.05 and |elasticity| below 0.01. *Fails:* the day-level instrument moves load before it can respond; the day-level result is not interpreted.
- **A2 Detection (A1 estimand).** Elasticity negative, p at most 0.05 and the interval excludes zero. *Fails with A0, A1 passed:* a bounded null at day level, reported with its detectable size.
- **A3 Agreement with the hourly result.** The day-level point estimate lies inside the hourly randomization interval [-0.021, +0.028]. *Fails:* the margins differ (net daily response against same-hour); reported as a difference and read through A5.
- **A4 Regimes (no pass/fail).** 2019-21H1 and 2021H2-23 reported separately with randomization intervals (mandatory since P3 failed).
- **A5 Cross-day (A2 estimand).** Run only if every price's conditional first-stage F is at least 10; otherwise **stop**: "the three prices cannot be separated with one wind series", and only A1 stands. If run: intertemporal substitution is *detected* if the coefficient on P_{d+1} is positive, its p at most 0.05 and its interval excludes zero; the own-day coefficient is then a gross response. No other pass/fail.
- **A6 Calibration.** Leave-one-out share of permutation p below 0.05 between 0.02 and 0.10.

**What each outcome means.** A0 and A0b pass, A2 passes: a detected day-level response, to be put beside the household elasticity with its regime split. A0 and A0b pass, A2 fails: a bounded null at the net-daily margin, tighter than hourly; the claim becomes "neither within the hour nor across the day". A0 passes, A0b fails: the hourly bound is the sharpest bound; day level adds consistency only. A0 fails: day level is not informative; the question of the whole-day margin is closed with "no more power than hourly". A5 detected: the aggregate has an intertemporal-substitution margin, and the same-hour elasticity cannot be read as the response to a lasting price.

## Part B: metered consumption of the largest consumers, 2019
**In one example.** The interruptibility service's published series are the *metered* load of its participants, not purchases. If a steel mill in the service runs more on a windy, cheap Tuesday, the series shows it, and the 91% offset between procurement channels is not in the way. The cost is a short window.

**Data (inspected, not estimated).** ESIOS 836-846 (peninsular), 10-minute mean MW (`data/esios/esios_{836..846}.parquet`), summed to hourly: about 3.0 GW through 2018-2019 (monthly means 2.7-3.1 GW), 1.4 GW from January 2020, near zero from July 2020. The 2019 mean is about **56% of the E3-E6 mean load (5.4 GW)**; that ratio is of means only, since whether the service sectors are nested inside E3-E6 is not verified. The frame's 28-day lags and its start (2018-10-01) leave **2019 only**: roughly 250 non-holiday weekdays. January-February 2020 are excluded (a level break). The series is nearly flat (baseload), which is itself a prior that the result will be a tight zero; this is stated before the run.

**Outcomes and method.** Hourly d ln of the summed sector series, week-on-week, same frame, instrument and inference as the wind-speed estimation (hour is the unit; the permutation is across days within year-month, hour matched), residualised without its own lag for the placebo. Also the day-level version of Part A for this series, with its own gate.

**Step 0 (power gate, no real slope).** Planted -0.1 and -0.3 (as the exposed-subgroup design) on 2019 only.

**Rules.**
- **B1 Power.** Planted -0.3 detected and recovered, as X1. *Fails:* one year of wind-driven variation is too little for an instrument estimate; the series is reported as uninformative and the question needs more years (none exist on disk) or another source; stop.
- **B2 Placebo.** p above 0.05. *Fails:* not interpreted.
- **B3 Detection.** Real p at most 0.05 and interval excluding zero, negative sign: a metered consumption response, reported with its interval. Otherwise a bound, reported.
- **B4 Translation (arithmetic).** Bound times the 56% ratio of means gives the contribution to the aggregate; reported as approximate and not nested-verified.
- **B5 Context (no pass/fail).** Next to G1 (-0.033 [-0.116, +0.017], purchases, all years): consumption against purchases, and 2019 against all years.

**What each outcome means.** B1 fails: the metered series cannot be used with this instrument; the thread rests on purchases. B1 and B2 pass, B3 fails with a tight interval: even metered consumption of the largest consumers, in the pre-crisis year, does not follow wind-driven prices, which closes the "it is only the offset" reading for them (not for the crisis regime). B3 detected: a consumption response exists in the largest consumers; the aggregate null then reflects exposed share and regime weights, to be reported with the share translation.

## Write-up arithmetic (no run; committed numbers only)
- **Regime bounds (A4 of the planted test).** 2019-21H1 [-0.013, +0.107] and 2021H2-23 [-0.029, +0.009]: neither regime has a response more negative than about -0.03; the pre-crisis regime is imprecise on the positive side.
- **Exposure-share translation.** If a share s of E3-E6 load responds with elasticity e and nothing else does, the aggregate is s x e. The aggregate bound -0.021 therefore excludes **e = -0.5 for any share above 4%, e = -0.2 above 10.5%, e = -0.1 above 21%**. Applies to responses that move the metered same-hour load; it says nothing about the sustained-level margin of von Graevenitz and Rottner, nor about offset purchases.

## Data and code
Scripts `scripts/analysis/industry_iv_day_level.py` (Part A, step 0 and step 1) and `scripts/analysis/industry_iv_metered.py` (Part B), written and committed before they run; they reuse `industry_iv_instrument_settlement.build_frame`, `industry_iv_second_settlement.residualise`, `industry_iv_estimation.run_sub`. Outputs `outputs/tables/industry_iv_day_level{,_checks}.csv` and `industry_iv_metered{,_checks}.csv`. **Running needs the user's go-ahead ('Confirmed, run it').** Proposed order: step 0 of both parts (planted only, no real slope), then step 1 of whichever passes its gate. A gate that fails is reported and kept, not rescued by changing the instrument, sample or unit.

## Results
(not run)
