# Does the firms' period-calendar shift come back every year? Medium firms and large industry, 2022–2025 (proposal)

**Status: registered 2026-11-23 (user: "Register it"); binding from this commit.** On
2026-11-23 the user asked for a persistence test for both firm groups, and for using all seasons, not only summer.
Revised before registration after a two-lens review; the changes are listed at the end.

Two earlier results stand and are not re-judged:
- **Medium firms** (`2026-11-23-medium-firms-period-calendar-design.md`): E1 and E2 pass, the E3 trend null fails
  (p 0.103). Reported as a shift that rests on the null model, not an estimate.
- **Large industry** (`2026-11-18-industry-regulated-price-elasticity-design.md`): the E6 reduced form gives −1.0
  point per period step, p 0.0001.

This is a new test, on years after 2021. **It is not a fallback for either verdict.**

**Terms.**
- **E1+E2**: measured demand at 1–36 kV, ESIOS indicators 1202 + 1203, mostly tariff 6.1TD. ESIOS is the data portal
  of REE (Red Eléctrica), the grid operator.
- **6.2, 6.3, 6.4**: ESIOS tariff series 1216, 1217 and 1218, for demand at 30 kV and above.
- **Period step**: old period number minus new period number for the hour (positive = the hour became dearer).
- **OLS**: ordinary least squares. **sd**: standard deviation. **MDE**: minimum detectable effect.
- **REN**: Redes Energéticas Nacionais, the Portuguese grid operator, whose files carry the Spanish day-ahead price.
- **RDL**: Real Decreto-ley (royal decree-law).

To avoid clashing with tariff periods (P1–P6), the rules are named R1–R9.

## In one example
In August before 2021, every hour of a 6.1 or 6.4 tariff was the cheapest period (P6). Since June 2021, August
daytime has been P3 or P4, two or three periods dearer. In summer 2021 the share of the day's load in those hours fell
relative to normal summers. If firms responded to the calendar, the same fall should appear in every later year,
because the calendar has not changed since. If 2021 was a one-off (COVID recovery, an odd August), it should not
come back. Using four later years also lowers the noise on the treated side.

## What is not blind
- Both groups' 2021 results.
- **`calendar_national_estimate`** (`docs/specs/2026-11-17-calendar-national-design.md`, run 2026-11-16) computed, for
  E1+E2 and 6.2–6.4, the day-against-night log ratio in 14-day windows around 1 June, 1 July and 1 August, and around
  placebo dates (the 15th) of 2022–2025. Its rows are in `outputs/tables/calendar_national_estimate.csv`, and its
  by-year values are in that spec's E8 row. The July-to-August contrast in those windows overlaps with this design's
  summer statistic, which rests mostly on August against the other months. So the summer part is **partly seen**,
  as boundary windows, not as this statistic.
- `tou_extended_months.csv` holds the industry series' monthly evening-against-night values, 2021-06 → 2023-12.
- The protection is only the registered rules, fixed before this statistic is computed on any post-reform year.

## The statistic (both parts)
**Working days** are days that are not a weekend, a national holiday or 6 January. **Hour share**
s = 100 × load / mean over the day's 24 hours; days without 24 hours are dropped. The per-year regression is raw: no
base year is subtracted. The reform is read as b_post minus what normal years predict.
- **Medium firms (E1+E2).** Hour effects: s_Y(c) = α_Y(h) + b_Y · d(c), OLS, unweighted. d is from
  `tou_tariff_schedule.schedule()`, tariff 6.1, averaged over the cell's working days. This is the registered
  medium-firm statistic.
- **Large industry (pooled 6.2 + 6.3 + 6.4).** One intercept: s_Y(c) = a_Y + b_Y · d(c), OLS, unweighted, over cells
  (series, part of the year, hour). This is the registered E6 form. d is identical for 6.2, 6.3 and 6.4, because their
  old and new calendars are the same.
  - E6 judged its placebo values centred leave-one-out (mean 0, sd 1.2 × the raw sd). **Here raw b_Y, with their mean
    m and sd s, are used throughout.** The E6-form p is reported beside them.
  - The version with series × hour effects is reported beside it, against both the mean and the trend null (its
    placebo values drift).

