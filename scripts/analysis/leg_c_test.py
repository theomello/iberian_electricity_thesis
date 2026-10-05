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
+-0.20. Otherwise specification 1 is not trusted. The check has no power against an
error in one unit's efficiency: fuel_index is the same gas index for every gas unit on a
day, so h_u is the price's pass-through of that index, and the rule scores about the same
with the efficiencies permuted across units (printed beside it). It tests the gas cost
LEVEL. Coal units go through the same recovery and are printed, not validated.

DIAGNOSTICS (Task 4 review). p rarely sits on the unit's own step: it sits inside a gap
of the unit's step curve, above its highest cleared offer (top), so p - c = (p - top) +
(top - c) and beta splits exactly into the two. Rows where the unit's own step is at p
(p - top <= 0.5) are where the condition binds on the unit's own offer; they are
selected on p, so they are diagnostic only. Also: each instrument alone, by year, unit +
year-month effects, and X's slope floor and its two parts (n and the slope).

WHY BETA EXCEEDS 1 (2026-10-05). The reduced forms are printed for the five firms and for
the other owners. The other owners' X does not move with rivals' renewables, yet their
p - c falls as much as the five firms': c is the unit's own cost, the price is set by
another unit, and more renewables move the price down the merit order for every unit.
The condition attributes that movement to X. With n alone moving, beta is rivals' slope
over the firm's own response dn/dp, which is printed beside it.

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
from iv_two_endog import ar_set_k1, ar_set_one, ar_test, fmt_intervals, sw_f, tsls_k  # noqa: E402
from midday_hydro_iv import ols  # noqa: E402
from solar_first_stage import demean  # noqa: E402

PANEL = ROOT / "outputs/tables/leg_c_panel.parquet"
OUT = ROOT / "outputs/tables/leg_c_results.csv"
MIN_ROWS = 500
MIN_UNIT = 200
WEAK_F = 10.0
FIVE = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")
MIN_SLOPE = 5.0          # leg_c_panel's floor on rivals' slope, MW per EUR/MWh
OWN_STEP = 0.5           # p within this of the unit's top cleared step: its own step is at p


