# Business tariffs' season boundaries: a repeated identification of σ (pre-registration, proposed)

**Status: proposed 2026-11-19, not registered. Binding when the user confirms and this file is committed. The
post-2021 toll and charge tables (gate Z1) are read only after that commit; the script is committed before its
run.** Origin: `notes/idea-calendar-boundary-business-tariffs.md`, `notes/open-doors-demand-review-2026-11-19.md` §B1.
Framework: `notes/thesis-demand-supply-link.md` §2 (σ in equation D).

**Identification is on the demand side only.** The shock is the regulator's calendar of periods (Order
ITC/2794/2007 before 1 June 2021; CNMC Circular 3/2020 art. 7 after), fixed years ahead. What moves on a boundary
date is the regulated toll, charge and power term of each hour. The wholesale price does not step on these dates; the
comparisons below hold it fixed. No bid or supply curve is used.

## In one example
A 6.4TD plant, 30 June 2023 against 3 July 2023. On 1 July the month turns from "medium" to "high" season: weekday
hours 9–14 and 18–22 move from period 3 to period 1, and their regulated price (toll + charge + power term) rises.
Nights and weekends stay period 6. If the plant responds, its weekday 20:00 share of daily load falls after 1 July,
relative to its own weekend 20:00 share. On 1 July 2019, under the old calendar, nothing changed (June 16–30 and
July were both type A1): the same date, same heat, same holidays, no price step. That year is the comparison. The
response per log-point of regulated price is σ.

## Events
Calendar dates that are a boundary under either calendar: **1 Mar, 1 Apr, 1 Jun, 16 Jun, 1 Jul, 1 Aug, 1 Sep, 1 Oct,
1 Nov, 1 Dec**, in every year 2014 → 2025, plus 1 Mar and 1 Apr 2026 (series end 2026-04-30). Old calendar
(`old_day_type`): boundaries on all of them except 1 Jul. New (`new_period_6`): all except 16 Jun and 1 Sep. A date that
is not a boundary in a year carries dose zero in that year, so every date has treated and untreated years.

Dropped before anything is computed: any event whose window touches **2021-06-01** (the reform itself, the source of
the six-summer σ; keeps the two estimates independent), the lockdown **2020-03-01 → 2020-06-30**, **2025-04-28**
(blackout day only), and any window containing a change of the toll or charge tables other than the boundary itself
(dates from Z1).

## Outcome, dose, statistic
- **Series:** 6.2, 6.3, 6.4 (ESIOS 1216–1218), pooled; E1+E2 secondary (from its first full year). E0 not used
  (households and 3.0TD mixed).
- **Window:** the 10 working days before and the 10 after the boundary; weekend and national-holiday days in the same
  calendar span. Holidays are period 6 under both calendars.
- **Outcome:** y = ln(L_h / day's mean hourly load). Δ_{k,e,h} = [after − before mean of y, working days] −
  [after − before mean of y, weekend/holiday days].
- **Dose:** d_{k,e,h} = after − before of ln r on working days, r = E_e + T(k, p) + W(k, p), p the period of hour h
  under the calendar in force, T the energy toll + charge, W the power term in €/MWh (π / hours of the period, as in
  `tou_industry_regulated_price.power_table`), E_e the mean day-ahead price over the event's 20 working days. Old
  values: `tou_tariff_schedule.OLD`, `PW_OLD`; new values for 2021-06-01 → 2021-09-15: on disk; later: Z1.
- **Estimator:** OLS of Δ on d with fixed effects for series × calendar date × hour (absorbs the usual change of
  daily shape at that date: heat, holidays, light) and series × event. η is identified only by the dose differing
  across years at the same date. **σ_season = η.**
- **Reduced form (no prices):** the same regression on the change of period number (new − old period index, working
  days), within a calendar regime's own price ordering. Reported, and used in R5.

## Inference
- **Primary, year permutation:** within each series × calendar date, permute the years' dose vectors (1,000 draws, seed
  20261117); p = rank of the real η; 95% interval by test inversion over a grid of η₀ (Fisher).
- **Second, fake dates:** the same statistic with every boundary moved to the 8th of its month (no boundary under either
  calendar), each event keeping its real dose vector; the real η against the fake-date η distribution
  (fake dates also shifted to the 22nd for a second draw).

## Rules (set before the run)
- **Z1 Tables (gate):** toll and charge tables (energy and power terms) for 6.2–6.4 for every change date
  2021-09-16 → 2026-04-30, read from the BOE/CNMC texts, entered twice and equal, one checked against an independent
  summary. Also: the old 6.x energy and power terms confirmed in force from 2014-02-01 to 2021-05-31 (Orden
  IET/107/2014 and any later order). A year whose tables fail leaves the sample; if 2022–2025 all fail, the run uses
  2014 → 2021-09-15 only and says so.