## Inference
- S = the number of placebo years. m and s = the mean and sd of the placebo b_Y. b̄ = the mean of the K post-reform
  b_Y (K = 4).
- **Pooled mean null:** t = (b̄ − m) / (s · √(1/K + 1/S)), Student's t with S − 1 degrees of freedom, one-sided. This
  treats the K post years as independent.
- **Conservative version** (the K post years as one draw, because they share regime shocks): se = s · √(1 + 1/S).
- **Pooled trend null:** a straight line in year through the placebo b_Y, predicted at the mean of the post years.
  se = s_e · √(1/K + 1/S + (ȳ_post − ȳ_pl)² / Σ(year − ȳ_pl)²), with S − 2 degrees of freedom, one-sided.
- **Per year:** each post b_Y against the placebo years, t = (b_Y − m) / (s · √(1 + 1/S)).
- **MDEs** (printed at step zero): mean null (t_{S−1,0.95} + t_{S−1,0.80}) · s · √(1/K + 1/S); conservative, with
  √(1 + 1/S); trend null (t_{S−2,0.90} + t_{S−2,0.80}) · se.
- **Pooled 95% interval:** (b̄ − m) ± t_{S−1,0.975} · s · √(1/K + 1/S).

## Part A (primary): summers, 1 June → 30 September
- **Cells.**
  - Medium firms: (1–15 June, 16–30 June, July, August, September) × hour = 120 cells, d from the 2021 calendar.
  - Large industry: (series, month June–September, hour) = 288 cells, d from the 2021 calendar.
- **Placebo summers:** medium firms 2014, 2017, 2018, 2019 (S = 4); large industry 2014–2019 (S = 6). **Post
  summers:** 2022, 2023, 2024, 2025. Summer 2021 is reported beside them, not ruled.
- **Solar-robust cells.** Rooftop self-consumption lowers measured daytime load. It biases the August cells towards
  the prediction (daytime d = +2/+3) and other cells either way. Its hours are 10–17h. The solar-robust statistic
  drops hours 10–17 from every cell set. That keeps 8–9h and 18–23h, where August still has d = +2/+3 and July
  +1 at 19–21h.

## Part B (beside A): all months, calendar years
**Calendar years**, January–December, all twelve months:
- Placebo years: medium firms 2014, 2017, 2018, 2019 (S = 4); large industry 2014–2019 (S = 6).
- Treated years: 2022–2025.
- No calendar year used contains COVID months or 2021.
- Days dropped everywhere: Holy Thursday, Good Friday and Easter Monday (the dates move between March and April),
  1 January.

**Cells:**
- Medium firms: (month, with June split at the 16th) × hour = 312 cells.
- Large industry: (series, month, hour) = 864 cells.
- d is taken from the 2022 calendar (working days).
- The old day types are A (December–February), A1 (16 June to July), B (1–15 June and September), B1 (March and
  November), C (April, May, October) and D (August, weekends and holidays), against the new seasons.

**What Part B adds:**
- March has d = +1/+2 at 8–15h and 18–23h.
- April and May have +1 at 9–13h and 18–21h.
- December to February have d = +1 only at 9h, 13h and 21h.

It also brings in winters and springs of 2022–2025. **2022–2023 fall under the Iberian gas cap (15 June 2022 → 31
December 2023, RDL 10/2022).**

