# One fixed step per unit and hour: the hydro departure without the simulation

**Status: built and run 2026-10-19 (`notes/rq-fixed-step.md`).** One claim below did not hold:
pooled, price-takers do read 0 at the fixed step, but within half-year × side and within-firm
cells they read up to ±0.6, because the read point moves with the hour's ladder (step 2, the
code check). Those cells are read against the simulated band. As first written: The data facts in §2 were
checked the same day on four months with a throwaway query (no committed script). It builds
on the step caches of `step_engine.py` (`outputs/cache/step/`), the water value λ*30s
(`build/build_water_value_forward.py`) and the at-cost stake Zb (`rq-leg-b-levels.md` §5).
It is a check on the simulation-based results in `notes/rq-price-taking-simulation.md`
§14–16. Framework: [`2026-09-29-thesis-framework-design.md`](2026-09-29-thesis-framework-design.md).

**In one example.** Iberdrola's Duero unit expects to run about 20% of the hours this month
(its capacity factor for the month in other years, moved by its basin's fill). In each hour
it offers a ladder of steps. Read the price of the step that covers the first 20% of what it
offers. That point is fixed before the auction, and it is the same point in every hour of the
month. A price-taker prices that step at its water value whatever its firm stands to gain from
a higher price. A firm with market power prices it higher in the hours when its stake is
large. **Every hour enters, whether or not the price reaches the step**, so we know without a
simulation what price-taking gives: a slope of zero on the stake.

---

## 1. Why the current estimator needs a simulation and this one does not

The step estimator keeps a step only in the draws where it sets the price. A price-taker
offering at λ* plus noise then shows a gap that rises with how high the hour's prices sit
above λ*: in a dear hour only its high steps set the price, in a cheap hour only its low ones.
The stake moves with that too (correlation −0.20, simulation note §3), so price-takers read
β ≠ 0, by an amount that depends on the rows: −0.14 to −0.26 in the first runs, +0.19 on the
seller side in §15. The simulation measures that amount, on two seeds whose bands can differ
by 0.25 (§16).

Here the step is chosen from the unit's expected running share, which comes from other years,
and from its own ladder in the hour, not from where the price lands. Nothing selects the rows
on the outcome. Under price-taking the slope on the stake is zero, and the reading needs no
band.

**What it does not remove.** Both designs assume λ* is a price-taker's cost, and that what is
left of a price-taker's offer does not move with the stake within the month. The simulation
assumed it too (its noise is independent of the hour). §6 lists the checks.

## 2. What the data show (checked 2026-10-19, four months)

Storage hydro units with a water value, leaving out unit-days where more than half the
offered hydro is at or below €1 (`zero_share > 0.5` in `hydro_cost_daily`: the cost does not
describe those units' offers; mostly small aggregated units and Endesa's `GDLQ`). Pumped
storage apart. The hour's curve: the unit's offered hydro steps, withdrawn steps out, sorted
by price.

| month | units | GW | unit-hours | one price only | read at cf_s / λ* (median) | same, in play | net-of-contracts read defined | Zb defined | Zb > 0 | in play |
|---|---|---|---|---|---|---|---|---|---|---|
| 2019-06 | 21 | 20.2 | 14,709 | 17% | 1.08 | 1.06 | 87% | 97% | 44% | 56% |
| 2021-03 | 18 | 18.9 | 12,732 | 13% | 1.09 | 1.13 | 94% | 93% | 56% | 25% |
| 2022-09 | 25 | 19.2 | 16,359 | 23% | 1.00 | 0.94 | 74% | 96% | 59% | 16% |
| 2024-10 | 22 | 18.8 | 15,509 | 17% | 0.97 | 0.91 | 65% | 87% | 28% | 14% |

Pumped: 7–8 units, 3.3–3.4 GW, 3,100–4,200 unit-hours a month; read at cf_s 0.72–1.08 × λ*.

- **The read at cf_s is defined on every unit-hour** and sits at about λ*: 0.97–1.09 × λ*,
  0.91–1.13 in the hours in play. It is the unit's water-value step, as §5.3 of
  `rq-water-value-forward.md` found at the daily level.
- **Net of contracts the read point is undefined where contracts take all the expected water**:
  6–36% of units in a month, rising over time. So the gross read at cf_s is the main outcome.
- **Zb is defined on 87–97%** of unit-hours (below the slope floor otherwise).
- **"In play"** = the hour's at-cost price (the draws' mean price with the firm's hydro at
  λ*, `hcompcostprice`) within ±10% of λ*. 56% of unit-hours in 2019, 14–25% from 2021: λ*
  is a high percentile of the month's prices for a unit that runs 10–30% of the hours, so
  most hours price below it. Above 1.1 λ*: 0–20%.
- **About 15,000 storage unit-hours a month**, so about 1.2 million over 81 months, against
  661,575 price-setting rows in the step estimator. But the step estimator has 46 units,
  because it keeps the zero-priced units this design leaves out.

## 3. Specification

**Outcome.** g_uh = b_uh(cf_s) − λ*30s_ud: the price of the first step at which the unit's
cumulative offered share in hour h reaches its expected running share cf_s that day, minus
its water value that day (€/MWh).

**Regressor.** Zb_fh, the firm's stake at cost in hour h: its net position over the slope of
its residual demand, read on the curve with its hydro at λ*, over the 5 draws nearest the
day's median λ* of the hydro class (`leg_b_levels.at_cost`). One value per firm and hour.

    g_uh = b · Zb_fh + unit × month + class × hour + e

