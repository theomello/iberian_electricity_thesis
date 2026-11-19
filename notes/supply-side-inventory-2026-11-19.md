# Supply-side inventory: every note and spec, and where it goes (2026-11-19)

**Rule (user, 2026-11-19):** the supply side is used for context; it is linked to the headline (demand) results only
where the link is called for. Add as little as possible.

**Destinations.**
- **C** = context in chapter 2 (main text);
- **V** = the short section "the reform through the market", the validity conditions of the demand estimates;
- **A** = appendix (method, or one line in "designs and lessons");
- **P** = a separate gas-cap/conduct paper (`docs/specs/2026-11-02-paper-outline.md`);
- **N** = nowhere (stays in the repo as a record).

Grades as in `docs/specs/2026-11-08-conduct-evidence-table.md`.

## 1. Foundations and descriptive (August–October)

| File | What it is / found | Dest. | Reason |
|---|---|---|---|
| `2026-08-07-spain-market-data-design.md`, `docs/data-reference/` | the data build | A | data appendix (sources, traps) |
| `report-ownership-mapping.md`, `unmapped-prefixes-to-confirm.md` | ownership by date and share | A | data appendix; one sentence in C |
| `2026-08-24-descriptive-price-formation-design.md`, `rq-descriptive-price-formation.md` | price formation 2018–26; setter check: 44% of hours a unit with a cost, 16% the open France line, 23% buy bids; residual-demand elasticity η fell, not separable from the price level | **C** (setter check only) | who sets the price is the context; the η trend is not identified |
| `result-markups-vs-hhi.md` | η fell by half 2018–23 while concentration fell | N | superseded by the conduct estimates; not identified against the price level |
| `rq-hedge-ratios.md` | published hedge ratios did not rise; "hedged" is mostly own retail | A (one line) | supports using the net position n |
| `rq-self-supply-cost.md` | integrated firms supply own customers with nuclear, hydro, wind; book balancing | **C** (one sentence, with the bilateral-hydro fact) | exposure context: retail customers do not see the hourly price |
| `rq-da-id-premium.md` | day-ahead minus intraday premium +€0.6; +0.95/GW with the outage instrument | N | user decision: out |
| `continuous-intraday-data.md` | data note | N | |
| `literature-to-thesis.md`, `literature-iberian-exception.md`, `positioning-vs-jha-leslie.md` | literature mapping | A/P | cite in C where used; Jha–Leslie as the start-up-cost caveat |

## 2. Cost measures

| File | What it is / found | Dest. | Reason |
|---|---|---|---|
| implied gas/coal cost (`_bid` columns), `min-income-condition.md` | plant-specific cost and the declared minimum-income cost | A | method; thermal result rests on it |
| `hydro-water-value-design.md`, `2026-09-29-water-value-design.md`, `rq-water-value-forward.md` | λ* from forwards matches EDP's revealed value within 6% (corr 0.81–0.91) | A | method; the hydro result rests on it |
| `rq-startup-cost-correction.md` | declared start-up term 5–13% of the static gap (bound up to 28–70%) | A (one line) | the caveat that static markups ignore start-up costs |
| `rq-midday-hydro.md`, `rq-hydro-rain-first-stage.md`, `rq-heat-demand-conduct.md`, `rq-sequential-market-premium.md`, `rq-clawback-size-rdd.md` | August probes and sketches before the framework | N | superseded by the framework; none graded |

## 3. Framework and legs A–D (September–October)

| File | What it is / found | Dest. | Reason |
|---|---|---|---|
| `2026-09-29-thesis-framework-design.md` | offer − cost = β·X, four legs | A | the condition is stated in chapter 3; the four-leg plan is history |
| leg A (`ml-methods-to-legs.md` §A, EDP hydro panel) | hydro within the day, β small | A (one line) | superseded |
| `rq-leg-b-levels.md` | hydro vs λ*: β −0.26 [−0.72, 0.04], Nash rejected | A (one line) | superseded by the step estimator |
| `rq-leg-c-thermal-cost.md` | thermal in levels β ≈ 3 = merit order, not conduct | **A (footnote)** | the lesson: levels confound the merit order with conduct |
| `rq-leg-d-sign-of-n.md` | β 0.024; buyer markdown 0.19, later contract routing | A (one line) | superseded |
| `rq-forecast-first-stage.md` | forecasts lower every firm's net position | N | instrument diagnostics |
| `ml-methods-to-legs.md` | ML material mapped to legs | N | |

## 4. The conduct estimates (October–November)

| File | What it is / found | Dest. | Reason |
|---|---|---|---|
| `2026-10-01-step-offer-design.md`, `rq-step-estimator.md` | the step estimator | A | method of the C result |
| `rq-price-taking-simulation.md` | price-taker benchmark; ten seeds | **A** + one sentence in C | the thermal and hydro readings rest on it |
| evidence table rows 1.1–1.2 (O7, O8) | **thermal: β +0.01 [−0.08, 0.10], price-taking accepted (δ 0.1), Nash rejected** (A) | **C** | the conduct context |
| rows 1.3–1.5, `hydro-conduct-settlement.md` | **hydro: Nash rejected; price-taking not rejected, not established (bounded at 0.15)**; 2024–25 does not differ (final) | **C** | same paragraph |
| rows 2.1–2.3, `hydro-departure-by-firm.md` | the 2019–21H1 departure: ≈ €1/MWh on a few steps, no price effect, Iberdrola's, ends May→June 2021 | **C** (one paragraph) | with V's D1 |
| `2026-10-19-fixed-step-design.md`, `rq-fixed-step.md` | second hydro design; agrees in size, less precise; 2023 = routing | A (one line) | settled in `hydro-conduct-settlement.md` §2 |
| `rq-counterfactual-hydro.md` | hydro priced at λ*: price −€0.83 on average, −€2.2 in 2025 | N | a levels counterfactual; would invite a second, conflicting hydro reading in C |
| `2026-11-19-hydro-conduct-settlement-design.md` | gates G1, G3 fail before any run | A (one line) | why hydro is not settled further |

