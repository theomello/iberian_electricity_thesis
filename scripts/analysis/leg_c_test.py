#!/usr/bin/env python3
"""Leg C: the condition p - c = beta * X in levels, at the margin of thermal units.

    .venv/bin/python scripts/analysis/leg_c_panel.py     # input
    .venv/bin/python scripts/analysis/leg_c_test.py

Framework spec §4, leg C. One row per unit-period at the unit's own margin (Task 3).

SPEC 1, cost imposed:     p - c = a_u + beta * X + e     units with a plant-specific JRC efficiency
SPEC 2, heat rate free:   p = a_u + h_u * fuel_index + beta * X + e     all units
ROUTE 3, declared cost:   p - var_term = a_u + beta * X + e     units declaring a variable term

a_u is a unit effect (O&M, any constant bias). X is instrumented by the owner's rivals'
offered wind and solar (zw, zs, GW); errors clustered by ISO week. beta = 0 is
price-taking, beta = 1 full supply-function Nash (p - c = X). Inference that survives
weak instruments: AR tests of beta = 0 and beta = 1, and the exact AR set for beta.
A row is WEAK when its first-stage F is below 10. `ar_set_p_min` is the chi2(2) p-value
at the AR minimum: the set is empty exactly when it is below 0.05 (with one regressor and
two instruments the properly sized over-identification test would use chi2(1)).

SPEC 2 VALIDATES SPEC 1. h_u is recovered as the OLS of (y - beta_hat * X) on the
unit-specific fuel_index columns (the 2SLS normal equations give exactly that). For gas
units with a plant-specific efficiency and at least MIN_UNIT rows, h_u * eff should be
near 1: VALIDATED when the median is within [0.85, 1.15] and at least half lie within
+-0.20. Otherwise specification 1 is not trusted.

THE MARKDOWN IN LEVELS. p - c tabulated by the sign of X: the spec's prediction is a
price below observed cost when the firm is a net buyer and above it when a net seller.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from iv_two_endog import ar_set_k1, ar_test, fmt_intervals, sw_f, tsls_k  # noqa: E402
from solar_first_stage import demean  # noqa: E402

PANEL = ROOT / "outputs/tables/leg_c_panel.parquet"
OUT = ROOT / "outputs/tables/leg_c_results.csv"
MIN_ROWS = 500
MIN_UNIT = 200
WEAK_F = 10.0
FIVE = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")


def iv(d: pd.DataFrame, y: str, label: str, spec: str, heat: bool = False) -> dict:
    """2SLS of y on X with unit effects (and unit-specific fuel_index slopes when heat)."""
    d = d.dropna(subset=[y, "X", "zw", "zs"])
    d = d[np.isfinite(d[[y, "X", "zw", "zs"]]).all(axis=1)].copy()
    if heat:
        # A unit with too few rows, or a fuel cost that never moves, has no estimable h_u,
        # and its all-zero column would void the whole specification.
        g = d.groupby("unit").fuel_index
        keep = (g.transform("size") >= MIN_UNIT) & (g.transform("nunique") >= 2)
        if (~keep).any():
            print(f"  spec 2 drops {d.loc[~keep, 'unit'].nunique()} units ({(~keep).sum()} rows) "
                  f"with < {MIN_UNIT} rows or a constant fuel cost")
        d = d[keep].copy()
    row = {"sample": label, "spec": spec, "n": len(d), "units": d.unit.nunique(), "weeks": d.wk.nunique()}
    if len(d) < MIN_ROWS:
        print(f"  {label:28s} {spec:8s} too few ({len(d)})")
        return row | {"status": "too few"}
    hcols = []
    if heat:
        for u in sorted(d.unit.unique()):
            c = f"h_{u}"
            d[c] = d.fuel_index.where(d.unit == u, 0.0)
            hcols.append(c)
    w = demean(d, [y, "X", "zw", "zs", *hcols], ["unit"])
    Y, X, Z = w[y].to_numpy(), w[["X"]].to_numpy(), w[["zw", "zs"]].to_numpy()
    W = w[hcols].to_numpy() if hcols else np.zeros((len(w), 0))
    cl = d.wk.to_numpy()
    b, V = tsls_k(Y, X, Z, W, cl)
    if np.isnan(b).any():
        print(f"  {label:28s} {spec:8s} not identified")
        return row | {"status": "not identified"}
    f1 = sw_f(X, Z, W, cl, 0)
    _, p0 = ar_test(Y, X, Z, W, cl, [0.0])
    _, p1 = ar_test(Y, X, Z, W, cl, [1.0])
    s = ar_set_k1(Y, X[:, 0], Z, W, cl)
    row |= {"status": "weak" if f1 < WEAK_F else "ok", "beta": b[0], "se": np.sqrt(V[0, 0]),
            "first_stage_f": f1, "ar_p_beta0": p0, "ar_p_beta1": p1,
            "ar_set": fmt_intervals(s["intervals"]), "ar_set_p_min": s["p_min"]}
    extra = ""
    if heat:
        h = np.linalg.lstsq(W, Y - X[:, 0] * b[0], rcond=None)[0]
        eff = d.groupby("unit").eff.first()
        gen = d.groupby("unit").eff_is_generic.first()
        fuel = d.groupby("unit").fuel.first()
        nrow = d.groupby("unit").size()
        ok_u = [u for u in sorted(d.unit.unique())
                if fuel[u] == "gas" and not gen[u] and nrow[u] >= MIN_UNIT]
        r = pd.Series({u: h[i] * eff[u] for i, u in enumerate(sorted(d.unit.unique())) if u in ok_u})
        med = float(r.median()) if len(r) else np.nan
        share = float((r.sub(1).abs() <= 0.20).mean()) if len(r) else np.nan
        valid = bool(len(r) > 0 and 0.85 <= med <= 1.15 and share >= 0.5)
        row |= {"h_eff_median": med, "h_eff_share_20": share, "h_units": len(r), "validated": valid}
        extra = f"  h*eff median {med:.3f}, within 20% {share:.2f} of {len(r)} gas units -> {'VALIDATED' if valid else 'NOT validated'}"
    flag = "  WEAK" if f1 < WEAK_F else ""
    print(f"  {label:28s} {spec:8s} n={len(d):>8,} beta {b[0]:+.3f} ({np.sqrt(V[0, 0]):.3f})  F {f1:.1f}  "
          f"AR p(beta=0) {p0:.3f} p(beta=1) {p1:.3f}  AR set {row['ar_set']}{flag}{extra}")
    return row


def markdown(d: pd.DataFrame) -> list[dict]:
    """p - c by the sign of X, spec 1's sample."""
    rows = []
    for sign, g in (("X < 0 (net buyer)", d[d.X < 0]), ("X > 0 (net seller)", d[d.X > 0])):
        m = g.p - g.c
        rows.append({"sample": "markdown table", "spec": "levels", "sign": sign, "n": len(g),
                     "median_p_minus_c": float(m.median()), "share_below_cost": float((m < 0).mean())})
        print(f"  {sign:22s} n={len(g):>8,}  median p - c {m.median():+.2f}  share below cost {(m < 0).mean():.3f}")
    return rows


