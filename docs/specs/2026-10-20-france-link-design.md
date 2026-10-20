# The France link: a rotation of every firm's residual demand

**Status: stopped at step 2, 2026-10-20 (`notes/rq-france-link.md`).** Step 1 stopped by 0.001
(open-state prediction corr 0.299, French part F 621) and step 2 was run at the user's request.
The slope French supply adds is small: a GW of Iberian residual demand moves the price €4.26
when the line is predicted full and €3.58 when open (S ≈ 62, 87 after recalibration, against a
market slope of 326). The instrument moves the corrected stake (F 17–93), but the minimum
detectable β is 2.7 (hydro) and 9.9 (thermal), against the bar of 1.

**In one example.** Iberdrola withholds 100 MW at 8 pm. If the line to France is full, Spain
and Portugal clear as an island and the price rises by about €0.20/MWh (100 MW over 500 MW
per €/MWh). If the line has room, imports from France fill the gap and the price barely moves.
So a firm's stake in the price, X = n/|RD′|, is large when the line is congested and close to
zero when it is open. A price-taker offers the same either way. A firm with market power marks
up more in congested hours than in open ones, by an amount proportional to its net position:
a large net seller most, a net buyer in the other direction. Whether the line will be full is
predicted here from things no Iberian firm controls: the capacity the grid operators publish
before the auction, French nuclear availability and French demand.

---

## 1. Why this design

- **It moves the slope, not the position.** Every instrument so far moves a firm's net
  position n (outages, rain, wind, holidays). The hour effects absorb anything that moves
  every firm's |RD′| alike, so a slope shock was thought useless. It is not, because a slope
  shock moves each firm's X by its own n: ΔX_f = n_f · Δ(1/|RD′|). With date × hour effects
  in, the identifying variation is n_f × the line's state, within the hour.
- **The repo's X ignores the line.** In the offer curves the France flow (unit `MIEU`) appears
  only as accepted rows at a fixed quantity, priced at −500/−300 €/MWh (imports) or high bids
  (exports) (CLAUDE.md, "offered curves do not re-clear"). So |RD′| never includes French
  supply, and X is overstated whenever the line is open. That is why a probe found that
  interconnector capacity "barely moved X" (framework §9.3): the X it moved could not move.
- **The state switches often and for outside reasons** (§2): open in 23–40% of periods each
  year, both states on 80% of days, capacities set by the operators before the auction, and
  one large outside shock, France's 2022 nuclear crisis.
- **Theory.** The same first-order condition, p − c = β · n/|RD′|. In a coupled market a
  firm's residual demand includes foreign supply up to the line's spare room, so the slope it
  faces for small changes is |RD′| + S when the line is open (S, the slope French supply adds)
  and |RD′| when it is full in either direction.

## 2. What the data show (throwaway tabulation, 2026-10-20)

OMIE's interconnection file (`omie_interconnection_capacity.parquet`, border `FR`), "full" =
no free capacity left (≤ 1 MW) in that direction:

| year | open both ways | full, importing to Spain | full, exporting |
|---|---|---|---|
| 2018 | 24% | 63% | 13% |
| 2019 | 23% | 67% | 10% |
| 2020 | 39% | 41% | 20% |
| 2021 | 35% | 42% | 23% |
| 2022 | 27% | 10% | 63% |
| 2023 | 33% | 29% | 39% |
| 2024 | 32% | 40% | 28% |
| 2025 | 40% | 37% | 22% |

- **Both states occur on 80% of days**, so the switch is mostly within the day.
- **Capacity varies**: import 1,200–3,700 MW, export 1,000–3,600 MW (10th–90th percentiles
  within a year).
- **Mean Spanish price**: €76.0 open, €75.1 importing at full, €68.1 exporting at full. Open
  hours are not cheap or dear hours on average.
- **2022**: with many French reactors offline for corrosion checks, Spain exported at full in
  63% of periods.

## 3. The design

### 3.1 The line's state

