# The price with hydro offered at its water value

Run 2026-10-07. Script `analysis/counterfactual_hydro.py`; results
`outputs/tables/counterfactual_hydro.csv` (hourly prices in `counterfactual_hydro_hourly.parquet`,
gitignored). Cost: the frozen hydro cost `outputs/tables/hydro_cost_daily.parquet`
(`build/build_hydro_cost.py`; λ*30s, CLAUDE.md "The hydro cost"). Framework spec §7.

**In one line.** Keep the water each storage unit actually used, but price it as a
price-taker would, and the day-ahead price falls by **€0.83/MWh on average (1.0%)**, rising
from €0.2 in 2019 to **€2.2 (3.1%) in 2025**. Hydro moves into the evening peak (−€9 to −15
at 20:00–22:00 in 2024–2025) and out of the night and midday (+€1–2). EDP and Iberdrola
account for most of it; Naturgy, Endesa and Repsol barely move the price, because their
hydro is sold bilaterally or offered at zero.

## 1. The idea, with an example

In an evening hour the price is €110, set by a hydro step at €110 whose water value is
€85. Moved to €85, that step clears; the next offers on the curve now meet demand at, say,
€104. The hour's price falls by €6. A step offered below its water value moves up instead.

## 2. Method

**Re-clearing.** Each hour's effective curve (`step_curves.py`): all MW offered at or below
each price, both sides, against all buy MW; the price is the lowest at which supply meets
demand. With nothing moved this reproduces the cached re-clear in every valid hour. A hydro
step priced below the clearing price is always fully accepted in the files (checked June
2019 and June 2024), so moving a step means taking its MW out at its offer price and putting
it back at the new one. Ties split pro rata. Rivals' offers stay as offered.

**Sample.** Valid hours 2019-01 → 2025-09 (unsplit, clearing identity holds, re-clear
within €0.5): 53,273 hours. The counterfactual is for the joint Iberian price.

**Bilateral hydro is outside the auction.** Over the valid hours 74% of Iberdrola's
storage-hydro output, 69% of Endesa's and 56% of Naturgy's (nearly all of it from 2023) is
delivered under bilateral contracts (PDBF role 4), against 4% of EDP's and none of Movhera's
or Repsol's. Their auction curves cover only the capacity left in each hour, and the
bilateral volume moves a lot between hours (Duero, June 2023: median 156 MW, up to 1,971
MW). The counterfactual leaves it as it was. Counted with it, actual output over the whole
period is 0.94–0.98 of what the cost's running share implies for every group (0.6–1.4 in
single years).

## 3. Results

Mean price change, €/MWh (counterfactual − actual), valid hours:

| | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | all |
|---|---|---|---|---|---|---|---|---|
| actual price | 48.0 | 34.0 | 110.7 | 166.5 | 88.5 | 65.1 | 69.7 | 83.2 |
| **same water** (main) | −0.20 | −0.07 | −0.62 | −0.95 | −1.32 | −1.03 | **−2.17** | **−0.83** |
| same water, EDP alone | −0.12 | −0.13 | −0.21 | −0.63 | −0.42 | −0.39 | −0.88 | −0.37 |
| same water, Iberdrola alone | −0.01 | +0.02 | +0.22 | −0.65 | −0.15 | −0.45 | −0.89 | −0.24 |
| same water, Movhera alone | | | −0.02 | −0.26 | −0.18 | −0.18 | −0.30 | −0.12 |
| same water, Naturgy / Endesa / Repsol | ≈0 | ≈0 | ≈0 | ≈0 | ≈0 | ≈0 | ≈0 | ≈0 |
| at the cost, water free | −0.15 | −0.39 | +3.35 | +2.72 | −1.49 | −2.86 | −3.03 | −0.12 |
| only offers above the cost moved down | −0.66 | −1.14 | −1.83 | −3.35 | −4.96 | −5.77 | −7.23 | −3.34 |
| 90-day cost, water free | +0.22 | +0.40 | +4.23 | +2.14 | +1.12 | −1.16 | −3.88 | +0.65 |

