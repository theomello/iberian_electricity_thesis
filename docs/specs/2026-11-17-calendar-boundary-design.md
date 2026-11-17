# Calendar boundaries of the business tariffs as a repeated price shock (proposal; step zero only)

**Status: proposed 2026-11-16, not registered. Binding when the user confirms and this file is committed; only step zero (S0-S2) is covered now. The estimation rules are registered in a separate amendment after step zero passes.** Source idea: `notes/idea-calendar-boundary-business-tariffs.md`. Data: `docs/data-reference/barcelona-electricity-by-postal-code.md` (unit kWh, 42 postal codes, 2019-2025, four six-hour bands, sectors Serveis, Residencial, Indústria). Literature read: Jessoe and Rapson (2015, mandatory TOU for commercial and industrial firms: little or no change in usage), Blonz (critical-peak pricing for small business: peak use -13.5%, elasticity -0.119), Hausman and Rapson (regression discontinuity in time: seasonality, serial correlation and short windows are the pitfalls). Aigner, Newman and Tishler (1994) not available.

**In one example.** A shop in the Eixample on tariff 3.0TD pays about €77/MWh in tolls and charges for a weekday 9-14h hour in July and about €32 in June (2021 values). On 1 July the top-period price steps up by about €45; on 1 September nothing changes. A model that looks at how the weekday daytime use of services in Barcelona moved around 1 July, relative to its own nights and weekends, relative to households (who face no step), and relative to the same dates in 2019 (before the six-period tariff), asks whether business demand follows the calendar. The step-zero question is only whether the data are quiet enough to see such a response: the same statistic on dates where nothing changes (1 January, 1 February, 1 May, 1 September) must be tight relative to the size of a real step.

## Why not the paper's LASSO here
The seasons are calendar months, so month dummies in a per-hour LASSO would absorb the boundary jump. The design uses **year-over-year differencing against 2019** (the first-differencing logic that worked for GoiEner), with day-minus-night, working-day-minus-weekend and business-minus-household layers; a LASSO is not used.

## The statistic (computed per boundary date b and year Y, city level, sector s)
Window: 14 days before and 14 days after the date (the date itself belongs to the 'after' window).
1. Log of the sum over the day bands (06-12, 12-18, 18-24) minus log of the 00-06 band, daily.
2. Working-day mean minus weekend-and-national-holiday mean, within each side of the date.
3. After minus before: **S(b, Y, s)**.
4. Difference against 2019 at the same calendar date: **D(b, Y, s) = S(b, Y, s) - S(b, 2019, s)**.
5. Business minus household: **DD(b, Y) = D(b, Y, Serveis) - D(b, Y, Residencial)**. Indústria is reported separately in the same way.
Event set. **Real boundaries** (price step in the top daytime period, sealed in step zero): 1 March, 1 April, 1 June, 1 July, 1 August, 1 October, 1 November, 1 December. **Placebo dates** (no change in the season: top period price unchanged): 1 January, 1 February, 1 May, 1 September. The 1 June 2021 boundary coincides with the reform start and is dropped in 2021. Years Y: 2021 (second half), 2022, 2023, 2024, 2025 (to November); 2019 is the base year; 2020 is excluded (COVID). The sample of events is 4 placebo dates by up to 5 years, about 18 usable (some 2021 and 2025 windows are incomplete).

