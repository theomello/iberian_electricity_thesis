"""Regression-discontinuity tools: the jump at a cutoff and McCrary's density test.

Both put the cutoff at 0 (centre the running variable first) and use a triangular
kernel within the bandwidth h.

  rd_jump(y, r, cluster, h)   local linear on each side, weights 1 − |r|/h; tau is the
                              coefficient on 1[r ≥ 0]; errors clustered (CR1)
  mccrary(r, h, b)            McCrary (2008, J. Econometrics): histogram in bins of width
                              b, local linear on the bin heights each side, theta =
                              ln f₊ − ln f₋ with his asymptotic standard error

Used by `analysis/mic_near_miss_describe.py`; checked by `qa/check_rd.py`.
"""
from __future__ import annotations

import math

import numpy as np


def _p(z: float) -> float:
    return math.erfc(abs(z) / math.sqrt(2.0))


def rd_jump(y, r, cluster, h: float = 2.0) -> dict:
    """The jump in E[y | r] at r = 0, local linear each side, triangular kernel."""
    y, r, cluster = np.asarray(y, float), np.asarray(r, float), np.asarray(cluster)
    keep = np.isfinite(y) & np.isfinite(r) & (np.abs(r) < h)
    y, r, cluster = y[keep], r[keep], cluster[keep]
    d = (r >= 0).astype(float)
    X = np.column_stack([np.ones_like(r), r, d, d * r])
    w = 1.0 - np.abs(r) / h
    XtW = X.T * w
    A = np.linalg.inv(XtW @ X)
    beta = A @ (XtW @ y)
    e = y - X @ beta
    _, g = np.unique(cluster, return_inverse=True)
    G = g.max() + 1
    s = np.zeros((G, X.shape[1]))
    np.add.at(s, g, X * (w * e)[:, None])
    n, k = X.shape
    c = G / max(G - 1, 1) * (n - 1) / max(n - k, 1)
    V = c * A @ (s.T @ s) @ A
    tau, se = float(beta[2]), float(math.sqrt(max(V[2, 2], 0.0)))
    return {"tau": tau, "se": se, "p": _p(tau / se) if se > 0 else 0.0,
            "n_left": int((d == 0).sum()), "n_right": int((d == 1).sum()), "clusters": int(G)}


def _side(x: np.ndarray, f: np.ndarray, h: float) -> float:
    """Intercept at 0 of a triangular-kernel local linear fit of f on x."""
    w = np.maximum(0.0, 1.0 - np.abs(x) / h)
    X = np.column_stack([np.ones_like(x), x])
    XtW = X.T * w
    return float(np.linalg.solve(XtW @ X, XtW @ f)[0])


def mccrary(r, h: float = 2.0, b: float = 0.05) -> dict:
    """McCrary's test that the density of r is continuous at 0."""
    r = np.asarray(r, float)
    r = r[np.isfinite(r)]
    n = len(r)
    k = int(math.ceil(h / b))
    edges = np.arange(-k, k + 1) * b
    counts, _ = np.histogram(r, bins=edges)
    mid = (edges[:-1] + edges[1:]) / 2
    height = counts / (n * b)
    lo, hi = mid < 0, mid > 0
    f_minus, f_plus = _side(mid[lo], height[lo], h), _side(mid[hi], height[hi], h)
    theta = math.log(f_plus) - math.log(f_minus)
    se = math.sqrt((1.0 / (n * h)) * (24.0 / 5.0) * (1.0 / f_plus + 1.0 / f_minus))
    return {"theta": theta, "se": se, "z": theta / se, "p": _p(theta / se), "n": n,
            "f_minus": f_minus, "f_plus": f_plus}
