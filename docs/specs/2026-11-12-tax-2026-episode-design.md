# The 2026 electricity-tax cut (RDL 7/2026) as a demand event: confirmed facts, design and stop rules

**Status: written 2026-11-12, before any run.** Branch `tax-gascap-demand`. Companion to `2026-11-12-demand-redesign-options.md` (§8 found the episode) and
`2026-11-11-tax-change-design.md` (the 2021–24 tax steps, killed). Acronyms as there: VAT = value-added tax; IEE = *Impuesto Especial sobre la Electricidad*
(electricity tax); PVPC = regulated tariff; E0 = measured low-voltage demand; DiD = difference-in-differences; LASSO = penalised regression;
MDE = minimum detectable effect; CPI = consumer price index.

**In one example.** A household's bill of 100 before tax was 127.2 with VAT at 21% and IEE at 5.11%. From 22 March 2026 it was 110.6 (VAT 10%, IEE 0.5%), a fall of
14 log points: the same size as the whole of the 2021 cuts together, on a known day, for every customer under 10 kW. Prices had spiked
in mid-March and then fell, so this time the pre-tax price did not rise after the cut.

## 1. What the BOE says (read 2026-11-12 by a subagent from the BOE consolidated text, BOE-A-2026-6544, and the Agencia Tributaria page; I have not re-read the articles myself)

| item | text | source |
|---|---|---|
| VAT 10% | contracts with contracted power **below 10 kW**, any voltage, plus bono-social "vulnerable severo"; 22 March → 30 June 2026 | Art. 42 |
| IEE 0.5% | all consumers; floors €0.5/MWh industrial, €1/MWh other; 22 March → 30 June 2026 | Art. 40 |
| **Condition** | if the April 2026 electricity CPI does **not** exceed April 2025's by more than 15%, the cut "dejará de aplicarse en el mes de junio" | Art. 40.2, 42 |
| What happened | AEAT's table: IEE 0.5% from 22 March to **31 May**, back to 5.11% from 1 June (condition not met); VAT's end date read only from the article (no AEAT statement) | AEAT 16 Oct 2026 |
| Later decrees | RDL 18/2026 (29 June) lets the IEE reduced rate apply in August and September, RDL 25/2026 (29 September) in November and December, each on its own CPI condition; **BOE texts not read, VAT extension unknown** | AEAT only |
| Same decree, other | bono social discounts 42.5% / 57.5% for 2026; electro-intensive industry gets 80% off tolls (Art. 7, 2026); generation tax relief (Art. 41); no PVPC-specific provision found | Arts. 1, 7, 41 |

**Unread:** Arts. 9–32, 51–64, the final provisions (entry-into-force date taken from the AEAT table), and the 18/2026 and 25/2026 texts. Whether the VAT cut ended on
31 May with the IEE is **not confirmed**; it is the one fact the design needs and must be read before any run (step 0).

## 2. Steps and the tax factor

(1 + IEE)(1 + VAT): 1.2719 before; **1.1055 on 22 March** (−14.0 log points, S5); back to 1.2719 on **1 June** if both ended (+14.0, S6), or to 1.1055 + the IEE
only (+4.5) if the VAT ran to 30 June. Later August–December re-allowances are condition-driven and out of scope.
**Timing.** The decree was published 21 March and in force on 22 March, two days of notice; the end date was fixed by the April CPI rule, a function of a price index
published by mid-May. So both dates are known and neither responds to Spanish demand, but **S5 responded to the March price spike and S6 is set by the CPI**:
the same endogeneity-to-prices that killed 2021–22, mitigated because the pre-tax price fell after the cut. The IEE hits industry too, so **industry is not a
placebo**; E0 is almost entirely treated (the VAT cut covers contracts below 10 kW and the IEE all).

## 3. Data on disk, and what a refresh would add

