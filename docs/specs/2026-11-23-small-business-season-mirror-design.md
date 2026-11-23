# Small-business (3.0TD) response to the 2021 reform, read from the season mirror inside E0 (proposal)

**Status: registered 2026-11-23 (user: "Register both"); binding from this commit.** Step zero
(placebo years and price tables only) runs after the commit. The estimation rules below are registered now, **before
any noise is seen**, and run only if step zero passes and the user says yes. Options and the user's choice (route A,
2026-11-23): `notes/business-demand-options.md`. Revised before registration after a three-lens review (identification,
facts, registration discipline); the changes are listed at the end.

Terms. **E0**: measured electricity demand below 1 kV, peninsula (ESIOS indicator 1201); about 69% tariff 2.0TD
(≤ 15 kW, mostly households) and 31% tariff 3.0TD (> 15 kW, small business) by energy. **ESIOS**: the data portal of
REE (Red Eléctrica, the Spanish grid operator). **CNMC**: the Spanish energy and competition regulator. **PVPC**: the
regulated household price, which follows the hourly wholesale price. **MDE**: minimum detectable effect.
**2.0DHA**: the old two-period household tariff.

## In one example
Before June 2021, a shop on tariff 3.0A paid its dearest price (P1) at **11–15h in summer-time months** and at
**18–22h in winter-time months**, every day of the week, weekends included. From 1 June 2021, tariff 3.0TD makes
weekends entirely the cheapest period (P6). So on a Sunday in July, the shop's 12h hour fell from the dearest period to
the cheapest (two steps down), while its 19h hour fell from the middle period (one step). On a Sunday in January it is
the other way round: 19h fell two steps, 12h one step.

If small businesses respond, the change in E0 against normal years should show a **mirror**: on weekends and holidays,
the summer midday rises relative to the winter midday, and the winter evening rises relative to the summer evening.
Most households cannot produce this. On the flat old tariff (2.0A, the large majority) and on the new 2.0TD, the
weekend price is flat before and after, in every season. The exception is the minority on old 2.0DHA (the
two-period household tariff), whose peak hours applied on weekends too. Their summer/winter difference falls only on
hour 12 (peak 12–22h in winter, 13–23h in summer), which rule E9 removes.

## What is identified, and why weekends
The design compares the reform's effect between two seasons, within each hour. It is not a boundary design: it has
no event at a date, and March and October, where the old seasons switch with the clock change, are left out
entirely. It shares the old 3.0A summer/winter calendar with route D of the options note (excluded as part of the
closed calendar family). The source of variation differs, though. Route D used before-and-after steps at clock-change
dates. This design uses the 2021 reform interacted with the old season, measured over whole months.

**The non-working-day leg is the confirmatory test**, for three reasons:
1. **Almost no household dose.** 2.0A and 2.0TD households face one flat price on weekends before and after (2.0DHA:
   hour 12 only, see E9).
2. **No direct charge-cut effect.** Royal Decree-law (RDL) 17/2021 cut the charges from 16 September to 31 December
   2021, which narrowed the households' weekday evening-versus-night price gap. It did not change any weekend price.
   A spillover through load moved from weekdays to weekends would differ by season, and that is not tested.
3. **Half unseen.** The winter half (January–February 2022, non-working days) and the season contrast have not been
   computed. The summer half is partly known (next section).

The working-day leg has a household dose, and the household dose differs between summer 2021 and winter 2021–22
(the charge cut). Its evening half is also already known (next section). **Working-day midday is a secondary rule.**
The known household confounds push it against the prediction (see Threats), so a detection there is conservative.
**Working-day evening is description only.**

## What is not blind
- E0's summer-2021 evening-versus-night shift is known: E0 about −5.7%, regulated (PVPC) households −3.9% by triple
  difference; elasticity −0.11 over six summers.
- `outputs/tables/tou_extended_months.csv` (`scripts/analysis/tou_extended.py`) has E0's monthly evening (18–21h)
  versus night triple difference, working days against weekends, against Portugal, for 2021-06 → 2023-12. It shows
  −4% to −7% in June–August 2021, −2.2% to 0.0% in October–December 2021 and −0.9% to −2.5% in January–March 2022.
  The working-day evening half of the mirror is therefore known, and it points the predicted way. This is why
  working-day evening is description only. That series mixes weekend and working-day evenings, so it carries some
  information on the weekend evening too. Its sign for the weekend leg alone is not known.
