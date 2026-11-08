# Conduct evidence table (2026-11-08)

One place for every estimate that says how close Iberian firms are to **price-taking** (offering at cost) or to
**Nash** conduct (the markup a profit-maximising firm with its share and residual demand would set), and how much of
the gas-cap subsidy reached offers. Built by reading all 35 running notes (three readers, each row checked against its
note by a second reader); figures are the current ones (ownership rebuild of 2026-10-27/28, ten seeds). The headline
table below picks the rows the paper can stand on; the full register of 80 rows, with the verifier's corrections, is
at the end.

**How to read β.** In the offer designs β is the share of the Nash markup a firm adds: β = 0 is price-taking, β = 1
is Nash. Example: a firm whose Nash markup on a step is €4/MWh and that offers €1 above cost has β = 0.25. "Nash
rejected" means the 95% interval excludes 1; "price-taking rejected" means it excludes the simulated price-taker band
(the simulation matters because the estimator is biased even for true price-takers: they give about −0.14 to −0.26
without the correction). For the gas cap, ρ is the share of the subsidy passed into offers or declared costs (1 = all).

**Evidence grade.** A = passes every check fixed before running; B = passes, with a stated weakness; C = a lead only.

## 1. Headline table

### Claim 1 — Offers are close to price-taking; Nash is rejected

| # | What | Sample | Estimate [95%] | Price-taker band | Nash rejected | Price-taking rejected | Grade |
|---|---|---|---|---|---|---|---|
| 1.1 | Gas and coal step prices (step estimator, simulation-corrected) | 2019–23, 78 units | β +0.01 [−0.08, 0.10] | +0.02 … +0.06 | yes | no; **price-taking accepted** within δ = 0.1 (equivalence) | A |
| 1.2 | Same, by period: 2019–21H1 / 2021H2–23 | | −0.06 [−0.16, 0.05] / −0.03 [−0.13, 0.06] | −0.20 … −0.14 / — | yes | no (2021H2–23 accepted within δ) | A |
| 1.3 | Hydro step prices, pooled | 2019–2025-09, ~46 units, 6 groups | β +0.06 [−0.05, 0.15] | −0.00 … +0.09 | yes | no | A |
| 1.4 | Hydro, crisis | 2021H2–23 | β +0.00 [−0.13, 0.13] | +0.00 … +0.10 | yes | no (not accepted within δ either) | B |
| 1.5 | Hydro, after the cap | 2024–2025-09 | β +0.19 [0.08, 0.33] | −0.06 … +0.09 | yes | no — **narrowly** (one seed of ten reaches the set) | B |
| 1.6 | Hydro offer at its expected running share (fixed-step design) | 2019–2025-09, 34 units | slope 0.155; gap +0.13 [−0.10, 0.36] | ten seeds | yes | no, in every cell but 2023 (Iberdrola) | B |

### Claim 2 — One departure: hydro before the 2021 crisis, carried by Iberdrola

| # | What | Sample | Estimate [95%] | Price-taker band | Nash rejected | Price-taking rejected | Grade |
|---|---|---|---|---|---|---|---|
| 2.1 | Hydro step prices | 2019–2021H1 | β +0.25 [0.15, 0.34]; gap +0.29 [0.13, 0.46] | −0.12 … +0.02 | yes | **yes**, by 0.13 (≈3 seed sd) | B |
| 2.2 | Its size | same | €0.98/MWh [0.44, 1.53] on price-setting steps (Iberdrola €1.49, EDP €0.86); **effect on the price −€0.01** | | | | B |
| 2.3 | When it stops | months 2021-04 → 08 | gap 2021-05 +0.24 [0.04, 0.46], 2021-06 −0.13 [−0.41, 0.23] | | | | C |

Weaknesses, stated: without Iberdrola it is −0.01 [−0.12, 0.10]; the fixed-step design (1.6) does **not** find it in
2019–21H1 and finds instead a 2023 Iberdrola departure; the stop falls between the clawback announcement (1 June
2021), the move of the offer limits off €0–180.30 (7 July) and the start of the gas crisis — a coincidence of dates,
not a test. Read: a small markup on a few steps that does not reach the price.

### Claim 3 — No quantity withholding detected

| # | What | Sample | Estimate [95%] | Nash value | Nash rejected | Price-taking rejected | Grade |
|---|---|---|---|---|---|---|---|
| 3.1 | Nuclear cuts beyond a price-taker's | 2019–2026-05, 16,326 reactor-days | β −0.19 [−1.00, 0.63] (MDE 1.16) | 1 | yes | no | B (power) |
| 3.2 | Same, cap period | 2022-06-15 → 2023-12 | β +0.01 [−0.45, 0.47] (MDE 0.66) | 1 | yes | no | B (cap confounded with gas crisis) |
| 3.3 | Firms' net auction position when own wind rises | 2019–25 weekdays, 5 firms | +0.275 MW per MW of own wind [0.13, 0.42] | −0.217 | yes (6.8 se) | yes, but the wrong way for withholding | B (post-hoc reading of the retail leg) |
| 3.4 | Generation on own customers' regional holidays | 2019–2025-09, 5 firms | β −0.20 [−0.55, 0.15] | 1 | yes | no | B |
| 3.5 | Unoffered hydro capacity and the incentive | 2019–2025-09, 13 Spanish units | +0.15 pp of capacity per sd [0.05, 0.25]; every pooled interval below 0.55 pp | — | — | the pre-fixed bar (1 pp) not reached | B |
| 3.6 | Gas/coal fault starts and the owner's stake | 2018–2026, 39,758 unit-days | −0.0014 pp per €/MWh of X, p 0.86 | — | — | no | B |

### Claim 4 — The gas cap reached declared costs almost one-for-one, offers by somewhat less

| # | What | Sample | Estimate [95%] | Grade |
|---|---|---|---|---|
| 4.1 | Declared variable cost (minimum-income term), jump on 15 June 2022 | 50 Iberian gas units | −0.544 log points; full pass-through −0.721; placebo dates ±0.125 | A |
| 4.2 | Declared cost, pass-through | June 2022 → Jan 2023 | ρ 0.91 [0.86, 0.96]; 0.92–1.00 in Jun–Oct 2022 | A |
| 4.3 | Offers: capacity offered within €20 of net cost, dose-response against Italy | 49 Iberian / 44 Italian units, 92 weeks | ρ 0.73 [0.51, 1.03]; with gas-price controls 0.54–0.85; with physical-supply controls 0.76 [0.62, 0.92] | B (depends on whether Iberian offers respond to gas apart from the subsidy; LNG channel ruled out, storage uninformative) |
| 4.4 | Offers minus declared costs | same, 8 of 10 firms | d +0.19 [−0.12, 0.38] | B (not distinguishable from 0) |
| 4.5 | Declared start-up cost as a share of the static price–cost gap | 84 plants, 2019–24 | 5–13% (fixed term); up to 28–70% with the variable term | B (bound; declarations are strategic) |

## 2. What the table supports, and what it does not

- **Supported (A/B rows):** across thermal and hydro offers, and across four quantity margins, every interval excludes
  Nash and almost every one includes the price-taker band. The cap's subsidy reached declared costs at 0.9–1.0 and
  offers at 0.5–1.0.
- **One exception:** hydro 2019–21H1, a markup of about €1/MWh on price-setting steps, resting on one firm, with no
  effect on the price, and not reproduced by the second hydro design.
- **Not supported:** "price-taking" as a positive finding outside rows 1.1–1.2 (thermal), where an equivalence test
  was fixed in advance. Elsewhere the reading is "no departure detected", with the interval as its size.
- **Open conflicts to settle in the write-up** (from the readers): (i) the two hydro designs disagree on where the
  departure is (2.1 vs 1.6); (ii) leg D's buyer markdown (β− 0.19, no interval) conflicts with the simulation, which
  finds no stable buyer pattern, and with the fixed step, which traces it to contract routing; (iii) the
  reactor-outage instrument gives a price-taker band near 0 in its own design but −0.40 / −0.59 in the step estimator;
  (iv) the welfare figures use ρ 0.55 / 0.73 / 1.0 — the corrected band (0.54–0.85) is covered by that grid.

## 3. Full register (80 rows, with the verifier's corrections)

Rows are as extracted; where the verifier corrected or superseded a figure, the correction follows the row and
**takes precedence**. "Missing" lists give estimates the verifier found that the extraction left out; they were not
re-verified.

### A. Offer prices (thermal and hydro)

