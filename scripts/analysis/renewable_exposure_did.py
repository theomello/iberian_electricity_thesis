#!/usr/bin/env python3
"""Differential renewable exposure: treatment that varies ACROSS firms.

    .venv/bin/python scripts/analysis/renewable_exposure_did.py

WHY THIS DESIGN

Every causal attempt in this project has failed the same way. The levy, the gas
cap and the market renewable share are all **market-wide**: they hit every firm
in a period identically. With time fixed effects they are absorbed; without
them, a single time series masquerades as hundreds of thousands of observations
and the standard errors are fiction.

The fix is treatment that varies across firms at a point in time. Firms differ
enormously in how renewable their own portfolios are, so a high-renewable hour
is not the same event for a wind-heavy independent as for a thermal-heavy
utility:

    treat_it  =  vre_exposure_i  x  vre_share_t

`vre_exposure_i` is the wind-and-solar share of firm i's own capacity, fixed at
its **pre-2021 value** so it cannot respond to anything later in the sample.

That interaction buys the thing nothing else here has: **period fixed effects**.
A full date-x-period effect absorbs the renewable share itself, demand, the
clearing price, fuel costs, the policy environment -- every market-wide shock,
known or unknown. What identifies beta is only that firms with different
portfolios responded differently to the same hour. No market-wide confound can
survive that, because none of them varies across firms within a period.

Instrumented with `vre_exposure_i x weather_t`, which is the standard shift-share
construction: exogenous variation in the shock, differential exposure to it.

THE THREAT, STATED FIRST BECAUSE IT IS SERIOUS

The markup is `(q - theta)/|RD'|`, so it scales with the firm's own output `q`.
And a renewable-heavy firm mechanically produces *more* in a windy hour. So the
interaction predicts markup partly through `q`, with no conduct involved.

There is no clean fix. Controlling for `q` is a bad control -- it is an outcome
of the treatment. The `--control-q` flag reports it anyway, not as the preferred
specification but as a bound: if the estimate survives stripping the mechanical
channel crudely, that is informative; if it vanishes, the result was mechanical.

Both are reported. Neither should be called a finding without the other.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
WX = DATA / "weather" / "weather_spain_aggregate.parquet"
ETA = ROOT / "outputs" / "tables" / "residual_demand_slope_full.parquet"


def maps():
    ul = pq.read_table(DATA / "omie/registry/omie_unit_lists.parquet").to_pandas()
    o = ul.dropna(subset=["agent_owner"]).drop_duplicates("unit", keep="last")
    t = ul.dropna(subset=["technology"]).drop_duplicates("unit", keep="last")
    cap = ul.dropna(subset=["agent_owner"]).drop_duplicates("unit", keep="last")
    return (dict(zip(o.unit, o.agent_owner)), dict(zip(t.unit, t.technology)),
            cap)


def vre_exposure(owner: dict, tech: dict) -> pd.Series:
    """Wind+solar share of each firm's own scheduled output, fixed pre-2021.

    Predetermined by construction: measured only on months before the sample's
    policy and renewable-growth variation, so it cannot be a response to them.
    """
    frames = []
    for ym in ["201804", "201810", "201904", "201910", "202004", "202010"]:
        f = DATA / "omie/pdbf/parquet" / f"pdbf_{ym}.parquet"
        if not f.exists():
            continue
        t = pq.read_table(f, columns=["unit", "schedule_mw", "resolution_min"]
                          ).to_pandas()
        t = t[t.schedule_mw > 0].copy()
        t["e"] = t.schedule_mw * t.resolution_min / 60.0
        t["firm"] = t.unit.map(owner)
        t["tech"] = t.unit.map(tech).astype(str)
        t["vre"] = t.tech.str.contains("Eólica|Solar", case=False, regex=True)
        frames.append(t.groupby("firm").apply(
            lambda x: pd.Series({"tot": x.e.sum(), "v": x[x.vre].e.sum()}),
            include_groups=False))
    d = pd.concat(frames).groupby(level=0).sum()
    d = d[d.tot > 1e3]
    return (d.v / d.tot).rename("exposure")


def build(months, band, firms):
    owner, tech, _ = maps()
    eta = pq.read_table(ETA, columns=["date", "period", "utc_timestamp",
                                      "vre_share", "demand"]).to_pandas()
    eta["date"] = pd.to_datetime(eta.date)
    px = pq.read_table(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                       columns=["date", "period", "price_es"]).to_pandas()
    px["date"] = pd.to_datetime(px.date)

    pos = []
    for ym in months:
        f = DATA / "omie/pdbf/parquet" / f"pdbf_{ym}.parquet"
        if not f.exists():
            continue
        t = pq.read_table(f, columns=["date", "period", "unit", "schedule_mw",
                                      "resolution_min", "role_code"]).to_pandas()
        t = t[t.schedule_mw > 0].copy()
        t["e"] = t.schedule_mw * t.resolution_min / 60.0
        t["firm"] = t.unit.map(owner)
        t["date"] = pd.to_datetime(t.date)
        pos.append(t.groupby(["date", "period", "firm"], as_index=False).agg(
            q=("e", "sum"),
            theta=("e", lambda s: s[t.loc[s.index, "role_code"] == "4"].sum())))
    pos = pd.concat(pos, ignore_index=True)
    pos = pos[pos.firm.isin(firms)]

    rows = []
    for ym in months:
        f = DATA / "omie/bids/parquet" / f"bids_{ym}.parquet"
        if not f.exists():
            continue
        b = ds.dataset(f).to_table(
            filter=(pc.field("status") == "O"),
            columns=["date", "period", "unit", "side", "price_eur_mwh", "power_mw"]
        ).to_pandas()
        b["date"] = pd.to_datetime(b.date)
        b = b.merge(px, on=["date", "period"], how="inner")
        b["firm"] = b.unit.map(owner)
        for (d, per), g in b.groupby(["date", "period"], sort=False):
            p = g.price_es.iloc[0]
            if p <= 1:
                continue
            near = g[g.price_eur_mwh.between(p - band, p + band)]
            sell = near[near.side == "V"]
            buy = near[near.side == "C"].power_mw.sum()
            tot = sell.power_mw.sum()
            own = sell.groupby("firm").power_mw.sum()
            for fm in firms:
                slope = (tot - own.get(fm, 0.0) + buy) / (2 * band)
                if slope > 0:
                    rows.append((d, per, fm, p, slope))
    sl = pd.DataFrame(rows, columns=["date", "period", "firm", "p", "slope"])
    m = sl.merge(pos, on=["date", "period", "firm"], how="inner")
    m["markup"] = (m.q - m.theta) / m.slope

    m = m.merge(eta, on=["date", "period"], how="inner")
    w = pd.read_parquet(WX)
    w["hour_utc"] = pd.to_datetime(w.utc_timestamp, utc=True)
    m["hour_utc"] = pd.to_datetime(m.utc_timestamp, utc=True).dt.floor("h")
    m = m.merge(w.drop(columns=["utc_timestamp"]), on="hour_utc", how="inner")
    m["wind"] = m.wind_speed_100m_wind_sites
    m["rad"] = m.radiation_solar_sites / 100.0
    m["pid"] = m.date.astype(str) + "_" + m.period.astype(str)
    return m


def demean(v, *codes):
    v = np.asarray(v, float).copy()
    for _ in range(400):
        prev = v.copy()
        for c in codes:
            v -= np.bincount(c, v)[c] / np.bincount(c)[c]
        if np.max(np.abs(v - prev)) < 1e-10:
            break
    return v


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--band", type=float, default=5.0)
    ap.add_argument("--top", type=int, default=54)
    ap.add_argument("--control-q", action="store_true")
    args = ap.parse_args()

    owner, tech, _ = maps()
    exp = vre_exposure(owner, tech)
    months = [f"{y}{m}" for y in range(2021, 2027) for m in ("04", "10")]

    # Firm set: largest by pre-sample output, intersected with those we can
    # assign an exposure to.
    base = vre_exposure(owner, tech)
    firms = [f for f in base.index if isinstance(f, str)][:args.top]
    d = build(months, args.band, set(firms))
    d["exposure"] = d.firm.map(exp)
    d = d.dropna(subset=["exposure", "markup", "vre_share"])
    d["treat"] = d.exposure * d.vre_share
    d["z_wind"] = d.exposure * d.wind
    d["z_rad"] = d.exposure * d.rad

    fi = pd.factorize(d.firm)[0]
    pi = pd.factorize(d.pid)[0]      # full period effects: absorbs everything market-wide

    print(f"DIFFERENTIAL RENEWABLE EXPOSURE   band +/-{args.band:g}, "
          f"{d.firm.nunique()} firms\n")
    print(f"  {len(d):,} firm-periods, {d.pid.nunique():,} distinct periods")
    print(f"  exposure (own wind+solar share, fixed pre-2021): "
          f"median {d.exposure.median():.2f}, "
          f"p10 {d.exposure.quantile(.1):.2f}, p90 {d.exposure.quantile(.9):.2f}")
    print(f"  median markup {d.markup.median():.2f} EUR/MWh\n")
    print("  firm + FULL PERIOD fixed effects: every market-wide shock absorbed\n")

    def ols(Y, X):
        b, *_ = np.linalg.lstsq(X, Y, rcond=None)
        e = Y - X @ b
        s2 = e @ e / max(len(Y) - X.shape[1], 1)
        return b, np.sqrt(np.diag(s2 * np.linalg.pinv(X.T @ X)))

    print(f"{'specification':<32}{'OLS':>10}{'2SLS':>10}{'se':>9}{'t':>7}{'obs':>9}")
    for lbl, x in (("all", d),
                   ("trimmed p1/p99",
                    d[d.markup.between(d.markup.quantile(.01),
                                       d.markup.quantile(.99))]),
                   ("trimmed p5/p95",
                    d[d.markup.between(d.markup.quantile(.05),
                                       d.markup.quantile(.95))])):
        f2 = pd.factorize(x.firm)[0]
        p2 = pd.factorize(x.pid)[0]
        y = demean(x.markup.to_numpy(), f2, p2)
        t_ = demean(x.treat.to_numpy(), f2, p2)
        zs = np.column_stack([demean(x.z_wind.to_numpy(), f2, p2),
                              demean(x.z_rad.to_numpy(), f2, p2)])
        cols = [t_]
        if args.control_q:
            cols.append(demean(x.q.to_numpy(), f2, p2))
        X = np.column_stack(cols)
        b1, s1 = ols(y, X)
        bz, _ = ols(t_, zs)
        that = zs @ bz
        X2 = np.column_stack([that] + cols[1:])
        b2, s2 = ols(y, X2)
        print(f"{lbl:<32}{b1[0]:>10.4f}{b2[0]:>10.4f}{s2[0]:>9.4f}"
              f"{b2[0]/s2[0]:>7.2f}{len(x):>9,}")
    if args.control_q:
        print("\n  NOTE: q is a bad control -- an outcome of treatment. Reported "
              "as a bound on\n  the mechanical channel, not as the preferred "
              "specification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
