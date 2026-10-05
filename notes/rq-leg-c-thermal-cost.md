# Leg C — thermal plant, cost observed

Framework spec §4, leg C. Run 2026-10-01 on branch `leg-c`.
Scripts: `build/build_rival_solar.py` (`--tech wind` and `--tech solar`),
`analysis/iv_two_endog.py`, `analysis/leg_c_panel.py`, `analysis/leg_c_test.py`;
checks in `qa/` (`check_rival_solar.py`, `check_iv_two_endog.py`,
`check_leg_c_panel.py`). Results: `outputs/tables/leg_c_results.csv`.

**Resolved 2026-10-05 (§6): β ≈ 3 is not conduct.** The other owners' plants,
whose X does not move, show the same fall in p − c as the five firms' when rivals'
renewables rise. The price falls down the merit order for every plant, and the
condition reads that fall as a change in markup. Conduct has to be read from the
firms' own offers, net of price-takers' offers (leg D §7 does this: β 0.024).

**In one line.** The condition in levels gives β ≈ 3, three times full Nash.
That rejects a joint hypothesis, not conduct alone, and the leading candidate
for the failure is that the price sits inside the gaps of the units' stepped
offers, where the smooth condition need not hold period by period. Where the
unit's own step sets the price, solar alone gives β 0.89 and does not reject
β = 1, but both instruments together give an empty set, those rows are
selected on the price, and in levels they sit about 8 €/MWh above what β ≈ 0.9
predicts. Leg C has no estimate of β yet.

## 1. Design, as run

For each gas or coal unit at its own margin:

```
p_t − c_ut = a_u + β · X_ft + ε_ut
```

- **The margin.** The unit is partly dispatched in period t (some offered
  volume cleared, some not), and cleared in the UTC (Coordinated Universal
  Time) periods just before and after, so any start-up is sunk. A firm with two
  units at its margin contributes both. Clean periods only (no ES–PT market
  split, clearing identity holds; `firm_x.clean`). 2018–2023.
- **Owner.** The unit's dated owner (the nearest preceding OMIE listing, the
  majority owner), with two dated overrides: Repsol from 2018-11-02 (Viesgo)
  and TotalEnergies for Castejón 1 and 3 from 2020-12-01. A unit-period is kept
  only when its dated owner is the static owner its firm's X is built on.
- **c** is the implied marginal cost: fuel price over JRC (Joint Research
  Centre) efficiency plus carbon; from 2022-06-15 the gas-capped cost.
- **X** = n / |RD′|: the firm's exposed net position (`net_exp_mw`, §2.4) over
  rivals' residual-demand slope within ±5 €/MWh, own offers removed
  (`slope_exp_h5`, `firm_incentive_net`), defined where that slope is at least
  5 MW per €/MWh. In €/MWh, so β = 1 is full supply-function Nash.
- **Instruments.** Rivals' offered wind (zw) and solar (zs) for the firm, in GW
  (`rival_wind.parquet`, `rival_solar.parquet`). One regressor, two
  instruments.
- **a_u** is a unit effect. Errors clustered by ISO week. Weak-instrument-robust
  inference: Anderson–Rubin (AR) tests of β = 0 and β = 1 and the exact AR set
  (a χ²(2) set; its minimum p is printed).
- **Three specifications.**
  1. **Cost imposed**: units with a plant-specific JRC efficiency.
  2. **Heat rate estimated**: p = a_u + h_u · fuel_index + β · X, all units.
     Validation: for gas units with a plant-specific efficiency, h_u · eff
     should be near 1 (median within [0.85, 1.15], at least half within ±20%).
  3. **Route 3**, the check: p minus the declared minimum-income variable term
     (`cab`), declaring units.
- **Headline samples leave out minimum-load gaps**: unit-periods whose cleared
  volume is all priced at or below 5 €/MWh, where p sits above a near-zero
  tranche (62,203 unit-periods, 15.2%). One robustness row keeps them.

## 2. Sample

409,426 unit-periods on 71 units and 311 weeks; 347,223 outside minimum-load
gaps. Specification 1: 335,545 unit-periods on 67 units (45 gas, 22 coal).

