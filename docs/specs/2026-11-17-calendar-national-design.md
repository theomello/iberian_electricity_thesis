# Calendar boundaries on the national voltage-band series (route R4; proposal, step zero only)

**Status: proposed 2026-11-16, not registered. Binding when the user confirms and this file is committed; only step zero (S0, S1b) is covered. Estimation rules are registered in a separate amendment after step zero passes, and the real boundary windows stay sealed until then.** Follows `2026-11-17-calendar-boundary-design.md` (Barcelona services: S1 failed as registered, S1b passed post hoc, estimation E1 failed, eta -0.004 [-0.080, +0.071], Portugal control -0.143) and `docs/business-demand-evidence.md`. This is the same identification (the eight season boundaries of the six-period business tariffs) on **independent data**: national hourly voltage-band demand, with two clean pre-years (2018, 2019) instead of one. It is a new test, not a rescue; a failure here closes the calendar idea.

**In one example.** On 1 July 2021 the top-period price of tariff 6.1TD steps up by about €29/MWh (medium season to high season) and drops back on 1 August. ESIOS publishes hourly demand for the 1-30 kV customers (E1+E2, 80% on 6.1TD). If those customers respond, their daytime use against their own night (P6, unchanged) and against weekends should dip in July and recover in August, relative to what 2018 and 2019 looked like on the same dates, and relative to Portugal. Step zero asks only whether those series are quiet enough on dates where nothing changes.

## Data and series
ESIOS hourly demand: **E1+E2** = indicators 1202 + 1203 (80% tariff 6.1TD, 20% old 3.1 -> 6.1); **6.2, 6.3, 6.4** = 1216, 1217, 1218 (pure tariffs, steps a half to a quarter of 6.1TD, secondary); 2018-01-01 to 2026-04. Control: Portugal national consumption (REN `Consumption`, 15-minute, Lisbon time, Portuguese holidays). Doses: the 6.1TD top-period toll-plus-charge steps of the eight boundaries (2021 values: -12, -27, +10, +29, -29, -10, +27, +12 €/MWh for 1 Mar, 1 Apr, 1 Jun, 1 Jul, 1 Aug, 1 Oct, 1 Nov, 1 Dec from `notes/idea-calendar-boundary-business-tariffs.md`; recomputed from `outputs/tables/tou_tariff_prices_2021.csv` in the script), converted to log changes with each year's mean OMIE price over the window; applied to E1+E2 as if all 6.1TD (labelled approximation). **The old 6.x tariffs had their own boundaries (Orden ITC/2794/2007: August all off-peak, June split on the 16th), so 2018-2019 are not zero-dose base years on the real dates; the estimation rules will use the new dose minus the old dose at the same date, built from the old tariff tables. Step zero uses placebo dates, where neither regime has a step.**

## The statistic
Per date t0, year Y, series s; window 14 days before and 14 days from t0:
1. ln(sum of hours 8-23) minus ln(sum of hours 0-7), daily (night is P6 every day; the day hours are on the seasonal periods).
2. Working-day mean minus weekend-and-national-holiday mean, within each side.
3. After minus before: S(t0, Y, s).
4. D(t0, Y, s) = S(t0, Y, s) - average of S(t0, 2018, s) and S(t0, 2019, s).
5. DD(t0, Y) = D(t0, Y, s) - D(t0, Y, Portugal).
**Placebo events (computed in step zero):** the 15th of January, February, March, April, May, July, August, September, October, November and December in 2021 (from 15 July) to 2025 (to the end of the data); June is excluded (old 16 June step); windows then span the 1st to the 28th of the month with no season boundary inside either side. **Real boundary windows (1 Mar, 1 Apr, 1 Jun, 1 Jul, 1 Aug, 1 Oct, 1 Nov, 1 Dec) are not computed in step zero; the script takes the event list as an argument and asserts that no real date is in it.**

## Step zero
- **S0 Data.** At least 95% of the calendar days of the placebo windows exist in the series and in Portugal, in 2018, 2019 and at least three of the post years. *Fails:* stop.
- **S1b Noise (pooled and year-clustered; written this way from the start after the Barcelona lesson).** sd of DD across the placebo events (E1+E2); SE_ind = sd / sqrt(sum of squared log doses over the real boundary-years, 2021 H2 to 2025); the intra-year correlation rho by one-way ANOVA of DD across the post years on the same placebo events, floored at 0 and capped at 1; DEFF = 1 + (m - 1) rho with m the mean number of real events per year; **detectable elasticity = 2.8 × SE_ind × sqrt(DEFF)**. **Pass if at most 0.15.** Sensitivity (no rule): rho = 0.5, and the same for 6.2, 6.3, 6.4 separately.
*If S1b fails, the calendar design is closed* with the detectable elasticity recorded; the estimate is not computed.