**O1. Do hydro step prices rise with the firm's stake, beyond what price-takers show?**  
storage and pumped hydro offer steps (price-setting); Step estimator, at-cost instrument (Zb = firm's markup term on its curve moved to cost), unit x month effects, slope-per-unit selection control, read against band of 10 simulated price-taker seeds. Sample: 2019-01 to 2025-09, ~46 hydro units of six groups, price-setting steps; rebuilt on corrected ownership 2026-10-27.  
Estimate: beta +0.06 (price-takers' mean +0.04). Interval: Anderson-Rubin set [-0.05, 0.15]; ten-seed price-taker band -0.00 to +0.09. Benchmarks: beta = 0 price-taking (offer at water value), beta = 1 supply-function Nash; 'differs' only if the AR set misses the simulated price-taker band.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: Ten seeds pass; simulation shows uncorrected at-cost IV is biased negative (price-takers give -0.14). Within-day (unit x day) -0.23 [-0.45, -0.06] against band -0.15 to -0.04, does not differ and is within delta = 0.1.  
Source: notes/rq-price-taking-simulation.md, §18 Ten seeds (2026-10-28).

**O2. Did hydro depart from price-taking before the 2021 crisis?**  
storage hydro offer steps, 2019 to mid-2021; Same simulation-corrected step estimator (at-cost IV, level control), period cell. Sample: 2019-01 to 2021-06, hydro price-setting steps; ADOURO left out over Movhera window.  
Estimate: beta +0.25; gap over price-takers +0.29. Interval: AR set [0.15, 0.34]; bias-adjusted gap [0.13, 0.46]. Benchmarks: beta = 0 price-taking, beta = 1 Nash; gap is actual minus price-takers' mean.  
Nash rejected: yes. Price-taking rejected: yes. Status: current. Checks: Clears ten-seed band by 0.13 (about 3 seed sd). Survives leaving out any firm except Iberdrola (without Iberdrola -0.01 [-0.12, 0.10], touches band). Survives planted firm water value, all four 6-hour blocks, interior-fill days, conventional storage only. Was +0.31 before ownership fix.  
Source: notes/rq-price-taking-simulation.md, §18 Ten seeds; §17 Rebuilt on corrected ownership.

**O3. Did hydro depart from price-taking after the gas cap (2024-2025)?**  
storage and pumped hydro offer steps, 2024-2025; Same simulation-corrected step estimator, period cell. Sample: 2024-01 to 2025-09, hydro price-setting steps.  
Estimate: beta +0.19; gap +0.17. Interval: AR set [0.08, 0.33]; bias-adjusted gap [-0.01, 0.39]. Benchmarks: beta = 0 price-taking, beta = 1 Nash.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: One seed of ten (+0.091) reaches past the set's lower end, so 'does not differ' narrowly (was 'differs' on 2-3 seeds, now superseded). No post-cap half-year departs on ten seeds; only 06-11h block, sample without EDP, and buyers 2024H2 still depart.  
Source: notes/rq-price-taking-simulation.md, §18 Ten seeds.

**O4. Did hydro depart from price-taking during the 2021-2023 crisis?**  
storage hydro offer steps, crisis; Same simulation-corrected step estimator, period cell. Sample: 2021-07 to 2023-12.  
Estimate: beta +0.00. Interval: AR set [-0.13, 0.13]; bias-adjusted range -0.23 to +0.13. Benchmarks: beta = 0 price-taking, beta = 1 Nash; equivalence accepts price-taking if upper end < 0.1.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: Ten seeds: no longer accepted as price-taking within delta = 0.1 (was accepted on two seeds after rebuild). Neither departs nor shown price-taking.  
Source: notes/rq-price-taking-simulation.md, §18 Ten seeds.

**O5. When does the pre-crisis hydro departure appear and stop?**  
storage hydro offer steps, by half-year and month; Same simulation-corrected step estimator, half-year and single-month cells, ten seeds. Sample: half-years 2019H1-2025H1; months 2021-04 to 2021-08.  
Estimate: gap 2020H2 +0.30, 2021H1 +0.35; month gap 2021-05 +0.24, 2021-06 -0.13. Interval: 2020H2 [0.07, 0.52]; 2021H1 [0.07, 0.65]; 2021-05 [0.04, 0.46]; 2021-06 [-0.41, 0.23]. Benchmarks: gap = actual minus price-taker mean; 0 = price-taking.  
Nash rejected: not tested. Price-taking rejected: yes. Status: current. Checks: Only 2020H2 and 2021H1 differ on ten seeds (2019H1, 2020H1, 2025H1 no longer). Stop between May and June 2021 coincides with clawback announcement (1 June 2021); single months wide, a coincidence of dates, not a test. Seller/buyer split: seller 2020H1 +0.53 [0.09, 0.95], 2020H2 +0.38 [0.03, 0.69] differ.  
Source: notes/rq-price-taking-simulation.md, §18 Ten seeds and §19 The month the departure stops.
> Verifier: Interval column mixes kinds: for 2021-05 and 2021-06 the bracketed figures are the bias-adjusted ranges of the gap; the AR sets of the actual beta are [0.13, 0.36] (2021-05, beta +0.24) and [-0.27, 0.15] (2021-06, beta -0.08). Label them as such. Also 2021-04 departs: gap +0.71 [0.10, 1.25] (§19).

**O6. How large is the 2019-2021H1 hydro departure in euros?**  
hydro markup on price-setting steps and on the market price; Bias-adjusted beta times Cournot markup term per step, weighted by draws in which step sets price. Sample: 2019-01 to 2021-06 (and 2024-2025), ten seeds.  
Estimate: EUR 0.98/MWh on price-setting steps when net seller (Iberdrola 1.49, EDP 0.86); price effect -EUR 0.01/MWh. Interval: steps [0.44, 1.53]; price none. Benchmarks: 0 = price-taking; full Cournot markup would be X (mean EUR 3.7 when net seller).  
Nash rejected: not tested. Price-taking rejected: yes. Status: current. Checks: 2024-2025: EUR 2.08 [-0.13, 4.66] on steps, +EUR 0.08 [-0.005, 0.17] on price, both ranges reach zero. Price effect is an upper bound.  
Source: notes/rq-price-taking-simulation.md, §18 Ten seeds (§12 size).
> Verifier: 'mean EUR 3.7 when net seller' (X-tilde) is from §12 as first written (pre-rebuild); §17/§18 do not restate it. Flag as pre-rebuild. Price-effect sign: 2019-2021H1 is -EUR 0.01 (was +0.01 before rebuild), 'nil'.

**O7. Are gas and coal step prices those of price-takers?**  
thermal (gas and coal) offer steps; Simulation-corrected step estimator: at-cost IV, unit x month and fuel x hour effects, level control, two simulated seeds. Sample: 2019-2023, 78 gas/coal units with plant-specific efficiency, price-setting steps.  
Estimate: beta +0.01. Interval: AR set [-0.08, 0.10]; band +0.02 to +0.06; bias-allowed range -0.14 to +0.08. Benchmarks: beta = 0 price-taking, beta = 1 Nash; price-taking accepted if bias-allowed upper end < delta = 0.1.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: Equivalence test accepts price-taking (pooled, five firms, 2021H2-2023). Thermal stays on two seeds (three in doubtful period). Rebuild on corrected ownership moved no thermal estimate by more than 0.01. Unit x day +0.09 [-0.03, 0.20], not shown price-taking.  
Source: notes/rq-price-taking-simulation.md, §6 and §7; §17 confirms no change.

**O8. Did thermal offers depart from price-taking in 2019-2021H1?**  
thermal offer steps, 2019 to mid-2021; Simulation-corrected step estimator, period cell, three seeds. Sample: 2019-01 to 2021-06, gas/coal steps.  
Estimate: beta -0.06. Interval: AR set [-0.16, 0.05]; three-seed band -0.21 to -0.14. Benchmarks: beta = 0 price-taking, beta = 1 Nash.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: Looked like a departure on two seeds; third seed and the ownership rebuild make the set touch the band, so no departure on any number of seeds. Correction works worst here (null -0.18 to -0.21).  
Source: notes/rq-price-taking-simulation.md, §6 (third seed) and §17.
> Verifier: Band after the ownership rebuild: §17 says the two seeds moved from -0.175 / -0.206 to -0.144 / -0.196; with seed 3 (-0.141) the band is about -0.20 to -0.14, not -0.21 to -0.14. The quoted row is the §6 pre-rebuild row; §17: 'The actual set [−0.16, 0.05] now touches the two-seed band as well as the three-seed one (§6), so thermal 2019 – 2021H1 does not depart on any number of seeds.'  
> Later figure: notes/rq-price-taking-simulation.md §17: seeds -0.144 / -0.196 (two-seed), actual -0.06 [-0.16, 0.05] unchanged

**O9. Uncorrected at-cost IV: do thermal step prices follow the firm's stake?**  
thermal offer steps; Step estimator with at-cost instrument (F 200-700), no selection control. Sample: 2019-2023, 78 gas/coal units.  
Estimate: beta -0.27 (unit x month); -0.08 (unit x day). Interval: [-0.37, -0.18]; unit x day [-0.19, 0.02]. Benchmarks: beta = 0 price-taking, beta = 1 Nash.  
Nash rejected: yes. Price-taking rejected: yes. Status: superseded. Checks: Superseded 2026-10-08: simulated price-takers (true beta 0) reproduce -0.26/-0.21 and the sign flip with fixed effects, so the negative sign is the estimator. Bound below 1 survives.  
Source: notes/rq-step-estimator.md, §7 and §8 Rebuilt on corrected ownership.
> Later figure: Uncorrected at-cost 2019-2021H1 rebuilt: -0.04 [-0.12, 0.03] (was -0.03); coal -0.08 [-0.57, 0.19] (was +0.04) — rq-step-estimator.md §8

**O10. Uncorrected at-cost IV: do hydro offers over water value follow the stake?**  
storage hydro offer steps against water value λ*30s; Leg B in levels, at-cost instrument Zb, unit x month effects, no selection control. Sample: 2019 to 2025-09, 46 hydro units.  
Estimate: beta -0.23 (rebuilt). Interval: [-0.32, -0.16], F 394. Benchmarks: beta = 0 price-taking, beta = 1 Nash.  
Nash rejected: yes. Price-taking rejected: yes. Status: superseded. Checks: Superseded by simulation: price-takers give -0.14 [-0.18, -0.09], so the negative sign is mostly the estimator. 2019-2021H1 at cost +0.03 [-0.06, 0.12] after rebuild (was +0.14).  
Source: notes/rq-leg-b-levels.md, §5 and §8; notes/rq-price-taking-simulation.md §2.
> Later figure: 2024-2025-09 at cost rebuilt -0.17 [-0.26, -0.07]; net sellers/buyers -0.36 / -0.03 (rq-leg-b-levels.md §8)

**O11. With reactor outages as instrument, do thermal step prices follow the stake?**  
thermal (gas/coal) price-setting steps; Step estimator (resampled residual demand), X instrumented by owner's planned and unplanned reactor-outage doses. Sample: 2019-2023, 228,090 unit-steps, 78 units; rebuilt 2026-10-27.  
Estimate: beta +0.07. Interval: AR set [-0.67, 1.02], F 9.7. Benchmarks: beta = 0 price-taking, beta = 1 Nash.  
Nash rejected: no. Price-taking rejected: no. Status: current. Checks: Weak first stage (F about 10); only four reactor-owning firms identify. Simulated price-takers with this instrument give -0.59 [-1.60, 0.04], so also contaminated (simulation §2). p(beta = 1) was 0.053 before rebuild.  
Source: notes/rq-step-estimator.md, §3 and §8 Rebuilt on corrected ownership.

**O12. Same outage-instrumented thermal design, in the strong-instrument period**  
thermal price-setting steps, 2019 to mid-2021; Step estimator, reactor-outage IV, period cell. Sample: 2019-01 to 2021-06.  
Estimate: beta -0.19. Interval: AR set [-0.64, 0.17], F 22.0. Benchmarks: beta = 0 price-taking, beta = 1 Nash.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: Strongest first stage of the outage design (F 22). Before rebuild -0.16 [-0.60, 0.19], p(beta = 1) 2e-7.  
Source: notes/rq-step-estimator.md, §3 and §8.

**O13. Within the day, do hydro step prices move with the firm's stake?**  
storage and pumped hydro steps, within unit-day; Step estimator, unit x day effects (water value differenced out); instruments regional wind deviation or reactor outages. Sample: 2019-01 to 2025-09, 442,208 main-sample price-setting steps after rebuild.  
Estimate: beta -0.10 (regional wind); +0.04 (outages). Interval: regional wind [-0.60, 0.36], F 13.4; outages [-0.90, 0.36], F 5.0. Benchmarks: beta = 0 price-taking, beta = 1 Nash.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: Firm x forecast instruments (strong, F 45-127) fail: AR sets empty in every sample, not read. Outage first stage weak.  
Source: notes/rq-step-estimator.md, §6 and §8.

**O14. Are thermal step lengths chosen strategically?**  
thermal step lengths (gap draws); Kastl step-length moment, reactor-outage IV. Sample: 2019-2023 gas/coal steps, gap draws.  
Estimate: beta -0.84 (se 0.27). Interval: [-1.58, -0.17], F 21.9. Benchmarks: beta = 0 price-taking, beta = 1 Nash.  
Nash rejected: yes. Price-taking rejected: yes. Status: failed a check. Checks: Wrong sign; condition assumes lengths re-chosen, but step boundaries repeat day to day (82% in June 2019). Read as lengths set by the plant, not conduct.  
Source: notes/rq-step-estimator.md, §3 Results (Length of a step).
> Verifier: The note does not call it a 'Kastl' moment; it says 'Length of a step' / 'the length condition'. §8 rebuild table does not list this row, so it is the pre-rebuild figure.

**O15. At one fixed point of each hydro ladder, does price follow the stake?**  
storage hydro offer read at expected running share (fixed step); Fixed-step slope on Zb by least squares, unit x month and hour effects, week clusters, read against ten simulated price-taker seeds. Sample: 2019-01 to 2025-09, 359,156 main-sample unit-hours, 34 storage units; reruns on corrected ownership 2026-10-21/22.  
Estimate: slope 0.155 (after Castejon rerun); gap over price-takers +0.13. Interval: bias-adjusted gap [-0.10, +0.36] (pre-rerun); ten-seed band -0.04 to +0.11. Benchmarks: slope 0 = price-taking, 1 = Nash.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: Ten seeds; placebo (bottom 5% of ladder) passes; but slope present where the step cannot set the price (+0.23 [0.09, 0.38] over band) and not robust (net of contracts +0.09; unit x hour-of-day +0.12). Volume withholding negligible (-0.5 points of capacity per sd).  
Source: notes/rq-fixed-step.md, Ten seeds (2026-10-20) and Rerun for Castejon (2026-10-22).
> Verifier: Gap +0.13 and range [-0.10, +0.36] are from the ten-seed table at slope +0.17 (before both reruns); after the 2026-10-22 rerun the slope is 0.155 and no reading changes, but the gap/range were not restated. State that.

**O16. Is the 2023 hydro departure at the fixed step one firm's?**  
storage hydro fixed-step reads, 2023 half-years; Fixed-step slope, half-year cells, ten seeds, with and without Iberdrola. Sample: 2023H1 and 2023H2.  
Estimate: gap +0.90 (2023H1), +1.51 (2023H2). Interval: [+0.01, +1.67] / [+0.54, +2.53]. Benchmarks: 0 = price-taking, 1 = Nash.  
Nash rejected: no. Price-taking rejected: yes. Status: current. Checks: Without Iberdrola both half-years fall inside the band. Fixed step finds no 2019-2021H1 departure (its 2020H2 seller departure went at ten seeds), contrary to the step estimator.  
Source: notes/rq-fixed-step.md, Ten seeds (2026-10-20), What ten seeds change.

**O17. Does Iberdrola mark down hydro when it is a net buyer?**  
Iberdrola storage hydro fixed-step read in buyer hours; Fixed-step slope on Zb in Iberdrola buyer hours, holding bilateral (own-retail contract) share fixed, ten seeds. Sample: Iberdrola buyer hours (about 21-22% of its main-sample hours), 2019-2025.  
Estimate: +0.82 with bilateral share held (raw Zb alone gap +1.55). Interval: held: [+0.20, +1.43], bias-adjusted [-0.10, +1.75]; raw gap [+0.40, +2.69]. Benchmarks: 0 = price-taking, 1 = Nash markdown.  
Nash rejected: no. Price-taking rejected: no. Status: current. Checks: Raw slope differs from band but mostly routing: in most-buying hours 131 MW leaves contracts and 130 MW more is offered in the auction. 'Price-motive signature' (Zb with n) withdrawn at ten seeds. Seller side: +6.8 EUR per GW of position [3.2, 10.6], position not stake, read as book management.  
Source: notes/rq-fixed-step.md, Ten seeds, Iberdrola's contracts with its own retailer.

**O18. Across days, do hydro offers over water value follow the stake (outage IV)?**  
storage hydro steps minus λ*30s; Leg B in levels, reactor-outage doses instrument X, unit x month effects. Sample: 2019 to 2025-09, about 661k price-setting steps, 46 units; rebuilt 2026-10-27.  
Estimate: beta -0.27. Interval: AR set [-0.74, 0.04], F 21.0. Benchmarks: beta = 0 price-taking, beta = 1 Nash.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: Simulated price-takers with this instrument give -0.40 (F 14, set empty), so contaminated. 2024-2025 weak (F 2-3). Outages plus wind give sets below zero but empty with λ*90, not read.  
Source: notes/rq-leg-b-levels.md, §3 and §8 Rebuilt on corrected ownership.
> Verifier: Sample count: 661,575 price-setting steps is the pre-rebuild §3 figure; after the rebuild the step estimator's hydro rows are 646,232 (rq-step-estimator.md §8). Leg B §8 does not restate its own count. Write 'about 646k after rebuild (661,575 before)'.

**O19. Does price minus thermal cost follow the firm's markup term?**  
market price minus implied gas/coal cost at units at their margin; Leg C: p - c on X, rivals' offered wind and solar as instruments, unit effects. Sample: 2018-2023, 363,867 unit-periods (dated owners), 67 units.  
Estimate: beta 3.094. Interval: AR set [2.574, 3.627], F 69.0. Benchmarks: beta = 0 price-taking, beta = 1 Nash; above 1 = more than Nash.  
Nash rejected: yes. Price-taking rejected: yes. Status: failed a check. Checks: Not conduct: other owners' p - c falls as much with zero movement in X (merit order, Bresnahan identification problem). Unstable across years, slope floor, which part of X moves. Own-step-at-price diagnostic 0.839 [0.489, 1.476] solar-only, selected on price.  
Source: notes/rq-leg-c-thermal-cost.md, header, §6 and §7 Rerun on owners by date.
> Verifier: Sample: '67 units' belongs to the static run (335,545 unit-periods on 67 units, §2); the dated run has 363,867 unit-periods and no unit count is stated (§7). Also it is 'Specification 1' (cost imposed, plant-specific efficiency). Own-step-at-price diagnostic 0.839 [0.489, 1.476] is the solar-alone row; both instruments 0.802 (empty set as of static run).

**O20. Does the shape of offers respond to the stake, net of price-takers' response?**  
share of unit capacity offered at or below unit-day median price (all dispatchable units of five firms); Leg D: REE day-ahead wind and solar forecasts instrument X, unit x day and hour x year-month effects, outcome net of fringe's response; one common slope. Sample: 2019-01 to 2026-05, 5,171,005 unit-hours of EDP, Endesa, Iberdrola, Naturgy, Repsol; dated owners 2026-10-03.  
Estimate: beta 0.024. Interval: AR approx [0.00, 0.05] (slope c AR set [-0.185, -0.015]); F 60.1. Benchmarks: beta = 0 price-taking, beta = 1 Nash (slope scaled by offer density).  
Nash rejected: yes. Price-taking rejected: yes. Status: current. Checks: Overidentification p 0.92. Placebo: fringe thermal responds to forecasts as the firms do, so raw offers fail exclusion (raw beta -0.068, wrong sign); result depends on fringe being a valid price-taking benchmark.  
Source: notes/rq-leg-d-sign-of-n.md, §7 and §8 Rerun on owners by date.

**O21. Do firms mark up when selling and mark down when buying?**  
offer shape, separate slopes for net seller and net buyer hours; Leg D forecast design, two slopes with forecasts x firm first stage, net of fringe. Sample: 2019-01 to 2026-05, five firms.  
Estimate: beta+ -0.014 (seller), beta- 0.186 (buyer). Interval: none (2SLS only; static gamma- se 0.087); F 39/34. Benchmarks: Nash predicts equal slopes; beta 0 price-taking, 1 Nash.  
Nash rejected: not tested. Price-taking rejected: yes. Status: current. Checks: Equality rejected p < 0.001; separation rests on differences between firms (Endesa buyer almost always) and ten exclusion restrictions; no AR projection.  
Source: notes/rq-leg-d-sign-of-n.md, §7.3 and §8.

**O22. Within the day, does EDP's storage hydro curve shift with its markup term?**  
EDP storage hydro offer price at 50% of offered volume; Leg A: unit x day effects remove water value, X instrumented by others' offered solar, hour x year-month effects. Sample: 2018-2026-06, EDP storage units, about 550,883 unit-periods; dated owners 2026-10-05.  
Estimate: beta 0.089. Interval: AR [-0.13, 0.33]. Benchmarks: beta = 0 flat curve (price-taking), beta = 1 Nash.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: Holds on exposed net position and dated owners. Not rebuilt on the 2026-10-21/22 ownership fixes. Four EDP cascades offer identical curves all day.  
Source: notes/rq-midday-hydro.md, §3.21 Owners by date and share.

**O23. Does the top quarter of EDP's hydro curve follow the markup term from 2024?**  
EDP hydro offer price at 75% of offered volume, 2024-2026; Leg A within-day IV, period cell. Sample: 2024-2026, EDP storage units.  
Estimate: beta 2.23. Interval: AR [1.26, 3.56]. Benchmarks: beta = 0 price-taking, beta = 1 Nash; above 1 cannot be a markup.  
Nash rejected: yes. Price-taking rejected: yes. Status: failed a check. Checks: Confined to two cascades (Tejo-Mondego, Mondego) with betas far above 1; read as exclusion failure, not conduct. Fixed-tranche subsample top -0.10 [-0.69, 0.40], rejects Nash. Price-setting version 3.71 [2.67, 5.72] invalid (selection).  
Source: notes/rq-midday-hydro.md, §3.12 and §3.21.

**O24. Do EDP's reshaping cascades offer less below a fixed price when the stake is high?**  
capacity offered at or below unit-day median price, three reshaping EDP cascades; Leg A read horizontally, solar IV, unit-day effects. Sample: 2024-2026, Douro, Mondego, Tejo-Mondego.  
Estimate: -0.137 pp of capacity per EUR/MWh of X; implied beta 0.07 (by cascade 0.14/0.03/0.09). Interval: coefficient AR [-0.24, -0.06]; implied beta none. Benchmarks: 0 = price-taking; negative = market-power sign; implied beta scaled so 1 = Nash.  
Nash rejected: not tested. Price-taking rejected: yes. Status: current. Checks: Correctly signed but implied beta 3-14% of Nash is a scale, not an estimate; small-storage physics and exclusion doubts (two cascades) offer a competitive reading.  
Source: notes/rq-midday-hydro.md, §3.14 and §3.21.

**O25. Does Iberdrola allocate water across hours like a price-taker?**  
Iberdrola storage hydro total scheduled energy by hour (all routes); Ranking fit: overlap of actual allocation with benchmark ranking hours by p - beta X, beta grid. Sample: 2018-2026, Iberdrola storage units, by era.  
Estimate: best beta -0.5 / -0.25 / -0.5 (2018-20 / 2021-23 / 2024-26). Interval: none. Benchmarks: beta = 0 price-taking ranking, beta = 1 Nash ranking.  
Nash rejected: not tested. Price-taking rejected: no. Status: current. Checks: Validation on EDP stable cascades passes (best beta 0). Descriptive, no inference; Nash ranking fits worse (overlap 0.802/0.708/0.676). IV version fails validation.  
Source: notes/rq-midday-hydro.md, §3.15 and §3.21.

**O26. Across days, does EDP's daily water value follow its markup term?**  
EDP large-reservoir daily median offer (λ̂50); Leg B first pass: day-mean X instrumented by day's offered solar, unit x week effects. Sample: 2018-2026, EDP large-storage cascades.  
Estimate: beta -0.82 on exposed position (was +0.13 as built). Interval: (-inf, +inf), F 1.3. Benchmarks: beta = 0 price-taking, beta = 1 Nash.  
Nash rejected: no. Price-taking rejected: no. Status: failed a check. Checks: Withdrawn: first stage came from SU Eletricidade's pass-through volume; on EDP's exposed position offered solar has no first stage (F 0.4-1.3). Across-day margin untested by this design.  
Source: notes/rq-midday-hydro.md, §3.20 The exposed net position.
> Later figure: rq-midday-hydro.md §3.21 (dated owners): leg B large storage, λ50 pooled F 0.4, 'still no first stage'

**O27. How far above the price-taking water value do groups offer hydro?**  
hydro offer at expected running share net of bilateral contracts, over λ*30s; Level ratio of offer to forward-based price-taking water value (no conduct parameter). Sample: 2019-2026, storage units of six groups, days both read points exist.  
Estimate: ratio EDP 0.95, Movhera 0.98, Iberdrola 1.11, Naturgy 1.22, Endesa 1.35. Interval: none. Benchmarks: 1 = price-taking water value; no Nash level prediction.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Benchmark validated on EDP (within 6%). Option value under 1%. Counts ADOURO as EDP's over Movhera window (not rebuilt). Endesa/Naturgy leave ~80% of unoffered capacity unused anywhere.  
Source: notes/rq-water-value-forward.md, header and §5.5 Net of bilateral contracts.

**O28. Does unoffered hydro capacity rise with the firm's price incentive?**  
unoffered share of hydro capacity (quantity withholding); Panel OLS of unoffered share on X̃ (own hydro removed), unit x month, hour, weekday effects, fill, running share and bilateral share controls; rules fixed before running. Sample: 2019-01 to 2025-09, 13 Spanish storage units of EDP, Endesa, Iberdrola, Naturgy, 635,717 unit-hours.  
Estimate: +0.15 pp of capacity per sd of X̃ (pooled P2); per firm -0.36 to -0.03. Interval: pooled [+0.05, +0.25]; every pooled interval below 0.55 pp. Benchmarks: positive = quantity market power; 0 = water or contracts.  
Nash rejected: not tested. Price-taking rejected: no. Status: current. Checks: Pass fails; 'fail for quantity market power as informative zero' holds (upper end below 1 pp per sd); stop rule triggered on pooled sign (P1 -0.21 vs P3 +0.45), so per-firm rows carry the reading. Lead placebo as large as current for within-firm negatives. No instrument.  
Source: notes/rq-water-value-forward.md, §5.10 Does the unoffered share follow the price incentive?.

**O29. Do a firm's other offers fall when its own reactor goes out?**  
offer price at 25% of offered volume, all dispatchable units; Offer regression, X instrumented by owner's unplanned and planned reactor-outage doses, technology x date x hour and unit x week effects. Sample: 2018-2026, 7.82 M unit-hours, 178 units; rerun on corrected ownership 2026-11-03.  
Estimate: beta -0.89. Interval: AR [-4.29, 0.66], F 10.0. Benchmarks: beta = 0 price-taking, beta = 1 Nash.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: Price-taker band about 0 (thermal within ±0.03, hydro ±0.6), so not estimator-contaminated. p(beta = 1) 0.03. Thermal-only or hydro-only sets contain 0 and 1. Event study of 21 trips: offers do not jump. Design closed 2026-11-02.  
Source: notes/rq-reactor-outages.md, §11 and §12.1 Results of the rerun.

**O30. With rain and outages as instruments, do thermal offers follow the stake?**  
thermal offer price at 50% of offered volume; Offer regression, X instrumented by outages plus own-catchment 30-day rain, unit x month effects. Sample: 2018-04 to 2026-05, 84 thermal units, 3.6 M unit-hours.  
Estimate: beta -0.85. Interval: AR [-3.96, 1.83], F 13.5. Benchmarks: beta = 0 price-taking, beta = 1 Nash.  
Nash rejected: no. Price-taking rejected: no. Status: current. Checks: Not rerun on the 2026-10-21 ownership fixes. Rain alone F 9.5.  
Source: notes/rq-reactor-outages.md, §7 Rain as a second instrument.

**O31. With regional wind as instrument, do thermal offers follow the stake?**  
thermal offer price at 50% of offered volume; Offer regression, X instrumented by firm's own-farm wind above national rate (forecast split), technology x date x hour effects (A). Sample: 2019-01 to 2026-05, 64 thermal units, 2.51 M unit-hours; 78.5% of wind located.  
Estimate: beta +1.49 (wind alone); -1.03 with outages. Interval: [-1.61, 4.99], F 27.0; with outages [-3.14, 1.53], F 14.1. Benchmarks: beta = 0 price-taking, beta = 1 Nash.  
Nash rejected: no. Price-taking rejected: no. Status: current. Checks: Strongest unit-level first stage; weak from 2022 (F 3-10). Not rerun on 2026-10-21 ownership fixes.  
Source: notes/rq-reactor-outages.md, §9.1 Rerun with 78.5% of wind located.

**O32. How much market power did market structure make available?**  
implied Lerner floor s/eta from residual-demand elasticity and CNMC shares; Structural bound L = share / elasticity, no conduct assumed. Sample: 2018-2023, market-wide curves, CNMC annual PDBF shares.  
Estimate: Iberdrola implied Lerner 10.4% (2018) to 23.7% (2023). Interval: none. Benchmarks: potential markup under full exercise (Nash-like); not a conduct measure.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Note says not evidence firms exercised power; PDBF shares overstate day-ahead incentive (contracts). Static-era result (pre-ownership fixes).  
Source: notes/result-markups-vs-hhi.md, The finding / Method / What this is, and is not.

**O33. Does a thermal plant's markup rise on hot, high-demand days?**  
thermal markup on marginal accepted offer (offer minus implied cost); Shock x predetermined size: cooling degree hours, unit effects, event study. Sample: 68 thermal units, 97,727 unit-days, 12 firms (2018-2026).  
Estimate: +0.96 EUR/MWh per CDH unit; size interaction -6.30 (se 3.47). Interval: roughly [-1.4, +3.3] EUR/MWh per CDH unit. Benchmarks: 0 = no conduct response; market power predicts positive markup and positive size interaction.  
Nash rejected: not tested. Price-taking rejected: no. Status: failed a check. Checks: Event study shows pre-trend with no step; size interaction wrong sign; heat also moves outages (not a clean demand shifter); cost measure omits O&M, start-up, part load.  
Source: notes/rq-heat-demand-conduct.md, §4 and §5.

**O34. Does net load (heat, wind) raise thermal markups?**  
thermal markup on marginal accepted offer; 2SLS of markup on net load, instruments heat, wind and irradiance. Sample: 68 thermal units, unit-days 2018-2026.  
Estimate: beta 0.345 EUR/MWh per GW (se 0.347). Interval: none. Benchmarks: 0 = no conduct response to net load.  
Nash rejected: not tested. Price-taking rejected: no. Status: current. Checks: F 184.8; OLS agrees (0.214). Note concludes the implied-cost markup measure, not the shock, is the binding constraint.  
Source: notes/rq-heat-demand-conduct.md, §8.2 Combining heat, wind and rain.

**O35. Do in-the-money thermal units withhold more when net load is high?**  
period-level in-the-money non-clearing share (withholding); 2SLS of withholding rate on net load, heat/wind/irradiance instruments. Sample: 68 thermal units, unit-days 2018-2026.  
Estimate: beta -0.0251 per GW (se 0.0013). Interval: none. Benchmarks: positive = withholding (market power); read as merit order.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: failed a check. Checks: Wrong sign for market power, precise (t -18.65, F 134.2); outcome dominated by unit commitment (median unit-day withholding 100%) because implied cost over-includes in-the-money periods.  
Source: notes/rq-heat-demand-conduct.md, §8.1 and §8.2.

**O36. How much would prices fall with hydro offered at its water value?**  
day-ahead price, storage hydro steps moved to k x λ*30s holding each unit's water; Counterfactual re-clearing of effective curves, same water, rivals unchanged. Sample: 2019-01 to 2025-09, 53,273 valid hours.  
Estimate: -EUR 0.83/MWh on average (1.0%); -EUR 2.17 in 2025. Interval: none. Benchmarks: 0 = hydro already offered as price-taker; an upper bound on market power in pricing given water.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Not shown to be market power (leg B finds gap not rising with stake). Not rebuilt on corrected ownership. Assumes cascades can run full turbine capacity.  
Source: notes/rq-counterfactual-hydro.md, §3 Results.

**Estimates the verifier found missing from this group (kept as reported, not re-verified):**

Estimates in the listed notes that the extraction does not have as their own rows:
(1) rq-price-taking-simulation.md §18. Hydro, reactor-outage instrument, simulation-corrected: +0.11 [-0.41, 0.48], ten-seed band -0.30 to +0.40, does not differ. §17 says hydro rejects beta = 1 with every instrument (p(1) 2e-6). 2024-25, 06-11h block: +0.19 [0.09, 0.30] against -0.03 to +0.09, differs. 2024-25 without EDP: +0.25 [0.11, 0.41], differs. Buyers 2024H2: +0.26 [0.01, 0.56], differs. Seller 2020H2: +0.38 [0.03, 0.69]. §7 thermal equivalence: five firms -0.14 to +0.05 accepted; 2021H2-2023 -0.20 to +0.04 accepted. The actual thermal cells are 2021H2-2023 -0.03 [-0.13, 0.06] and five firms -0.03 [-0.12, 0.06]. Size of the 2024-25 departure: EUR 2.08 [-0.13, 4.66] on price-setting steps and +EUR 0.08 [-0.005, 0.17] on the price (row 5 mentions these only in its checks). Month 2021-04: beta +0.44 [0.24, 0.73], gap +0.71 [0.10, 1.25], departs (§19).
(2) rq-step-estimator.md §3. One draw, the realised residual demand: own step sets the price -0.12 [-0.14, -0.04], F 11.3; price in the gap -0.02 [-0.09, -0.01], F 4.3. Both sets are narrow because they condition on the realised clearing. §8, after the rebuild: hydro two slopes 2024-25 are -0.80 / +0.73, firm-by-forecast instruments, not read.
(3) rq-leg-b-levels.md §3. Unit x month, regional wind: -1.16 [-3.78, -0.37], F 8.8 (10.0 after the rebuild), weak. Outages plus wind: -0.35 [-0.83, -0.15], F 17.3, not read because the set is empty with lambda*90.
(4) rq-leg-d-sign-of-n.md §8. Iberdrola, net of the fringe, one slope: beta 0.033, overidentification p 0.027 (wind and solar disagree). Iberdrola raw, two slopes: AR p of price-taking 0.78. EDP: AR set empty.
(5) rq-midday-hydro.md §3.15. Iberdrola IV on the deviation from the benchmark: -0.14 (AR [-0.19, -0.09]); it fails validation and is read only relative to EDP. §3.21: within-day markup bound on lambda-hat-50, median 0.40 (p90 1.74).
(6) rq-reactor-outages.md §12.1. Unplanned doses only, 25%: -2.80 [-8.00, -0.18], p(beta = 0) 0.04, p(beta = 1) 0.01; this sub-row excludes zero. Planned only: +0.47 [-3.18, 4.24]. Hydro 50%: +0.41 [-1.83, 2.22]. Combined cycle 50%: -2.41 [-8.87, 1.99]. Thermal offer minus c_bid: -1.60 [-7.03, 2.78]. §11 price-taker band: thermal cost +0.006 [-0.006, 0.018]; hydro lambda* +0.08 [-0.12, 0.24]. §7, rain alone (30 days): -2.46 [-7.18, 1.52], F 9.5. §9.1, regional wind measured, effects B: +3.37 [0.07, 7.45], excludes 0, a check only.
(7) rq-fixed-step.md, ten seeds. Iberdrola seller, n with Zb: +6.8 EUR per GW [3.2, 10.6], differs, read as book management. Ladder at 1.5 cf_s in the departure periods: +0.29 [+0.01, +0.60] at ten seeds, then no longer differs after the 2026-10-21 rerun (b 0.210, low end -0.023).
(8) Conduct and pass-through estimates in notes outside the list (not fully verified here):
- rq-crisis-quantity.md: in-money rho 0.73 [0.51, 1.03] (line 157/218), central band 0.5-0.85.
- rq-gas-cap-declared-cost.md §2: the declared minimum-income cost passes through about nine-tenths of the gas subsidy.
- rq-ivpee-tax-test.md: pass-through theta 1.45, p 0.18 for theta = 1, p < 0.001 for theta = 0.
- rq-gas-cap-control.md / rq-gas-cap-conduct.md: Design B p_mid rho 1.06 [0.58, 1.90] (per memory).
- rq-regional-holidays.md: holiday quantity test beta -0.16 [-0.52, 0.20], Nash rejected (per memory).
- rq-own-wind-quantity.md: stopped at step 1 on power.
- rq-self-supply-cost.md: stopped at step 1a on power (MDE EUR 53 against EUR 17/MWh).
- rq-mic-near-miss.md and rq-france-link.md: both stopped.

**Open conflicts flagged by the extractor:**

1) Conflict between hydro designs: the simulation-corrected step estimator finds a departure in 2019-2021H1 (+0.25, rests on Iberdrola) and none after the cap; the fixed step finds none in 2019-2021H1 and a departure in 2023 that is Iberdrola's. Neither finds one in 2024-2025. 2) Leg D's buyer markdown (beta- 0.19, no Anderson-Rubin interval) conflicts with the simulation's §16 finding that the buyer side has no stable pattern and with the fixed step attributing Iberdrola's buyer markdown to contract routing. 3) Reactor-outage instruments: the simulation (§2) shows price-takers give -0.40 (hydro) and -0.59 (thermal) under the outage IV in the step estimator and leg B, while rq-reactor-outages §11 finds a price-taker band of about 0 for its own offer-regression design. The outage-based step-estimator and leg-B rows are therefore of uncertain bias. 4) Not rebuilt on the 2026-10-21/22 ownership fixes (Movhera Douro dams in ADOURO, EDP Energia sale, Castejon): leg A (midday hydro, dated 2026-10-05), leg C and leg D (2026-10-03), water-value ratios (§5.5 counts ADOURO as EDP's), the counterfactual, reactor rain and regional-wind rows, and the step-estimator start-up check. 5) Thermal simulation rests on two seeds (three in two periods); hydro on ten. 6) The fixed-step reruns report the pooled slope 0.155 without a new interval; the quoted bias-adjusted range [-0.10, +0.36] is from before the reruns. 7) Leg D dated common-slope beta interval is given only as 'AR ≈ [0.00, 0.05]'. Its slope set [-0.185, -0.015] excludes 0. The two-slope betas have no interval. 8) Superseded figures that are still quoted elsewhere: raw at-cost thermal -0.27 / -0.08 and hydro -0.23 (estimator artefact), the 2-seed hydro 2024-2025 departure (+0.20), the pre-rebuild hydro 2019-2021H1 +0.31 and leg-B at-cost 2019-2021H1 +0.14, and the first-design leg D (rival solar, superseded by §7). 9) Midday hydro leg-B first pass (+0.13 [-0.43, 0.77]) is withdrawn because it has no first stage on the exposed position. EDP's across-day margin is untested. 10) Paper-method λ̂ (rq-leg-b-levels §4) assumes beta = 1, so it is not a conduct test and was left out. 11) The heat-demand and markups-vs-HHI notes date from August 2026 and use the older implied cost, static ownership and CNMC PDBF shares. Their intervals are rough or absent. 12) In the unoffered-capacity test (water-value §5.10) the stop rule fired on the pooled sign, so the per-firm rows carry the reading. It has no instrument.