**Same water** (the main reading). Each unit's steps above €1 go to k × its cost, one k
per unit and month: the water value at which a price-taker releasing the unit's actual
auction water would run, in the month's hours where price over cost is highest. k and the
prices are found together (12 damped rounds; a large unit lowers the price where it runs,
so its target is scaled until its output matches). Output over actual: 0.93–1.16 by group
and year, most within 5%. The k that does this, weighted by output: EDP, Iberdrola, Endesa
and Movhera 0.85–1.06 in most years, so the cost is consistent with the water they used;
Naturgy 1.30–1.43 from 2022 (its small auction remainder), EDP 1.47 and Repsol 1.90 in 2025.

**By hour, same water, 2024–2025**: −€15.1 at 21:00, −€9.6 at 20:00, −€8.6 at 22:00,
−€3.2 at 07:00; +€1.2 to +1.9 from 01:00 to 05:00 and +€0.5 to +1.1 at midday. 2019–2023:
the same shape, about 40% of the size.

**At the cost, water free** releases different amounts of water: Iberdrola 15–18% more
than it used in 2024–2025, Naturgy 11–19% more in 2022–2025, EDP 52% less in 2022. In
2021–2022 hydro was offered below the forward-based cost (the forwards rose faster), so
moving it to the cost raises the price. Read it as a description of offers against the
benchmark, not as a counterfactual.

**Only offers above the cost moved down**, −€3.3 (4.0%), −€7.2 (10.4%) in 2025, is an upper
bound: it removes every markup over the benchmark and releases more water than was used.

## 4. Reading

- **Holding the water fixed, hydro priced as a price-taker lowers prices by about 1%, and
  by 3% in 2025.** The effect is the evening peak: the counterfactual runs full turbine
  capacity there, where the actual offer ladders leave part of it unsold at higher prices.
- **That is an upper bound on market power in the pricing of a given volume of water.** A
  cascade cannot always run every plant at once (water routing between dams, minimum
  flows), and the counterfactual assumes it can. The steep ladders beyond the expected
  running share (`rq-water-value-forward.md` §5.3) are consistent with both.
- **It does not measure withholding of water across months**: the same-water counterfactual
  keeps each unit's monthly release as it was.
- **Leg B finds the gap between offers and the cost does not rise with the firm's stake in
  a higher price** (`rq-leg-b-levels.md` §5–6), so what this counterfactual removes is not
  shown to be market power. It is the price effect of hydro not being offered as a
  price-taker with this cost would offer it.

## 5. What this changes elsewhere

**The comparison of offers with the cost at the expected running share** (`rq-water-value-forward.md`
§5.3–5.4: Iberdrola 1.19–1.21, Naturgy 1.13–1.40) reads the auction curve at the unit's
running share. Expected here: for units selling most of their hydro bilaterally, the
water left for the auction is smaller, so the read point and the offer price are lower and
those ratios overstate the gap. Redone 2026-10-08 (§5.5 of that note), this holds for
Iberdrola only (1.16 → 1.11 on the same days; 1.21 → 1.07 in 2025). Endesa and Naturgy
offer only part of their capacity in the auction (not because it is out of service: declared
outages explain 17% of what they leave unoffered, §5.6), so their read point rises: Endesa 1.13 →
1.35, Naturgy 1.19 → 1.22. Their gaps from 2022 stay.

## 6. Limits

- Rivals do not react: gas and coal offers stay as they were.
- About 10% of hours are not valid and left out, mostly market splitting (more in 2021–2022).
- The cost is a lower bound (no option value beyond the month), which overstates the
  water-free variants; same water does not depend on its level, only on its daily path.
- Pumped storage is held as offered in the main reading (`with pumped` moves it too).