The full panel by year and fuel (minimum-load and generic-efficiency rows
included):

| year | coal | gas |
|---|---|---|
| 2018 | 64,018 | 18,922 |
| 2019 | 13,859 | 74,801 |
| 2020 | 3,261 | 48,540 |
| 2021 | 3,524 | 40,254 |
| 2022 | 6,668 | 96,964 |
| 2023 | 164 | 38,451 |

By firm (all rows): Endesa 100,275; Naturgy 94,991; Iberdrola 67,032; Repsol
35,165; EDP 29,222; Cepsa 28,948; Engie 21,414; TotalEnergies 12,670; Bahía de
Bizkaia 10,777; RWE 6,454; Axpo 2,470; Cogen 8.

- 95.2% of rows carry a plant-specific efficiency; 87.9% declare a variable
  term.
- **Dropped**: unit-periods outside their firm's static X (Amorebieta/Bizkaia
  14,940; Castejón 1 and 3 under EDP 6,336 and 5,305; Plana del Vent 1 under
  RWE's group, before the 2019-07-18 listing, 4,326); Repsol before 2018-11-02 (1,252); X undefined because rivals'
  slope is below 5 MW per €/MWh (127).
- In specification 1, the firm is a net buyer (X < 0) in 53.6% of rows.

## 3. Results

### 3.1 As designed

| sample | spec | n | β (se) | F | AR p(β=0) | AR p(β=1) | AR set | status |
|---|---|---|---|---|---|---|---|---|
| **pooled** | 1 | 335,545 | 3.103 (0.218) | 70.1 | 7·10⁻²⁶ | 2·10⁻¹⁵ | [2.587, 3.665] | ok |
| gas | 1 | 257,661 | 3.695 (0.288) | 56.5 | 3·10⁻²² | 1·10⁻¹⁴ | [3.187, 4.228] | ok |
| coal | 1 | 77,884 | 1.362 (0.320) | 51.8 | 5·10⁻⁶ | 0.003 | empty (min p 0.008) | ok |
| 2018–2021 | 1 | 218,500 | 2.054 (0.298) | 35.3 | 2·10⁻⁷ | 0.003 | [1.326, 2.442] | ok |
| 2022–2023 | 1 | 117,045 | 3.354 (0.265) | 57.8 | 2·10⁻³⁹ | 5·10⁻²⁴ | [2.833, 4.088] | ok |
| five firms | 1 | 262,825 | 2.314 (0.190) | 72.6 | 2·10⁻²⁶ | 5·10⁻¹³ | [2.110, 2.749] | ok |
| other owners | 1 | 72,720 | −17.7 (10.6) | 3.1 | 2·10⁻²¹ | 4·10⁻²² | [98.7, 268.2] | weak |
| without Axpo, Engie | 1 | 314,389 | 2.799 (0.213) | 69.7 | 8·10⁻²⁷ | 3·10⁻¹⁵ | [2.407, 3.347] | ok |
| without static-X misfits | 1 | 308,332 | 3.173 (0.216) | 66.6 | 4·10⁻²⁹ | 5·10⁻¹⁸ | [2.677, 3.751] | ok |
| with minimum-load gaps | 1 | 389,788 | 2.925 (0.178) | 100.2 | 6·10⁻²⁷ | 1·10⁻¹⁵ | empty (0.008) | ok |
| **pooled** | 2 | 347,184 | 3.060 (0.209) | 65.0 | 4·10⁻²³ | 6·10⁻¹⁴ | [2.550, 3.597] | ok |
| **pooled** | route 3 | 311,844 | 3.049 (0.243) | 50.4 | 3·10⁻²⁶ | 2·10⁻¹⁸ | empty (0.028) | ok |

F is the first-stage F. "Without static-X misfits" drops EDP and TotalEnergies
before 2020-12-01 and Naturgy before 2019-07-18.

**Specification 2's validation.** h_u · eff has median 1.058, and 0.67 of the
45 gas units lie within ±20%: VALIDATED by the plan's rule. But the rule cannot
see an error in one unit's efficiency. Every gas unit's fuel_index is the same
gas index on a given day, so h_u is the price's pass-through of that index, and
shuffling the efficiencies across units scores 0.69 (median of 200
permutations). The rule fails only for a common bias. So it validates the gas
cost **level**. Coal is not validated: the same recovery gives a median h_u · eff
of 0.615 over 20 units, 0.20 within ±20%. Coal is 23% of specification 1.

