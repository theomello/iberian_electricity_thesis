#!/usr/bin/env python3
"""EDP's markup term X for every period, the zero-price ones included.

    .venv/bin/python scripts/analysis/edp_x_all_periods.py            # build + validate
    .venv/bin/python scripts/analysis/edp_x_all_periods.py --report   # validate only

WHY

Leg B (`water_value_across_days.py`, `notes/rq-midday-hydro.md` §3.18) averages
EDP's X over each day and instruments it with the day's offered solar. X came
from the firm panel, which drops every period cleared at or below 1 EUR/MWh
(`residual_demand.ZERO_PRICE`), because its elasticity eta = slope * p / q means
nothing at a zero price. Those are the sunny middays. So on the sunniest days
the day's mean X was taken over the fewer, dearer periods left, which weakens
the first stage exactly where solar should move X most: 2024-26, F = 12.

X itself is defined at any price. So it is rebuilt here from the bids for every
period, with the panel's own definitions:

    n         = cleared sell - cleared buy over every unit EDP owns, EDP Comercial
                included (as in edp_hydro_panel.py)
    slope_net = (all offered MW within +/-5 EUR/MWh of p*
                 - EDP's own offered MW in that band, both sides) / 10
    X         = n / slope_net, undefined below MIN_SLOPE

with p* the Spanish price. Split periods (ES != PT) and clearing-identity
failures are flagged, not dropped, so the consumer chooses; Leg B drops both,
as the panel does.

The build is validated against the panel's X on the periods the panel keeps. The
two must agree, or the zero-price periods are being measured on a different
basis from the rest.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_owner import owner_group  # noqa: E402
from residual_demand import IDENTITY_TOL, KEY, ZERO_PRICE, cleared_by_period  # noqa: E402

DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
PANEL = ROOT / "outputs/tables/edp_hydro_panel.parquet"
OUT = ROOT / "outputs/tables/edp_x_all_periods.parquet"
OWN = ("EDP", "EDP COMERCIAL")
H = 5.0
MIN_SLOPE = 5.0   # MW per EUR/MWh, as in edp_hydro_panel.py


def own_units() -> set[str]:
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["unit", "agent_owner"])
    return set(u.unit[u.agent_owner.map(owner_group).isin(OWN)])


def prices() -> pd.DataFrame:
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "price_es", "price_pt"])
    px["date"] = pd.to_datetime(px.date)
    px["split"] = px.price_es != px.price_pt
    return px.rename(columns={"price_es": "p_star"})[KEY + ["p_star", "split"]]


def month(ym: str, own: set[str], px: pd.DataFrame) -> pd.DataFrame:
    b = pq.read_table(BIDS / f"bids_{ym}.parquet",
                      columns=["date", "period", "unit", "side", "status", "power_mw",
                               "price_eur_mwh"]).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b["side"] = b.side.astype(str)
    b["status"] = b.status.astype(str)
    b["own"] = b.unit.astype(str).isin(own)

    idg = cleared_by_period(b)[KEY + ["identity_gap"]]
    c = b[(b.status == "C") & b.own]
    net = (c.power_mw * c.side.map({"V": 1.0, "C": -1.0})).groupby([c.date, c.period]).sum()

    o = b[b.status == "O"].merge(px, on=KEY, how="inner")
    o = o[(o.price_eur_mwh - o.p_star).abs() <= H]
    band = o.groupby(KEY).power_mw.sum().rename("band_mw")
    own_band = o[o.own].groupby(KEY).power_mw.sum().rename("own_band_mw")

    out = px[px.date.dt.strftime("%Y%m") == ym].merge(idg, on=KEY, how="left")
    out = out.merge(net.rename("net_mw").reset_index(), on=KEY, how="left")
    out = out.merge(band.reset_index(), on=KEY, how="left").merge(own_band.reset_index(), on=KEY, how="left")
    out[["net_mw", "band_mw", "own_band_mw"]] = out[["net_mw", "band_mw", "own_band_mw"]].fillna(0.0)
    out["slope_net"] = (out.band_mw - out.own_band_mw) / (2 * H)
    out["X"] = np.where(out.slope_net >= MIN_SLOPE, out.net_mw / out.slope_net, np.nan)
    out["zero_price"] = out.p_star <= ZERO_PRICE
    out["clean"] = (~out.split) & (out.identity_gap <= IDENTITY_TOL)
    return out


def build() -> pd.DataFrame:
    own, px = own_units(), prices()
    months = sorted(f.stem.split("_")[1] for f in BIDS.glob("bids_*.parquet"))
    parts = []
    for ym in months:
        parts.append(month(ym, own, px))
        print(f"  {ym}", flush=True, file=sys.stderr)
    d = pd.concat(parts, ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(d):,} periods)")
    return d


def report(d: pd.DataFrame) -> None:
    p = pd.read_parquet(PANEL, columns=["date", "period", "group", "X", "net_mw", "slope_net"])
    p = p[p.group == "EDP"].drop_duplicates(KEY)
    p["date"] = pd.to_datetime(p.date)
    m = d.merge(p, on=KEY, how="inner", suffixes=("", "_panel")).dropna(subset=["X", "X_panel"])
    print("\nVALIDATION against the panel, on the periods it keeps")
    print(f"  periods compared         {len(m):,}")
    for c in ("net_mw", "slope_net", "X"):
        diff = (m[c] - m[f"{c}_panel"]).abs()
        print(f"  {c:10s} corr {m[c].corr(m[f'{c}_panel']):.6f}   median |diff| {diff.median():.4f}   "
              f"p99 |diff| {diff.quantile(.99):.4f}   exact (<1e-6) {(diff < 1e-6).mean():.3f}")

    c = d[d.clean]
    print("\nWHAT THE ZERO-PRICE PERIODS ADD (clean periods: no split, identity holds)")
    t = c.assign(year=c.date.dt.year).groupby("year").agg(
        zero_share=("zero_price", "mean"),
        X_kept=("X", lambda s: s[~c.loc[s.index, "zero_price"]].median()),
        X_zero=("X", lambda s: s[c.loc[s.index, "zero_price"]].median()),
        slope_zero=("slope_net", lambda s: s[c.loc[s.index, "zero_price"]].median()))
    print(t.round(3).to_string())


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    d = pd.read_parquet(OUT) if args.report else build()
    report(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
