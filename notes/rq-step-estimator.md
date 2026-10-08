# The step estimator: β from the conditions of a step bidder

Framework spec §9.7 step 6; design in `docs/specs/2026-10-01-step-offer-design.md` §3.
Run 2026-10-06. Scripts: `analysis/step_curves.py` (re-clearable curves by hour),
`analysis/step_engine.py` (resampled residual demand), `analysis/step_estimator.py`
(moments and estimates). Results: `outputs/tables/step_estimator_results.csv`; rows
`step_estimator_rows.parquet`; caches in `outputs/cache/step/` (gitignored). Logs:
`.superpowers/sdd/2026-10-06-step/`.

**In one line.** On the steps that set the price, β is close to 0: +0.07 with
reactor outages as instruments (95% set −0.68 to 1.01), and −0.16 (set −0.60 to 0.19)
in 2019 – mid-2021, where the instrument is strongest (F 23) and full Nash is
rejected. The step-length conditions fail, which says the lengths are set by the
plants, not chosen.

**Added 2026-10-07 (§7).** An instrument built from the model, X̃ on the curve the firm
would offer at cost, is strong (F 200–700) and rejects full Nash in every
specification: β −0.08, set [−0.19, 0.02], with unit × day effects. Its sign moves with
the fixed effects (−0.27 to +0.10 on all years), so it settles the upper bound, not the
sign.

## 1. The idea, with an example

A gas plant offers its first 200 MW at €60 and the next 100 MW at €90. It does not
know tomorrow's residual demand when it bids. Some days its €60 step sets the price;
on others the price lands between €60 and €90, set by a rival.

- **Price of a step.** On the days the €60 step sets the price, raising it by €1
  earns €1 on every MW the firm is net long and loses the MW that rivals take
  instead. The firm stops where those balance: €60 − cost = β × X̃, where X̃ is the
  firm's position over rivals' slope, averaged over the days that step sets the
  price (weighted by slope: X̃ = Σ n / Σ |RD′|).
- **Length of a step.** On the days the price falls in the €60–90 gap, adding one MW
  to the €60 step earns the price minus cost and lowers the price on everything the
  firm sells: the average gap price − cost = β × average X.

Both conditions hold in expectation over the residual demands the firm could face
(Kastl 2011; Wolak 2007; Reguant 2014). So the estimator needs that distribution,
and needs to know which step clears in each.

## 2. What was built

**Curves that re-clear.** Clearing OMIE's offered curves does not reproduce the price.
In June 2019 it comes out €13 too low, for two reasons found in the files:

- units withdrawn by their minimum-income condition stay in the offered curve: about
  9 GW an hour of sell offers below the price are not accepted, 93% of them from units
  accepted in no hour that day, all of which declare the condition;
- the flow with France under market coupling (unit `MIEU`) appears only among the
  accepted rows.

So each side's curve takes the accepted rows on the accepted side of the price and
the offered rows at and beyond it. Over 2019–2023 that reproduces the published price
exactly in 61–97% of hours a month and within €0.50 in 80–99.6%. An hour is used
(`valid`) when it is unsplit, the clearing identity holds and the re-clear is within
€0.50: 79–99.5% of hours a month.

**Residual demand by resampling.** For each firm that owns a gas or coal unit with a
plant-specific efficiency (13 groups) and each valid hour:

- **Draws:** 40 hours at the same clock hour within ±28 days (the hour's own day left
  out), nearest in REE's day-before forecast of net load.
- **Rivals' curve:** each draw hour's curve minus the firm's own offers in it, shifted
  sideways to the target hour's forecasts. The shift counts only rivals' demand and
  rivals' wind and solar, net of the firm's own shares.
- **Clearing:** the firm's actual curve against each draw's rivals, which gives the
  price, the firm's net position n, rivals' slope |RD′| (MW within ±€5) and X.
- **Events:** each of the firm's price points either sets the price, or has the price
  fall in the gap above it.
