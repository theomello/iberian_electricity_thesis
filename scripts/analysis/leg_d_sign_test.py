#!/usr/bin/env python3
"""Leg D: does a firm's offer respond to X with the same slope whether it is buying or selling?

    .venv/bin/python scripts/analysis/leg_d_panel.py        # input
    .venv/bin/python scripts/analysis/leg_d_sign_test.py

Framework spec §4, leg D. For each dispatchable unit-hour of the five firms

    y_uh = a_ud + a_hym + g+ * Xp_fh + g- * Xm_fh + c * fcst_h + e

y is the share of capacity offered at or below the unit-day's median offer
price, in percentage points (s50). a_ud is a unit x day effect (it removes the
water value or the day's fuel price), a_hym an hour x year-month effect (the
solar profile's growth), fcst the day-ahead demand forecast. Xp and Xm are
instrumented by rivals' offered solar z and z * s_prev (s_prev: net seller in
that hour yesterday). Errors clustered by ISO week.

READING (spec table): price-taking g+ = g- = 0; supply-function Nash on the net
position g+ = g- < 0; market power on output, ignoring purchases, g+ < 0 < g-.
Weak-instrument-robust: the Anderson-Rubin test of (0, 0); the exact AR set of
values c with g+ = g- = c not rejected (empty: no common slope fits), with the
smallest AR p over c; and each coefficient's AR projection, whose sign is the
robust sign test that separates Nash (g- < 0) from output-based conduct (g- > 0).

BETA SCALE. Nash is symmetric in beta, and gamma = -beta * the curve's offer
density at the reference price, so beta+ and beta- divide by the mean density in
seller and buyer hours separately; their equality and their common-value AR set
are reported beside the gamma-scale ones.

FLAGS. WEAK: a conditional first-stage F below 10 (read AR, not 2SLS).
FEW-WEEKS: s = 1 or s = 0 in fewer than 100 week clusters, where AR over-rejects
(28% at 3 weeks, 6% at 100 in the Task 2 review's simulation). A last robustness
row uses the sign seven days before (zs7): s_prev is a lagged outcome.

PLACEBO. FRINGE units (outside the five, >= 50 MW) have small X. Their reduced
form, y on rivals' solar, estimates how solar reshapes offers through cost
alone (start-ups, cycling); the five firms' reduced forms are read against it,
hydro against hydro and thermal against thermal.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from iv_two_endog import (ar_common_exact, ar_projection, ar_test, fmt_intervals,  # noqa: E402
                          fmt_set, projection_grid, projection_sign, sw_f, tsls_k)
from midday_hydro_iv import ols  # noqa: E402
from solar_first_stage import demean  # noqa: E402

PANEL = ROOT / "outputs/tables/leg_d_panel.parquet"
OUT = ROOT / "outputs/tables/leg_d_results.csv"
MIN_ROWS = 2000
WEAK_F = 10.0   # below this conditional F, read the AR results, not 2SLS
FEW_WEEKS = 100  # AR over-rejects when either sign of s occurs in fewer weeks (Task 2 review)
ERAS = [("2018-2021", 2018, 2021), ("2022-2023", 2022, 2023), ("2024-2026", 2024, 2026)]


def load() -> pd.DataFrame:
    h = pd.read_parquet(PANEL)
    h["ud"] = h.unit + "_" + h.date.dt.strftime("%Y%m%d")
    h["hym"] = h.hour.astype(str) + "_" + h.date.dt.strftime("%Y%m")
    for q in ("25", "50", "75"):
        h[f"y{q}"] = h[f"s{q}"] * 100
        h[f"dd{q}"] = h[f"d{q}"] * 100
    return h


def _negate(iv):
    """Intervals of c = -beta as intervals of beta."""
    return None if iv is None else [[-hi, -lo] for lo, hi in reversed(iv)]


def estimate(d: pd.DataFrame, label: str, y: str = "y50", dens: str = "dd50",
             zs: str = "zs") -> dict:
    s_col = "s_prev" if zs == "zs" else "s_prev7"
    cols = [y, "Xp", "Xm", "z", zs, "fcst"]
    d = d.dropna(subset=cols)
    w1, w0 = d.loc[d[s_col] == 1, "wk"].nunique(), d.loc[d[s_col] == 0, "wk"].nunique()
    row = {"sample": label, "outcome": y, "instrument": f"z, {zs}", "n": len(d),
           "units": d.unit.nunique(), "weeks": d.wk.nunique(), "weeks_s1": w1, "weeks_s0": w0,
           "few_weeks": bool(min(w1, w0) < FEW_WEEKS)}
    if len(d) < MIN_ROWS:
        print(f"  {label:34s} too few ({len(d)})")
        return row | {"status": "too few"}
    w = demean(d, cols, ["ud", "hym"])
    Y = w[y].to_numpy()
    X = w[["Xp", "Xm"]].to_numpy()
    Z = w[["z", zs]].to_numpy()
    W = w[["fcst"]].to_numpy()
    cl = d.wk.to_numpy()
    b, V = tsls_k(Y, X, Z, W, cl)
    if np.isnan(b).any():
        print(f"  {label:34s} n={len(d):>8,}  not identified (instruments cannot separate X+ and X-)"
              f"  weeks s=1/0 {w1}/{w0}")
        return row | {"status": "not identified"}
    se = np.sqrt(np.diag(V))
    p_eq = float(2 * stats.norm.sf(abs(b[0] - b[1]) / np.sqrt(V[0, 0] + V[1, 1] - 2 * V[0, 1])))
    f_p, f_m = sw_f(X, Z, W, cl, 0), sw_f(X, Z, W, cl, 1)
    _, p00 = ar_test(Y, X, Z, W, cl, [0.0, 0.0])
    ex = ar_common_exact(Y, X, Z, W, cl)
    # Each projection grid is dense around its own 2SLS estimate (iv_two_endog.projection_grid).
    gp, gm = projection_grid(b[0], se[0]), projection_grid(b[1], se[1])
    pp, pm = ar_projection(Y, X, Z, W, cl, 0, gp), ar_projection(Y, X, Z, W, cl, 1, gm)
    # Nash is symmetric in beta, and gamma = -beta * the curve's offer density, so the
    # beta-scale test divides each side by its own regime's mean density.
    m_p, m_m = d.loc[d.Xp > 0, dens].mean(), d.loc[d.Xm < 0, dens].mean()
    bp, bm = -b[0] / m_p, -b[1] / m_m
    v_beta = V[0, 0] / m_p ** 2 + V[1, 1] / m_m ** 2 - 2 * V[0, 1] / (m_p * m_m)
    p_eq_beta = float(2 * stats.norm.sf(abs(bp - bm) / np.sqrt(v_beta)))
    exb = ar_common_exact(Y, X * np.array([m_p, m_m]), Z, W, cl)
    beta_common = fmt_intervals(_negate(exb["intervals"])) if exb else "not identified"
    weak = bool(min(f_p, f_m) < WEAK_F)
    row |= {"status": "weak" if weak else "ok", "g_plus": b[0], "se_plus": se[0],
            "g_minus": b[1], "se_minus": se[1], "p_equal": p_eq, "sw_f_plus": f_p,
            "sw_f_minus": f_m, "ar_p_zero": p00,
            "ar_common": fmt_intervals(ex["intervals"]), "ar_common_p_min": ex["p_min"],
            "proj_plus": fmt_set(pp, gp), "proj_minus": fmt_set(pm, gm),
            "sign_plus": projection_sign(pp), "sign_minus": projection_sign(pm),
            "density_plus": m_p, "density_minus": m_m, "beta_plus": bp, "beta_minus": bm,
            "p_equal_beta": p_eq_beta, "beta_common": beta_common}
    flags = ("  WEAK" if weak else "") + ("  FEW-WEEKS" if row["few_weeks"] else "")
    print(f"  {label:34s} n={len(d):>8,}  g+ {b[0]:+.3f} ({se[0]:.3f})  g- {b[1]:+.3f} ({se[1]:.3f})  "
          f"SW F {f_p:.1f}/{f_m:.1f}  AR p(0,0) {p00:.3f}  common g {row['ar_common']} "
          f"(min p {ex['p_min']:.3f})  sign g+/g- {projection_sign(pp)}/{projection_sign(pm)}  "
          f"beta {bp:+.2f}/{bm:+.2f} p(eq) {p_eq_beta:.3f} common beta {beta_common}  "
          f"weeks s=1/0 {w1}/{w0}{flags}")
    return row


def reduced_form(d: pd.DataFrame, label: str) -> dict:
    cols = ["y50", "z", "fcst"]
    d = d.dropna(subset=cols)
    if len(d) < MIN_ROWS:
        return {"sample": label, "status": "too few", "n": len(d)}
    w = demean(d, cols, ["ud", "hym"])
    b, se = ols(w.y50.to_numpy(), w[["z", "fcst"]].to_numpy(), d.wk.to_numpy())
    print(f"  {label:34s} n={len(d):>8,}  s50 on rivals' solar {b[0]:+.3f} pp per GW (t {b[0]/se[0]:+.1f})")
    return {"sample": label, "outcome": "y50 reduced form", "status": "ok", "n": len(d),
            "rf": b[0], "rf_se": se[0]}


def main() -> int:
    h = load()
    five = h[h.firm != "FRINGE"]
    rows = []
    print("LEG D -- g+ and g- in pp of capacity per EUR/MWh of X; beta = -g / density.\n")
    print("POOLED, all five firms")
    rows.append(estimate(five, "pooled"))
    for q in ("25", "75"):
        rows.append(estimate(five, f"pooled, s{q}", f"y{q}", f"dd{q}"))
    print("\nBY TECHNOLOGY")
    rows.append(estimate(five[five.cls.isin(["hydro", "pumped"])], "hydro + pumped"))
    rows.append(estimate(five[five.cls.isin(["ccgt", "coal"])], "ccgt + coal"))
    print("\nBY FIRM")
    for f, g in five.groupby("firm"):
        rows.append(estimate(g, f))
    print("\nBY ERA")
    for lab, a, b in ERAS:
        rows.append(estimate(five[five.date.dt.year.between(a, b)], lab))
    print("\nROBUSTNESS")
    both = (five.groupby(["firm", "date"]).Xp.transform("max") > 0) & \
           (five.groupby(["firm", "date"]).Xm.transform("min") < 0)
    rows.append(estimate(five[both], "firm-days with both signs"))
    rows.append(estimate(five[five.zero_price == 0], "no zero-price hours"))
    rows.append(estimate(five, "pooled, sign 7 days before", zs="zs7"))
    print("\nPLACEBO -- reduced forms, s50 on rivals' solar")
    fringe = h[h.firm == "FRINGE"]
    rows.append(reduced_form(fringe, "FRINGE (placebo)"))
    # Solar's cost channel differs by technology (cycling is thermal), so each
    # five-firm reduced form is read against the fringe of the same technology.
    for who, d in (("FRINGE", fringe), ("five firms", five)):
        for c, g in d.groupby(d.cls.isin(["ccgt", "coal"]).map({True: "thermal", False: "hydro"})):
            rows.append(reduced_form(g, f"{who}, {c}"))
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    # Exit 1 only if the pooled test could not be computed at all.
    return 0 if rows[0].get("status") in ("ok", "weak") else 1


if __name__ == "__main__":
    raise SystemExit(main())