### B. Quantities, declared costs and sequential markets

**Q1. Do reactors cut output on the days a price-taker would?**  
nuclear quantity (partial cuts); T2 benchmark: simulated price-taking reactor at book-value fuel cost (c_acct), one-day-ahead rule using OMIP forward price, with each reactor's own minimum load and ramp limits. Sample: 2024-01 to 2026-05, 7 Spanish reactors (actual partial cuts 10.95 TWh).  
Estimate: price-taker cuts 11.77 TWh vs actual 10.95 TWh; only 46% of actual cut volume shared (daily corr 0.44); end-of-cycle fuel value implies 3-26x actual cuts. Interval: none. Benchmarks: Price-taking = actual cuts match the simulated price-taker's cuts in volume and timing; no Nash benchmark in T2 (misfit is what T3 tests).  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Hour-by-hour realised-price check: shared share 47-52%. Snapshot-day restriction (2026-11-05): 2.26 vs 1.87 TWh, shared 51%. Cost rates provisional (to verify). End-of-cycle fuel valuation rejected by behaviour.  
Source: notes/rq-nuclear-cuts.md, §5 T2 and §7.1 Part 1.
> Later figure: §7.1 Part 1 (2026-11-05) leaves T2 unchanged: 'the price-taker's cut against the actual is 2.26 against 1.87 TWh on snapshot days (11.77 against 10.95 on all days); the shared share is 51% against 46%; daily correlation 0.52 against 0.44'. §7.1 Part 3 adds the cap-period shared share: 'share only 46% (2024–26) to 15% (cap period) of cut volume'.

