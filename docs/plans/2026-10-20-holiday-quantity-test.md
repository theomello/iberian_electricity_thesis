# The holiday quantity test — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test whether the generation firms cut on their customers' holidays follows the dose's price effect (P = dose/|RD′|, market power) or the dose itself (Z, book balancing), with β on the quantity margin and its interval.

**Architecture:** One script, `scripts/analysis/holiday_quantity_test.py`, with `--panel` (the hourly firm panel: PDBF legs, dose, slope, own offer slope s → `outputs/tables/holiday_quantity_panel.parquet`, gitignored) and `--test` (step 1's checks and stop rule, then step 2's regressions → `outputs/tables/holiday_quantity_test.csv`). Regressions with `wdemean` and `cluster_meat` as elsewhere.

**Tech Stack:** Python 3.14 `.venv`, pandas, numpy; `step_estimator.wdemean`, `midday_hydro_iv.cluster_meat`, `lib/unit_ownership`, step caches.

**Spec:** `docs/specs/2026-10-20-holiday-quantity-test-design.md`.

## Global Constraints

- Spec §2: five firms, weekdays, 2019-01 → 2025-09; outcomes PDBF generation (auction, bilateral, sum) and retail purchases (auction, bilateral), MW signed (sold +); Z = dose GW; P = 1000 Z / |RD′| (`firm_x.slope_net`, slope ≥ FLOOR = 20); control 1/|RD′|; date × hour and firm × month effects; date clusters, week as a check.
- Spec §2: s = the firm's own sell offers within ±€5 of the hour's price per €/MWh (step cache `own`, `hours.p_star`); s̄ = dose-weighted mean of s.
- Spec §3 step 1 stop: generation (sum) on Z with |t| < 2, or se(b_P) > s̄ / 2.8.
- Predictions fixed in spec §2 (book balancing: b_P = 0; Nash: b_P = −s̄).
- Run step 2 only if step 1 says CONTINUE; ask before committing.

## Review Focus

1. **Hour alignment**: PDBF (date, period) local; quarter-hourly from 2025-03-19 → mean of the four quarters per hour; DST days dropped (the step caches have none). Pinned by Task 1's check: the hourly panel's daily means reproduce step 2's daily legs.
2. **Sign conventions**: sold +, bought − as in `holiday_schedule_legs.py`; retail purchases rise toward 0 on a holiday (less bought). Pinned by the first stage's sign (retail legs on Z positive).
3. **s near the price, not the whole curve**: within ±€5 of p*. Pinned by a check that s is positive and below the firm's offered sell MW / 10.

---

### Task 1: The hourly panel and step 1

**Files:** create `scripts/analysis/holiday_quantity_test.py` (`--panel`, `--test --step 1`), `scripts/qa/check_holiday_quantity.py`.

- [ ] Check (on the panel): daily means of the hourly legs, regressed as in `holiday_schedule_legs.py` (deltas against the reference days, date and firm × year effects), give generation bilateral within 2 se of −0.54 and retail bilateral within 2 se of +0.69; s > 0 on ≥ 95% of rows and s ≤ offered sell MW / 10; P = 1000 Z / slope exactly.
- [ ] Run → fails. Implement `--panel`. Run → passes.
- [ ] Run `--test --step 1`: first stage (retail legs on Z), generation on Z, se(b_P) against s̄ / 2.8; print the stop rule.

### Task 2: The slope test (only if step 1 continues)

- [ ] `--test --step 2`: §2's regression for each outcome, pooled and for Endesa and Iberdrola; β = −b_P / s̄ with its interval; the checks of spec §4 (at-cost slope, flat profile, adjacent days out, national vs regional days, COVID out).

### Task 3: Write-up

- [ ] `notes/rq-regional-holidays.md` (a quantity-test section), spec status, memory. Ask before committing.