def iv(d: pd.DataFrame, y: str, label: str, spec: str, heat: bool = False, x: str = "X",
       z: tuple = ("zw", "zs"), fes: tuple = ("unit",)) -> dict:
    """2SLS of y on x with unit effects (and unit-specific fuel_index slopes when heat)."""
    z = list(z)
    d = d.dropna(subset=[y, x, *z])
    d = d[np.isfinite(d[[y, x, *z]]).all(axis=1)].copy()
    if heat:
        # A unit with too few rows, or a fuel cost that never moves, has no estimable h_u,
        # and its all-zero column would void the whole specification.
        g = d.groupby("unit").fuel_index
        keep = (g.transform("size") >= MIN_UNIT) & (g.transform("nunique") >= 2)
        if (~keep).any():
            print(f"  spec 2 drops {d.loc[~keep, 'unit'].nunique()} units ({(~keep).sum()} rows) "
                  f"with < {MIN_UNIT} rows or a constant fuel cost")
        d = d[keep].copy()
    row = {"sample": label, "spec": spec, "n": len(d), "units": d.unit.nunique(), "weeks": d.wk.nunique(),
           "instruments": "+".join(z), "effects": " + ".join(fes)}
    if len(d) < MIN_ROWS:
        print(f"  {label:28s} {spec:8s} too few ({len(d)})")
        return row | {"status": "too few"}
    hcols = []
    if heat:
        for u in sorted(d.unit.unique()):
            c = f"h_{u}"
            d[c] = d.fuel_index.where(d.unit == u, 0.0)
            hcols.append(c)
    w = demean(d, [y, x, *z, *hcols], list(fes))
    Y, X, Z = w[y].to_numpy(), w[[x]].to_numpy(), w[z].to_numpy()
    W = w[hcols].to_numpy() if hcols else np.zeros((len(w), 0))
    cl = d.wk.to_numpy()
    b, V = tsls_k(Y, X, Z, W, cl)
    if np.isnan(b).any():
        print(f"  {label:28s} {spec:8s} not identified")
        return row | {"status": "not identified"}
    f1 = sw_f(X, Z, W, cl, 0)
    _, p0 = ar_test(Y, X, Z, W, cl, [0.0])
    _, p1 = ar_test(Y, X, Z, W, cl, [1.0])
    if len(z) == 2:
        s = ar_set_k1(Y, X[:, 0], Z, W, cl)
        s_iv, p_min = s["intervals"], s["p_min"]
    else:
        s_iv, p_min = ar_set_one(Y, X[:, 0], Z, W, cl), np.nan
    row |= {"status": "weak" if f1 < WEAK_F else "ok", "beta": b[0], "se": np.sqrt(V[0, 0]),
            "first_stage_f": f1, "ar_p_beta0": p0, "ar_p_beta1": p1,
            "ar_set": fmt_intervals(s_iv), "ar_set_p_min": p_min}
    extra = ""
    if heat:
        h = np.linalg.lstsq(W, Y - X[:, 0] * b[0], rcond=None)[0]
        eff = d.groupby("unit").eff.first()
        gen = d.groupby("unit").eff_is_generic.first()
        fuel = d.groupby("unit").fuel.first()
        nrow = d.groupby("unit").size()
        ok_u = [u for u in sorted(d.unit.unique())
                if fuel[u] == "gas" and not gen[u] and nrow[u] >= MIN_UNIT]
        hu = pd.Series(h, index=sorted(d.unit.unique()))
        r = (hu * eff)[ok_u]
        med = float(r.median()) if len(r) else np.nan
        share = float((r.sub(1).abs() <= 0.20).mean()) if len(r) else np.nan
        valid = bool(len(r) > 0 and 0.85 <= med <= 1.15 and share >= 0.5)
        # The same rule with the efficiencies shuffled across the units: if it scores as
        # well, the check cannot see an error in any one unit's efficiency.
        rng = np.random.default_rng(0)
        perm = float(np.median([(hu[ok_u] * rng.permutation(eff[ok_u].to_numpy())).sub(1).abs().le(0.20).mean()
                                for _ in range(200)])) if len(r) else np.nan
        coal_u = [u for u in hu.index if fuel[u] == "coal" and not gen[u] and nrow[u] >= MIN_UNIT]
        rc = (hu * eff)[coal_u]
        med_c = float(rc.median()) if len(rc) else np.nan
        row |= {"h_eff_median": med, "h_eff_share_20": share, "h_units": len(r), "validated": valid,
                "h_eff_share_20_permuted": perm, "h_eff_median_coal": med_c, "h_units_coal": len(rc),
                "h_eff_share_20_coal": float((rc.sub(1).abs() <= 0.20).mean()) if len(rc) else np.nan}
        extra = (f"  h*eff median {med:.3f}, within 20% {share:.2f} of {len(r)} gas units -> "
                 f"{'VALIDATED' if valid else 'NOT validated'} (gas cost level only: permuted efficiencies "
                 f"{perm:.2f}); coal, not validated: median {med_c:.3f} of {len(rc)} units")
    flag = "  WEAK" if f1 < WEAK_F else ""
    print(f"  {label:28s} {spec:8s} n={len(d):>8,} beta {b[0]:+.3f} ({np.sqrt(V[0, 0]):.3f})  F {f1:.1f}  "
          f"AR p(beta=0) {p0:.3f} p(beta=1) {p1:.3f}  AR set {row['ar_set']}{flag}{extra}")
    return row


