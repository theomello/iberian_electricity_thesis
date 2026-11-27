# Tariff 6.2 on a constant population: rerun the 6.2 results on E3 (registered on commit)

**Status: registered when this file is committed (user: "Yes, register it", 2026-11-27); the run follows the commit of
its script.** Follows `2026-11-26-tariff-drift-design.md` (Step 3), `2026-11-26-joint-regression-design.md` and
`2026-11-26-orthogonal-and-sensitivity-design.md` (Part A).

## Why
ESIOS 1216, the outcome series for tariff 6.2 in every industry run, is not one population over 2014–2026
(`docs/data-reference/ree-ren-esios-miteco.md`, checked 2026-11-27): it equals E3 (ESIOS 1204, measured demand at
36–72.5 kV) to the MWh until September 2018, and from October 2018 adds the 30–36 kV customers (about 365–475 GWh a
month, E3/1216 about 0.77 after). The placebo summers 2014–2018 therefore measure one group and 2019 and 2021
another. The orthogonal-score 6.2 placebo thetas are −0.13 to −0.32 for 2014–2018 and +0.53 in 2019, the first summer
after the break. **E3 is the constant-population series for 6.2.** It drops the 30–36 kV part (about 23% of 6.2 after
2018), which the earlier summers never contained.

**What is not blind.** All 6.2 results on 1216 (baseline −0.064, placebo mean +0.020, sd 0.017; joint-regression betas;
orthogonal-score θ +0.23, placebo sd 0.31), the pooled 6.2–6.4 headline (−0.15 trend null to −0.32 mean null), and the
break itself with the 2019 theta. Nothing has been computed on E3.

## Design
One script, `scripts/analysis/tou_six_two_e3.py`, runs the existing estimators unchanged with only the 6.2 outcome
series swapped: `tou_industry_six_summer.IDS["6.2"]` = [1204] instead of [1216]. Everything else is as registered
before: dose (tariff 6.2's full regulated-price dose), Portugal differencing, leave-one-year-out per-hour LASSO,
aligned 107-day windows, placebo summers 2014–2019, gates. Only the 6.2 LASSO errors are refitted; the cached errors
of every other series are reused, and the merged cache is written to a separate file
(`data/cache_tou/six_summer_errors_e3.parquet`). Outputs go to `outputs/tables/six_two_e3/` (the committed tables are not
overwritten).

Estimators rerun:
1. **Step 3 (baseline by tariff and pooled):** `tou_tariff_drift` — 6.2 and the 6.2–6.4 pool: η_2021, placebo mean
   and sd, slope, mean-null and trend-null effects.
2. **Joint regression:** `tou_joint_regression 6.2` — the counterfactual-calendar version.
3. **Orthogonal score (Part A):** `tou_dml_pooled --series 6.2` — θ_2021 A/B, placebo sd, rules O1–O4 as registered.

## Rules, set now
- **M0 machinery.** The script run with the source left at 1216 reproduces the committed 6.2 baseline (η −0.06369,
  placebo mean +0.01955, sd 0.01684, within 0.0015, the existing T1 check). If not, stop.
- **Z0 data.** E3 has no missing hours in any month 2014–2021 used (the existing completeness gate). A summer failing it
  leaves the 6.2 placebo set, as before.
- **C1 the break explains the orthogonal-score failure** if, on E3, the 2019 orthogonal-score placebo theta lies within
  the range of the 2014–2018 thetas widened by one of their sd, **and** the placebo sd falls to at most 3× the baseline's
  (0.0168 → ≤ 0.05). Otherwise the failure is not attributed to the break.
- **C2 the outcome series for 6.2 becomes E3 in the thesis, whatever the results** (decided now, before the run: it is
  the series with a constant population). The 1216 numbers move to an appendix note with the reason. The pooled 6.2–6.4
  headline is recomputed with E3 and replaces −0.15 to −0.32 in `numbers.tex` and the tariff table, with the old range
  stated beside it once.
- **C3 the drift.** Report the pooled placebo slope on E3 beside the committed −0.0377 (se 0.0106). If its magnitude
  falls by more than a quarter, part of the pooled "shape drift" was the 6.2 composition break; otherwise it was not.

## Not covered
The large-industry persistence runs (2022–2025, `2026-11-23-firm-calendar-persistence-design.md`,
`2026-11-26-persistence-joint-design.md`) also use 1216 with placebo summers 2014–2019; they are not rerun here. If C2
changes the 6.2 picture materially, they are the next candidate, on a separate go-ahead.

## Results (run 2026-11-27, `scripts/analysis/tou_six_two_e3.py`, committed before the run as 503d1fa; outputs in `outputs/tables/six_two_e3/`)

**M0 passes:** with the source at 1216 the script reproduces the committed 6.2 baseline exactly (η −0.06369, placebo mean
+0.01955, sd 0.01684), and 6.3, 6.4 and the pooled trend null (−0.150, p 0.045). **Z0 passes:** E3 is complete in every
year 2014–2020.

| | on 1216 | on E3 |
|---|---|---|
| 6.2 baseline η_2021 | −0.064 | −0.057 |
| placebo mean (sd) | +0.020 (0.017) | +0.029 (0.026) |
| effect, mean null (p) | −0.083 (0.003) | −0.086 (0.014) |
| effect, trend null (p) | −0.079 (0.025) | −0.079 (0.073) |
| 6.2 joint regression, mean / trend null | −0.03 / −0.08 | −0.08 [−0.17, 0.01] (p 0.032) / −0.11 [−0.25, 0.02] (p 0.040) |
| 6.2 orthogonal score θ_2021 (A / B) | +0.231 / +0.227 | **−0.157 / −0.153** |
| orthogonal-score placebo thetas (A), 2014…2019 | −0.27, −0.13, −0.13, −0.20, −0.32, **+0.53** | −0.12, +0.01, +0.07, +0.09, −0.01, +0.05 |
| orthogonal-score placebo sd (A) | 0.311 | 0.076 |
| pool 6.2–6.4, mean null | −0.320 (p 0.007) | −0.321 (p 0.006) |
| pool 6.2–6.4, trend null | −0.151 (p 0.045) [−0.34, +0.04] | −0.151 (p 0.027) [−0.31, +0.005] |
| pool placebo slope per year | −0.0377 (0.0106) | −0.0379 (0.0088) |

**C1: fails on the registered bar.** The 2019 orthogonal-score theta (+0.048) now lies inside the 2014–2018 range
(−0.115 to +0.093), so the first condition holds; the placebo sd (0.076) is 4.5 times the baseline's, above the 3× bar
(0.05). As registered, the orthogonal-score failure is not attributed to the break. Stated beside it: the break removes
the 2019 jump and the wrong sign (θ_2021 +0.23 → −0.16, ridge −0.15, O4 passes), and the spread falls fourfold; what
remains is a noisier estimator, as for E0 (1.4×) and 6.4 (1.25×), only more so.

**C2 (decided before the run): E3 is the 6.2 series in the thesis.** The pooled headline is unchanged to two decimals
(−0.15 to −0.32; trend-null p 0.045 → 0.027). The per-tariff table (`paper/tables/tariff_effects.tex`, generated) now
takes 6.2 from the E3 run: 6.2 moves from "not detected, a bound" to negative under both nulls in the joint
regression (one-sided p 0.03–0.04, intervals reaching just above zero). The registered joint-regression rules were not
re-applied to 6.2.

**C3: the drift is not the break.** The pooled placebo slope is −0.0379 on E3 against −0.0377: unchanged.
