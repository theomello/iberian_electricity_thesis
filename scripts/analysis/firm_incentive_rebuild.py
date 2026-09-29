#!/usr/bin/env python3
"""Rebuild the firm incentive and ability indices on the right exposure and slope.

    .venv/bin/python scripts/analysis/residual_demand_firm.py --tier owner --full --save  # input
    .venv/bin/python scripts/analysis/firm_incentive_rebuild.py

Corrects the two defects recorded in `notes/rq-descriptive-price-formation.md`
§4.5 (2026-09-28), without rerunning the firm panel: it reads
`firm_residual_demand_full_owner.parquet` and adds corrected columns beside the
old ones, which are kept for the record.

1. EXPOSURE. The panel's `incentive_h* = ability * (q - theta)/q` takes q from
   the firm's AUCTION-cleared sales and theta from its BILATERAL schedule.
   Bilateral energy never enters the auction, so contracts are subtracted twice.
   The firm's exposure to the auction price is its NET AUCTION POSITION,
   n = cleared sales - cleared purchases over every unit it owns (all roles):
       incentive_net_h = ability * n/q = n / (100 |RD'_net|)
   in EUR/MWh per 1% of output withheld, the same scale as ability. Negative for
   a net buyer.

2. SLOPE. The panel removes a firm's own SELL offers from the band around p*
   but maps only supply-role units, so the firm's own DEMAND bids near p* were
   counted as everyone else's (`own_demand_in_band.py`). Here every unit the
   firm owns is mapped, and its own buy offers inside +/-h of p* are removed too:
       slope_net_h   = slope_i_h - own_buy_band_h / 2h
       ability_net_h = q / (100 slope_net_h)
   Undefined below MIN_SLOPE: a band the firm's own demand nearly fills leaves a
   slope just above zero and an index that is a division artefact.

Owner groups come from `lib/omie_owner.owner_group`, as in the panel. Periods
and p* are the panel's own (p* is the Spanish price; split periods are already
excluded there).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_owner import owner_group  # noqa: E402
from residual_demand import BANDWIDTHS  # noqa: E402

DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
PANEL = ROOT / "outputs/tables/firm_residual_demand_full_owner.parquet"
OUT = ROOT / "outputs/tables/firm_incentive_net.parquet"
MIN_SLOPE = 5.0     # MW per EUR/MWh, as in edp_hydro_panel.py
TABLE_FIRMS = ["EDP", "IBERDROLA", "ENDESA", "NATURGY", "ACCIONA", "AXPO", "REPSOL"]
KEY = ["date", "period"]


def unit_firm() -> pd.Series:
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["unit", "agent_owner"])
    return pd.Series(u.agent_owner.map(owner_group).to_numpy(), index=u.unit).dropna()


def month_extras(ym: str, fmap: pd.Series, pstar: pd.DataFrame) -> pd.DataFrame:
    b = pq.read_table(BIDS / f"bids_{ym}.parquet",
                      columns=["date", "period", "unit", "side", "status", "power_mw",
                               "price_eur_mwh"]).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b["firm"] = b.unit.map(fmap)
    b = b[b.firm.notna()]
    b["side"] = b.side.astype(str)
    c = b[b.status == "C"]
    net = (c.power_mw * c.side.map({"V": 1.0, "C": -1.0})).groupby(
        [c.date, c.period, c.firm]).sum().rename("net_mw")
    o = b[(b.status == "O") & (b.side == "C")].merge(pstar, on=KEY, how="inner")
    o["dev"] = (o.price_eur_mwh - o.p_star).abs()
    o = o[o.dev <= max(BANDWIDTHS)]
    parts = [net]
    for h in BANDWIDTHS:
        s = o.power_mw.where(o.dev <= h, 0.0).groupby([o.date, o.period, o.firm]).sum()
        parts.append(s.rename(f"own_buy_h{h:g}"))
    return pd.concat(parts, axis=1).fillna(0.0).reset_index()


def build() -> pd.DataFrame:
    cols = ["date", "period", "resolution_min", "firm", "p_star", "q_firm_mw", "theta_mw"] + [
        f"{s}_h{h:g}" for h in BANDWIDTHS for s in ("slope_i", "ability", "incentive")]
    f = pq.read_table(PANEL, columns=cols).to_pandas()
    f["date"] = pd.to_datetime(f.date)
    pstar = f.drop_duplicates(KEY)[KEY + ["p_star"]]
    fmap = unit_firm()
    months = sorted({f"{d.year}{d.month:02d}" for d in pd.to_datetime(pstar.date.unique())})
    extra = []
    for ym in months:
        if not (BIDS / f"bids_{ym}.parquet").exists():
            continue
        extra.append(month_extras(ym, fmap, pstar))
        print(f"  {ym}", flush=True, file=sys.stderr)
    e = pd.concat(extra, ignore_index=True)
    f = f.merge(e, on=KEY + ["firm"], how="left")
    f[["net_mw"] + [f"own_buy_h{h:g}" for h in BANDWIDTHS]] = f[
        ["net_mw"] + [f"own_buy_h{h:g}" for h in BANDWIDTHS]].fillna(0.0)
    for h in BANDWIDTHS:
        sn = f[f"slope_i_h{h:g}"] - f[f"own_buy_h{h:g}"] / (2 * h)
        ok = sn >= MIN_SLOPE
        f[f"slope_net_h{h:g}"] = sn
        f[f"ability_net_h{h:g}"] = np.where(ok & (f.q_firm_mw > 0), f.q_firm_mw / (100 * sn), np.nan)
        f[f"incentive_net_h{h:g}"] = np.where(ok, f.net_mw / (100 * sn), np.nan)
    f["date"] = pd.to_datetime(f.date)
    f["year"] = f.date.dt.year
    OUT.parent.mkdir(parents=True, exist_ok=True)
    f.to_parquet(OUT, index=False)
    return f


def report(f: pd.DataFrame) -> None:
    t = f[f.firm.isin(TABLE_FIRMS)]
    print("\nMEDIAN INDICES BY FIRM AND YEAR, h = 5 (EUR/MWh per 1% withheld)")
    for col, lab in (("ability_h5", "ability, panel (own demand counted as rivals')"),
                     ("ability_net_h5", "ability, own demand removed"),
                     ("incentive_h5", "incentive, panel (q - theta: contracts subtracted twice)"),
                     ("incentive_net_h5", "incentive, net auction position")):
        print(f"\n  {lab}")
        print(t.groupby(["firm", "year"])[col].median().unstack().reindex(TABLE_FIRMS)
              .round(3).to_string())
    print("\nSHARE OF FIRM-PERIODS AS A NET BUYER in the auction (net < 0)")
    nb = t.assign(buyer=t.net_mw < 0).groupby(["firm", "year"]).buyer.mean().unstack()
    print(nb.reindex(TABLE_FIRMS).round(2).to_string())
    print("\nCHECKS")
    for h in BANDWIDTHS:
        print(f"  h={h:g}: slope_net below {MIN_SLOPE:g} on {(f[f'slope_net_h{h:g}'] < MIN_SLOPE).mean():.4f} "
              f"of firm-periods (index undefined there); median slope_net/slope_i "
              f"{(f[f'slope_net_h{h:g}'] / f[f'slope_i_h{h:g}']).median():.3f}")
    # Enel Green Power Espana is Endesa's; build_owner_groups.GROUP_MERGES folds it in.
    print(f"  firm-periods still labelled ENEL: {(f.firm == 'ENEL').sum():,} (0 expected)")
    print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(f):,} firm-periods)")


def main() -> int:
    report(build())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
