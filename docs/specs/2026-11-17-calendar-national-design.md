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