- `outputs/tables/tou_events.csv` holds E0 windows from October 2021 to June 2022 (peak/mid/off by 2.0TD period).
- **The summer-2021 weekend half is partly known.** `docs/specs/2026-11-11-tou-hardening-design.md` (block split
  table) gives E0's summer-2021 change against night, Portugal control, on weekends: **10–13h −5.24, 18–21h −3.48**
  (working days −5.67 and −8.42). `tou_ddd_path.csv` has the monthly weekend arm: +6.2, +6.8, +4.8, +1.6 in
  February–May 2021, then −2.1, −3.6, −8.8, −1.9 in June–September. The morning fall was the same on working days and
  weekends, and was read there as a daylight effect: rooftop self-consumption lowering measured midday load. **For
  this design that is a known headwind.** Summer weekend midday is predicted to rise, and it fell against night,
  probably from solar self-consumption. Unless the winter weekend midday fell by more, the midday block (E5) will
  fail. This is stated before registration.
- Nothing has been computed on E0 for January–February 2022 by hour block, or for working-day midday by season. No
  statistic of this design has been computed on any year.

## Data
- **E0**: ESIOS 1201, hourly, 2014-01-01 → 2026-04-30, on disk; loaded with `tou_cross_tariff.esios_load([1201])`. Hours
  are labelled by their start, in local Madrid clock time. The date filter is applied to the returned frame at once.
- **Mix weights**: ESIOS 1209 (2.0TD) and 2532 (3.0TD), filtered to 2024-06-01 → 2026-04-30 local. 1209 also holds a
  stray row on 2019-06-01, which the filter removes. 3.0TDVE (2531, about 0.16 TWh over 23 months) is ignored.
- **Holidays**: `data/holidays/holidays_es_pt.parquet` (national, 2014 →), plus 6 January, as in `tou_tariff_schedule`.
- **Periods**: old 3.0A from `tou_tariff_schedule.old_period_3` (summer or winter clock time by date, every day); new
  3.0TD from `new_period_6`. **D is computed from the rank mapping below, not from `schedule()`'s period numbers.**
- **Prices (for the elasticity scale only)**: `outputs/tables/tou_tariff_prices_2021.csv` (3.0TD energy toll plus
  charge). Old 3.0A energy toll from `tou_tariff_schedule.OLD`. Old 3.0A and new 3.0TD power terms are read in Z1.
  For the price-shape check: the Spanish day-ahead hourly price from REN (the Portuguese grid operator),
  `data/ren/ren_market_prices.parquet`, series ES, from 2014-01-01, joined through UTC. The OMIE file (OMIE is the
  Iberian power exchange) starts only in 2018.
- **Solar check**: ESIOS 1161 (measured solar photovoltaic generation, hourly). To fetch: 2014-01-01 → 2022-02-28. Its
  hourly profile stands in for the shape of rooftop self-consumption.
- **Households, description only**: the GoiEner 2.0TD panel (cooperative members' smart meters, streamed from
  `data/goiener/raw/imp-*.tzst` with `zstd -dc` as in `build_goiener_daily.py`). The panel is balanced over
  2017-06-01 → 2022-05-31, with at most 5% missing hours and residential activity codes (CNAE) only.
- Scripts run from the main checkout (`data/` and `outputs/` live there).

## Years and months
A "year" Y runs from 1 June of Y to the end of February of Y+1. **Months used in every year: June, July, August,
September (summer time) and January, February (winter time).** Dropped in every run:
- March and October, where the old season switches mid-month.
- November and December. In the treated year the RDL 17/2021 cut was deepest there: the households' weekday
  evening-versus-night charge gap was 0.14, against 0.46 in summer 2021 and 0.36–0.38 in early 2022. This matters
  for the working-day legs. 16–30 September 2021 is also under the cut and is kept.
- March to May, because placebo year 2019 ends at the COVID cut.

The cell set is the same in every year and in every rule.
- **Treated year: R = 2021** (June–September 2021, January–February 2022).
- **Placebo years: 2014, 2015, 2016, 2017, 2018, 2019** (2019: June–September 2019, January–February 2020). S = 6.
  These are all the clean pre-reform years E0 has, so six independent years is the most this data allows.
  Many-window randomization inference is not possible here, because shifted windows of one year overlap and are
  not independent.
- Not used: 2020 (COVID). Later years 2022–2024 are description only.
- Day dropped everywhere: 1 January. No clock-change or Christmas day falls in the months used.

## The statistic
1. **Hour share.** s(d,h) = 100 × E0(d,h) / mean over the 24 hours of E0(d,·).
2. **Cells.** c = (calendar month m, day type τ ∈ {working, non-working = weekend or national holiday}, hour h). Season
   σ follows from the month. A cell's value in year Y, s_Y(c), is the mean of s over Y's days in c.
