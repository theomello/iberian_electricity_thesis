# Revision: what the thesis is built from (2026-11-26)

**Purpose.** A review of everything run since August 2026, to decide what goes in the master's thesis, what goes in
an appendix and what is left out. Part 1 sorts every research thread. Part 2 is the outline that follows from it.
Part 3 lists what is still owed before writing.

**Constraints.** Master's thesis, deadline **9 February 2027, 12 noon** (about ten and a half weeks from today).
Length **60,000–120,000 characters** including spaces, excluding the table of contents, sources, footnotes and
appendices; target about 100,000 (budget per chapter below, checked by `make count`). Submitted as PDF through the ISC
web form, named `Matrikelnummer_First-Last_Masterarbeit_Abgabeversion_DD-MM-YYYY` (no umlauts or special characters),
contact the ISC if over 11 MB (`make submission` does the naming and the size check).

**Fixed by earlier decisions (not re-opened here).**
- The headline is on the demand side (19 Nov). The supply side is context only, linked to the demand story where it is
  needed.
- Question and order (20 Nov, "B towards C"). The question is *which prices move electricity demand, and for whom?*
  The introduction leads with the contrast between industry and the wholesale price. The body runs: households
  (replication = method check) → industry → contrast with the wholesale price → validity.
- Headline numbers (20 Nov, extended 24 Nov):
  - large industry −0.15 to −0.32;
  - E0 −0.11;
  - industry's response to the same-hour wholesale price is zero;
  - medium firms −0.025 (persistence).
- Supply-side triage (19 Nov, `notes/supply-side-summary-2026-11-19.md` §4) and hydro wording
  (`notes/hydro-conduct-settlement.md`), both accepted as final.

Verdicts: **Main** = main text · **Context** = descriptive chapter · **App** = appendix · **Out** = not in the thesis
(one line in the stopped-designs table at most).

---

## Part 1. Triage of every thread

### 1A. Demand: households and small business (low voltage, E0)

| Thread | Result in one line | Status | Verdict |
|---|---|---|---|
| Replication of Enrich, Li, Mizrahi & Reguant (DiD on LASSO errors, Portugal control) | evening vs night −3.8% (paper LASSO) to −5.3% (DDD); Wald elasticity −0.06 to −0.09; column 4 −0.100 (se 0.012, F 80), within the paper's −0.082…−0.135 | settled | **Main** (ch. 6, method check) |
| Six-summer prediction test, E0 | −0.116, p 0.019, placebos centred on zero (mean −0.005); clean break on 1 June | settled | **Main** (headline E0) |
| Randomization inference | RI0–RI6 pass, η −0.101 [−0.122, −0.079] | settled | **Main** (ch. 5 method) |
| Pooled placebo (2018 + 2019 dose) | the floor is 9% of the E0 effect; E0 separates (z −12.4), industry series do not | settled | **App** (placebo table) |
| Per-capita area panel + MERRA-2 weather | contrast −6.9 pts and column 4 −0.086 hold; rules 7/8, W3/W4 fail: the *level* depends on the control | settled, failures kept | **App**; the main text claims the contrast only |
| Contrast placebo (six windows) | −6.90 against placebo spread ±4.5 | registered after looking | **App** (supporting) |
| Charge-cut dose response / charge events | the autumn fade is seasonal; placebo-adjusted charge elasticity +0.02 | settled (rules 2–6 fail) | **App**, one paragraph: "a reform response, not a clean price slope" |
| Who responds: PVPC vs free market | regulated −3.9% (η −0.064) vs rest about −5.7% | settled | **Main**, short (links to Fabra et al. 2021) |
| GoiEner household smart meters (2.0TD) | households −0.053 [−0.077, −0.039]; first difference −0.047; about half of E0 | settled (G2, G6 pass) | **Main**: separates households from small business inside E0 |
| Persistence 2021–2025, E0 | −3.9, −1.1, −1.7, −4.3, −4.4% by summer; weaker in the crisis, back in 2024–25; drift guard fails in 4 of 5 summers | settled, post-hoc reading | **Main** (one paragraph + figure), caveat stated |
| CES / nested CES substitution | σ_U 0.07 (peak vs rest), σ_L 0.20 (mid vs valley, estimated control); equality rejected | rules pass | **App** (within-day substitution, feeds ch. 4 equation D) |
| Dose search (which price the consumer reacts to) | dose not identified; paper's convention primary, range −0.07…−0.10 | A1 fails | **App**, one line |
| Energy-price interaction | response weaker above the 90th percentile of the energy price (−0.066 → −0.054) | post hoc | **App**, one sentence |
| Causal forest heterogeneity | calibration fails (F1), no-price ranking fails (F3) | stopped | **Out** |
| Area heterogeneity (B0) | all five areas too noisy | stopped at step zero | **Out** |
| Calibrated reform / levy (K4, K5) | levy about 350× the tariff effect on average cost; rules fail | stopped | **Out** (perhaps a footnote on salience) |
| RDL 14/2022, PVPC, clean-dirty CES, capacity clean-dirty | stopped at step zero | stopped | **Out** |