**The markdown in levels** (specification 1), with p − c split at the unit's
highest cleared offer step ("top"):

| | n | median p − c | share p < c | median p − top | median top − c | share top < c |
|---|---|---|---|---|---|---|
| X < 0 (net buyer) | 179,761 | +14.05 | 0.095 | +10.63 | +2.87 | 0.411 |
| X > 0 (net seller) | 155,782 | +16.28 | 0.070 | +22.85 | +1.00 | 0.480 |
| at minimum-load gaps, X < 0 | 32,403 | +4.33 | 0.351 | +54.01 | −55.16 | 1.000 |
| at minimum-load gaps, X > 0 | 21,840 | +10.43 | 0.180 | +57.28 | −47.51 | 1.000 |

### 3.2 The leading candidate for β ≈ 3: the price sits in a gap of the unit's step curve

The unit offers in steps. At a partly dispatched unit, p rarely sits on the
unit's own offer:

- **p is within 0.005 €/MWh of the unit's top cleared step in 1.4% of rows.**
  The median p − top is 13.41 €/MWh. In July 2019 (the Task 4 review's scratch
  script, not committed; one month of offer steps), 1.1% of rows have volume
  offered at p, the median gap from
  the top cleared step to the next offered step is 123.9 €/MWh, and p sits a
  tenth of the way up it.
- **β splits exactly** (p − c = (p − top) + (top − c), same first stage):
  2.251 from p − top (AR set [2.101, 3.040]) and 0.853 from top − c (AR set
  empty). Three quarters of β is the price's distance above the unit's own
  accepted offers. The split is an identity, and "top" is itself a function of
  p, so it shows where β sits, not why.
- **What moves.** Reduced forms, per GW of rivals' solar (unit effects): p falls
  2.09 €/MWh (se 0.46) and p − c 2.00; the firm's exposed n falls 91 MW, and X
  only 0.64 €/MWh (se 0.06), so 2.00 / 0.64 ≈ 3.1. Wind gives the same n
  (−91 MW) and X (−0.68). X's movement comes mostly from the low-slope tail:
  91 MW over the median rivals' slope (470.5 MW per €/MWh) is only 0.19, while
  the mean of 1,000 / slope is 5.12 against 1,000 / median slope 2.13. That
  convexity is also why β rises with the slope floor (§3.3).
- **Why this need not be conduct, and why it need not be exclusion failure
  either.** A step bidder chooses each step's length as well as its price. In
  the periods where p falls in the gap above step k, the optimal length
  satisfies the smooth condition in expectation (Kastl 2011):
  E[(p − c − β · X) · 1{p in the gap above k} | information at bidding] = 0. So
  instruments the firm knew when it bid, as rivals' offered renewables largely
  are (they are submitted at the same noon deadline), remain valid over the gap
  periods. The condition breaks for the unforeseen part of the instruments, for
  step lengths fixed by technology (minimum load, capacity), and where the unit
  is in a gap but the **firm** is not: the condition is the firm's, and in July
  2019 another unit of the same firm offers within ±0.5 €/MWh of p in 42.1% of
  panel rows (final review's scratch script, not committed). The step gap is the
  leading candidate, not an established cause. β ≈ 3 rejects the joint
  hypothesis: Nash, freely chosen step lengths, foreseen instruments, X and c
  measured correctly, and the unit being the firm's marginal unit.
- **Where the unit's own step is at p** (p − top ≤ 0.5 €/MWh, 13,515 rows):

  | instruments | β (se) | F | AR p(β=1) | AR set |
  |---|---|---|---|---|
  | wind and solar | 0.869 (0.215) | 15.9 | 8·10⁻⁶ | empty (min p 0.0003) |
  | solar alone | 0.894 (0.219) | 29.0 | 0.651 | [0.554, 1.517] |

  With both instruments, the specification the plan defines, the AR set is
  empty and β = 1 is rejected. Solar alone was run after that set came back
  empty; it does not reject β = 1. Wind alone has no first stage here (F 1.2)
  and its AR set excludes solar's estimate (final review's scratch script). The
  rows are selected on p, the outcome, so this is a diagnostic, not an
  estimate. **In levels**, at solar's β of 0.894 the unit effects absorb a
  median +8.31 €/MWh (interquartile range +4.82 to +14.61, 63 units): the rows
  sit about 8 €/MWh above the condition's prediction, unless the omitted costs
  (operation and maintenance, part-load efficiency, start-ups) are that large.
  β ≈ 0.9 there is a within-unit slope, not a fit in levels.