## Step zero (one sealed script; placebo years only; run after the commit)
`firm_persistence_step0.py` keeps E1+E2 rows only up to 2019-12-31 and 6.2–6.4 rows only up to 2019-12-31, cut right
after loading. The cut is asserted on the filtered frame, so no 2020 or later row is read.
- **Z0 Data.**
  - Every placebo year has at least 99% of its hours in every month used.
  - **Volume (E1+E2 only, the series with a known break at source):** each month's energy lies within ±15% of its
    2017–19 mean for that month (the 2014 gate of the medium-firm design, extended to all months). The 6.x series
    have real structural steps (6.2 in October 2018), so no volume gate is applied to them; their series-alone
    results are reported instead.
  - Post-year coverage (2022–2025) is checked by row count only, not by energy or share.
  - *Fails:* the failing year leaves that part's placebo set, and this is recorded.
- **Z1 Reproduction (gate).**
  - Medium-firm summer b_Y must equal 0.2277, 0.2929, 0.1773, 0.2334 (within 1e-4).
  - Large industry: the leave-one-out transform of the raw summer b_Y (×1/100) must equal the placebo slopes that
    `tou_industry_regulated_price.py` computes for 2014–2019 (its E6 `slope()`, recomputed on placebo years only),
    within 1e-6. Its recorded range was −0.11 to +0.08 points.
  - *Fails:* stop and fix before anything else. **If it cannot be fixed, Part A is not run.**
- **Z2 Part B decision (gate, recorded before Part A is opened).** For each group, Part B goes ahead only if
  **s_B ≤ 0.8 · s_A**. These are the raw placebo sds of the main statistic, in points per period step, over the same
  placebo years, with no rescaling. A ratio of two sds from four or six draws is itself noisy, so this is a coarse
  screen.
- **Printed:**
  - all placebo b_Y, m, s and the trend slope, for every statistic used in the rules (main, solar-robust, no-August,
    wrong hours, hour-effects version);
  - all MDEs;
  - the large-industry dose per step d̄: the slope of Δ ln p(c) on d(c) over the summer cells, one intercept,
    unweighted. The full dose is energy plus the power term, at 2021 values and E = €100.81.
- **Then stop and report.** The post years are opened by `firm_persistence.py`, committed before its single run,
  only after the user's yes.

## Rules (per group; the same for Part A and, if Z2 lets it go ahead, Part B)
- **R1 Pooled detection (primary).** b̄ − m < 0, pooled mean-null one-sided p ≤ 0.05.
- **R2 Robust to shared shocks.** The conservative version (one-draw se) has one-sided p ≤ 0.10.
- **R3 Solar-robust hours.** On the solar-robust cells, b̄ − m < 0 with pooled mean-null p ≤ 0.10, against that
  statistic's own placebo values.
- **R4 Wrong hours (one-sided).** Hours 0–7 have d = 0 under both calendars. The fake step is the mean d over hours
  8–23 of the same cell's month (or part), laid on hours 1–4, with hour effects, over the 1–4h cells. **Fails only
  if** its b̄ − m is below the lower bound of its own pooled 95% interval.
- **R5 Price shape.**
  - Add the cell's mean price share (hourly Spanish day-ahead price over the daily mean) to every year's
    regression. The price comes from REN, series ES; days from 2014 to 2017 are rebuilt from the doubled 30-minute
    grid, as in `mf_period_calendar_estimate.price_share`.
  - b̄ − m keeps its sign and stays inside the pooled 95% interval.
  - Limitation: in 2022–2023 the day-ahead price excludes the gas-cap adjustment cost, which consumers paid on top
    and which varied by hour. So the price shape is understated in those years.
- **R6 Not August alone.** Without the August cells, b̄ − m < 0, with pooled mean-null p ≤ 0.10 **and** a negative
  trend-null effect. Both nulls are needed because the no-August placebo values drift.
- **R7 Not one year.** Dropping each post year in turn (K = 3, with √(1/3 + 1/S)), R1's p ≤ 0.10.
- **R8 Trend null.** b̄ minus the trend prediction < 0, one-sided p ≤ 0.10. For medium firms (S = 4, 2 degrees of
  freedom, extrapolating 6.5 years past the placebo centre) this has little power. That is stated now; its MDE is
  printed at step zero.
