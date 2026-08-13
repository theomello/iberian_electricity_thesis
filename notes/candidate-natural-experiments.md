# Candidate natural experiments, and open questions for the supervisor

Written 2026-08-13. The point is to choose the *event* before arguing about
treatment and control groups, since the event determines them.

---

## The two Spanish interventions treat opposite halves of the market, back to back

This is the useful discovery. Spain ran two emergency measures in sequence, and
each covers what the other excludes.

### A. RDL 17/2021 — clawback on non-emitting generation

- **In force 16 September 2021 → 31 December 2023.** Verified against the BOE
  consolidated text on 2026-08-13, correcting an earlier "→ 31 March 2022" in
  this note. 31 March 2022 was only the *original* sunset; the mechanism was
  extended four times and never lapsed:

  | decree | extends to |
  |---|---|
  | RDL 17/2021 (original) | 31 March 2022 |
  | RDL 6/2022 | 30 June 2022 |
  | RDL 11/2022 | 31 December 2022 |
  | RDL 18/2022 | 31 December 2023 |
- **Treated:** peninsular non-emitting generation **above 10 MW** that has no
  specific remuneration framework and won no renewable auction — in practice
  **nuclear, hydro, and merchant renewables**.
- **Not treated:** anything under a specific remuneration regime (RECORE
  renewables, cogeneration, waste), installations **under 10 MW**, and all
  emitting plant — gas and coal are untouched.
- **Mechanism:** revenue clawback proportional to the MIBGAS gas price above
  €20/MWh, so **treatment intensity varies daily with the gas price** and is
  computable.

### B. RDL 10/2022 — the Iberian Exception gas cap

- **In force 15 June 2022 → 31 December 2023** (12 months initially, extended).
- **Treated:** combined-cycle gas, **conventional coal**, and cogeneration
  **without** a regulated remuneration framework.
- **Not treated:** nuclear, hydro, wind, solar, RECORE cogeneration.
- **Mechanism:** the gas price usable in a bid is capped (€40/MWh rising toward
  €65) with plants compensated for the difference, so **treatment intensity is
  the wedge between the market and capped gas price divided by efficiency** —
  computable from MIBGAS plus JRC efficiencies.

**Why the pairing matters.** A is a tax on inframarginal rent falling on hydro
and nuclear; B is a subsidy to marginal cost falling on gas and coal. They are
adjacent in time and almost disjoint in coverage, so each provides a
placebo-like mirror for the other, and a firm's response to both is observable
in the same units.

**They overlap, and heavily — this was recorded backwards.** A runs to 31
December 2023 and B begins 15 June 2022, so the two coincide for **18.5
months**, from 15 June 2022 to 31 December 2023. Every earlier statement in
this repo that they are adjacent and disjoint is wrong.

That is a real problem for the mirrored-episodes design, not a footnote. In the
overlap, A's treated group (hydro, nuclear, merchant renewables) is under
clawback *while* B's treated group (gas, coal) is being subsidised, so neither
serves as a clean control for the other. What survives:

- **A alone, 16 Sep 2021 → 14 Jun 2022** — clawback in force, gas cap not yet.
  Nine months, and it contains the March 2022 gas spike.
- **B alone — does not exist.** B never runs without A.
- **The 15 June 2022 discontinuity** is still sharp: A is already in force on
  both sides of it, so it differences out, and B switches on. This is arguably
  the cleanest single date available.

**The EU inframarginal revenue cap does not add a date.** Council Regulation
2022/1854 set a €180/MWh cap, but **Spain did not implement it separately** —
it relied on the existing RDL 17/2021 mechanism, which was already a revenue
clawback and binds much tighter (~€67/MWh). Verified 2026-08-13. So the
earlier worry that an unlisted EU measure contaminates B's control group is
unfounded; the contamination is A itself.

### Why A may be the better thesis

Hydro sets the clearing price more often than any other identifiable
technology in our data — 17% to 38% of periods in every year, more than gas in
all but the crisis years. **A treats hydro directly.** It also connects to the
water-value literature: a clawback on inframarginal rent changes the value of
generating now versus storing, which is exactly the object Arzhintar, Leslie,
Neill and Wyrwoll estimate.

A also offers a **size discontinuity**: treated above 10 MW, exempt below. We
have nameplate capacity from `cab` for effectively all near-marginal units, so a
regression discontinuity in capacity is available. Whether enough small units
bid near the margin is an open empirical question.

---

## Other candidates, ranked lower

| event | dates | why it ranks lower |
|---|---|---|
| Coal plant closures | staggered, 2020–21 | exit rather than policy; endogenous timing |
| 15-minute market time unit | intraday Jun-2025, day-ahead Oct-2025 | staggered but **no control group** anywhere |
| Iberian blackout | 28 April 2025 | short, confounded, overlaps the 61-day data anomaly |
| Market splitting ES/PT | continuous | variation not an event; already used as a filter |

---

## Open questions for the supervisor

1. **Which event.** A (clawback on hydro and nuclear), B (gas cap), or both as
   mirrored episodes.
2. **The cost side.** Whether to attempt realised markups, and if so via firms'
   declared minimum-income terms in `cab` (a revealed bound, no engineering
   data) or via JRC efficiencies with gas and carbon prices (conventional
   marginal cost, `OEM_derived` for the large CCGTs, ~20% of near-marginal
   volume).
3. **The control group, once the event is fixed.** For B, the untreated
   technologies are also *exposed* through the market price, so a naive
   difference-in-differences would be wrong; the spillover is arguably the
   finding. For A, the EU inframarginal cap needs dating before controls are
   settled.
4. **Sample window.** Firm coverage of near-marginal volume runs 93–97% for
   2018–2022 but falls to 76–86% for 2023–2026. Both candidate events sit in
   the well-covered part of the window, which is an argument for either.
5. **Static versus dynamic markups.** Jha & Leslie show static markups overstate
   market power once start-up costs are counted. Our Lerner estimates are
   static and therefore biased upward. `cab` publishes declared start-up costs,
   so the correction is available — but it changes the headline number.

---

## What is not in question

The descriptive result stands on its own and does not depend on any of the
above: residual demand elasticity fell from 1.83 to 0.85 between 2018 and 2023
while CNMC's Herfindahl index fell from 1,314 to 1,007, and the weather
instrument agrees with OLS to within 4%.