- **Check:** clearing against the hour's own rivals reproduces the re-cleared price in
  90–100% of firm-hours by month; the rest differ by rounding at ties (median €0.12).

297,712 firm-hours, 3.2 million gas and coal steps.

The draws are centred close to the actual price in calm months (mean draw price minus
actual within ±€3 in 2019–2020). From August 2021 they spread by €12–67, because a
±28-day window mixes gas prices.

**Estimating equation (price of a step).** For each step that sets the price in at least
one draw (228,090 unit-steps, 78 units):

    b_k − c_u = β · X̃_k + unit × month + fuel × date × hour + fuel × ladder position

- c_u is the implied cost, using fuel and carbon prices known when offers close, with
  the gas cap applied.
- Ladder position is the decile of the step within the unit's capacity. These effects
  net out the ladder that price-takers also offer (framework §9.1).
- Weights: the number of draws in which the step sets the price. Week clusters.
- X̃ is undefined where rivals' mean slope over those draws is below 20 MW per €/MWh
  (5 and 50 as checks). At the €150–300 prices of 2021–2023 the ±€5 band is thin: the
  median slope is 76–190 there, against 450–485 in 2019–2020.

**Instruments.** X̃ depends on the step's own price, since a higher step sets the price
in tighter draws. An unmeasured cost would raise both. So X̃ is instrumented by the
firm's planned and unplanned reactor outages (GW, by share).

- An outage lowers the firm's n and so its X̃: −3.3 (se 1.7) per GW unplanned and
  −6.3 (1.5) planned. In 2019 – mid-2021 the figures are −3.1 (0.9) and −2.8 (0.4).
- Only Endesa, Iberdrola, Naturgy and EDP own reactors, so the outages identify β
  from those four firms against the rest.

## 3. Results

**Price of a step** (β = 1 is full Nash; F is the first-stage F):

| sample | least squares | β (2SLS) | se | F | 95% set (Anderson–Rubin) | p(β = 0) | p(β = 1) |
|---|---|---|---|---|---|---|---|
| **all, outages** | +0.14 | **+0.07** | 0.31 | 9.9 | **[−0.68, 1.01]** | 0.41 | 0.053 |
| + regional wind | | +0.07 | 0.31 | 6.7 | [−0.90, 1.23] | 0.53 | 0.12 |
| fuel × date and hour effects | +0.18 | −0.11 | 0.32 | 8.9 | [−1.13, 0.74] | 0.94 | 0.014 |
| no ladder effects | +0.20 | +0.03 | 0.33 | 9.2 | [−0.79, 0.98] | 0.30 | 0.047 |
| slope floor 5 | +0.08 | +0.00 | 0.23 | 9.6 | [−0.56, 0.69] | 0.76 | 0.009 |
| slope floor 50 | +0.23 | +0.28 | 0.37 | 17.2 | [−0.23, 1.34] | 0.19 | 0.19 |
| \|X̃\| ≤ 30 | +0.25 | +0.16 | 0.46 | 18.5 | [−0.51, 1.48] | 0.51 | 0.25 |
| gas only | +0.15 | +0.06 | 0.32 | 9.6 | [−0.72, 1.03] | 0.40 | 0.058 |
| **2019 – 2021 H1** | +0.27 | **−0.16** | 0.16 | **22.6** | **[−0.60, 0.19]** | 0.52 | 2·10⁻⁷ |
| 2021 H2 – 2023 | +0.11 | +0.07 | 0.37 | 8.0 | [−0.82, 1.37] | 0.41 | 0.14 |
| five firms only | +0.16 | −0.00 | 0.20 | 7.7 | [−0.55, 0.65] | 0.93 | 0.010 |
| other owners only | +0.51 (se 0.15) | — | | | | | |

Regional wind alone has no first stage here (F 0.1).

**The least-squares slope is not conduct.** It is positive for every group, and largest
for the other owners (+0.51). Their X̃ is near 0 and they have no stake in the price.
That is the mechanical link: a high-priced step sets the price only in tight draws,
where X̃ is high for a net seller.

