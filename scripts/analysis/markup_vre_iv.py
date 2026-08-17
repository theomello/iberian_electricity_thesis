#!/usr/bin/env python3
"""Do renewables raise firm-level markups? Causal, with a robust outcome.

    .venv/bin/python scripts/analysis/markup_vre_iv.py
    .venv/bin/python scripts/analysis/markup_vre_iv.py --band 2 --top 12

WHY THIS OUTCOME AND NOT AN OFFER PRICE

Every behavioural measure built from offer prices in this repo has failed a
robustness check -- levy passthrough, gas-cap passthrough, bid-curve steepness.
The reason is the same each time: offer price distributions have enormous tails,
withholding bids and cost-revealing bids are pooled, and no principled rule
separates them, so the sign follows whichever trimming or banding rule is
chosen.

The markup from the Hortacsu-Puller first-order condition is not built from
offer prices at all:

    markup_it  =  p_t - MC_it  =  (q_it - theta_it) / |RD'_it|

  q       scheduled output, an accounting quantity from PDBF
  theta   contract position, a published field (PDBF role 4)
  |RD'|   residual demand slope facing the firm, the same object as eta

All three are direct computations and all three survived every check. The markup
inherits their behaviour rather than the offer distribution's, which is what
makes it usable as a dependent variable.

THE DESIGN

    markup_it = beta * vre_share_t + firm FE + month FE + hour FE + controls

with `vre_share` instrumented by ERA5 wind speed and irradiance. Renewable share
varies **hour to hour**, so month fixed effects absorb fuel, carbon and every
slow-moving cost driver while leaving the identifying variation intact. That is
the structure the policy designs lacked: their treatment was a monthly series
that time effects absorbed.

`beta > 0` means renewable growth raises markups.

WHAT THE CHECKS ARE FOR

The band used for the residual demand slope, the set of firms, and the sample of
months are all choices. A result that moves with them is a choice, not a
finding -- that is the lesson of the four withdrawn results. `--band` and
`--top` exist to be varied, and the trimmed rows below report whether the
estimate survives dropping the extreme markups.
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


def owner_map() -> dict[str, str]:
    ul = pq.read_table(DATA / "omie/registry/omie_unit_lists.parquet").to_pandas()
    o = ul.dropna(subset=["agent_owner"]).drop_duplicates("unit", keep="last")
    return dict(zip(o.unit, o.agent_owner))


def firm_position(ym: str, owner: dict) -> pd.DataFrame:
    """Total scheduled output and contracted volume per firm-period."""
    f = DATA / "omie/pdbf/parquet" / f"pdbf_{ym}.parquet"
    if not f.exists():
        return pd.DataFrame()
    t = pq.read_table(f, columns=["date", "period", "unit", "schedule_mw",
                                  "resolution_min", "role_code"]).to_pandas()
    t = t[t.schedule_mw > 0].copy()
    t["e"] = t.schedule_mw * t.resolution_min / 60.0
    t["firm"] = t.unit.map(owner)
    t["date"] = pd.to_datetime(t.date)
    return t.groupby(["date", "period", "firm"], as_index=False).agg(
        q=("e", "sum"),
        theta=("e", lambda s: s[t.loc[s.index, "role_code"] == "4"].sum()))


def build(months: list[str], band: float, top: int) -> pd.DataFrame:
    owner = owner_map()
    eta = pq.read_table(ETA, columns=["date", "period", "utc_timestamp",
                                      "vre_share", "demand"]).to_pandas()
    eta["date"] = pd.to_datetime(eta.date)
    px = pq.read_table(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                       columns=["date", "period", "price_es"]).to_pandas()
    px["date"] = pd.to_datetime(px.date)

    pos = pd.concat([firm_position(m, owner) for m in months], ignore_index=True)
    pos = pos[pos.firm.notna()]
    top_firms = pos.groupby("firm").q.sum().nlargest(top).index.tolist()
    pos = pos[pos.firm.isin(top_firms)]

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
            for fm in top_firms:
                # Residual demand facing this firm excludes its own supply.
                slope = (tot - own.get(fm, 0.0) + buy) / (2 * band)
                if slope > 0:
                    rows.append((d, per, fm, p, slope))
    sl = pd.DataFrame(rows, columns=["date", "period", "firm", "p", "slope"])
    m = sl.merge(pos, on=["date", "period", "firm"], how="inner")
    m["markup"] = (m.q - m.theta) / m.slope
    m["lerner"] = m.markup / m.p

    m = m.merge(eta, on=["date", "period"], how="inner")
    w = pd.read_parquet(WX)
    w["hour_utc"] = pd.to_datetime(w.utc_timestamp, utc=True)
    m["hour_utc"] = pd.to_datetime(m.utc_timestamp, utc=True).dt.floor("h")
    m = m.merge(w.drop(columns=["utc_timestamp"]), on="hour_utc", how="inner")

    m["month"] = m.hour_utc.dt.to_period("M")
    m["hour"] = m.hour_utc.dt.hour
    m["wind"] = m.wind_speed_100m_wind_sites
    m["wind3"] = m.wind ** 3 / 1000.0
    m["rad"] = m.radiation_solar_sites / 100.0
    m["temp"] = m.temperature_2m_mean
    m["log_demand"] = np.log(m.demand.clip(lower=1))
    return m.dropna(subset=["markup", "vre_share", "wind", "rad", "temp"])


def demean(v, *codes):
    v = np.asarray(v, float).copy()
    for _ in range(300):
        prev = v.copy()
        for c in codes:
            v -= np.bincount(c, v)[c] / np.bincount(c)[c]
        if np.max(np.abs(v - prev)) < 1e-10:
            break
    return v


def fit(d: pd.DataFrame, ycol: str):
    fi = pd.factorize(d.firm)[0]
    mi = pd.factorize(d.month)[0]
    hi = pd.factorize(d.hour)[0]
    y = demean(d[ycol].to_numpy(), fi, mi, hi)
    x = demean(d.vre_share.to_numpy(), fi, mi, hi)
    ctrl = np.column_stack([demean(d[c].to_numpy(), fi, mi, hi)
                            for c in ("log_demand", "temp")])
    inst = np.column_stack([demean(d[c].to_numpy(), fi, mi, hi)
                            for c in ("wind", "wind3", "rad")])

    def ols(Y, X):
        b, *_ = np.linalg.lstsq(X, Y, rcond=None)
        e = Y - X @ b
        s2 = e @ e / max(len(Y) - X.shape[1], 1)
        return b, np.sqrt(np.diag(s2 * np.linalg.pinv(X.T @ X)))

    b1, se1 = ols(y, np.column_stack([x, ctrl]))
    bz, _ = ols(x, np.column_stack([inst, ctrl]))
    xhat = np.column_stack([inst, ctrl]) @ bz
    b2, se2 = ols(y, np.column_stack([xhat, ctrl]))
    return b1[0], se1[0], b2[0], se2[0], len(d)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--band", type=float, default=5.0)
    ap.add_argument("--top", type=int, default=8)
    args = ap.parse_args()

    months = [f"{y}{m}" for y in range(2018, 2027) for m in ("04", "10")]
    d = build(months, args.band, args.top)

    print(f"MARKUPS AND RENEWABLES   band +/-{args.band:g} EUR/MWh, "
          f"top {args.top} firms\n")
    print(f"  {len(d):,} firm-periods, {d.firm.nunique()} firms, "
          f"{d.month.nunique()} months")
    print(f"  median markup {d.markup.median():.1f} EUR/MWh, "
          f"median Lerner {d.lerner.median():.3f}, "
          f"median price {d.p.median():.1f}\n")

    print(f"{'outcome / sample':<34}{'OLS':>10}{'2SLS':>10}{'se':>9}"
          f"{'t':>7}{'obs':>9}")
    for lbl, x, yc in (("markup, EUR/MWh", d, "markup"),
                       ("  trimmed at p1/p99", d[d.markup.between(
                           d.markup.quantile(.01), d.markup.quantile(.99))], "markup"),
                       ("  trimmed at p5/p95", d[d.markup.between(
                           d.markup.quantile(.05), d.markup.quantile(.95))], "markup"),
                       ("Lerner index", d, "lerner"),
                       ("  trimmed at p1/p99", d[d.lerner.between(
                           d.lerner.quantile(.01), d.lerner.quantile(.99))], "lerner")):
        b1, s1, b2, s2, n = fit(x, yc)
        print(f"{lbl:<34}{b1:>10.4f}{b2:>10.4f}{s2:>9.4f}{b2/s2:>7.2f}{n:>9,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