| series | on disk to | refresh |
|---|---|---|
| E0, ESIOS 1201 (measured) | 2026-04-30 (5.5 weeks after S5) | published about six months late; none possible |
| ESIOS 352, 351, 353 (scheduled) | 2026-11-09 | none needed |
| PVPC energy term ESIOS 1001 | 2026-04-30 | refetch (needs the ESIOS token) |
| OMIE day-ahead price, REN Portugal load | 2026-05-31 | refetch (token-free): extends the Portuguese control past S6 |
| RTE France load | 2026-08-31 | none needed |
| temperature | on disk to 2026-05 | refetch if S6 is run |

S5 can be gated on what is on disk. S6 needs the refetches (step 0) and has no measured E0, so it uses 352 and 351 (scheduled, a forecast) against Portugal or France.

## 4. Design

Level effect on log demand relative to a control (no hour-of-day contrast: a tax scales every hour alike). Treated: E0 (S5 only), 352, 351. Controls: Portugal (REN), France (RTE),
and for S6 only France if Portugal is not refetched. Estimators: the DiD on the log difference with hour, weekday and month effects and temperature/holiday differences,
**and the paper's per-hour LASSO prediction errors, trained on 2021-10-01 → the break** (four-plus years of post-reform data, the
long, stable pre-period that the 2022 event lacked, `w23908`'s condition). Elasticity: Δ ln demand ÷ Δ ln tax-inclusive price (observed PVPC × tax factor), reported also
with the tax factor alone as the instrument.

## 5. Steps and stop rules, set now (each needs the user's go-ahead)

**Step 0, read and refresh (no estimation).** Read Arts. 40 and 42 and the final provision myself, and the 18/2026 and 25/2026 texts for the VAT; confirm the VAT end date.
Refetch 1001, OMIE prices, REN, temperature. **Stop** if the VAT cut did not end with the IEE and the dates cannot be fixed.

**Step 1, price gate, no demand series.** Windows 28 days pre, 35 post (S5; S6 likewise). Placebo breaks: 1st and 15th of each month 2025-02 → 2026-01 (VAT 21% and IEE 5.11% throughout, so no tax step).
- **G1** the tax-inclusive PVPC energy term changes by ≥ 0.10 in absolute log points and beyond the placebo 95th percentile (expected near −0.14 plus the pre-tax move).
- **G2** the pre-tax PVPC term does **not** rise by more than 0.05 across the break (S5: it should fall; a rise is the 2021 confounding again).
- **G3** the tax factor's share: |tax part| ≥ half of |total price change|, so the tax, not the wholesale move, drives the price the household sees.

**Step 2, power gate on placebo breaks only; real window sealed.** DiD and LASSO-error placebos of E0, 352, 351 against Portugal at the same 24 breaks, level effect.
Implied effect = 1.4% (elasticity −0.1 on 14 points; at −0.5, 7%). MDE = 2.8 × placebo sd.
- **P1** MDE ≤ 0.7% → run as an estimate. **P2** MDE ≤ 7% → run as a bound only. **P3** otherwise kill.
- Honest expectation: the 2021–22 placebo sd for E0 was 1.1% over four-month windows; a 35-day window is noisier, so P2 at best. The longer LASSO training is the thing that might change that.

**Step 3, the real events.** Only after Step 2, rules in order: (1) sign: S5 raises demand relative to the control, S6 lowers it; (2) elasticity between −0.5 and 0 (a plausibility band, not a derived
bound: published short-run elasticities are about −0.1 to −0.4; the unrestricted value is also reported); (3) real effect outside the placebo 5–95% range and in the top 2 of the placebo set; (4) Portugal and France controls agree within two combined
standard errors; (5) E0 and 352 agree in sign; (6) S6 reverses S5 within a factor of two (S6 only if the VAT end is confirmed); (7) dropping the first week after each break (a billing lag) leaves the sign. Stop unless 1–5 pass.

## 6. Threats written down

The March price spike and the Middle East war (a demand-side shock to industry in Spain, not Portugal?); the cut coincides with the end of the winter heating season; the pre-tax price still moved and 352
(PVPC) reacts to it hourly; households see the tax change on bills, which arrive after a month or two; the IEE hits industry, so a household-only effect cannot be isolated; the March 2026 bono-social and
electro-intensive measures start earlier (1 January) and are not step changes in the window; Portugal had its own measures in 2026 (not checked).