def x_parts(d: pd.DataFrame) -> pd.DataFrame:
    """The rows with X's two parts: the exposed net position n and rivals' slope."""
    x = pd.read_parquet(ROOT / "outputs/tables/firm_incentive_net.parquet",
                        columns=["date", "period", "firm", "net_exp_mw",
                                 *[f"slope_exp_h{h}" for h in (1, 2, 5, 10)]],
                        filters=[("firm", "in", sorted(d.firm.unique())), ("year", ">=", 2018),
                                 ("year", "<=", 2023)])
    x["date"] = pd.to_datetime(x.date).astype("datetime64[us]")
    out = d.assign(date=d.date.astype("datetime64[us]")).merge(
        x, on=["date", "period", "firm"], how="left", validate="m:1")
    gap = float((out.net_exp_mw / out.slope_exp_h5 - out.X).abs().max())
    assert gap < 1e-9 and (out.slope_exp_h5 >= MIN_SLOPE).all(), f"X is not n / slope (max |diff| {gap})"
    return out


def diagnostics(d: pd.DataFrame, s1: pd.DataFrame) -> list[dict]:
    """The Task 4 review's checks: where p sits, and what identifies beta."""
    rows = []
    s1 = s1.assign(p_top=s1.p - s1.top_cleared_eur, top_c=s1.top_cleared_eur - s1.c)
    print(f"  p within 0.005 of the unit's top cleared step: {(s1.p_top.abs() <= 0.005).mean():.4f} of rows; "
          f"median p - top {s1.p_top.median():.2f}, top - c {s1.top_c.median():.2f} EUR/MWh")
    print("  p - c = (p - top) + (top - c), so beta splits exactly:")
    rows.append(iv(s1, "p_top", "pooled: p - own top step", "spec 1"))
    rows.append(iv(s1, "top_c", "pooled: own top step - c", "spec 1"))
    own = s1[s1.p_top <= OWN_STEP]
    print(f"  the unit's own step at p (p - top <= {OWN_STEP}), selected on p:")
    rows.append(iv(own, "pc", "own step at p (selected on p)", "spec 1"))
    r = iv(own, "pc", "own step at p, solar alone (selected on p)", "spec 1", z=("zs",))
    # In levels: what the unit effects absorb at that beta, and p - c by the sign of X.
    a_u = (own.pc - r["beta"] * own.X).groupby(own.unit).mean()
    q = a_u.quantile([0.25, 0.5, 0.75])
    r |= {"own_step_unit_effect_median": float(q[0.5]), "own_step_unit_effect_p25": float(q[0.25]),
          "own_step_unit_effect_p75": float(q[0.75])}
    rows.append(r)
    print(f"    in levels: unit effects at beta {r['beta']:.3f} have median {q[0.5]:+.2f} EUR/MWh "
          f"(IQR {q[0.25]:+.2f} to {q[0.75]:+.2f}, {len(a_u)} units)")
    for lab, g in (("X < 0", own[own.X < 0]), ("X > 0", own[own.X > 0])):
        print(f"    {lab}: n={len(g):,}  median X {g.X.median():+.2f}  median p - c {g.pc.median():+.2f}")
    print("  each instrument alone:")
    for z, lab in ((("zw",), "wind alone"), (("zs",), "solar alone")):
        rows.append(iv(s1, "pc", f"pooled, {lab}", "spec 1", z=z))
        rows.append(iv(s1[s1.fuel == "coal"], "pc", f"coal, {lab}", "spec 1", z=z))
        rows.append(iv(d[d.var_term > 0], "pv", f"pooled, {lab}", "route 3", z=z))
    print("  by year, and with time effects:")
    for yr in range(2018, 2024):
        rows.append(iv(s1[s1.date.dt.year == yr], "pc", str(yr), "spec 1"))
    rows.append(iv(s1.assign(ym=s1.date.dt.strftime("%Y%m")), "pc", "unit + year-month effects", "spec 1",
                   fes=("unit", "ym")))
    xp = x_parts(s1)
    xp["load"] = xp.cleared_mw / xp.offered_mw * 100
    print("  reduced forms on rivals' wind and solar, per GW (unit effects, week clusters):")
    rf = {}
    for lab, g in (("", xp), ("five firms", xp[xp.firm.isin(FIVE)]), ("other owners", xp[~xp.firm.isin(FIVE)])):
        if lab:
            print(f"   {lab}:")
        for y in ("p", "pc", "X", "net_exp_mw", "slope_exp_h5", "load"):
            w = demean(g, [y, "zw", "zs"], ["unit"])
            b, se = ols(w[y].to_numpy(), w[["zw", "zs"]].to_numpy(), g.wk.to_numpy())
            rf[lab, y] = b
            rows.append({"sample": f"reduced form{', ' + lab if lab else ''}: {y}", "spec": "spec 1", "n": len(g),
                         "rf_zw": b[0], "rf_zw_se": se[0], "rf_zs": b[1], "rf_zs_se": se[1]})
            print(f"    {y:14s} zw {b[0]:+9.3f} ({se[0]:.3f})  zs {b[1]:+9.3f} ({se[1]:.3f})")
    print(f"    median rivals' slope {xp.slope_exp_h5.median():.1f} MW per EUR/MWh: 1 GW at that slope "
          f"moves p by {1000 / xp.slope_exp_h5.median():.2f}; mean of 1000/slope {(1000 / xp.slope_exp_h5).mean():.2f}, "
          f"1000/mean slope {1000 / xp.slope_exp_h5.mean():.2f}")
    # With n alone moving, beta = rivals' slope over the firm's own response to the price (dn/dp): a
    # ratio of slopes. The other owners' X does not move, yet their p - c falls as much: the price
    # moves down the merit order for every unit, which the condition attributes to X.
    s_f = rf["", "net_exp_mw"] / rf["", "p"]
    print(f"    the firm's response dn/dp: zw {s_f[0]:.1f}, zs {s_f[1]:.1f} MW per EUR/MWh; median rivals' slope "
          f"over it: zw {xp.slope_exp_h5.median() / s_f[0]:.2f}, zs {xp.slope_exp_h5.median() / s_f[1]:.2f}")
    print("  X at other half-widths of rivals' slope (+-1, 2, 10 EUR/MWh):")
    for h in (1, 2, 10):
        xh = xp.assign(X_h=(xp.net_exp_mw / xp[f"slope_exp_h{h}"]).where(xp[f"slope_exp_h{h}"] >= MIN_SLOPE))
        rows.append(iv(xh, "pc", f"X at +-{h} EUR/MWh", "spec 1", x="X_h"))
    print("  X's slope floor, and its two parts:")
    for fl in (20, 50, 100):
        rows.append(iv(xp[xp.slope_exp_h5 >= fl], "pc", f"slope >= {fl}", "spec 1"))
    xp["X_n"] = xp.net_exp_mw / xp.slope_exp_h5.median()
    xp["X_slope"] = xp.groupby("firm").net_exp_mw.transform("mean") / xp.slope_exp_h5
    rows.append(iv(xp, "pc", "X = n / median slope (n moves)", "spec 1", x="X_n"))
    rows.append(iv(xp, "pc", "X = firm-mean n / slope (slope moves)", "spec 1", x="X_slope"))
    return rows


def markdown(d: pd.DataFrame) -> list[dict]:
    """p - c by the sign of X, spec 1's sample."""
    rows = []
    for sign, g in (("X < 0 (net buyer)", d[d.X < 0]), ("X > 0 (net seller)", d[d.X > 0])):
        m, top = g.p - g.c, g.top_cleared_eur - g.c
        rows.append({"sample": "markdown table", "spec": "levels", "sign": sign, "n": len(g),
                     "median_p_minus_c": float(m.median()), "share_below_cost": float((m < 0).mean()),
                     "median_X": float(g.X.median()),
                     "median_p_minus_top": float((g.p - g.top_cleared_eur).median()),
                     "median_top_minus_c": float(top.median()), "share_top_below_cost": float((top < 0).mean())})
        print(f"  {sign:22s} n={len(g):>8,}  median X {g.X.median():+.2f}  median p - c {m.median():+.2f}  "
              f"share below cost {(m < 0).mean():.3f}"
              f"  | median p - top {(g.p - g.top_cleared_eur).median():+.2f}, top - c {top.median():+.2f}, "
              f"share top below cost {(top < 0).mean():.3f}")
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
    print("\nDIAGNOSTICS (spec 1 sample unless stated)")
    rows += diagnostics(d, s1)
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
