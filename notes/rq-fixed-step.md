# One fixed step per unit and hour: running note

Design: `docs/specs/2026-10-19-fixed-step-design.md`. Script: `analysis/fixed_step_test.py`.

## Step 1: the rows (2026-10-19)

`fixed_step_test.py --build` → `outputs/cache/step/fixed_step_YYYYMM.parquet` (81 months,
2019-01 → 2025-09; one row per unit, owner group and hour); `--summarise` →
`outputs/tables/fixed_step_rows_summary.csv`. Logs `.superpowers/sdd/2026-10-19-fixed-step/`.
Descriptive only; no estimates.

**In one line.** The fixed step exists in every unit-hour and sits at about the water value
(1.06 × λ* pooled), so it is the right object. The main sample is 374,721 unit-hours on 39
storage units (about 25 GW). But **the seller and buyer sides are mostly different firms**: the
seller side is 74% EDP and Iberdrola, the buyer side 64% Endesa and Naturgy. Endesa's stake at
cost is positive in 0.2% of its hours.

**Rows.** 2,853,351 unit-hours on 64 units. Storage hydro with the cost describing the
offers (`zero_share ≤ 0.5`): 1,257,606, about 15,500 a month. Left out: the unit-days where
more than half the offered hydro is at or below €1. Units out on most days are 31 units, 2.4
GW, mostly aggregated units offering at €0. The main sample adds Zb defined and the hour's
at-cost price ≥ 0.9 λ*.

### Coverage, storage hydro

| year | units | unit-hours | main | one price | offered / capacity | Zb defined | Zb > 0 | in play (0.9–1.1 λ*) | above 1.1 λ* | net read defined | contracted |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2019 | 25 | 176,565 | 62,608 | 17% | 0.68 | 87% | 34% | 35% | 1% | 90% | 0.02 |
| 2020 | 24 | 168,360 | 56,700 | 14% | 0.73 | 88% | 42% | 31% | 4% | 91% | 0.00 |
| 2021 | 25 | 166,998 | 45,346 | 19% | 0.70 | 90% | 41% | 24% | 4% | 89% | 0.00 |
| 2022 | 33 | 196,182 | 49,123 | 24% | 0.73 | 88% | 47% | 20% | 5% | 84% | 0.08 |
| 2023 | 32 | 229,924 | 63,787 | 37% | 0.53 | 88% | 31% | 19% | 9% | 83% | 0.39 |
| 2024 | 30 | 188,601 | 58,460 | 23% | 0.69 | 88% | 36% | 19% | 12% | 80% | 0.40 |
| 2025 (to Sep) | 29 | 130,976 | 38,697 | 18% | 0.73 | 80% | 30% | 17% | 13% | 81% | 0.41 |

"Contracted": the median unit-month's bilateral delivery over its expected water. "Offered /
capacity": median.

### Where the ladder sits, main sample (medians, over λ*30s)

| year | λ* (€) | bottom 5% | 0.1 cf_s | 0.5 cf_s | **cf_s** | 1.5 cf_s | 2 cf_s | net read | fixed MW | read within €10 of the price |
|---|---|---|---|---|---|---|---|---|---|---|
| 2019 | 54 | 0.96 | 0.93 | 0.98 | **1.01** | 1.04 | 1.08 | 1.03 | 1.01 | 60% |
| 2020 | 39 | 0.81 | 0.10 | 0.95 | **1.04** | 1.11 | 1.19 | 1.07 | 1.04 | 56% |
| 2021 | 100 | 0.80 | 0.69 | 0.89 | **0.94** | 0.98 | 1.04 | 0.97 | 0.94 | 38% |
| 2022 | 186 | 0.94 | 0.89 | 0.98 | **1.05** | 1.15 | 1.25 | 1.08 | 1.07 | 12% |
| 2023 | 108 | 1.11 | 1.10 | 1.16 | **1.26** | 1.39 | 1.66 | 1.25 | 1.25 | 14% |
| 2024 | 96 | 1.10 | 1.09 | 1.14 | **1.22** | 1.32 | 1.51 | 1.16 | 1.18 | 19% |
| 2025 | 99 | 1.07 | 1.06 | 1.11 | **1.17** | 1.27 | 1.39 | 1.09 | 1.15 | 17% |
| all | 90 | 0.96 | 0.94 | 1.00 | **1.06** | 1.13 | 1.23 | 1.07 | 1.06 | 32% |

Pumped storage apart (7–8 units, 3.3 GW, 7,800–14,500 main rows a year): read at cf_s 0.99–1.09
× λ* to 2024, 0.82 in 2025.

### By owner group, storage