At the cost point, and for small β, the firm's stake on its actual curve is close to Zb, so b
is β to a first approximation: the markup over the water value as a share of the Cournot
markup.

**Fixed effects and inference** as in §14–16: unit × month and class × hour
(`leg_b_levels.UNIT_MONTH`), clusters by week. With one regressor and no instrument, the 95%
set is the confidence interval.

**Main sample.** Storage hydro, `zero_share ≤ 0.5`, Zb defined, 2019-01 → 2025-09, **hours in
play or above them** (at-cost price ≥ 0.9 λ*): the hours in which a price-taker would want its
water. A step far above the hour's price cannot set it, so a markup there earns nothing.

**Cells**, the ones the simulation read:
1. pooled; departure periods (2019-01 → 2021-06, 2024-01 → 2025-09) against the crisis;
2. each half-year 2019H1 → 2025H1 (§14);
3. seller side (Zb > 0) and buyer side (Zb < 0), pooled and by half-year (§15–16).

**Reading rule.** A cell **differs** from price-taking if its 95% set excludes 0. Price-taking
is **accepted** if the set lies within ±0.1, the δ of the simulation note (§7). No null band.

## 4. Profile and checks

| check | what it answers |
|---|---|
| **the ladder at fixed shares** 0.1, 0.25, 0.5 × cf_s and 1.5, 2 × cf_s (capped at the top step) | where on the ladder b sits; under market power, near cf_s and above it, not at the bottom |
| **the bottom step** (the cheapest 5% of the ladder), as a placebo | it clears in any hour, so a markup there earns nothing; b ≠ 0 there means the whole ladder moves with Zb for a reason other than market power |
| **all hours**, and hours by band of at-cost price / λ* (below 0.9, 0.9–1.1, above 1.1) | whether b is in the hours that matter |
| **net of contracts** (read at the water left after PDBF role 4, pooled over the month; `water_value_forward_check.offered`) | the auction's own marginal water; the unit-months where it is defined |
| **unit × day** effects, outcome b_uh(cf_s) | λ* drops out entirely; identified from hours within the day |
| **unit × hour-of-day** effects added | stable within-day profiles of a cascade |
| **the `level` control** (a slope per unit on at-cost price − λ*) | should barely move b, since there is no selection to correct; if it does, offers follow the hour's price for a reason the design does not model |
| **quantity**: offered hydro MW over capacity; MW offered at or below λ* | withholding by volume, which a read at a fixed share of a smaller ladder would hide |
| **the simulated price-takers** (`step_engine.simulate`, seeds 1 and 2, offers regenerated, no re-clearing), read the same way | a code check: they must give b ≈ 0 |

## 5. Predictions, fixed in advance

- **If the simulation's results are about the firms**, the seller side shows b > 0 in
  2019–2021H1 (§16: +0.29 to +0.55), b ≈ 0 from 2021H2 to 2024H1, and the bottom step shows
  nothing.
- **If they are about the price-taker band**, b ≈ 0 everywhere, or the pattern does not follow
  the dates.
- **If b > 0 and the bottom step moves too**, the ladder moves with the stake for another
  reason (within-day water values, §6), and neither design measures market power there.

## 6. Threats

| threat | answer |
|---|---|
| A price-taker's cost varies across hours in ways tied to the stake (a cascade cannot run every plant at once; evening water is worth more) | unit × hour-of-day effects; the bottom-step placebo; the unit × day check. The simulation's price-takers ignored this too |
| λ* errors correlated with Zb across days of a month | unit × day check (λ* is daily) |
| The firm offers less volume when its stake is high, so a fixed share of a shorter ladder reads a cheaper step | the quantity outcomes; and a read at a fixed MW (cf_s × the month's mean offered MW), where it exists |
| The read step is not where the price lands in most hours (in play 14–25% from 2021) | main sample is the hours in play or above; b by band of at-cost price |
| Fewer units than the step estimator (18–25 against 46) | the excluded units offer mostly at zero, so their λ* gap says nothing. Report capacity covered |
| Flat ladders (13–23% one price) | the read is the ladder's price; a flat ladder that moves with Zb still counts |
| Contracts take all the expected water in 6–36% of unit-months | gross read as main; net read as check |
| Zb below the slope floor in 3–13% of unit-hours | rows dropped, as in the step estimator; the floor is predetermined (the at-cost curve) |

## 7. Steps, each a separate run proposed before it starts

1. **Rows.** One row per unit and hour, from the caches: reads at cf_s and at the grid, the
   bottom step, the net read, offered MW and MW ≤ λ*, Zb, at-cost price, λ*30s, fill,
   storage, side. Descriptive summary by year. (`analysis/fixed_step_test.py --build`, a cache
   in `outputs/cache/step/fixed_step_YYYYMM.parquet`.)
2. **Estimates.** §3's cells and §4's checks, with the reading rule; the simulated
   price-takers as the code check.

## 8. Left to the builder

- Whether the read is the first step reaching cf_s (as `water_value_forward_check.read_at`)
  or an interpolation within it. The first step is the default.
- Whether an IV version is worth adding: the stake on the actual curve at the draws nearest
  the cost point, instrumented by Zb, if the caches already hold it.
- How to report the fixed-MW read where the unit offers less than it.

**My calls, to check:** the gross read at cf_s as the main outcome, not net of contracts;
leaving out the zero-priced unit-days; the main sample cut at at-cost price ≥ 0.9 λ*; δ = 0.1
as before; the bottom step as the placebo.