### 3.3 What else moves β

| check | β (se) | F | AR set |
|---|---|---|---|
| wind alone | 3.067 (0.486) | 25.9 | [2.157, 4.238] |
| solar alone | 3.124 (0.284) | 137.1 | [2.597, 3.727] |
| coal, wind alone | −0.483 (0.562) | 34.2 | [−1.587, 0.754] |
| coal, solar alone | 2.554 (0.464) | 80.4 | [1.632, 3.497] |
| route 3, wind alone | 2.035 (0.307) | 19.8 | [1.522, 2.912] |
| route 3, solar alone | 3.924 (0.366) | 95.1 | [3.266, 4.738] |
| 2018 | 0.567 (0.435) | 65.5 | empty |
| 2019 | 1.831 (0.670) | 76.5 | empty |
| 2020 | 0.747 (0.568) | 67.7 | empty |
| 2021 | 3.132 (0.425) | 31.4 | [2.419, 4.326] |
| 2022 | 3.265 (0.268) | 71.0 | [2.663, 3.869] |
| 2023 | 4.740 (0.827) | 30.0 | [3.300, 7.716] |
| unit + year-month effects | 3.421 (0.202) | 81.4 | [2.934, 3.923] |
| rivals' slope ≥ 20 | 3.409 (0.249) | 86.0 | [2.805, 4.043] |
| rivals' slope ≥ 50 | 4.224 (0.330) | 109.7 | [3.469, 5.051] |
| rivals' slope ≥ 100 | 5.433 (0.460) | 117.3 | [4.651, 6.356] |
| X = n / median slope (n moves) | 10.47 (1.14) | 295.3 | [7.674, 13.251] |
| X = firm-mean n / slope (slope moves) | −19.1 (5.8) | 7.9 | empty |

- **The two instruments agree pooled but not within years**: the AR set is
  empty in 2018, 2019 and 2020, and for coal and route 3 wind and solar give
  different βs.
- **β is not a stable parameter of X.** It rises with the slope floor (the
  low-slope tail, where X is largest, pulls it down), it is about 10 when only n
  moves, and negative and weak when only the slope moves. A conduct parameter
  would not depend on which part of X moves.
- **Not the half-width of rivals' slope.** At ±1, ±2, ±5 and ±10 €/MWh β is
  3.03, 3.04, 3.10 and 3.21.
- **Time effects raise β** rather than lower it. Clustering by month instead of
  week lowers F to 36.6 and widens the AR set to [2.34, 3.81] (Task 4 review's
  scratch script, not committed).

## 4. Verdict

The plan's rules (Task 5, Step 1), applied to the pooled rows:

| rule | result |
|---|---|
| 1. Specification 1 trusted (specification 2 validated)? | yes by the rule, but the rule checks only the gas cost level; coal fails it |
| 2. Readable 2SLS (two-stage least squares; F ≥ 10)? | yes: F 70.1, 65.0, 50.4 |
| 3. Price-taking not rejected (AR p(β=0) ≥ 0.05)? | rejected in all three (p ≤ 4·10⁻²³) |
| 4. Full Nash not rejected (AR p(β=1) ≥ 0.05)? | rejected in all three (p ≤ 6·10⁻¹⁴) |
| 5. Conduct between the two (AR set inside (0, 1))? | no: [2.587, 3.665] and [2.550, 3.597] lie above 1 |
| 6. Markdown in levels (median p − c < 0 for X < 0, > 0 for X > 0)? | fails for buyers (+14.05), holds for sellers (+16.28) |
| 7. Route 3 agrees (AR sets overlap)? | no: route 3's AR set is empty |