- **Z2 Power (gate, computed on fake dates before the real η):** sd of the fake-date η. Continue only if
  2.8 × sd ≤ **0.12** (an estimate at σ's point, −0.177, must be able to put its interval end below −0.095, the end that
  sets T1's λ bound). Fail: stop; σ_season is not reported as a result.
- **R1 Detection:** η < 0, year-permutation p ≤ 0.05 (one-sided).
- **R2 Fake dates:** real η more negative than 95% of fake-date η (both shifts).
- **R3 Both directions:** η estimated on dearer steps only (d > 0 cells) and on cheaper steps only (d < 0) is negative
  in both (load leaves dearer hours and enters cheaper ones).
- **R4 Not one year:** leaving out each year, p ≤ 0.10.
- **R5 Proportional across tariffs:** each series' η inside the pooled 95% interval (the six-summer σ failed this).

## What each outcome means
- **Z2, R1–R5 pass:** business demand responds to the regulated period price, identified on many dated steps in both
  directions; σ_season is reported beside σ_reform (−0.177 [−0.544, −0.095]). The thesis uses whichever interval is
  tighter for λ, stated as such, and T1's bound is recomputed with the same formula (λ_U = −ε_lo / (|σ|_lo θ s), no new
  rule).
- **R1 fails with Z2 passing:** a bounded null: the season steps move business load by less than the interval's end,
  which sits against σ_reform's size; the thesis states that the reform response of 6.x was not reproduced by the
  calendar's repeated steps.
- **R3 or R5 fails:** reported; σ_season is not used for λ.
- No other window, series set, fixed-effect structure or dose conversion is tried after a failure.

## Reported, no rule
- E1+E2; η by calendar regime (old years, new years); the reduced form; the energy-only and power-only doses; a
  contract variant (half the energy priced at the period-average wholesale price, as in the regulated-price design).

## Threats
- **Contracts:** a supply contract priced by period may smooth the season steps (or pass them through on top of the
  tolls); the estimand is the response to the regulated price, and the contract variant bounds it.
- **Seasonal shape at the boundary** is absorbed by date × hour effects only if it is the same in every year; a
  shape change correlated with the regime switch (post-2021 work patterns) is not. R2 and R4 are the guard.
- **Windows of 1 Jun and 16 Jun overlap** (and 16 Jun with 1 Jul); the date × hour effects are separate per date, the
  overlap is stated.
- Anticipated steps: firms may plan the month in advance; the estimate is the planned response, which is what σ is.
- W assumes the power term's marginal value spreads evenly over the period's hours (as before).

## Outputs
`scripts/analysis/tou_season_boundaries.py`; `outputs/tables/tou_season_boundaries{,_checks,_events}.csv`;
Z1 tables in `docs/tou-policy-sources.md` and a csv beside `tou_tariff_prices_2021.csv`.

## Z1 result (2026-11-19) and a conflict found before Z2

**Z1 passes.** Fourteen BOE texts read for 6.2–6.4 (energy and power; tolls from the CNMC resolutions BOE-A-2021-4565,
-2021-21208, -2022-21799, -2023-26251, -2024-26218, -2025-26348; charges from BOE-A-2021-6390, RDL 17/2021
BOE-A-2021-14974, BOE-A-2021-21794, RDL 6/2022 BOE-A-2022-4972, BOE-A-2022-23737, BOE-A-2024-2774,
BOE-A-2024-27289, BOE-A-2025-26705). Pass 1: XML parsed by code, with transport + distribution = combined checked on
every toll row (all equal). Pass 2: an independent read of the HTML pages (72 rows) and, for the two decree-laws, a
second parser on the HTML (12 rows): **84 of 84 rows equal**. Errata read: BOE-A-2021-21647 relabels the 2022 energy
tables (values unchanged); BOE-A-2024-27271 touches only a self-consumption table. Independent check: the parsed 2022
2.0TD toll plus charge gives €100.76 (Jan–30 Mar) and €74.41 (from 31 Mar) against ESIOS 1876's €100.8 and €74.4.
The 2023 charges ran on until 14 February 2024 (extension) and the 15 February 2024 order repeats them for segments
4–6. Old 6.x terms 2014-02 → 2021-05: as recorded in `docs/tou-policy-sources.md` (Orden ETU/1282/2017 statement
and the 2.0A check; the 2019–2020 orders were not read). Values: `outputs/tables/tou_tariff_tables_6x_2021_2026.csv`.

**Conflict, found after registration and before any outcome was computed.** The same idea was registered and run on
2026-11-16 (`docs/specs/2026-11-17-calendar-boundary-design.md`, Barcelona services on 3.0TD): η −0.004
[−0.080, +0.071], E1–E5 failed, and the design was closed with "no other window, sector aggregation or base year is
tried". This design uses different series (national 6.2–6.4), the old calendar's boundaries and a cross-year
comparison, but it tests the same idea after a closure. My review of 2026-11-19 missed the earlier design (the idea
note still says "idea only"). Z2 and everything after it are not run until the user decides whether this is a new
test or a closed door.