Per date and period, from OMIE's file: **open** (free capacity in both directions),
**import-full**, **export-full**. Checked against prices: when the line is open, the Spanish
and French day-ahead prices should be equal (Ember's hourly prices); when full, they differ.

### 3.2 The predicted state

P̂_open,t (and P̂_import-full, P̂_export-full) from variables known before offers close and
outside the Iberian firms' control:
- the import and export capacity OMIE publishes for the period (set by the operators before
  the auction; the occupation is an outcome and is not used);
- France's D-1 demand forecast (RTE `prevision_j1`);
- French nuclear output over D−8 … D−2, a proxy for availability known at the bid;
- month × hour.

**Iberian conditions are deliberately left out** of the prediction (REE's forecasts, gas), so
the instrument does not carry them. They enter the estimate as controls (§3.4). Fitted
leaving out the year predicted, so a year's own outcomes never shape its prediction.

### 3.3 The French slope and the corrected stake

X_f,t = n_f,t / (|RD′_f,t| + S · 1[open_t]), with |RD′_f,t| the repo's island slope.

**S is calibrated, not assumed**: the price response to REE's D-1 forecast of Iberian demand
net of wind and solar (ESIOS 1775 − 1777 − 1779), in predicted-congested against
predicted-open hours, with month × hour effects. If a GW of residual demand moves the price
by a in congested hours and by b in open ones, then (|RD′| + S)/|RD′| = a/b. S at half and
double as checks.

### 3.4 The instrument, the outcomes and the estimate

- **Instrument:** Z_f,t = Zb_f,t × P̂_open,t, with Zb the firm's at-cost stake on the island
  slope (`hcompcost` for hydro, `compcost` for thermal, as in the at-cost design). **Zb itself
  is a control**, so only the rotation identifies: how much the stake changes with the line's
  predicted state.
- **Controls:** Zb × REE's D-1 Iberian residual-demand forecast and Zb × the gas price, so
  Iberian conditions that move with the line cannot load on Z.
- **Outcomes** (as in the holiday design §3.4): storage hydro, the fixed-step read at the
  unit's expected running share minus λ*30s (2019-01 → 2025-09); thermal, the offer price at
  25% and 50% of the unit's offered volume minus `marginal_cost_bid_eur_mwh` (capped column in
  the gas-cap window). A unit's firm is its largest owner that day (`majority_group`).
- **Estimate:** y_u,t = β · X_f(u),t + γ · Zb + controls + date × hour + unit × month + e, X
  instrumented by Z. Errors clustered by date; by week as a check.
- **Read against the simulated price-takers** on the same rows and instrument, by the rule in
  `notes/rq-price-taking-simulation.md`. Their X needs the same correction.

### 3.5 The test

- **Price-taking** predicts the same response to Zb in open and congested hours; **Nash**
  predicts β = 1 on the corrected X. For a firm with an at-cost net position of 2 GW,
  |RD′| = 500 and S = 3,000 (a guess until §3.3), X is 4.0 €/MWh congested and 0.6 open:
  Nash predicts its offers 3.4 €/MWh higher in congested hours than in open ones.
- **By sign of n**: sellers' markups and buyers' markdowns (Endesa) separately.
- **Between models** (Duarte, Magnolfi, Sølvsten & Sullivan 2024, *Quantitative Economics*):
  a Rivers–Vuong test of price-taking against Nash with Z as instrument, beside the
  Anderson–Rubin set on β.
- **2022 separately**: the French nuclear crisis is the largest single shift in the line's
  state.

## 4. Steps, each with a stop rule (each run needs a yes first)

1. **Data and the predicted state.** Fetch Ember's hourly prices (France, Spain) and RTE's
   eco2mix (national, consolidated), 2018-01 → 2026-05. Build §3.1 and check it against the
   price gap. Fit §3.2 leaving each year out. *Stop* if the predictors are weak: F below 20 on
   the excluded predictors for the open state (clustered by date), or an out-of-sample
   correlation between P̂_open and the state below 0.3.
2. **The slope and the first stage.** Calibrate S (§3.3); corrected X; first stage of X on Z
   with the controls and effects of §3.4; power. *Stop* if F is below 20 or the minimum
   detectable β at 80% power exceeds 1 (2.80 × se under β = 0, from the outcome's noise only).
3. **Main estimate.** §3.4–3.5, hydro and thermal; by sign; Rivers–Vuong.
4. **Checks** (§5).

## 5. Threats and checks

- **Firms can fill the line themselves**: withholding raises the Iberian price and can congest
  the line. Hence the prediction from French conditions and published capacity only.
- **French conditions move the Iberian price for everyone**: the date × hour effects absorb
  that. The exclusion needed is narrower: French conditions must not change a firm's offers
  in proportion to its stake except through the slope.
- **The gas crisis coincided with the French nuclear crisis** in 2022, and firms differ in gas
  exposure. Zb × gas is a control; run without 2022 too.
- **A barely open line**: with 50 MW free, French supply covers only small deviations. Check
  with "open" requiring 300 MW free.
- **Spain–Portugal splits**: split hours are dropped, as in the step caches.
- **Direction**: both full states make Iberia an island for small changes; check import-full
  and export-full separately against open.
- **The 15-minute day-ahead from 2025-10-01**: the step caches end 2025-09, and so does the
  sample.

## 6. Data

| what | source | status |
|---|---|---|
| Line capacity and state, by period | OMIE `capacidad_inter_pbc` (`omie_interconnection_capacity.parquet`) | on disk |
| French and Spanish day-ahead prices, hourly | Ember, *European wholesale electricity price data* (hourly zip, 42 MB; from ENTSO-E; CC BY 4.0) | to fetch |
| French nuclear output, D-1 demand forecast, exchanges with Spain | RTE eco2mix, national consolidated (`eco2mix-national-cons-def` on ODRÉ, 2012-01 → 2026-08, half-hourly, UTC) | to fetch |
| REE's D-1 Iberian forecasts | ESIOS 1775, 1777, 1779 | on disk (from 2019) |
| Offers, at-cost stakes, slopes, costs, price-taker seeds | bids, step caches (`hcompcost`, `compcost`), `firm_x`, `hydro_cost_daily`, `implied_marginal_cost_daily` | on disk |
| French nuclear availability declared | EDF/RTE (REMIT) or ENTSO-E (token pending) | optional check on the output proxy |

## 7. Goals and limits

- **Goal:** β from a rotation instrument, both sides of n.
- **By-product, not a goal here:** the corrected X, which every earlier design could reuse.
- **Not a goal:** market power in France, or the French slope as a structural object (S is
  calibrated).
- **Limit:** β's scale rests on S. The reduced form (does the response to the at-cost stake
  differ between predicted-open and predicted-congested hours?) does not, and is reported
  first.
- **Limit:** French nuclear output is a proxy for availability; it also responds to prices
  (modulation), which a lag of two days or more weakens but does not remove.

## 8. Left to the builder

- "Full" (my call: ≤ 1 MW free; 50 MW as a check).
- The prediction model (my call: one logit per state, the §3.2 variables, leave-one-year-out;
  changed in step 1 to one multinomial logit over the three states, since open is the middle
  state and a logit per state missed it).
- Clocks: OMIE is Madrid time, RTE's `date_heure` is UTC, Ember carries both; join on UTC.
- Clustering: by date as the main, by week as a check.