### 1B. Demand: firms (high voltage)

| Thread | Result in one line | Status | Verdict |
|---|---|---|---|
| Large industry (6.2–6.4), regulated per-period price (energy toll + power term) | −0.15 (trend null, p 0.044) to −0.32 (mean null, p 0.007); reduced form −1.0 pt of daily share per dearer period step, p 0.0001 | E3 and E5 fail as registered | **Main** (headline) |
| Cause of the 2021 high-voltage shift | matches the new 6.x period calendar hour by hour (July 9–10h and 19–21h became P1; August all-P6 → P3/P4) | descriptive | **Main**: the mechanism figure (`hv_shift_2021_by_month.png`) |
| Prediction-model selection (PR #16, chosen on placebo summers only, 2021 sealed) | no candidate model beats the paper's LASSO; the headline stays on M0 | settled (step 1) | **App** (robustness of the prediction step), one sentence in ch. 5 |
| By tariff | 6.2 −0.06, 6.3 −0.23, 6.4 −0.34; not proportional to the dose | E5 fails | **Main** as a finding, not a test |
| Industry, earlier designs (cross-tariff, adjusted, IND −0.288 artefact, corrected −0.189) | superseded by the regulated-price design; −0.288 was the E5 loader gap | superseded | **Out** (errata recorded in the specs) |
| Medium firms (6.1TD, E1+E2), 2021 | −0.175 pts/step, p 0.023, but trend null fails (p 0.103); carried by August | registered reading: "rests on a drift" | **App** |
| Medium firms, persistence summers 2022–25 | −0.283 pts/step, p 0.002, all 9 rules pass, elasticity −0.025 [−0.035, −0.016] | settled | **Main** (headline for medium firms) |
| Large industry, persistence 2022–25 | −0.136 pts/step (vs −1.0 in 2021); R3, R5, R8 fail; only 6.3 shifts | settled | **Main**, stated plainly in ch. 7 (decided 26 Nov) |
| Small business (3.0TD) season mirror | η_MDE 0.42 > 0.15 bar | stopped at step zero | **Out**; one line: "not identified; CNMC data requested" |
| Calendar-boundary design (Barcelona services + national) | η −0.004 [−0.080, +0.071] and +0.013: bounded null at month scale | closed | **App** (bounded null, links to the business story) |
| Direct consumers' bid curves | stated arc elasticity 0.36 → 0.06; 91% of extra auction purchases offset elsewhere | descriptive | **Context** (ch. 3) |

### 1C. The contrast: wholesale price, short notice (T1)

| Thread | Result in one line | Status | Verdict |
|---|---|---|---|
| Wind-speed instrument (C1), 6.2–6.4 | impact elasticity −0.0006 [−0.0185, +0.0265], F 97.5, placebo clean | settled (passes the settlement) | **Main** (headline: the wholesale zero) |
| T1 short-notice share λ | λ̂ ≈ 0.01; λ < 0.71 (θ 0.32) or < 0.47 (θ 0.49) | all rules pass | **Main** |
| Bid-curve instrument | −0.036 [−0.080, +0.010], F 17–20; λ ≈ 0.75, unbounded | closed (weak) | **App**, reported beside C1 |
| Noise-reducer IV (V3), power run, forecast-error IV, exposed subgroup, price shape, solar probe, day-level/metered | placebo fails / F 6.95 / wrong signs / stopped | stopped | **Out** (stopped-designs table) |
| Literature links A1–A4 (Fabra et al. 2021 ≈ 0 for PVPC; Hirth et al. on period charges; Ito; Jessoe–Rapson) | supply households' λ and the mechanism for λ ≈ 0 | no run | **Main** (ch. 4, ch. 8 discussion) |
| Gas-cap charge as a volume-weighted exposure check (θ 0.48 in June 2022) | supports the θ range | no run | **Main**, one paragraph (ch. 2) |

### 1D. Validity through the market

| Thread | Result in one line | Status | Verdict |
|---|---|---|---|
| Price effect of the load shift (re-clearing the day-ahead curve) | evening-minus-night −2.62 €/MWh with industry's shift (−2.39 E0 only); net to consumers ≈ 0 | settled, rerun 21 Nov | **Main** (ch. 9) |
| T2 market power | M2 passes (average change < €0.16/MWh), D1 passes, M1 fails for 4 firms (shifted between night and evening by < €1) | settled, rerun 21 Nov | **Main** (ch. 9); D1 also in ch. 3 hydro paragraph |
| T3 price signal and feedback | the reform is 20–28% of the evening–night spread; surprise response moves 2%; worst-case feedback 3.5%/7.3% | all pass | **Main** (ch. 9) |

### 1E. Supply side (context; decided 19 Nov)

| Thread | Result in one line | Grade | Verdict |
|---|---|---|---|
| Who sets the price (setter check) | 44% of hours a unit with a cost, 16% the open France line, 23% buy bids | description | **Context** (lead item) |
| Price-taker simulation + step estimator | standard estimators give β −0.14…−0.26 for true price-takers; every β read against ten seeds | method | **App** (method), one sentence in ch. 3 |
| Thermal offers | β +0.01 [−0.08, 0.10]; price-taking accepted (equivalence 0.1), Nash rejected | A | **Context** |
| Hydro offers, pooled | +0.06 [−0.05, 0.15]; Nash rejected, price-taking not established | A | **Context** (quote from the settlement) |
| Hydro departure 2019–21H1 | +0.25, Iberdrola's, ≈ €1 on price-setting steps, nil on the price; stops May→June 2021; D1: the reform is not the reason | B | **Context**, one paragraph; firm table **App** |
| Gas cap (Iberian exception) | declared costs ρ 0.91 [0.86, 0.96] (A); offers ρ 0.87 [0.48, 1.00] (B); consumers paid the adjustment charge | A/B | **Context**, one paragraph |
| Integrated firms' hydro mostly bilateral; ~80% of unoffered hydro used nowhere | exposure context | description | **Context**, two sentences |
| Withholding (nuclear, own wind, holidays, unoffered hydro) | none detected, power-limited | B | **App** table, one sentence in the text |
| Data foundations (dated ownership, λ* water value, cost measures) | ownership by date and share; λ* matches EDP within 6% | infrastructure | **Context** (data section) |
| Legs A–D, leg C β ≈ 3 | superseded; leg C = merit order, not conduct | superseded | **Out**; leg C as a footnote in the method appendix (still open from 19 Nov) |
| Italy, Great Britain as gas-cap controls | fail (five designs for Italy) | — | **App**, one paragraph |
| Gas-cap welfare, outage IVs, DA−ID premium, intraday, hedge ratios, clawback RDD, markups vs HHI, cogeneration, IVPEE, MIC near-miss, France link, FIT exits, own-wind surprise, start-up correction, heat demand | not needed for the demand story, or stopped | — | **Out** (stopped-designs table where they were designs) |
| Unit dispatch / fuel switching logits | no fuel-switching elasticity (U2–U4, U6 fail; F3, F6 fail) | stopped | **Out** |

---

## Part 2. Thesis outline (about 99,000 characters of main text)

Page counts are a rough guide; the binding budget is in characters: ch. 1 9k, ch. 2 11k, ch. 3 11k, ch. 4 8k,
ch. 5 11k, ch. 6 13k, ch. 7 15k, ch. 8 9k, ch. 9 7k, ch. 10 5k (in `scripts/qa/paper_charcount.py`). Figures and tables marked ✓ exist on disk; ○ have to be made.

**1. Introduction** — 4 pp.
The contrast first: large industry responds to the regulated period price (−0.15 to −0.32) and not at all to the
same-hour market price (zero), and more than low-voltage consumers (−0.11; households alone −0.05). The method:
replication as foundation, then extension, with every test registered before it was run. Contributions: (i) the first
firm-level response to the 2021 period calendar; (ii) the planned-versus-short-notice split (λ); (iii) the evidence
that the reform did not change market power or the price signal. Related literature woven in, not a separate chapter
(Enrich et al.; Fabra et al. 2021; Hirth, Khanna & Ruhnau; Ito; Jessoe & Rapson; Blonz; Burlig et al.).

**2. Setting: Spain's June 2021 tariff reform** — 5 pp.
2.0TD three periods; 3.0TD and 6.xTD six periods and the new period calendar; tolls, charges and the power term;
who pays the hourly price (PVPC vs free market; CNMC contract mix ~50% indexed; θ 0.32–0.49, gas-cap volume check
0.48). Figures: ○ period calendars old vs new (one panel per tariff); ○ price dose by tariff.

**3. The wholesale market and who sets the price** (supply context) — 5 pp.
MIBEL day-ahead auction, data (bids, dated ownership, costs). Who sets the price (44 / 16 / 23%). Offers sit near cost:
thermal (A) and hydro pooled (A), one table, one sentence on the price-taker benchmark. The hydro departure in one
paragraph with D1. The gas cap as a consumer price (ρ, adjustment charge). Direct consumers' stated slope. No
withholding detected. Figures: ✓ `price_monthly.png`, ✓ `generation_mix.png` or `vre_share.png`, ✓ `bid_curves.png`;
○ setter-share bar; table: conduct summary (5 rows).

**4. Framework** — 4 pp.
Equations D (planned response σ, short-notice share λ, exposure θ), S (offer = cost + β·markup), E (clearing). What the
reform is in the model (a change in τ). What each piece of evidence identifies (table from
`thesis-demand-supply-link.md` §3, updated). Worked example first (the plant at 20:00), then the algebra.

**5. Data and method** — 5 pp.
ESIOS demand by tariff, REN, temperature (MERRA-2/ERA5), holidays, GoiEner. The LASSO prediction (paper's per-hour
version). The six-summer prediction test and randomization inference; trend null vs mean null (**owed: 3.2**). Pre-
registration and stop rules; failures kept.

**6. Households and small business** — 6 pp.
Replication (Wald −0.06…−0.09, column 4 −0.10) as the check that the method works; six-summer E0 −0.116; households
alone −0.05 (GoiEner); PVPC vs free market; persistence 2021–25. Why the replication range sits below E0 −0.11
(**owed: 3.3**). Figures: ○ evening-vs-night event study; ○ six-summer placebo panel (exists in the supervisor page,
needs a script output); ○ persistence by summer. Table: replication vs paper.

**7. Firms: the period calendar** — 7 pp.
Large industry: the 2021 shift matches the new calendar hour by hour (✓ `hv_shift_2021_by_month.png`); regulated-price
elasticity −0.15 to −0.32; reduced form −1.0 pt/step; by tariff. Medium firms: persistence −0.025 (2022–25), 2021
alone rests on a drift. Large industry after 2021, stated plainly: the 2021 response does not persist in the
registered form (2022–25 −0.136 pts/step vs −1.0; R3, R5, R8 fail; only 6.3 keeps shifting). Small business not identified. Table: the
headline table (one estimator, all groups).

**8. Planned prices vs the hourly market price** — 4 pp.
Wind-speed instrument: zero for industry; T1: λ < 0.5–0.7, point ≈ 0; bid-curve instrument beside it. Why: period
charges and the power term bind, hourly prices are not seen or planned around (A1–A4 literature). Calendar-boundary
bounded null. Figure: ○ elasticity forest plot (all groups, both price types) — the single picture of the thesis.

**9. Through the market: validity** — 3 pp.
Price effect −2.6 €/MWh evening-minus-night (a quarter of the spread), net ≈ 0 for consumers; T2 market power
unchanged on average, moved across hours by < €1; T3 no feedback. Conclusion: the demand estimates can be read as
consumer responses, not equilibrium artefacts.

**10. Conclusion** — 2 pp.
Policy reading: regulated period prices move firm demand, real-time price exposure alone does not. Limits: one reform
year, bundled reform, aggregate series, Portugal as the only weather control.

**Appendices** (not counted):
A. Placebo table of every headline result, failures included (E3, E5, rules 7/8). B. Price-taker simulation and step
estimator. C. Hydro firm table and the June 2021 stop. D. Stopped designs, one line each with the reason. E. Area
panel and control dependence. F. CES and nested CES. G. Data traps that matter for replication.

---

## Part 3. Owed before or while writing

**Decisions for you (no run needed):**
1. ~~**Large industry after 2021.**~~ **Decided 26 Nov:** stated in ch. 7 as "the 2021 response does not persist in
   the registered form" (2022–25 −0.136 pts/step vs −1.0; only 6.3 shifts). No new design. The 2021 result stays the
   headline.
2. ~~**Which household number leads.**~~ **Decided 26 Nov:** the headline says "low-voltage consumers (−0.11)"
   (E0 = households and small business); ch. 6 gives −0.05 for households alone (GoiEner). Industry is 1.5–3× the
   low-voltage figure and 3–6× households alone.
3. ~~**Merge the business-demand branch.**~~ **Done 26 Nov:** PR #17 was already in `main`; this branch was
   fast-forwarded to `main`, which also brought PR #16 (prediction-model selection).
4. ~~**Page rules.**~~ **Settled 26 Nov:** 60,000–120,000 characters of main text; appendices, footnotes, sources and
   table of contents do not count. No template required; the skeleton uses the standard `report` class, author–year
   citations.

**Writing tasks (no estimation):**

5. **Trend null vs mean null (−0.15 vs −0.32).** Interpret the range: what each null assumes about the placebo drift
   (−0.038/yr, p 0.023, cause unnamed; solar ruled out).
6. **Why the replication range is smaller and narrower than E0 −0.11.** Candidates already named: training years
   (2018–20 vs 2014–20 leave-one-out), Wald ratio vs equation-4 η, within-year vs across-summer standard errors.
7. **Placebo table** of all results (appendix A). Built from existing outputs.
8. **Figures.** Most chapter figures (○ above) do not exist as script outputs yet; the supervisor page's two figures
   should be regenerated by scripts into `paper/figures/`.

**External, may arrive in time:**

9. CNMC energy by toll and period (due about 24 Dec, extendable to about 24 Jan): could identify small business. Plan
   the thesis without it.
10. Portuguese control (E-REDES/REN/ERSE): open, unlikely before February.

**Timeline sketch (10.5 weeks):**
- by 6 Dec: outline frozen; LaTeX skeleton built (done 26 Nov); figure scripts written;
- 7 Dec – 10 Jan: chapters 2–9 drafted (about one a week, holidays included);
- 11 – 24 Jan: introduction, conclusion, appendices;
- 25 Jan – 9 Feb: supervisor read, revisions, final Overleaf build.
