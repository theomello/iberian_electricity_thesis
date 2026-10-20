# The holiday quantity test: book balancing or market power?

**Status: run 2026-10-20 (`notes/rq-regional-holidays.md`, quantity test).** The cut follows the
dose (−0.33 MW per MW), not its price effect: β on the quantity margin −0.16 [−0.52, +0.20]; Nash
rejected (p 4·10⁻¹⁰), also for Endesa and Iberdrola alone and under every check. Book balancing.

**In one example.** On the Diada, Endesa's Catalan customers use about 450 MW less, and Endesa
cuts the output it sells them through bilateral contracts by about half that. Two stories fit.
- **Market power.** Endesa buys less, so it gains more from a higher price and holds back output.
  How much it holds back depends on how much each MW moves the price: a lot in a steep hour (few
  rival offers near the price), little in a flat one.
- **Book balancing.** Endesa keeps its own generation matched to its own customers' load and cuts
  by the load it lost, steep hour or flat.

So the cut should follow P = dose / |RD′| (the dose as a move along Endesa's residual demand,
€/MWh) under market power, and the dose Z itself under book balancing.

---

## 1. Why this test

- **The pattern recurs.** Firms absorb shocks to their own load or output by quantity: the reactor
  owners keep their remaining nuclear running for their own customers (`rq-nuclear-cuts.md` §6),
  Iberdrola routes hydro between its retail contracts and the auction (`rq-fixed-step.md`), and
  holidays move bilateral self-supply, not the auction (per MW of dose: generation sold bilaterally
  −0.54 (se 0.13), in the auction +0.02 (0.19); `holiday_schedule_legs.csv`).
- **For the nuclear cuts the slope test decided it**: the cut followed the lost output, not its
  price effect, and full market power was rejected (p ≈ 0.01). The holiday dose is a cleaner
  shock (fixed by law a year ahead, on the retail side only) on different firms and plants.
- **The shock is known.** The dose exists by group, date and hour (`holiday_dose.parquet`, step 2).

## 2. The test

**Panel.** Each of the five firms (Endesa, Iberdrola, Naturgy, EDP, Repsol) by date and hour,
weekdays, 2019-01 → 2025-09 (the step caches' window, for the firms' own offer slopes):
- **Outcomes** (PDBF, MW, signed, sold +): generation in the auction, generation in bilateral
  contracts, their sum; retail purchases in each leg, as the first stage. Units by role and owner
  as in `holiday_schedule_legs.py` (largest owner that day, regulated suppliers out).
- **Z**: the firm's holiday dose in the hour, GW (`holiday_dose.parquet`).
- **P** = 1000 Z / |RD′|, €/MWh, with |RD′| the firm's residual-demand slope in that hour
  (`firm_x.slope_net`).
- **Controls**: 1/|RD′|.
- **Effects**: date × hour (everything market-wide, including the holiday's own effect on the
  market) and firm × month. Errors clustered by date; by week as a check.

**Regression.** y = b_Z · Z + b_P · P + c · (1/|RD′|) + effects + e, for each outcome.

**Predictions, fixed before the run.**

| | b_Z (MW per MW of dose) | b_P (MW per €/MWh) |
|---|---|---|
| book balancing | about −0.5 on generation, all of it bilateral | 0 |
| market power, β | 0 beyond what P carries | **−β · s**, mostly on auction generation |

s is the firm's own offer slope near the price: its own sell offers within ±€5 of the hour's
price per €/MWh (step cache `own`), the MW a price-taker would add per €/MWh of price. Nash
(β = 1) means the firm withholds s MW for each €/MWh the dose adds to its stake. P measures that
stake change before any quantity response, since retail load falls one for one with the dose.

**Reading.** b_P compared with −s̄ (the dose-weighted mean of s) gives β on the quantity margin,
with its confidence interval: β = 0 (book balancing) against β = 1 (Nash). By firm where the
dose allows (Endesa, Iberdrola).

## 3. Steps, each with a stop rule (each run needs a yes first)

1. **The hourly panel and the first stage.** Build it; reproduce step 2's daily legs from it
   (generation bilateral about −0.54 per MW of dose); compute s. *Stop* if generation does not
   respond to Z in the hourly panel (|t| < 2 on the sum), since there is then nothing to explain,
   or if se(b_P) exceeds s̄ / 2.8, since the test could not tell β = 0 from β = 1.
2. **The slope test** (§2), pooled and by firm, both legs; with the checks below.

## 4. Threats and checks

- **Steep hours are tight hours.** The date × hour effects take market-wide tightness; |RD′|
  varies by firm within the hour because each firm's own offers are excluded from its slope.
  Check: P built on the at-cost slope (`hcompcost` kb_s), which does not move with the firm's own
  offers.
- **The dose's hourly profile** is the national holiday profile (step 2): the same shape in every
  region. Check with a flat profile (daily mean dose in every hour).
- **Days around holidays and bridge days**: drop them as a check.
- **Spain-only national days** move every Spanish retailer at once; regional days move one or two
  firms. Check each alone.
- **COVID-19** (March–June 2020): with and without.

## 5. Data

All on disk: `holiday_dose.parquet` (step 2), PDBF, `unit_registry`, `lib/unit_ownership.py`,
`firm_x.parquet`, the step caches (`own`, `hours`, `hcompcost`).

## 6. Goals and limits

- **Goal:** tell book balancing from market power on the quantity margin, with β's interval.
- **Not a goal:** β on offer prices (the holiday design's step 3 needed a first stage it lacks).
- **Limit:** the five firms only; s from the day-ahead own curve, which mixes plants that would
  and would not run.

## 7. Left to the builder

- Hourly PDBF legs: PDBF is quarter-hourly from 2025-03-19, so from then average the four
  quarters' MW to the hour (the day-ahead itself stays hourly to 2025-09).
- How to treat hours with |RD′| below the floor (my call: drop, as `step_estimator_hydro.FLOOR`).
