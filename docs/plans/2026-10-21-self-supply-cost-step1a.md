# The cost of self-supply, step 1a — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Describe who supplies the five firms' own customers and at what margin (composition, above-cost self-supply, hydro timing), and check the power of step 1b's holiday € test, with the spec's stop rule.

**Architecture:** One script, `scripts/analysis/self_supply_cost.py`: `--build` reads PDBF month by month, keeps the five firms' generation unit-hours (same legs as `holiday_quantity_test.month_legs`), gives each unit a class and a daily cost, prices each unit-hour at its country's day-ahead price, and aggregates to group × date × hour × class × leg (`outputs/tables/self_supply_panel.parquet`) plus storage-hydro unit-days (`self_supply_hydro_unitday.parquet`), both gitignored. `--describe` writes step 1a's tables and prints the stop rule. Check script `scripts/qa/check_self_supply_cost.py`.

**Tech Stack:** Python 3.14 `.venv`, pandas, numpy; `lib/unit_ownership.majority_group`, `step_estimator.wdemean`, `midday_hydro_iv.cluster_meat`.

**Spec:** `docs/specs/2026-10-21-self-supply-cost-design.md` (§2 the measure, §3 step 1a).

## Global Constraints

- Five firms `ENDESA, IBERDROLA, NATURGY, EDP, REPSOL`; each unit to its largest exposed owner that day (`majority_group(..., exposed=True)`); window 2019-01 → 2025-09; full days only (24 hourly or 96 quarter-hourly periods; DST days out, as `month_legs`).
- Generation = a unit-hour-leg with summed MW > 0 whose registry role is not `purchase_retail` or `pumping` (exactly `month_legs`' `gen`). Legs: bilateral = PDBF `role_code == "4"`, else auction. Hourly MW = Σ schedule_mw × resolution_min / 60 within the hour.
- m = Σ q (p − c) over costed unit-hours, € per hour; p = `price_pt` for registry country PT, else `price_es`.
- Classes and costs (spec §2), by precedence: reactor in `nuclear_cuts_benchmark_daily` → `nuclear`, c = `c_acct`; `hydro_cost_daily` with `pumped` → `pumped` (no cost); `hydro_cost_daily` otherwise → `hydro_storage`, c = `cost_eur_mwh`; `implied_marginal_cost_daily` with `eff_is_generic == False` → `gas` / `coal` by `fuel`, c = `marginal_cost_capped_bid_eur_mwh`; then the label (`tech_omie`, else `tech_omie_early`): wind → `wind` (c 0), solar → `solar` (c 0), hydro → `hydro_other` (c 0), pumped storage → `pumped`, gas CCGT or coal → `thermal_nocost`; anything else → `nocost`. A unit-day whose class has a cost but the cost is missing that day is uncosted.
- Variants carried for step 1b: `m_nuc_lo` (`c_lo`), `m_nuc_hi` (`c_hi`), `m_hyd90` (`cost_90_eur_mwh`); equal to m outside their class.
- Stop (spec §3, 1a): costed share of the five firms' output < 80% in any year (pooled), or 2.8 × se(b) > |A|. A single firm below 80% in a year is flagged, no stop.
- Ask before committing code and results (the plan is committed when written).

## Review Focus

1. **The legs must equal the quantity test's.** Pinned in Task 1: on weekdays, Σ over classes of the panel's MW equals `holiday_quantity_panel.parquet`'s `gen_auction` and `gen_bilateral` on every (group, date, hour), within 0.01 MW.
2. **Country price for Portuguese units** (EDP's hydro): pinned by a synthetic test in Task 1 that a PT unit is priced at `price_pt`.
3. **A cost defined on part of a day or class**: pinned by a synthetic test that an uncosted unit-hour adds to `mwh` but not to `costed_mwh`, `m` or `above_*`.
4. **Capture ratio**: Σ p q / Σ p̄_d q, with p̄_d the day's mean price in the unit's country; pinned by synthetic tests (all output in the day's top-price hour → ratio > 1; flat output → 1).
5. **se(b) under the null**: from the outcome residual only, without forming b; pinned by a synthetic test where it is within 10% of the OLS clustered se when b = 0.

---

### Task 1: The panel (`--build`)

**Files:** create `scripts/analysis/self_supply_cost.py`, `scripts/qa/check_self_supply_cost.py`.

**Produces:** `unit_classes() -> pd.DataFrame` [unit, cls]; `daily_costs() -> pd.DataFrame` [unit, date, c, c_nuc_lo, c_nuc_hi, c_hyd90]; `margin_rows(u: pd.DataFrame) -> pd.DataFrame` (input columns unit, group, date, hour, leg, cls, q, p, pbar, c, c_nuc_lo, c_nuc_hi, c_hyd90; adds mwh, costed_mwh, pq, pbarq, m, m_nuc_lo, m_nuc_hi, m_hyd90, above_mwh, above_eur); `build() -> int`. Panel columns: group, date, hour, cls, leg, mwh, costed_mwh, pq, pbarq, m, m_nuc_lo, m_nuc_hi, m_hyd90, above_mwh, above_eur. Unit-day columns: unit, group, date, q_auction, q_bilateral, pq, pbarq.

- [ ] Write the checks: `margin_rows` on three hand unit-hours (ES nuclear q 100, p 60, c 25 → m 3,500, above 0; PT hydro q 50 priced at p_pt 40 against λ* 55 → m −750, above_mwh 50, above_eur 750; an uncosted CCGT q 80 → mwh 80, costed 0, m 0); class precedence on a table with a unit in both the nuclear set and labelled `nocost`; and, if the panel exists, the leg invariant of Review Focus 1.
- [ ] Run → fails (no module). Implement. Run the synthetic checks → pass.
- [ ] Run `--build` in the background (log `.superpowers/sdd/2026-10-21-self-supply-cost-step1a/build.log`). Run the checks → the invariant passes.

### Task 2: Step 1a (`--describe`)

**Produces:** `capture(pq, pbarq)`, `fit_daily(d, y, x, cluster="date") -> (b, se)` (date and group × month effects), `se_null(d, y, x, cluster="date") -> float`; tables `outputs/tables/self_supply_{composition,above_cost,hydro_timing,power}.csv`.

- [ ] Write the checks of Review Focus 4 and 5, and that `fit_daily` recovers a planted b of −20 € per MWh within 3 se.
- [ ] Run → fails. Implement `--describe`:
  1. **Composition**: TWh by group × year × class × leg; costed share by year (pooled) and by group × year.
  2. **Above cost**: above_mwh, above_eur, and above_mwh / costed_mwh, by group × year × class × leg.
  3. **Hydro timing**: `hydro_storage` capture by group × year × leg; unit-day capture on bilateral share with unit × month effects, date clusters, per group with any bilateral hydro.
  4. **The generic units** `GGNCOV1`, `GREPSV1`: registry role and country, `cab` description and max power, OMIE listing owner and technology, and their bilateral TWh by year.
  5. **Power**: weekday firm-days with the holiday dose Z_fd = Σ_h dose_mw (MWh, `holiday_dose.parquet`); M_fd = Σ m; b_k = `fit_daily` of each class's MWh on Z; m̄_k = Σ_dosed Z · m_k / Σ_dosed Z · costed_mwh_k; A = Σ_k b_k m̄_k over costed classes; se(b) = `se_null(M on Z)`; MDE = 2.8 se. Print the stop rule.
- [ ] Run the checks → pass. Run `--describe` (log `describe.log`).

### Task 3: Write-up

- [ ] New running note `notes/rq-self-supply-cost.md` (step 1a), the spec's status line, memory. Then ask before committing.
