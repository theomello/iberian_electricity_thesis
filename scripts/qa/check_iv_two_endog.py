#!/usr/bin/env python3
"""The two-endogenous-regressor IV estimator recovers known coefficients on simulated data.

    .venv/bin/python scripts/qa/check_iv_two_endog.py

Framework spec §4, leg D. The data mimic the design: a firm is a seller (s = 1)
or a buyer, X's sign follows s, rivals' solar z moves X with a sign that
depends on s, and an unobserved shock v enters both X and y (so OLS is biased).
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from iv_two_endog import (ar_common_exact, ar_common_set, ar_projection, ar_test,  # noqa: E402
                          fmt_intervals, fmt_set, sw_f, tsls_k)
from midday_hydro_iv import ols, tsls  # noqa: E402

GRID = np.round(np.arange(-3.0, 3.0001, 0.005), 4)


def dgp(gp, gm, seed, n=20000, groups=400, share_seller=0.5):
    r = np.random.default_rng(seed)
    cl = r.integers(0, groups, n)
    s = (r.random(n) < share_seller).astype(float)
    z, w, v = r.normal(size=n), r.normal(size=n), r.normal(size=n)
    x = np.where(s == 1, 2.0, -2.0) + z * np.where(s == 1, 1.0, -0.8) + 0.3 * w + v
    xp, xm = np.maximum(x, 0), np.minimum(x, 0)
    y = gp * xp + gm * xm + 0.2 * w + 0.7 * v + r.normal(size=n)
    return y, np.column_stack([xp, xm]), np.column_stack([z, z * s]), w[:, None], cl


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    for name, truth in (("asymmetric", (-0.5, 0.5)), ("symmetric", (-0.5, -0.5))):
        y, X, Z, W, cl = dgp(*truth, seed=11)
        b, V = tsls_k(y, X, Z, W, cl)
        se = np.sqrt(np.diag(V))
        dev = np.abs(b - truth) / se
        print(f"{name}: b {b.round(3)} se {se.round(3)}")
        check(bool((dev < 3).all()), f"{name}: 2SLS within 3 se of {truth}")
        check(min(sw_f(X, Z, W, cl, 0), sw_f(X, Z, W, cl, 1)) > 100, f"{name}: strong first stages")
        check(ar_test(y, X, Z, W, cl, truth)[1] > 0.05, f"{name}: AR does not reject the truth")
        check(ar_test(y, X, Z, W, cl, [0.0, 0.0])[1] < 1e-6, f"{name}: AR rejects (0, 0)")
        keep = ar_common_set(y, X, Z, W, cl, GRID)
        print(f"  common-slope set {fmt_set(keep, GRID)}")
        if name == "asymmetric":
            check(len(keep) == 0, "asymmetric: no common slope fits")
        else:
            check(len(keep) > 0 and keep.min() <= -0.5 <= keep.max(), "symmetric: set covers -0.5")

    # Exact common-slope set (L = 2): no grid, so a narrow set cannot fall between points.
    y, X, Z, W, cl = dgp(-0.5, -0.5, seed=11)
    ex = ar_common_exact(y, X, Z, W, cl)
    print(f"symmetric, exact common set {fmt_intervals(ex['intervals'])}, "
          f"min AR p {ex['p_min']:.3f} at {ex['c_min']:+.4f}")
    iv = ex["intervals"]
    check(len(iv) == 1 and iv[0][0] < -0.5 < iv[0][1], "symmetric: exact set is one interval around -0.5")
    grid_keep = ar_common_set(y, X, Z, W, cl, GRID)
    check(abs(iv[0][0] - grid_keep.min()) < 0.006 and abs(iv[0][1] - grid_keep.max()) < 0.006,
          "symmetric: exact endpoints agree with the grid set")
    for c in iv[0]:
        p_end = ar_test(y, X, Z, W, cl, [c, c])[1]
        check(abs(p_end - 0.05) < 1e-4, f"endpoint {c:+.4f}: AR p = 0.05 ({p_end:.5f})")
    coarse = np.array([-0.55, -0.45])
    check(ar_common_set(y, X, Z, W, cl, coarse).size == 0,
          "a coarse grid misses the set (the artefact the exact version removes)")
    y, X, Z, W, cl = dgp(-0.5, 0.5, seed=11)
    ex = ar_common_exact(y, X, Z, W, cl)
    check(ex["intervals"] == [] and ex["p_min"] < 0.05, "asymmetric: exact set empty, min AR p < 0.05")
    pm = ar_projection(y, X, Z, W, cl, 1, GRID)
    pp = ar_projection(y, X, Z, W, cl, 0, GRID)
    print(f"asymmetric, AR projection: g+ {fmt_set(pp, GRID)}, g- {fmt_set(pm, GRID)}")
    check(len(pm) > 0 and pm.min() > 0 and pm.min() < 0.5 < pm.max(), "projection: g- set positive, covers 0.5")
    check(len(pp) > 0 and pp.max() < 0 and pp.min() < -0.5 < pp.max(), "projection: g+ set negative, covers -0.5")

    y, X, Z, W, cl = dgp(-0.5, -0.5, seed=3)
    x1 = X.sum(axis=1)
    b1, V1 = tsls_k(y, x1[:, None], Z[:, :1], W, cl)
    b0, se0 = tsls(y, x1, Z[:, 0], W, cl)
    check(abs(b1[0] - b0) < 1e-10 and abs(np.sqrt(V1[0, 0]) - se0) < 1e-10,
          "one regressor: tsls_k equals midday_hydro_iv.tsls")
    bf, sef = ols(x1, np.column_stack([Z[:, 0], W]), cl)
    check(abs(sw_f(x1[:, None], Z[:, :1], W, cl, 0) - (bf[0] / sef[0]) ** 2) < 1e-8,
          "one regressor: sw_f equals the first-stage F")

    y, X, Z, W, cl = dgp(-0.5, -0.5, seed=5, share_seller=0.0)
    b, _ = tsls_k(y, X, Z, W, cl)
    check(bool(np.isnan(b).all()), "never a seller: tsls_k returns NaN, not an error")
    check(bool(np.isnan(sw_f(X, Z, W, cl, 0))), "never a seller: sw_f returns NaN")
    check(bool(np.isnan(ar_test(y, X, Z, W, cl, [0.0, 0.0])[1])), "never a seller: ar_test NaN")
    check(ar_common_set(y, X, Z, W, cl, GRID).size == 0, "never a seller: empty common set")
    check(ar_common_exact(y, X, Z, W, cl) is None, "never a seller: exact set is None (not identified)")

    y, X, Z, W, cl = dgp(-0.5, -0.5, seed=5, share_seller=0.02)
    fp, fm = sw_f(X, Z, W, cl, 0), sw_f(X, Z, W, cl, 1)
    print(f"rarely a seller: SW F {fp:.1f} / {fm:.1f}")
    check(fp < fm, "rarely a seller: X+ has the weaker first stage")

    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
