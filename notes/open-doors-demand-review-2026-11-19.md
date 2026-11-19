# Last pass: open doors and links to the demand story (review, 2026-11-19)

**Status: review only. Nothing estimated, nothing downloaded, nothing registered.** Read: `papers/README.md` and the
paper markdown cited below; `notes/` (every `idea-*`, `scope-*`, `rq-direct-consumers`, `rq-cogeneration`,
`rq-crisis-quantity` §E, `handover-2026-11-18-industrial-demand`, `tou-headline-outline`,
`literature-industrial-demand-elasticities`, `thesis-demand-supply-link`); `docs/business-demand-evidence.md`.
Frame: demand headline, supply descriptive only (`thesis-demand-supply-link.md`). λ = short-notice share of the
planned response; θ = exposure to the hourly price; σ = response to a planned price change.

## A. Links that need no new run (write them in)

| # | Link | Source | Where it goes | What it adds |
|---|---|---|---|---|
| A1 | **Households' λ is supplied by the literature.** Spanish PVPC households facing hourly prices, wind-forecast instrument: elasticity zero (2016–17), and again ≈ 0 in 2021–23 | Fabra, Rapson, Reguant & Wang (2021, `papers/md/fabra-et-al-2021-…`); Fabra & Reguant survey fn 6 (`survey-ar-energy-transition.md`, citing Fabra et al. 2026c) | ch. 3 framework, ch. 6 T3 | T3 had to set households' λ = 1 because we cannot identify it; with Fabra et al. the household term σλθ ≈ 0, so the household part of the worst-case feedback (2.4–4.8 MW) is a pure bound. Also matches our reform finding that PVPC customers respond *less* than the rest |
| A2 | **A volume-based check of θ.** Energy under fixed-price contracts signed before 26 April 2022 was exempt from the gas-cap adjustment charge. The free-market charge ÷ reference charge is therefore the non-exempt share: **0.48 in June 2022**, rising to 0.76 by February 2023 as contracts expired; the Commission put the charged share at 41% of Spanish consumption | RDL 10/2022 art. 8; `rq-crisis-quantity.md` §E "Correction 2" | ch. 2 exposure; T1 threat "θ is a contract count, not a volume" | an independent, **volume-weighted** exposure at a dated point, about equal to the CNMC's 0.49 (indexed at all) used in L2; supports the θ range without a new run (it is an upper bound on hourly exposure: new fixed contracts also pay) |
| A3 | **Why λ ≈ 0: the binding incentive is the period, not the hour.** Hirth, Khanna & Ruhnau find −0.05 in Germany (−0.2 to −0.5 for the exposed 10–25%) and argue German peak-demand charges and the constant-load rebate mute the hourly signal for large industry. Spain's six-period power term (contracted power by period, P1 ≤ … ≤ P6) is the same kind of device, and our σ includes it (full dose) | `papers/md/how-aggregate-electricity-demand-responds-…` (pp. on exposure); `scope-2021-high-voltage-shift.md` "Cause found" | ch. 5 discussion of T1 | turns "λ ≈ 0" from a number into a mechanism the literature already names; explains why Spain's same-hour response is below Germany's |
| A4 | **Salience and information.** Consumers respond to the price they can see and plan around (Ito 2014: average not marginal price; Jessoe & Rapson 2014: information raises response) | `papers/md/w18533.md`, `w18344.md` | ch. 3 microfoundation of λ | the "rescheduling cost" in equation D gets an information-cost reading too |
| A5 | **Demand sets the price in about a quarter of hours.** Setter check: 23% of hours set by buy bids (pumping, exports, price-sensitive retail and direct-consumer bids) | memory / `rq-descriptive-price-formation.md` setter check | ch. 2, as the X′ term of equation S | the descriptive chapter's direct link to the demand side: the X′ slope is observed, not assumed |
| A6 | **Direct consumers' stated slope.** Process-industry direct consumers' bid curves imply an arc elasticity of 0.36 (2019–21H1) → 0.06 (2023–26); 91% of extra auction purchases are offset elsewhere | `docs/business-demand-evidence.md` row 12; `rq-direct-consumers.md` | ch. 2 / ch. 5 | the stated price sensitivity of the one group that bids, against our near-zero realised one: stated ≠ realised, because load moves between channels |
| A7 | **The gas cap as a consumer price.** The cap lowered the day-ahead price but buyers paid the adjustment charge (ESIOS 10403: €27/MWh June 2022, €67 July); net to consumers negative at any ρ | `rq-crisis-quantity.md` | ch. 2 | ties the supply pass-through result (ρ) to the price consumers actually faced, without making it a headline |