**Levels.** At price-setting steps the markup over implied cost averages €8. For the
five firms it runs €6.5–9 at X̃ below 0 and €10–15 at X̃ of 0 to 4; for the other
owners, €2–7 at X̃ of 0 to 4. Part of that level is cost the implied cost leaves out
(operation and maintenance, part-load efficiency, start-ups), which the effects absorb.

**Length of a step** (gap draws, unit's last step and blocks at €5 or less left out):
β −0.84 (se 0.27), F 21.9, set [−1.58, −0.17]; −0.75 with regional wind; −0.85 on gas.
Both 0 and 1 are rejected, with the wrong sign. The length condition assumes the firm
re-chooses its step lengths when an outage shortens its curve.

- If the lengths are fixed, an outage pushes the firm's draws higher up rivals' curve:
  the gap price rises while X falls.
- And they mostly are fixed: a gas or coal unit repeats yesterday's step boundaries at
  noon on 82% of days in June 2019 (76%, 67%, 48%, 61% in June 2020–2023), and
  yesterday's step prices on only 55% (57%, 44%, 19%, 42%).
- Prices are re-chosen; lengths follow the plant. The design said a length at a
  technical bound gives only an inequality; here that is most of them.

**One draw (the realised residual demand)**, the ex-post version:

| | n | β | F | 95% set |
|---|---|---|---|---|
| own step sets the price | 7,672 | −0.12 (0.05) | 11.3 | [−0.14, −0.04] |
| price in the gap above an own step | 134,567 | −0.02 (0.01) | 4.3 | [−0.09, −0.01] |

The realised X varies far more than its expectation, so these sets are narrow. They
condition on the realised clearing, which the bidder did not know. They sit just below
0, as leg D's sellers do (β⁺ 0.00).

## 4. What it means

- **On the steps that set the price, the five firms price close to cost plus a common
  ladder.** In the period with a strong instrument, 2019 – mid-2021, the set is
  [−0.60, 0.19]: full Nash is rejected, price-taking is not.
- **The same order as legs A and D.** Within-day hydro gave 0.03–0.14 and the sign of n
  gave 0.02–0.03. Leg C's β ≈ 3 was the price falling down the merit order (framework
  §9.1). Read on the firm's own steps, with the ladder netted and the expectation over
  residual demand built explicitly, it goes away.
- **Thermal step lengths are not a margin of conduct.** They repeat day after day, and
  their condition fails. Withholding, if any, would show in step prices or whole-unit
  withdrawals, not in where steps end.
- **What it does not settle.** The full-sample set still reaches 1.01: from mid-2021
  the instrument is weak (F 8) and the draws mix gas prices. The across-day margin,
  start-up costs and hydro are not in it.

## 5. Limits

- **Only firms with reactors are moved by the instrument**: EDP, Endesa, Iberdrola,
  Naturgy. Repsol and the other owners enter through the effects.
- **The draws are a model of beliefs.** They take the same clock hour within ±28 days,
  nearest in forecast net load, shifted by the forecast. In 2021–2023 that window mixes
  gas prices; a price-level adjustment was not tried.
- **Withdrawn units.** A unit withdrawn by its minimum-income condition keeps its
  offers above the price. A draw that clears higher treats them as available, though
  the condition might still withdraw them.
- **Ties.** On a price point shared with rivals, the firm's acceptance is pro rata.
  Points where the firm's sell volume is less than 90% gas or coal are left out.
- **X̃ needs a slope floor.** Results move with it: the set is [−0.56, 0.69] at a floor
  of 5 and [−0.23, 1.34] at 50.
- **Cost.** It is an engineering cost with no operation and maintenance, part-load or
  start-up terms; the effects take the parts that are constant or common. Coal's cost
  is not validated (leg C).
- **The 15-minute era** (from 2025-10) and hourly 2024–2025 are not run.

## 6. Hydro, with the water value differenced out (run 2026-10-06)