**Q2. Does reactors' departure from price-taking rise with owners' price stake?**  
nuclear quantity (cut minus price-taker cut); T3 IV (two-stage least squares): dev on owners' n_full/|RD'| (X), instruments = owners' shares of other reactors' unplanned and planned outages, regional wind deviation, catchment rain; reactor x month and day-of-week effects, week clusters; Anderson-Rubin (AR) sets. Sample: 2024-01 to 2026-05, 4,926 reactor-days (2019-2026: 16,326).  
Estimate: gamma +14.3 MW per EUR/MWh (se 6.0), F 3.7, implied beta about 4.4; on register-snapshot days only +0.5 (4.8), F 3.2. Interval: AR [10.5, 62.2] all days; snapshot days AR [2.0, 65.5] (excludes its own 2SLS estimate). Benchmarks: gamma = 0 is price-taking; Nash (beta = 1) implies gamma equal to the price-taker's response to cost, about 3.3 MW per EUR/MWh in 2024-26 (1.5 over 2019-26).  
Nash rejected: not tested. Price-taking rejected: yes. Status: failed a check. Checks: Weak first stage (F 0.1-6.4); instruments disagree (AR set away from 2SLS). Rejection carried by gap days (no indisp snapshot): 2019-26 all days +3.0 (4.7) AR p 0.003 vs snapshot days -0.8 (2.6) AR p 0.13. Snapshot-days all-four estimate lies inside price-taker null band [-5.3, 2.2]. Implied beta > 1 not believable as conduct; operator split implies beta about 14 (supply rule, not price stake).  
Source: notes/rq-nuclear-cuts.md, §6 T3 and §7.1 Part 1.
> Verifier: price_taking_rejected should not read a plain 'yes'. §7.1 Part 1 says 'The rejection of "no departure from price-taking linked to X" is carried by gap days' and 'T3 is **not answered in either direction for 2024–26**, and the T3 rejection over 2019–26 should not be quoted without the note that it is carried by gap days.' Write: 'yes on all days (AR p 0.003); not answered once restricted to snapshot days (2019–26 −0.8 (2.6), AR p 0.13; 2024–26 +0.5 (4.8) inside the null band [−5.3, 2.2])'. The quote joins two places: the §6 table row and the §7.1 Part 1 text. Cite both sections. The rest checks out: F 3.7, AR [10.5, 62.2], snapshot AR [2.0, 65.5], β≈4.4 (se 1.8), and β≈14 from the operator split (§6.1).  
> Later figure: §7.1 Part 1 (2026-11-05): 'snapshot days +0.5 (4.8), AR p 0.032, F 3.2'. Also 'Outages alone on snapshot days stay at +15.7 (6.0), F 5.2, AR [9.8, 61.0]; regional wind alone loses its first stage (F 1.3).'

**Q3. Do reactor cuts respond to how much refuelling elsewhere moves the price (pooled)?**  
nuclear quantity (cut deviation from price-taker); Slope test: dev on owners' refuelling dose Z and its price effect P = 1000 Z/|RD'|, cut opportunity controlled; beta-equivalent = P-hat / Nash value (gamma_N x lambda, lambda = -1.04). Sample: 2019-01 to 2026-05, all days, 16,326 reactor-days (5,703 dosed).  
Estimate: P-hat +0.29 MW per EUR/MWh (se 0.64); beta-equivalent -0.19; MDE_beta 1.16. Interval: beta [-1.00, 0.63]; P-hat [-0.97, 1.54]. Benchmarks: beta 0 = price-taking (no price motive); beta 1 = Nash (full market power); positive P-hat is what an own-supply rule predicts.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: Nash p 0.004; MDE_beta 1.16 > 1 so wording is 'no detectable market power', not 'price-taking'. Supersedes §6.2 (P +0.3 (0.6), Nash about -1.4, p about 0.01, lambda -0.92). Snapshot days: -0.36 [-1.44, 0.72], MDE 1.54, Nash p 0.013. Reproduction to 6 digits failed, relaxed to 0.15% of se (firm_x rebuilt 2026-10-22). Panel X is 2026-10-19 vintage.  
Source: notes/rq-nuclear-cuts.md, §7.1 Part 1 (slope test table).

**Q4. During the gas cap, did reactor cuts show any price motive?**  
nuclear quantity (cut deviation from price-taker); Slope test by period (same spec as pooled), all operators pooled. Sample: cap period 2022-06-15 to 2023-12-31, all days and snapshot days.  
Estimate: all days P-hat -0.02 (se 0.44), beta-equivalent +0.01, MDE_beta 0.66; snapshot days +0.21 (0.36), beta -0.11, MDE 0.52. Interval: beta [-0.45, 0.47] all days; [-0.48, 0.26] snapshot days. Benchmarks: beta 0 = price-taking; beta 1 = Nash.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: Only cell passing the pre-set 'price-taking' wording (interval contains 0, upper end < 0.5, MDE_beta <= 1). Pre-cap beta -1.05 [-2.76, 0.66], MDE 2.45 ('no information'). Period confounds the cap with the 2021-22 gas crisis. Several operator cells have pooled vs in-cell lambda verdicts disagreeing (13 of 43).  
Source: notes/rq-nuclear-cuts.md, §7.1 Part 2 and Part 3.

**Q5. In 2024-26, when most cutting happens, is there a price motive?**  
nuclear quantity (cut deviation from price-taker); Slope test, 2024-26 window, all days and snapshot days. Sample: 2024-01 to 2026-05, 4,926 reactor-days (2,001 dosed); snapshot days 1,357 (439).  
Estimate: all days P-hat +1.82 (se 3.04), beta-equivalent -0.54, MDE_beta 2.51; snapshot days +2.54 (4.82), beta -1.84, MDE_beta 9.74. Interval: beta [-2.29, 1.22] all days; [-8.65, 4.98] snapshot days. Benchmarks: beta 0 = price-taking; beta 1 = Nash.  
Nash rejected: no. Price-taking rejected: no. Status: failed a check. Checks: Power: MDE_beta 2.51 (all days) and 9.74 (snapshot days) > 1, so 'no information'. Nash p 0.087 / 0.415. 83% of 2024-26 partial cut volume is on register-gap days.  
Source: notes/rq-nuclear-cuts.md, §7.1 Part 1.

**Q6. Does own wind separate book balancing from market-power output cuts?**  
firms' other generation (quantity) vs price effect of own wind; Own-wind slope test: other generation on own wind and its price effect P_W = W_s/|RD'|, instruments Wdev x terciles of 1/|RD'| (slope groups); date x hour and firm x month effects. Sample: 2019-2025 weekdays, 5 firms, 199,675 firm-hours.  
Estimate: outcome regression not formed; minimum detectable beta 1.16 (auction 1.07, bilateral 1.10). Interval: none. Benchmarks: b_P = 0 (beta 0) = book balancing/price-taking; b_P = -s-bar = -62 MW per EUR/MWh (beta 1) = Nash.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: stopped before estimate. Checks: First stage passes with slope groups (Sanderson-Windmeijer F 53.0 and 38.9); the linear version failed (F 3.7, 2.5, MDE beta 2.13). Stopped on power (MDE > 1). Placebo (own retail purchases) moves slightly (+0.03 to +0.09).  
Source: notes/rq-own-wind-quantity.md, 'Step 1 with slope groups'.

