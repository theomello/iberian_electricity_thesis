#!/usr/bin/env python3
"""Design K step 4: robustness of the within-Iberia plant-level rho, and a re-weighted triple difference.
(notes/rq-crisis-quantity.md, "K step 4", rules fixed before running; literature in notes/literature-triple-difference.md)

    .venv/bin/python scripts/analysis/gas_cap_quantity_unit_dose_robust.py [--reps 199] [--wild 9999]

4a bound with Italy's gas response imposed; 4b split-sample near-cost mass (2SLS); 4c imputation of plant effects from
untreated weeks; 4d heterogeneity by dose / efficiency tercile, Spain vs Portugal, per firm; 4e CV3 jackknife and wild
cluster restricted bootstrap (Webb weights); 4f honest bound (relative magnitudes, union form); 4g entropy-balanced
triple difference with Italy, placebos first.

Writes outputs/tables/gas_cap_quantity_unit_dose_robust.csv (one row per estimate) and
gas_cap_quantity_unit_dose_triple_balance.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_quantity_b1 import CAP0, END, RUN, panel  # noqa: E402
from gas_cap_offer_panel import iberia_steps, italy_steps  # noqa: E402
from gas_cap_quantity_unit_dose import PLACEBOS, REF, F, curves, dose, gas_weekly, long  # noqa: E402

T = ROOT / "outputs" / "tables"
C_ITALY = {"full": -0.168, "pre": -0.232}   # step 3, Italy's c per EUR100 gas x z
V_PLACEBO = 0.061                           # step 1, largest |Iberian placebo b|
MAIN = (0.866, 0.624, 1.032)                # step 2 main rho and 95% interval


# ---------------------------------------------------------------- regression helpers
def dummies(uid, wid):
    U = pd.get_dummies(pd.Series(uid)).to_numpy(float)
    Wd = pd.get_dummies(pd.Series(wid)).to_numpy(float)[:, 1:]
    return np.column_stack([U, Wd])


def resid(M: np.ndarray, D: np.ndarray, sw=None) -> np.ndarray:
    """Residuals of the columns of M on D (weighted least squares if sw = sqrt weights)."""
    if sw is not None:
        M, D = M * sw[:, None], D * sw[:, None]
    coef = np.linalg.lstsq(D, M, rcond=None)[0]
    return M - D @ coef


def fe_ols(d: pd.DataFrame, xcols, ycol="y", sw=None) -> np.ndarray:
    D = dummies(d.unit.to_numpy(), d.w.to_numpy())
    R = resid(np.column_stack([d[ycol].to_numpy(float)] + [d[c].to_numpy(float) for c in xcols]), D, sw)
    return np.linalg.lstsq(R[:, 1:], R[:, 0], rcond=None)[0]


def resample(d: pd.DataFrame, rng) -> pd.DataFrame:
    fs = d.firm.unique()
    pick = rng.choice(fs, size=len(fs), replace=True)
    return pd.concat([d[d.firm == f].assign(unit=lambda x, k=k: x.unit + f"#{k}") for k, f in enumerate(pick)],
                     ignore_index=True)


def boot(d, fn, reps, rng):
    out = []
    for _ in range(reps):
        try:
            out.append(fn(resample(d, rng)))
        except (np.linalg.LinAlgError, ValueError, KeyError):
            out.append(np.nan)
    return np.array(out, dtype=float)


def ci(x):
    return tuple(np.nanpercentile(x, [2.5, 97.5]))


def ebal(X: np.ndarray, target: np.ndarray, iters: int = 200) -> np.ndarray:
    """Entropy balancing (Hainmueller 2012): weights w ∝ exp(X·lam) with weighted means of X equal to target."""
    Xc = X - target
    sd = Xc.std(axis=0)
    sd[sd == 0] = 1.0
    Xc = Xc / sd
    lam = np.zeros(X.shape[1])
    for _ in range(iters):
        w = np.exp(Xc @ lam - (Xc @ lam).max())
        w /= w.sum()
        g = Xc.T @ w
        H = (Xc * w[:, None]).T @ Xc - np.outer(g, g)
        step = np.linalg.solve(H + 1e-10 * np.eye(len(lam)), g)
        lam -= step
        if np.abs(g).max() < 1e-10:
            break
    w = np.exp(Xc @ lam - (Xc @ lam).max())
    return w / w.sum() * len(w)


# ---------------------------------------------------------------- data
def build(reps_seed=20261108):
    h = panel()
    meta = h.drop_duplicates("unit").set_index("unit")
    weeks = pd.date_range(pd.Timestamp("2021-10-01").to_period("W").start_time, END, freq="W-MON")
    Wall = h.groupby(["unit", "w"]).run20.mean().unstack().reindex(columns=weeks)
    Wall.index.name = "unit"
    miss = Wall.isna().mean(axis=1)
    ib_all = meta.iberia.reindex(Wall.index)
    keep = (ib_all & (miss <= 0.30)) | (~ib_all & (miss <= 0.50))
    W = Wall[keep]
    ib = ib_all.reindex(W.index)
    firm = meta.firm.reindex(W.index)
    zone = meta.zone.reindex(W.index)
    h = h[h.unit.isin(W.index)]
    si, ci_ = iberia_steps()
    st, ct = italy_steps()
    S = ci_.groupby("date").subsidy.max()
    src = {True: (si, ci_), False: (st, ct)}
    gas = gas_weekly()
    effi = pd.read_parquet(ROOT / "data" / "jrc_ppdb" / "implied_marginal_cost_daily.parquet",
                           columns=["unit", "eff"]).drop_duplicates("unit").set_index("unit").eff
    efft = pd.read_parquet(ROOT / "data" / "jrc_ppdb" / "italy_implied_marginal_cost_daily.parquet",
                           columns=["unit", "eff"]).drop_duplicates("unit").set_index("unit").eff
    eff = pd.concat([effi, efft])
    cols = [w for w in W.columns if not (w < CAP0 and w + pd.Timedelta(days=7) > CAP0 - REF)]
    Sw = h.assign(S=h.date.map(S).fillna(0.0)).groupby("w").S.mean()
    frames, cur = {}, {}
    for c in (True, False):
        hc = h[h.iberia == c]
        cur[c] = curves(hc, *src[c], CAP0)
        early = curves(hc, *src[c], pd.Timestamp("2022-01-01"))
        z = {u: float(F(v, RUN) - F(v, RUN - 100.0)) for (u, hod), v in cur[c].items() if hod is None}
        ze = {u: float(F(v, RUN) - F(v, RUN - 100.0)) for (u, hod), v in early.items() if hod is None}
        G = dose(hc, *src[c], CAP0, S, END, cur[c]).unstack()
        d = long(W[ib == c], G, cols)
        d["firm"] = d.unit.map(firm)
        d["z"], d["z_early"] = d.unit.map(z), d.unit.map(ze)
        d["gas"] = d.w.map(gas[c]).to_numpy()
        d["gz"], d["gz_early"] = d.gas * d.z, d.gas * d.z_early
        d["eff"] = d.unit.map(eff)
        d["zone"] = d.unit.map(zone)
        d["S_w"] = d.w.map(Sw).fillna(0.0)
        frames[c] = d.dropna(subset=["gz"]).reset_index(drop=True)
    return dict(h=h, W=W, ib=ib, firm=firm, src=src, S=S, gas=gas, cols=cols, frames=frames, cur=cur, Sw=Sw)


# ---------------------------------------------------------------- 4e inference
def cv3(d: pd.DataFrame, b0: float) -> float:
    fs = d.firm.unique()
    bs = np.array([fe_ols(d[d.firm != f], ["g"])[0] for f in fs])
    G = len(fs)
    return float(np.sqrt((G - 1) / G * ((bs - bs.mean()) ** 2).sum()))


def wcr(d: pd.DataFrame, draws: int, rng, grid=np.arange(-1.2, 0.6001, 0.005)):
    """Wild cluster restricted bootstrap (Webb weights), cluster = firm; CI by test inversion; p for given nulls."""
    D = dummies(d.unit.to_numpy(), d.w.to_numpy())
    R = resid(np.column_stack([d.y.to_numpy(float), d.g.to_numpy(float)]), D)
    yt, gt = R[:, 0], R[:, 1]
    cl = pd.factorize(d.firm)[0]
    Gn, N, K = cl.max() + 1, len(d), D.shape[1] + 1
    sgg = (gt ** 2).sum()
    q = np.bincount(cl, gt ** 2, Gn)
    sgy = np.bincount(cl, gt * yt, Gn)
    adj = Gn / (Gn - 1) * (N - 1) / (N - K)
    webb = np.array([-np.sqrt(1.5), -1, -np.sqrt(0.5), np.sqrt(0.5), 1, np.sqrt(1.5)])
    V = rng.choice(webb, size=(draws, Gn))
    bhat = sgy.sum() / sgg

    def se(b, s_c):  # s_c: per-cluster sum of g~ * u
        return np.sqrt(adj * (s_c ** 2).sum(axis=-1)) / sgg

    se_hat = se(bhat, sgy - bhat * q)

    def pval(b0):
        t0 = (bhat - b0) / se_hat
        s = sgy - b0 * q                       # per-cluster sum of g~ * e (restricted residuals)
        bstar = b0 + (V @ s) / sgg
        ustar = (b0 - bstar)[:, None] * q[None, :] + V * s[None, :]
        tstar = (bstar - b0) / se(bstar, ustar)
        return float(np.mean(np.abs(tstar) >= abs(t0)))

    ps = np.array([pval(b) for b in grid])
    acc = grid[ps > 0.05]
    return bhat, (acc.min(), acc.max()) if len(acc) else (np.nan, np.nan), pval(0.0), pval(-1.0)


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=199)
    ap.add_argument("--wild", type=int, default=9999)
    a = ap.parse_args()
    rng = np.random.default_rng(20261108)
    B = build()
    d, dit = B["frames"][True], B["frames"][False]
    rows = []

    def add(name, b, lo=np.nan, hi=np.nan, **kw):
        rows.append({"estimate": name, "b": b, "rho": 1 + b, "rho_lo": 1 + lo, "rho_hi": 1 + hi, **kw})
        print(f"  {name:48s} rho {1 + b:.3f}  [{1 + lo:.3f}, {1 + hi:.3f}]  "
              + "  ".join(f"{k} {v:.3g}" if isinstance(v, float) else f"{k} {v}" for k, v in kw.items()))

    print(f"Iberia: {d.unit.nunique()} units, {d.firm.nunique()} firms, {len(d)} unit-weeks; "
          f"Italy (50% rule): {dit.unit.nunique()} units, {dit.firm.nunique()} firms")
    b_main = fe_ols(d, ["g"])[0]
    add("main (reproduces step 2)", b_main, *ci(boot(d, lambda x: fe_ols(x, ["g"])[0], a.reps, rng)))

    print("\n4a  Italy's gas response imposed on Iberia")
    for k, c in C_ITALY.items():
        fn = lambda x, c=c: fe_ols(x.assign(y=x.y - c * x.gz), ["g"])[0]
        add(f"4a c = {c} ({k})", fn(d), *ci(boot(d, fn, a.reps, rng)))

    print("\n4b  split-sample near-cost mass (2SLS)")

    def iv(x):
        D = dummies(x.unit.to_numpy(), x.w.to_numpy())
        R = resid(x[["y", "g", "gz", "gz_early"]].to_numpy(float), D)
        y, X, Z = R[:, 0], R[:, [1, 2]], R[:, [1, 3]]
        Xh = Z @ np.linalg.lstsq(Z, X, rcond=None)[0]
        return np.linalg.lstsq(Xh, y, rcond=None)[0]

    dv = d.dropna(subset=["gz_early"])
    Dv = dummies(dv.unit.to_numpy(), dv.w.to_numpy())
    Rv = resid(dv[["gz", "gz_early", "g"]].to_numpy(float), Dv)
    fs_coef = np.linalg.lstsq(Rv[:, [1, 2]], Rv[:, 0], rcond=None)[0]
    fs_r = Rv[:, 0] - Rv[:, [1, 2]] @ fs_coef
    r2 = 1 - (fs_r ** 2).sum() / (Rv[:, 0] ** 2).sum()
    corr_z = float(dv.drop_duplicates("unit")[["z", "z_early"]].corr().iloc[0, 1])
    est = iv(dv)
    draws = []
    for _ in range(a.reps):
        try:
            draws.append(iv(resample(dv, rng)))
        except (np.linalg.LinAlgError, ValueError):
            draws.append([np.nan, np.nan])
    draws = np.array(draws)
    clo, chi = ci(draws[:, 1])
    add("4b 2SLS, gas*z instrumented by gas*z_early", est[0], *ci(draws[:, 0]),
        c=float(est[1]), c_lo=float(clo), c_hi=float(chi), corr_z_zearly=corr_z, first_stage_partial_r2=float(r2))
    iv_rule = clo < chi < 0

    print("\n4c  imputation: plant effects from untreated weeks only")

    def imput(x):
        un = x[(x.w < CAP0) | (x.S_w <= 0)]
        tr = x[(x.w >= CAP0) & (x.S_w > 0)]
        D = dummies(un.unit.to_numpy(), un.w.to_numpy())
        coef = np.linalg.lstsq(D, un.y.to_numpy(float), rcond=None)[0]
        units = pd.get_dummies(pd.Series(un.unit.to_numpy())).columns
        alpha = pd.Series(coef[: len(units)], index=units)
        tr = tr[tr.unit.isin(units)].assign(yt=lambda t: t.y - t.unit.map(alpha))
        Dw = pd.get_dummies(pd.Series(tr.w.to_numpy())).to_numpy(float)
        R = resid(np.column_stack([tr.yt.to_numpy(float), tr.g.to_numpy(float)]), Dw)
        return float((R[:, 0] @ R[:, 1]) / (R[:, 1] @ R[:, 1]))

    bi = imput(d)
    lo, hi = ci(boot(d, imput, a.reps, rng))
    add("4c imputation", bi, lo, hi, outside_main=not (MAIN[1] <= 1 + bi <= MAIN[2]))

    print("\n4d  heterogeneity")
    pm = d[d.S_w > 0].groupby("unit").g.mean()
    effu = d.drop_duplicates("unit").set_index("unit").eff
    het_flag = False
    for lab, var in (("dose tercile", pm), ("efficiency tercile", effu)):
        t = pd.qcut(var.rank(method="first"), 3, labels=["low", "mid", "high"])
        dd = d.assign(k=d.unit.map(t))
        dd = dd.dropna(subset=["k"])
        for kk in ("low", "mid", "high"):
            dd[f"g_{kk}"] = dd.g * (dd.k == kk)
        fn = lambda x: fe_ols(x, ["g_low", "g_mid", "g_high"])
        est = fn(dd)
        dr = []
        for _ in range(a.reps):
            try:
                dr.append(fn(resample(dd, rng)))
            except (np.linalg.LinAlgError, ValueError):
                dr.append([np.nan] * 3)
        dr = np.array(dr)
        for j, kk in enumerate(("low", "mid", "high")):
            add(f"4d {lab}: {kk}", est[j], *ci(dr[:, j]), units=int((t == kk).sum()))
        dlo, dhi = ci(dr[:, 2] - dr[:, 0])
        diff_ex = not (dlo <= 0 <= dhi)
        het_flag |= diff_ex
        rows.append({"estimate": f"4d {lab}: high - low (b)", "b": est[2] - est[0], "b_lo": dlo, "b_hi": dhi,
                     "excludes_0": diff_ex})
        print(f"  {lab}: high - low in b {est[2] - est[0]:+.3f} [{dlo:+.3f}, {dhi:+.3f}]"
              f"{'  <-- excludes 0' if diff_ex else ''}")
    dd = d.assign(g_es=d.g * (d.zone == "ES"), g_pt=d.g * (d.zone == "PT"))
    fn = lambda x: fe_ols(x, ["g_es", "g_pt"])
    est = fn(dd)
    dr = np.array([fn(resample(dd, rng)) for _ in range(a.reps)])
    add("4d Spain", est[0], *ci(dr[:, 0]), units=int(d[d.zone == "ES"].unit.nunique()))
    add("4d Portugal", est[1], *ci(dr[:, 1]), units=int(d[d.zone == "PT"].unit.nunique()))
    D = dummies(d.unit.to_numpy(), d.w.to_numpy())
    gt = resid(d[["g"]].to_numpy(float), D)[:, 0]
    wfirm = pd.Series(gt ** 2).groupby(d.firm.to_numpy()).sum()
    wfirm /= wfirm.sum()
    print("  per firm (b alone, its share of the regression's weight):")
    for f in wfirm.sort_values(ascending=False).index:
        sub = d[d.firm == f]
        try:
            bf = fe_ols(d.assign(gf=d.g * (d.firm == f), go=d.g * (d.firm != f)), ["gf", "go"])[0]
        except np.linalg.LinAlgError:
            bf = np.nan
        rows.append({"estimate": f"4d firm {f}", "b": bf, "rho": 1 + bf, "weight": float(wfirm[f]),
                     "units": int(sub.unit.nunique())})
        print(f"    {str(f)[:34]:34s} weight {wfirm[f]:.3f}  rho {1 + bf:+.2f}  ({sub.unit.nunique()} units)")

    print("\n4e  inference with few clusters")
    se3 = cv3(d, b_main)
    G = d.firm.nunique()
    tq = stats.t.ppf(0.975, G - 1)
    add("4e CV3 jackknife, t(G-1)", b_main, b_main - tq * se3, b_main + tq * se3, se_cv3=se3, clusters=G)
    bh, (wl, wh), p1, p0 = wcr(d, a.wild, rng)
    add("4e wild cluster restricted (Webb)", bh, wl, wh, p_rho_eq_1=p1, p_rho_eq_0=p0, draws=a.wild)
    ints = {"firm block": (MAIN[1] - 1, MAIN[2] - 1), "CV3": (b_main - tq * se3, b_main + tq * se3),
            "wild": (wl, wh)}
    widest = max(ints, key=lambda k: ints[k][1] - ints[k][0])
    wlo, whi = ints[widest]
    print(f"  widest: {widest}  rho [{1 + wlo:.3f}, {1 + whi:.3f}]")

    print("\n4f  honest bound (relative magnitudes, union form), around the widest interval")
    for M in (0.5, 1.0, 2.0):
        add(f"4f M = {M}", b_main, wlo - M * V_PLACEBO, whi + M * V_PLACEBO)

    print("\n4g  entropy-balanced triple difference")
    tri = triple(B, a.reps, rng, rows)

    pd.DataFrame(rows).to_csv(T / "gas_cap_quantity_unit_dose_robust.csv", index=False)
    print("\nRules:")
    print(f"  4b: {'gas channel present (IV): its rho becomes main' if iv_rule else 'IV c not negative-significant: 0.87 stays'}")
    print(f"  4c: imputation {'OUTSIDE' if rows[[r['estimate'] for r in rows].index('4c imputation')]['outside_main'] else 'inside'} the main interval")
    print(f"  4d: {'a tercile difference excludes 0: 0.87 is a weighted average, quote terciles beside' if het_flag else 'no tercile difference excludes 0'}")
    print(f"  4e: quote the {widest} interval rho [{1 + wlo:.3f}, {1 + whi:.3f}]")
    print(f"  4g: {tri}")
    return 0


def triple(B, reps, rng, rows) -> str:
    d, dit = B["frames"][True], B["frames"][False]
    iu = d.drop_duplicates("unit").set_index("unit")
    tu = dit.drop_duplicates("unit").set_index("unit")
    pm_i = d[d.S_w > 0].groupby("unit").g.mean()
    pm_t = dit[dit.S_w > 0].groupby("unit").g.mean()
    Xi = pd.DataFrame({"dose": pm_i, "z": iu.z, "eff": iu.eff}).dropna()
    Xt = pd.DataFrame({"dose": pm_t, "z": tu.z, "eff": tu.eff}).dropna()
    target = Xi.mean().to_numpy()
    w = pd.Series(ebal(Xt.to_numpy(), target), index=Xt.index)
    bal = pd.DataFrame({"iberia": Xi.mean(), "italy_raw": Xt.mean(), "italy_weighted": (Xt.mul(w, axis=0)).sum() / w.sum()})
    neff = float(w.sum() ** 2 / (w ** 2).sum())
    bal.loc["n_units"] = [len(Xi), len(Xt), neff]
    bal.to_csv(T / "gas_cap_quantity_unit_dose_triple_balance.csv")
    print(bal.round(3).to_string())
    print(f"  effective Italian plants {neff:.1f} of {len(Xt)}; max weight {w.max():.2f}")
    dit = dit[dit.unit.isin(w.index)].assign(sw=lambda x: np.sqrt(x.unit.map(w).to_numpy()))

    def b_it(x):
        return fe_ols(x, ["g", "gz"], sw=x.sw.to_numpy())[0]

    def b_ib(x):
        return fe_ols(x, ["g", "gz"])[0]

    # placebos first
    h, W, ib, firm, src, S, gas = B["h"], B["W"], B["ib"], B["firm"], B["src"], B["S"], B["gas"]
    ok = True
    stop = CAP0 - pd.Timedelta(days=1)
    for P in PLACEBOS:
        Sp = pd.Series(S.reindex(pd.date_range(CAP0, CAP0 + (stop - P))).fillna(0.0).to_numpy(),
                       index=pd.date_range(P, stop))
        cols = [x for x in W.columns if x + pd.Timedelta(days=6) < CAP0
                and not (x < P and x + pd.Timedelta(days=7) > P - REF)]
        L = {}
        for c in (True, False):
            hc = h[h.iberia == c]
            cur = curves(hc, *src[c], P)
            z = {u: float(F(v, RUN) - F(v, RUN - 100.0)) for (u, hod), v in cur.items() if hod is None}
            G = dose(hc, *src[c], P, Sp, stop, cur).unstack()
            x = long(W[ib == c], G, cols)
            x["firm"] = x.unit.map(firm)
            x["gz"] = x.w.map(gas[c]).to_numpy() * x.unit.map(z)
            x = x.dropna(subset=["gz"])
            if not c:
                x = x[x.unit.isin(w.index)].assign(sw=lambda t: np.sqrt(t.unit.map(w).to_numpy()))
            L[c] = x.reset_index(drop=True)
        b0 = b_ib(L[True]) - b_it(L[False])
        dr = []
        for _ in range(reps):
            try:
                dr.append(b_ib(resample(L[True], rng)) - b_it(resample(L[False], rng)))
            except (np.linalg.LinAlgError, ValueError):
                dr.append(np.nan)
        dr = np.array(dr)
        lo, hi = ci(dr)
        mde = 2.8 * np.nanstd(dr, ddof=1)
        flat = lo <= 0 <= hi
        ok &= flat and mde <= 0.5
        rows.append({"estimate": f"4g placebo {P.date()} triple b", "b": b0, "b_lo": lo, "b_hi": hi, "mde": mde,
                     "excludes_0": not flat})
        print(f"  placebo {P.date()}: triple b {b0:+.3f} [{lo:+.3f}, {hi:+.3f}], MDE {mde:.3f}"
              f"{'' if flat else '  <-- excludes 0'}{'  <-- MDE > 0.5' if mde > 0.5 else ''}")
    if not ok:
        return "STOP at the placebos: triple difference not read"
    bi_, bt_ = b_ib(d), b_it(dit)
    dr = []
    for _ in range(reps):
        try:
            dr.append([b_ib(resample(d, rng)), b_it(resample(dit, rng))])
        except (np.linalg.LinAlgError, ValueError):
            dr.append([np.nan, np.nan])
    dr = np.array(dr)
    lo, hi = ci(dr[:, 0] - dr[:, 1])
    tlo, thi = ci(dr[:, 1])
    rows.append({"estimate": "4g Italy weighted b (gas term)", "b": bt_, "b_lo": tlo, "b_hi": thi})
    rows.append({"estimate": "4g triple (re-weighted, gas term)", "b": bi_ - bt_, "rho": 1 + bi_ - bt_,
                 "rho_lo": 1 + lo, "rho_hi": 1 + hi})
    print(f"  Italy weighted b {bt_:+.3f} [{tlo:+.3f}, {thi:+.3f}]")
    print(f"  triple rho {1 + bi_ - bt_:.3f} [{1 + lo:.3f}, {1 + hi:.3f}]")
    overlap = not (1 + hi < MAIN[1] or 1 + lo > MAIN[2])
    return f"placebos pass; triple rho {1 + bi_ - bt_:.2f} [{1 + lo:.2f}, {1 + hi:.2f}], " \
           f"{'overlaps' if overlap else 'does NOT overlap'} the main interval (check only)"


if __name__ == "__main__":
    raise SystemExit(main())