| group | units | GW | main rows | seller share (main) | offered / capacity | contracted | net read defined | cf_s / λ* | bottom / λ* | 2 cf_s / λ* |
|---|---|---|---|---|---|---|---|---|---|---|
| EDP | 8 | 8.3 | 112,931 | 70% | 0.95 | 0.00 | 99% | 0.99 | 0.85 | 1.10 |
| Iberdrola | 9 | 9.4 | 93,682 | 78% | 0.76 | 0.66 | 76% | 1.25 | 1.13 | 1.90 |
| Naturgy | 4 | 1.8 | 60,281 | 20% | 0.23 | 0.67 | 66% | 1.33 | 1.26 | 1.45 |
| Endesa | 10 | 3.5 | 59,044 | 0.2% | 0.12 | 0.58 | 85% | 1.05 | 1.01 | 1.15 |
| Repsol | 1 | 0.3 | 24,582 | 80% | 0.65 | 0.00 | 100% | 0.81 | 0.00 | 1.25 |
| Movhera | 1 | 1.7 | 10,604 | 90% | 0.92 | 0.00 | 100% | 0.94 | 0.70 | 1.11 |
| Ignis | 1 | 0.1 | 9,805 | 100% | 0.93 | 0.00 | 100% | 1.49 | 1.24 | 1.54 |
| Acciona | 4 | 0.8 | 3,573 | 64% | 0.31 | 0.00 | 100% | 0.01 | 0.01 | 0.01 |

Who forms each side (main sample): **seller side** 205,956 unit-hours: EDP 39%, Iberdrola 35%,
Repsol 10%, Naturgy 6%, Ignis 5%, Movhera 5%. **Buyer side** 167,820: Endesa 35%, Naturgy 29%,
EDP 20%, Iberdrola 13%.

### What this shows

- **The read at cf_s is defined on every unit-hour and sits at the water value.** It is 0.94–
  1.05 × λ* in 2019–2022, with the ladder rising through it (from 0.93 at a tenth of cf_s to
  1.08 at twice it, 2019). It is the unit's water-value step, as the daily read found
  (`rq-water-value-forward.md` §5.3).
- **From 2023 the whole storage ladder sits above λ***: 1.26, 1.22 and 1.17 × at cf_s, and the
  bottom step at 1.07–1.11. The gap is Iberdrola's (1.25) and Naturgy's (1.33), not EDP's (0.99)
  or Movhera's (0.94), as §5.4 of that note found by year. The unit × month effects absorb that
  level. Step 2 asks whether the gap moves with the stake within the month.
- **The read step is near the price less often in dear years.** It is within €10 of the
  clearing price in 56–60% of main-sample hours in 2019–2020, and in 12–19% from 2022. So
  2022–2025 carry less power per row.
- **Side and firm go together.** Endesa is on the buyer side in 99.8% of its main hours, and
  Naturgy in 80%. EDP and Iberdrola are on both sides (70% and 78% seller). A pooled
  seller/buyer contrast is therefore largely EDP and Iberdrola against Endesa and Naturgy. The
  simulation's §15–16 split used the same Zb, so it likely carries the same mix (not measured
  there).
- **Contracts take much of three firms' water.** Iberdrola, Naturgy and Endesa deliver 58–67%
  of their expected water bilaterally (median unit-month), from 2023 for most of it. Their net
  reads are undefined in 15–34% of hours. EDP, Movhera and Repsol deliver none.
- **Endesa and Naturgy offer little of their capacity** (12% and 23%, median). So a fixed share
  of their ladders reads few MW, which is why the quantity outcomes are in step 2.

### Implications for step 2 (my calls, to check)

1. **Count offers at ≤ €2 as zero-priced** when dropping unit-days. Acciona's four kept units
   offer at €1.03, just above the €1 threshold, so their reads are 0.01 × λ* (3,573 main rows,
   1%).
2. **Add the side split within firm**, for EDP and Iberdrola, the two firms on both sides. That
   separates "net sellers price higher" from "EDP and Iberdrola price differently from Endesa and
   Naturgy". Report the pooled side split as designed.
3. **The bottom-step placebo is clean only to 2022.** From 2023 the bottom step itself sits
   above λ* (1.07–1.11), so it may not clear in every hour. Read the placebo for 2019–2022, and
   from 2023 add the step at 0.1 cf_s as a second placebo, with the same caveat.
4. Pumped storage apart, as designed; 2025 pumped reads sit below λ* (0.82).

## Step 2: the estimates (2026-10-19)