3. **Rank step D(c) = old rank − new rank** (positive = dearer). Rank within the day: dearest period 1, middle 2,
   cheapest 3. Old 3.0A: P1 = 1, P2 = 2, P3 = 3, every day. New 3.0TD on working days: hours 9–13 and 18–21 = 1;
   8, 14–17, 22–23 = 2; 0–7 = 3. On non-working days all hours = 3. Resulting D (hour-beginning, summer / winter):
   - **working days:** hours 9–10 +1/+1; **11–13 0/+1**; **14 −1/0**; 15–17 0/0; **18–21 +1/0**; 8, 22, 23 0/0;
     0–7 0/0;
   - **non-working days:** hours 8–10, 15–17, 22–23 −1/−1; **11–14 −2/−1**; **18–21 −1/−2**; 0–7 0/0.
   Only the bold hours vary between seasons; all other hours are absorbed by the fixed effects. The code asserts that
   D reproduces this table.
4. **Per-year regression, raw (no base year subtracted).** For each year Y separately, on one day type:
   s_Y(c) = α_Y(h) + b_Y · D(c) + error, weighted by the number of days in the cell. α_Y(h) absorbs everything that is
   the same in summer and winter within an hour. b_Y measures how strongly E0's hour shares follow the 3.0 rank
   steps between seasons. Normal years have their own b_Y (the normal seasonal profile); the reform is read as
   **b_R minus what normal years predict**.
   - **Main statistic b^nw:** non-working days, hours 11–14 and 18–21 identifying.
   - **Secondary b^wm:** working days, hours 0–17 and 22–23 only (hours 18–21 removed), so 11–14 identify.
   - **Description b^we:** working days, all hours (adds the known evening block).
5. **Scaling to 3.0 (for the gate and for reporting, not for the rules).** w(m,τ) = 2532 / (1209 + 2532) of daily
   energy, mean over 2024-06 → 2026-04, by month and day type (non-working days 0.24–0.30, working days 0.29–0.35).
   A 3.0 shift of x points of its own daily mean moves E0's share by about x·w. **β3 = (b_R − null) / w̄**, with w̄ the
   day-weighted mean of w over the leg's cells.
6. **Elasticity scale (for the gate).** b is identified only from the summer–winter difference within an hour, so
   the dose per step is d̄ = the day-weighted mean over the identifying hours h of
   |Δ ln p3(summer, h) − Δ ln p3(winter, h)| / |D(summer, h) − D(winter, h)|. On non-working days this is
   |ln p_old(P1) − ln p_old(P2)|, because the new price is P6 in both seasons.
   p3 is the regulated 3.0 price of the hour: energy toll plus charge, plus the power term spread over its period's
   hours (W = π / H, as in the industry spec), old 3.0A against new 3.0TD, 2021 values, energy price E = €100.81.
   s̄_B = 3.0's own mean hour share (points, ESIOS 2532, 2024-06 → 2026-04) in the identifying cells. The elasticity
   equivalent of x points per step is **(x / s̄_B) / d̄**.

## Inference (the same for every statistic)
m and s are the mean and standard deviation of the six placebo b_Y.
- **Mean null:** t = (b_R − m) / (s·√(1 + 1/6)), one-sided p from Student's t with 5 degrees of freedom.
- **Trend null:** a straight line in year through the six placebo b_Y, predicted at 2021: ŷ, se_pred =
  s_e·√(1 + 1/6 + (2021 − ȳear)² / Σ(year − ȳear)²), with 4 degrees of freedom (Amendment A2 of
  `docs/specs/2026-11-18-industry-regulated-price-elasticity-design.md`).
- **Main 95% interval:** (b_R − m) ± t₅,₀.₉₇₅ · s · √(7/6). Sub-statistics (blocks, controls, wrong hours, leave-outs)
  recompute m and s from their own placebo values; E4 uses S = 5, t₄ and √(6/5).