**Q7. When own wind blows, do firms cut other output, and through which leg?**  
firms' other generation by leg (auction vs bilateral); 2SLS: other generation on own scheduled wind W_s, instrumented by Wdev (located wind x regional capacity-factor deviation); date x hour and firm x month effects, date clusters. Sample: 2019-2025 weekdays, 5 firms, 199,675 firm-hours.  
Estimate: total -0.20 MW per MW own wind (se 0.06); auction +0.01 (0.06); bilateral -0.21 (0.06); refreshed-ownership rerun -0.202 (0.061). Interval: none stated (net-position run gives -0.34 to -0.10 under controls without retail). Benchmarks: 0 = price-taking; -0.41 on bilateral leg = full physical book balancing; -0.22 on auction leg = Nash (beta 1).  
Nash rejected: yes. Price-taking rejected: yes. Status: current. Checks: First stage F 1,610. Auction Nash cut rejected at 3.9 se (3.2 se with firm x date). Firm x date effects halve total to -0.09 (0.06), not significant. Carried by Iberdrola (-0.27). Gives no beta; size does not separate book balancing from Nash.  
Source: notes/rq-own-wind-quantity.md, 'Own wind alone (2026-10-21, design §9)'.
> Verifier: Minor: the quote splices two table rows (the outcome table and the reference table) under 'Own wind alone'. Every number checks out (−0.20 (0.06), auction +0.01 (0.06), bilateral −0.21 (0.06), F 1,610, 3.9 se / 3.2 se, firm × date −0.09 (0.06), Iberdrola −0.27 (0.10)).  
> Later figure: Net position section, Results (2026-11-05), refreshed panel: 'other generation A under the original controls (C1) is **−0.202 (0.061)**'. Under C0 (no retail control): A −0.218 (0.062) [−0.34, −0.10], auction +0.004 (0.058) [−0.11, +0.12], bilateral −0.222 (0.057) [−0.33, −0.11].

**Q8. Does a firm's net auction position fall with its own wind?**  
firms' net position excluding own wind (auction and total), retail buying legs; 2SLS on own wind instrumented by Wdev, outcomes NX_auc, NX_tot, B_a (buying units' auction purchases); controls without retail (C0); refreshed ownership panel. Sample: 2019-2025 weekdays, 5 firms, 199,675 firm-hours.  
Estimate: NX_auc +0.275 per MW own wind (se 0.072); NX_tot -0.119 (0.066); B_a -0.233 (0.064). Interval: NX_auc [+0.13, +0.42]; NX_tot [-0.25, +0.01]; B_a [-0.36, -0.11]. Benchmarks: NX_auc = -r = -0.217 is Nash (beta 1, market power in net terms); 0 = price-taking/book balancing; buy-back requires B_a >= +0.10.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: Gates: F 1,609, G2 data pass, G3 power passes narrowly (0.202 vs 0.217). NX_auc is 6.8 se above Nash. Buy-back rejected. Stability 4 of 6 checks (not the 5 required); rules had no branch for a rise. NX_tot cannot tell 0 from Nash. Firm-level: only Iberdrola readable; others STOP on power.  
Source: notes/rq-own-wind-quantity.md, 'Net position and the retail legs (2026-11-05)', Results.

**Q9. Do regional holidays shift firms' stake enough to identify buyer-side markdown?**  
thermal and hydro offers (beta minus, buyer markdown) via holiday dose; Holiday dose (regional retail exposure x hourly profile) as instrument for exposed stake X or Zb. Sample: 2019-2025 weekdays, 5 firms; Endesa dosed on 147 days.  
Estimate: none (outcome not estimated); smallest detectable beta-minus 27 (thermal offers), 297 (hydro). Interval: none. Benchmarks: beta 0 = price-taking; beta 1 = Nash.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: stopped before estimate. Checks: First stage fails: pooled F 0.1-3.5; Endesa F 22 on X is wrong sign and carried by slope variation. Power MDE >> 1. Reason: holiday cut absorbed by bilateral self-supply (generation -0.54, retail bilateral +0.69 per MW dose).  
Source: notes/rq-regional-holidays.md, 'Step 2: the dose, the first stage and the power — STOP'.

**Q10. Do output cuts on customers' holidays grow in steep hours (market power)?**  
firms' generation quantity on own customers' holidays; Holiday quantity slope test: generation on dose Z and P = dose/|RD'|, own wind held fixed; 1/|RD'| control, date x hour and firm x month effects, date clusters; beta = -b_P / s-bar. Sample: 2019-01 to 2025-09 weekdays, 5 firms, 12,760 dosed firm-hours (199,675 with own wind).  
Estimate: beta -0.20 (generation, both legs); cut b_Z -0.27 MW per MW dose (se 0.13). Interval: [-0.55, +0.15]. Benchmarks: beta 0 (b_P = 0) = book balancing / no market power; beta 1 (b_P = -72 MW per EUR/MWh) = Nash.  
Nash rejected: yes. Price-taking rejected: no. Status: current. Checks: p(beta = 1) 3e-11. MDE 0.54 at step 1. Supersedes -0.16 [-0.52, +0.20] (before own-wind control). s x P refinement -0.12 [-0.25, +0.02]; Endesa -0.23 [-0.66, +0.20]; Iberdrola -0.28 [-0.59, +0.04]; slope at cost -0.17 [-0.70, +0.36]; regional days only +0.22 [-0.52, +0.96] (Nash p 0.04); week clusters -0.20 [-0.53, +0.13]. Nonzero b_Z is book balancing, not price-taking in the strict sense. Panel predates 2026-10-21 EDP ownership fixes.  
Source: notes/rq-regional-holidays.md, 'The quantity test with own wind held fixed (2026-10-21)'.

**Q11. What does the holiday self-supply cut cost the firm, in euros?**  
value of generation cut on holidays (book-balancing cost); Euro test: margin-weighted generation response per MWh of holiday dose, firm-days, date and firm x month effects. Sample: 2019-01 to 2025-09 weekdays, 5 firms, 8,805 firm-days (567 dosed).  
Estimate: none (stopped); reference loss -EUR 17 per MWh of dose (about -EUR 5 after the wind correction); se under b = 0 EUR 18.8, MDE EUR 53. Interval: none. Benchmarks: 0 = cut costs nothing (cheap book balancing); reference A = every cut MWh lost at its class margin.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: stopped before estimate. Checks: Stopped on power (MDE EUR 53 vs reference EUR 17). Wind part of cut was weather (wind schedule -0.04 (0.03) with own wind controlled).  
Source: notes/rq-self-supply-cost.md, Step 1a §4 and 'The wind checks'.

**Q12. Do thermal plant breakdowns follow the owner's price stake?**  
gas and coal fault starts (possible withholding); Daily fault-start rate on owner's stake X = n/|RD'| the day before; unit x month and date effects. Sample: 2018-2026, 39,758 unit-days of units that ran the day before, five largest owners, 370 fault starts.  
Estimate: -0.0014 percentage points per EUR/MWh of X (se 0.0078), p 0.86; one sd of X moves fault rate -1.7%. Interval: about -21% to +17% of the fault rate per sd of X. Benchmarks: 0 = faults not chosen (price-taking); positive = withholding disguised as faults.  
Nash rejected: not tested. Price-taking rejected: no. Status: current. Checks: Unit x month only: p 0.50; on n: p 0.99. Fault doses as instruments stopped (gas first stage 0.40, F 3.7; joint F 15.8 < 20).  
Source: notes/rq-outage-events.md, §4 'Are faults chosen?'.
> Verifier: Minor: the note's sample wording is 'largest owner one of the five', not 'five largest owners'. The '2018-2026' window is not stated in §4 itself.

**Q13. After a reactor trip, do rivals squeeze the forced intraday buyer?**  
intraday price premium after reactor trips (rivals' offers); Event study of 31 unplanned reactor trips; premium change regressed across trips on whole-market slide (reactor gross buy-back / slope of all others' offers within EUR 5). Sample: 2018 to 2024-06-13, 31 trips with reacting sessions (main sample, MIBEL six sessions).  
Estimate: premium = +1.24 (se 1.78) + 1.95 (se 0.77) x slide; remainder after slide +2.70 EUR/MWh (se 1.35). Interval: remainder about 0 to EUR 5.3/MWh; slope 0.4 to 3.5 times the slide. Benchmarks: Price-taking = intercept 0 and slope 1 on the whole-market slide; a squeeze = premium above the slide, growing with the forced buy.  
Nash rejected: not tested. Price-taking rejected: no. Status: current. Checks: Placebo (last pre day) remainder -2.17 (1.00), same size as effect. Sessions closed before the trip and post-window days show nothing. All 39 trips incl. IDA era: intercept +4.07 (1.44), slope 0.32 (0.15), driven by two trips. Earlier net-take dose response failed (wrong dose).  
Source: notes/rq-intraday-squeeze.md, §2.1 'The whole-market slide'.

**Q14. Can minimum-income near-misses identify withdrawal conduct via an RDD?**  
combined-cycle withdrawal and intraday sales at the minimum income condition threshold; Regression discontinuity at the margin where the minimum-income condition binds (re-cleared margin r_A), local linear, bandwidth EUR 2/MWh; McCrary density test. Sample: 2019-01-01 to 2025-03-18, 137,417 declaring unit-days on 121 units; single-plant days 304.  
Estimate: none (step 2 not run); acceptance jump 0.890 (se 0.015); withdrawn plant sells about 91 MW more intraday (se 6). Interval: none. Benchmarks: Design aimed at beta (0 price-taking, 1 Nash); not reached.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: failed a check. Checks: Density test fails on every sample: log ratio 0.766 (se 0.068) all days; 1.18 (0.26), p 8e-6 on single-plant days. Declared variable term jumps +16.8 (3.7) on all days; balances on single-plant days but only 264 firm-days vs 1,000 required; first stage there 22 MW (se 16).  
Source: notes/rq-mic-near-miss.md, §1.2 and §1.7.

**Q15. Does the day-ahead minus intraday premium rise with strategic firms' net position?**  
day-ahead vs first intraday price premium (Ito and Reguant sequential-market conduct); Premium on combined net position N of five firms, instrumented by planned reactor outages; year-month x hour effects, forecast-error controls, week clusters. Sample: 2019-01-01 to 2025-03-18, 54,170 hours.  
Estimate: IV +0.95 EUR/MWh per GW of N (se 0.39); first stage -0.49 (0.12), F 17.9; OLS main -0.029 (0.035). Interval: none. Benchmarks: 0 = no strategic arbitrage (price-taking); positive slope = market power (net sellers withhold day-ahead, net buyers under-buy); no Nash magnitude computed.  
Nash rejected: not tested. Price-taking rejected: yes. Status: current. Checks: Raw relation flat in all periods (2019-21H1 -0.003, 2021H2-23 -0.037, 2024-25Q1 -0.036). Single instrument with an exclusion threat (outage tightens market); note calls it 'a lead, not a result'. Firms are net buyers in 92.5% of hours. No placebo reported.  
Source: notes/rq-da-id-premium.md, §3 Results.
> Verifier: Minor: the quote is three table rows given in reverse order of the source. The note does not state the IV's controls (forecast errors, year-month × hour effects); the row infers them. The price_taking_rejected 'yes' rests on one instrument that the note itself calls 'a lead, not a result'. Keep that qualifier beside the verdict.

**Q16. Does the DA-intraday premium rise with concentration (Ito-Reguant comparative static)?**  
day-ahead vs intraday session 1 price premium; Premium on top-firm share, HHI (Herfindahl index), 1/eta (inverse residual-demand elasticity), max firm Lerner; hour and year-month effects, month clusters. Sample: 2018-01 to 2026-05, session 1, 71,441 period-days.  
Estimate: top firm share beta +8.139 (se 2.472); 1/eta -0.014 (0.019); max Lerner -0.017 (0.051). Interval: none. Benchmarks: beta > 0 = market power raises premium; 0 = competitive.  
Nash rejected: not tested. Price-taking rejected: yes. Status: superseded. Checks: Elasticity-scaled measures (the first-order-condition object) null and wrong-signed; share is not the FOC object. Predates ownership corrections and ESIOS forecasts; wind-forecast-error confound unresolved. Treated as superseded by the firm-position version (rq-da-id-premium.md, 2026-10-06) - inferred, not stated in the note.  
Source: notes/rq-sequential-market-premium.md, §7.1.
> Verifier: Status 'superseded' is inferred and not stated in the note (the row says so). §7.2 also gives the instrumented market-power measures, both wrong-signed: '1/eta −0.238, t = −1.65; max Lerner −1.199, t = −1.95'.

**Q17. Do REE wind/solar forecast surprises identify thermal intraday conduct?**  
thermal (combined cycle, coal) intraday offers; IV: owner's intraday X instrumented by firm-specific wind and solar surprise (realised minus REE D-1 forecast); unit x week and class x session x date x period effects. Sample: 2019-01-01 to 2024-06-13, 2.2 M unit-session-periods, 90 units.  
Estimate: beta -10.8 (se 4.0), F 6.4 (all sessions). Interval: AR set empty (p < 1e-11 at 0 and at 1). Benchmarks: beta 0 = price-taking; beta 1 = Nash.  
Nash rejected: yes. Price-taking rejected: yes. Status: failed a check. Checks: Empty AR set: instruments contradict each other. Day-ahead placebo fails (day-ahead X F 31.4 shift-share, 12.2 firm-specific). Shift-share first stage wrong sign (F 3.3). Point estimates 'mean nothing'.  
Source: notes/rq-intraday-surprise.md, §3 and §4.

