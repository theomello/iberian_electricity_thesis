#!/usr/bin/env python3
"""Design K, step 1: the plant-level dose (notes/rq-crisis-quantity.md §K, rules fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_quantity_unit_dose.py [--reps 199]

No rho and no post-cap outcome. (a) How much the dose g_iw differs across plants within a week, after the cap
(Iberia real, Italy would-be). (b) Placebo slopes at 2022-01-01 and 2022-03-01 of
    y_iw = alpha_i + delta_w + b * g_iw   per country, and b_IB - b_IT,
with firm block bootstrap intervals and MDE = 2.8 x bootstrap sd.

Dose: unit i's offer curve over the 8 weeks before date D (markups over gross cost, in-money hours, by hour of
day, B1's fallback), F_i(x) = mean share of K at markup <= x; per in-money hour from D, F_i(20) - F_i(20 - S),
weekly mean; 0 before D. Placebo P: S on P + k = real S on 2022-06-15 + k. Weeks overlapping the reference window
are dropped from the regression.

Writes outputs/tables/gas_cap_quantity_unit_dose_{spread,placebo}.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_quantity_b1 import CAP0, END, MIN_DAYS, RUN, panel, matrix  # noqa: E402
from gas_cap_offer_panel import iberia_steps, italy_steps  # noqa: E402

T = ROOT / "outputs" / "tables"
PLACEBOS = [pd.Timestamp("2022-01-01"), pd.Timestamp("2022-03-01")]
REF = pd.Timedelta(weeks=8)


def curves(h: pd.DataFrame, s: pd.DataFrame, cost: pd.DataFrame, D: pd.Timestamp) -> dict:
    """Per (unit, hod) and per unit: sorted markups and cumulative share of K over the reference window."""
    off = s.groupby(["unit", "date", "period"]).mw.sum()
    K = off[off.index.get_level_values("date") < CAP0].groupby("unit").quantile(0.99).rename("K")
    keys = h[h.date.between(D - REF, D - pd.Timedelta(days=1))][["unit", "date", "period"]]
    r = (s.merge(keys, on=["unit", "date", "period"])
         .merge(cost[["unit", "date", "cost_gross"]], on=["unit", "date"]).merge(K, on="unit"))
    r["m"] = r.p - r.cost_gross
    r["hod"] = r.period.clip(upper=24)
    out = {}
    for u, gu in r.groupby("unit"):
        nhu = len(gu[["date", "period"]].drop_duplicates())
        out[(u, None)] = mk(gu, nhu)
        for hod, gc in gu.groupby("hod"):
            if gc.date.nunique() >= MIN_DAYS:
                out[(u, hod)] = mk(gc, len(gc[["date", "period"]].drop_duplicates()))
    return out


def mk(c: pd.DataFrame, n: int):
    o = np.argsort(c.m.to_numpy())
    return c.m.to_numpy()[o], np.cumsum((c.mw / c.K).to_numpy()[o]) / n


def F(cur, x):
    m, cw = cur
    i = np.searchsorted(m, x, side="right")
    return np.where(i > 0, cw[np.maximum(i - 1, 0)], 0.0)


def dose(h: pd.DataFrame, s, cost, D: pd.Timestamp, S: pd.Series, stop: pd.Timestamp, cur=None) -> pd.Series:
    """g_iw for dates D..stop, from the subsidy path S (indexed by date)."""
    cur = curves(h, s, cost, D) if cur is None else cur
    post = h[h.date.between(D, stop)][["unit", "date", "period", "w"]].copy()
    post["S"] = post.date.map(S).fillna(0.0).to_numpy()
    post["hod"] = post.period.clip(upper=24)
    parts = []
    for (u, hod), g in post.groupby(["unit", "hod"]):
        c = cur.get((u, hod)) or cur.get((u, None))
        if c is None:
            continue
        parts.append(g.assign(g=F(c, RUN) - F(c, RUN - g.S.to_numpy())))
    e = pd.concat(parts)
    return e.groupby(["unit", "w"]).g.mean()


def twfe(y: np.ndarray, g: np.ndarray, uid: np.ndarray, wid: np.ndarray, trend: bool = False) -> float:
    """OLS slope on g with unit and week dummies (rows already filtered to observed cells); `trend` adds a
    linear trend per unit."""
    U = pd.get_dummies(uid).to_numpy(float)
    Wd = pd.get_dummies(wid).to_numpy(float)[:, 1:]
    X = np.column_stack([g, U, Wd])
    if trend:
        tt = (pd.to_datetime(pd.Series(wid)) - pd.Timestamp("2022-06-15")).dt.days.to_numpy() / 365.0
        X = np.column_stack([X, U * tt[:, None]])
    return float(np.linalg.lstsq(X, y, rcond=None)[0][0])


def long(W: pd.DataFrame, G: pd.DataFrame, keep_cols) -> pd.DataFrame:
    y = W[keep_cols].stack().rename("y")
    g = G.reindex(index=W.index, columns=keep_cols).fillna(0.0).stack().rename("g")
    return pd.concat([y, g], axis=1).dropna(subset=["y"]).reset_index().rename(columns={"level_1": "w"})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=199)
    ap.add_argument("--stage", type=int, choices=(1, 2, 3), default=1)
    a = ap.parse_args()
    rng = np.random.default_rng(20261108)

    h = panel()
    W, thr = matrix(h, "run20")
    W.index.name = "unit"
    meta = h.drop_duplicates("unit").set_index("unit")
    ib = meta.iberia.reindex(W.index)
    firm = meta.firm.reindex(W.index)
    h = h[h.unit.isin(W.index)]
    print(f"units: {int(ib.sum())} Iberian, {int((~ib).sum())} Italian (missing-week threshold {thr})")
    if a.stage == 2:
        return step2(h, W, ib, firm, a.reps, rng)
    if a.stage == 3:
        return step3(h, W, ib, firm, a.reps, rng)

    si, ci = iberia_steps()
    st, ct = italy_steps()
    S = ci.groupby("date").subsidy.max()  # same for every unit on a day
    src = {True: (si, ci), False: (st, ct)}

    # (a) spread of the real dose after the cap
    rows = []
    for c in (True, False):
        hc = h[h.iberia == c]
        g = dose(hc, *src[c], CAP0, S, END).unstack()
        Sw = h[h.date >= CAP0].assign(S=lambda x: x.date.map(S)).groupby("w").S.mean()
        wk = Sw.index[Sw > 0]
        G = g.reindex(columns=wk)
        x = G.stack()
        d = x.reset_index()
        d.columns = ["unit", "w", "g"]
        res = d.g - d.groupby("unit").g.transform("mean") - d.groupby("w").g.transform("mean") + d.g.mean()
        rows.append({"country": "Iberia" if c else "Italy (would-be)", "unit_weeks": len(d),
                     "weeks": d.w.nunique(), "mean_g": d.g.mean(),
                     "median_weekly_sd": G.std(axis=0).median(),
                     "p10_unit_mean_g": d.groupby("unit").g.mean().quantile(0.1),
                     "p90_unit_mean_g": d.groupby("unit").g.mean().quantile(0.9),
                     "share_var_within": float(res.var() / d.g.var())})
    sp = pd.DataFrame(rows)
    sp.to_csv(T / "gas_cap_quantity_unit_dose_spread.csv", index=False)
    print("\n(a) dose after the cap, weeks with S > 0:")
    print(sp.round(3).to_string(index=False))

    # (b) placebos
    out = []
    for P in PLACEBOS:
        stop = CAP0 - pd.Timedelta(days=1)
        Sp = pd.Series(S.reindex(pd.date_range(CAP0, CAP0 + (stop - P))).fillna(0.0).to_numpy(),
                       index=pd.date_range(P, stop))
        cols = [w for w in W.columns if w + pd.Timedelta(days=6) < CAP0
                and not (w < P and w + pd.Timedelta(days=7) > P - REF)]
        L = {}
        for c in (True, False):
            hc = h[h.iberia == c]
            G = dose(hc, *src[c], P, Sp, stop).unstack()
            Wc = W[ib == c]
            d = long(Wc, G, cols)
            d["firm"] = d.unit.map(firm)
            L[c] = d
        bhat = {c: twfe(L[c].y.to_numpy(), L[c].g.to_numpy(), L[c].unit.to_numpy(), L[c].w.to_numpy())
                for c in (True, False)}
        draws = []
        for _ in range(a.reps):
            bd = {}
            for c in (True, False):
                d = L[c]
                fs = d.firm.unique()
                pick = rng.choice(fs, size=len(fs), replace=True)
                parts = [d[d.firm == f].assign(unit=lambda x, k=k: x.unit + f"#{k}") for k, f in enumerate(pick)]
                dd = pd.concat(parts)
                bd[c] = twfe(dd.y.to_numpy(), dd.g.to_numpy(), dd.unit.to_numpy(), dd.w.to_numpy())
            draws.append([bd[True], bd[False], bd[True] - bd[False]])
        dr = np.array(draws)
        for j, (name, b0) in enumerate([("Iberia", bhat[True]), ("Italy", bhat[False]),
                                        ("triple (IB - IT)", bhat[True] - bhat[False])]):
            lo, hi = np.nanpercentile(dr[:, j], [2.5, 97.5])
            sd = np.nanstd(dr[:, j], ddof=1)
            out.append({"placebo": P.date(), "estimate": name, "b": b0, "lo": lo, "hi": hi,
                        "excludes_0": not (lo <= 0 <= hi), "mde": 2.8 * sd,
                        "weeks": len(cols), "unit_weeks": len(L[True]) if j == 0 else len(L[False]) if j == 1 else
                        len(L[True]) + len(L[False]),
                        "firms": L[True].firm.nunique() if j == 0 else L[False].firm.nunique() if j == 1 else np.nan,
                        "mean_g_post": (L[True] if j != 1 else L[False]).query("g > 0").g.mean()})
    pl = pd.DataFrame(out)
    pl.to_csv(T / "gas_cap_quantity_unit_dose_placebo.csv", index=False)
    print(f"\n(b) placebos, firm block bootstrap {a.reps}:")
    print(pl.round(3).to_string(index=False))

    # rules
    ibm = pl[pl.estimate == "Iberia"]
    tr = pl[pl.estimate.str.startswith("triple")]
    print("\nRule 1 (power):", "STOP: within-Iberia MDE > 0.5 at a placebo" if (ibm.mde > 0.5).any()
          else "within-Iberia MDE <= 0.5 at both")
    if (tr.mde > 0.5).any():
        print("   triple difference MDE > 0.5 at a placebo: check only, not the main estimate")
    if not ibm.excludes_0.any():
        f = "Iberian placebo flat at both dates -> within-Iberia slope main, triple difference a check"
    elif not tr.excludes_0.any():
        f = "Iberian placebo not flat, triple difference flat at both -> triple difference main"
    else:
        f = "STOP: Iberian and triple-difference placebos both exclude 0 at some date"
    print("Rule 2 (flatness):", f)
    return 0


def boot_b(L: dict, reps: int, rng, trend: bool = False) -> np.ndarray:
    """Firm block bootstrap within country; returns draws of [b_IB, b_IT] (b_IT NaN if Italy absent)."""
    out = []
    for _ in range(reps):
        bd = []
        for c in (True, False):
            d = L.get(c)
            if d is None:
                bd.append(np.nan)
                continue
            fs = d.firm.unique()
            pick = rng.choice(fs, size=len(fs), replace=True)
            dd = pd.concat([d[d.firm == f].assign(unit=lambda x, k=k: x.unit + f"#{k}") for k, f in enumerate(pick)])
            bd.append(twfe(dd.y.to_numpy(), dd.g.to_numpy(), dd.unit.to_numpy(), dd.w.to_numpy(), trend))
        out.append(bd)
    return np.array(out)


def step2(h, W, ib, firm, reps, rng) -> int:
    """Section K step 2: the real rho within Iberia, with the checks fixed in the note."""
    si, ci = iberia_steps()
    st, ct = italy_steps()
    S = ci.groupby("date").subsidy.max()
    src = {True: (si, ci), False: (st, ct)}
    cols = [w for w in W.columns if not (w < CAP0 and w + pd.Timedelta(days=7) > CAP0 - REF)]
    cur = {c: curves(h[h.iberia == c], *src[c], CAP0) for c in (True, False)}

    def frame(c, Spath, hh=None, Wm=None):
        hh = h if hh is None else hh
        Wm = W if Wm is None else Wm
        G = dose(hh[hh.iberia == c], *src[c], CAP0, Spath, END, cur[c]).unstack()
        d = long(Wm[ib.reindex(Wm.index) == c], G, cols)
        d["firm"] = d.unit.map(firm)
        return d

    def b_of(d, trend=False):
        return twfe(d.y.to_numpy(), d.g.to_numpy(), d.unit.to_numpy(), d.w.to_numpy(), trend)

    L = {c: frame(c, S) for c in (True, False)}
    b0, bt = b_of(L[True]), b_of(L[True], True)
    dr = boot_b({True: L[True]}, reps, rng)[:, 0]
    lo, hi = np.nanpercentile(dr, [2.5, 97.5])
    drt = boot_b({True: L[True]}, reps, rng, trend=True)[:, 0]
    tlo, thi = np.nanpercentile(drt, [2.5, 97.5])
    stop_trend = not (1 + lo <= 1 + bt <= 1 + hi)
    print(f"\nmain (within Iberia): {len(L[True])} unit-weeks, {L[True].unit.nunique()} units, "
          f"{L[True].firm.nunique()} firms, {len(cols)} weeks")
    print(f"  rho = 1 + b          {1 + b0:.3f}  95% [{1 + lo:.3f}, {1 + hi:.3f}]  width {hi - lo:.3f}")
    print(f"  with unit trends     {1 + bt:.3f}  95% [{1 + tlo:.3f}, {1 + thi:.3f}]  "
          f"{'<-- outside main interval: STOP' if stop_trend else '(inside main interval: check holds)'}")

    # timing permutation: cyclic shifts of the post-cap S path by whole weeks
    days = pd.date_range(CAP0, END)
    Sv = S.reindex(days).fillna(0.0).to_numpy()
    nw = len(days) // 7
    shifted = []
    for k in range(1, nw):
        Sk = pd.Series(np.roll(Sv, 7 * k), index=days)
        shifted.append(b_of(frame(True, Sk)))
    shifted = np.array(shifted)
    p = float(np.mean(shifted <= b0))
    print(f"  timing permutation: {len(shifted)} shifts, 5th pct of shifted b {np.percentile(shifted, 5):+.3f}, "
          f"real b {b0:+.3f}, one-sided p {p:.3f}")

    # triple difference (check)
    bit = b_of(L[False])
    drr = boot_b(L, reps, rng)
    trip = drr[:, 0] - drr[:, 1]
    tl, th = np.nanpercentile(trip, [2.5, 97.5])
    il, ih = np.nanpercentile(drr[:, 1], [2.5, 97.5])
    print(f"  Italy would-be b     {bit:+.3f}  95% [{il:+.3f}, {ih:+.3f}]")
    print(f"  triple rho           {1 + b0 - bit:.3f}  95% [{1 + tl:.3f}, {1 + th:.3f}]")

    # reported beside: reference weeks kept; gross-cost in-money sample
    cols_all = list(W.columns)
    Gr = dose(h[h.iberia], *src[True], CAP0, S, END, cur[True]).unstack()
    dk = long(W[ib], Gr, cols_all)
    b_ref = b_of(dk)
    hg = h[(h.price_lag - h.cost_gross) > 50]
    Wg = hg.groupby(["unit", "w"]).run20.mean().unstack().reindex(index=W.index, columns=W.columns)
    Wg.index.name = "unit"
    dg = frame(True, S, hg, Wg)
    b_g = b_of(dg)
    print(f"  reference weeks kept: rho {1 + b_ref:.3f};  gross-cost in-money sample: rho {1 + b_g:.3f} "
          f"({len(dg)} unit-weeks)")

    pd.DataFrame([
        {"estimate": "main", "rho": 1 + b0, "lo": 1 + lo, "hi": 1 + hi, "unit_weeks": len(L[True])},
        {"estimate": "unit trends", "rho": 1 + bt, "lo": 1 + tlo, "hi": 1 + thi, "stop": stop_trend},
        {"estimate": "permutation", "rho": 1 + b0, "p": p, "shifts": len(shifted),
         "shifted_b_p5": np.percentile(shifted, 5)},
        {"estimate": "italy would-be b", "rho": bit, "lo": il, "hi": ih},
        {"estimate": "triple", "rho": 1 + b0 - bit, "lo": 1 + tl, "hi": 1 + th},
        {"estimate": "reference weeks kept", "rho": 1 + b_ref},
        {"estimate": "gross-cost in-money sample", "rho": 1 + b_g, "unit_weeks": len(dg)},
    ]).to_csv(T / "gas_cap_quantity_unit_dose_rho.csv", index=False)

    excl1 = not (1 + lo <= 1 <= 1 + hi)
    print("\nRule:", "STOP (unit trends)" if stop_trend else
          ("incomplete pass-through claimed and " + ("timing supports it" if p <= 0.05 else "timing FAILS: STOP"))
          if excl1 else f"interval includes rho = 1 (full pass-through not rejected); permutation p {p:.3f} reported")
    print("B3 for comparison: 0.73 [0.51, 1.03], width 0.52")
    return 0


def twfe_x(y, X, uid, wid) -> np.ndarray:
    """OLS coefficients on the columns of X, with unit and week dummies."""
    U = pd.get_dummies(uid).to_numpy(float)
    Wd = pd.get_dummies(wid).to_numpy(float)[:, 1:]
    return np.linalg.lstsq(np.column_stack([X, U, Wd]), y, rcond=None)[0][: X.shape[1]]


def gas_weekly() -> dict:
    """Weekly mean of the daily gas price lagged two days (final at bid time), EUR 100/MWh."""
    mib = pd.read_parquet(ROOT / "data" / "mibgas" / "mibgas_price_index_daily.parquet", columns=["date", "mibgas_es_eur_mwh"])
    mib = mib.assign(date=pd.to_datetime(mib.date)).set_index("date").mibgas_es_eur_mwh
    psv = pd.read_parquet(ROOT / "data" / "gme" / "gas" / "gme_mgp_gas_daily.parquet", columns=["product", "price_ref"])
    psv["date"] = pd.to_datetime(psv["product"].str[4:], errors="coerce")
    psv = psv.dropna(subset=["date"]).groupby("date").price_ref.last()
    out = {}
    for c, s in ((True, mib), (False, psv)):
        s = s.asfreq("D").ffill().shift(2)
        out[c] = s.groupby(s.index.to_period("W").start_time).mean() / 100.0
    return out


def step3(h, W, ib, firm, reps, rng) -> int:
    """Section K step 3: b with a gas x near-cost-mass term."""
    si, ci = iberia_steps()
    st, ct = italy_steps()
    S = ci.groupby("date").subsidy.max()
    src = {True: (si, ci), False: (st, ct)}
    cols = [w for w in W.columns if not (w < CAP0 and w + pd.Timedelta(days=7) > CAP0 - REF)]
    gas = gas_weekly()
    L, rows = {}, []
    for c in (True, False):
        hc = h[h.iberia == c]
        cur = curves(hc, *src[c], CAP0)
        z = {u: float(F(cur[(u, None)], RUN) - F(cur[(u, None)], RUN - 100.0)) for (u, hod) in cur if hod is None}
        G = dose(hc, *src[c], CAP0, S, END, cur).unstack()
        d = long(W[ib == c], G, cols)
        d["firm"] = d.unit.map(firm)
        d["z"] = d.unit.map(z)
        d["gz"] = d.w.map(gas[c]).to_numpy() * d.z
        d = d.dropna(subset=["gz"])
        L[c] = d
    name = {True: "Iberia", False: "Italy (would-be)"}

    def fit(d):
        return twfe_x(d.y.to_numpy(), d[["g", "gz"]].to_numpy(), d.unit.to_numpy(), d.w.to_numpy())

    def boot(d):
        out = []
        fs = d.firm.unique()
        for _ in range(reps):
            pick = rng.choice(fs, size=len(fs), replace=True)
            dd = pd.concat([d[d.firm == f].assign(unit=lambda x, k=k: x.unit + f"#{k}") for k, f in enumerate(pick)])
            out.append(fit(dd))
        return np.array(out)

    for c in (True, False):
        d = L[c]
        res = d[["g", "gz"]].copy()
        for col in ("g", "gz"):  # two-way demeaning by alternating projections
            v = d[col].astype(float).copy()
            for _ in range(50):
                v = v - v.groupby(d.unit).transform("mean")
                v = v - v.groupby(d.w).transform("mean")
            res[col] = v
        rc = float(res.g.corr(res.gz))
        bc = fit(d)
        dr = boot(d)
        (blo, bhi), (clo, chi) = np.nanpercentile(dr[:, 0], [2.5, 97.5]), np.nanpercentile(dr[:, 1], [2.5, 97.5])
        pre = d[d.w < CAP0]
        cpre = twfe_x(pre.y.to_numpy(), pre[["gz"]].to_numpy(), pre.unit.to_numpy(), pre.w.to_numpy())[0]
        fs = pre.firm.unique()
        cp = []
        for _ in range(reps):
            pick = rng.choice(fs, size=len(fs), replace=True)
            dd = pd.concat([pre[pre.firm == f].assign(unit=lambda x, k=k: x.unit + f"#{k}") for k, f in enumerate(pick)])
            cp.append(twfe_x(dd.y.to_numpy(), dd[["gz"]].to_numpy(), dd.unit.to_numpy(), dd.w.to_numpy())[0])
        plo, phi = np.nanpercentile(cp, [2.5, 97.5])
        rows.append({"country": name[c], "unit_weeks": len(d), "resid_corr_g_gz": rc,
                     "b": bc[0], "b_lo": blo, "b_hi": bhi, "rho_gas": 1 + bc[0], "rho_lo": 1 + blo, "rho_hi": 1 + bhi,
                     "c": bc[1], "c_lo": clo, "c_hi": chi, "c_pre": cpre, "c_pre_lo": plo, "c_pre_hi": phi,
                     "z_mean": d.drop_duplicates("unit").z.mean(), "z_sd": d.drop_duplicates("unit").z.std()})
        print(f"\n{name[c]}: {len(d)} unit-weeks; residual corr(g, gas*z) {rc:+.3f}; z mean {rows[-1]['z_mean']:.3f} "
              f"sd {rows[-1]['z_sd']:.3f}")
        print(f"  b {bc[0]:+.3f} [{blo:+.3f}, {bhi:+.3f}]  -> rho_gas {1 + bc[0]:.3f} [{1 + blo:.3f}, {1 + bhi:.3f}]")
        print(f"  c per EUR100 gas x z {bc[1]:+.3f} [{clo:+.3f}, {chi:+.3f}];  pre-cap only {cpre:+.3f} [{plo:+.3f}, {phi:+.3f}]")
    pd.DataFrame(rows).to_csv(T / "gas_cap_quantity_unit_dose_gas.csv", index=False)
    r = rows[0]
    if abs(r["resid_corr_g_gz"]) > 0.9:
        v = "STOP: g and gas*z not separable; 0.87 stays, caveat unresolved"
    elif r["c_hi"] < 0:
        v = f"gas channel present: rho_gas {r['rho_gas']:.2f} becomes main, 0.87 the version without it"
    elif r["c_lo"] > 0:
        v = "c positive (against the drift hypothesis): reported, 0.87 stays main"
    else:
        v = f"gas channel not detected: 0.87 stays main, rho_gas {r['rho_gas']:.2f} beside"
    print("\nRule:", v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
