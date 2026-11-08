#!/usr/bin/env python3
"""Design L, step 1: did the gas-cap subsidy make gas plants run more? (notes/rq-crisis-quantity.md §L, rules fixed
before running.) No post-cap estimate here.

    .venv/bin/python scripts/analysis/gas_cap_dispatch_dose.py [--reps 199]

Per plant and hour: output / K (Iberia PDBF, Italy GME accepted sales), margin x = yesterday's same-hour zone price
minus bid-time gross cost, dose flip(S) = 1[x <= 0 < x + S]. (a) overlap of doses Iberia vs Italy; (b) monthly capacity
factor around March 2022; (c) the mechanical benchmark m; (d) placebo slopes at 2022-01-01 and 2022-03-01 with
gas / residual-demand x near-margin controls.

Writes outputs/tables/gas_cap_dispatch_dose_{overlap,monthly,placebo}.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_offer_panel import ESSENTIAL, iberia_steps, italy_steps  # noqa: E402
from gas_cap_quantity_unit_dose import gas_weekly  # noqa: E402
from gas_cap_quantity_unit_dose_robust import ci, ebal, fe_ols, resample  # noqa: E402

DATA, T = ROOT / "data", ROOT / "outputs" / "tables"
WIN0, END = pd.Timestamp("2021-10-01"), pd.Timestamp("2023-06-30")
CAP0 = pd.Timestamp("2022-06-15")
PLACEBOS = [pd.Timestamp("2022-01-01"), pd.Timestamp("2022-03-01")]


def week(d: pd.Series) -> pd.Series:
    return d.dt.to_period("W").dt.start_time


def capacity(s: pd.DataFrame) -> pd.Series:
    off = s.groupby(["unit", "date", "period"]).mw.sum()
    return off[off.index.get_level_values("date") < CAP0].groupby("unit").quantile(0.99)


def iberia_hours() -> tuple[pd.DataFrame, pd.Series]:
    s, cost = iberia_steps()
    s["date"] = pd.to_datetime(s.date)
    K = capacity(s)
    zone = s.groupby("unit").country.agg(lambda x: x.mode().iat[0])
    parts = []
    for ym in pd.period_range(WIN0, END, freq="M"):
        p = pd.read_parquet(DATA / "omie" / "pdbf" / "parquet" / f"pdbf_{ym.strftime('%Y%m')}.parquet",
                            columns=["date", "period", "unit", "schedule_mw"])
        parts.append(p[p.unit.isin(K.index)])
    out = pd.concat(parts)
    out["date"] = pd.to_datetime(out.date)
    out = out.groupby(["unit", "date", "period"]).schedule_mw.sum().clip(lower=0).rename("mw").reset_index()
    pr = pd.read_parquet(DATA / "omie" / "prices" / "omie_day_ahead_prices.parquet",
                         columns=["date", "period", "price_es", "price_pt"])
    pr["date"] = pd.to_datetime(pr.date)
    pr = pr[pr.date.between(WIN0 - pd.Timedelta(days=1), END)]
    pl = pr.melt(id_vars=["date", "period"], value_vars=["price_es", "price_pt"], var_name="zone", value_name="p")
    pl["zone"] = pl.zone.map({"price_es": "ES", "price_pt": "PT"})
    pl["date"] = pl.date + pd.Timedelta(days=1)          # yesterday's price, same period
    grid = cost[cost.date.between(WIN0, END) & cost.unit.isin(K.index)][["unit", "date", "cost_gross"]].copy()
    grid["date"] = pd.to_datetime(grid.date)
    grid["zone"] = grid.unit.map(zone)
    grid = grid.merge(pl, on=["date", "zone"])
    h = grid.merge(out, on=["unit", "date", "period"], how="left")
    h["mw"] = h.mw.fillna(0.0)
    h["y"] = h.mw / h.unit.map(K)
    h["x"] = h.p - h.cost_gross
    S = cost.assign(date=pd.to_datetime(cost.date)).groupby("date").subsidy.max()
    firm = pd.read_parquet(ROOT / "outputs" / "tables" / "gas_cap_offer_panel.parquet", columns=["unit", "firm"]) \
        .drop_duplicates("unit").set_index("unit").firm
    h["firm"] = h.unit.map(firm).fillna(h.unit)
    return h[["unit", "firm", "date", "period", "y", "x"]], S


def italy_hours() -> tuple[pd.DataFrame, pd.DataFrame]:
    t, cost = italy_steps()
    t["date"] = pd.to_datetime(t.date)
    t = t[~t.unit.isin(ESSENTIAL)]
    K = capacity(t)
    zone = t.groupby("unit").zone.agg(lambda x: x.mode().iat[0])
    firm = t.groupby("unit").operator.agg(lambda x: x.mode().iat[0])
    price = t.groupby(["date", "period", "zone"]).price.first().rename("p").reset_index()
    price["date"] = price.date + pd.Timedelta(days=1)
    d = ds.dataset(DATA / "gme" / "offers" / "parquet")
    acc = d.to_table(filter=(pc.field("side") == "OFF") & (pc.field("status") == "ACC") & pc.field("unit").isin(list(K.index)),
                     columns=["date", "period", "unit", "quantity_mwh"]).to_pandas()
    acc["unit"] = acc.unit.astype(str)
    acc["date"] = pd.to_datetime(acc.date)
    acc = acc.groupby(["unit", "date", "period"]).quantity_mwh.sum().rename("mw").reset_index()
    tot = d.to_table(filter=(pc.field("status") == "ACC"), columns=["date", "side", "quantity_mwh"]).to_pandas()
    tot["date"] = pd.to_datetime(tot.date)
    tot = tot.groupby(["date", "side"], observed=True).quantity_mwh.sum().unstack()
    grid = cost[cost.unit.isin(K.index)][["unit", "date", "cost_gross"]].copy()
    grid["date"] = pd.to_datetime(grid.date)
    grid = grid[grid.date.between(WIN0, END)]
    grid["zone"] = grid.unit.map(zone)
    grid = grid.merge(price, on=["date", "zone"])
    h = grid.merge(acc, on=["unit", "date", "period"], how="left")
    h["mw"] = h.mw.fillna(0.0)
    h["y"] = h.mw / h.unit.map(K)
    h["x"] = h.p - h.cost_gross
    h["firm"] = h.unit.map(firm)
    return h[["unit", "firm", "date", "period", "y", "x"]], tot


def controls(tot_it: pd.DataFrame) -> dict:
    g = gas_weekly()
    f = {}
    for i in (1775, 1777, 1779):
        e = pd.read_parquet(DATA / "esios" / f"esios_{i}.parquet", columns=["datetime", "value"])
        e["date"] = pd.to_datetime(e.datetime.str[:10])
        f[i] = e.groupby("date").value.sum()
    rd = (f[1775] - f[1777] - f[1779]).dropna()
    st = pd.read_parquet(DATA / "esios" / "esios_623.parquet", columns=["datetime", "value"])
    st["w"] = pd.to_datetime(st.datetime.str[:10])
    st = st.set_index("w").value.asfreq("W-MON").ffill().shift(2)      # published ~10 days late: two weeks' lag
    ib = pd.DataFrame({"gas": g[True], "rd": rd.groupby(week(rd.index.to_series())).mean(), "stor": st})
    dem = tot_it["BID"]
    imp = tot_it["BID"] - tot_it["OFF"]
    it = pd.DataFrame({"gas": g[False], "dem": dem.groupby(week(dem.index.to_series())).mean(),
                       "imp": imp.groupby(week(imp.index.to_series())).mean()})
    std = lambda d: (d - d.mean()) / d.std()
    return {True: std(ib), False: std(it)}


def weekly(h: pd.DataFrame, D: pd.Timestamp, Sp: pd.Series, stop: pd.Timestamp, ctl: pd.DataFrame,
           keep_weeks) -> pd.DataFrame:
    """Plant-week frame: y, g (dose from date D), z (near-margin propensity before D), control x z columns."""
    h = h.assign(w=week(h.date))
    pre = h[(h.date >= WIN0) & (h.date < D)]
    z = ((pre.x <= 0) & (pre.x + 100.0 > 0)).groupby(pre.unit).mean().rename("z")
    S = h.date.map(Sp).fillna(0.0)
    flip = ((h.x <= 0) & (h.x + S > 0) & (h.date >= D) & (h.date <= stop)).astype(float)
    d = h.assign(g=flip).groupby(["unit", "firm", "w"])[["y", "g"]].mean().reset_index()
    d = d[d.w.isin(keep_weeks)].merge(z, left_on="unit", right_index=True)
    xs = []
    for k in ctl.columns:
        d[f"c_{k}"] = d.w.map(ctl[k]).to_numpy() * d.z
        xs.append(f"c_{k}")
    return d.dropna(subset=xs).reset_index(drop=True), xs


def benchmark(h: pd.DataFrame) -> float:
    p = h[h.date < CAP0].assign(w=week(h.date), im=lambda d: (d.x > 0).astype(float))
    grp = p.groupby(["unit", "w"])
    yd = p.y - grp.y.transform("mean")
    xd = p.im - grp.im.transform("mean")
    return float((yd * xd).sum() / (xd ** 2).sum())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=199)
    a = ap.parse_args()
    rng = np.random.default_rng(20261108)
    hib, S = iberia_hours()
    hit, tot = italy_hours()
    ctl = controls(tot)
    H = {True: hib, False: hit}
    weeks = pd.date_range(WIN0.to_period("W").start_time, END, freq="W-MON")
    for c in (True, False):          # plants with output data in >= 70% of weeks
        cover = H[c].assign(w=week(H[c].date)).groupby("unit").w.nunique() / len(weeks)
        H[c] = H[c][H[c].unit.isin(cover.index[cover >= 0.70])]
        print(f"{'Iberia' if c else 'Italy'}: {H[c].unit.nunique()} plants, {H[c].firm.nunique()} firms, "
              f"{len(H[c]):,} plant-hours")

    # (c) mechanical benchmark
    m = {c: benchmark(H[c]) for c in (True, False)}
    print(f"\n(c) mechanical benchmark m (capacity factor, in vs out of the money, within plant-week): "
          f"Iberia {m[True]:.3f}, Italy {m[False]:.3f}")

    # (a) overlap
    post = {c: weekly(H[c], CAP0, S, END, ctl[c], weeks)[0] for c in (True, False)}
    pm = {c: post[c][post[c].w.map(S.groupby(week(S.index.to_series())).mean()).fillna(0) > 0]
          .groupby("unit").g.mean() for c in (True, False)}
    zz = {c: post[c].drop_duplicates("unit").set_index("unit").z for c in (True, False)}
    rows = []
    for c in (True, False):
        q = pm[c].quantile([0.1, 0.25, 0.5, 0.75, 0.9])
        rows.append({"country": "Iberia" if c else "Italy (would-be)", "plants": len(pm[c]),
                     **{f"dose_p{int(k * 100)}": v for k, v in q.items()}, "dose_mean": pm[c].mean(),
                     "z_mean": zz[c].mean()})
    Xi = pd.DataFrame({"dose": pm[True], "z": zz[True]}).dropna()
    Xt = pd.DataFrame({"dose": pm[False], "z": zz[False]}).dropna()
    w = ebal(Xt.to_numpy(), Xi.mean().to_numpy())
    neff = float(w.sum() ** 2 / (w ** 2).sum())
    rows.append({"country": "Italy entropy-balanced to Iberia", "plants": len(Xt), "effective_plants": neff,
                 "dose_mean": float((Xt.dose * w).sum() / w.sum()), "z_mean": float((Xt.z * w).sum() / w.sum()),
                 "max_weight": float(w.max())})
    ov = pd.DataFrame(rows)
    ov.to_csv(T / "gas_cap_dispatch_dose_overlap.csv", index=False)
    print("\n(a) overlap, plant mean post-cap dose (weeks with S > 0):")
    print(ov.round(3).to_string(index=False))

    # (b) monthly capacity factor
    mon = pd.DataFrame({("Iberia" if c else "Italy"): H[c][H[c].date < pd.Timestamp("2022-07-01")]
                        .groupby(H[c].date.dt.to_period("M")).y.mean() for c in (True, False)})
    mon.to_csv(T / "gas_cap_dispatch_dose_monthly.csv")
    print("\n(b) mean capacity factor by month:")
    print(mon.round(3).T.to_string())

    # (d) placebos
    out = []
    stop = CAP0 - pd.Timedelta(days=1)
    pre_weeks = [x for x in weeks if x + pd.Timedelta(days=6) < CAP0]
    for P in PLACEBOS:
        Sp = pd.Series(S.reindex(pd.date_range(CAP0, CAP0 + (stop - P))).fillna(0.0).to_numpy(),
                       index=pd.date_range(P, stop))
        L, X = {}, {}
        for c in (True, False):
            L[c], X[c] = weekly(H[c], P, Sp, stop, ctl[c], pre_weeks)
        b = {c: fe_ols(L[c], ["g"] + X[c])[0] for c in (True, False)}
        dr = []
        for _ in range(a.reps):
            try:
                dr.append([fe_ols(resample(L[c], rng), ["g"] + X[c])[0] for c in (True, False)])
            except (np.linalg.LinAlgError, ValueError):
                dr.append([np.nan, np.nan])
        dr = np.array(dr)
        for j, (name, b0, col) in enumerate([("Iberia", b[True], dr[:, 0]), ("Italy", b[False], dr[:, 1]),
                                            ("triple", b[True] - b[False], dr[:, 0] - dr[:, 1])]):
            lo, hi = ci(col)
            mde = 2.8 * np.nanstd(col, ddof=1)
            out.append({"placebo": P.date(), "estimate": name, "b": b0, "lo": lo, "hi": hi, "mde": mde,
                        "mde_over_m_ib": mde / m[True], "excludes_0": not (lo <= 0 <= hi),
                        "mean_g_dosed": (L[True] if j != 1 else L[False]).query("g > 0").g.mean()})
    pl = pd.DataFrame(out)
    pl.to_csv(T / "gas_cap_dispatch_dose_placebo.csv", index=False)
    print(f"\n(d) placebos, firm block bootstrap {a.reps} (MDE also as a share of m_IB = {m[True]:.3f}):")
    print(pl.round(3).to_string(index=False))

    ibp, trp = pl[pl.estimate == "Iberia"], pl[pl.estimate == "triple"]
    r1 = "STOP" if (ibp.excludes_0.any() or (ibp.mde > 0.5 * m[True]).any()) else "passes"
    r2 = neff >= 20 and not trp.excludes_0.any() and (trp.mde <= 0.5 * m[True]).all()
    print(f"\nRule 1 (within Iberia): {r1}")
    print(f"Rule 2 (triple): {'readable in step 2' if r2 else 'not usable'} "
          f"(effective Italian plants {neff:.1f}; triple placebo excl. 0: {trp.excludes_0.tolist()}; "
          f"MDE/m_IB {trp.mde_over_m_ib.round(2).tolist()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
