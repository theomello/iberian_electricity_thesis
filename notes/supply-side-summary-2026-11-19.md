# The supply side, summarized for the write-up (2026-11-19)

**Purpose:** one page on everything done on the supply side (August → November 2026), and a proposal for what enters
the thesis now that the headline is demand-side and supply sits only in the descriptive part
(`thesis-demand-supply-link.md`). Grades A/B/C as in `docs/specs/2026-11-08-conduct-evidence-table.md` (the full
80-row register). Nothing here is new; every number is in that table or the named note.

**The one condition behind it all.** offer − cost = β × X, with X = the firm's net auction position ÷ the slope of
its residual demand (the Nash markup, €/MWh). β = 0 is price-taking, β = 1 is Nash. Example: X = €4, offer €1 above
cost → β = 0.25.

## 1. What was done, by strand

| # | Strand | When | What it found | Grade / status |
|---|---|---|---|---|
| 1 | **Data foundations**: unit ownership by date and share (`lib/unit_ownership.py`), cost measures (implied gas/coal cost, `_bid` columns; hydro water value λ* from forwards; declared minimum-income cost in `cab`; start-up costs) | Aug–Oct | λ* matches EDP's own (within 6%, corr 0.81–0.91); ownership a contribution in itself | infrastructure |
| 2 | **Legs A–D** (framework of 2026-09-29) | Sep–Oct | A: hydro within the day, β small; B: hydro in levels against λ*, β −0.26 [−0.72, 0.04], Nash rejected; C: thermal in levels gives β ≈ 3 — the merit order, not conduct (rivals' plants show the same fall); D: sign of n, β 0.024, seller 0.00, buyer markdown 0.19 (later traced to contract routing) | the first pass; superseded as estimates by strand 3, kept as the lesson that levels confound merit order with conduct |
| 3 | **Price-taker simulation + step estimator** | Oct | standard estimators give β ≠ 0 for true price-takers (−0.14 to −0.26); every β is read against ten simulated price-taker seeds | **the methodological core** |
| 4 | **Offer prices, thermal** | Oct | β +0.01 [−0.08, 0.10]; price-taking accepted within 0.1 (equivalence), Nash rejected | **A** |
| 5 | **Offer prices, hydro** | Oct–Nov | pooled +0.06 [−0.05, 0.15] (A); one departure 2019–21H1, +0.25 [0.15, 0.34] ≈ €1/MWh on price-setting steps, −€0.01 on the price; rests on Iberdrola; stops May→June 2021; second (fixed-step) design does not find it | A pooled, **B** departure |
| 6 | **Quantity margins** (withholding) | Oct–Nov | nuclear cuts β −0.19 (MDE 1.16); own wind +0.275 MW/MW (wrong sign for withholding); regional holidays −0.20; unoffered hydro +0.15 pp/sd (< 1 pp bar); faults don't follow stake. Unoffered hydro of Endesa/Naturgy: ~80% used nowhere | B (power-limited); "no withholding detected" |
| 7 | **Gas cap** (Iberian exception) | Oct–Nov | declared costs fall by ρ 0.91 [0.86, 0.96] of the subsidy (A); offers ρ 0.87 [0.48, 1.00] within Iberia (B); Italy (five designs) and Great Britain fail as controls; welfare at ρ 0.73: buyers −€3.2 bn, 74% transfer, 17% DWL; hydro offers did not follow | **A** declared, **B** offers |
| 8 | **Price formation, descriptive** | Aug–Oct | setter check: 44% of hours a unit with a cost, 16% the open France line, 23% buy bids; DA−ID premium +€0.6; integrated firms' hydro mostly bilateral; hedge ratios did not rise | description |
| 9 | **Stopped designs** | Sep–Nov | regional holidays (self-supply absorbs), MIC near-miss, France link, FIT exits, outage IVs (several), own-wind and intraday surprises, IVPEE 2024 (2018–21 steps pass through, θ 1.45), cogeneration (fuel gate), clawback RDD, heat-demand, start-up correction | all recorded with their reason |
| 10 | **Link to demand (this week)** | 19 Nov | T2: the reform left market power unchanged on average (M2), moved it between hours by < €1 (M1 fails, 3 firms), gave hydro no incentive reason to stop (D1); T3: price signal unchanged, no feedback; hydro firm table | registered, results in |

## 2. What goes into the thesis (proposal)

Chapter 2 (market and descriptive) carries the supply side; chapter 6 carries T2/T3.

**In (main text, chapter 2), in this order:**
1. **Who sets the price** (setter check). The direct link to demand: 23% of hours a buy bid sets it.
2. **Offers sit near cost** — thermal (A, equivalence) and hydro pooled (A), one table, with one paragraph on why the
   simulated price-taker benchmark is needed (strand 3; method in an appendix).
3. **The one departure**: hydro 2019–21H1, about €1/MWh on a few steps, no effect on the price, Iberdrola's, ends
   with June 2021 — and T2's D1: the reform gave no incentive reason for the stop. One paragraph, the firm table in
   an appendix.
4. **The gas cap as context**: declared costs passed the subsidy ρ 0.91 (A), offers ρ 0.87 (B); consumers paid the
   adjustment charge, so the cap reached consumers as a net price (links to the demand chapter's exposure θ).
5. **No withholding detected** — one sentence and a pointer to the appendix table.

**In (chapter 6):** the price effect, T2 (M1/M2/D1), T3.

**Appendix:** the price-taker simulation and step estimator; the hydro firm table; the conduct evidence table
(headline rows only); the stopped designs, one line each with the reason; Italy/GB as failed controls, one
paragraph.

**Out:**
- legs A–D as estimates (superseded; leg C's merit-order lesson can be a footnote in the method appendix);
- welfare of the gas cap (a gas-cap paper item; the grid is at ρ 0.73, not the current 0.87);
- the outage regression rerun and the gas-cap hour-of-day counterfactual (dropped earlier);
- intraday, DA−ID premium, hedge ratios, clawback size, markups vs HHI, cogeneration, IVPEE: not needed for the
  demand story (IVPEE is the one that could return as a pass-through footnote).

**Open conflicts to state, not resolve** (evidence table §2): the two hydro designs disagree on where the departure
is; leg D's buyer markdown vs the simulation; the outage instrument's band. Under the demand frame only the first
matters, and it is one sentence.

## 3. Disk space (for a separate session)

Disk 88% full (12 GiB free). Largest: `data/omie` 9.4 G, `data/esios` 9.1 G, `outputs/cache` 3.6 G,
`outputs/tables` 3.5 G, `data/gme` (Italy) 2.9 G, `data/goiener` 1.3 G, `data/eobs` 0.8 G. Candidates once
the chapters are fixed: Italy (`data/gme`) and Great Britain (`data/elexon`) if they stay out of the main text;
re-buildable caches (`outputs/cache`, `data/cache_tou`); parquet panels of stopped designs in `outputs/tables`.
Never delete the three non-re-fetchable sets in CLAUDE.md (OMIE unit lists, SNIRH raw, investing CSVs).

## 4. Decisions (user, 2026-11-19)

**Principle:** the supply side is used for context; it is linked to the headline results only where the link is
called for.

- **In, as context (chapter 2):** the conduct conclusion: Nash rejected everywhere; price-taking accepted for thermal
  (equivalence, δ = 0.1); hydro to be settled (session `hydro-settle`, started 2026-11-19). The hydro departure gets
  one paragraph plus D1. The finding that integrated firms sell hydro mostly through bilateral contracts goes in as
  context for exposure.
- **Price-taker simulation:** in the appendix (the thermal result rests on it), cited in one sentence in the text.
- **Out:** gas-cap welfare (no rerun at ρ 0.87); withholding (out of the main text, appendix lines at most); the
  day-ahead minus intraday premium.
- **Undecided:** leg C's lesson (footnote or a method-appendix paragraph); what the price effect, T2 and T3 add, and
  where they go (under discussion).
- **Next:** go through every supply-side note and spec rigorously, assigning each to context, appendix, a separate
  gas-cap/conduct paper, or nothing.