## 5. Quantity margins and stopped designs (October)

All **A, one line each** ("no withholding detected; the designs detect only large effects"), or N where noted.

| File | Found | Dest. |
|---|---|---|
| `2026-10-19-nuclear-cuts-design.md`, `rq-nuclear-cuts.md` | not answered (F 0.1–6.4) | A |
| `rq-reactor-outages.md` | outage moves n by 0.86 MW/MW (F 121); offer β −0.9 [−4.2, 0.7] | A |
| `2026-10-19-outage-events-design.md`, `rq-outage-events.md` | faults do not follow the stake; F too low | A |
| `2026-10-19-intraday-squeeze-design.md`, `rq-intraday-squeeze.md`, `rq-intraday-surprise.md` | descriptive / design fails | N |
| `2026-10-20-regional-holidays-design.md`, `2026-10-20-holiday-quantity-test-design.md`, `rq-regional-holidays.md` | book balancing; Nash rejected | A |
| `2026-10-21-own-wind-quantity-test-design.md`, `rq-own-wind-quantity.md` | stop (F 3.7/2.5) | A |
| `2026-10-21-self-supply-cost-design.md` | stop on power | A |
| `2026-10-20-mic-near-miss-design.md`, `rq-mic-near-miss.md` | stop (density jump) | A |
| `2026-10-20-france-link-design.md`, `rq-france-link.md` | stop at step 2 | A |
| `rq-fit-exits.md` | not viable in the window | N |
| `2026-10-21-clawback-exemption-design.md`, `-edp-retail-sale-`, `-post-auction-option-` | premises fail, never built | N |
| `rq-ivpee-tax-test.md` | 2018–21 tax steps pass through to declared costs (θ 1.45) | A (one line) or P |

## 6. Gas cap (October–November)

| File | What it is / found | Dest. | Reason |
|---|---|---|---|
| `rq-gas-cap-declared-cost.md` | declared cost passes ρ 0.91 [0.86, 0.96] (A); also the offer-limit fact (€0–180.30 to 2021-07-06) | **C** (one sentence) + P | context for 2022–23 prices; the offer-limit fact is needed in C for the June 2021 stop |
| `2026-10-28-crisis-quantity-design.md`, `rq-crisis-quantity.md` §K | offers ρ 0.87 [0.48, 1.00] within Iberia (B); welfare at ρ 0.73; adjustment charge and its exemption | **C** (one sentence: ρ 0.87, and that buyers paid the adjustment charge) + P | consumers' net price; the exemption ratio 0.48 is the volume check of θ |
| `2026-10-28-gas-cap-conduct-design.md`, `rq-gas-cap-conduct.md`, `rq-gas-cap-control.md` | Italy as control (five designs), Great Britain | P | comparison markets; fail or corroborate only |
| `rq-gas-cap-hydro-link.md` | hydro did not follow the cap | P | |
| `2026-11-02-paper-outline.md`, `2026-11-08-conduct-evidence-table.md` | the conduct paper and its ledger | P | the home for everything marked P |

## 7. Linking the reform to supply (November)

| File | What it is / found | Dest. | Reason |
|---|---|---|---|
| `2026-11-13-supply-side-extension-sketch.md`, `2026-11-13-tou-price-effect-design.md` | the reform moved evening − night price by −€2.39 (R1–R4 pass) | **V** | gives Δp for the feedback condition |
| `2026-11-14-hydro-levy-simulation-design.md` | the clawback-announcement hydro pattern lowered the window's price by €5.63/MWh; the reform contrast is −3.01 with pre-announcement hydro (H4 fails by a hair, H6 fails) | **V** (one sentence) | the coincident announcement moved the price level; the shape effect the demand side uses is the reform's |
| `2026-11-16-levy-reform-calibrated-design.md` | reform effect on the average price −€0.016, levy −€5.60; K4, K5 fail | V (with the line above) or N | same fact, other units |
| `2026-11-19-reform-market-power-design.md` | M2, D1 pass; M1 fails for 3 firms | **V** | supply did not respond strategically |
| `2026-11-19-short-notice-share-design.md` (T1), `2026-11-19-price-signal-feedback-design.md` (T3) | λ bounded; no feedback (≤ 7%) | **V** (T1 belongs to the industry chapter) | the validity conditions |
| `2026-11-19-season-boundary-design.md` | closed after Z1; tariff tables kept | N (tables reused) | |

## 8. What enters, in sum

- **C, chapter 2 (about 2 pages):** setter check; thermal price-taking (A); hydro bounded, Nash rejected; the
  2019–21H1 departure, one paragraph; self-supply and bilateral hydro (exposure); the gas cap in two sentences
  (ρ 0.91 declared, 0.87 offers; buyers paid the adjustment charge); the offer-limit fact.
- **V, end of the demand chapters (2–3 pages):** the reform's price effect, the clawback announcement's level effect,
  T2/D1, T3.
- **A:** data and ownership; cost measures (λ*, implied cost, declared cost); the step estimator and price-taker
  simulation; leg C footnote; one line per stopped design.
- **P:** the gas-cap and conduct paper (Italy, Great Britain, welfare, hydro link, quantity margins in full).
- **N:** about 20 files, kept as the record.
