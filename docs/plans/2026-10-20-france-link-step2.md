# The France link, step 2: the French slope, the corrected stake, the first stage and the power — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Calibrate S, the slope French supply adds while the line is open; build each firm's corrected at-cost stake Zb_c = n / (|RD′| + S · open); show whether the instrument Zb × z_open moves it (first stage) given the controls; compute the smallest β the design could detect, without reading the outcome's response to the instrument.

**Architecture:** One analysis script, `scripts/analysis/france_link_first_stage.py`, with modes `--calibrate` and `--first-stage` (which also does the power). It reuses `holiday_first_stage.py`'s samples' construction and the step caches; a new `iv_ctrl` partials the controls out after the fixed effects, then does what `iv_null` does.

**Tech Stack:** Python 3.14 `.venv`, pandas, numpy; `step_estimator.wdemean`, `midday_hydro_iv.cluster_meat`, `fixed_step_test.load_rows`/`stake_parts`, `step_engine.NEAR`, `step_estimator_hydro.FLOOR`.

**Spec:** `docs/specs/2026-10-20-france-link-design.md` §3.3–3.4, §4 step 2; step 1 and the split in `notes/rq-france-link.md` (§1.5, §1.7).

## Global Constraints

- Spec §3.3: "X_f,t = n_f,t / (|RD′_f,t| + S · 1[open_t]) … S is calibrated, not assumed: the price response to REE's D-1 forecast of Iberian demand net of wind and solar … in predicted-congested against predicted-open hours … (|RD′| + S)/|RD′| = a/b. S at half and double as checks."
- The instrument after the split (note §1.7): Z = Zb × z_open; controls Zb, Zb × p_open_ib, Zb × REE's D-1 Iberian residual-demand forecast, Zb × the gas price known at the bid (MIBGAS, D−2).
- Zb: the at-cost stake on the island slope, n_gw · 1000 / slope from `hcompcost` (hydro) and `compcost` (thermal, 2019-01 → 2023-12), as in `fixed_step_test.stake_parts`; slope ≥ `FLOOR`.
- Samples (as in the holiday step 2): firm, hydro at cost (`hcompcost`, group × month and hour effects); unit, hydro (the fixed-step main sample, unit × month and class × hour effects; outcome `g_p_cf`); unit, thermal (gas and coal in `outage_offer_panel` with `compcost`, unit × week and class × date × hour effects; outcome o25 − c_bid). 2019-01 → 2025-09 (thermal to 2023-12).
- Clusters by date (main) and week.
- MDE at 80% power, 5% two-sided: 2.80 × se(β) under β = 0, se(β) = se(reduced form under the null) / |first stage|, the outcome never fitted on the instrument.
- **Stop rule, fixed before the run:** STOP if the pooled first-stage F (the smaller of date and week) is below 20 on both unit-level samples, or if the pooled minimum detectable β (the larger of date and week) exceeds 1 on both outcomes. Otherwise CONTINUE, on the samples that pass.
- Ask before committing; ask before step 3.

## Review Focus

1. **The controls must be partialled out of x, z and y alike**, after the fixed effects. Pinned by Task 2's synthetic check (a control correlated with z).
2. **Joins on the hour**: the step caches' `hid` against `france_link_hours` (date, period); DST days are not in the caches. Pinned by Task 2: every sample row finds its hour, or the share lost is printed and below 1%.
3. **S must come out positive**: a ≤ b would make the correction meaningless. Task 1 stops with a message if so.
4. **The outcome is not read against the instrument**: power uses the residual of y on the fixed effects and controls only.

---

### Task 1: Calibrate S

**Files:** create `scripts/analysis/france_link_first_stage.py` (mode `--calibrate`), `scripts/qa/check_france_link_first_stage.py`.

**Interfaces:**
- `calibrate(d: pd.DataFrame, p: str = "p_open_full") -> dict`: price on RDf, RDf × p, p, with date and month × hour effects (`wdemean`), date clusters; returns `a` (€/MWh per GW at p = 0), `b` (at p = 1), their se, `ratio` a/b.
- Writes `outputs/tables/france_link_slope.csv`: a, b, ratio, the median island slope (MW per €/MWh, over the hours' effective-curve slope within ±€5 of the price, step cache `market`), S = slope × (ratio − 1), and S/2, 2S.

- [ ] Check (synthetic): price = α_d + 3·RDf·(1 − p) + 1·RDf·p + noise → ratio within 3 se of 3.
- [ ] Run → fails. Implement. Run → passes. Run `--calibrate`.

### Task 2: First stage and power

**Files:** extend `france_link_first_stage.py` (mode `--first-stage`); extend the check.

**Interfaces:** `iv_ctrl(df, xs, zs, controls, codes, clusters, y=None) -> list[dict]`: as `holiday_first_stage.iv_null`, with `controls` partialled out of every column after the fixed effects. Writes `outputs/tables/france_link_first_stage.csv` (sample, x, z, pi, F_date, F_week, mde_date, mde_week, n) for S, S/2 and 2S.

- [ ] Check (synthetic): x = 1·z + 2·w + e, z correlated with the control w → pi within 3 se of 1; y = 0·x + w + u → se(β) under the null within 20% of the empirical sd over 150 draws.
- [ ] Run → fails. Implement. Run → passes. Run `--first-stage`; logs to `.superpowers/sdd/2026-10-20-france-link-step2/`.

### Task 3: Write-up

- [ ] `notes/rq-france-link.md` step 2 section; spec status; memory.
- [ ] Ask before committing and before step 3.
