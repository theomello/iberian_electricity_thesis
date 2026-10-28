#!/usr/bin/env python3
"""Step 2 of the gas-cap design, the main estimate: pass-through of the Iberian subsidy into gas
plants' offers, against Italian gas plants, with interactive fixed effects.
(docs/specs/2026-10-28-gas-cap-conduct-design.md, "Step 2, the main estimate"; fixed before running)

    .venv/bin/python scripts/analysis/gas_cap_ife.py [--reps 199]

Weekly unit means of mmid = p_mid - cost after the subsidy, 2021-06-15 -> 2023-06-30. Dose Y_w = the
week's mean bid-time subsidy. theta is the change in the Iberian markup per EUR of subsidy: 0 if
plants bid at cost (offers fall with the cost), 1 if offers ignored the subsidy. rho = 1 - theta.

A. Bai (2009) / Gobillon & Magnac (2016): y = a_i + x_w + l_i'F_w + theta * (Iberia x Y_w) + e,
   all units, alternating least squares and principal components, EM for missing cells.
B. Xu (2017), generalised synthetic control: factors from Italian units only; each Iberian unit's
   intercept and loadings from pre-cap weeks; imputed no-cap path; theta from the weekly mean gap on
   Y_w over the binding weeks; the mean gap after 2023-02-25 as a check (no subsidy then).
Number of factors: Bai & Ng's IC_p2 on the Italian matrix (k_max 8), main; Xu's leave-one-week-out
cross-validation beside it; r = 0..5 as sensitivity. Firm block bootstrap within country.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
PANEL = ROOT / "outputs" / "tables" / "gas_cap_offer_panel.parquet"
START, END = pd.Timestamp("2021-06-15"), pd.Timestamp("2023-06-30")
CAP0, CAP1 = pd.Timestamp("2022-06-15"), pd.Timestamp("2023-02-25")
MAXMISS, KMAX = 0.30, 8


def load():
    h = pd.read_parquet(PANEL, columns=["unit", "date", "iberia", "firm", "p_mid", "cost"])
    h = h.dropna(subset=["p_mid", "cost"])
    h["m"] = h.p_mid - h.cost
    h["w"] = h.date.dt.to_period("W").dt.start_time
    W = h.groupby(["unit", "w"]).m.mean().unstack()
    W = W[W.isna().mean(axis=1) <= MAXMISS]
    meta = h.drop_duplicates("unit").set_index("unit")
    ib = meta.iberia.reindex(W.index).to_numpy()
    firm = meta.firm.fillna(pd.Series(meta.index, index=meta.index)).reindex(W.index).to_numpy()
    sub = pd.read_parquet(DATA / "jrc_ppdb" / "implied_marginal_cost_daily.parquet",
                          columns=["fuel", "date", "subsidy_bid_eur_mwh"]).query("fuel == 'gas'").drop_duplicates("date")
    sub["w"] = sub.date.dt.to_period("W").dt.start_time
    Y = sub.groupby("w").subsidy_bid_eur_mwh.mean().reindex(W.columns).fillna(0.0).to_numpy()
    return W, ib, firm, Y


def em_factor(M: np.ndarray, r: int, it: int = 300) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Two-way effects + rank-r factors on a matrix with NaNs (EM). Returns a, b, LF."""
    obs = ~np.isnan(M)
    fit = np.where(obs, M, np.nanmean(M))
    for _ in range(it):
        R = np.where(obs, M, fit)
        a = R.mean(axis=1, keepdims=True)
        b = (R - a).mean(axis=0, keepdims=True)
        E = R - a - b
        if r:
            U, s, Vt = np.linalg.svd(E, full_matrices=False)
            LF = (U[:, :r] * s[:r]) @ Vt[:r]
        else:
            LF = np.zeros_like(E)
        new = a + b + LF
        if np.nanmax(np.abs((new - fit)[~obs])) < 1e-4 if (~obs).any() else True:
            fit = new
            break
        fit = new
    return a, b, LF


def ic_p2(M: np.ndarray) -> tuple[int, list]:
    N, T = M.shape
    a, b, LF = em_factor(M, KMAX)
    R = np.where(np.isnan(M), a + b + LF, M)
    E = R - R.mean(axis=1, keepdims=True) - (R - R.mean(axis=1, keepdims=True)).mean(axis=0, keepdims=True)
    U, s, Vt = np.linalg.svd(E, full_matrices=False)
    ics = []
    for k in range(KMAX + 1):
        V = ((E - (U[:, :k] * s[:k]) @ Vt[:k]) ** 2).mean()
        ics.append(np.log(V) + k * (N + T) / (N * T) * np.log(min(N, T)))
    return int(np.argmin(ics)), ics


def bai(Y: np.ndarray, X: np.ndarray, r: int, it: int = 300) -> float:
    obs = ~np.isnan(Y)
    theta, fit = 0.0, np.where(obs, Y, np.nanmean(Y))
    for _ in range(it):
        R = np.where(obs, Y - theta * X, fit - theta * X)
        a = R.mean(axis=1, keepdims=True)
        b = (R - a).mean(axis=0, keepdims=True)
        E = R - a - b
        LF = ((lambda U, s, Vt: (U[:, :r] * s[:r]) @ Vt[:r])(*np.linalg.svd(E, full_matrices=False))
              if r else np.zeros_like(E))
        res = Y - a - b - LF
        xs = X[obs]
        new = (res[obs] @ xs) / (xs @ xs)
        fit = a + b + LF + new * X
        if abs(new - theta) < 1e-7:
            return new
        theta = new
    return theta


