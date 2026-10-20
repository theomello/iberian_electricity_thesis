# Regional holidays, step 2: the dose, the first stage and the power — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn step 1's exposures into each firm's holiday dose by day and hour, show whether it moves the firm's stake (first stage), and compute the smallest β (and Endesa's β⁻) the design could detect, without reading the outcome's response to the dose.

**Architecture:** One analysis script with three modes. `--dose` writes the dose (group × date × local hour). `--first-stage` regresses the stake on the dose at firm level (hydro owners' at-cost stake from `hcompcost`; the five firms' actual stake from `firm_x`) and at unit level (the fixed-step rows; the thermal offer panel). `--power` takes the outcome's residuals from the fixed-effects-only regression (no dose in it), so the reduced form's standard error is computed under β = 0, and divides by the first stage.

**Tech Stack:** Python 3.14 `.venv`, pandas, numpy; `step_estimator.wdemean`, `midday_hydro_iv.cluster_meat`, `fixed_step_test.load_rows`/`stake_parts`, `build_holiday_exposure.design`.

**Spec:** `docs/specs/2026-10-20-regional-holidays-design.md` §3.2–3.5, §4 step 2; step 1 results `notes/rq-regional-holidays.md`.

## Global Constraints

- Spec §3.2 as amended by step 1: dose = (Σ local areas e_fr·H + e_f,ES·(share of mainland demand off) + e_f,PT·H_PT) × p_h, exposures leaving the day's year out (`holiday_exposure_loyo.csv`).
- Spec: "p_h, the hourly profile of a holiday's demand drop, from national demand (`ree_realtime_5min`) on national holidays against the same weekday ±1 week. My call: one profile for all regions." Normalised to mean 1, so a day's mean dose is its daily exposure.
- Spec §3.3: "The firm's net position n … at the cost point, from `hcompcost`, `kb_sn` … and its stake X = n / |RD′|, on dose and dose / |RD′|, with firm × month and date × hour effects."
- Spec §4 step 2: "Stop if the firm-level F on the dose is below 20, or if the minimum detectable β⁻ at 80% power exceeds 1."
- Spec §8: "Clustering: by date (the event), as the main; by week as a check." The stop rule uses the larger of the two standard errors.
- MDE at 80% power, 5% two-sided: 2.80 × SE(β), SE(β) = SE(reduced form under β = 0) / |first-stage coefficient|.
- Ask before committing; ask before step 3.

## Review Focus

1. **A dose on a day the exposures were estimated from**: leave-one-year-out must use e from the run that left the day's year out. Pinned in Task 1's check (Diada 2024 uses year_out 2024).
2. **Merged area names differ across leave-out runs** ("AS+EX" in one, absent in another): the dose must read each run's own names. Pinned in Task 1's check (an AS+EX day).
3. **Hours**: the fixed-step `period` is the local period (1..23/25 on DST days); the thermal panel's `hour`. Map both to the profile's local hour 0–23. Pinned by the check that p_h has 24 values and the dose's daily mean equals the exposure.
4. **The outcome must not be read against the dose in this step**: power uses residuals from regressions without the dose. Pinned by construction (`--power` never fits y on the dose).

---

### Task 1: The dose

**Files:** create `scripts/analysis/holiday_first_stage.py` (mode `--dose`), `scripts/qa/check_holiday_dose.py`.

**Interfaces:** produces `outputs/tables/holiday_dose.parquet`: `group`, `date`, `hour` (0–23 local), `dose_mw`; and `outputs/tables/holiday_profile.csv`: `hour`, `p_h`.

- [ ] Write `check_holiday_dose.py`: p_h has 24 positive values with mean 1; ENDESA's mean dose over 2024-09-11 equals its `CT` exposure in the run leaving out 2024 (±0.5 MW); ENDESA on 2023-10-12 (Spain-only national day, all mainland off) equals its `ES` exposure leaving out 2023 (±0.5); EDP on 2024-04-25 equals its `PT` exposure leaving out 2024; every group's dose is 0 on 2024-09-18 (a clean Wednesday) and on 2024-12-25 (market-wide); on 2019-09-09 (8 Sep Sunday moved? check) — an AS+EX local day — ENDESA's dose equals its `AS+EX` exposure leaving out that year if that run has the name, else 0.
- [ ] Run it → fails (no file). Implement `--dose`. Run → passes.

### Task 2: First stage and power

**Files:** extend `scripts/analysis/holiday_first_stage.py` (modes `--first-stage`, `--power`); `scripts/qa/check_holiday_first_stage.py`.

**Interfaces:** `iv_se(y, x, z, codes, clusters) -> dict` (first-stage b, se, F; reduced-form se under β = 0; se(β); MDE); writes `outputs/tables/holiday_first_stage.csv`, `outputs/tables/holiday_power.csv`.

Samples and specifications:
- **Firm level, hydro owners, at cost**: one row per group × hour from `hcompcost` (`kb_sn`, `kb_s` over NEAR, Zb as `fixed_step_test.build_month`), 2019-01 → 2025-09. n (GW) on dose (GW); Zb on P = dose / slope. Group × month and hour effects.
- **Firm level, five firms, actual**: `firm_x` (`net_mw`, `slope_net`, `X`), clean rows, 2018-01 → 2026-05. Same.
- **Unit level, hydro**: the fixed-step main sample (`load_rows`, Zb defined, rel ≥ 0.9). Zb on P; unit × month and class × hour effects. Outcome for power: `g_p_cf`.
- **Unit level, thermal**: `outage_offer_panel`, gas and coal rows with `c_bid` and X; X on dose (GW); unit × week and class × date × hour effects. Outcome for power: `o25 − c_bid`.
- Endesa alone: the dose and the stake interacted with an Endesa indicator, other firms' terms in the same regression.

- [ ] Write `check_holiday_first_stage.py`: on synthetic data with a planted first stage (π = 1) and β = 0.5, `iv_se` returns a first-stage coefficient within 3 se of 1, a reduced-form se within 20% of the empirical sd over 200 draws, and MDE = 2.80 × se(β).
- [ ] Run → fails. Implement. Run → passes.
- [ ] Run `--first-stage` and `--power`; logs to `.superpowers/sdd/2026-10-20-regional-holidays-step2/`.

### Task 3: Write-up

- [ ] `notes/rq-regional-holidays.md` step 2 section: first-stage table, power table, the stop rule's verdict.
- [ ] Ask before committing and before step 3.
