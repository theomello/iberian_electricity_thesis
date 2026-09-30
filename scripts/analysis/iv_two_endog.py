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
    ar_common_exact(y, X, Z, W, cl)      the same set exactly (two instruments), with min AR
    ar_projection(y, X, Z, W, cl, j, grid)  values of coefficient j kept for SOME value of
                                         the other (the AR set projected: a robust sign test)
    fmt_set(keep, grid), fmt_intervals(iv)  accepted sets as text

The grid version can call a set narrower than its step "empty"; with millions of
rows the common-slope set can be that narrow, so the leg D test reads the exact
one (reviewer finding, 2026-10-01).

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
from numpy.polynomial import Polynomial as P
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


def _ar_parts(y, X, Z, W, cl):
    """Z-coefficients of y and of each column of X, and their cluster covariance blocks.

    Returns C (L x (1+k): column 0 for y, 1.. for X) and V, a (1+k) x (1+k) nested
    list of L x L blocks, so that under H0 "coefficients = g" with w = (1, -g),
    the Z-coefficients of y - Xg are C @ w with covariance sum_ab w_a w_b V[a][b].
    """
    L = Z.shape[1]
    M = np.column_stack([Z, W])
    A = np.linalg.inv(M.T @ M)
    E = np.column_stack([y, X])
    C = A @ M.T @ E
    R = E - M @ C
    order = np.argsort(cl, kind="stable")
    cl_s, M_s, R_s = cl[order], M[order], R[order]
    bounds = np.flatnonzero(np.r_[True, cl_s[1:] != cl_s[:-1], True])
    m = E.shape[1]
    S = [[np.zeros((M.shape[1], M.shape[1])) for _ in range(m)] for _ in range(m)]
    for a, z in zip(bounds[:-1], bounds[1:]):
        G = M_s[a:z].T @ R_s[a:z]
        for i in range(m):
            for j in range(m):
                S[i][j] += np.outer(G[:, i], G[:, j])
    V = [[(A @ S[i][j] @ A)[:L, :L] for j in range(m)] for i in range(m)]
    return C[:L], V


def _affine_ar(C, V, u, e):
    """With w(g) = u + g e, the AR numerator b' adj(V) b and det V(g) as polynomials in g."""
    m = len(u)
    b = [P([C[i] @ u, C[i] @ e]) for i in range(2)]
    v = [[P([sum(u[a] * u[c] * V[a][c][i, j] for a in range(m) for c in range(m)),
             sum((u[a] * e[c] + e[a] * u[c]) * V[a][c][i, j] for a in range(m) for c in range(m)),
             sum(e[a] * e[c] * V[a][c][i, j] for a in range(m) for c in range(m))])
          for j in range(2)] for i in range(2)]
    quad = b[0] * b[0] * v[1][1] - b[0] * b[1] * (v[0][1] + v[1][0]) + b[1] * b[1] * v[0][0]
    det = v[0][0] * v[1][1] - v[0][1] * v[1][0]
    return quad, det


def _real_roots(f):
    r = f.roots() if f.degree() > 0 else np.array([])
    return sorted(float(x.real) for x in r if abs(x.imag) <= 1e-9 * (1 + abs(x.real)))


def _q_min(quad, det):
    """Minimum over g of Q(g) = quad/det and where it is attained (inf if only in the limit)."""
    cands = [(float(quad(t) / det(t)), t) for t in _real_roots(quad.deriv() * det - quad * det.deriv())
             if det(t) > 0]
    if quad.degree() == det.degree() and det.coef[-1] != 0:  # the limit as |g| -> inf
        cands.append((float(quad.coef[-1] / det.coef[-1]), float("inf")))
    return min(cands) if cands else (float("nan"), float("nan"))


def ar_common_exact(y, X, Z, W, cl, level=0.95):
    """Exact AR set of the common slope c (every coefficient on X = c), two instruments.

    Accept c when b(c)' V(c)^-1 b(c) <= crit, i.e. b' adj(V) b - crit det V <= 0: a
    polynomial of degree <= 4 in c, so the set is a union of intervals between its
    real roots, possibly unbounded. Returns None when not identified, else a dict:
    intervals (list of [lo, hi], +-inf allowed; [] = no common slope fits), q_min,
    p_min (the smallest AR statistic over c and its chi2(2) p-value) and c_min.
    """
    if Z.shape[1] != 2:
        raise ValueError("ar_common_exact needs exactly two instruments")
    if not _full_rank(np.column_stack([Z, W])):
        return None
    C, V = _ar_parts(y, X.sum(axis=1)[:, None], Z, W, cl)
    quad, det = _affine_ar(C, V, np.array([1.0, 0.0]), np.array([0.0, -1.0]))
    crit = stats.chi2.ppf(level, 2)
    f = quad - crit * det
    edges = [-np.inf] + _real_roots(f) + [np.inf]
    intervals: list[list[float]] = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        if np.isinf(lo) and np.isinf(hi):
            mid = 0.0
        elif np.isinf(lo):
            mid = hi - 1.0 - abs(hi)
        elif np.isinf(hi):
            mid = lo + 1.0 + abs(lo)
        else:
            mid = (lo + hi) / 2
        if f(mid) <= 0:
            if intervals and intervals[-1][1] == lo:
                intervals[-1][1] = hi
            else:
                intervals.append([lo, hi])
    q, c = _q_min(quad, det)
    return {"intervals": intervals, "q_min": q, "p_min": float(stats.chi2.sf(q, 2)), "c_min": c}


def ar_projection(y, X, Z, W, cl, j, grid, level=0.95):
    """Grid values t of coefficient j for which SOME value of the other coefficient is kept.

    The joint AR set (k = 2, L = 2) projected onto coordinate j: for each t the
    other coefficient is profiled out exactly (the minimum of a ratio of
    polynomials), so only coefficient j is gridded. Conservative, and valid however
    weak the instruments. A set entirely above 0 is a robust positive sign.
    """
    if X.shape[1] != 2 or Z.shape[1] != 2:
        raise ValueError("ar_projection needs two regressors and two instruments")
    if not _full_rank(np.column_stack([Z, W])):
        return np.array([])
    C, V = _ar_parts(y, X, Z, W, cl)
    crit = stats.chi2.ppf(level, 2)
    o = 1 - j
    e = np.zeros(3)
    e[1 + o] = -1.0
    keep = []
    for t in grid:
        u = np.array([1.0, 0.0, 0.0])
        u[1 + j] = -t
        q, _ = _q_min(*_affine_ar(C, V, u, e))
        if q <= crit:
            keep.append(t)
    return np.array(keep)


def fmt_intervals(iv) -> str:
    """Exact intervals as text; None (not identified) and [] (nothing kept) are named."""
    if iv is None:
        return "not identified"
    if not iv:
        return "empty"
    f = lambda v: "-inf" if v == -np.inf else ("+inf" if v == np.inf else f"{v:.3f}")  # noqa: E731
    return " U ".join(f"[{f(lo)}, {f(hi)}]" for lo, hi in iv)


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
