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
is a lead to follow, not a result (against the price-takers it shrinks to about Nash: see "The
Iberdrola check" below): something in Iberdrola's hydro moves with its net purchases
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

## Next: Iberdrola's buyer hours (proposed 2026-10-20, not run)

**What they look like** (descriptive, main sample, within unit × month; a throwaway query).
Iberdrola is a net buyer at cost in 21% of its main-sample hours: 43% in 2019 and 44% in 2023,
2–7% in 2022, 2024 and 2025; mostly January–May. **So the high 2023 half-years (+0.8, +1.3)
probably come from these hours too.** Its buyer hours split into fifths by how much it is
buying (stake demeaned within unit-month):

| fifth | stake | step at cf_s | step at fixed MW | bottom step | offered MW | steps | cleared MW | λ* | at-cost price |
|---|---|---|---|---|---|---|---|---|---|
| most buying | −18.9 | −16.3 | −22.4 | −3.0 | +130 | +0.65 | −17 | +2.6 | −0.8 |
| 2nd | −5.8 | −9.0 | −11.8 | −6.2 | +92 | +0.44 | +3 | +0.6 | −0.8 |
| 3rd | −2.5 | −0.2 | −1.5 | −1.8 | +51 | +0.20 | −3 | +0.1 | −0.5 |
| 4th | −1.2 | −0.9 | −0.1 | −0.2 | +7 | 0.00 | +3 | +0.3 | +0.2 |
| least buying | +0.7 | +2.4 | +2.2 | +2.1 | −13 | −0.07 | −1 | −0.4 | 0.0 |

€/MWh and MW, deviations from the unit-month mean. EDP's most-buying fifth: −0.9 at cf_s, no
pattern.

When Iberdrola buys most, it **offers about 130 MW more hydro and prices the middle of its
ladder €16–22 lower**. The bottom barely moves, and the hour's at-cost price is not lower. A
price-taker would not do this: its water value does not depend on its own purchases.

**Three readings, and what separates them.**
1. **Buyer market power with a stake larger than measured.** The markdown is 2–3 × β·Zb, so
   β ≤ 1 needs a true stake two to three times Zb. That could happen if Iberdrola's exposed
   purchases exceed its auction position.
2. **Covering its own customers by quantity.** When its own generation falls short (a reactor
   out, low wind), it offers more hydro cheaply so the hydro runs, whatever that does to the
   price.
3. **The post-auction bilateral option.** Iberdrola can nominate hydro to its own retailer up
   to 13:00, after the day-ahead prices (`rq-midday-hydro.md` §3.8), so its auction ladder is
   only part of the decision.

**The check.** Split the stake into its two parts, as the nuclear slope test did
(`rq-nuclear-cuts.md`). Zb = n / |RD′|: n is the firm's net position at the cost point (MW),
|RD′| the slope of its residual demand.
- **Price motive (1)**: the response runs through Zb, i.e. it scales with 1/|RD′|. With both in,
  n adds nothing.
- **Supply motive (2)**: it runs through n, the MW short. With n in, Zb adds nothing.
- **An exogenous shift in n**: Iberdrola's reactor-outage dose
  (`reactor_outage_dose.parquet`, by owner share) moves its MW short without moving the slope of
  its residual demand.
- **Read against EDP and the simulated price-takers** (seeds 1, 2) as the band; 2019 and 2023
  apart, the two years with most buyer hours. Also the 2023 half-years without Iberdrola, to see
  if they drop to price-taking.
- **Data**: n and the slope are in `hcompcost` (`kb_sn`, `kb_s`, over the 5 draws nearest the
  cost point). Step 1's rows dropped them, so they are re-attached. Nothing to fetch.

(3) cannot be tested from the auction alone. It needs the PDBF bilateral nominations
hour by hour against the auction ladder, which `iberdrola_self_supply.py` began.

## The Iberdrola check (2026-10-20)

`fixed_step_test.py --iberdrola` → `outputs/tables/fixed_step_iberdrola.csv` (actual offers,
seed 0, and simulated price-takers, seeds 1 and 2, on the same rows); log
`.superpowers/sdd/2026-10-19-fixed-step/iberdrola.log`. Main sample as in step 2. Each
regression is one pooled regression, with every firm's terms in it, so the hour effects come
from all firms. n = the firm's net position at the cost point (GW), from `hcompcost`; Zb =
n / |RD′| exactly. Within unit-month, n and Zb correlate 0.67 on Iberdrola's buyer side and
0.61 on its seller side, so they can be told apart. Dose = Iberdrola's planned and unplanned
reactor outages, owner's share (`reactor_outage_dose.parquet`), > 0 in 39% of its hours (mean
522 MW); P = dose / |RD′|.