## B. Doors still open that need a design (each: pre-registration and your yes)

| # | Door | Why it links to the demand story | Cost / risk |
|---|---|---|---|
| **B1** | **Season-calendar boundaries of the business tariffs** — *correction 2026-11-19: already run and closed on 2026-11-16 on Barcelona services (`docs/specs/2026-11-17-calendar-boundary-design.md`: η −0.004 [−0.080, +0.071], E1–E5 fail); this review missed it* (`idea-calendar-boundary-business-tariffs.md`): since June 2021 the 3.0TD and 6.xTD daytime period steps on eight dates a year (up 1 July, down 1 August, …) while nights and weekends do not; 2021–25 gives about 35 dated events in both directions, with pre-reform years as placebos | It is a **second, repeated identification of σ** for business customers. σ's interval end (−0.095) is what drives T1's λ bound (0.71; 0.38 at σ's point), and σ's two failed rules (E3 drifted null, E5 not proportional) are exactly what many signed events test. A tighter σ tightens λ directly | National series on disk (E0 mixes 3.0TD with households; 6.x clean). The Barcelona Datadis file would separate services from households but **needs a download (your yes)**. Risk: boundaries fall on seasonal turns (1 July, 1 August); likely a precise zero for 6.2–6.4 |
| B2 | **Portuguese control series** (E-REDES request sent 2026-11-18; REN and ERSE not yet asked) | would firm up the level of the household effect (rule 7/8 failures: level depends on the control) | external; waiting |
| B3 | **IND rerun with the fixed E5 loader** | housekeeping: the IND 2021 estimate (−0.288) and its six-summer row rest on 40% of hours (E5 gap). E0, E1+E2 and 6.2–6.4, and therefore σ and T1–T3, are unaffected | minutes; but IND is not in the headline, so it can simply be marked superseded instead |

## C. Checked and closed (no action)

- Portuguese access-tariff swing: Portugal is a control only (your decision); its own swing is not used.
- Sustained price-level margin (von Graevenitz–Rottner −0.4 to −0.6): no way to separate electricity from gas at sector level.
- Within-day substitution by instrument (price shape): wrong signs, instruments disagree; thread closed.
- Direct consumers' curve shifts (E3): 91% offset elsewhere; event studies rejected (no control).
- Cogeneration: fuel known for 12.9% of capacity (gate 60%); not run.
- Power (capacity) term as a separate dose: already inside σ's full dose (`tou_power_term_6x.csv`).
- Leslie et al.'s duck-curve/evening-ramp check: answered by T3a (the reform took a quarter off the evening–night spread).

## Recommendation

Write A1–A7 into the chapters; they cost nothing and A1–A3 close the main gaps in T1 and T3 (households' λ, θ by
volume, the mechanism for λ ≈ 0). Of the doors, **B1 is the only one that strengthens the headline itself**:
it re-identifies σ on many signed events and would tighten λ. Mark B3 superseded unless IND is to be quoted.

**B1 spec drafted (2026-11-19, proposed, not registered):** `docs/specs/2026-11-19-season-boundary-design.md`.

**Correction (2026-11-19):** B1 is not an untried door. The Barcelona-services version was closed on 2026-11-16 with a bounded null; that bounded null is itself a link (A-type): business customers' month-scale response to the 3.0TD steps is no stronger than about −0.08. The 6.x national version registered today stops before Z2 pending the user's decision.
**Closed (2026-11-19, user decision):** the 6.x national version is not run; B1 is closed. Use the Barcelona bounded null as a link in the descriptive chapter.
