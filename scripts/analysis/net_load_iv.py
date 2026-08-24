#!/usr/bin/env python3
"""Heat, wind and rain as three instruments for one endogenous variable.

    .venv/bin/python scripts/analysis/net_load_iv.py

Inputs: outputs/tables/{heat_demand_panel,withholding_period_panel,
residual_demand_slope_full}.parquet, the weather indices, MITECO reservoirs.
Prints; writes nothing.

WHY COMBINE THEM, AND WHY NOT AS AN "EXTREME WEATHER INDEX"

The obvious way to combine heat, wind and rainfall is to build a single index of
weather extremity. That would be wrong. The three shocks act with different
signs through different channels — heat raises demand, wind adds supply, rain
shifts hydro's opportunity cost — and averaging them would net a demand shock
against a supply shock and call the result zero.

The right combination is to notice that all three move the **same economic
quantity**: how far up the thermal supply stack the market has to clear. That is
net load,

    NetLoad_t  =  demand_t  -  wind_t  -  solar_t

and it is what the markup theory actually depends on. The profit-maximising
markup is `q_i / |RD_i'|`; both terms are functions of where on the stack the
price is set, and weather enters only through that. So heat, wind and rain are
not three separate designs. They are **three instruments for one endogenous
regressor**, and the model is

    second stage:  y_it     = beta * NetLoad_t + alpha_i + tau_ym + ...
    first stage:   NetLoad_t = pi' Z_t + alpha_i + tau_ym + ...

    Z = {CDH, HDH, wind speed cubed, solar radiation, reservoir fill anomaly}

THREE THINGS THIS BUYS

1. **Power.** The heat shock alone is 537 MW of net load at one standard
   deviation. Wind swings are 3,814 MW. A first stage on all of them is far
   stronger than any single-shock reduced form this repo has run.
2. **The right estimand.** Testing each weather variable separately asks whether
   markups respond to *weather*, which nobody claims. This asks whether they
   respond to *scarcity*, which is the actual prediction.
3. **A testable exclusion restriction.** With more instruments than endogenous
   variables the restrictions are overidentifying, and disagreement between them
   is evidence that at least one is invalid.

HOW THE OVERIDENTIFICATION CHECK IS DONE HERE

Not with a Hansen J statistic, but by estimating the **just-identified model one
instrument at a time** and comparing the coefficients. That is more informative
than a single J: a J tells you the instruments disagree, this tells you *which*
one disagrees. If CDH-only, wind-only and reservoir-only 2SLS give materially
different betas, at least one instrument affects the outcome other than through
net load.

There is already a specific reason to expect heat to be the offender:
`withholding_extensive_margin.py` found declared outages themselves rising on
hot days (+0.41pp on a 2.2% base, t = 2.02). Turbine derating and cooling-water
limits are a direct heat-to-supply channel that bypasses net load entirely.

WHAT THIS DOES NOT FIX

If every instrument is invalid in the same direction, the estimates agree and
the overidentification check passes anyway. Agreement is weak evidence, not
proof. And net load is a **national** quantity, so with year-month fixed effects
the identifying variation is within-month day-to-day movement — the gas-price
path is absorbed at monthly frequency but not at daily.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs" / "tables"
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from hydro_spill_window_did import demean, ols_cluster  # noqa: E402
from heat_demand_conduct import firm_size  # noqa: E402


def net_load_daily() -> pd.DataFrame:
    """Daily mean net load in GW, from REE 5-minute actuals."""
    rt = pq.read_table(DATA / "ree/ree_realtime_5min.parquet",
                       columns=["utc_timestamp", "demand", "wind",
                                "solar_total"]).to_pandas()
    rt["date"] = pd.to_datetime(rt.utc_timestamp, utc=True) \
                   .dt.tz_convert("Europe/Madrid").dt.tz_localize(None) \
                   .dt.normalize()
    g = rt.groupby("date", as_index=False).agg(
        demand=("demand", "mean"), wind=("wind", "mean"),
        solar=("solar_total", "mean"))
    g["net_load"] = (g.demand - g.wind.fillna(0) - g.solar.fillna(0)) / 1000.0
    g["load"] = g.demand / 1000.0
    return g[["date", "net_load", "load"]]


def instruments() -> pd.DataFrame:
    t = pd.read_parquet(DATA / "weather/temperature_population_index.parquet")
    t["date"] = pd.to_datetime(t.utc_timestamp).dt.tz_convert(None).dt.normalize()
    td = t.groupby("date", as_index=False).agg(cdh=("cdh_es", "mean"),
                                               hdh=("hdh_es", "mean"))
    w = pd.read_parquet(DATA / "weather/weather_spain_aggregate.parquet")
    w["date"] = pd.to_datetime(w.utc_timestamp).dt.tz_convert(None).dt.normalize()
    wd = w.groupby("date", as_index=False).agg(
        wind3=("wind_speed_cubed", "mean"), rad=("radiation_solar_sites", "mean"))

    r = pd.read_parquet(DATA / "miteco/embalses_historico.parquet")
    r["date"] = pd.to_datetime(r.date)
    r = r.dropna(subset=["capacity_hm3", "stored_hm3"])
    r = r[r.capacity_hm3 > 0]
    nat = (r.groupby("date").agg(st=("stored_hm3", "sum"), cap=("capacity_hm3", "sum"))
             .assign(fill=lambda x: x.st / x.cap).reset_index())
    nat = (nat.set_index("date")
              .reindex(pd.date_range(nat.date.min(), "2026-05-31", freq="D"))
              .ffill(limit=10))
    nat.index.name = "date"
    nat = nat.reset_index()
    nat["week"] = nat.date.dt.isocalendar().week.astype(int)
    nat["resv"] = nat.fill - nat.groupby("week").fill.transform("mean")
    return td.merge(wd, on="date").merge(nat[["date", "resv"]], on="date")


def tsls(s: pd.DataFrame, y: str, x: str, Z: list[str], W: list[str],
         fe1: str, fe2: str, cl: str):
    """2SLS with two-way FE absorbed and cluster-robust SEs.

    Returns beta on x, its SE, the first-stage cluster-robust Wald F on the
    excluded instruments, and n.
    """
    cols = list(dict.fromkeys([y, x] + Z + W + [fe1, fe2, cl]))
    s = s[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 500:
        return None
    M = demean(s[[y, x] + Z + W].to_numpy(float),
               pd.factorize(s[fe1])[0], pd.factorize(s[fe2])[0])
    Y, X = M[:, 0], M[:, 1:2]
    Zm, Wm = M[:, 2:2 + len(Z)], M[:, 2 + len(Z):]
    g = pd.factorize(s[cl])[0]

    # first stage: x on [Z, W]
    A = np.hstack([Zm, Wm])
    pi, se_pi, e1 = ols_cluster(X[:, 0], A, g)
    Xhat = (A @ pi).reshape(-1, 1)
    # cluster-robust Wald on the excluded instruments
    AtA_inv = np.linalg.pinv(A.T @ A)
    meat = np.zeros((A.shape[1], A.shape[1]))
    for c in np.unique(g):
        m = g == c
        v = A[m].T @ e1[m]
        meat += np.outer(v, v)
    G = len(np.unique(g))
    V = (G / (G - 1)) * ((len(s) - 1) / (len(s) - A.shape[1])) \
        * AtA_inv @ meat @ AtA_inv
    R = np.zeros((len(Z), A.shape[1]))
    for i in range(len(Z)):
        R[i, i] = 1.0
    Wald = float(pi[:len(Z)] @ np.linalg.pinv(R @ V @ R.T) @ pi[:len(Z)])
    F = Wald / len(Z)

    # second stage
    B = np.hstack([Xhat, Wm])
    beta, _, _ = ols_cluster(Y, B, g)
    resid = Y - np.hstack([X, Wm]) @ beta        # residual at TRUE x, not xhat
    BtB_inv = np.linalg.pinv(B.T @ B)
    meat2 = np.zeros((B.shape[1], B.shape[1]))
    for c in np.unique(g):
        m = g == c
        v = B[m].T @ resid[m]
        meat2 += np.outer(v, v)
    V2 = (G / (G - 1)) * ((len(s) - 1) / (len(s) - B.shape[1])) \
        * BtB_inv @ meat2 @ BtB_inv
    return dict(beta=float(beta[0]), se=float(np.sqrt(V2[0, 0])),
                F=F, n=len(s), nclust=G)


def row(lbl, r, w=46):
    if r is None:
        print(f"{lbl:<{w}}{'insufficient obs':>46}")
        return
    print(f"{lbl:<{w}}{r['beta']:>12.4f}{r['se']:>10.4f}"
          f"{r['beta']/r['se']:>7.2f}{r['F']:>9.1f}{r['n']:>10,}{r['nclust']:>7}")


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()

    nl = net_load_daily()
    iv = instruments()
    base = nl.merge(iv, on="date", how="inner")

    # OUTCOME 1: thermal markup on the marginal accepted offer
    mk = pd.read_parquet(OUT / "heat_demand_panel.parquet")
    mk["date"] = pd.to_datetime(mk.date)
    mc = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet")
    mc = mc[~mc.eff_is_generic].copy()
    mc["date"] = pd.to_datetime(mc.date)
    mk = mk.merge(mc[["unit", "date", "marginal_cost_eur_mwh"]],
                  on=["unit", "date"], how="inner")
    mk["markup_acc"] = mk.marg_acc - mk.marginal_cost_eur_mwh
    lo, hi = mk.markup_acc.quantile([0.01, 0.99])
    mk["markup_acc"] = mk.markup_acc.clip(lo, hi)

    # OUTCOME 2: period-level withholding, if it has been built
    wh = None
    p = OUT / "withholding_period_panel.parquet"
    if p.exists():
        wh = pd.read_parquet(p)
        wh["date"] = pd.to_datetime(wh.date)
        wh = wh[wh.n_itm >= 4]
        wh["wh_rate"] = wh.n_notcleared / wh.n_itm

    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                         columns=["unit", "firm"])
    sz = firm_size()

    def prep(d):
        d = d.merge(ua, on="unit", how="left")
        d["size"] = d.firm.map(sz)
        d = d.merge(base, on="date", how="inner")
        d["ym"] = d.date.dt.to_period("M").astype(str)
        return d[(d.date >= "2018-01-01") & (d.date <= "2026-05-08")]

    mk = prep(mk)
    print("=" * 110)
    print("NET LOAD AS THE SINGLE CHANNEL — heat, wind and rain as instruments")
    print("=" * 110)
    print(f"  {len(mk):,} unit-days, {mk.unit.nunique()} units, "
          f"{mk.date.nunique():,} days")
    print(f"  net load: mean {mk.net_load.mean():.1f} GW, sd "
          f"{mk.net_load.std():.2f} GW  (load mean {mk.load.mean():.1f} GW)")
    print("\n  INSTRUMENT correlations with net load (raw):")
    for z, nm in (("cdh", "cooling degree hours"), ("hdh", "heating degree hours"),
                  ("wind3", "wind speed cubed"), ("rad", "solar radiation"),
                  ("resv", "reservoir fill anomaly")):
        print(f"    {nm:<24} {mk[z].corr(mk.net_load):+.3f}")

    ALL = ["cdh", "hdh", "wind3", "rad", "resv"]
    hdr = (f"\n{'specification':<46}{'beta':>12}{'se':>10}{'t':>7}"
           f"{'F(1st)':>9}{'obs':>10}{'clust':>7}")

    print("\n" + "-" * 110)
    print("OUTCOME: markup over plant-specific marginal cost (EUR/MWh per GW "
          "of net load)")
    print("-" * 110 + hdr)
    row("OLS (net load, no instrument)",
        (lambda r: r and dict(r, F=np.nan))(
            (lambda z: z and dict(beta=z["beta"], se=z["se"], n=z["n"],
                                  nclust=z["nclust"], F=np.nan))(
                (lambda: (lambda b: dict(beta=b["beta"], se=b["se"], n=b["n"],
                                         nclust=b["nclust"]))(
                    _ols(mk, "markup_acc", ["net_load"], "net_load")))())))
    row("2SLS, all five instruments",
        tsls(mk, "markup_acc", "net_load", ALL, [], "unit", "ym", "ym"))
    print("\n  just-identified, ONE instrument at a time — if these disagree,\n"
          "  at least one exclusion restriction fails")
    print("-" * 110 + hdr)
    for z, nm in (("cdh", "heat only (CDH)"), ("wind3", "wind only"),
                  ("rad", "solar radiation only"),
                  ("resv", "reservoir anomaly only")):
        row(f"2SLS — {nm}",
            tsls(mk, "markup_acc", "net_load", [z], [], "unit", "ym", "ym"))

    if wh is not None:
        wh = prep(wh)
        print("\n" + "-" * 110)
        print("OUTCOME: period-level withholding rate (share of in-the-money "
              "periods with no output)")
        print("-" * 110 + hdr)
        row("2SLS, all five instruments",
            tsls(wh, "wh_rate", "net_load", ALL, [], "unit", "ym", "ym"))
        for z, nm in (("cdh", "heat only (CDH)"), ("wind3", "wind only"),
                      ("resv", "reservoir anomaly only")):
            row(f"2SLS — {nm}",
                tsls(wh, "wh_rate", "net_load", [z], [], "unit", "ym", "ym"))

    print("\nRead: a strong first stage with a null second stage is the "
          "informative case —\nit says scarcity is well measured and markups "
          "do not respond to it.")
    return 0


def _ols(d, y, xs, j, fe1="unit", fe2="ym", cl="ym"):
    cols = list(dict.fromkeys([y] + xs + [fe1, fe2, cl]))
    s = d[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 300:
        return None
    M = demean(s[[y] + xs].to_numpy(float),
               pd.factorize(s[fe1])[0], pd.factorize(s[fe2])[0])
    g = pd.factorize(s[cl])[0]
    b, se, _ = ols_cluster(M[:, 0], M[:, 1:], g)
    k = xs.index(j)
    return dict(beta=b[k], se=se[k], n=len(s), nclust=len(np.unique(g)))


if __name__ == "__main__":
    raise SystemExit(main())