**In one line.** (Two seeds. With ten, the "price-motive signature" below is withdrawn and the
buyer slope is mostly routing between contracts and the auction: see "Ten seeds" below.)
**The high 2023 half-years are Iberdrola's**: without it, both fall inside
the price-takers' band. Iberdrola's buyer-hour slope is half artefact. What is left, +0.9 to
+1.45 above the price-takers, runs through the stake Zb and not through the MW position n:
the sign of a price motive, about the size of Nash. On its seller side the opposite holds: the
step rises with the MW position (+€6.9 per GW), not with the stake. The reactor dose cannot
separate the two, because price-takers' reads move with it too.

**The stake split into position and slope** (gap at cf_s on Zb and n jointly; €/MWh per unit
of Zb, and per GW of n):

| term, pooled | actual | price-takers | gap | bias-adjusted range | differs |
|---|---|---|---|---|---|
| Iberdrola buyer: Zb | +1.80 [+0.97, +2.63] | +0.89 … +0.91 | +0.90 | [+0.07, +1.74] | **yes** |
| Iberdrola buyer: n | −0.03 [−5.7, +5.7] | −4.3 … −3.4 | | [−2.3, +10.0] | no |
| Iberdrola buyer, n alone | +10.2 [+4.3, +16.0] | +0.8 … +1.6 | +9.0 | [+2.7, +15.3] | yes |
| Iberdrola seller: Zb | −0.27 [−0.45, −0.08] | −0.14 … −0.01 | | [−0.45, +0.05] | no |
| Iberdrola seller: n | +6.9 [+4.6, +9.3] | +0.7 … +1.4 | +5.9 | [+3.2, +8.6] | **yes** |
| EDP buyer: Zb / n | +0.22 / −2.1 | +0.08 … +0.19 / −0.3 … +2.7 | | | no / no |
| EDP seller: Zb / n | −0.03 / +2.3 | +0.04 … +0.16 / +0.1 … +1.1 | | [−0.49, +0.24] / [−0.29, +3.70] | no / no |

By year, Iberdrola's buyer Zb: 2019 +1.10 [−2.1, +4.3], 2023 +1.23 [−0.03, +2.49], other years
+0.71 against a band of +0.58 … +0.89. Each year alone is inside the band. The pooled excess
comes from 2019 and 2023 together, the years Iberdrola was a buyer in 43–44% of its hours. Its
seller n: 2019 +7.8, 2023 +39.6, other years +6.2 (the last two clear of the band).

**The reactor dose.**

| | actual | price-takers |
|---|---|---|
| first stage: Iberdrola's n per GW of dose | −0.81 [−1.06, −0.56] | (the same rows) |
| gap on D (per GW) and P (per €/MWh) jointly, pooled: D / P | +10.8 [−1.2, +22.9] / −1.45 [−2.22, −0.69] | +9.6 … +10.6 / −1.07 … −0.95 |
| gap on D alone, pooled / departure / crisis | −2.1 / +8.7 / −17.7 | +1.1 / +3.3 … +8.2 / −9.7 … −2.1 |

- A GW of lost reactor output lowers Iberdrola's position at cost by 0.81 GW, as the reactor
  note found (77–86%).
- Its hydro step moves with the dose about as the price-takers' does. The simulated reads
  respond to the dose (P −1.0) because the outage changes the hour's ladder, which the
  simulation keeps. So the dose cannot separate a price motive from a supply motive here.

**2023 without Iberdrola.**

| | all firms | without Iberdrola | price-takers, without Iberdrola |
|---|---|---|---|
| 2023H1 | +1.07 [+0.43, +1.70], differs | +0.27 [−0.39, +0.92] | +0.16 … +0.87 |
| 2023H2 | +1.75 [+1.12, +2.38], differs | +1.09 [+0.25, +1.94] | +0.41 … +0.76 |

### Reading