def gsc(W: np.ndarray, ib: np.ndarray, pre: np.ndarray, r: int):
    """Xu (2017). Returns the weekly mean gap of treated units (NaN where none observed)."""
    a, b, LF = em_factor(W[~ib], r)
    if r:
        U, s, Vt = np.linalg.svd(LF, full_matrices=False)
        F = Vt[:r].T * np.sqrt(W.shape[1])              # T x r
    else:
        F = np.zeros((W.shape[1], 0))
    xi = b.ravel()
    gaps = []
    for y in W[ib]:
        o = ~np.isnan(y) & pre
        Z = np.column_stack([np.ones(o.sum()), F[o]])
        coef = np.linalg.lstsq(Z, y[o] - xi[o], rcond=None)[0]
        y0 = xi + np.column_stack([np.ones(len(xi)), F]) @ coef
        gaps.append(y - y0)
    G = np.array(gaps)
    return np.nanmean(G, axis=0)


def xu_cv(W: np.ndarray, ib: np.ndarray, pre: np.ndarray, rmax: int = 5) -> list:
    out = []
    for r in range(rmax + 1):
        a, b, LF = em_factor(W[~ib], r)
        F = (np.linalg.svd(LF, full_matrices=False)[2][:r].T * np.sqrt(W.shape[1])) if r else np.zeros((W.shape[1], 0))
        xi = b.ravel()
        err = []
        for y in W[ib]:
            idx = np.flatnonzero(~np.isnan(y) & pre)
            Zall = np.column_stack([np.ones(len(xi)), F])
            for s_ in idx:
                keep = idx[idx != s_]
                coef = np.linalg.lstsq(Zall[keep], y[keep] - xi[keep], rcond=None)[0]
                err.append(y[s_] - xi[s_] - Zall[s_] @ coef)
        out.append(float(np.mean(np.square(err))))
    return out


def estimates(W, ib, Y, r, cols):
    X = np.outer(ib.astype(float), Y)
    tA = bai(W, X, r)
    D = np.outer(ib.astype(float), (Y > 0).astype(float))
    tAD = bai(W, D, r)
    pre = (cols < CAP0)
    att = gsc(W, ib, pre, r)
    bind = Y > 0
    after = cols > CAP1
    tB = np.nansum(att[bind] * Y[bind]) / np.sum(Y[bind] ** 2)
    return tA, tAD, tB, np.nanmean(att[bind]), np.nanmean(att[after]), att


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=199)
    a = ap.parse_args()
    Wdf, ib, firm, Y = load()
    W, cols = Wdf.to_numpy(), Wdf.columns
    pre = cols < CAP0
    print(f"{ib.sum()} Iberian and {(~ib).sum()} Italian units x {W.shape[1]} weeks; "
          f"{np.isnan(W).mean():.1%} cells missing; mean subsidy over binding weeks {Y[Y > 0].mean():.1f}")
    r_ic, ics = ic_p2(W[~ib])
    cv = xu_cv(W, ib, pre)
    print(f"IC_p2 (k=0..{KMAX}): " + ", ".join(f"{v:.3f}" for v in ics) + f"  -> r = {r_ic}")
    print("Xu CV MSPE (r=0..5): " + ", ".join(f"{v:,.0f}" for v in cv) + f"  -> r = {int(np.argmin(cv))}")
    print("\nsensitivity (point estimates):  r | A theta (per EUR) | A binary | B theta | B mean gap binding | B mean gap after")
    for r in range(0, 6):
        tA, tAD, tB, gb, ga, _ = estimates(W, ib, Y, r, cols)
        print(f"  {r}{' *' if r == r_ic else '  '} | {tA:+.3f} | {tAD:+.1f} | {tB:+.3f} | {gb:+.1f} | {ga:+.1f}")
    r = r_ic
    tA, tAD, tB, gb, ga, att = estimates(W, ib, Y, r, cols)
    rng = np.random.default_rng(20261028)
    fi = pd.Series(firm)
    groups = {c: fi[ib == c].unique() for c in (True, False)}
    draws = []
    for _ in range(a.reps):
        idx = []
        for c in (True, False):
            for f_ in rng.choice(groups[c], size=len(groups[c]), replace=True):
                idx.extend(np.flatnonzero((fi.to_numpy() == f_) & (ib == c)))
        idx = np.array(idx)
        draws.append(estimates(W[idx], ib[idx], Y, r, cols)[:5])
    dr = np.array(draws)
    names = ["A theta per EUR", "A binary (EUR)", "B theta per EUR", "B mean gap, binding (EUR)", "B mean gap, after (EUR)"]
    print(f"\nmain estimate, r = {r} (IC_p2), firm block bootstrap {a.reps} draws "
          f"({len(groups[True])} Iberian, {len(groups[False])} Italian firms):")
    for n, est, col in zip(names, (tA, tAD, tB, gb, ga), dr.T):
        lo, hi = np.nanpercentile(col, [2.5, 97.5])
        print(f"  {n:<28} {est:+8.3f}   95% [{lo:+.3f}, {hi:+.3f}]")
    print(f"  pass-through rho = 1 - theta:  A {1 - tA:.2f}, B {1 - tB:.2f}")
    out = pd.DataFrame({"week": cols, "subsidy": Y, "att": att})
    out.to_csv(ROOT / "outputs" / "tables" / "gas_cap_ife_att_weekly.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