**Read mechanically, leg C rejects both price-taking and full Nash, with β
above 1. In conduct terms β > 1 is the more-than-Nash region: firms acting as
if their residual demand were steeper than it is, which is how coordination
would show (Puller 2007 reads θ > 1 the same way). That reading is set aside
here, not adopted, for three reasons.** β is not stable to which part of X
moves (10.5 with n alone, negative with the slope alone), to the slope floor
(3.1 to 5.4) or across years (AR sets empty in 2018–2020); wind and solar give
different βs for coal and route 3; and the price sits inside a gap of the
unit's step curve in nearly every row, where the smooth condition holds only in
expectation over gap periods and fails for unforeseen shocks and fixed step
lengths. β ≈ 3 rejects the joint hypothesis, not Nash conduct by itself.

**What leg C says about β: nothing yet that is an estimate.** At the rows where
the unit's own step sets the price, β is 0.87 with both instruments (AR set
empty, β = 1 rejected) and 0.89 with solar alone (β = 1 not rejected), but those
rows are selected on p and sit about 8 €/MWh above the condition in levels. The
markdown in levels runs against the prediction: at the unit's own top step the
median markup is +2.87 €/MWh for net buyers (median X −2.37) and +1.00 for net
sellers (median X +1.53), and sellers' top steps lie below the measured cost
more often (48% against 41%). Net buyers are not seen pricing below cost; with
an engineering cost that omits operation and maintenance, part-load efficiency
and start-ups, that is not evidence against it either.

**What it would take.** The conditions of a step bidder, estimated on the offer
steps rather than on p (spec §8 step 5b): for each step's price, the moment
E[1{step k sets the price} · ((b_k − c) · |RD′| − β · n)] = 0, so that
b_k − c = β · E[n | k] / E[|RD′| | k], a slope-weighted mean of X; and for each
step's length, Kastl's moment over the gap periods above. The expectations come
from resampling residual demand (Wolak 2007; Reguant 2014, who also puts the
minimum-income condition and start-up costs into the bidder's problem, as this
market's offers do). Steps that never set the price, minimum-load tranches and
withholding blocks, give inequalities only.

## 5. Limits

- **The condition is for smooth supply functions; the offers are steps** (§3.2).
  It holds over the gap periods only in expectation, so every row above tests
  it jointly with foreseen instruments and freely chosen step lengths.
- **X is built on static unit owners** (`firm_incentive_net`). Unit-periods
  outside their firm's X are dropped, but each firm's X itself still counts
  sold or bought units on one owner: EDP's X excludes Castejón (sold
  2020-12-01) and its NATVD wind before 2020-09, TotalEnergies' includes them;
  Naturgy's counts Plana del Vent 1 before the 2019-07-18 listing, which first
  shows it under Gas Natural (the 2018-08-03 listing still shows Alpiq, grouped
  with RWE here), and RWE's leaves it out. The "without static-X misfits" row
  drops the Naturgy and EDP/TotalEnergies periods (β 3.17), but not RWE's 626
  Plana del Vent 2 rows before 2019-07-18.
- **Axpo and Engie bid mostly for farms they represent**, so their X is mostly
  third parties' volume; without them β is 2.80.
- **Rivals' offered renewables are partly a choice.** Offered volume is not
  weather; spec §8 step 6 queues a weather-at-site instrument.
- **Selection on partial dispatch.** The sample is periods in which a unit is
  at its margin, which depends on the price.
- **Cost.** The implied cost omits O&M (absorbed by a_u if constant),
  start-ups beyond t ± 1, and part-load efficiency; it uses the delivery day's
  closing fuel and carbon prices, not the prices known at the D−1 auction. Coal
  uses the API2 Rotterdam import price. From 2022-06-15 to 2023-12-31 gas is
  valued at the gas cap's reference price, and coal is never capped.
- **Specification 2 validates only the gas cost level** (§3.1), so a
  unit-specific efficiency error in specification 1 is not ruled out.
- **Ramp-constrained rows** (870, mostly EDP's: in-the-money volume left
  uncleared, or cleared volume priced above p) are kept.

## 6. Why β exceeds 1, and what replaces it (2026-10-05)