- **2023 is Iberdrola.** Without it, both half-years sit inside the band.
- **As a buyer, Iberdrola prices its hydro below the water value by about the Nash markdown,
  in 2019 and 2023.** The excess over the price-takers is +0.9 with n in the regression
  ([+0.07, +1.74]) and +1.45 without ([+0.60, +2.30]), so "beyond Nash" (step 2) no longer
  holds once the band is subtracted. It scales with 1/|RD′|, not with the MW it is short, which
  is the price motive's signature. Caveats: the band comes from two seeds, no single year is
  clear of it, and Iberdrola can still move hydro to its own retailer after the auction
  (`rq-midday-hydro.md` §3.8).
- **As a seller, the step follows its position, not its stake.** When Iberdrola is longer at
  cost by 1 GW, its step at cf_s is €6 higher, whatever the slope of its residual demand. That
  fits managing its own book by quantity (keep the water when long) and not a price motive,
  which the seller-side Zb (−0.27, inside the band) rules against.
- **EDP shows neither**: its terms sit on the price-takers.
- So the hydro departures the fixed step finds come down to one firm, Iberdrola, mostly in two
  years. It shades its hydro down as a buyer with the price motive's signature and up as a
  seller with a position effect. The step estimator's dated seller-side departure for all firms
  (2019–2021H1) is not where the fixed step puts it.

## Ten seeds, and Iberdrola's after-auction contracts (2026-10-20)

`fixed_step_test.py --simulated 3 … 10` (eight more seeds, same construction), then
`--band-seed 0 … 10` (every cell for the actual offers and each seed) and `--band-combine` →
`outputs/tables/fixed_step_band_reading.csv` (the reading rule over **ten** seeds: the band is
their min–max). The contracts: `bilateral_hours()` (PDBF role 4 by unit and hour, cached in
`outputs/cache/step/fixed_step_bilateral.parquet`; 27 hydro units, 10–22 TWh a year) and
`routing_cells()`. Logs `.superpowers/sdd/2026-10-19-fixed-step/band_*.log`.

**In one line.** With ten seeds, **the fixed step finds hydro offers indistinguishable from
price-taking in every pooled, period, side and half-year cell except 2023, which is
Iberdrola.** Iberdrola's buyer-hour markdown is mostly hydro moved between its contracts with
its own retailer and the auction. When it buys most, it takes 131 MW out of those contracts and
offers 130 MW more in the auction. Holding that share fixed takes the markdown inside the band.
Two results from the two-seed band are withdrawn: the seller-side departure of 2020H2, and the
"price-motive signature" of Iberdrola's buyer slope.

### What ten seeds change

| cell | actual | band, 2 seeds | band, 10 seeds | gap, bias-adjusted range (10) | differs (10) |
|---|---|---|---|---|---|
| pooled | +0.17 | −0.00 … +0.06 | −0.04 … +0.11 | +0.13 [−0.10, +0.36] | no |
| seller side | +0.05 | | −0.13 … +0.14 | +0.01 [−0.26, +0.35] | no |
| seller side 2019H2 / 2020H1 / 2020H2 | +0.95 / +0.81 / +0.51 | | +0.36…+0.82 / +0.22…+0.63 / −0.26…+0.22 | +0.37 / +0.48 / +0.59 [−0.22, +1.29] | no / no / **no (was yes)** |
| 2023H1 / 2023H2, all firms | +1.07 / +1.75 | | +0.04…+0.42 / −0.14…+0.58 | +0.90 [+0.01, +1.67] / +1.51 [+0.54, +2.53] | yes / yes |
| 2023H1 / 2023H2 without Iberdrola | +0.27 / +1.09 | | +0.01…+0.87 / −0.32…+0.76 | | no / no |
| Iberdrola buyer, Zb alone | +2.00 | +0.52 … +0.59 | +0.13 … +0.79 | +1.55 [+0.40, +2.69] | yes |
| Iberdrola buyer, Zb with n | +1.80 | +0.89 … +0.91 | +0.30 … +1.14 | +1.10 [−0.17, +2.33] | **no (was yes)** |
| Iberdrola buyer, n alone (per GW) | +10.2 | | −0.1 … +2.7 | +8.9 [+1.6, +16.2] | yes |
| Iberdrola seller, n with Zb (per GW) | +6.9 | | −1.3 … +1.4 | +6.8 [+3.2, +10.6] | yes |
| hours the step cannot set the price (at-cost < 0.9 λ*) | +0.27 | | +0.00 … +0.08 | +0.23 [+0.09, +0.38] | yes |
| hours in play (0.9–1.1 λ*) | +0.31 | | +0.05 … +0.19 | +0.20 [−0.03, +0.41] | no |
| ladder at 1.5 cf_s, departure periods | +0.23 | | −0.14 … −0.01 | +0.29 [+0.01, +0.60] | yes |
| placebo, bottom 5%, 2019–2022 | −0.13 | | −0.07 … +0.12 | | no (passes) |
| reactor dose, any term | | | | | no |

