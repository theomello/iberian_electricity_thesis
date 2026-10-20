# The France link, step 1: French data, the line's state and its prediction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** French day-ahead prices and RTE's French system data on disk; each hour's France-line state (open, import-full, export-full) checked against the price gap; the state predicted from published capacity and French conditions, each year left out of its own fit; the spec's step 1 stop rule.

**Architecture:** Two fetchers (Ember's hourly prices; RTE's eco2mix through ODRÉ's export API). One builder that joins OMIE's interconnection file, the prices and RTE's data on UTC hours and fits one logit per state leaving each year out. One analysis script for the stop rule.

**Tech Stack:** Python 3.14 `.venv`, pandas, numpy, pyarrow, requests, statsmodels (Logit; on disk).

**Spec:** `docs/specs/2026-10-20-france-link-design.md` §2, §3.1–3.2, §4 step 1, §8.

## Global Constraints

- Spec §3.1: "Per date and period, from OMIE's file: open (free capacity in both directions), import-full, export-full. Checked against prices: when the line is open, the Spanish and French day-ahead prices should be equal". §8: "Full" = ≤ 1 MW free.
- Spec §3.2 predictors: the period's published import and export capacity; RTE `prevision_j1`; French nuclear output over D−8 … D−2; month × hour. "Iberian conditions are deliberately left out." "Fitted leaving out the year predicted."
- Spec §4 step 1 stop: F below 20 on the excluded predictors for the open state (clustered by date), or out-of-sample correlation between P̂_open and the state below 0.3.
- **Window 2018-01-01 → 2025-09-30, hourly.** The step caches (the estimation sample) end 2025-09; from 2025-10-01 the day-ahead is quarter-hourly. Fetch RTE and Ember to 2026-05 anyway.
- Clocks: OMIE (date, period) is Madrid time; map it to UTC through `omie_day_ahead_prices.parquet` (`utc_timestamp`); RTE `date_heure` is UTC; Ember carries UTC.
- Month × hour in the logit enters as month + hour dummies (additive; 36 columns, not 288) — my call, recorded as a ruling; the F test uses month × hour cells.
- Ask before committing; ask before step 2.

## Review Focus

1. **The clock join**: RTE half-hours and Ember hours in UTC against OMIE's local periods, DST days included. Pinned in Task 3: Ember's Spanish price equals OMIE's on ≥ 99% of hours.
2. **A year's own outcomes in its prediction**: pinned in Task 3 by a synthetic test (flip one year's labels; its predictions must not move).
3. **The nuclear proxy must be known at the bid**: D−8 … D−2 only. Pinned in Task 3: the proxy for date d equals the mean daily nuclear output of d−8 … d−2 on a sampled day.
4. **Sign of the France–Spain exchange** in RTE: checked against OMIE's occupation, not assumed. Task 2.
5. **Periods with 23/25 hours** (DST): kept; UTC handles them.

---

### Task 1: Ember's hourly prices

**Files:** create `scripts/fetch/fetch_ember_prices.py`, `scripts/qa/check_ember_prices.py`.

**Interfaces:** produces `data/ember/ember_prices_hourly.parquet`: `country` (ISO3), `utc` (datetime64[ns, UTC]), `price_eur_mwh`; countries ESP, FRA, PRT; the raw zip kept in `data/ember/raw/`. Source: `https://files.ember-energy.org/public-downloads/price/outputs/european_wholesale_electricity_price_data_hourly.zip` (CC BY 4.0).

- [ ] Write `check_ember_prices.py`: ESP's price equals OMIE's `price_es` at the same UTC hour within €0.01 on ≥ 99% of hours 2018-01-01 → 2025-09-30; FRA has a price in ≥ 99.9% of those hours; no duplicate (country, utc).
- [ ] Run → fails (no file). Implement; fetch. Run → passes.

### Task 2: RTE eco2mix

**Files:** create `scripts/fetch/fetch_rte_eco2mix.py`, `scripts/qa/check_rte_eco2mix.py`.

**Interfaces:** produces `data/rte/eco2mix_national.parquet`, hourly UTC means of the half-hourly (or quarter-hourly) rows: `utc`, `consommation`, `prevision_j1`, `nucleaire`, `eolien`, `solaire`, `ech_comm_espagne` (MW). Source: ODRÉ `eco2mix-national-cons-def` export (`/api/explore/v2.1/catalog/datasets/eco2mix-national-cons-def/exports/parquet`, or csv), rows from 2017-12-01; raw export kept in `data/rte/raw/`.

- [ ] Write `check_rte_eco2mix.py`: ≥ 99.9% of UTC hours 2018-01-01 → 2025-09-30 present; `nucleaire` within 10–65 GW on every hour; corr(`prevision_j1`, `consommation`) > 0.95; |corr(`ech_comm_espagne`, OMIE FR net flow)| > 0.8, the sign printed (OMIE net flow = export_occupied + import_occupied, imports negative as published).
- [ ] Run → fails. Implement; fetch. Run → passes.

### Task 3: The line's state and its prediction

**Files:** create `scripts/build/build_france_link.py`, `scripts/qa/check_france_link.py`.

**Interfaces:**
- `fit_loyo(df: pd.DataFrame, y: str, xs: list[str], year_col: str = "year") -> pd.Series`: for each year, a statsmodels Logit of `y` on `xs` + month + hour dummies fitted on the other years, predicting that year.
- Produces `outputs/tables/france_link_hours.parquet`, one row per OMIE (date, period) 2018-01-01 → 2025-09-30: `date, period, utc, year, month, hour, cap_imp, cap_exp, free_imp, free_exp, state` (`open`/`import_full`/`export_full`), `price_es, price_fr, gap` (ES − FR), `fr_load_fc` (RTE `prevision_j1`, MW), `fr_nuc_lag` (mean daily `nucleaire`, D−8 … D−2, MW), `p_open, p_import_full, p_export_full`.
- `cap_imp` is the import capacity as a positive MW.

- [ ] Write `check_france_link.py`: (a) `fit_loyo` on synthetic data (two years, y = 1[x > 0]) predicts each year well (corr > 0.8), and flipping year 2's labels leaves year 2's predictions unchanged to 1e-9; (b) the file: every row has one state; open periods have |gap| ≤ €0.01 on ≥ 90%, full periods |gap| > €0.01 on ≥ 90% (shares printed); `fr_nuc_lag` on 2022-07-15 equals the mean of RTE's daily nuclear on 2022-07-07 … 2022-07-13 (±1 MW); p's in [0, 1].
- [ ] Run → fails. Implement; build. Run → passes.

### Task 4: The stop rule

**Files:** create `scripts/analysis/france_link_predict.py`.

**Interfaces:** writes `outputs/tables/france_link_predict.csv` (`sample, n, F_excluded, corr_oos, auc_oos` for the open state; and the same for the two full states).

- Linear probability model of `open` on `cap_imp, cap_exp, fr_load_fc, fr_nuc_lag`, demeaned within month × hour cells, errors clustered by date; F = Wald / 4.
- Out of sample: corr(`p_open`, open) and the area under the ROC curve, pooled and by year.
- Samples: 2018-01 → 2025-09 and the estimation window 2019-01 → 2025-09.
- Prints the stop rule.

- [ ] Run; read against the stop rule.

### Task 5: Write-up

- [ ] `notes/rq-france-link.md`; spec status line; `CLAUDE.md` (two fetcher rows, the build row, a short section on Ember and RTE); memory entry.
- [ ] Ask before committing and before step 2.
