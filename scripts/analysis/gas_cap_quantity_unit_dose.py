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


def dose(h: pd.DataFrame, s, cost, D: pd.Timestamp, S: pd.Series, stop: pd.Timestamp) -> pd.Series:
    """g_iw for dates D..stop, from the subsidy path S (indexed by date)."""
    cur = curves(h, s, cost, D)
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


def twfe(y: np.ndarray, g: np.ndarray, uid: np.ndarray, wid: np.ndarray) -> float:
    """OLS slope on g with unit and week dummies (rows already filtered to observed cells)."""
    U = pd.get_dummies(uid).to_numpy(float)
    Wd = pd.get_dummies(wid).to_numpy(float)[:, 1:]
    X = np.column_stack([g, U, Wd])
    return float(np.linalg.lstsq(X, y, rcond=None)[0][0])


def long(W: pd.DataFrame, G: pd.DataFrame, keep_cols) -> pd.DataFrame:
    y = W[keep_cols].stack().rename("y")
    g = G.reindex(index=W.index, columns=keep_cols).fillna(0.0).stack().rename("g")
    return pd.concat([y, g], axis=1).dropna(subset=["y"]).reset_index().rename(columns={"level_1": "w"})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=199)
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


if __name__ == "__main__":
    raise SystemExit(main())