With ten seeds the band widens in the finer cells (seller-side half-years up to 0.5 across;
Iberdrola's buyer slope 0.13 … 0.79). Only what is above is clear of it.

### Iberdrola's contracts with its own retailer

Iberdrola delivers 56–82% of its storage hydro schedule bilaterally, every year (EDP 1–8%).
Its buyer hours by fifth of the stake (within unit-month, MW):

| fifth | stake | gap at cf_s (€) | bilateral | offered in the auction | cleared in the auction | total schedule |
|---|---|---|---|---|---|---|
| most buying | −18.9 | −16.3 | **−131** | **+130** | −17 | −148 |
| 2nd | −5.8 | −9.0 | −100 | +92 | +3 | −97 |
| 3rd | −2.5 | −0.2 | −58 | +51 | −3 | −61 |
| 4th | −1.2 | −0.9 | −11 | +7 | +3 | −7 |
| least buying | +0.7 | +2.4 | +13 | −13 | −1 | +13 |

EDP's fifths: bilateral within ±1 MW, offered −5 … +2.

| regression (one pooled regression, firm × side terms) | Iberdrola buyer | price-takers (10) | differs |
|---|---|---|---|
| bilateral share of capacity on Zb | +0.0042 [+0.003, +0.005] (−2.5 points per sd of Zb) | (actual quantities, the same in every seed) | |
| total schedule share on Zb | +0.0031 [+0.002, +0.004] | | |
| gap at cf_s on Zb | +2.00 [+1.19, +2.82] | +0.13 … +0.79 | yes |
| **gap, bilateral share held** | **+0.82 [+0.20, +1.43]** | −0.31 … +0.30 | **no** ([−0.10, +1.75]) |
| 2023: gap / gap, bilateral share held | +2.46 / +0.68 | +0.32…+1.05 / −0.25…+0.40 | yes / no |

- **The hydro is moved, MW for MW.** In the hours Iberdrola buys most, the hydro it would
  deliver to its own retailer under contract (131 MW) is offered in the auction instead (130 MW).
  Little of it clears, so its total hydro schedule falls by about the same amount. EDP, with
  almost no contracts, shows nothing of the kind.
- **That move can make both the stake and the cheap read.** When contract volume leaves the
  bilateral route, Iberdrola's retailer presumably buys that energy in the auction (its retail
  bids were not checked here). Its net position at cost then falls, so Zb is more negative. Its hydro ladder gets longer, so the read at a fixed share
  lands lower. So the slope runs at least partly from the routing to the stake, not from the
  stake to the price.
- **Holding the bilateral share fixed removes 60% of the slope and takes it inside the band**
  (+0.82, against price-takers' −0.31 … +0.30; bias-adjusted [−0.10, +1.75]). In 2023 the slope
  goes from +2.46 to +0.68. The bilateral share is chosen too, up to 13:00 after the auction
  (`rq-midday-hydro.md` §3.8), so this is a decomposition, not a causal estimate.

### Reading

- **At the fixed step, with ten seeds, hydro is price-taking.** Pooled, by period, by side and by
  half-year, every cell sits inside the band except 2023, and 2023 is Iberdrola.
- **Iberdrola's buyer-hour markdown is mostly a routing choice**: hydro moved out of contracts
  with its own retailer and into the auction. That is a choice about where the volume goes, made
  with its retail and generation together. It is not shown to be a price set to lower what it
  pays. What remains with the share held (+0.8) is inside the band.
- **Iberdrola's seller-side position effect survives** (+€6.8 per GW of net sales at cost). It
  follows the MW position, not the stake, so it is book management, not the price motive.
- **The slope in hours where the step cannot set the price** (+0.23 over the band) says part of
  the ladder moves with the stake for reasons a price motive does not give.
- **Open: the step estimator's band rests on two seeds too.** Its dated seller departure (§14–16
  of the simulation note: 2019–2021H1, off from 2021H2) may not survive ten. That needs
  `step_engine.py --sim` for more seeds, which re-clears the market and is the expensive run.
