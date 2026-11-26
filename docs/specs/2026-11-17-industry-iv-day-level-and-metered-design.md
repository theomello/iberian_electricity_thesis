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

**Data (inspected, not estimated).** ESIOS 836-846 (peninsular), 10-minute mean MW (`data/esios/esios_{836..846}.parquet`), summed to hourly: about 3.0 GW through 2018-2019 (monthly means 2.7-3.1 GW), 1.4 GW from January 2020, near zero from July 2020. The 2019 mean is about **56% of the E3-E6 mean load (5.4 GW)**; that ratio is of means only, since whether the service sectors are nested inside E3-E6 is not verified. The frame's 28-day lags and its start (2018-10-01) leave **2019 only**: roughly 250 non-holiday weekdays. January-February 2020 are excluded (a level break). The series is nearly flat (baseload). **Regulatory reading (Orden IET/2013/2013, `literature/BOE_Orden_IET_2013_2013_interrumpibilidad.pdf`, read 2026-11-17):** participants are high-voltage consumers buying in the production market directly or through a retailer, and the service **requires a consumption floor**: at least 50% (40 MW product) or 55% (5 MW product) of tariff-period-6 energy, and a verifiable average hourly consumption above a declared residual power (40 MW product: in at least 91% of hours). REE may also call reductions on economic criteria (article 8; suspended by Orden SND/260/2020). So a tight zero in this series is **built in by contract**, not evidence about behaviour; Part B is therefore read as "metered consumption under a contractual floor", and B3 below is reworded accordingly. Days of economic activation inside 2019 are not identified on disk and are a known contaminant.

**Outcomes and method.** Hourly d ln of the summed sector series, week-on-week, same frame, instrument and inference as the wind-speed estimation (hour is the unit; the permutation is across days within year-month, hour matched), residualised without its own lag for the placebo. Also the day-level version of Part A for this series, with its own gate.

**Step 0 (power gate, no real slope).** Planted -0.1 and -0.3 (as the exposed-subgroup design) on 2019 only.

**Rules.**
- **B1 Power.** Planted -0.3 detected and recovered, as X1. *Fails:* one year of wind-driven variation is too little for an instrument estimate; the series is reported as uninformative and the question needs more years (none exist on disk) or another source; stop.
- **B2 Placebo.** p above 0.05. *Fails:* not interpreted.
- **B3 Detection.** Real p at most 0.05 and interval excluding zero, negative sign: a metered consumption response, reported with its interval. Otherwise a bound, reported.
- **B4 Translation (arithmetic).** Bound times the 56% ratio of means gives the contribution to the aggregate; reported as approximate and not nested-verified.
- **B5 Context (no pass/fail).** Next to G1 (-0.033 [-0.116, +0.017], purchases, all years): consumption against purchases, and 2019 against all years.

**What each outcome means.** B1 fails: the metered series cannot be used with this instrument; the thread rests on purchases. B1 and B2 pass, B3 fails with a tight interval: the metered consumption of the largest consumers, in the pre-crisis year, does not follow wind-driven prices; because of the contractual floor this is the expected outcome and does **not** show that these plants would not respond without it, but it does close the "it is only the offset between procurement channels" reading for metered load under the floor (not for the crisis regime). B3 detected: a consumption response exists in the largest consumers; the aggregate null then reflects exposed share and regime weights, to be reported with the share translation.

## Write-up arithmetic (no run; committed numbers only)
- **Regime bounds (A4 of the planted test).** 2019-21H1 [-0.013, +0.107] and 2021H2-23 [-0.029, +0.009]: neither regime has a response more negative than about -0.03; the pre-crisis regime is imprecise on the positive side.
- **Exposure-share translation.** If a share s of E3-E6 load responds with elasticity e and nothing else does, the aggregate is s x e. The aggregate bound -0.021 therefore excludes **e = -0.5 for any share above 4%, e = -0.2 above 10.5%, e = -0.1 above 21%**. Applies to responses that move the metered same-hour load; it says nothing about the sustained-level margin of von Graevenitz and Rottner, nor about offset purchases.

- **Exposure share from the regulator (CNMC IS/DE/031/24, pages 26-27, `literature/CNMC_IS_DE_031_24_mercado_minorista_flexibilidad_2023.pdf`).** Industrial energy billed in December 2023: hourly variable price 32%, mixed 35% (CNMC counts mixed as half indexed), fixed by period 32%, single fixed price about 1%; so about **50% indexed** (about 45% in October 2021), 32% on hourly prices. The 67% quoted earlier is a share of customers, not of energy. With s between 0.32 and 0.50, the aggregate bound -0.021 implies an exposed-customer elasticity no more negative than about **-0.04 (s = 0.50) to -0.07 (s = 0.32)**. Caveats: the CNMC industrial segment is not the E3-E6 voltage set; the figures are 2021-23, nothing is known for 2019; an indexed contract does not guarantee a plant sees the hourly price inside the day. This is arithmetic on published numbers, not an estimate.