- **Rank:** p_rank = (1 + #{placebo b_Y ≤ b_R}) / 7.
- **MDE** in E0 points = (t₅,₀.₉₅ + t₅,₀.₈₀) · s · √(1 + 1/6) = 2.94 · s · √(7/6). The normal-quantile version (2.49)
  is reported beside it.

## Step zero (placebo years and prices only; run after the commit)
- **S0 Data (gate).** E0 has at least 99% of the hours of the used months in every placebo year; 1209 and 2532 have at
  least 95% of the hours of 2024-06 → 2026-04. *Fails:* stop.
- **S1 Seal.** The step-zero script keeps E0 rows only up to 2020-02-29; this is asserted on the filtered frame. It reads
  no other E0 date, no GoiEner post file and no PVPC schedule. 1209 and 2532 are used only for w and s̄_B.
- **Z1 Price tables (gate for the elasticity scale).** The old 3.0A power-term prices (P1–P3, €/kW-year) and the new
  3.0TD power-term tolls and charges (P1–P6) are read from the Spanish official gazette (BOE) twice, from the XML and
  from the PDF, and both readings must agree. *Fails:* d̄ uses the energy term only, which gives a smaller dose per
  step, so the gate becomes stricter. This fallback is fixed now.
- **S2 Noise (gate).** For b^nw: MDE, MDE3 = MDE / w̄ and the elasticity equivalent η_MDE = (MDE3 / s̄_B) / d̄.
  **Pass if η_MDE ≤ 0.15**, the bar of the options note and of the earlier business designs. The gate is on detection
  (E1) only. The trend-null MDE (t₄, se_pred ≈ 1.52 s_e) is reported beside it and is larger, so E3 can fail on power
  alone. This is stated now.
  Reported beside it, with no rule: the same for b^wm and b^we, the placebo b_Y by year, m, and the trend slope.
  *Fails:* the design is closed with η_MDE recorded, and the treated year is never computed.
- **S2 passes:** stop and ask the user before the estimation runs.

## Estimation rules (registered now; run only after S2 passes and the user says yes)
- **E1 Detection (primary).** b^nw_R − m < 0, mean-null one-sided p ≤ 0.05.
- **E2 Rank.** b^nw_R is below all six placebo values (p_rank = 1/7).
- **E3 Trend null.** b^nw_R − ŷ < 0, trend-null one-sided p ≤ 0.10. (This replaces a centring rule. A leave-one-out
  centring rule would be met mechanically, so the trend null is the guard against drift.)
- **E4 Not one year.** Leaving out each placebo year in turn (S = 5, the same cells), the mean-null p ≤ 0.10.
- **E5 Both blocks.** Re-estimated with the non-working identifying hours split into 11–14 only and 18–21 only (each
  with the other block's hours removed). Both effects (b_R − m) are negative. The two blocks are the two halves of
  the mirror. A confound that moves only one block, or moves summer and winter equally, cannot make both negative.
  Solar self-consumption works against the prediction in both blocks, because it lowers the summer midday share and
  so raises the summer evening share.
- **E6 Price-shape check.** PVPC households (about 23–30% of E0) pay the hourly wholesale price, whose shape within the
  day differs by season. Add to every year's regression the cell's mean price share (hourly Spanish day-ahead price
  over its daily mean, REN series, averaged over the cell). b^nw_R − m keeps its sign and stays inside the main 95%
  interval.
- **E7 Wrong block (one-sided).** D is replaced by the same season pattern placed on hours 0–3 of non-working days
  (summer −2, winter −1), a block the tariff did not move. **Fails only if** its b_R − m is below the lower 95% bound of
  its own placebo prediction interval, which would mean the mirror shows up where the tariff did not move.
- **E8 Working-day midday (secondary).** b^wm_R − m < 0 with mean-null one-sided p ≤ 0.10.
- **E9 Without hour 12.** With hour 12 removed (old 2.0DHA households' season step), b^nw_R − m keeps its sign and stays
  inside the main 95% interval.
- **Reported, no rule:**
  1. β3 and its interval under both nulls.
  2. The elasticity equivalent (with Z1's dose).
  3. b^we, working days with the evening.
  4. Solar control: the cell's mean solar share (ESIOS 1161 hourly over its daily mean) added to every year's
     regression.
  5. The log-share version (ln s in place of s).
  6. Weights rescaled to the CNMC monthly 3.0TD share of 2021–22 (keeping the 2024–26 day-type ratio).
  7. Later years 2022–2024 against the same null.
  8. GoiEner 2.0TD households: the same b^nw on placebo years 2017–2019 and 2021, read as a magnitude check only
     (three placebo years: too few for a test).

Failed rules are recorded and kept. No other months, cells, base, weights, treatment coding or control is tried
after a failure.

## What each outcome means (the most severe failure decides)
- **S0 fails:** stop. **S2 fails:** E0 is too diluted to show a small-business response; recorded. The remaining route
  is the request to REE for tariff-level history (route E).
- **E1–E7 and E9 pass:** small businesses moved weekend load with the reform's period calendar. Reported as β3 (points per
  step for 3.0, mean and trend null), with the elasticity equivalent, beside households and large industry. E8 is then
  reported as passing or failing, without changing that verdict.
- **E1 or E2 fails:** no detected response; β3's prediction interval is the bound.
- **E9 fails:** the result rests on hour 12 (2.0DHA households); not reported as a business response.
- **b_R − m positive and significant (one-sided p ≤ 0.05 in the wrong direction):** sign failure, no estimate.
- **E3 or E4 fails (alone or together), with E1 and E2 passing:** the result rests on a drifted null or on one year;
  reported as such, not as an estimate.
- **E5 fails:** only one half of the mirror moved; a seasonal confound is as likely as a response. Not reported as a
  response.
- **E6 fails:** the result depends on the hourly price shape (PVPC households); not reported as a business response.
- **E7 fails:** the mirror appears where the tariff did not move; not reported as a response.
- **GoiEner (description):** if the households show a mirror of similar size, the result is reported as not specific
  to business, even with all rules passing.

**Next to the closed Barcelona result** (services, month-scale steps of the new tariffs, −0.004 [−0.080, +0.071]):
that interval is about responses to the new tariff's month-to-month steps on weekdays. This design measures the
reform's change on weekends. A pass here would be a different margin, not a contradiction. A fail here would be
reported beside it as a second null.

## Threats
- **3.0TDVE** (the 3.0 tariff for electric-vehicle charging) is negligible. **Routes D and E** of the options note are
  the excluded clock-change boundary design and the data request to REE.
- **Dilution.** 3.0 is about 24–30% of E0 on non-working days. This is the reason for the step-zero gate.
- **Season-specific drifts.**
  - Rooftop self-consumption lowers measured summer midday load. It jumped in 2021–22, which the trend through
    2014–19 does not capture. It works against the prediction in both weekend blocks, and on the known summer-2021
    numbers (weekend 10–13h −5.2 against night) it is large next to the expected business effect (3.0's weight times
    a shift of 1–2 points). This is the most likely reason for a failure. Item 4 (the solar control) shows how much
    it matters.
  - Air conditioning raises summer evenings, which works against the predicted rise of the winter evening.
  - The trend null (E3) guards against drift; E5 guards against single-block confounds.
- **Hourly-price shape.** PVPC households facing a cheap summer midday and a dear winter evening would mimic the
  midday half and oppose the evening half. E5 and E6 cover this.
- **COVID (Omicron), January–February 2022.** Telework and restrictions on hospitality hours in some regions. Weekend
  hospitality restrictions in winter lower the winter weekend evening, against the prediction. On working days,
  household telework raises the winter midday, also against the prediction for E8. Both push toward no detection.
- **2.0DHA households.** Their old peak switched by an hour with the clock (12–22h winter, 13–23h summer), which
  affects hour 12 only. It works against the prediction on both legs; item 4 above reports the result without it.
- **The weights are from 2024–26.** The 2021–22 shares were close to these (CNMC: 25.6% to 35.6% by month), and the
  weights only scale β3 and the gate.
- **Ranks, not prices.** The rules use steps. The elasticity scale uses 2021 prices; the 2022 charges (January–February
  winter cells) are not read, so the elasticity equivalent is approximate and labelled so.
- **Intertemporal shifting from weekdays to weekends** raises weekend load at all hours roughly in proportion. It
  changes levels, not shares between hours, so it is mostly absorbed.

## Code and outputs
`scripts/analysis/sb_season_mirror_step0.py` (S0, S1, Z1, S2), with the power-term table in
`outputs/tables/tou_power_term_30.csv` and outputs in `outputs/tables/sb_season_mirror_step0{,_years}.csv`.
Estimation: `scripts/analysis/sb_season_mirror_estimate.py`, outputs in
`outputs/tables/sb_season_mirror_estimate{,_summary}.csv`. Deterministic; no random draws.

## Changes made before registration (review of 2026-11-23)
These were made after the review, and no statistic had been computed:
- Leave-one-out centring replaced by raw per-year statistics: a leave-one-out base made the centring rule pass
  mechanically and inflated s by 6/5.
- MDE multiplier set to the registered test (2.94).
- The confirmatory leg moved to non-working days, because of the household dose, the RDL 17/2021 charge cut, the
  already-known evening path, and the seasonal household mix.
- Months fixed to June–September and January–February.
- Wrong-block check made one-sided and moved to night hours.
- Price-shape check added.
- Seal made consistent (no E0 read after 2020-02-29 in step zero).
- The numeric industry benchmark dropped, because its "step" is a different quantity. The gate is in elasticity
  units, as the options note said.
- GoiEner made description only, because it has three placebo years.
- Second review: the known summer-2021 weekend blocks declared (a headwind for the midday block); the dose per step
  defined on the season difference; prices from REN (OMIE starts in 2018); the gate stated as detection-only;
  hour 12 made a rule (E9); a solar control added as description; the solar wording corrected.