**Q18. Does a firm's own wind surprise identify thermal intraday conduct?**  
thermal intraday offers; IV: X instrumented by own surprise S = firm's realised located wind minus its own day-ahead wind schedule; firm x REE error controls. Sample: 2019-01-01 to 2024-06-13, five large firms plus Acciona.  
Estimate: beta -3.1 (se 7.7), S pooled; S by firm F 6.6. Interval: AR [-19.2, 13.6] (pooled); [-0.02, +infinity] (by firm). Benchmarks: beta 0 = price-taking; beta 1 = Nash.  
Nash rejected: no. Price-taking rejected: no. Status: failed a check. Checks: First stage passes (position F 120, X F 27, thermal unit F 24) but day-ahead placebo fails in three variants (e.g. five firms' DA X F 21.5, 4.1, 12.3); stopped after three variants. Uninformative even if valid.  
Source: notes/rq-intraday-surprise.md, §6 'The own surprise'.

**Q19. Can the France line's open state shift the stake enough to test beta?**  
hydro (fixed-step) and thermal offers via corrected stake; First stage of corrected at-cost stake Zb_c on Zb x predicted French-driven open probability; holiday step-2 effects. Sample: 2019-01 to 2025-09; unit hydro 359,156 rows, unit thermal to 2023-12 781,511 rows.  
Estimate: none (stopped); MDE beta 1.95 / 2.72 hydro, 8.3 / 9.9 thermal (date / week clusters). Interval: none. Benchmarks: beta 0 = price-taking; beta 1 = Nash.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: stopped before estimate. Checks: First stage F 42/17 hydro, 93/35 thermal; power fails (MDE > 1). Step 1 prediction missed correlation bar by 0.001 (0.299 vs 0.3). French supply adds only S about 62-87 MW per EUR/MWh.  
Source: notes/rq-france-link.md, Step 2 §2.2.

**Q20. Do EDP feed-in tariff exits identify its buyer-side markdown?**  
EDP offers (beta minus) via Portuguese wind leaving guaranteed tariffs; Within-firm shift from tariff exits (not built). Sample: none (615 MW EDPR wind; full exposure only 2027-2032).  
Estimate: none; implied stake shift about EUR 0.3/MWh on about a fifth of days. Interval: none. Benchmarks: Nash would move EDP offers by about EUR 0.3; price-taker not at all.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: stopped before estimate. Checks: Not viable in window: 7-year floor/cap extension (EUR 74-98) pushes market exposure to 2027-32; dose an order of magnitude below France design, which already had MDE 2-10.  
Source: notes/rq-fit-exits.md, 'Why it is not built'.

**Q21. Did the 2024 IVPEE tax steps pass into declared costs?**  
declared minimum-income variable cost of combined cycles; Spain vs Portugal, log declared term on Spain x log(1/(1-tau)), unit and date effects, unit cost slopes; wild cluster bootstrap. Sample: 2023-04 to 2025-03, 50 combined cycles (43 ES, 7 PT), 27,880 unit-days.  
Estimate: theta 0.04 (se 0.56); +EUR 0.3/MWh vs EUR 9.3 predicted. Interval: 95% band of about plus/minus EUR 10/MWh around +0.3. Benchmarks: theta 1 = full pass-through of a known cost (cost-based declaration); theta 0 = none.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: failed a check. Checks: p theta=0 0.95, p theta=1 0.18. Steps (1.8-3.6%) too small vs month-start noise (sd 5.5% / 3.5%); quarterly drift; step-day jumps inconsistent (Jan -1.2%, Apr +6.0%, Jul +2.1%).  
Source: notes/rq-ivpee-tax-test.md, §3 Results.
> Later figure: Superseded as the IVPEE (Spanish tax on the value of generated electricity) test by §5 (the full 7% steps), which is row 21.

**Q22. Did the full 7% IVPEE tax steps pass into declared costs?**  
declared minimum-income variable cost of combined cycles and coal; Event study on three full 7% steps (2019-04-01, 2018-10-07, 2021-07-01), Spain minus Portugal gap, date x fuel effects; benchmark = 39 ordinary month starts. Sample: 2018-01-04 to 2021-12, gas 44 ES + 10 PT, coal 22 ES + 6 PT, 91,692 unit-days.  
Estimate: stacked theta 1.46 (plus/minus 7 days) / 1.45 (plus/minus 14 days); 2019-04-01 alone 1.78 / 1.64. Interval: none (month-start sd 0.31 / 0.32 used as se). Benchmarks: theta 1 = full pass-through (declared term behaves like a cost); theta 0 = none.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: p theta=0 < 0.001; p theta=1 0.14 / 0.18. Each event moves more than 95-100% of ordinary month starts. Overshoot driven by unexplained Portuguese moves. Spanish side moves predicted way at every event and fuel.  
Source: notes/rq-ivpee-tax-test.md, §5 'The full 7% steps'.
> Verifier: Optional: §5 also gives a pooled figure of 'θ is 2.12 (0.28)' over 2018-01 → 2021-06. The note calls it drift-contaminated: 'the step days are the measure'.

**Estimates the verifier found missing from this group (kept as reported, not re-verified):**

In the listed notes:
(1) rq-nuclear-cuts.md §6 table, regional wind instrument alone, 2024–26: 'regional wind, 2024–2026 | 6.4 | **+15.2 (8.0)** | [2.8, 64.8] | 0.02'. The implied β is 4.7 (se 2.5). The outages-alone IV over 2019–26 is +22.8 (12.4), AR [5.2, 382]. The selling-week vs buying-week sign test: sellers −0.9 (5.9, F 2.7), buyers +4.9 (4.7, F 1.7).
(2) rq-nuclear-cuts.md §6.1: 'IV on the other-operator dose alone, 2019–2026: F 7.5, γ +21.0 (11.8), AR [4.2, 86.0]', implying β ≈ 14. Row 1 cites the β only in its checks.
(3) rq-nuclear-cuts.md §7.1 Part 2, slope test by operator and period (Nash value from the pooled λ). Example: Cofrentes post-cap '+13.3 (3.14) [−3.44]', a loading of the wrong sign for a price motive. Nash is not pinned in 13 of 43 cells.
(4) rq-nuclear-cuts.md §7.1 Part 2, reservation price as a fixed rule. ANAV after the cap: 'the slope on p_exp is −0.07 (0.03) ... 95% interval [−0.125, −0.020]'. CNAT cap → post-cap: '+€5.0 with an interval of [−10.4, 50.7]'.
(5) rq-own-wind-quantity.md Results, by firm (refreshed panel). Iberdrola NX_auc '+0.36 (0.13)', the only firm read. Repsol 'NX_tot −0.63 [−0.89, −0.36]: a net cut 20 times its Nash reference' (Repsol has G3 'STOP: power' on NX_auc). Firm × date check: NX_auc +0.381 (0.072), B_a −0.374 (0.052).
(6) rq-regional-holidays.md, quantity test with own wind held fixed: auction leg β −0.13 [−0.61, +0.35] and bilateral leg −0.07 [−0.33, +0.19], both with p(β=1) < 1e-4.
(7) rq-da-id-premium.md §3, by firm (between-firm comparison, not shocks): 'EDP +0.28 (0.08) and Iberdrola +0.17 (0.05) go the predicted way, Naturgy −0.79 (0.10) and Repsol −0.36 (0.20) the opposite'. The 2018 run without forecast controls gives +0.141 (0.049).
(8) rq-sequential-market-premium.md §7.1 to §7.2. HHI +8.307 (4.261), t 1.95. Arbitrage, 2SLS of log intraday units on the premium: −10.526 (2.748), F 16.4, against OLS +1.672 (0.490). Instrumented 1/eta −0.238 (t −1.65) and max Lerner −1.199 (t −1.95).
(9) rq-intraday-squeeze.md step 2, net-take dose response: 'the premium falls by 0.62 per 100 MW of take (se 0.71); a squeeze needs it to rise'. Also, with the ±€10 band the remainder is +2.79 (1.41).
(10) rq-intraday-surprise.md §3: sessions 1–2 β −1.6 (2.8), F 4.6, AR set empty; sessions 3–6 −21.7 (5.2), F 5.2, empty; shift-share +14.2 (9.3), F 3.9, empty; with the efficiency control −12.6 (4.6), F 5.3, empty.

No conduct estimates in rq-hedge-ratios.md (published ratios only, 'nothing estimated'). None in rq-forecast-first-stage.md or rq-hydro-rain-first-stage.md (first stages only, e.g. X instrumented with F 64 for EDP and 53 for Iberdrola). None in rq-clawback-size-rdd.md (a design with a density count, never run).

Outside the listed notes, recorded in CLAUDE.md and memory but not in this set; verify against their own notes:
- Thermal offer IV with outages: β −0.9 [−4.2, 0.7]. With rain added: −0.85 [−4.0, 1.8]. Regional wind (v3 locations): +1.5 [−1.6, 5.0], F 27–33.
- Price-taking simulation and fixed-step hydro departures: 2019–21H1 +0.25 on ten seeds.
- Leg B at-cost.
- Gas-cap pass-through of the declared minimum-income cost: about 0.9–1.0 of the subsidy.
- Crisis quantity design: ρ 0.73 [0.51, 1.03], or 0.54 [0.10, 0.87] with gas controls.
- Gas-cap vs Italy and Great Britain tests (2c Design B p_mid ρ 1.06 [0.58, 1.90]).

**Open conflicts flagged by the extractor:**

1) No conduct estimates (excluded): rq-hedge-ratios.md (web-sourced hedge ratios, nothing estimated), rq-forecast-first-stage.md (first stages only, e.g. F on X 10-66), rq-hydro-rain-first-stage.md (first stage only, pooled F 21.3; second stage never run), rq-clawback-size-rdd.md (design note of 2026-08-18; density check and Tier-1 RDD never run). 2) Vintage/ownership: none of these 17 notes reports ten-seed or 2026-10-27/28 ownership-rebuilt figures. Nuclear T3/slope panel X and n_full are the 2026-10-19 vintage; its 1/|RD'| was restated from firm_x rebuilt 2026-10-22 (reproduction relaxed to 0.15% of se). Holiday quantity panels predate the 2026-10-21 EDP ownership fixes (own-wind net-position run found only EDP legs stale; pooled results unchanged within 0.002). Sequential-market premium (2026-08-21) predates all ownership corrections; marking it superseded by rq-da-id-premium.md is my inference, the note does not say so. 3) Conflicting figures: nuclear slope-test Nash value differs between §6.2 (about -1.4 over 2019-26, -2.3 in 2024-26, lambda -0.92/-0.71) and §7.1 (lambda -1.04, P_N -3.39 in 2024-26); §7.1 is used as current. Nuclear T3 rejection over 2019-26 (AR p 0.003) is carried by register-gap days (snapshot days p 0.13); the note says it should not be quoted without that caveat. Own-wind 'alone' total -0.20 reproduces as -0.202 (C1) and -0.218 (C0) in the 2026-11-05 run. 4) Missing intervals: nuclear T2, DA-ID IV (+0.95, se 0.39), sequential premium, IVPEE stacked theta (only month-start sd), own-wind 'alone' (se only) have no stated 95% interval. 5) Not tabulated but conduct-relevant: nuclear reservation prices (ANAV EUR 35 post-cap, slope on forward price -0.07 (0.03), 95% [-0.125, -0.020]; CNAT cap-to-post change +EUR 5.0 [-10.4, 50.7]); nuclear operator split (other-operator IV gamma +21.0 (11.8), AR [4.2, 86.0], implied beta about 14); own-wind by-firm results (Repsol NX_tot -0.63 [-0.89, -0.36], 20x its Nash reference, unexplained); intraday-surprise fleet-response table; holiday s x P refinement and per-firm betas (folded into checks). 6) Status labels are judgement where notes do not use them: 'failed a check' for nuclear T3 (gap-day contamination, weak instruments), nuclear 2024-26 slope cells (power), MIC near-miss (density), IVPEE 2024 (power).


### C. The gas cap

**G1. How much of the gas-cap subsidy did plants pass into their declared cost on day one?**  
declared cost: variable term of the minimum-income condition (cab) of gas combined cycles; Event jump J: change in each unit's mean log(declared/gross fuel-and-carbon cost), 7 days before vs 7 days from 2022-06-15, median over units, against 273 pre-cap placebo dates. Sample: 50 Iberian gas units (43 ES, 7 PT) with plant-specific efficiency, Turbogas out; 2021-06 to 2023-06.  
Estimate: J = -0.544 (log points); full pass-through would give -0.721. Interval: none (placebo-date band 2.5/97.5%: -0.125 / +0.124; most negative placebo -0.291). Benchmarks: J = 0: none of the subsidy passed into the declared cost (subsidy kept); J = -0.721: full pass-through (declares its net cost, the price-taking benchmark). Not a Nash benchmark..  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Placebo: actual jump is about 4x the widest placebo band (passes). Descriptive only, no standard errors; shortfall from -0.721 attributed to the first days lagging, not a lasting gap.  
Source: notes/rq-gas-cap-declared-cost.md, §2 The declared cost passes through about nine-tenths of the subsidy.

**G2. What share of the subsidy entered declared costs over the cap months?**  
declared cost (minimum-income variable term), gas combined cycles; Pass-through share rho by month and by firm: each unit's own March to mid-June 2022 declared/gross ratio held fixed; days with subsidy >= EUR 20; firm-block bootstrap in the paired test (G1b). Sample: 50 Iberian gas units, June 2022 to January 2023; bootstrap: 8 of 10 Iberian firms that declare, 199 draws.  
Estimate: rho 0.92-1.00 June-October 2022 (bid-time subsidy), 0.74-0.88 in small-subsidy months; firm-block bootstrap rho 0.91. Interval: [0.86, 0.96] (firm-block bootstrap, G1b). Benchmarks: rho = 1: full pass-through (declares net cost, price-taking); rho = 0: subsidy fully kept. The note says rho is a lower bound: with the post-cap declared/cost ratio as reference, rho would be about 1..  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: No formal test of rho = 1 was set; bootstrap interval excludes 1 but the note reads rho as a lower bound (reference ratio rose to 1.25-1.36 after the cap). By firm Jun-Oct 2022: 0.83 (Iberdrola, 8 units; Engie, 4) to 1.02 (TotalEnergies). Small-subsidy months noisy.  
Source: notes/rq-gas-cap-declared-cost.md §2 and §3 Caveats; notes/rq-crisis-quantity.md §G1 results (G1b).
> Verifier: '0.74-0.88 in small-subsidy months' is wrong. December 2022 (rho 0.88) had a median bid-time subsidy of EUR 130 and is not a small-subsidy month. The small-subsidy months are November 2022 (rho 0.76, subsidy EUR 23) and January 2023 (rho 0.74, subsidy EUR 28). Say instead: 'rho 0.92-1.00 June-October 2022, 0.88 December 2022, 0.74-0.76 in the small-subsidy months (Nov 2022, Jan 2023)'. Add by country (bid-time): Spain 0.93, Portugal 0.96 (declared-cost §2; also crisis-quantity E1). G1b sample: unit-days with subsidy >= EUR 20, 2022-06-15 to 2023-02-25. The caveat states the declared sample is 50 units in 11 firms.

