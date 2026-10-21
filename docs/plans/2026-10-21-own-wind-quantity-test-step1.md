# Own wind as the shock, step 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the own-wind quantity panel and run step 1 of the design (first stage, placebo, power) with its stop rule; the outcome regression itself (b_W, b_P) is not formed.

**Architecture:** One script, `scripts/analysis/own_wind_quantity_test.py`. `--panel` joins the holiday quantity panel's rows (slope, s, retail, inv_slope) to the self-supply panel's generation by class and leg, to own wind and its regional deviation (`self_supply_cost.own_wind_hourly`, real and forecast versions) and to REE's D-1 forecasts, and writes `outputs/tables/own_wind_quantity_panel.parquet` (gitignored). `--test --step 1` writes `outputs/tables/own_wind_quantity_step1.csv` and prints the stop rule. Check script `scripts/qa/check_own_wind_quantity.py`.

**Tech Stack:** Python 3.14 `.venv`, pandas, numpy; `holiday_quantity_test.resid` (date × hour and firm × month effects), `iv_two_endog.tsls_k` / `sw_f`, `midday_hydro_iv.cluster_meat`, `regional_wind_offer_test.{forecasts, regional_cf, own_capacity}`.

**Spec:** `docs/specs/2026-10-21-own-wind-quantity-test-design.md` (§2 the test, §3 step 1, §7).

## Global Constraints

- Five firms `ENDESA, IBERDROLA, NATURGY, EDP, REPSOL`; weekdays 2019-01 → 2025-09; the holiday quantity panel's rows with `slope` and `s` defined (slope ≥ FLOOR already applied there); hours without own wind (fewer than 30 provinces) dropped by an inner join.
- W_s = the self-supply panel's `wind` class MW, both legs. G_other = generation of every class except `wind` and `generic`, both legs; also by leg. P_W = W_s × inv_slope.
- Instruments: Wdev = Σ_r K_gr (cf_rt − cf_t) in MW (`own_wind_hourly`'s `Wdev_real`) and Wdev_inv = Wdev × inv_slope. Forecast version Wdev_fc the same with `cf_fc` / `dev_fc`, carried for step 2.
- Controls: inv_slope; `retail` (own retail purchases, PDBF both legs); group × each of F_wind, F_solar, F_demand (ESIOS 1777, 1779, 1775), 15 columns. Effects: date × hour and firm × month (`resid`); clusters: date.
- s̄ = Σ s |Wdev| / Σ |Wdev|. MDE β = 2.8 · se(b_P | b_P = 0) / s̄.
- Stop (spec §3, step 1): Sanderson–Windmeijer F < 10 for W_s or for P_W, or MDE β > 1. The placebo (retail on Wdev and Wdev_inv, other controls) is reported with its t; the spec gives it no stop rule.
- Step 1 does not form b_W or b_P on the outcome. Ask before committing code and results (the plan is committed when written).

## Review Focus

1. **Generation must add up.** Pinned in Task 1: on every panel row, G_other + W_s + generic equals the holiday panel's `gen` within 0.01 MW, and each leg equals `gen_auction` / `gen_bilateral`.
2. **The power figure must not peek at b_P.** `se_null_iv` takes the residual of the model restricted to b_P = 0; pinned by a synthetic test where it is within 10% of the 2SLS se when b_P = 0.
3. **The 2SLS fit must recover both stories** through the same demeaning and controls the real run uses: planted book balancing (b_W −0.5, b_P 0) and Nash (b_P = −40) on a synthetic panel with W_s endogenous (its error correlated with the outcome's), each within 3 se; and OLS on the same data must be off, so the test shows the instrument doing work.
4. **Firms with no located wind in a region** contribute 0 to Wdev there, not NaN: `own_wind_hourly` sums over located regions only; checked by every panel row having a finite Wdev.
5. **Hour alignment** (Madrid date and hour) is pinned by `check_self_supply_cost.py`'s hourly own-wind test, unchanged.

---

### Task 1: The panel (`--panel`)

**Files:** create `scripts/analysis/own_wind_quantity_test.py`, `scripts/qa/check_own_wind_quantity.py`.

**Produces:** `build_panel() -> int`; panel columns: the holiday panel's KEY, gen, gen_auction, gen_bilateral, retail, slope, inv_slope, s, slope_cost; `W_s, W_s_auction, W_s_bilateral, generic, G_other, G_other_auction, G_other_bilateral`, `g_hydro_storage, g_nuclear, g_thermal` (gas + coal + thermal_nocost), `g_rest` (the other classes); `W_real, Wdev, Wdev_fc`; `F_wind, F_solar, F_demand`; `P_W, Wdev_inv, Wdev_fc_inv`.

- [ ] Write the check of Review Focus 1 and 4 (skipped with a note when the panel is absent).
- [ ] Run → fails (no module). Implement `--panel`. Run `--panel` (log `.superpowers/sdd/2026-10-21-own-wind-quantity-test-step1/panel.log`); it prints rows kept, own-wind coverage, and W_s's auction / bilateral shares. Run the checks → pass.

### Task 2: Step 1 (`--test --step 1`)

**Produces:** `prep(d, cols) -> np.ndarray` (the `resid` effects); `fit_iv(d, y, endog, inst, controls) -> {name: (b, se)}`; `se_null_iv(y, X, Z, W, cl, j) -> float`; `step1() -> int`; `outputs/tables/own_wind_quantity_step1.csv` with rows `first stage` (W_s and P_W on each instrument: b, se, SW F), `placebo` (retail on Wdev and Wdev_inv: b, se, t), `power` (se_bP_null, s̄, MDE β, per outcome G_other, G_other_auction, G_other_bilateral).

- [ ] Write the checks of Review Focus 2 and 3 on a synthetic panel (5 groups × 260 weekdays × 24 hours).
- [ ] Run → fails. Implement. Run the checks → pass.
- [ ] Run `--test --step 1` (log `step1.log`). Read the stop rule.

### Task 3: Write-up

- [ ] New running note `notes/rq-own-wind-quantity.md` (step 1), the spec's status line, memory. Then ask before committing.
