#!/usr/bin/env python3
"""2SLS with several endogenous regressors, and weak-instrument-robust tests.

Leg D of the framework spec (§4) instruments Xp = max(X, 0) and Xm = min(X, 0)
with rivals' offered solar z and z * s_prev. `midday_hydro_iv.py` handles one
endogenous regressor; this generalises it. Inputs are already demeaned of the
fixed effects (`solar_first_stage.demean`); W holds the remaining controls.

    tsls_k(y, X, Z, W, cl)               coefficients on X and their cluster covariance
    sw_f(X, Z, W, cl, j)                 Sanderson-Windmeijer conditional F for X[:, j]
    ar_test(y, X, Z, W, cl, g)           Anderson-Rubin Wald and p for H0: coefficients = g
    ar_common_set(y, X, Z, W, cl, grid)  grid values c with H0 "every coefficient = c" kept
    fmt_set(keep, grid)                  an accepted set as text

Cluster-robust throughout (`midday_hydro_iv.cluster_meat`), no small-sample
correction. When the instruments cannot separate the regressors -- a zero
column, or a firm that is never a seller -- the functions return NaN (or an
empty set) instead of raising. `scripts/qa/check_iv_two_endog.py` tests them on
simulated data.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from midday_hydro_iv import cluster_meat  # noqa: E402

RANK_TOL = 1e-8



def _full_rank(M):
    """Columns of M linearly independent, judged on the scale-free Gram matrix."""
    G = M.T @ M
    d = np.sqrt(np.diag(G))
    if (d == 0).any():
        return False
    return np.linalg.eigvalsh(G / np.outer(d, d)).min() > RANK_TOL


def _ols_cov(y, M, cl):
    inv = np.linalg.inv(M.T @ M)
    b = inv @ M.T @ y
    return b, inv @ cluster_meat(M, y - M @ b, cl) @ inv


def _separable(Xhat_k, W):
    """The instrumented regressors vary independently once W is partialled out."""
    R = Xhat_k - W @ np.linalg.lstsq(W, Xhat_k, rcond=None)[0]
    sd = R.std(axis=0)
    if (sd <= RANK_TOL * (1 + np.abs(Xhat_k).std(axis=0))).any():
        return False
    if R.shape[1] == 1:
        return True
    return np.linalg.eigvalsh(np.corrcoef(R, rowvar=False)).min() > RANK_TOL


def tsls_k(y, X, Z, W, cl):
    """2SLS of y on X (n x k, endogenous) and W (exogenous), instruments Z (n x L, L >= k).

    Returns (b, V): the k coefficients on X and their cluster covariance, or NaN
    arrays when the instruments cannot separate the regressors.
    """
    k = X.shape[1]
    Zf, Xf = np.column_stack([Z, W]), np.column_stack([X, W])
    if not _full_rank(Zf):
        return np.full(k, np.nan), np.full((k, k), np.nan)
    Xhat = Zf @ np.linalg.lstsq(Zf, Xf, rcond=None)[0]
    if not _separable(Xhat[:, :k], np.atleast_2d(W.T).T):
        return np.full(k, np.nan), np.full((k, k), np.nan)
    inv = np.linalg.inv(Xhat.T @ Xf)
    b = inv @ Xhat.T @ y
    V = inv @ cluster_meat(Xhat, y - Xf @ b, cl) @ inv.T
    return b[:k], V[:k, :k]


def sw_f(X, Z, W, cl, j):
    """Sanderson-Windmeijer (2016) conditional first-stage F for X[:, j].

    X[:, j] is regressed by 2SLS on the other endogenous regressors; the residual
    is regressed on Z and W, and the cluster Wald statistic on Z is divided by
    L - k + 1. With k = 1 it is the ordinary first-stage F.
    """
    k, L = X.shape[1], Z.shape[1]
    if not _full_rank(np.column_stack([Z, W])):
        return float("nan")
    u = X[:, j]
    if k > 1:
        d, _ = tsls_k(u, np.delete(X, j, axis=1), Z, W, cl)
        if np.isnan(d).any():
            return float("nan")
        u = u - np.delete(X, j, axis=1) @ d
    b, V = _ols_cov(u, np.column_stack([Z, W]), cl)
    bz, Vz = b[:L], V[:L, :L]
    return float(bz @ np.linalg.solve(Vz, bz)) / (L - k + 1)


def ar_test(y, X, Z, W, cl, g):
    """Anderson-Rubin: (Wald statistic, p-value) for H0 that the coefficients on X equal g."""
    L = Z.shape[1]
    if not _full_rank(np.column_stack([Z, W])):
        return float("nan"), float("nan")
    b, V = _ols_cov(y - X @ np.asarray(g, float), np.column_stack([Z, W]), cl)
    bz, Vz = b[:L], V[:L, :L]
    stat = float(bz @ np.linalg.solve(Vz, bz))
    return stat, float(stats.chi2.sf(stat, L))


def ar_common_set(y, X, Z, W, cl, grid):
    """Grid values c for which H0 "every coefficient on X equals c" is not rejected at 5%.

    Under that H0 the model is y = c * X.sum(1) + W w + e, so the AR statistic is
    a ratio of quadratics in c, built from moments once. An EMPTY set rejects a
    common slope at every value: the weak-instrument-robust test of symmetry.
    """
    L = Z.shape[1]
    M = np.column_stack([Z, W])
    if not _full_rank(M):
        return np.array([])
    A = np.linalg.inv(M.T @ M)
    xs = X.sum(axis=1)
    cy, cx = A @ M.T @ y, A @ M.T @ xs
    ey, ex = y - M @ cy, xs - M @ cx
    order = np.argsort(cl, kind="stable")
    cl_s, M_s, ey_s, ex_s = cl[order], M[order], ey[order], ex[order]
    bounds = np.flatnonzero(np.r_[True, cl_s[1:] != cl_s[:-1], True])
    p = M.shape[1]
    myy, mxx, myx = np.zeros((p, p)), np.zeros((p, p)), np.zeros((p, p))
    for a, z in zip(bounds[:-1], bounds[1:]):
        gy, gx = M_s[a:z].T @ ey_s[a:z], M_s[a:z].T @ ex_s[a:z]
        myy += np.outer(gy, gy); mxx += np.outer(gx, gx); myx += np.outer(gy, gx)
    Vyy, Vxx, Vyx = ((A @ m @ A)[:L, :L] for m in (myy, mxx, myx))
    crit = stats.chi2.ppf(0.95, L)
    keep = []
    for c in grid:
        bz = cy[:L] - c * cx[:L]
        V = Vyy - c * (Vyx + Vyx.T) + c * c * Vxx
        if bz @ np.linalg.solve(V, bz) <= crit:
            keep.append(c)
    return np.array(keep)


def fmt_set(keep, grid):
    """Accepted grid points as intervals; an interval touching the grid's edge is open."""
    if len(keep) == 0:
        return "empty"
    step = grid[1] - grid[0]
    gaps = np.flatnonzero(np.diff(keep) > 1.5 * step)
    pieces = np.split(keep, gaps + 1)
    lo, hi = grid[0], grid[-1]
    return " U ".join(f"[{'-inf' if p[0] <= lo else f'{p[0]:.3f}'}, "
                      f"{'+inf' if p[-1] >= hi else f'{p[-1]:.3f}'}]" for p in pieces)