**G3. Did Portuguese gas plants' declared costs respond to the subsidy like Spanish ones?**  
declared cost (minimum-income variable term), Portuguese gas combined cycles; Same day-one jump J as the thermal declared-cost event, Portuguese units alone, against 273 placebo dates. Sample: 7 Portuguese units (Lares 1-2, Pego 3-4, Ribatejo 1-3) vs 45 Spanish; 2022-06-15 event.  
Estimate: J Portugal = -0.609 (full pass-through -0.744); Spain -0.544 (full -0.721). Interval: none (placebo band Portugal -0.161 / +0.121). Benchmarks: J = 0: no pass-through; J = full-pass-through value: declares net cost (price-taking benchmark).  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Rule met for Portugal (below 2.5th placebo percentile and within 0.15 of full). Spain misses only the closeness leg (0.177 from full); the note calls that criterion too tight.  
Source: notes/rq-crisis-quantity.md, E results (E1).

**G4. Does a regulatory step in the reference gas price size declared-cost pass-through?**  
declared cost (minimum-income variable term), gas units; Event J at the reference-price (PRGN) steps that cut the subsidy by ~EUR 9/MWh; implied rho read off predicted J at rho = 0 and rho = 1; power rule: gap >= 2 placebo sd. Sample: 48 units, 1 January 2023 step (PRGN 40 to 45), mean subsidy EUR 41.  
Estimate: implied rho = 0.78 (1 Jan 2023 step only). Interval: none (rough band about 0.4-1.2 from one placebo sd of J). Benchmarks: rho = 1 full pass-through (price-taking cost); rho = 0 subsidy kept.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Power gate passed for 1 Jan 2023 (gap 0.148 >= 0.112); 1 Feb 2023 step underpowered (not reported); 1 Mar 2023 skipped. One event only.  
Source: notes/rq-crisis-quantity.md, I3 results.

**G5. What share of the subsidy reached offers near cost (headline offer-side estimate)?**  
gas combined-cycle offers: run20 = share of capacity offered within EUR 20 of own cost, in predicted in-money hours; B3 dose-response vs Italy: weekly Iberia-minus-counterfactual gap (Xu 2017 generalised synthetic control, r = 0 by cross-validation) regressed on the dose g_w (full minus no pass-through end); rho = 1 + b. Sample: 49 Iberian and 44 Italian gas units, 92 weeks 2021-09 to 2023-06; 46 post-cap weeks; margin EUR 50; 10 Iberian / 12 Italian firm clusters.  
Estimate: rho = 0.73 (quoted with a central band 0.5-0.85 across gas controls). Interval: [0.51, 1.03] (firm-block bootstrap, 199 draws). Benchmarks: rho = 1: full pass-through (offers at net cost, price-taking); rho = 0: no pass-through (subsidy kept as markup). Not a Nash benchmark. rho = 0 rejected at every r; rho = 1 just inside..  
Nash rejected: not tested. Price-taking rejected: no. Status: current. Checks: All pre-fixed checks pass on the main sample: timing permutation p 0.000 (45 shifts); without Dec 2022 0.74, without Oct-Nov 0.73; gas controls 0.54-0.58 inside. Trend version 0.79 [0.66, 0.91] excludes 1. Fourth Italian specification, requested after three failed. LNG confound ruled out at pre-set power (power 1.00); storage uninformative (power 0.42). About ten firm clusters bind.  
Source: notes/rq-crisis-quantity.md B3 results and B3 check results; notes/rq-gas-cap-control.md Plain reading and LNG and storage: results.
> Later figure: Unchanged by the later physical-supply test. notes/rq-gas-cap-control.md 'LNG and storage: results' (2026-11-05): 'The quote is unchanged: ρ 0.73 [0.51, 1.03], band 0.54–0.85.' Physical control sets give 'Iberian P1–P3 0.762 [0.615, 0.916]; + bid-time MIBGAS + PSV 0.914 [0.376, 1.318]'. None is favoured.

**G6. Does controlling for gas prices change the offer pass-through estimate?**  
gas combined-cycle offers, run20 (as B3); B3 with weekly gas-price controls (delivery-day or bid-time MIBGAS, PSV, spread), same firm-block bootstrap draws; H6 contrast and control-set comparison. Sample: as B3 main (r = 0, 199 draws, 10 Iberian / 12 Italian firms).  
Estimate: rho 0.544 (delivery-day MIBGAS + spread); 0.583 (delivery-day MIBGAS); 0.722 (bid-time MIBGAS); 0.847 (PSV alone); 0.823 (bid-time MIBGAS + PSV). Interval: [0.097, 0.872] (MIBGAS + spread); [0.118, 0.941] (MIBGAS); [0.237, 1.128] (bid-time MIBGAS); [0.622, 1.085] (PSV). Benchmarks: as B3: rho = 1 full pass-through, rho = 0 subsidy kept.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Contrast none minus both controls +0.182 [-0.119, +0.584]: gas response not detectable. No-dose test uninformative by rule (power 22%). No control set favoured by blocked CV (best gain 0.8% vs 10% required). Dose explains 95.7% of MIBGAS variance. Earlier quoted band 0.55-0.75 superseded by 0.5-0.85. Full pass-through outside the delivery-day-controlled interval, inside the bid-time/PSV ones.  
Source: notes/rq-gas-cap-control.md (3) Better controls; notes/rq-crisis-quantity.md H6 results.
> Later figure: Add the interval for bid-time MIBGAS + PSV: 0.823 [0.334, 1.206] (rq-gas-cap-control.md (3)). Add the physical-supply sets from 'LNG and storage: results': Iberian LNG/storage rows 0.762 [0.615, 0.916]; with bid-time MIBGAS + PSV 0.914 [0.376, 1.318].

**G7. How sensitive is the offer pass-through to specification choices?**  
gas combined-cycle offers, run20; Specification curve over B3: margin (EUR 20/50/all hours) x r 0-5 x gas controls x trend x window end; point estimates, 216 cells. Sample: as B3; 216 cells (72 at the main EUR 50 margin).  
Estimate: all cells median rho 0.70 (middle half 0.32-0.87); main margin quartiles 0.37 / 0.56 / 0.68; honest range at main margin about 0.4-0.75. Interval: none (spread across specifications, not a confidence interval). Benchmarks: rho = 1 full pass-through, rho = 0 subsidy kept.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Margin and gas controls move rho; r, trend, window end do not. 71% of cells pass permutation (all at main margin). Run before the 2026-11-05 correction that bid-time/PSV controls give 0.72-0.85, so the 'with controls 0.41-0.45' reading uses delivery-day MIBGAS only.  
Source: notes/rq-crisis-quantity.md, G1 results (G1a).
> Later figure: The 'with controls 0.41-0.45' reading at the main margin uses delivery-day MIBGAS only. rq-gas-cap-control.md (3), 2026-11-05: controlled rho is 0.54-0.85 depending on the gas series. rq-crisis-quantity.md H6 correction: 'the central band is **0.5–0.85**, not 0.5–0.75'.

**G8. Do offers pass through less of the subsidy than declared costs?**  
difference: declared-cost rho minus offer (run20) rho; Paired firm-block bootstrap of declared rho and B3 offer rho on the same draws. Sample: main B3 sample, r = 0, 199 draws; 8 of 10 Iberian firms declare.  
Estimate: d = +0.19 (mean +0.16); offer rho 0.73, declared rho 0.91. Interval: [-0.12, +0.38]. Benchmarks: d = 0: offers and declarations pass through the same share; d > 0: offers keep more of the subsidy than declared costs suggest.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Rule: no difference detectable (interval holds 0); 87% of draws d > 0; pairing removed little noise (correlation +0.29). The two rho are different objects.  
Source: notes/rq-crisis-quantity.md, G1 results (G1b).

**G9. Does the offer price fall one euro per euro of subsidy?**  
gas combined-cycle offer prices: p50 (price at half of offered volume) and p_mid, minus gross cost; I4: Xu generalised synthetic control vs Italy, weekly median in predicted in-money hours; ATT_w = a + c * mean weekly subsidy; rho = -c. Sample: 49 Iberian / 28 Italian units (y50), 48 / 25 (ymid); post-cap weeks 2022-06 to 2023-06; r = 1 by cross-validation.  
Estimate: rho 1.17 (y50), 1.34 (ymid); with MIBGAS control 0.62 / 0.60. Interval: y50 [0.71, 1.74]; ymid [0.95, 1.90] (firm-block bootstrap, 199). Benchmarks: rho = 1 (c = -1): full pass-through, offer falls by the subsidy (price-taking cost pass-through); rho = 0: no fall (subsidy kept).  
Nash rejected: not tested. Price-taking rejected: no. Status: current. Checks: Gates pass for both: permutation p 0.000; trend version 1.05 [0.74, 1.39] / 1.11 [0.87, 1.54] inside. Uncontrolled slope absorbs gas co-movement (cost_gross enters y); not independent of B3 (same panel). Earlier price-level designs failed their post-cap check (+EUR 168).  
Source: notes/rq-crisis-quantity.md, I4 results.

**G10. Within Iberia, did offers near cost reach the full pass-through end?**  
gas combined-cycle offers, run20 and run20_gross; B1: actual Iberian mean vs two ends built from each unit's last eight pre-cap weeks of markups carried forward (no Italian counterfactual); linear interpolation. Sample: Iberian main sample, 35 weeks with a subsidy (mean subsidy EUR 102).  
Estimate: rho approx. 1.1 on run20 (actual 0.665 vs full end 0.646, none end 0.388). Interval: none. Benchmarks: rho = 1: full pass-through (offers at net cost); rho = 0: pre-cap markups over gross cost kept.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Descriptive only. B1's power check for the Italian design STOPPED: MDE 0.133 vs half-gap 0.129 (run20), run20_gross far off; passes only after a post-result amendment restricting to high-subsidy months (gap 0.410).  
Source: notes/rq-crisis-quantity.md, B1 The two ends and the minimum detectable effect.

**G11. Mean pass-through against Italy over high-subsidy weeks (in-money hours)?**  
gas combined-cycle offers, run20, predicted in-money hours; B2: Xu generalised synthetic control vs Italy, ATT over 19 high-subsidy weeks; rho = 1 + ATT/0.410. Sample: 49 Iberian and 44 Italian units x 92 weeks; 10 Iberian / 12 Italian firms.  
Estimate: rho 1.06 (ATT +0.025). Interval: [0.87, 1.29]. Benchmarks: rho = 1 full pass-through; rho = 0 subsidy kept.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: failed a check. Checks: STOP: post-subsidy gap should be ~0 but is +0.134 [+0.019, +0.197], outside +/-0.05 at every r; rho cannot be read. Superseded by B3.  
Source: notes/rq-crisis-quantity.md, B2. Pass-through against Italy.

**G12. Mean and dose pass-through against Italy using all hours?**  
gas combined-cycle offers, run20, every hour; B2 and B3 on all hours (sample chosen after the in-money B2 stopped); Xu r = 2. Sample: 51 Iberian and 53 Italian units x 92 weeks; 12 / 13 firms.  
Estimate: B2 rho 1.17; B3 rho 1.18 (0.96 with trend). Interval: B2 [0.97, 1.50]; B3 [0.78, 1.50]. Benchmarks: rho = 1 full pass-through; rho = 0 subsidy kept.  
Nash rejected: not tested. Price-taking rejected: no. Status: failed a check. Checks: B1 power fails on all hours (placebo MDE 0.207 > 0.170); B2 after-check holds at r = 2 only (fails at r = 1, 4, 5); B3 all-hours fails timing permutation (p 1.000) and MIBGAS control (0.70-0.77). Corroboration/footnote only.  
Source: notes/rq-crisis-quantity.md, B2 on all hours; B3 check results.
> Later figure: Superseded by B3 in-money 0.73 [0.51, 1.03]. B2 note: 'For scale only, not a result: subtracting the after-gap would give ρ ≈ 0.73.'

**G13. Does a daily dose sharpen the offer pass-through estimate?**  
gas combined-cycle offers, run20, unit-day; G2: Xu generalised synthetic control on unit x day matrix, ATT_d on daily dose g_d; rho = 1 + b. Sample: 41 Iberian and 39 Italian units x 638 days; 10 / 10 firms; r = 3.  
Estimate: rho 0.82. Interval: [0.63, 1.01] (not to be quoted per rule). Benchmarks: rho = 1 full pass-through; rho = 0 subsidy kept.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: failed a check. Checks: Timing permutation fails (p 0.117 over 206 day shifts) -> STOP. Trend 0.96 [0.84, 1.09]; controls 0.84-0.89. 38% of cells missing.  
Source: notes/rq-crisis-quantity.md, G2 results.
> Later figure: B3 all hours with trend: 0.96 [0.76, 1.19]. rq-crisis-quantity.md B3 check results: 'All hours drops to a footnote.'

**G14. Can a better counterfactual (hour-of-day or within-Iberia) estimate pass-through?**  
gas combined-cycle offers, run20; H7 hour-of-day blocks vs Italy; H8 within-Iberia ridge prediction from bid-time conditions; both gated on pre-cap fit before any rho. Sample: as B3 (49 Iberian, 44 Italian units); H8 36 fit weeks.  
Estimate: none (no rho computed). Interval: none. Benchmarks: would be rho = 1 full pass-through, rho = 0 subsidy kept.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: stopped before estimate. Checks: H7 STOP: pre-cap R2 median -0.70 vs baseline -0.35 (two blocks dropped). H8 STOP: both Iberian variants fail gate (c), MAE 0.89-1.05 of Italy-based vs <=0.80 required.  
Source: notes/rq-crisis-quantity.md, H7 stage 1 results; H8 stage 1 results.

**G15. Did hydro offers, relative to the price-taking water value, move at the cap start?**  
hydro offers: ocf (offer price at expected running share) over lambda* (price-taking forward water value); Event J: change in median log(ocf/lambda*), 7 days before vs 7 days from 2022-06-15, against 273 placebo dates; per firm. Sample: EDP 5 units, Iberdrola 7, all eligible 20; non-pumped storage hydro; Endesa and Naturgy STOP (too few units).  
Estimate: J EDP -0.102, Iberdrola -0.075, pooled -0.061; EDP minus Iberdrola -0.027 (log points). Interval: none (placebo band EDP -0.311/+0.280; Iberdrola -0.162/+0.206; pooled -0.120/+0.193). Benchmarks: J = 0: offer moves with lambda* (stays relative to the price-taking water value); J = -0.72: thermal-style fall (pricing off the subsidised gas cost). Measures a change, not the level of conduct..  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Inside band for both firms and the contrast; thermal-sized fall (-0.544) lies outside both bands; checks (a)-(f) leave firm positions unchanged; pooled row not robust under lambda*90s. lambda* fell the week before, so flat ratio means offers caught up. Clawback date (2021-06-01) secondary: all inside.  
Source: notes/rq-gas-cap-hydro-link.md, §2.2 The cap start, 2022-06-15.