- **R9 Every year.** Each post b_Y − m < 0.
- **Reported, no rule:**
  1. each year's effect, and 2021;
  2. each series alone (6.2 steps up about 25% from October 2018: a composition break between the 2018 and 2019
     placebo years);
  3. the hour-effects version for large industry and the intercept-only version for medium firms, against both
     nulls;
  4. the E6-form p;
  5. elasticity equivalents (medium d̄ 0.105; large industry from Z2's d̄);
  6. for Part B, the summer and non-summer cells separately. Part B assumes the per-step effect is the same across
     seasons.

## What each outcome means
The verdict is the line of the highest-ranked failing rule, in the order **R1 > R5 > R4 > R3 > R6 > R2 > R7 > R8 > R9**.
All other failures are listed beside it. Part A is the primary result; Part B is reported beside it, whatever Part A
shows.
- **All pass:** the shift is a lasting response to the period calendar, in four more years. For medium firms it is
  reported beside the 2021 verdict, which stays as recorded.
- **R1 fails:** no lasting shift detected; the pooled interval is the bound.
- **Significantly positive** (one-sided p ≤ 0.05 the other way): sign failure, no estimate.
- **R5 fails:** it follows the wholesale price shape, not the calendar.
- **R4 fails:** it shows up in hours the tariff did not move; not a calendar response.
- **R3 fails:** it may be solar self-consumption; not reported as a calendar response.
- **R6 fails:** it rests on August; reported as an August shift.
- **R2 fails:** detected only if the post years are independent; reported with that caveat.
- **R7 fails:** it rests on one year; reported with that year named.
- **R8 fails:** it rests on the mean null, as in 2021; reported as such (for medium firms, likely on power alone).
- **R9 fails alone:** a lasting shift on average, not in every year; the years are listed.
- **Z0** drops years. **Z1 unfixable:** Part A not run. **Z2 fails** for a group: Part B is not run for that group,
  and this is recorded before Part A is opened.
- **A and B disagree:** Part A's verdict stands, and Part B is reported as the all-months reading with its own
  verdict.

Failed rules are recorded and kept. No other year set, month set, cells, control, dose or step coding is tried after
a failure. Part B is not a fallback for Part A.

## Threats
- **2022–2023 gas cap and crisis prices.** Covered by R5 (with the limitation above) and R7.
- **Solar growth 2023–2025.** Covered by R3. The hour-effects version absorbs solar effects common to all months.
- **Composition:** closures, new loads, and the 6.2 step in October 2018. Series-alone results are reported.
- **Not blind:** see above.
- **Shared post-reform shocks:** covered by R2.
- **Old-calendar holidays and Holy Week:** dropped. Part B's d is from the 2022 calendar.

## Code and outputs
`scripts/analysis/firm_persistence_step0.py` (Z0–Z2, sealed), then `scripts/analysis/firm_persistence.py` (R1–R9 for
Part A and, where Z2 lets it go ahead, Part B). Each is committed before its single run. Outputs:
`outputs/tables/firm_persistence_step0{,_years}.csv` and `firm_persistence{,_summary}.csv`. Deterministic.

## Changes made before registration (review of 2026-11-23)
- The non-blind boundary windows of 2022–2025 are declared.
- Step zero is split into a sealed script, with the Part B decision made before Part A is opened.
- Part B uses calendar years for both groups. This keeps March–May and avoids COVID and 2021.
- A conservative variant is added (R2), and a solar-robust rule (R3) and a wrong-hours rule (R4).
- R6 requires both nulls.
- A large-industry reproduction gate is added (Z1), and a volume gate (Z0).
- The gas-cap price limitation is stated.
- A severity order is set, and the outcome lines are completed.
- The rules are renamed R1–R9.
- The 6.2 break is noted.
