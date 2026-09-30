#!/usr/bin/env python3
"""The five large firms' markup term X for every period, as built and exposed.

    .venv/bin/python scripts/analysis/firm_x.py            # build + validate
    .venv/bin/python scripts/analysis/firm_x.py --report   # validate only

X = n / slope, the Hortacsu-Puller markup term, from the bids, for EDP,
Iberdrola, Endesa, Naturgy and Repsol, in every period:

    n       = cleared sell - cleared buy over the firm's units
    slope   = (all offered MW within +/-H of p* - the firm's own offered MW in
               that band, both sides) / 2H
    X       = n / slope, undefined below MIN_SLOPE

with p* the Spanish price. Two definitions of "the firm's units":

    *_built   every unit whose owner rolls up to the firm (owner_group)
    exposed   the same, less regulated pass-through suppliers (is_pass_through;
              framework spec §2.4). Their volume leaves n and their offers
              count as a rival's.

Split periods and clearing-identity failures are flagged (`clean`), zero prices
too (`zero_price`: p* <= 1), not dropped. Legs A and B use clean periods; the
firm panel's periods are `clean & ~zero_price`.

Supersedes edp_x_all_periods.py (EDP only, as built), which it reproduces.

VALIDATION (exits non-zero on failure). Against firm_incentive_net.parquet on
the periods it keeps: the as-built net and slope must reproduce net_mw and
slope_net_h5, and the exposed ones net_exp_mw and slope_exp_h5 -- a second,
independent computation of the same correction. Every period x firm is present,
and the exposed slope is never below the as-built one.
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
from omie_owner import is_pass_through, owner_group  # noqa: E402
from residual_demand import IDENTITY_TOL, KEY, ZERO_PRICE, cleared_by_period  # noqa: E402

DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
PANEL = ROOT / "outputs/tables/firm_incentive_net.parquet"   # firm_incentive_rebuild.py
OUT = ROOT / "outputs/tables/firm_x.parquet"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")
H = 5.0
MIN_SLOPE = 5.0   # MW per EUR/MWh
MW = ["net_built_mw", "net_mw", "q_mw", "pt_net_mw", "own_band_built_mw", "own_band_mw"]


def unit_map() -> pd.DataFrame:
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["unit", "agent_owner"])
    u["firm"] = u.agent_owner.map(owner_group)
    u["pt"] = u.agent_owner.map(is_pass_through).astype(bool)
    return u[u.firm.isin(FIRMS)].set_index("unit")[["firm", "pt"]]


def prices() -> pd.DataFrame:
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "resolution_min", "price_es", "price_pt"])
    px["date"] = pd.to_datetime(px.date)
    px["split"] = px.price_es != px.price_pt
    return px.rename(columns={"price_es": "p_star"})[KEY + ["resolution_min", "p_star", "split"]]


def month(ym: str, umap: pd.DataFrame, px: pd.DataFrame) -> pd.DataFrame:
    b = pq.read_table(BIDS / f"bids_{ym}.parquet",
                      columns=["date", "period", "unit", "side", "status", "power_mw",
                               "price_eur_mwh"]).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b["unit"] = b.unit.astype(str)
    b["side"] = b.side.astype(str)
    b["status"] = b.status.astype(str)
    idg = cleared_by_period(b)[KEY + ["identity_gap"]]

    m = b.join(umap, on="unit", how="inner")
    m["sgn"] = m.side.map({"V": 1.0, "C": -1.0})
    c = m[m.status == "C"]
    fk = KEY + ["firm"]
    net_b = (c.power_mw * c.sgn).groupby([c.date, c.period, c.firm]).sum().rename("net_built_mw")
    ce, cp = c[~c.pt], c[c.pt]
    net_e = (ce.power_mw * ce.sgn).groupby([ce.date, ce.period, ce.firm]).sum().rename("net_mw")
    q_e = ce.power_mw.where(ce.side == "V", 0.0).groupby([ce.date, ce.period, ce.firm]).sum().rename("q_mw")
    pt = (cp.power_mw * cp.sgn).groupby([cp.date, cp.period, cp.firm]).sum().rename("pt_net_mw")

    o = b[b.status == "O"].merge(px[KEY + ["p_star"]], on=KEY, how="inner")
    o = o[(o.price_eur_mwh - o.p_star).abs() <= H]
    band = o.groupby(KEY).power_mw.sum().rename("band_mw")
    om = o.join(umap, on="unit", how="inner")
    own_b = om.groupby([om.date, om.period, om.firm]).power_mw.sum().rename("own_band_built_mw")
    ome = om[~om.pt]
    own_e = ome.groupby([ome.date, ome.period, ome.firm]).power_mw.sum().rename("own_band_mw")

    per = px[px.date.dt.strftime("%Y%m") == ym]
    out = per.merge(pd.DataFrame({"firm": FIRMS}), how="cross")
    out = out.merge(idg, on=KEY, how="left").merge(band.reset_index(), on=KEY, how="left")
    firm_cols = pd.concat([net_b, net_e, q_e, pt, own_b, own_e], axis=1).reset_index()
    out = out.merge(firm_cols, on=fk, how="left")
    out[MW + ["band_mw"]] = out[MW + ["band_mw"]].fillna(0.0)
    out["slope_built"] = (out.band_mw - out.own_band_built_mw) / (2 * H)
    out["slope_net"] = (out.band_mw - out.own_band_mw) / (2 * H)
    out["X_built"] = np.where(out.slope_built >= MIN_SLOPE, out.net_built_mw / out.slope_built, np.nan)
    out["X"] = np.where(out.slope_net >= MIN_SLOPE, out.net_mw / out.slope_net, np.nan)
    out["zero_price"] = out.p_star <= ZERO_PRICE
    out["clean"] = (~out.split) & (out.identity_gap <= IDENTITY_TOL)
    return out


def build() -> pd.DataFrame:
    umap, px = unit_map(), prices()
    months = sorted(f.stem.split("_")[1] for f in BIDS.glob("bids_*.parquet"))
    parts = []
    for ym in months:
        parts.append(month(ym, umap, px))
        print(f"  {ym}", flush=True, file=sys.stderr)
    d = pd.concat(parts, ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(d):,} firm-periods)")
    return d


def compare(m: pd.DataFrame, a: str, b: str) -> tuple[float, float]:
    diff = (m[a] - m[b]).abs()
    print(f"    {a:14s} vs {b:14s} corr {m[a].corr(m[b]):.6f}   median |diff| {diff.median():.4f}   "
          f"p99 |diff| {diff.quantile(.99):.4f}   exact (<1e-3) {(diff < 1e-3).mean():.3f}")
    return m[a].corr(m[b]), diff.median()


def report(d: pd.DataFrame) -> bool:
    bad = []
    n_periods = d.drop_duplicates(KEY).shape[0]
    if len(d) != n_periods * len(FIRMS):
        bad.append(f"rows {len(d):,} != periods {n_periods:,} x {len(FIRMS)} firms")
    v = (d.slope_net < d.slope_built - 1e-6).mean()
    print(f"exposed slope below as-built slope on {v:.6f} of firm-periods (must be 0)")
    if v > 0:
        bad.append("slope_net < slope_built")

    p = pd.read_parquet(PANEL, columns=KEY + ["firm", "net_mw", "slope_net_h5", "net_exp_mw",
                                               "slope_exp_h5"])
    p = p[p.firm.isin(FIRMS)]
    p["date"] = pd.to_datetime(p.date)
    m = d.merge(p, on=KEY + ["firm"], how="inner", suffixes=("", "_panel"))
    print(f"\nVALIDATION against {PANEL.name}, {len(m):,} firm-periods")
    for f, g in m.groupby("firm"):
        print(f"  {f}")
        for a, b in (("net_built_mw", "net_mw_panel"), ("slope_built", "slope_net_h5"),
                     ("net_mw", "net_exp_mw"), ("slope_net", "slope_exp_h5")):
            r, med = compare(g, a, b)
            if not (r > 0.9999 and med < 1e-3):
                bad.append(f"{f}: {a} does not reproduce {b} (corr {r:.6f}, median {med:.4f})")

    c = d[d.clean].assign(year=d.date.dt.year)
    for col, lab in (("net_built_mw", "as built"), ("net_mw", "EXPOSED")):
        print(f"\nNET-BUYER SHARE of clean periods, {lab}")
        print(c.assign(b=c[col] < 0).groupby(["firm", "year"]).b.mean().unstack(0).round(2).to_string())
    day = c.assign(buyer=c.net_mw < 0).groupby(["firm", "year", "date"]).buyer.mean()
    both = ((day > 0) & (day < 1)).groupby(["firm", "year"]).sum().unstack(0)
    print("\nFIRM-DAYS WITH BOTH SIGNS of the exposed position (leg D's sample)")
    print(both.to_string())
    print(f"  total: {both.sum().to_dict()}")

    for b_ in bad:
        print(f"  FAIL {b_}")
    return not bad


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    d = pd.read_parquet(OUT) if args.report else build()
    return 0 if report(d) else 1


if __name__ == "__main__":
    raise SystemExit(main())