`fixed_step_test.py --estimate` → `outputs/tables/fixed_step_results.csv`; `--simulated 1`,
`--simulated 2` (the code check: simulated price-takers' offers, seeds 1 and 2 as in the
simulation note, steps above €1 moved as `step_engine.simulate` moves them, read the same way)
→ `fixed_step_results_sim{1,2}.csv`, plus `fixed_step_results_sim_halfyear.csv` (the half-year,
profile and band cells on the simulated rows); actual against simulated in
`fixed_step_reading.csv`; within-firm checks in `fixed_step_results_within_firm_checks.csv`.
Logs `.superpowers/sdd/2026-10-19-fixed-step/`. Unit-months with more than half the offered MW
at or below €2 are out: 1,212,678 storage rows, **359,156 in the main sample** (34 units).
g = read at cf_s − λ*30s on Zb by least squares, unit × month and hour effects, week clusters.

**In one line.** At the fixed step, hydro offers are close to price-taking. Pooled, the slope is
+0.17 [+0.02, +0.31], and the simulated price-takers give −0.00 and +0.06, so +0.14 above them
[−0.05, +0.32]. The seller side, and EDP, sit on the price-takers. **The simulation's dating
(sellers depart in 2019–2021H1 and stop in 2021H2) gets weak support**: positive seller-side
gaps in 2019H2–2020H2, one of three clear of the band, none in 2019H1 or 2021H1. Two things
stand out instead. Iberdrola's buyer hours are 1.4–2.1 above the price-takers, beyond Nash.
And 2023 is high. **The code check fails in the finer cells**: price-takers read up to ±0.6
there, so the fixed step needs the band too, though less than the step estimator.

### The code check: what price-takers give at the fixed step

| cell | actual | seed 1 | seed 2 |
|---|---|---|---|
| pooled | +0.17 [+0.02, +0.31] | +0.06 [−0.03, +0.16] | −0.00 [−0.10, +0.09] |
| departure / crisis | +0.10 / +0.20 | −0.03 / +0.11 | −0.06 / +0.03 |
| seller side / buyer side | +0.05 / +0.26 | +0.06 / +0.17 | −0.00 / +0.02 |
| Iberdrola buyer hours | +2.00 [+1.19, +2.82] | +0.59 [+0.18, +1.00] | +0.52 [+0.14, +0.89] |
| seller side 2019H2 / 2020H1 | +0.95 / +0.81 | +0.44 / +0.44 | +0.55 / +0.63 |
| buyer side 2020H1 / 2022H1 | −1.21 / −0.77 | −2.07 / −1.06 | −1.75 / −0.79 |

- **Pooled, the fixed step does what the design said**: price-takers read 0 (+0.06, −0.00), with
  no band needed.
- **Within a half-year and side, or within a firm, it does not**: price-takers read +0.44 to
  +0.63 on the seller side in 2019H2–2020H1, −0.8 to −2.1 on the buyer side in some half-years,
  and +0.5 on Iberdrola's buyer hours. The read at a share of the hour's ladder lands on a
  different step when the ladder's volume and number of steps change. The firm sets those hour
  by hour, and they move with the stake (the simulation keeps them as offered). So the fixed
  step removes the price-setting selection but not this one. The table below reads every cell
  against the two seeds, by the simulation note's rule (differs when the 95% interval misses
  the seeds' range; bias-adjusted range = [low − seed max, high − seed min]).

### Against the price-takers

| cell | actual | price-takers | gap | bias-adjusted range | differs |
|---|---|---|---|---|---|
| pooled | +0.17 | −0.00 … +0.06 | +0.14 | [−0.05, +0.32] | no |
| departure | +0.10 | −0.06 … −0.03 | +0.15 | [−0.08, +0.38] | no |
| crisis | +0.20 | +0.03 … +0.11 | +0.13 | [−0.11, +0.37] | no |
| seller side | +0.05 | −0.00 … +0.06 | +0.02 | [−0.18, +0.23] | no |
| seller, departure / crisis | −0.21 / +0.15 | | −0.06 / +0.05 | [−0.36, +0.25] / [−0.21, +0.31] | no / no |
| buyer side | +0.26 | +0.02 … +0.16 | +0.17 | [−0.28, +0.61] | no |
| EDP seller / buyer | +0.12 / +0.03 | | −0.03 / −0.19 | [−0.39, +0.33] / [−0.75, +0.37] | no / no |
| Iberdrola seller | +0.05 | −0.08 … +0.02 | +0.08 | [−0.15, +0.30] | no |
| **Iberdrola buyer** | **+2.00** | +0.52 … +0.59 | **+1.45** | **[+0.60, +2.30]** | **yes** |
| Iberdrola buyer, departure / crisis | +2.74 / +1.91 | | +2.13 / +1.39 | [+1.01, +3.26] / [+0.47, +2.31] | yes / yes |

