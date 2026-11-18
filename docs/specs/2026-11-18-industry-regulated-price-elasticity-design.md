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

## Results (run 2026-11-18; `scripts/analysis/tou_industry_regulated_price.py`, committed in eba9f4e before the run; outputs `outputs/tables/tou_industry_regulated_price_summary.csv`, `tou_power_term_6x.csv`)

**Z1 pass.** All twelve power-term rows (old 6.1A–6.4 from BOE-A-2014-13475 and BOE-A-2014-1052; new tolls 6.1TD–6.4TD,
BOE-A-2021-4565 Annex I 1.a, transport + distribution; new charges segments 3–6, BOE-A-2021-6390 art. 2.a) read from
the XML tables and, independently, from the PDF text: identical to six decimals. Independent check: the new transport
and distribution tables sum exactly to the published T&D table. Equivalent €/MWh (6.4TD, old → new): P1 21.6 → 18.5,
P2 7.8 → 10.7, P3 11.6 → 6.2, P6 0.5 → 0.2. **Z2 pass:** within-day sd of the dose 6.2 0.055, 6.3 0.050, 6.4 0.036,
E1+E2 0.086 (energy-only: 0.026, 0.023, 0.014, 0.050).

| pooled 6.2+6.3+6.4 | η 2021 | placebo summers 2014 … 2019 | m (sd) | p_t | p_rank | 95% interval |
|---|---|---|---|---|---|---|
| **full dose (energy + power)** | **−0.177** | +0.232 +0.216 +0.183 +0.102 +0.024 +0.100 | +0.143 (0.081) | **0.007** | 0.143 | **[−0.544, −0.095]** |
| energy only (old dose) | −0.150 | +0.307 … +0.339 | +0.250 (0.082) | 0.003 | 0.143 | [−0.629, −0.172] |
| power only | −0.320 | +0.339 … +0.063 | +0.185 (0.143) | 0.011 | 0.143 | [−0.901, −0.109] |
| contract bound (half weight) | −0.165 | | +0.142 (0.072) | 0.006 | 0.143 | [−0.508, −0.106] |

Series alone (full dose): 6.2 −0.064, 6.3 −0.233, 6.4 −0.337; E1+E2 −0.084 (S = 3, p 0.077, interval [−0.20, +0.06]).
**Reduced form (E6):** hour share changes by **−1.00 point of the daily mean per one-step dearer period** in
June–September 2021; placebo years −0.11 to +0.08; p_t 0.0001.

**Rules.** E1 detection **pass** (p 0.007). E2 rank **pass** (below all six summers). **E3 null centred fails**
(placebo mean +0.143 > |η|/3 = 0.059). E4 leave-one-summer-out **pass** (all p ≤ 0.016). **E5 proportionality fails**
(6.2 −0.064 lies outside [−0.544, −0.095]; the series estimates still rise with voltage). E6 reduced form **pass**.

**Verdict, as registered.** The response to the reform's period calendar is detected, against every pre-reform summer,
in both the elasticity (E1, E2, E4) and the price-free reduced form (E6, the strongest result). But the elasticity's
size is not pinned down: its null is drifted (E3) and the series do not scale with the new dose (E5). Reported as a
detected industrial response to the regulated period price with an interval of **[−0.54, −0.10]** and these two caveats,
not as a single number. The spec named no outcome for an E3 failure; this reading follows the six-summer spec's wording
("rests on a drifted null; reported as such").

**Descriptive, not rules.**
- The drift has a direction: placebo values fall from +0.23 (2014) to +0.02–0.10 (2018–19). Large-plant load in the
  dose-heavy cells has been declining across years, so the "no reform" value for 2021 is somewhere between the trend's
  extrapolation (about −0.05) and the placebo mean (+0.14): the elasticity is roughly **−0.13 to −0.32**, centred near
  the raw −0.18. This bracket is post hoc and is not a test.
- Contracts barely matter: the contract bound moves the estimate from −0.177 to −0.165.
- Omitted price component: old capacity payments by period (e.g. 6.1A P1 €13.63/MWh) fell to about €1/MWh with
  Orden TED/371/2021. Not in the dose. It makes the new period 1 *cheaper* in energy than the old one, so leaving it out
  overstates the dose in P1 hours and makes the elasticity too small in absolute value, if anything.
- Direct consumers (59 units present in 2018, 2019 and 2021, 47% of own and represented volume; purchases, not
  metering): hour share on the rank change −0.0054 against ±0.0012 in the 2018/2019 placebo pair. July night hours
  +9 to +17 points, daytime −3 to −11; August night +5 to +7, day and evening −3 to −10. Buyers without period-priced
  contracts moved the same way, so the response is not a contract artefact. Their pattern is less hour-specific than
  6.4's (14–17h did not rise in July).

## Amendment A (2026-11-18, after the results above; approved by the user: "lets do it if its cheap and fast")
**Post hoc, stated as such.** Two changes that fix known problems, registered before either is computed. The
original verdict above stands; these are reported beside it.

**A1 Capacity payments in the dose.** Add the per-period capacity payment (pagos por capacidad, €/kWh, an energy-term
adder by period) to both regimes: new from Orden TED/371/2021 art. 2 last table (segments 3–6: 1.031 / 0.476 / 0.317 /
0.238 / 0.238 / 0 €/MWh, P1…P6); old for 6.2–6.4 from the BOE order that set them for those tariffs (to be found; the
6.1A/6.1B values are in Orden IET/2444/2014). **Gate A1-Z:** the old 6.2–6.4 values are found in a BOE text and read
twice (XML and PDF) with equal results; if they are not found, A1 is not run and that is recorded.
**A2 Trend-adjusted null.** The no-reform value for 2021 is predicted from a straight line in year through the six
placebo values (2014–2019), not their mean. Prediction t-test with S − 2 = 4 degrees of freedom: t = (η_2021 − ŷ_2021)
/ se_pred, se_pred = s_e·sqrt(1 + 1/S + (2021 − ȳear)² / Σ(year − ȳear)²), one-sided p; 95% prediction interval
likewise. Applied to the full dose and to the A1 dose.
**Reported, no new rule:** η, p and interval for (i) full dose, mean null (as above), (ii) full dose, trend null,
(iii) A1 dose, mean null, (iv) A1 dose, trend null. **Stop after this:** no further dose components or null models.
