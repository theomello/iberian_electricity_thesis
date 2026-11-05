# How much of the static gap is the plant's own declared start-up cost? Running note

Written 2026-11-05. Script: `scripts/analysis/startup_cost_correction.py`. Tables:
`outputs/tables/startup_cost_correction*.csv`.

**Why.** Jha & Leslie (SSRN 3603627, summarised in `positioning-vs-jha-leslie.md`) show that a
positive static gap `price − marginal cost` can be start-up cost recovery under perfect
competition, and that it grows with solar. Here the plant states its requirement itself, in
`cab`: a fixed term F (EUR per day) and a variable term V (EUR per MWh) of the minimum-income
condition. The positioning note says to "adopt the correction rather than fight it". This is
that correction, with the data's limits stated.

**A worked example first.** Take a combined cycle that runs one day, sells 3,000 MWh, and
earns 15 EUR/MWh above its fuel-and-carbon cost: static gap `M` = 45,000 EUR. If it declared
F = 9,000 EUR for the day, then 9,000 / 45,000 = 20% of the gap is start-up cost it told the
market it needs, and the gap net of start-up is 12 EUR/MWh. If it also declared V = 8 EUR/MWh
above its fuel cost, a further 24,000 EUR (8 × 3,000) is a *declared* variable cost beyond
fuel (operation and maintenance, start-up spread per MWh, or padding). The rest, 12,000 EUR,
is margin above everything it declared. The minimum-income rule says the sum of the last two pieces
(everything above the declared variable cost) is at least F on any accepted day, so E ≥ 0, which
gives a check on the whole join.

---

## 1. RULES (written before the script was run)

### 1.1 What is computed

Per unit-day `u,d` with cleared sell volume `Q > 0`, with hourly cleared energy `q_h`,
hourly price `p_h` of the unit's own country (`price_es` or `price_pt`), and the bid-time
cost `c` of the day:

- `R = Σ p_h q_h`   revenue at the day-ahead price.
- `M = Σ (p_h − c) q_h`   **static gap** (the repo's static Lerner-style numerator).
- `F` = `min_income_fixed_eur`; `V` = `min_income_var_eur_mwh`.
- **Declaring** = F > 0 or 0 < V < 999 (999 is OMIE's "never"; V = 999 is treated as "V
  unusable", not as a declaration). Rows with a missing F and V (cab header absent) are left
  out of the declaring/non-declaring split and counted.
- **Clean V** = declaring on V, and 0.5 ≤ V / c ≤ 3 (the ivpee_tax_test rule: outside it the
  term is not a cost declaration).

Three quantities per group, always as ratios of sums (volume-weighted), never means of daily
ratios, which explode when M is near zero:

1. `ΣM / ΣQ`   static gap per MWh;  `ΣM / ΣR`   static Lerner-style share.
2. **F-correction**: `ΣF / ΣM` over declaring unit-days with `M > 0`, and `(ΣM − ΣF) / ΣQ`
   over the same days. Also the median daily `F / M` (M > 0), and the share of declaring days
   with `M ≤ 0` or `F > M`.
3. **Declared-cost decomposition** on clean-V days:
   `M = W + F + E`, with `W = (V − c) Q` (declared variable cost beyond fuel and carbon),
   `E = Σ (p_h − V) q_h − F` (margin above everything declared).
   `F / M` is a **lower** bound on the start-up share of the gap: the plant can also fold
   start-up cost into V. `(F + W) / M` is an **upper** bound on the share explained by declared
   cost: W also holds operation and maintenance cost and strategic padding.

### 1.2 Sample

- Units: the 84 in `jrc_cab_match` with a plant-specific efficiency (`eff_is_generic` False):
  44 Spanish and 10 Portuguese combined cycles (gas), 22 Spanish and 6 Portuguese coal
  units. Groups: ES gas, PT gas, coal (both countries; coal's start-up cost is a different
  engineering object and is read apart).
- Days: 2018-01-01 → 2025-03-18 (wide `cab` layout; the SCO lump sum after it is not
  comparable and is left out). Excluded days: 2018-06-14 and 2022-10-12 (the whole-day
  clearing-identity dropouts in CLAUDE.md; a unit's volume could be missing). The 2025
  dropout cluster starts 2025-03-19, after the sample.
- Unit-days without a bid-time cost (the first two days of 2018) are dropped and counted.
- **Cap window.** Gas units: 2022-06-15 → 2023-02-25 (days with a positive subsidy). In this
  window the uncapped cost is not what the plant faces. **Main = bid-time cost
  `marginal_cost_bid_eur_mwh`, window excluded.** Variants: (V2) the same cost, window
  included, to show what it does; (V3) `marginal_cost_subsidised_bid_eur_mwh`, window
  included (cost net of the decree's subsidy; coal keeps its own cost).
- Cleared volume: `curva_pbc_uof` status `C`, side `V`, summed per unit and period, ×
  `resolution_min / 60` (all hourly in this window).

### 1.3 Gates and stops

- **Join gate.** The minimum-income rule says an accepted declaring unit satisfies
  `Σ (p_h − V) q_h ≥ F`, i.e. `E ≥ 0`. On clean-V declaring days with `Q > 0`, E ≥ −100 EUR
  must hold on at least 95% of unit-days. If it does not, volume or price is mis-joined and
  the results are a **stop**, reported as such.
- **Reading bands** for the headline `ΣF / ΣM` (main sample, declaring days, M > 0), per
  year: under 5% the declared fixed term is negligible and the static gap is not start-up
  recovery in the sense J&L need; 5–25% is a partial correction; over 25% large. Fixed here
  so the band cannot move after the number is seen.
- A year with fewer than 500 declaring unit-days in a group is printed but not read.

### 1.4 Selection, reported not corrected

- Declare share of cleared unit-days and of cleared volume, by year and group.
- Static gap per MWh for declaring against non-declaring days (a difference means the
  declaring sample is not the whole fleet's gap).
- Our units' share of all declaring unit-days in `cab` (all units, same window), and the
  daily count of declaring units in `cab`, by year.
- Not-declaring days carry no correction in the data, which does not mean they have no
  start-up cost: they price it in their energy offers (`rq-step-estimator.md` §7). The
  declared correction is a lower bound for the fleet.

### 1.5 The declaration is strategic

F and V are choices (Reguant 2014), not engineering measurements. Every number is a bound on
what the plant says it needs, and a firm can inflate F to raise the price it demands. Nothing
here separates start-up cost from that padding. Comparing F with an engineering start-up cost
(J&L's regression on gas metering) is not possible in Spain.

### 1.6 The solar gradient (description only, no pass/fail)

J&L predict the start-up share of the gap rises with solar. Daily wind plus photovoltaic
share of REE generation (`ree_generation_daily`, excluding the aggregate); terciles within
each year; `ΣF/ΣQ`, `ΣM/ΣQ` and `ΣF/ΣM` by tercile; and a unit-by-year fixed-effect slope of
`F/Q` and `M/Q` on the within-year VRE share, clustered by month. A rising F/Q with a flat M/Q
would fit them; neither moving would not. Read as description: 8 years, one fleet.

### 1.7 What would change the reading

- Join gate fails → stop.
- If `W` is large and F small, the correction depends on whether V is a cost or a markup, which
  this data cannot settle; the answer is then a range, not a number.
- If the cap-window variants move the yearly headline for 2022 or 2023 by more than 5
  percentage points of `ΣF/ΣM`, those two years are read with the variant range, not the main.

---

## 2. Results (run 2026-11-05)

**In one line.** The plant's declared fixed term is **5–13% of the gas plants' static gap in
2019–2024 (23% in 2018)**, €1.4–2.8 per MWh against a gap of €12–30. For Spanish combined cycles it
is **2–5%**, because they declare almost everything in the variable term; for Portuguese ones it is
10–50%. Adding the declared variable term above fuel cost gives an upper bound of 28–70% for gas.
**The gate failed as the rules were written; the numbers below use an amendment (§3) that I
decided after seeing the failure and that the data then confirmed.**

### 2.1 Sample

84 plants (44 ES and 10 PT combined cycles, 22 ES and 6 PT coal), 2018-01-01 → 2025-03-18: 41,786
cleared unit-days. Left out: 52 on the two dropout days, 23 without a bid cost, 5,679 in the gas-cap
window (kept in the variants). Main sample: 36,032 unit-days under the original rules, **32,326
after the amendment**. Of the 36,032 original ones, 31,108 declare, 4,922 do not and 2 have no
cab header.

### 2.2 The join gate: failed as written, and why

Rule 1.3: E ≥ −100 EUR on at least 95% of clean-V declaring days. Result under the original rules:
**91–94% in 2018–2023, 79% in 2024, 81% in 2025: failed.** Per the rule, that is a stop for the
original sample, and its tables are kept as `*_orig.csv` (headline F share for gas in 2024: 15%, not
10%).

The failures are not noise. `startup_cost_correction_short_runs.csv` splits the days by number of
cleared periods:

| cleared periods | starts at period 1 | days | identity holds | F declared (EUR m) |
|---|---|---|---|---|
| 1 | yes | 2,019 | 15% | 57.2 |
| 2 | yes | 385 | 16% | 8.7 |
| 3 | yes | 435 | 7% | 12.2 |
| 1–3, any other start | no | 82 | 89–100% | 0.1 |
| 4 or more | either | 27,374 | **100.0%** | 437.3 |

Every failure is a run of one to three hours at the very start of the day, e.g. Sines 1 and 3 on
2019-06-02, 90 MW for one hour each with F = 80,000 EUR. That is the tail of the
previous day's run (a shutdown ramp): the unit did not start that day, and the minimum-income test
does not bind it as a full day. Their F (78 million EUR) belongs to a start that happened the day
before, so leaving them in overstates F: gas F share in 2024 is 15% with them, 10% without.

### 2.3 Headline: F against the static gap (amended sample, cap window out)

Ratio of sums over declaring unit-days with M > 0. Band rule from 1.3 (under 5%, 5–25%, over 25%).
I read the bands by group and for gas pooled; the pooled "all" row is dominated by coal in 2018–19 and
is in the csv only.

| year | gas gap €/MWh | gas F €/MWh | **gas ΣF/ΣM** | ES gas | PT gas | coal |
|---|---|---|---|---|---|---|
| 2018 | 12.0 | 2.8 | **23%** | 3% | 34% | 28% |
| 2019 | 13.8 | 1.4 | **10%** | 3.5% | 26% | 65% |
| 2020 | 12.3 | 1.6 | **13%** | 4.4% | 25% | not read (gap ≈ 0) |
| 2021 | 22.7 | 1.6 | **7%** | 2.4% | 15% | not read |
| 2022 | 29.5 | 1.8 | **5%** | 3.0% | 10% | not read |
| 2023 | 14.9 | 1.8 | **11%** | 3.6% | 30% | not read |
| 2024 | 21.4 | 2.4 | **10%** | 4.7% | 50% (178 days, not read) | not read |
| 2025 (to 18 Mar) | 36.2 | 3.4 | 9% (184 days, not read) | | | |

- **Spanish combined cycles: under 5% every year.** They declare F on only 12–28% of days; three of
  the largest (Ambiéta, Arcos 3, Campo de Gibraltar 2) never do.
- **Portuguese combined cycles: 10–50%.** They declare F on 72–92% of days and V close to fuel cost
  (median V/c ≈ 1.0), so their declared requirement sits in F. The two countries use the same
  instrument in opposite ways, which is why the pooled gas number moves with the Portuguese weight in
  the sample (70% of 2018's gas days, 17% of 2024's).
- **Coal**: 28% and 65% in 2018–19, then too few days (coal stops running); F per MWh is €4–8. Coal's
  start-up cost is a different object and is not pooled.
- Median daily F/M is between 0 and 4.5% for gas in every year but 2018 (24%), because most days
  declare no F. F exceeds the whole gap on 1–9% of gas declaring days (0–4.5% for Spanish plants).

### 2.4 The declared variable term: an upper bound

Clean-V days, `M = W + F + E`:

| year | ES gas gap | W | F | E | (F+W) / gap, ES | (F+W) / gap, gas pooled |
|---|---|---|---|---|---|---|
| 2018 | 13.9 | 10.8 | 0.4 | 2.6 | 81% | 52% |
| 2019 | 13.8 | 8.6 | 0.4 | 4.7 | 66% | 62% |
| 2020 | 12.9 | 7.5 | 0.6 | 4.9 | 62% | 52% |
| 2021 | 25.2 | 10.4 | 0.6 | 14.2 | 44% | 35% |
| 2022 | 29.7 | 10.6 | 1.0 | 18.2 | 39% | 28% |
| 2023 | 16.4 | 6.8 | 0.6 | 9.0 | 45% | 29% |
| 2024 | 26.1 | 17.8 | 1.2 | 7.1 | 73% | 70% |

Spanish combined cycles declare a variable term 9–29% above fuel and carbon cost (median V/c 1.09–1.29).
In normal years that wedge, not F, is most of the static gap; in the 2021–22 gas crisis the gap
doubles and the wedge does not, so the unexplained margin E reaches €14–18/MWh.

**What W is.** It is not start-up cost alone. It holds operation and maintenance, part-load fuel
use (the implied cost uses full-load efficiency), start-up spread over MWh, and padding. The note
cannot separate these. So the declared-cost share of the Spanish gas gap is a range, **2–5% (F) to
39–81% (F + W)**, and the right statement is the range.

**What E is not.** It is the margin above everything declared, averaged over all hours, including the
many hours the plant is inframarginal and earns the price set by another unit. It is not a markup
and not market power.

### 2.5 Selection

- Declaring is the norm in this sample, 73–97% of gas unit-days and 81–98% of volume, but Spanish
  combined cycles skip it on 17–42% of days (2022: 4%).
- Non-declaring days carry a lower gap in 2018–2020 (ES gas 2018: €6.6 against €13.9) and similar or
  higher later (gas 2021: €25.1 against €22.7). So the declaring days are not a random half of the
  plant's days; the earlier years' gap is higher on the days the plant states a requirement.
- Our 84 plants are 72–88% of all declaring unit-days in `cab` (50–85 declaring units a day across
  all units, falling from 85 in 2018 to 51 in 2025). The thermal fleet is nearly the whole declaring
  population; the selection that matters is within the plant, across days.
- No declaration, no correction in the data. Those days still carry start-up cost, priced into the
  energy offer (`rq-step-estimator.md` §7), so the declared correction is a lower bound for the
  fleet.

### 2.6 The cap window and cost variants

Variant 2 (uncapped bid cost, window included) puts the 2022 gas gap at −€55.6/MWh, which is the
uncapped cost exceeding the price, not a loss; do not read it. Variant 3 (subsidised cost) gives
2022 ΣF/ΣM 3.7% and 2023 12.0%, against 5.4% and 11.3% in the main sample. The largest difference is
1.7 percentage points, under the 5-point trigger in rule 1.7: **the main sample stands.**

### 2.7 The solar gradient (description)

Within each year, by terciles of the daily wind-plus-PV share of generation, gas only:

| year | F share of gap, low → mid → high VRE |
|---|---|
| 2018 | 19% → 24% → 31% |
| 2019 | 8% → 9% → 15% |
| 2020 | 10% → 12% → 19% |
| 2021 | 4.5% → 7.5% → 9.8% |
| 2022 | 3.8% → 5.1% → 9.3% |
| 2023 | 9.8% → 11% → 15% |
| 2024 | 9.8% → 11% → 8.4% |
| 2025 | 9% → 9% → 10% |

Unit-by-year fixed effects, standard errors clustered by month, gas: F per MWh rises **+€0.16 per
10 points of VRE share (t 4–5)**, and the static gap falls **€4.0–4.3 per 10 points (t −7)**. The
rise in the F share inside a year is therefore mostly the gap shrinking at high-VRE days, with F per
MWh rising a little as the plant runs fewer hours. That is the direction Jha & Leslie predict.
It does not show up across years: gas F per MWh is 2.8, 1.4, 1.6, 1.6, 1.8, 1.8, 2.4 in 2018–2024,
and the 2024 reversal in the terciles. Eight years and one fleet.

### 2.8 What failed or is thin

- The gate as written (§2.2).
- Coal is readable in two years. 2025 has 184 gas days and is not read.
- The gate checks the join of volume and price, not the cost c. The cost is the full-load
  engineering figure, and the part-load gap is inside W.
- `cab` after 2025-03-18 (the SCO lump sum, `sco_fixed_eur`) is not used, so the 2025–26 market is
  outside this correction.

---

## 3. Amendments to the rules (made after seeing results)

**3.1 Short runs (changes rule 1.2's sample and rule 1.3's gate).** Original: every unit-day with
Q > 0. The gate failed (§2.2). Diagnosis, from the periods cleared per unit-day: all failures are runs
of one to three periods starting at period 1. Amended sample: drop unit-days with at most three
cleared periods (`SHORT = 3` in the script), 3,706 unit-days of the main sample. The same 95% gate is
then re-run: it passes at 100.0% in every year (clean-V days, and all declaring days with V < 999).
I chose the cut-off from the same table that shows the failure, so the amendment is not independent
of the data; the check that it is the right mechanism is that the identity holds at 100% on every
other bucket, including one- to three-period runs that do not start at period 1. The original
results are kept in the `_orig` files and the difference is reported (2024 gas: 15% against 10%).

**3.2 Pooled gas row and the volume-weighted slope.** Added 'gas' (ES plus PT combined cycles) as a
pooled group after seeing that the 'all' row is dominated by coal in 2018–19, and a volume-weighted
version of the VRE slope after seeing that the unweighted F/Q slope in the first run (before the
amendment) was driven by days with a few MWh. The original thresholds in rule 1.3 are unchanged.

---

## 4. What this means for the paper

1. The fixed start-up term the plants declare is **a small correction to the static gap**: 5–13% of
   it for gas in 2019–2024 (€1.4–2.8 of €12–30 per MWh), 2–5% for Spanish combined cycles.
2. That is a lower bound. Spanish plants declare their requirement in the variable term, and adding
   the declared wedge over fuel cost gives an upper bound of 28–70%; the data cannot say how much of
   it is start-up, operation and maintenance, or padding. Report the range, not a point.
3. After every declared cost, €3–5/MWh remains for Spanish gas in 2018–2020 and €14–18 in 2021–22, but
   it includes inframarginal rent, so it is not a markup.
4. Inside a year the F share rises with VRE, as Jha & Leslie predict, mainly because the gap shrinks;
   across years F per MWh does not rise with VRE. This is the static price-cost gap, not the
   s/η Lerner index of `result-markups-vs-hhi.md`, so the s/η steepening argument is untouched here.
5. Limits: strategic declaration, declaring days selected, 84 plants with a plant-specific
   efficiency, 2018 to 18 March 2025 only, and a gate that failed as written and passed after an
   amendment made with the failure in view.

---

## 5. After 2025-03-19: the SCO lump sum (2026-11-05)

### 5.1 What the SCO term is (scoping, workflow wf_3464975a-9b8; sources below)

From 2025-03-19 the minimum-income condition is the **Scalable Complex Order (SCO)**: one fixed term `Fijoeuro` in EUR
per unit and day (`cab` `sco_fixed_eur`), and the condition (CNMC resolution of 28-02-2025, BOE-A-2025-4908, Anexo 1
§2.2.1; EUPHEMIA public description §5.3.1) is

    Σ_h Σ_k p_h q_hk  ≥  Fijo + Σ_h Σ_k b_hk q_hk

with `b_hk` the offer price of each cleared tranche. There is no V: the variable cost is the price of each step. Plants
now offer their minimum-load block at about €1/MWh (48% of cleared volume on accepted declaring days), so **its fuel
cost has moved into Fijo**. Fijo is therefore neither a start-up term nor a whole-day cost: Spanish gas declares
~€150k a day (0.16× a full day's fuel at full output), Portuguese gas ~€820k (0.9×). Around the switch SAGU2 goes from
F = 0, V = 167.5 to Fijo ≈ €152k; Ribatejo 1 from F = 150,000, V = 125 to Fijo ≈ €943k.

**So the lower bound (F share) is not identified after 2025-03-19**: Fijo − fuel of the minimum-load block reads
0.77 of the gap against 0.05 before, a reshuffle of the declaration, not of behaviour. **Only the upper bound has a
counterpart**: everything declared beyond fuel, `D = Fijo + Σ b q − c Q`, against the old `F + W = F + (V − c) Q`.

### 5.2 RULES — written after the scoping saw the headline (stated, not hidden)

The scoping computed (Fijo + Σbq − cQ)/M ≈ 0.78 before these rules were written, so this is a pre-specified
**reproduction and extension**, not a blind test.

- **Sample.** The same `units()` (82 units in current data: 44 ES gas, 10 PT gas, 28 coal), 2025-03-19 → the last day
  with prices (2026-05-31). Unit-days with a sell `cab` header, `sco_fixed_eur > 0` (declaring) and cleared Q > 0;
  the `SHORT = 3` cut of §3.1 kept. Coal is reported but not read (one unit, two accepted days in the scoping).
- **Tranche prices.** Cleared rows of SCO offers carry −500 (data trap, §5.4), so `Σ b q` is the cleared quantity
  filled up the offered (status O) curve in price order, per unit and period; energy = MW × resolution_min/60.
- **Gate.** `R ≥ Fijo + Σ b q − 100` on ≥ 95% of accepted declaring days, by group; otherwise stop and report.
- **Computed, by group (ES gas, PT gas, gas) and by quarter for ES gas, ratios of sums:** M/Q, `D/M` (the upper bound),
  `Fijo/M` and the slack `(R − Fijo − Σbq)/Fijo` (median), n days, GWh; and the selection table: cleared share and
  GWh on declaring against non-declaring unit-days.
- **Comparison.** `D/M` against the pre-switch `(F + W)/M` (ES gas 2024 0.73, 2025 to 03-18 0.74). Reading: within
  ±0.10 = "the declared requirement explains the same share of the gap across the switch"; otherwise report the
  difference. No lower bound is quoted after the switch.
- **Outputs.** `outputs/tables/startup_cost_correction_sco.csv`, `..._sco_selection.csv`; `--sco` stage of the script.

### 5.3 Results (run 2026-11-05, `--sco`)

| group | accepted declaring days | GWh | gap €/MWh | **D / M (upper bound)** | gate | slack (median) |
|---|---|---|---|---|---|---|
| ES gas | 294 | 840 | 31.4 | **0.785** | 100% | 8.6% of Fijo |
| PT gas | 9 | 60 | 32.9 | 0.853 | 100% | 6.5% |
| gas | 303 | 899 | 31.5 | **0.790** | 100% | 8.4% |
| coal | 2 | 7 | −68.9 | not read | | |

ES gas by quarter: 2025Q2 0.80, Q3 0.75, Q4 0.80, 2026Q1 0.85 (16 days). Offered curve covers the cleared quantity in
100% of periods.

- **Reading, by rule 5.2: the declared requirement explains the same share of the gap across the switch.** 0.785
  against 0.73 (2024) and 0.74 (2025 to 03-18) for Spanish gas, within ±0.10.
- **The gate binds tightly** (median slack 8.6% of Fijo): plants set Fijo close to what the day pays. That is what a
  strategic declaration looks like, which is why D is an upper bound, not a cost.
- **Selection is much harsher than before.** Declaring Spanish gas unit-days clear 4.5% of the time against 14.5% for
  non-declaring ones; 840 of 3,680 GWh of Spanish gas output. Portuguese gas: declaring days clear 0.4%. 18 Spanish
  combined cycles never declare an SCO.
- **No lower bound after 2025-03-19** (§5.1). The paper's "5–13% (lower bound) to 28–70% (upper bound)" range holds to
  2025-03-18; after it, only the upper bound, ~0.79, on a thin and selected sample.

### 5.4 Data traps found

- **Cleared (C) bid rows of SCO offers carry −500 €/MWh, not the step price.** 100% of 7,423 cleared rows of declaring
  thermal units in July 2025 (96% in January 2026); 19–36% of non-declaring ones. Before 2025-03-19 cleared rows carry
  real prices. Take step prices from the offered (O) curve.
- **`offer_type` in the bid parquet is empty until 2025-12 and filled from 2026-01** (`S`, `C01`, `C02` = SCO, `C04`).
  Whether the raw files carry it earlier and the parser drops it is not checked.

Sources: OMIE file spec v1.37 (pp. 25, 27–28), https://www.omie.es/sites/default/files/2025-09/formato_ficheros_inf_pub_137.pdf;
CNMC resolution 28-02-2025 (BOE-A-2025-4908), https://cnmc.es/sites/default/files/5813806.pdf; EUPHEMIA public description
(NEMO Committee, Dec 2025), https://www.nemo-committee.eu/assets/files/euphemia-public-description.pdf.