Seller side by half-year (gap over the price-takers; the step estimator's §16 gap beside it):

| | 2019H1 | 2019H2 | 2020H1 | 2020H2 | 2021H1 | 2021H2 | 2022H1 | 2022H2 | 2023H1 | 2023H2 | 2024H1 | 2024H2 | 2025H1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fixed step | −0.07 | +0.45 | +0.28 | **+0.64** | +0.03 | −0.13 | −0.27 | +0.29 | −0.40 | **+1.89** | −0.02 | +0.21 | −0.36 |
| step estimator (§16) | **+0.41** | +0.29 | **+0.55** | **+0.44** | +0.46 | +0.05 | +0.14 | **−0.29** | −0.17 | −0.22 | −0.08 | +0.30 | +0.08 |

Bold: differs from the price-takers. All half-years pooled over both sides: differs only in
2023H1 (+0.82) and 2023H2 (+1.26).

### Profile, placebo, bands, checks

| | actual | price-takers | gap |
|---|---|---|---|
| bottom 5% of the ladder (placebo, 2019–2022) | −0.13 [−0.30, +0.03] | | (passes) |
| bottom 5% / 0.5 cf_s / cf_s / 1.5 cf_s / 2 cf_s, pooled | −0.02 / +0.10 / +0.17 / +0.21 / +0.19 | −0.07…−0.02 / −0.02…+0.04 / −0.00…+0.06 / −0.01…+0.05 / 0.00…+0.07 | +0.03 / +0.09 / +0.14 / **+0.19** / +0.16 |
| hours with at-cost price < 0.9 λ* (the step cannot set the price) | +0.27 [+0.17, +0.38] | +0.04 … +0.07 | **+0.22** |
| hours 0.9–1.1 λ* / above 1.1 λ* | +0.31 [+0.16, +0.46] / −0.09 [−0.33, +0.15] | | |
| net of contracts | +0.09 [−0.06, +0.23] | | |
| fixed MW | +0.23 [+0.08, +0.38] | | |
| unit × day effects | +0.14 [−0.01, +0.29]; departure −0.25, crisis +0.33 | | |
| + unit × hour of day | +0.12 [−0.03, +0.27] | | |
| level control (slope per unit on at-cost price − λ*) | +0.23 [+0.08, +0.37] | | |
| offered MW / capacity, per sd of Zb | −0.5 points of capacity | | |
| MW offered at or below λ* / capacity, per sd of Zb | −0.4 points | | |
| pumped storage (8 units) | +0.14 [−0.02, +0.30]; departure +0.18 [+0.06, +0.29] | | |

- **The placebo passes**: the bottom of the ladder does not move with the stake (−0.13 to 2022;
  −0.02 pooled). The slope rises along the ladder, from 0 at the bottom to +0.2 from 1.5 cf_s
  up, which is the shape market power predicts.
- **But it is there in hours where the step cannot set the price** (+0.22 over the
  price-takers when the at-cost price is below 0.9 λ*). A firm gains nothing from pricing a
  step it cannot sell. So at least part of the slope is the top of the ladder moving with the
  stake for another reason.
- **Withholding by volume is negligible**: half a point of capacity per standard deviation of
  the stake.
- **The pooled slope is not robust**: net of contracts +0.09, with unit × hour-of-day effects
  +0.12 (both include 0); unit × day gives −0.25 in the departure periods and +0.33 in the
  crisis.

### Iberdrola's buyer hours

When Iberdrola is a net buyer at cost (22% of its main-sample hours: `EBRA`, `SIL`, `DUER`,
`TAJO` mostly), its step at cf_s falls by about €2 for each €1 of Cournot markdown. Robust:
+1.74 with unit × hour-of-day effects, +2.81 with unit × day, +2.85 without `EBRA` (the 220 MW
unit offered flat at about €360), +1.56 in the hours in play. Price-takers give +0.5 there.
**Twice to three times the Nash markdown is more than market power can give** (β ≤ 1), so it
is a lead to follow, not a result: something in Iberdrola's hydro moves with its net purchases
hour by hour (pumping, its retail load, its contracts), and the stake picks it up. EDP's slope,
on both sides, sits on the price-takers.

### Reading

- **Both designs bound the pooled hydro β well below Nash**: about +0.14 above price-takers here
  (range to +0.32), against +0.07 in the step estimator.
- **The step estimator's dated departure does not carry over.** Sellers' markups in 2019–2021H1
  and the stop in 2021H2 were the simulation note's main finding (§14–16). At the fixed step,
  seller-side gaps are positive in 2019H2–2020H2 and mixed after (around zero except 2023H2),
  but only 2020H2 is clear of the band, 2019H1 and 2021H1 show nothing, and 2023H2 is the largest of all. What both
  designs share is a modest seller-side departure in 2019H2–2020H2.
- **Neither design is free of the band.** The fixed step removes the selection on the price,
  and the pooled slope then needs no band; within cells, the ladder's volume and steps still
  move with the stake.
- **New**: Iberdrola's buyer hours (beyond Nash, so probably not conduct) and 2023 (+0.8, +1.3,
  both sides). Neither was predicted.
