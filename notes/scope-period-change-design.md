# Scope: industrial response to the 2021 period-calendar change (proposal, not registered)

**Status: scoping note, 2026-11-18. Nothing estimated beyond the descriptive hour-by-month check in
`notes/scope-2021-high-voltage-shift.md`. A registration with step-zero rules comes after the user decides the open
choices at the end.**

## In one example
A plant on tariff 6.4TD in July 2020 paid period 2 for 19–22h and period 1 for 14–18h. From 1 June 2021 those swapped:
19–22h became period 1 (dearest) and 14–18h period 2. In July 2021 its load at 19–21h fell about 7% of its daily mean
and its 14–17h load rose about 4%; hours whose period did not change hardly moved. In August, when every hour used to
be the cheapest period and daytime became periods 3–4, its night load rose and its daytime load fell. Nothing like this
happened in June or September, where the calendar barely changed, or in any pre-reform year.

## The treatment: a change of period, by tariff, month, day type and hour
For each tariff k (6.1–6.4, and 3.0 inside E0), month m, day type d (working, weekend/holiday) and hour h:
`Δperiod(k, m, d, h) = new period − old period` (from `tou_tariff_schedule.py`: `old_period_6`, `new_period_6`;
June is split on the 16th under the old calendar). It is known in advance, set by regulation, and varies over
24 × 12 × 2 cells, in both directions (dearer and cheaper hours), with zero-change cells in the same days. Pre-reform
years carry the same cells with no change: placebos.

## The outcome and the comparison
Load by hour as a share of the day's mean (working days), per tariff series (ESIOS 1216–1218, E1+E2; E0 for 3.0TD),
2021 against the same month and hour in normal years (2014–19 where clean). Contrasts already in the design family:
(i) hour-within-day (shape), which removes the day's level; (ii) against the same cell in pre-reform years, which removes
the normal seasonal shape; (iii) Spain minus Portugal LASSO errors, as the paper does, as the main specification or a
check. Because the treatment varies **within** the day and month, the pre-reform deviation of 2021 seen in E1+E2
(January–May) is absorbed by month-by-year effects; only a deviation that lines up with the period changes hour by hour
would bias it.

## From a response to an elasticity: the price of each period
**Reduced form (no prices needed):** the change in load share per one-step change of period. Identified now, but not
an elasticity.

**Elasticity, three price components:**
1. **Energy toll + charges (€/MWh by period):** public, already in `outputs/tables/tou_tariff_prices_2021.csv`; old
   values in `tou_tariff_schedule.py`. This is the current dose, and it is small for 6.3–6.4.
2. **Power term (€/kW-year by period):** public. New: CNMC toll resolution for 2021 (Annex I 1.a, read but not
   tabulated) and the charges order; old: the 6.x power prices in force in 2020 (Orden IET/107/2014 or later update,
   to read). The rule that contracted power must not fall from P1 to P6 (P1 ≤ P2 ≤ … ≤ P6) is what rewards moving
   load out of the dearer periods. Conversion to €/MWh needs an assumption (the period's €/kW-year spread over its
   hours, the standard equivalent-energy price), stated as such.
3. **Energy supply price by period (contracts):** not observable for individual plants. What is observable: the
   contract mix (CNMC IS/DE/031/24: about 32% fixed by period, 35% mixed, 32% hourly-indexed), and wholesale averages by
   period. For a fixed-by-period contract the per-period price is roughly the expected wholesale average over that
   period's hours, so it moves with the calendar only as much as wholesale prices differ between the hours involved
   (small: evening over night about +8% in summer).

**Proposed estimand:** the elasticity of load with respect to the **regulated per-period price** (components 1 + 2),
the part the regulator sets and the reform changed. This is the same kind of object as the paper's household
elasticity: a reform elasticity, not a structural price slope. Component 3 is the threat: if contract prices by period
also moved, the response divided by the regulated change overstates the elasticity. A bound can be stated with the
wholesale-average approximation.

## Step zero (to register)
- **Z1 Placebo spread:** the same statistic in each pre-reform year as if the new calendar had started on 1 June
  (cells with Δperiod ≠ 0 against cells with 0). Gate: detectable reduced-form effect at least three times smaller than
  the descriptive July–August 2021 pattern.
- **Z2 Price gate:** the regulated per-period price change (1 + 2) varies across cells enough to separate it from the
  period step itself (within-day standard deviation of the log change at least 0.02, the earlier readability rule).
- **Z3 Data:** the power-term tables, old and new, read from the BOE and checked against one published bill example.

## Threats
- Plants respond to the calendar through contracts we cannot see (component 3); stated as a bound.
- 2021 has its own oddities (pre-reform deviation in E1+E2, rising wholesale prices). The hour-by-month treatment
  absorbs anything that is not aligned with the period changes.
- Few placebo years for the industrial sum (2017–19); the tariff series 6.2–6.4 have six (2014–19).
- The E5 gap: use the fixed loader for any series that includes 1206.
- Many cells, one reform: inference by year (placebo years), not by cell.

## Open choices for the user
1. Estimand: reduced form only, or the elasticity to the regulated per-period price (energy + power term)?
2. Series: tariff series 6.2–6.4 and E1+E2 only, or also E0 for 3.0TD (mixed with households)?
3. Main specification: hour-share (no control) or Spain-minus-Portugal LASSO errors?
