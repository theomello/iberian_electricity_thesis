# Minimum-income near-misses, step 1: the running variable and what withdrawn plants do — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** For every unit-day declaring a minimum-income condition, the margin it would have earned had it run (r_A); whether acceptance, the density and pre-set covariates are continuous at r_A = 0; and what happens to plants just withdrawn (REE's grid-security schedule, intraday sales, idle). Ends with the spec's step 1 stop rule.

**Architecture:** A fetcher for OMIE's `pdvd`. A small regression-discontinuity library (`lib/rd.py`: local linear jump, McCrary density test). A builder that computes r, r_A and acceptance per unit-day, re-clearing hours on the step cache's effective curve with the withdrawn unit's offers added. An analysis script that reads the builder's file, adds covariates and each near-miss plant's fate, runs the checks and prints the stop rule.

**Tech Stack:** Python 3.14 `.venv`, pandas, numpy, pyarrow; `lib/omie_common` (`omie_url`, `month_may_grow`), `lib/unit_ownership.majority_group`, the step cache (`outputs/cache/step/hours_*`, `market_*`, from `analysis/step_curves.py`).

**Spec:** `docs/specs/2026-10-20-mic-near-miss-design.md` §2, §3.1–3.2, §4 step 1, §8.

## Global Constraints

- Spec §2 rule 1: "Count a plant as accepted only if it clears in at least 4 hours."
- Spec §3.1: r = (Σ_h p_h q_h − F) / Σ_h q_h − v, q_h the unit's offered sell MW at or below the hour's price (Portuguese price for Portuguese units); r_A the same "at the prices that would clear with the unit's offers in"; accepted units r_A = r; "Other units with a condition keep their status."
- Spec §8: hours where the effective curve misses the published price by more than €0.50, and split hours, are left out of the re-clearing; "flag the day if more than four are left out".
- Spec §4 step 1 stop: accepted-share jump below 0.5; density test rejects at 1%; two or more covariates jump at 1%; fewer than 1,000 single-unit firm-days within €2 in 2019-01-01 → 2024-06-13.
- RD: local linear each side, triangular kernel, bandwidth €2/MWh, errors clustered by date (spec §3.4).
- **Window 2019-01-01 → 2025-03-18, not 2018**: the step cache (the re-clearing curves) starts 2019-01, and so do REE's D-1 forecasts used as covariates. 2018 joins in step 5 (spec §4 step 5). DST days are left out (the step cache has none).
- The shift, not the re-cleared level: p^A_h = p*_h + (p_clear'_h − p_clear_h), so the re-clearing error on the published price cancels.
- No outcome (intraday offers of other units) is read in this step.
- Ask before committing; ask before step 2.

## Review Focus

1. **Portuguese units on split hours** must earn the Portuguese price: a wrong price makes accepted units look like they missed. Pinned in Task 3: among accepted unit-days, r ≥ −0.5 for at least 98% of Spanish and of Portuguese units separately.
2. **The scheduled stop** (1–3 hours cleared) must count as withdrawn. Pinned in Task 4: share accepted in r_A ∈ [−2, 0) below 2%.
3. **r_A can only be lower than r for a withdrawn unit** (adding supply cannot raise the price). Pinned in Task 3.
4. **The `cab` layout change on 2025-03-19**: no row after 2025-03-18. Pinned in Task 3.
5. **PDVD's layout differs from PDBF's** (seven fields, no unit id or group tag). Pinned in Task 1 by the example plants.

---

### Task 1: Fetch PDVD

**Files:** create `scripts/fetch/fetch_omie_pdvd.py`, `scripts/qa/check_pdvd.py`.

**Interfaces:** produces `data/omie/pdvd/parquet/pdvd_YYYYMM.parquet`: `date` (date), `period` (int8), `resolution_min` (int8, from the day's period count as in `fetch_omie_pdbf.py`), `unit` (str), `schedule_mw` (float32, average MW as published), `role_code` (str). Months 2019-01 → 2025-03 by default; `--month YYYYMM`; resumable; zips deleted once parsed, as PDBF.

Format (checked on `pdvd_20190103.1`): header line `PDVD;`, then `year;month;day;period;unit;MW;role_code;`, latin-1, dot decimal.

- [ ] Write `check_pdvd.py`: on 2019-01-03, `SAGU1` has 24 rows, role 1, mean 51.67 ± 0.05 MW, max 155; `SROQ1` mean 235.63 ± 0.05; every 2019-01 day has 24 periods except none (January has no DST); no duplicate (date, period, unit, role_code).
- [ ] Run → fails (no file). Implement. Fetch 2019-01 → 2025-03. Run → passes.

### Task 2: RD tools

**Files:** create `scripts/lib/rd.py`, `scripts/qa/check_rd.py`.

**Interfaces:**
- `rd_jump(y, r, cluster, h=2.0) -> dict` with `tau, se, p, n_left, n_right`: weighted least squares of y on [1, r, D, D·r], D = 1[r ≥ 0], weights 1 − |r|/h within |r| < h; tau = coefficient on D; cluster-robust se.
- `mccrary(r, h=2.0, b=0.05) -> dict` with `theta, se, z, p, n`: McCrary (2008): bin r in width b, local linear on bin heights each side with the triangular kernel, theta = log f₊ − log f₋, se = sqrt((1/(n h))·(24/5)·(1/f₊ + 1/f₋)).

- [ ] Write `check_rd.py`, synthetic, fixed seed: (a) y = 1 + 0.5r + 2·D + N(0,1), 20,000 draws, 2,000 clusters → |tau − 2| < 3 se and p < 0.001; (b) y = D exactly → tau = 1, se < 1e-6; (c) r uniform on [−3, 3] with 1.5× the density right of 0, n = 20,000 → |theta − ln 1.5| < 3 se, p < 0.01; (d) r uniform, no break → p > 0.01.
- [ ] Run → fails. Implement. Run → passes.

### Task 3: The running variable

**Files:** create `scripts/build/build_mic_running.py`, `scripts/qa/check_mic_running.py`.

**Interfaces:**
- `shift_price(prices: np.ndarray, a: np.ndarray, d_tot: float, add_p: np.ndarray, add_mw: np.ndarray) -> float`: one hour's market table (unique prices ascending, cumulative effective MW `a`), plus a unit's added steps; the lowest price on the union grid where a + added MW at or below it − d_tot ≥ 0.
- Produces `outputs/tables/mic_running.parquet`, one row per declaring sell unit-day: `date, unit, country, group, F, v, cap_mw, q_mwh, rev, r, hours_cleared, accepted, r_A, n_hours, n_left_out, flag, dp_mean`. `group` from `majority_group`; `n_left_out` hours left out of the re-clearing; `flag` = n_left_out > 4; `dp_mean` the mean price shift over the unit's hours.

Rules:
- Declaring: `cab`, side V, F > 0 or v > 0, one row per (date, unit).
- q_h, rev: status O sell steps at or below the hour's country price; accepted = status C sell MW > 0 in ≥ 4 periods.
- Re-clear only withdrawn unit-days with r ≥ −5 (r_A ≤ r, so the others stay outside any bandwidth); for them, the steps added in hour h are the unit's O steps priced below p*_h (those above are already in the effective curve). Other withdrawn unit-days: r_A = r, `far` = True (add the column).
- Hours not `valid` in `hours_YYYYMM` keep p*_h and count in `n_left_out`.

- [ ] Write `check_mic_running.py`: `shift_price` on prices [0,10,20,30], a [100,200,300,400], d_tot 300 → 20 with nothing added, 20 with 50 MW at 5, 10 with 100 MW at 5; `SAGU1` 2019-01-03 withdrawn, r = −0.058 ± 0.01, r_A ≤ r; `SROQ1` 2019-01-03 accepted, 20 hours cleared, r_A = r = 0.226 ± 0.01; r_A ≤ r + 1e-9 for every withdrawn row; r_A = r for every accepted row; no date after 2025-03-18; accepted rows: r ≥ −0.5 in ≥ 98% for country ES and for PT separately.
- [ ] Run → fails. Implement. Build. Run → passes. Log to `.superpowers/sdd/2026-10-20-mic-near-miss-step1/`.

### Task 4: The checks and the fate of near-miss plants

**Files:** create `scripts/analysis/mic_near_miss_describe.py`.

**Interfaces:** reads `mic_running.parquet`; writes `outputs/tables/mic_near_miss_rd.csv` (`check, tau, se, p, n_left, n_right`), `outputs/tables/mic_near_miss_fate.csv` (`side, year, group, n, pdvd_share, pdvd_mw, id_share, id_mw, idle_share`).

- **Sample**: rows not `flag`, |r_A| < 2 for the RD and fate, 2019-01-01 → 2025-03-18; the count of single-unit firm-days (exactly one unit within €2 for the group that day) also within 2019-01-01 → 2024-06-13.
- **Checks** (each `rd_jump`, cluster date): `accepted`; covariates v, F, D's mean D-1 forecast of demand, wind and solar (ESIOS 1775/1777/1779, local date of `datetime`), MIBGAS Spanish index at D−2, `ran_prev` (the unit's PDBF schedule > 0 in ≥ 4 periods on D−1), `weekend`; `mccrary` on r_A.
- **Fate**, per near-miss unit-day: `pdvd_mw` mean PDVD schedule over the day (all roles); `id_mw` the unit's net intraday cleared MW (status C, sell − buy, all sessions) averaged over the day's periods; REE-scheduled if pdvd_mw > 1, sold intraday if id_mw > 1, idle if neither; by side (withdrawn r_A < 0, accepted r_A ≥ 0), year and group (the four large firms, others pooled).
- Prints each stop condition and STOP/CONTINUE.

- [ ] Run; read the output against the stop rule. (No new unit test: the estimators are pinned in Task 2, the inputs in Tasks 1 and 3.)

### Task 5: Write-up

- [ ] `notes/rq-mic-near-miss.md`: the running variable, the checks table, the fate table, the verdict. Spec status line. `CLAUDE.md`: the PDVD fetcher row and a short PDVD paragraph. Memory entry.
- [ ] Ask before committing and before step 2.