Script `analysis/step_estimator_hydro.py`; engine `step_engine.py --kind hydro`;
results `outputs/tables/step_estimator_hydro_results.csv`. Storage hydro and
pumped-storage turbines (leg D's units), 2019-01 → 2025-09 (the last hourly month).

**The idea.** A reservoir's marginal cost is its water value, which nobody publishes.
Within a day it is one number per unit (leg A's assumption A1), so unit × day effects
take it out:

    step price = water value (unit × day) + β · X̃ + hydro class × hour + class × ladder position

β comes from how a unit's step prices move across the hours of one day against the
firm's X̃ in those hours, compared with other owners' hydro in the same hour.

**Who is in it.** The fringe's hydro units offer everything at €1/MWh or less, so no
fringe hydro step ever sets the price. The rows are the five firms, Movhera (from
2022) and a few Acciona and Ignis steps:

- 661,669 unit-steps set the price in at least one draw, on 46 units.
- 28% of them come from unit-days with the same curve in all 24 hours. Those are left
  out of the main rows, which leaves 457,263.

**Instruments that vary within the day:**

- **Each firm's own response to REE's D-1 wind and solar forecasts** (16 instruments,
  as in leg D §7).
- **Reactor outages** and **regional wind deviation**, which vary little within a day.

| instruments (sample) | least squares | β (2SLS) | F | 95% set (Anderson–Rubin) |
|---|---|---|---|---|
| firm × forecast (main) | +0.34 | +0.12 (0.04) | 71 | **empty** |
| firm × forecast, flat unit-days in | +0.32 | +0.06 (0.04) | 88 | empty |
| firm × forecast, 2019–2023 | +0.40 | +0.20 (0.06) | 45 | empty |
| firm × forecast, 2024 – 2025-09 | +0.14 | −0.09 (0.05) | 105 | empty |
| firm × forecast, storage only | +0.37 | +0.14 (0.05) | 97 | empty |
| firm × forecast, slope floor 5 / 50, price-scaled band, \|X̃\| ≤ 30 | +0.15 to +0.49 | +0.03 to +0.14 | 53–127 | empty |
| **reactor outages** | +0.34 | +0.06 (0.15) | 5.3 | **[−0.73, 0.37]** |
| **regional wind deviation** | +0.34 | −0.12 (0.20) | 14.4 | **[−0.61, 0.31]** |

- **The firm × forecast instruments do not agree on one β.** The first stage is strong,
  but the Anderson–Rubin set is empty in every sample. Each firm's hydro answers the
  forecasts in its own way, beyond what its X̃ explains. Water management, inflows and
  the other plants in a cascade are candidate routes. This is the same failure as the
  intraday firm-specific instruments, so the 2SLS point estimates here are not read.
- **The two instruments whose exclusion is plausible give β near 0**: outages
  [−0.73, 0.37] (weak, F 5) and regional wind [−0.61, 0.31]. Full Nash is rejected by
  both (p 0.001 and 0.001); price-taking is not. Regional wind is on the third location
  pass (78.5% of wind located, 2026-10-06); on the first (54%) it gave −0.17 (0.25),
  F 10.8, [−0.83, 0.38], p(β = 1) 0.004.
- **By sign of X̃**, with the firm × forecast instruments: β⁺ −0.24, β⁻ +0.44 (equal
  rejected, p < 0.001); in 2024–2025, −0.85 and +0.79. These rest on the same
  instruments that fail above, so they are not read as conduct.
- **Five firms only** is not identified: with the hour effects, the firms' forecast
  instruments add nothing beyond them.

**Reading.** Hydro step prices within the day move little with the firm's expected X̃.
The least-squares slope is +0.14 to +0.49, and its bias probably runs upward (§3:
other owners' gas and coal steps show +0.51 with no stake in the price). The two
plausible instruments put β between about −0.8 and 0.4. That is the thermal result
again: well below Nash, not separable from price-taking. It covers the within-day
margin only; the water value's level, the across-day margin, is still untested.

## 7. An instrument from the model: X̃ at cost (2026-10-07)

> **Superseded in part, 2026-10-08** (`rq-price-taking-simulation.md`): simulated price-takers
> (β = 0) reproduce these at-cost estimates almost exactly (−0.26 / −0.21 against −0.27 with the
> main effects, +0.27 against +0.10 with fuel × date), including the sign flip. With a slope per
> unit on the at-cost draws' price, thermal offers cannot be told apart from price-takers in any
> period (pooled +0.01 [−0.08, 0.10]). Nash is still rejected.

**The idea, with an example.** Iberdrola offers a gas step at €95 against a measured
cost of €90. A step priced higher sets the price only in tighter draws, so its X̃ is
computed there. If the extra €5 is a cost we do not see, least squares reads it as
market power, which is why X̃ needs an instrument. Now move Iberdrola's gas and coal
steps to their cost and clear the same 40 draws again. X in the draws whose price
lands nearest €90 depends on Iberdrola's position and on rivals' slopes, which is what
X̃ measures, but not on the €95. That is the instrument: X̃ on the curve the firm would
offer as a price-taker in its thermal plant. It evaluates the endogenous term with the
unobserved cost set to zero, as Berry, Levinsohn & Pakes (1999) approximate optimal
instruments. It needs no outside shock, so it is not limited by how rarely reactors trip.

**Built.** `step_engine.py --comp` (60 months, about 95 s each): the same draws and
shifts as §2; the firm's non-withdrawn gas and coal steps moved to their unit's cost
(97% of their MW is found in the effective curve and moved). A unit's cost point sets
the price in at least one draw for only 14% of unit-hours (June 2019), so X is averaged
over the 5 draws whose price is nearest the cost: the unit's own cost (Zc) or the
median cost of its fuel that day (Zb, used below unless stated), so that an error in
one unit's measured cost cannot enter the instrument. Also written, not used: the
exact events at the cost point and a ±5 €/MWh band. The draws' prices sit a median
1.2 €/MWh from the cost.

**Results** (price moments of §3, same rows, weights and week clusters):

| fixed effects | least squares | β (2SLS) | F | 95% set (AR) |
|---|---|---|---|---|
| unit × month, fuel × hour, ladder (as §3) | +0.14 | −0.27 (0.05) | 492 | [−0.37, −0.18] |
| same, at the unit's own cost (Zc) | +0.14 | −0.23 (0.05) | 543 | [−0.32, −0.13] |
| same, at cost + reactor outages | | −0.27 (0.05) | 201 | [−0.38, −0.17] |
| fuel × date and hour | +0.18 | +0.10 (0.04) | 602 | [0.04, 0.17] |
| **unit × day, fuel × hour, ladder** | +0.16 | **−0.08 (0.06)** | 222 | **[−0.19, 0.02]** |

| period | unit × month (as §3) | unit × day | fuel × date and hour |
|---|---|---|---|
| 2019 – 2021 H1 | −0.03 [−0.10, 0.04] | +0.12 [0.03, 0.20] | +0.46 [0.35, 0.57] |
| 2021 H2 – 2023 | −0.29 [−0.38, −0.19] | −0.09 [−0.20, 0.01] | −0.03 [−0.11, 0.05] |

Other checks, §3 effects: slope floor 5 −0.20 [−0.28, −0.12], floor 50 −0.40
[−0.52, −0.27], |X̃| ≤ 30 −0.53 [−0.72, −0.35]; gas −0.27, coal +0.04 [−0.39, 0.28];
five firms −0.25 [−0.35, −0.15] (unit × day −0.08 [−0.20, 0.03]); other owners +1.55
[−0.92, 3.83] (unit × day +1.18 [−0.31, 2.93]; their X̃ is small, so β is imprecise).

**Reading.**

- **The instrument is strong**: F 200–700, against 10 for the outages. Full Nash
  (β = 1) is rejected in every specification on all steps, on gas, on coal and on
  the five firms, with p below 10⁻¹¹. The highest upper bound among them is 0.57;
  with unit × day effects it is 0.20. Only the other owners' set includes 1.
- **The outages agree with it**: together the set is [−0.38, −0.17], not empty; the
  outages alone give [−0.68, 1.02] on the same rows.
- **The sign depends on which variation is used.** Within the hour and across days of
  a month (§3 effects) β is negative; holding each unit's day fixed takes it to −0.08,
  which contains 0; using the shape of each day (fuel × date and hour) makes it
  positive, +0.46 in 2019 – mid-2021. With a strong instrument, estimates that move
  with the fixed effects mean that something tied to the firm's position also moves
  its step prices in some dimensions. One candidate is commitment: a firm that is
  short on a day (reactor or hydro output low) starts more thermal plant, and start-up
  costs show in its step prices. That is the same pattern outages and rain gave
  (`rq-reactor-outages.md` §10: a shock cutting a firm's cheap output raises its
  thermal offers). Unit × day effects take out each unit's daily commitment state, as
  the hydro rows of §6 do, and are preferred on that ground. That choice was made
  after seeing the §3-effects estimate, so all three columns are reported.
- **What it settles: the upper bound, not the sign.** β is small: [−0.19, 0.02] with
  unit × day effects, and below 0.6 in every specification. Price-taking is not
  rejected in the preferred one; a small negative β is not ruled out.

### 7.1 Start-up cost does not explain the sign (2026-10-07)

> 2026-10-08: the sign is the estimator's (`rq-price-taking-simulation.md` §2–3).

`analysis/step_startup_check.py` → `outputs/tables/step_startup_check.csv`. The candidate
in §7: a firm short on a day starts more plant, and start-up costs raise its step
prices. Two splits, known at noon on D-1: whether the unit was cleared in D-1's last
hour (**running**, 74% of marginal draws), and whether it declares a minimum-income
condition for D in `cab` (**MIC**, 74%). The condition recovers the start-up cost
separately, so a unit declaring it can offer its steps at cost; one that does not must
put the start-up into its step prices. And it does: markups (b − c) are 3.1 €/MWh on
running MIC units, 9.0 off MIC, 15.3 running without MIC, 20.9 off without MIC.

| steps | unit × month, fuel × hour | unit × day, fuel × hour | fuel × date and hour |
|---|---|---|---|
| all | −0.27 [−0.37, −0.18] | −0.08 [−0.19, 0.02] | +0.10 [0.04, 0.17] |
| **running, MIC** (no start-up in the step price) | −0.32 [−0.47, −0.17] | −0.04 [−0.22, 0.14] | +0.10 [0.00, 0.19] |
| off, no MIC (start-up in the step price) | −0.22 [−0.41, −0.03] | +0.09 [−0.18, 0.32] (F 7) | +0.24 [0.13, 0.35] |
| MIC | −0.35 [−0.49, −0.22] | −0.11 [−0.29, 0.06] | +0.07 [−0.03, 0.17] |
| no MIC | +0.03 [−0.08, 0.17] | +0.38 [0.10, 0.88] (F 19) | +0.29 [0.21, 0.37] |

- **The sign moves the same way where no start-up cost can enter the step price**
  (running, MIC: −0.32, −0.04, +0.10). Start-up cost is not the explanation.
- **What differs between the columns is which variation is used.** Going from the first
  to the second column removes each unit's day-to-day variation within the month and
  takes β from about −0.3 to about 0: something that varies by day and moves with the
  firm's position lowers its step prices relative to measured cost. The third column
  uses each day's hourly shape and gives about +0.1. Not identified yet; candidates are
  the firm's daily hydro and nuclear position (its portfolio, not its start-ups) and the
  timing of the gas price in the cost (prices dated D-2).
- **Units without a minimum-income condition** lean positive (+0.03 to +0.38). They are
  a quarter of the draws, with weaker first stages; not read further.
- **Unchanged:** full Nash is rejected in every row, and the preferred column stays near
  0. The bound holds; the sign is open.