**G16. Did hydro offers fall relative to lambda* on the cap's first day (post hoc)?**  
hydro offers relative to lambda*; Post hoc one-day change D-1 to D at 2022-06-15 against 269 placebo dates; plus capacity-weighted 7-day J. Sample: EDP 5, Iberdrola 7, all eligible 20 units.  
Estimate: one-day change EDP -0.214, Iberdrola -0.275, pooled -0.155; capacity-weighted 7-day J Iberdrola -0.225. Interval: none (placebo band EDP -0.168/+0.182; Iberdrola -0.184/+0.166). Benchmarks: 0: offers track lambda*; -0.72: thermal-style fall.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Post hoc, not pre-registered; below band in both firms but day before is the ratio's peak (partly undoes a run-up). Unit-level: DUER, TAJO, HCHI unusual; with 20 units 1-2 extremes expected by chance; read as a lead.  
Source: notes/rq-gas-cap-hydro-link.md, §2.4 Post hoc: the one-day change.

**G17. Do hydro offers relative to lambda* move with the daily subsidy dose?**  
hydro offers relative to lambda*; Dose regression y = a_u + phi * x_d (log fall in gas cost from subsidy), with/without log MIBGAS; placebo shifted windows. Sample: 2022-06-01 to 2023-03-31; EDP 7 units, Iberdrola 9, all eligible 27.  
Estimate: phi Iberdrola 0.171 (0.157 with gas); EDP 0.052 (0.447 with gas); pooled 0.145 (0.223 with gas). Interval: none (placebo bands: Iberdrola -0.39/+0.34; EDP -0.39/+0.30 and -0.39/+0.28 with gas; standard errors indicative). Benchmarks: phi = 0: offer does not move relative to lambda*; phi = 1: thermal-style response to the gas cost shifter.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Only EDP with gas control above band (1 of 4 firm cells); about 8 independent placebo windows; one episode collinear with winter gas hump. Endesa, Naturgy not findings.  
Source: notes/rq-gas-cap-hydro-link.md, §2.5 Dose.
> Later figure: Capacity-weighted 7-day J, in full (§2.4): EDP −0.140 (6.6th pct, two-sided 0.12); Iberdrola −0.225 (2.6th pct, two-sided 0.055); all eligible −0.143 (2.2nd pct, 0.08). The band was computed after the fact.

**G18. How far are hydro offers from the price-taking water value, by firm?**  
hydro offers: monthly median ocf/lambda*; Descriptive monthly ratio of offer at expected running share to price-taking water value. Sample: EDP and Iberdrola eligible units, 2022-03 to 2022-12; Naturgy March 2022 to May 2023.  
Estimate: ratio EDP 0.77-1.04; Iberdrola 0.95-1.39; Naturgy 1.7-3.1. Interval: none. Benchmarks: ratio 1: offers at the price-taking water value; above 1: offers above it (withholding/markup or a water value beyond lambda*).  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Descriptive only; lambda* is a lower bound on water value; Endesa too thin to read.  
Source: notes/rq-gas-cap-hydro-link.md, §2.3 What the days around the cap show.

**G19. How much of gas plants' static price-cost gap is their declared start-up cost?**  
declared cost: minimum-income fixed term F and variable term V vs static gap M = sum (p - c) q; Ratio of sums F/M (lower bound on declared-cost share) and (F + W)/M with W = (V - c)Q (upper bound), cap window out. Sample: 84 plants with plant-specific efficiency (44 ES, 10 PT gas; 28 coal), 2018-01-01 to 2025-03-18; 32,326 unit-days after amendment.  
Estimate: gas F/M 5-13% in 2019-2024 (23% in 2018); ES gas 2-5%; (F + W)/M 28-70% (gas pooled); residual E EUR 14-18/MWh ES gas 2021-22. Interval: none. Benchmarks: Share of the static gap explained by the plant's own declared cost; residual E is margin above everything declared but includes inframarginal rent, so it is explicitly not a markup or market power.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Join gate (E >= -100 on 95% of days) FAILED as written (79-94%); passes at 100% after a post-result amendment dropping 1-3-period shutdown-tail days. Cap-window variants move 2022/2023 by <=1.7 pp (main stands). Declaration strategic; declaring days selected.  
Source: notes/rq-startup-cost-correction.md, §2 Results and §4 What this means for the paper.

**G20. After the 2025 switch, how much of the gap does the declared SCO requirement explain?**  
declared cost: SCO lump sum (sco_fixed_eur) plus cleared tranche prices beyond fuel, D/M; Upper bound D/M with D = Fijo + sum(b q) - cQ, tranche prices from the offered curve; compared with pre-switch (F + W)/M. Sample: 2025-03-19 to 2026-05-31; 294 accepted declaring ES gas unit-days, 9 PT.  
Estimate: D/M ES gas 0.785; gas pooled 0.790 (vs 0.73-0.74 before the switch). Interval: none. Benchmarks: Upper bound on the share of the static gap explained by declared requirement; not a conduct benchmark (residual includes inframarginal rent).  
Nash rejected: not tested. Price-taking rejected: not tested. Status: current. Checks: Gate passes 100%; rules written after scoping saw the headline (reproduction, not blind). Within +/-0.10 of pre-switch. No lower bound identifiable after the switch. Declaring days clear 4.5% vs 14.5%: heavy selection; median slack 8.6% of Fijo.  
Source: notes/rq-startup-cost-correction.md, §5.3 Results.
> Later figure: For Spanish gas only, the range is 'a range, **2–5% (F) to 39–81% (F + W)**' (§2.4). After 2025-03-19 only the upper bound exists, D/M 0.785 for Spanish gas (§5.3; see row 20).

**G21. Did unhedged hydro plants raise offers more under the 2021 windfall levy?**  
hydro offers under the 2021 levy (RDL 23/2021); Design 4: differential forward-contract exposure within Spain (exempt contracted energy), predetermined exposure. Sample: 23 Spanish hydro units.  
Estimate: beta log(median offer) +0.0067 (t 3.76); levels +0.31 (t 0.43); marginal accepted offer -0.73 (t -1.96). Interval: none. Benchmarks: beta = 0: levy not passed into offers by more-exposed plants; per-MWh levy predicts an additive shift in levels.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: failed a check. Checks: Both placebos pass, but sign depends on outcome and levels range 0.13 to 1.82 across trimming; reservoir control moves beta only in third decimal. Note: cannot produce a reportable estimate.  
Source: notes/rq-gas-cap-conduct.md, How it compares to the alternative — both are now live.

**G22. Does drought steepen firms' residual demand (a market-power instrument)?**  
firm residual-demand price impact (first stage for market power in the cap window); Fill anomaly on log firm price impact (band-density estimator, own offers removed), firm x hour + year-month FE. Sample: 10 firms, 350,995 firm-periods; cap window 19 month clusters.  
Estimate: beta +1.14 (se 1.64) pooled; +10.1% price impact per 1-sd wetter move; firms +0.17 to +2.93. Interval: roughly [-18.3%, +38.5%] per 1-sd move (95%). Benchmarks: Channel needs beta < 0 (drought raises price impact, more scope for markup); not a conduct estimate itself.  
Nash rejected: not tested. Price-taking rejected: not tested. Status: stopped before estimate. Checks: First stage absent: wrong sign in all ten firms, none significant (max t 1.49); no heterogeneity by rival hydro exposure. Drought kept as a control only.  
Source: notes/rq-gas-cap-conduct.md, 2026-08-21: the 2022 drought — It is not an instrument for market power.
> Verifier: The status 'failed a check' is inaccurate. Both placebos pass ('**both placebos pass** — the only design here that manages that'). The design stopped because 'It still cannot produce a reportable estimate, because the sign depends on which outcome variable is chosen'. The levels form is the correct one, and 'in levels nothing survives sample choice'. Use the status: stopped, not reportable (outcome-dependent sign; levels unstable across trimming). Add the 2026-08-18 update in the same section: the MITECO reservoir fill-anomaly control 'moves beta in the third decimal place on every specification'. Marginal accepted offer across trimming: −0.69 → +0.17.

**Estimates the verifier found missing from this group (kept as reported, not re-verified):**

The extraction missed these conduct estimates. In the listed notes:
(1) rq-gas-cap-control.md 'LNG and storage: results'. Rho with physical gas-supply controls: Iberian LNG tank fill, storage anomaly and arrivals (P1–P3) give 0.762 [0.615, 0.916]; adding bid-time MIBGAS and PSV gives 0.914 [0.376, 1.318]; the Italian sets give 0.689–0.766, reported only. None is favoured. LNG gap world rejected: P1 slope per sd −0.004 [−0.038, 0.032], P3 interval [−0.054, 0.013], power 1.00. Storage P2 is uninformative (power 0.42).
(2) rq-gas-cap-control.md (1) No-dose tests. The Iberian-minus-Italian gas response in weeks with no subsidy is not a pass-through rho, but it tests the confound in rho. Pooled slope −0.00057 per EUR/MWh, double bootstrap [−0.00232, +0.00028], power 22% at c* +0.00087. Uninformative by the rule.
(3) rq-gas-cap-declared-cost.md §5. Capacity offered near cost (run20) in predicted in-money hours, pre-trend test: Iberia 0.64–0.72 / 0.60–0.67 / 0.63–0.73 (flat across the cap); Italy falls in March 2022. Main sample trend +0.038 (0.033), placebo 2021-10-01 +0.100 (0.059): 'fails'. This is a withholding-level descriptive and a design gate.
(4) rq-gas-cap-hydro-link.md §2.2, secondary date. Clawback announcement 2021-06-01: J EDP −0.037 (band −0.30/+0.35), Iberdrola +0.007 (−0.11/+0.15), Endesa −0.035 (4 units, not a finding), pooled −0.026, EDP minus Iberdrola −0.043. 'All inside.' It is mentioned in row 15's checks only and could be its own row (levy conduct, hydro).
(5) rq-startup-cost-correction.md §2.7. Unit-by-year fixed effects, gas: F per MWh '+€0.16 per 10 points of VRE share (t 4–5)'; static gap falls '€4.0–4.3 per 10 points (t −7)'. Descriptive; Jha & Leslie direction.
(6) rq-gas-cap-conduct.md 2026-08-21. Market-level drought first stage β −0.645 (se 0.932) on residual-demand elasticity. Context only.

Outside the six listed notes, these are superseded or stopped price-side conduct results in docs/specs/2026-10-28-gas-cap-conduct-design.md, which the table should cite:
- Step 2, interactive fixed effects (IFE) vs Italy: 'NOT IDENTIFIED'. At r = 8, A −0.12 [−0.52, +0.65] and B −1.69 [−4.47, +0.68]. The post-cap gap is '+€168 [+25, +479]'.
- Step 2b, sharp break: 'STOP on every variant'. J(p_mid) −190 [−422, −67] (rho 1.8).
- Step 2c, monthly Design B within Iberia: p_mid with controls 'ρ = 1.06 [0.58, 1.90]' (linear 1.60 [0.48, 2.95]). The premise passes, but identification is before/after. p_band 1.04 [0.90, 1.16] is the clearing price by construction, not conduct.
- Difference in discontinuities vs Italy 'FAILS at every k' (D(mmid) −197 [−430, −68], rho 1.85). Italian-looking subset FAILS.
- Step 2d, Great Britain: the price outcome FAILS (trend +330/yr). The run outcome fails one placebo (−0.066). The pooled estimate is not run.
The memory file also records non-gas-cap conduct legs (legs A–D, hydro at-cost IV, price-taking simulation, holiday quantity test, and others). They are outside these notes and should be gathered from their own rq-*.md notes.

**Open conflicts flagged by the extractor:**

1) Declared-cost rho: the firm-block bootstrap gives 0.91 [0.86, 0.96], which excludes 1, but §3 of rq-gas-cap-declared-cost.md calls ~0.9 a lower bound (rho ~1 with the post-cap reference ratio). No pre-fixed test of rho = 1 exists, so the full-pass-through verdict was left "not tested". 2) B3's quoted band changed over time: 0.55-0.75 (B3 checks, 2026-11-03) and 0.5-0.75 (H6) were corrected on 2026-11-05 to 0.5-0.85, and the union of the intervals widened to 0.10-1.21. The euro and welfare figures (C, D, F, J) still use 0.55-0.75 and were not recomputed. G1's spec-curve reading "honest range 0.4-0.75" predates that correction and used delivery-day MIBGAS controls only. 3) Pass-through rows are not Nash tests. rho = 1 (full pass-through) is treated as the price-taking benchmark, and rho = 0 (subsidy kept) as the strategic extreme. Rejection of rho = 0 (B3: yes at every r; B2 all hours: yes) is recorded in checks, not in nash_rejected. 4) The earlier gas-cap price designs ("steps 2 and 2c", p_mid rho 1.06, post-cap gap +EUR 168, and the 2b sharp-break stop) are only cited from rq-crisis-quantity.md I4. Their figures are not in my six files (they are in docs/specs/2026-10-28-gas-cap-conduct-design.md), so no row was made. 5) The no-control-group passthrough design in rq-gas-cap-conduct.md is marked "not identified (9481fc2)" in its header, with no estimate in the file. The HP2008 PctAchieved design there was never run. 6) The declared-cost note §5 run20 in-money pretrend is a check, not a conduct estimate: Iberia is flat at 0.63-0.73, and the step-1 rule fails on the 2021-10-01 placebo (+0.100). It is omitted as a row. 7) Hydro-link J and dose are placebo bands, not confidence intervals: about 20 independent placebo windows for J and about 8 for the dose. 8) The start-up-correction gate failed as written and passed only after a post-result amendment. 9) The levy Design 4 figures in rq-gas-cap-conduct.md (2026-08-14/18) predate the 2026-10-27/28 ownership rebuild. No rerun is recorded in these files.
