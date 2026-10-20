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
which the spec kept out of the prediction on purpose. Adding it with a split (§1.7) brings the
correlation to 0.299: still a stop, by 0.001, while the French part is strongly related to the
open state given the Iberian part (F 621).

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

### 1.7 The split (run 2026-10-20): misses the bar by 0.001

Plan Task 6. REE's D-1 forecasts of peninsular demand, wind and solar added to the multinomial
logit (2019-01 → 2025-09, each year left out of its own fit); the French predictors and capacity
then held at their calendar month's mean over the sample to get the Iberian-only part. **Stop
rule fixed before the run**: corr(p_open_full, open) ≥ 0.3 and F ≥ 20 for open on z_open given
p_open_ib (month × hour cells, date clusters).

| sample | corr, full prediction | corr, France only (§1.3) | F, French part given Iberian part | partial corr, French part |
|---|---|---|---|---|
| 2019-01 → 2025-09 | **0.299** | 0.203 | **621** | 0.256 |
| without 2022 | 0.341 | 0.232 | 888 | 0.303 |
| 2019 | 0.421 | 0.290 | 206 | 0.384 |
| 2020 | 0.333 | 0.233 | 172 | 0.303 |
| 2021 | 0.382 | 0.276 | 165 | 0.313 |
| 2022 | 0.092 | 0.037 | 36 | 0.164 |
| 2023 | 0.359 | 0.135 | 257 | 0.323 |
| 2024 | 0.307 | 0.195 | 65 | 0.208 |
| 2025 (to Sep) | 0.157 | 0.162 | 1.4 | 0.037 |

The French part varies as much as the Iberian part (sd 0.18 against 0.15).

**Stop rule: STOP**, by 0.001 on the correlation; the F passes by a factor of 30.

- **Adding the Iberian side helps as expected**: 0.20 → 0.30 pooled, and above 0.3 in five of
  seven years.
- **The French part is strongly related to the open state given the Iberian part** (F 621),
  which is what the instrument needs. The correlation bar asks how well the whole model
  predicts openness, a weaker proxy for the same thing.
- **2022 and 2025 are where it fails.** In 2022 the line was export-full most of the year
  (French nuclear crisis), which fits from other years do not foresee; without 2022 the pooled
  correlation is 0.34 and the F 888. 2025 (nine months) has almost no French part (F 1.4).
- **The direct test of strength is step 2's**: the first stage of the corrected stake X on
  Zb × z_open, F ≥ 20, and the minimum detectable β ≤ 1.

### 1.8 Rulings in this step

- One multinomial logit instead of a logit per state (§1.4).
- Window 2018-01-01 → 2025-09-30, hourly: the estimation sample ends 2025-09.
- Month + hour dummies in the logit (additive), month × hour cells in the F test.
- In the split, the French predictors and capacity are held at their calendar month's mean over
  the whole sample, not the year-month's, so the instrument keeps across-month French shifts
  such as 2022's.
