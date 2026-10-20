# The France link: running note

Spec: [`docs/specs/2026-10-20-france-link-design.md`](../docs/specs/2026-10-20-france-link-design.md).
Plan: `docs/plans/2026-10-20-france-link-step1.md`. Ledger and logs:
`.superpowers/sdd/2026-10-20-france-link-step1/`.

## Step 1 (2026-10-20): French data, the line's state, its prediction — STOP

**In one line.** The line's state is measured cleanly (open hours have equal Spanish and
French prices 99.7% of the time), and French conditions with the published capacity predict
*which way* the line will be full well (out-of-sample correlation about 0.5, AUC 0.8). But
they predict *whether it will be open* poorly: correlation 0.20 against the bar of 0.3, though
the predictors are strongly related to it (F 83). The open state needs the Iberian side too,
which the spec kept out of the prediction on purpose.

### 1.1 What was built

- `fetch/fetch_ember_prices.py` → `data/ember/ember_prices_hourly.parquet`: Ember's hourly
  day-ahead prices for Spain, France and Portugal, 2015-01-01 → 2026-10-07 (from ENTSO-E,
  CC BY 4.0). Spain's equals OMIE's `price_es` within €0.01 on **100%** of 67,919 hours.
- `fetch/fetch_rte_eco2mix.py` → `data/rte/eco2mix_national.parquet`: RTE's éCO2mix national
  consolidated data, hourly UTC means, 2017-12-01 → 2026-08-31: demand, its D-1 forecast
  (corr 0.994 with demand), nuclear (19–59 GW), wind, solar, the commercial exchange with Spain
  (corr +0.963 with OMIE's scheduled Spain→France flow: same sign).
- `build/build_france_link.py` → `outputs/tables/france_link_hours.parquet`: 67,919 hours,
  2018-01-01 → 2025-09-30, the state and its prediction.
- `analysis/france_link_predict.py` → `outputs/tables/france_link_predict.csv`.

### 1.2 The state is measured cleanly

Open (free room both ways): 31% of hours; import-full 41%; export-full 28% (both full: 6
hours, assigned by the flow's direction). **In open hours the Spanish and French prices are
equal on 99.7%; in full hours they differ on 99.8%.** So OMIE's occupation file and the price
gap say the same thing.

### 1.3 The prediction

One multinomial logit over the three states, on the capacity published for the period,
France's D-1 demand forecast, French nuclear output over D−8 … D−2, month and hour; each year
predicted from a fit on the others. Estimation window 2019-01 → 2025-09 (59,153 hours):

| state | share | F, excluded predictors | F, on the prediction | corr out of sample | AUC |
|---|---|---|---|---|---|
| open | 0.32 | 83 | 221 | **0.20** | 0.62 |
| import-full | 0.37 | 444 | 1,142 | 0.51 | 0.80 |
| export-full | 0.31 | 350 | 747 | 0.47 | 0.79 |

(F: linear probability model within month × hour cells, errors clustered by date.)

By year, the open state's correlation runs 0.25 (2018), 0.29 (2019), 0.23, 0.28, **0.04 (2022)**,
0.14, 0.20, 0.16 (2025). In 2022 the French nuclear crisis made the line export-full most of the
year, and a model fitted on the other years does not foresee it.

**Stop rule: STOP** (open: correlation 0.20 < 0.3; F 83 passes).

### 1.4 Why the open state is hard to predict from France alone

The line is full one way when France is clearly cheaper, full the other way when France is
clearly dearer, and open when the two prices are close. Which way France leans follows from
French demand and nuclear output, which is why the two full states are predicted well. Whether
the two prices end up close depends as much on the Iberian side (wind, solar, hydro, demand),
which the spec kept out so that the instrument would not carry Iberian conditions.

**A first try with one logit per state did worse** (open: 0.08), because a single linear
index cannot make the middle state likely; the multinomial logit can (0.21). Ruling in the
ledger.

### 1.5 A way to keep the Iberian side out of the instrument but in the prediction (not run)

Fit the prediction on French conditions, capacity *and* REE's D-1 Iberian forecasts (demand,
wind, solar). Then split the predicted open probability into:
- the part Iberian conditions alone give, with French conditions and capacity held at their
  month's means: a **control**, interacted with the at-cost stake Zb;
- the rest, what French conditions and capacity add given the Iberian side: the
  **instrument**, Zb × that part.

The model can then see that openness needs both sides to balance, while only the French and
capacity part identifies β. Step 1's checks would be rerun on that part.

### 1.6 Rulings in this step

- One multinomial logit instead of a logit per state (§1.4).
- Window 2018-01-01 → 2025-09-30, hourly: the estimation sample ends 2025-09.
- Month + hour dummies in the logit (additive), month × hour cells in the F test.
