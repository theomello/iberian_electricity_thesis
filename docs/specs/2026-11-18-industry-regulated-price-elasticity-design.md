# Industrial elasticity to the regulated price of each period (proposal)

**Status: proposed 2026-11-18, not registered. Binding when the user confirms and this file is committed. The power-term
tables are read only after that commit (they are price data, but they set the dose).** Follows
`notes/scope-period-change-design.md` and `notes/scope-2021-high-voltage-shift.md`: in July and August 2021 the large
plants moved load out of exactly the hours that the new 6.x calendar made dearer periods. The toll-only dose of the
earlier designs (`2026-11-12`, `2026-11-16`, `2026-11-18-industry-six-summer`) measured that price change as tiny for
6.3–6.4. Those verdicts stand; this is a new test with a new dose.

**What is not blind.** The hour-by-month pattern of July–August 2021 has been seen (descriptively, in load shares).
What has not been computed: any estimate with the new dose, its placebo distribution, or the power-term values.

## In one example
A 6.4TD plant in July. Old calendar: 19–22h was period 2; new: period 1. Its energy toll for those hours rises by about
€1/MWh, a 1% change on a €100 energy price: the old dose. But its power term also follows the period. A kW drawn at
20h now counts towards period 1's contracted power, priced at (say) €15/kW-year instead of period 2's €8. Spread over the
roughly 600 working hours of period 1 a year, that is about €12/MWh: a 10% change, not 1%. (Placeholder figures,
to be replaced by the BOE values.) The elasticity is the load response divided by the change in this regulated price.

## Estimand
The elasticity of hourly load with respect to the **regulated per-period price**: wholesale price level E (post-window
mean, as before) plus the energy toll and charge of the period, plus the **power term converted to €/MWh**. It is a
reform elasticity, like the paper's household number: the response to what the regulator set, not a structural price
slope.

## Dose
For tariff k, date t and hour h, with old period o = `old_period_6` and new period n = `new_period_6`:
Δp(k,t,h) = ln[(E + T_new(k,n) + W_new(k,n)) / (E + T_old(k,o) + W_old(k,o))],
where T is the energy toll plus charge (€/MWh, as in the earlier designs) and **W(k,p) = π(k,p) / H(k,p)**: π the
power-term price of period p (€/kW-year, toll plus charge, old and new) and H the number of hours a year in period p
under that calendar (counted from the calendar functions, a non-leap year, national holidays as in the schedule
module). W spreads the period's capacity price over its hours, the standard equivalent-energy conversion. It is an
assumption: the marginal value of a kW in an hour is π only if that hour sets the period's maximum. Stated as a limit.
- Old power prices: the 6.x access-tariff power terms in force on 31 May 2021 (the latest order that set them; to be
  identified and read from the BOE). New: CNMC resolution of 18 March 2021 (tolls, Annex I 1.a) plus the charges order
  for 2021 (power-term charges).
- IND and E1+E2 doses are load-weighted mixes as before (fixed loader, absent E5 = 0).

## Statistic, sample and inference (as the six-summer test)
`Fit.eta` (η_am), Spanish series minus Portugal (REN), leave-one-year-out LASSO errors (`six_summer_errors.parquet`,
already fitted; the outcome side does not change), aligned summer windows, post window 2021-06-01 → 09-15.
- **Series:** 6.2, 6.3, 6.4 (placebo summers 2014–19, S = 6) and E1+E2 (2017–19, S = 3). E0 is not a target
  (households and 3.0TD mixed).
- **Primary: pooled elasticity** over 6.2, 6.3, 6.4: one η, the stack of the three series with series-specific fixed
  effects (the Equation 4 fixed effects interacted with series), one dose per series. Inference by summer: the same
  pooled statistic on each placebo summer (S = 6), prediction t-test with S − 1 degrees of freedom, and rank.
- Series-specific η reported beside it.
- **Reduced form without prices (check):** hour share of daily load, working days, 2021 minus the mean of the placebo
  years, regressed on the change of period rank (new − old) over the cells of June–September; same placebo years.

## Rules, set before the power-term tables are read
- **Z1 Tables (gate).** Old and new power-term prices for 6.2–6.4 read from the BOE, entered twice independently
  (two passes of the text), and the two entries equal. The new values are checked against one independent CNMC or
  BOE summary table.
- **Z2 Readable dose (gate).** Within-day standard deviation of Δp over the post window ≥ 0.02 for each of 6.2, 6.3,
  6.4 (the earlier readability rule; 6.4 failed it with the toll-only dose, 0.014). A series failing it leaves the pool.
- **E1 Detection.** Pooled η < 0, prediction t-test one-sided p ≤ 0.05.
- **E2 Rank.** 2021 more negative than every placebo summer (p_rank = 1/7).
- **E3 Null centred.** |mean placebo| ≤ |η| / 3.
- **E4 Not one summer.** Leaving out each placebo summer, p ≤ 0.10.
- **E5 Proportionality.** Each series' η lies inside the pooled 95% interval (the new dose should make the responses
  scale; the toll-only dose did not).
- **E6 Reduced form agrees.** The rank-change regression has a negative slope with prediction t-test p ≤ 0.05 against
  its placebo years.
- **Description, no rule:** η with the energy-only dose (the old one) and with the power-only dose; E1+E2 with S = 3;
  the contract bound (below).
- **Direct-consumer check (description, no rule; added at the user's request before registration).** Direct market
  consumers buy in the day-ahead market, so their energy price is the hourly wholesale price: no retailer contract
  priced by period. For them the period calendar moves only the regulated toll and power term, the estimand. Outcome:
  the hour share of daily cleared purchases (`total_buy_mw`, `outputs/tables/direct_consumer_panel/`), own and
  represented consumers only (`kind` in own, represented; balance and auxiliary units out), units present in every
  compared summer, working days, 2021 minus the mean of 2018 and 2019 by month and hour, against the change of period
  rank of each cell (by the unit's tariff where known, else 6.1TD). Reported: the slope and the July and August hour
  profiles beside the tariff series. Limits stated: purchases are a schedule, not metering; two placebo summers.
A failed rule is recorded and kept; no other conversion of the power term, window, series set or control is tried
after it.

## Contracts: the stated threat and its bound
Supply contracts priced by period (about a third of industrial energy fixed by period, a third mixed: CNMC
IS/DE/031/24) may also have moved with the calendar. A fixed-by-period price is roughly the expected wholesale average
over the period's hours, so the calendar moves it by the wholesale difference between the hours that changed period
(summer evening over night about +8%). Bound, reported: the dose recomputed with the per-period wholesale averages added
for the fixed and mixed share (0.5 weight), giving a smaller elasticity in absolute value.

## What each outcome means
- Z1 or Z2 fails: stop or shrink the pool; recorded.
- E1–E6 pass: an industrial elasticity to the regulated per-period price, with its interval, reported beside the
  household one, with the contract bound.
- E1–E4 pass, E5 fails: the response is real but the power-term conversion does not make it proportional across
  tariffs; reported as pooled with that caveat.
- E1 or E2 fails: no detected elasticity; the interval is the bound.

## Code and outputs
`scripts/analysis/tou_industry_regulated_price.py` reusing `tou_industry_six_summer` (build, errors, aligned windows) and
`tou_cross_tariff`; power-term table `outputs/tables/tou_power_term_6x.csv` (old and new, € per kW-year, source BOE ids);
outputs `outputs/tables/tou_industry_regulated_price{,_summary}.csv`. Deterministic.