## Amendment 2026-11-17 (after further reading, before any run; rules above unchanged)
1. **Duration.** Boisvert, Cappers, Neenan and Scott (2004) find response is highest for short high-price episodes and falls as the high-price duration rises ("response fatigue"). A null for whole-day wind-driven price moves therefore says nothing about short, sharp spikes. Every Part A result is reported with this reading.
2. **Shifting against conserving.** The same study finds about 75% of the response is load shifted between periods rather than energy saved (Goldman et al. find the opposite split, about 75% conservation, for a different programme). Part A's day-level total is the margin where shifting nets out; a same-hour estimate is not comparable with their substitution elasticities (peak/off-peak usage ratio per price ratio, 0.10-0.18, up to 0.20-0.27 for customers with more short-term exposure).
3. **Instrument scope.** C1 is used here because it is the one instrument that passed the registered checks, not because other routes are excluded. The closed routes (bid-curve, slope, outage) may be reopened where the setting calls for them, each with a stated reason and the earlier failed checks (idle-wind zero first stage, 2019-21H1 placebo) as pre-registered hurdles. A price-shape design (substitution between peak and off-peak, log-odds of shares) is the setting where that case would be made; it is not registered here.
4. **Margins this thread does not cover:** the sustained price level (von Graevenitz and Rottner; Gerster and Lamp's implied -0.09 to -0.20 from levy exemptions) and the plant's own generation substitution.

## Amendment 2 (2026-11-17, scripts written, before any run): three deviations found while writing the code
1. **Sample.** The registered wording "the common sample of the wind-speed estimation, collapsed to days" cannot be met: that sample (19,388 hours) is restricted by bid-curve columns C1 does not use and contains only **142 complete 24-hour days** (1,061 dates with partial days). The day-level frame is instead built from the raw series: non-holiday weekdays 2019-02-05 → 2023-12-29 with complete 24-hour days, COVID months excluded, partner day (d-7) not a holiday: **993 days, mean daily price 95.74**. The hourly frame built the same way has 25,167 hours (not 19,388), so A3 compares the day-level estimate with the committed hourly interval from a somewhat different sample; this is stated with the result. Part B uses the same raw frame for 2019: **5,554 hours on 232 days (HOUR), 212 days (DAY)**.
2. **A5 intervals.** With three endogenous prices the randomization interval by test inversion is not implemented; A5 reports the permutation t-rank p (same 1,000 permutations) and a robust normal interval, and "intertemporal substitution detected" requires **both** p at most 0.05 and the normal interval excluding zero. The conditional first-stage F is the Angrist-Pischke form (other endogenous prices partialled out of the price and of the instruments, robust Wald), threshold 10 as registered.
3. **Metered ratio.** The B4 ratio of means is computed in the script on the 2019 sample (0.51 in a data check before any estimation), not the all-months 56% quoted above.
Also: the planted estimates in step 0 contain the real component (as in the earlier planted test), so step 0 is not blind to the real slope in the strict sense; the script prints only the registered rule outcomes and the planted table, and the real slope is never computed separately before step 1. Step 1 of each script refuses to run if step 0 has not been run or its gate (A0 for Part A; B1 per unit for Part B) failed.

## Data and code
Scripts `scripts/analysis/industry_iv_day_level.py` (Part A, step 0 and step 1) and `scripts/analysis/industry_iv_metered.py` (Part B), written and committed before they run; they reuse `industry_iv_instrument_settlement.build_frame`, `industry_iv_second_settlement.residualise`, `industry_iv_estimation.run_sub`. Outputs `outputs/tables/industry_iv_day_level{,_checks}.csv` and `industry_iv_metered{,_checks}.csv`. **Running needs the user's go-ahead ('Confirmed, run it').** Proposed order: step 0 of both parts (planted only, no real slope), then step 1 of whichever passes its gate. A gate that fails is reported and kept, not rescued by changing the instrument, sample or unit.

## Results
### Step 0 (run 2026-11-17, scripts `industry_iv_day_level.py --step 0` and `industry_iv_metered.py --step 0`, committed before the run; outputs `outputs/tables/industry_iv_day_level_step0{,_checks}.csv`, `industry_iv_metered_step0{,_checks}.csv`). Planted effects only; no real-outcome result computed.
**Part A, day level (993 days, mean daily price 95.74, first stage F 57).**

| Plant | Estimate | 95% randomization interval | Detected |
|---|---|---|---|
| pooled -0.02 | -0.0200 | [-0.046, +0.010] | no (p 0.041, interval contains zero) |
| pooled -0.03 | -0.0296 | [-0.056, +0.0003] | no (interval just touches zero; p 0.004) |
| pooled -0.05 | -0.0474 | [-0.075, -0.017] | yes |
| pooled -0.10 | -0.1006 | [-0.130, -0.069] | yes |
| -0.10 in 2019-21H1 only | -0.0299 | [-0.058, -0.005] | yes (regime weight 0.30) |
| -0.10 in 2021H2-23 only | -0.0721 | [-0.103, -0.034] | yes (regime weight 0.72) |

**A0 passes** (-0.05 detected and recovered). **A0b fails**: the smallest detected pooled plant is -0.05, not smaller than the hourly design's -0.03, so any real day-level result is a check on the margin, **not a new or tighter bound**. Regime weights 0.30 / 0.72, the same as hourly. Step 1 is therefore allowed to run, with that reading fixed in advance.

**Part B, metered consumption of the interruptibility-service participants, 2019 (mean price 50.19 HOUR / 49.17 DAY; metered load 0.511 of E3-E6).**

| Unit | n | F | Planted -0.1 | Planted -0.3 | B1 |
|---|---|---|---|---|---|
| HOUR | 5,554 hours, 232 days | 48.0 | -0.111 [-0.227, +0.049], not detected | -0.320 [-0.427, -0.167], detected | **pass** |
| DAY | 212 days | 65.6 | -0.119 [-0.236, +0.005], not detected | -0.315 [-0.435, -0.196], detected | **pass** |

Both units pass B1 (the expected DAY failure did not happen). The metered series can detect an elasticity of about -0.3 and not -0.1: **a real null here rules out only responses more negative than about -0.2 to -0.3**, which is weak next to the aggregate bound, and the contractual consumption floor applies. Step 1 not yet run.

### Step 1 (run 2026-11-17, same scripts with `--step 1`, committed before the run; outputs `industry_iv_day_level{,_checks,_crossday}.csv`, `industry_iv_metered{,_checks}.csv`). Real outcomes.
**Part A, day level (993 days, F 57; elasticity of daily E3-E6 load to the daily day-ahead price, randomization intervals).**

| Estimate | Elasticity | 95% interval | p (t-rank) |
|---|---|---|---|
| Primary | -0.0014 | [-0.027, +0.028] | 0.92 |
| d_pc only (F 109) | 0.0000 | [-0.020, +0.024] | 1.00 |
| 2019-21H1 | +0.040 | [-0.031, +0.141] | 0.090 |
| 2021H2-23 | -0.015 | [-0.041, +0.005] | 0.035 (AR 0.139) |
| Placebo outcome | -0.0203 | [-0.066, +0.023] | 0.088 |

**Rules.** A0b fails (fixed in step 0: a margin check, not a new bound). **A1 fails**: placebo p 0.088 passes but |elasticity| 0.0203 exceeds the registered 0.01, so per the rule **the day-level result is not interpreted**; it is reported for completeness and the failure is kept. A2 fails (p 0.92). A3 passes (-0.0014 inside the hourly interval [-0.021, +0.028]). A4 reported above. A6 passes (leave-one-out 0.049). Hansen J 0.32, p 0.57.
**A5 cross-day** (conditional F 56 / 45 / 64, so identified; 993 days with neighbours): price d-1 +0.011 [-0.013, +0.036] (t-rank p 0.021), own day +0.006 [-0.031, +0.043] (p 0.38), **next-day price -0.015 [-0.040, +0.010] (p 0.005)**, sum of three +0.002 [-0.020, +0.025] (p 0.55). Intertemporal substitution (positive next-day coefficient) **not detected**; the point estimate has the opposite sign. The t-rank p-values of the d-1 and d+1 terms and the robust normal intervals disagree (as for the bid-curve estimate, t-rank p 0.010 against AR p 0.178): the intervals contain zero and nothing is rescued.
**Reading.** Same-day and next-day prices do not move aggregate daily E3-E6 load detectably; the point estimate is a precise zero, matching the hourly result, but the placebo check fails by magnitude and the day-level design is no sharper than hourly, so this adds consistency, not a bound.

**Part B, metered consumption of the interruptibility-service participants, 2019.**

| Unit | Elasticity | 95% interval | p (t-rank) | Placebo | B2 | B3 |
|---|---|---|---|---|---|---|
| HOUR (F 48) | -0.0147 | [-0.133, +0.149] | 0.86 | +0.070 [-0.037, +0.218], p 0.058 | pass (borderline) | not detected |
| DAY (F 66) | -0.0086 | [-0.127, +0.109] | 0.91 | +0.012 [-0.072, +0.139], p 0.74 | pass | not detected |

B4 (ratio of means 0.51, approximate): the hourly interval translates to [-0.068, +0.076] and the daily to [-0.065, +0.056] in aggregate terms; both are far wider than the aggregate bound (-0.021). B5: G1 (purchases, all years) -0.033 [-0.116, +0.017].
**Reading.** Not detected, as expected under the contractual consumption floor. The step-0 gate showed only about -0.3 would have been detected, and the intervals confirm it: **the 2019 metered series rules out responses more negative than about -0.13 and says nothing finer**. It does not show these plants would not respond without the floor. Part B closes with "uninformative at the precision that matters"; its value is the metered-versus-purchases comparison, which is too wide to use.