## Step zero
- **S0 Data.** At least 95% of the calendar days of the windows around the placebo dates and the real boundaries exist in 2019 and in at least three of the post years (missing day 2025-08-19 and the cut at 2025-11-30 noted); Serveis has non-zero day-band values in at least 30 postal codes on at least 95% of days; the 'No consta' band is dropped. *Fails:* stop, the data cannot support the design.
- **S1 Noise.** The standard deviation of DD across the placebo events (computed only on placebo dates; the real-boundary windows stay sealed) gives a detectable elasticity (2.8 × sd / dose) of at most **0.15**, where the dose is the mean absolute log change of the top-period price for the real boundaries (3.0TD, 2021 tolls and charges, each year's mean OMIE price over the window as the energy price, `outputs/tables/tou_tariff_prices_2021.csv`; 2022-25 tolls and charges are not yet read, so this dose is an approximation and is labelled so). Also reported: the same sd for mid-month dates (the 15th of each month, windows of 14 days) as a larger placebo set, and for Indústria. *Fails:* the design is closed with the detectable elasticity recorded; no real boundary is computed.
- **S2 Seal.** The step-zero script takes the list of events as an argument and computes only the placebo dates and mid-month dates; the real boundary windows are not computed or printed. (Checked in the script: the real dates are not in the event list.)
Both S0 and S1 are gates; S1's 0.15 bar is a judgement set before any number is seen: it sits between the Blonz elasticity (-0.12) and zero.

## What each outcome means
S0 and S1 pass: the design is feasible; the estimation rules (sign pattern across steps of both signs, dose-response across years, a randomization test that reassigns real doses over real and placebo events, a placebo outcome in Residencial, leave-one-boundary-out, hour-band checks) are registered next and the real boundaries are opened. S1 fails: the data are too noisy at the 2-week window, and either longer windows or a tariff-level data source (which the national E1-E6 series cannot give for 3.0TD) is needed; recorded as a stop. S0 fails: gap or coverage problem in Barcelona.

## Threats (carried from the note, plus)
Pass-through of toll changes to the contract the shop pays; July heat and August holidays coincide with boundaries (the layers guard, not prove); 2019 is the only clean pre-year in Barcelona, so the base year is one year of noise; the dose for 2022-2025 uses 2021 tolls and charges until the later resolutions are read; services are not only 3.0TD; the six-hour bands blend several price periods (06-12 contains P6, P2 and the top period); anticipation (the calendar is known a year ahead).

## Data and code
`data/barcelona_electricity/raw/*.csv`, `outputs/tables/tou_tariff_prices_2021.csv`, OMIE hourly prices, holiday calendar. New code `scripts/analysis/calendar_boundary_noise.py`; outputs `outputs/tables/calendar_boundary_noise.csv`. No random draws; the statistic is deterministic.

## Results of step zero (run 2026-11-16; `calendar_boundary_noise.py`, committed before the run; outputs `outputs/tables/calendar_boundary_noise{,_summary}.csv`, `calendar_boundary_dose.csv`)

The first run returned NaN for most events because the weekend side of each window was built from national holidays only (a code bug; weekends were not counted). Fixed (weekends and national holidays), rules unchanged, rerun. Forced by the data: 1 January cannot be computed (the 2018 days of its 2019 window do not exist), so the placebo dates are 1 Feb, 1 May, 1 Sep: 13 events (2021 Sep; 2022-2025 Feb, May, Sep).

- **S0 passes:** 99.9% of the window days exist (1,862 of 1,863); 99.9% of days have at least 30 Serveis postal codes with non-zero day bands.
- **Dose (prices only; no outcome at a real boundary was computed):** 34 real boundary-years (2021 H2 to 2025), steps of ±14.7, ±18.1, ±41.9 and ±45.3 €/MWh on the 3.0TD top period, **mean |log dose| 0.248** (by year 0.19, 0.15, 0.25, 0.32, 0.34).
- **S1 fails as registered:** placebo-date sd of DD (Serveis minus Residencial) = 0.038 (mean +0.017), detectable elasticity 2.8 × 0.038 / 0.248 = **0.43**, bar 0.15. Mid-month dates (53 events) give sd 0.058, detectable 0.66. Indústria is noisier (sd 0.11, detectable 1.24).

**By the registered rule the design closes here.** One point must be recorded with the failure: S1, as I wrote it, is a *single-event* detectability (one boundary against the placebo spread). The estimator the design would use pools many events (a regression of D on the log dose through the origin, about 34 real boundary-years), whose precision is about sd / sqrt(sum of squared doses) = 0.038 / sqrt(3.09) = 0.0215, a detectable elasticity of **0.060** if the 34 events were independent (they are not: events in the same year share year effects, and 2019 is the only base year, so the effective number is lower). So S1 asked a stricter question than the estimator needs. This is recorded as a flaw in the rule, not as a pass; whether to amend S1 to a pooled, year-clustered version and run a new step zero is the user's decision, as it would be made after seeing this result.

## Amendment 2026-11-16 (user decision, after seeing the S1 result): S1b, a pooled and year-clustered detectability

**This amendment is post hoc**: it was written after S1 failed as registered and after the independence-based pooled figure (0.060) was seen. The original S1 and its failure stay in the record. The bar is **not relaxed**: 0.15.

**S1b (replaces S1 as the gate).** Detectable elasticity of the pooled estimator `eta = sum(dose_i · D_i) / sum(dose_i²)` over the real boundary-years (dose_i the log top-period price change of the 34 real events, `calendar_boundary_dose.csv`):
1. Event-level noise sd = the placebo-date sd of DD (Serveis minus Residencial), 0.0379 (13 events; computed in step zero).
2. Independence precision: SE_ind = sd / sqrt(sum(dose_i²)).
3. **Year clustering:** events in one year share year effects. The intra-year correlation rho is estimated from the 53 mid-month placebo events by one-way ANOVA across the five years (estimator (MSB - MSW) / (MSB + (k0 - 1) MSW), floored at 0 and capped at 1; k0 the adjusted mean group size). Design effect DEFF = 1 + (m - 1) rho with m = mean number of real events per year (34 / 5 = 6.8). SE_pooled = SE_ind × sqrt(DEFF); detectable = 2.8 × SE_pooled.
4. **Pass if detectable <= 0.15.** Sensitivity (no rule): the same with the mid-month sd (0.0584) instead of the placebo-date sd, and with rho replaced by 0.5.
Only placebo outputs and prices are used; no real boundary outcome is computed. If S1b fails, the design closes and the estimate stays recorded. If it passes, the estimation rules are registered next as a separate amendment before any real boundary window is opened.

## Result of S1b (run 2026-11-16; `calendar_boundary_s1b.py`, committed before the run; output `outputs/tables/calendar_boundary_s1b.csv`)

**S1b passes: detectable elasticity 0.060 (bar 0.15).** Components: 34 real boundary-years, sum of squared doses 3.09, placebo-date sd 0.0379, SE under independence 0.0215. The intra-year correlation estimated from the 53 mid-month placebo events is 0 (MSB 0.0026 below MSW 0.0035; floored at 0), so DEFF = 1 and the clustered detectability equals the independence figure. Sensitivity (no rule): with the mid-month sd 0.0584 the detectable elasticity is 0.093; with an assumed intra-year correlation of 0.5 it is 0.119; both stay below 0.15. The rho estimate rests on only five years and should not be read as 'no clustering'. **Step zero is passed as amended (post hoc); the original S1 failure stays in the record.**

## Estimation rules (proposed 2026-11-16; binding when the user confirms and this file is committed; no real boundary window is computed before that)

**Estimator.** For each real boundary-year i (34 events, 2021 H2 to 2025), DD_i = D_i(Serveis) - D_i(Residencial) as in step zero (year-over-year difference against 2019 of the working-day-minus-weekend, day-minus-night, after-minus-before contrast). Dose_i = log change of the 3.0TD top-period price (2021 tolls and charges, each year's mean OMIE price in the window; the 2022-2025 toll and charge values are not yet read, so this dose is an approximation, labelled in every table). **eta = sum(dose_i DD_i) / sum(dose_i²)**, the elasticity of the relative business daytime-over-night, weekday-over-weekend ratio to the price. Indústria is run the same way as a secondary series.
**Inference.** Randomization: dose labels are permuted **within year** across the 34 real events and the 13 placebo and 53 mid-month events of the same year (events without a price change carry dose 0; 10,000 permutations; one-sided p = (1 + #{eta_perm <= eta_real}) / (1 + N)); Fisher-style interval from the permutation distribution.
- **E1 Sign and detection.** eta in [-1, 0] and the one-sided randomization p <= 0.05, interval excluding zero. *Fails:* a bounded response (the interval is reported as the result); if eta is positive, flag as a sign failure and look at E3 and E4 for the cause.
- **E2 Alternation.** The estimates from price-up boundaries (positive dose) and price-down boundaries (negative dose) are estimated separately and both are negative (a response that follows the sign of the step, not a season turn). *Fails:* the response is asymmetric or driven by one season, which points to a seasonal confound.
- **E3 Placebo outcome.** The same estimator with Residencial alone (D_res, households, no boundary) as outcome: two-sided randomization p above 0.05 and absolute eta below one third of the main estimate. *Fails:* the dose pattern moves households too, so the DD is not a business response.
- **E4 Leave-out stability.** Dropping each year, and each of the eight boundary months in turn, eta keeps its sign and stays inside the main interval. *Fails:* the result is carried by one year or one boundary (August and July are the candidates).
- **E5 Band robustness.** Using only bands 12-18 and 18-24 as the 'day' (more top-period hours), the estimate has the same sign and lies inside the main interval.
- **E6 Dose approximation (description).** The estimate rescaled with the actual 2022-2025 tolls and charges once read, and with a half-size pass-through assumption, reported as a range; no pass/fail.
- **E7 Heterogeneity (exploratory, no pass/fail).** By year (the dose grows from 0.15 to 0.34), by sign of the step, and for Indústria.
- **E8 Portuguese control (added 2026-11-16 at the user's suggestion; robustness, same status as E1-E7).** The same statistic computed on Portugal's national load (REN, data on disk) in place of Residencial: DD_PT = D(Serveis) - D(Portugal). Portugal's tariffs have their own seasons and their own clock-change cycle, so the dates 1 April and 1 October (next to the late-March and late-October clock changes) are dropped in this version, and the boundary-years in which ERSE changed the access tariffs on a Spanish boundary date (the exceptional settings of 1 July 2023 and 1 June 2024 reported in `notes/idea-portugal-access-tariff-swing.md`, not verified) are dropped until ERSE's tariff tables have been read. Pass: the estimate has the same sign as the main estimate and lies inside its randomization interval. *Fails:* the national Portuguese series is not a comparable control (it is dominated by households and large industry, and its weather and holidays differ), which is recorded; the Residencial version stays the primary.
A failed rule is recorded and kept; no other window length, sector aggregation or base year is tried after a failure.

**What each outcome means.** E1 to E4 pass: a business response to the regulated price calendar, identified from repeated alternating steps, comparable with the household -0.05 (a different margin: month-scale shifting of daytime use, in one city, for services). E1 fails with E3 passing: a bounded response whose interval is the contribution. E3 fails: the design does not isolate a business response.

Code: `scripts/analysis/calendar_boundary_estimate.py`; outputs `outputs/tables/calendar_boundary_estimate.csv`.

## Results of the estimation rules (run 2026-11-16; `calendar_boundary_estimate.py`, committed before the run; outputs `outputs/tables/calendar_boundary_estimate{,_summary}.csv`)

34 real boundary-years (2021 H2 to 2025), Serveis minus Residencial, Barcelona, 3.0TD top-period log dose (2021 tolls and charges; 2022-25 values not read), within-year randomization over 100 events (10,000 draws).

| Rule | Result | Detail |
|---|---|---|
| **E1 sign and detection** | **fail** | **eta = -0.004, one-sided p 0.46, interval [-0.080, +0.071]** |
| E2 alternation | fail | price-up boundaries -0.103 (17 events); price-down boundaries **+0.053** (17 events): the two signs disagree |
| E3 placebo outcome | fail (by the size clause) | Residencial alone eta -0.029, two-sided p 0.35; the p-value passes but the size is not below one third of the main estimate (-0.004) |
| E4 leave-out stability | fail | leaving out 2021, 2024, March, July or November flips the sign (+0.009, +0.044, +0.008, +0.038, +0.022); range -0.053 to +0.044 |
| E5 band robustness | fail | bands 12-24 as day: +0.022 |
| E6 (description) | | half pass-through range -0.004 to -0.008 |
| E7 (exploratory) | | by year 2021 -0.157, 2022 -0.002, 2023 +0.012, 2024 -0.077, 2025 +0.152; Indústria -0.041 |
| E8 Portuguese control | fail (by the interval clause) | eta -0.143 (24 events), same sign as the main estimate but outside its interval; the result depends on the control |

**By the user's stated stop rule (E1 or E3 failing closes the design), the calendar-boundary design is closed.** No other window, sector aggregation or base year is tried.

**What stands.** A bounded result: the pooled elasticity of Barcelona services' relative day-use to the 3.0TD calendar steps is -0.004 with a 95% randomization interval of [-0.080, +0.071], consistent with no response and ruling out responses stronger than about -0.08 (Blonz's -0.12 is outside the interval; Jessoe and Rapson's near-zero is inside). The sign pattern is not alternating (up-steps negative, down-steps positive), single years and boundaries move the estimate, and a different control (Portugal's national load) gives -0.14, so the estimate is sensitive to the control and the design does not identify a business response. The small residual household 'response' (-0.029) means the dose pattern also moves households relative to the 2019 base.
