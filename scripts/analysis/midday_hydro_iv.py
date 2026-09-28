#!/usr/bin/env python3
"""Second stage: does EDP's storage hydro price at its markup term, or at its water value?

    .venv/bin/python scripts/build/build_solar_instrument.py   # input
    .venv/bin/python scripts/analysis/edp_hydro_panel.py       # input
    .venv/bin/python scripts/analysis/midday_hydro_iv.py

Step 5b of `notes/rq-midday-hydro.md`, §3.11 there.

THE TEST OF RECORD: THE POSITION OF THE OFFER CURVE

With a daily water value lambda, the Hortacsu-Puller first-order condition
says the unit's offer curve sits at

    b_t(fixed point) = lambda_{unit,day} + beta * X_t,    X = net auction position / |RD'_firm|

The unit-day fixed effect absorbs lambda. beta = 0 is price-taking (the curve
does not move within the day); beta = 1 is supply-function Nash. The outcome
is the price at a FIXED point on the unit's curve -- 25/50/75% of offered
volume (`o25`...), or of capacity (`p25_cap`...) -- over all EDP unit-periods.
Demand cutting the curve somewhere else cannot move it, and nothing is
conditioned on. X is instrumented with `z_offered`, the day-ahead solar volume
offered by non-EDP solar units (`solar_first_stage.py`).

    fixed effects   unit-day + hour x YEAR-month
    control         REE day-ahead demand forecast (sunny days are hot)
    errors          clustered on date

REPORTED: OLS for comparison; the reduced form and first-stage F; 2SLS beta;
and an Anderson-Rubin 95% set in closed form (valid however weak the
instrument), checked once against grid inversion.

THE p* VERSION IS REPORTED AND IS INVALID

The first design used the periods where an EDP unit SETS the price, where its
offer is p*. It returns beta = 3.6 -- outside [0, 1], so the specification is
broken, not the market. Two reasons, both checked below: (1) SELECTION -- the
sample keeps only price-setting periods, and the solar instrument changes which
periods those are, so it conditions on an outcome of the instrument; (2)
movement along the unit's own stepped curve, which is real (solar lowers the
marginal unit's quantity, and p* rises with it) but explains only ~5% of the
reduced form. It is kept so the failure stays on the record.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from solar_first_stage import demean, load_edp_sample, price_setting  # noqa: E402

GRID = np.round(np.arange(-3.0, 4.0001, 0.01), 4)
CRIT = 1.959964


def cluster_meat(M: np.ndarray, e: np.ndarray, cl: np.ndarray) -> np.ndarray:
    order = np.argsort(cl, kind="stable")
    cl_s, M_s, e_s = cl[order], M[order], e[order]
    bounds = np.flatnonzero(np.r_[True, cl_s[1:] != cl_s[:-1], True])
    s = np.zeros((M.shape[1], M.shape[1]))
    for a, z in zip(bounds[:-1], bounds[1:]):
        g = M_s[a:z].T @ e_s[a:z]
        s += np.outer(g, g)
    return s


def ols(y, M, cl):
    inv = np.linalg.inv(M.T @ M)
    b = inv @ M.T @ y
    V = inv @ cluster_meat(M, y - M @ b, cl) @ inv
    return b, np.sqrt(np.diag(V))


def tsls(y, x, z, w, cl):
    """Just-identified 2SLS of y on x (endogenous) and w (exogenous), instrument z."""
    Z = np.column_stack([z, w])
    Xf = np.column_stack([x, w])
    Xhat = Z @ np.linalg.solve(Z.T @ Z, Z.T @ Xf)
    inv = np.linalg.inv(Xhat.T @ Xf)
    b = inv @ Xhat.T @ y
    e = y - Xf @ b
    V = inv @ cluster_meat(Xhat, e, cl) @ inv.T
    return b[0], float(np.sqrt(V[0, 0]))


def ar_closed(y, x, z, w, cl) -> str:
    """Anderson-Rubin 95% set in closed form, just-identified.

    With reduced form py = pi_y and first stage px = pi_x on z, and their joint
    cluster covariance, beta = b is accepted when
        (py - b px)^2 <= c^2 (vyy - 2 b vyx + b^2 vxx),
    a quadratic in b: bounded when the instrument is strong enough (a2 > 0),
    the complement of an interval or the whole line otherwise.
    """
    Z = np.column_stack([z, w])
    A = np.linalg.inv(Z.T @ Z)
    cy, cx = A @ Z.T @ y, A @ Z.T @ x
    ey, ex = y - Z @ cy, x - Z @ cx
    order = np.argsort(cl, kind="stable")
    cl_s, Z_s, ey_s, ex_s = cl[order], Z[order], ey[order], ex[order]
    bounds = np.flatnonzero(np.r_[True, cl_s[1:] != cl_s[:-1], True])
    myy = mxx = myx = np.zeros((Z.shape[1], Z.shape[1]))
    for a, b in zip(bounds[:-1], bounds[1:]):
        gy, gx = Z_s[a:b].T @ ey_s[a:b], Z_s[a:b].T @ ex_s[a:b]
        myy = myy + np.outer(gy, gy); mxx = mxx + np.outer(gx, gx); myx = myx + np.outer(gy, gx)
    vyy, vxx, vyx = (A @ myy @ A)[0, 0], (A @ mxx @ A)[0, 0], (A @ myx @ A)[0, 0]
    py, px, c2 = cy[0], cx[0], CRIT ** 2
    a2, a1, a0 = px ** 2 - c2 * vxx, -2 * (py * px - c2 * vyx), py ** 2 - c2 * vyy
    disc = a1 ** 2 - 4 * a2 * a0
    if a2 > 0:
        if disc < 0:
            return "empty"
        r = sorted([(-a1 - np.sqrt(disc)) / (2 * a2), (-a1 + np.sqrt(disc)) / (2 * a2)])
        return f"[{r[0]:.2f}, {r[1]:.2f}]"
    if disc < 0:
        return "(-inf, +inf)"
    r = sorted([(-a1 - np.sqrt(disc)) / (2 * a2), (-a1 + np.sqrt(disc)) / (2 * a2)])
    return f"(-inf, {r[0]:.2f}] U [{r[1]:.2f}, +inf)"


def ar_set(y, x, z, w, cl) -> str:
    """Anderson-Rubin 95% set by grid inversion -- kept to validate ar_closed."""
    Z = np.column_stack([z, w])
    inv = np.linalg.inv(Z.T @ Z)
    keep = []
    for b0 in GRID:
        yt = y - b0 * x
        c = inv @ Z.T @ yt
        V = inv @ cluster_meat(Z, yt - Z @ c, cl) @ inv
        if abs(c[0]) / np.sqrt(V[0, 0]) < CRIT:
            keep.append(b0)
    if not keep:
        return "empty"
    keep = np.array(keep)
    gaps = np.flatnonzero(np.diff(keep) > 0.0101)
    lo_open = keep[0] <= GRID[0]
    hi_open = keep[-1] >= GRID[-1]
    pieces = np.split(keep, gaps + 1)
    txt = " U ".join(f"[{'-inf' if (lo_open and i == 0) else f'{p[0]:.2f}'}, "
                     f"{'+inf' if (hi_open and i == len(pieces) - 1) else f'{p[-1]:.2f}'}]"
                     for i, p in enumerate(pieces))
    return txt


def run(df: pd.DataFrame, y: str, z: str, fes: list[str], label: str) -> None:
    cols = [y, "X", z, "fcst"]
    d = df.dropna(subset=cols)
    if len(d) < 200:
        print(f"  {label:38s} too few ({len(d)})")
        return
    w = demean(d, cols, fes)
    cl = d["date"].to_numpy().astype("datetime64[D]").astype(np.int64)
    Y, X, Z, W = (w[c].to_numpy() for c in cols)
    b_ols, se_ols = ols(Y, np.column_stack([X, W]), cl)
    b_fs, se_fs = ols(X, np.column_stack([Z, W]), cl)
    b_rf, se_rf = ols(Y, np.column_stack([Z, W]), cl)
    F = (b_fs[0] / se_fs[0]) ** 2
    b, se = tsls(Y, X, Z, W, cl)
    ar = ar_closed(Y, X, Z, W, cl)
    print(f"  {label:38s} n={len(d):>7,}  OLS {b_ols[0]:+.3f} ({se_ols[0]:.3f})  "
          f"RF {b_rf[0]*1000:+.2f}/GW (t {b_rf[0]/se_rf[0]:+.1f})  F {F:6.1f}  "
          f"2SLS {b:+.3f} ({se:.3f})  AR95 {ar}")


def validate_ar(df: pd.DataFrame, fes: list[str]) -> None:
    cols = ["p_zone", "X", "z_offered", "fcst"]
    d = df.dropna(subset=cols)
    w = demean(d, cols, fes)
    cl = d["date"].to_numpy().astype("datetime64[D]").astype(np.int64)
    Y, X, Z, W = (w[c].to_numpy() for c in cols)
    print(f"  AR check on the pooled price-setting run: grid {ar_set(Y, X, Z, W, cl)}, "
          f"closed form {ar_closed(Y, X, Z, W, cl)}\n")


def main() -> int:
    p = load_edp_sample(panel_cols=("p_zone", "o25", "o50", "o75", "p25_cap", "p50_cap",
                                    "p75_cap", "cleared_mw", "offered_mw", "cap"))
    hym, hm = ["ud", "hym"], ["ud", "hm"]

    print("SECOND STAGE -- beta = 0 price-taking, 1 supply-function Nash.")
    print("FE unit-day + hour x year-month; control: demand forecast; SE clustered on date.")
    print("OLS and 2SLS: coefficient (se). RF: reduced form, EUR/MWh per GW of the instrument.\n")

    print("THE TEST: position of EDP's offer curve at fixed points, all unit-periods")
    for y in ("o25", "o50", "o75", "p25_cap", "p50_cap", "p75_cap"):
        run(p.dropna(subset=[y]), y, "z_offered", hym, f"{y}, pooled")
    for y in ("o50", "o75"):
        d = p.dropna(subset=[y])
        for era, g in d.groupby("era", observed=True):
            run(g, y, "z_offered", hym, f"{y}, {era}")
        run(d, y, "z_offered_indep", hym, f"{y}, pooled, z_offered_indep")
        run(d, y, "z_offered", hm, f"{y}, pooled, hour x calendar-month FE")

    # Composition: if the volume EDP offers moved with solar, the o-points would
    # move along the curve without the curve moving.
    p["off_share"] = p.offered_mw / p.cap
    d = p.dropna(subset=["off_share", "z_offered", "fcst"])
    w = demean(d, ["off_share", "z_offered", "fcst"], hym)
    cl = d["date"].to_numpy().astype("datetime64[D]").astype(np.int64)
    b, se = ols(w.off_share.to_numpy(), np.column_stack([w.z_offered, w.fcst]), cl)
    print(f"  composition: offered MW / capacity on z_offered {b[0]*1000:+.4f} per GW "
          f"(t {b[0]/se[0]:+.1f})")

    print("\nFOR THE RECORD: p* in EDP's price-setting periods -- INVALID, see docstring")
    mg = price_setting(p)
    validate_ar(mg, hym)
    run(mg, "p_zone", "z_offered", hym, "pooled, z_offered")
    for era, g in mg.groupby("era", observed=True):
        run(g, "p_zone", "z_offered", hym, f"{era}, z_offered")
    for y, x in (("cleared_mw", "z_offered"), ("p_zone", "cleared_mw")):
        d = mg.dropna(subset=[y, x, "fcst"])
        w = demean(d, [y, x, "fcst"], hym)
        cl = d["date"].to_numpy().astype("datetime64[D]").astype(np.int64)
        b, se = ols(w[y].to_numpy(), np.column_stack([w[x], w["fcst"]]), cl)
        unit = "MW per GW" if x == "z_offered" else "EUR/MWh per MW"
        scale = 1000 if x == "z_offered" else 1
        print(f"  mechanism: {y} on {x}: {b[0]*scale:+.4f} {unit} (t {b[0]/se[0]:+.1f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