Numbers in this section are from the rerun on owners by date (2026-10-03; pooled
β 3.09). Script: the diagnostics of `analysis/leg_c_test.py`; one-off checks in
`.superpowers/sdd/2026-10-05-beta-diagnosis/` (not committed).

### 6.1 The cause: the price falls for every plant

c is the cost of the plant in the row; the price is set by another plant in 98.6%
of rows. When rivals' wind or solar rises, a cheaper plant sets the price and p − c
falls for every plant, whether its firm has a stake in the price or not. The
instrument is meant to move p − c only through X. This second path breaks that.

Reduced forms per GW of rivals' wind / solar (unit effects, week clusters):

| | p − c (€/MWh) | X (€/MWh) | n (MW) | the unit's cleared share (pp) |
|---|---|---|---|---|
| five firms' plants | −1.77 / −2.13 | −0.91 / −0.86 | −128 / −126 | −0.43 / +0.17 |
| other owners' plants | **−2.56 / −1.31** | **0.00 / −0.02** | −6 / +2 | −1.09 / −0.05 |
| all | −2.00 / −1.88 | −0.63 / −0.62 | −90 / −88 | −0.61 / +0.15 |

The other owners are Cepsa, Engie, TotalEnergies, Bahía de Bizkaia, RWE and Axpo.
Their X does not move; their p − c falls as much as the five firms'. With any β
between 0 and 1 it could not move at all. The size matches the merit order: 1 GW
over the median rivals' slope (504 MW per €/MWh) is 1.98 €/MWh.

**β is then a ratio of two slopes, not conduct.** β̂ = Δ(p − c)/ΔX. With n alone
moving, ΔX = Δn/|RD′|, so β̂ = |RD′| · Δp/Δn: rivals' slope over the firm's own
response to the price. The firm's n moves 52–58 MW per €/MWh, about 9% of each GW;
504/52 ≈ 9.7, and the estimate with n alone is 10.9. This is the identification
problem of Bresnahan (1982): a shift of residual demand alone cannot separate
conduct from the shape of the curve the firm is moved along.

**The step gap of §3.2 is the same thing seen from one plant.** A plant whose
offers are unchanged can see p − c fall by the whole price movement while its own
output stays put (the other owners' cleared share barely moves with solar).

### 6.2 Fixes tried on the price outcome, none of which works

| attempt | β | why it fails |
|---|---|---|
| a cost slope in the unit's load, pinned by the other owners | 2.44 [2.08, 2.80] | their price moves at an unchanged load: not a cost curve |
| rows where the unit's own step sets p, D-1 forecasts as instruments | 1.42, AR set empty | the other owners' offer − cost still falls 1.7–2.2 €/MWh per GW: a lower step of the same ladder sets p |
| the step condition in product form, (b − c)·\|RD′\| = β·n | 3.5–10.7 | same |
| date × period effects | 0.51 [0.12, 1.26] | with p absorbed, only fuel price × efficiency and which units are marginal remain: not conduct |

### 6.3 What replaces it

A parameter that differs by firm must be read from an outcome that differs by
firm: the firm's own offers, compared with price-takers' offers facing the same
shock, with instruments known when offers are submitted. Leg D §7 is that design
(offer shape, unit × day effects, D-1 forecasts, net of the other owners'
response): β 0.024 (F 60, overidentification p 0.92); leg A gives 0.03–0.14.

Leg C's own contribution, the observed cost level, comes back by putting the
offers on the left: the unit's offer price at fixed points of its ladder minus c,
for all offered units (no selection on being at the margin), the other owners'
gas and coal plants on the same day as the benchmark, D-1 forecasts as
instruments. The built-in test is that the other owners' own β is about 0. The
main threat is the benchmark (more gas, less coal, REN Trading's legacy contracts,
Axpo and Engie bidding for third parties), not the cost panel: constant cost errors
fall into unit effects and common daily ones into the comparison. Cost matters for
the markup level; using D-1 fuel and carbon prices and JRC's Portuguese plants are
the cheap improvements.

**The β ≈ 3 stays as a result:** a conduct test with the market price as its
outcome would, in this market, wrongly find more-than-Nash conduct.