## What each outcome means
S0 and S1b pass: the national series are quiet enough; the estimation rules (same structure as the Barcelona ones: sign and detection by within-year randomization, alternation of up and down steps, placebo outcome in the series without a boundary, leave-one-out, the Portugal control, the old-tariff dose subtracted) are registered next. S1b fails: calendar boundaries cannot identify a business response with Spanish national data either, and the business bound stays the one in `docs/business-demand-evidence.md`.

## Threats
The national series mixes customers with different tariffs and sectors; the 6.1TD dose (log 0.1-0.25) is smaller than the Barcelona 3.0TD dose (0.25), and 6.2-6.4 smaller still, so detectability may fail; Portugal's own cycle follows the clock changes (the dates 1 April and 1 October are dropped in the Portugal-control version) and ERSE tariff steps may coincide with boundaries; the old tariff's boundaries contaminate the base years on the real dates (handled in estimation, not in step zero); COVID in 2020 is excluded from the base; 2022-2023 price levels change the log dose; pass-through of tolls to the customer's contract is unknown.

## Code
`scripts/analysis/calendar_national_noise.py` (placebo events only); outputs `outputs/tables/calendar_national_noise*.csv`. The statistic is deterministic; no random draws.

## Results of step zero (run 2026-11-16; `calendar_national_noise.py`, committed before the run; outputs `outputs/tables/calendar_national_noise{,_summary}.csv`)

**S0 passes:** 99.9% of the window days exist in every series (E1+E2, 6.2, 6.3, 6.4, Portugal) in 2018, 2019 and the post years. 50 placebo events (the 15th of eleven months, 2021 H2 to 2025). Real boundary windows were not computed.

| Series | Tariff | Mean abs log dose | Placebo sd of DD | rho (mid-month ANOVA) | Detectable (S1b) | Detectable at rho = 0.5 |
|---|---|---|---|---|---|---|
| **E1+E2** | 6.1TD | 0.185 | 0.0321 | 0.0 | **0.067** | 0.132 |
| 6.2 | 6.2TD | 0.111 | 0.0335 | 0.0 | 0.109 | 0.215 |
| 6.3 | 6.3TD | 0.104 | 0.0504 | 0.0 | 0.172 | 0.340 |
| 6.4 | 6.4TD | 0.061 | 0.0440 | 0.0 | 0.248 | 0.491 |

**S1b passes for E1+E2 (0.067, bar 0.15), also at an assumed intra-year correlation of 0.5 (0.132).** 6.2 would pass at rho 0 and fail at 0.5; 6.3 and 6.4 fail and are descriptive only. The rho estimate is again 0 and rests on five years. The national E1+E2 noise (sd 0.032) is similar to Barcelona services (0.038), with a smaller dose (0.185 against 0.248) and 50 placebo events instead of 13.

## Estimation rules (proposed 2026-11-16; binding when the user confirms and this file is committed; the real boundary windows stay sealed until then)

**Prerequisite R0 (old-tariff dose).** The old 6.x tariffs had their own season boundaries (Orden ITC/2794/2007), so on each real date the 2018-2019 base already contains an old step. The regressor is the **dose difference** dose_new - dose_old (log top-period price change at that date under the new and the old calendar, the same energy price). The old table is built from `docs/tou-policy-sources.md` (old period calendar) and the old tolls in `outputs/tables/tou_tariff_old_vs_new_2021.csv`; **stop rule: if the old dose cannot be reproduced for at least six of the eight boundaries, the estimation is not run.**
**Estimator.** eta = sum(doseDiff_i DD_i) / sum(doseDiff_i²) over the 34 real boundary-years of E1+E2 (DD against Portugal). Randomization: doseDiff labels permuted within year over the real and the 50 placebo events (placebo dose 0; 10,000 draws), one-sided p, interval eta - [q97.5, q2.5].
- **E1 Sign and detection.** eta in [-1, 0], one-sided p <= 0.05, interval excluding zero.
- **E2 Alternation.** Estimates from price-up and price-down boundaries separately are both negative.
- **E3 Placebo outcome.** The same estimator with Portugal's D alone as outcome: two-sided p above 0.05 and absolute eta below one third of the main estimate.
- **E4 Leave-out stability.** Dropping each year and each boundary month keeps the sign and stays inside the main interval.
- **E5 Hour-window robustness.** With the top-period hours 9-14 and 18-22 as 'day' (against 0-7), same sign and inside the main interval.
- **E6 Control sensitivity.** With no control (D alone) and with the Portugal control, the estimates have the same sign and each lies inside the other's interval. (The Barcelona estimate failed here.)
- **E7 Other tariffs (description).** 6.2 as a secondary series (detectable 0.109); 6.3 and 6.4 descriptive; whether the estimates line up across the four tariffs given their doses.
- **E8 Exploratory.** By year and by sign.
Failed rules are recorded and kept; no other window, series, base year or control is tried. If E1 or E3 fails, the calendar design is closed for good (Barcelona and national).