def main() -> int:
    full = pd.read_parquet(PANEL)
    full["pc"] = full.p - full.c
    full["pv"] = full.p - full.var_term
    # Headline samples leave out unit-periods at a minimum-load gap (panel `min_load`): their
    # price sits above a near-zero tranche, not on a cost-reflecting step.
    d = full[~full.min_load]
    s1 = d[~d.eff_is_generic]
    rows = []
    print("LEG C -- beta in p - c = beta * X (beta = 1: full Nash); X instrumented by rivals' wind and solar.\n")
    print("SPEC 1, cost imposed (plant-specific efficiency)")
    rows.append(iv(s1, "pc", "pooled", "spec 1"))
    for f in ("gas", "coal"):
        rows.append(iv(s1[s1.fuel == f], "pc", f, "spec 1"))
    for lab, a, b in (("2018-2021", 2018, 2021), ("2022-2023", 2022, 2023)):
        rows.append(iv(s1[s1.date.dt.year.between(a, b)], "pc", lab, "spec 1"))
    rows.append(iv(s1[s1.firm.isin(FIVE)], "pc", "five firms", "spec 1"))
    rows.append(iv(s1[~s1.firm.isin(FIVE)], "pc", "other owners", "spec 1"))
    # AXPO and ENGIE bid mostly for farms they represent, so their X is mostly others' volume.
    rows.append(iv(s1[~s1.firm.isin(["AXPO", "ENGIE"])], "pc", "without AXPO, ENGIE", "spec 1"))
    # X is static-owner: EDP's excludes its NATVD wind (to 2020-08) and Castejon's sales,
    # TotalEnergies' includes them, until the sale of 2020-12-01.
    # Naturgy's static X counts Plana del Vent, RWE's until 2019-07-18.
    early = ((s1.firm.isin(["EDP", "TOTALENERGIES"]) & (s1.date < "2020-12-01"))
             | ((s1.firm == "NATURGY") & (s1.date < "2019-07-18")))
    rows.append(iv(s1[~early], "pc", "without static-X misfits", "spec 1"))
    rows.append(iv(full[~full.eff_is_generic], "pc", "with minimum-load gaps", "spec 1"))
    print("\nSPEC 2, heat rate estimated (all units)")
    rows.append(iv(d, "p", "pooled", "spec 2", heat=True))
    print("\nROUTE 3, declared variable term (declaring units, to 2025-03-18)")
    rows.append(iv(d[d.var_term > 0], "pv", "pooled", "route 3"))
    print("\nTHE MARKDOWN IN LEVELS (spec 1 sample)")
    rows += markdown(s1)
    print("  ... and at minimum-load gaps (excluded from the headline)")
    gap = full[~full.eff_is_generic & full.min_load]
    rows += [r | {"sample": "markdown table, minimum-load gaps"} for r in markdown(gap)]
    print(f"\nspec 1 sample: {len(s1):,} unit-periods on {s1.unit.nunique()} units "
          f"(generic-efficiency units excluded: {d[d.eff_is_generic].unit.nunique()}; "
          f"minimum-load gaps excluded: {int(full.min_load.sum()):,} unit-periods)")
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if rows[0].get("status") in ("ok", "weak") else 1


if __name__ == "__main__":
    raise SystemExit(main())
