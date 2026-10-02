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

3. PASS-THROUGH. Regulated last-resort suppliers (SU Eletricidade in EDP,
   Curenergia in Iberdrola) buy and sell volume whose cost is passed through to
   regulated tariffs (framework spec §2.4). The `*_exp_*` columns leave that
   volume out of n and q and give those units' offers back to the rivals:
       slope_exp_h = slope_net_h + (pt_sell_h + pt_buy_h) / 2h

Owners come from `lib/unit_ownership.py` (2026-10-02): the groups in force on each
date, each times its listed share, so a co-owned reactor splits pro rata and a sold
business counts for its owner at the time. The panel this script reads
(`residual_demand_firm.py --tier owner`) attributes the same way. Periods
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
from unit_ownership import attach_owners, spells  # noqa: E402
from residual_demand import BANDWIDTHS  # noqa: E402

DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
PANEL = ROOT / "outputs/tables/firm_residual_demand_full_owner.parquet"
OUT = ROOT / "outputs/tables/firm_incentive_net.parquet"
MIN_SLOPE = 5.0     # MW per EUR/MWh, as in edp_hydro_panel.py
TABLE_FIRMS = ["EDP", "IBERDROLA", "ENDESA", "NATURGY", "ACCIONA", "AXPO", "REPSOL"]
KEY = ["date", "period"]


def unit_firm() -> pd.DataFrame:
    """Ownership spells (lib/unit_ownership): the owner groups in force on each date,
    with their shares, and whether each owner is pass-through. Until 2026-10-02 a
    unit went whole to its latest listed owner for the whole window
    (notes/report-ownership-mapping.md)."""
    return spells().dropna(subset=["group"])


def month_extras(ym: str, umap: pd.DataFrame, pstar: pd.DataFrame) -> pd.DataFrame:
    b = pq.read_table(BIDS / f"bids_{ym}.parquet",
                      columns=["date", "period", "unit", "side", "status", "power_mw",
                               "price_eur_mwh"]).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b["unit"] = b.unit.astype(str)
    b = attach_owners(b[b.unit.isin(set(umap.unit))], umap)
    b = b.dropna(subset=["group"]).rename(columns={"group": "firm"})
    b["side"] = b.side.astype(str)
    b["status"] = b.status.astype(str)
    b["sgn"] = b.side.map({"V": 1.0, "C": -1.0})
    c = b[b.status == "C"]
    net = (c.power_mw * c.sgn).groupby([c.date, c.period, c.firm]).sum().rename("net_mw")
    cp = c[c.pt]
    k = [cp.date, cp.period, cp.firm]
    pt_net = (cp.power_mw * cp.sgn).groupby(k).sum().rename("pt_net_mw")
    pt_q = cp.power_mw.where(cp.side == "V", 0.0).groupby(k).sum().rename("pt_q_mw")
    o = b[b.status == "O"].merge(pstar, on=KEY, how="inner")
    o["dev"] = (o.price_eur_mwh - o.p_star).abs()
    o = o[o.dev <= max(BANDWIDTHS)]
    g = [o.date, o.period, o.firm]
    parts = [net, pt_net, pt_q]
    for h in BANDWIDTHS:
        inb = o.dev <= h
        buy, sell = inb & (o.side == "C"), inb & (o.side == "V")
        parts.append(o.power_mw.where(buy, 0.0).groupby(g).sum().rename(f"own_buy_h{h:g}"))
        parts.append(o.power_mw.where(buy & o.pt, 0.0).groupby(g).sum().rename(f"pt_buy_h{h:g}"))
        parts.append(o.power_mw.where(sell & o.pt, 0.0).groupby(g).sum().rename(f"pt_sell_h{h:g}"))
    return pd.concat(parts, axis=1).fillna(0.0).reset_index()


def build() -> pd.DataFrame:
    cols = ["date", "period", "resolution_min", "firm", "p_star", "q_firm_mw", "theta_mw"] + [
        f"{s}_h{h:g}" for h in BANDWIDTHS for s in ("slope_i", "ability", "incentive")]
    f = pq.read_table(PANEL, columns=cols).to_pandas()
    f["date"] = pd.to_datetime(f.date)
    pstar = f.drop_duplicates(KEY)[KEY + ["p_star"]]
    umap = unit_firm()
    months = sorted({f"{d.year}{d.month:02d}" for d in pd.to_datetime(pstar.date.unique())})
    extra = []
    for ym in months:
        if not (BIDS / f"bids_{ym}.parquet").exists():
            continue
        extra.append(month_extras(ym, umap, pstar))
        print(f"  {ym}", flush=True, file=sys.stderr)
    e = pd.concat(extra, ignore_index=True)
    f = f.merge(e, on=KEY + ["firm"], how="left")
    ext = ["net_mw", "pt_net_mw", "pt_q_mw"] + [
        f"{s}_h{h:g}" for h in BANDWIDTHS for s in ("own_buy", "pt_buy", "pt_sell")]
    f[ext] = f[ext].fillna(0.0)
    f["net_exp_mw"] = f.net_mw - f.pt_net_mw
    f["q_exp_mw"] = f.q_firm_mw - f.pt_q_mw
    for h in BANDWIDTHS:
        sn = f[f"slope_i_h{h:g}"] - f[f"own_buy_h{h:g}"] / (2 * h)
        ok = sn >= MIN_SLOPE
        f[f"slope_net_h{h:g}"] = sn
        f[f"ability_net_h{h:g}"] = np.where(ok & (f.q_firm_mw > 0), f.q_firm_mw / (100 * sn), np.nan)
        f[f"incentive_net_h{h:g}"] = np.where(ok, f.net_mw / (100 * sn), np.nan)
        # Exposed (framework spec §2.4): pass-through offers go back to the rivals.
        se = sn + (f[f"pt_sell_h{h:g}"] + f[f"pt_buy_h{h:g}"]) / (2 * h)
        oke = se >= MIN_SLOPE
        f[f"slope_exp_h{h:g}"] = se
        f[f"ability_exp_h{h:g}"] = np.where(oke & (f.q_exp_mw > 0), f.q_exp_mw / (100 * se), np.nan)
        f[f"incentive_exp_h{h:g}"] = np.where(oke, f.net_exp_mw / (100 * se), np.nan)
    f["date"] = pd.to_datetime(f.date)
    f["year"] = f.date.dt.year
    OUT.parent.mkdir(parents=True, exist_ok=True)
    f.to_parquet(OUT, index=False)
    return f


def report(f: pd.DataFrame) -> bool:
    t = f[f.firm.isin(TABLE_FIRMS)]
    print("\nMEDIAN INDICES BY FIRM AND YEAR, h = 5 (EUR/MWh per 1% withheld)")
    for col, lab in (("ability_h5", "ability, panel (own demand counted as rivals')"),
                     ("ability_net_h5", "ability, own demand removed"),
                     ("incentive_h5", "incentive, panel (q - theta: contracts subtracted twice)"),
                     ("incentive_net_h5", "incentive, net auction position"),
                     ("incentive_exp_h5", "incentive, EXPOSED net position (pass-through excluded)")):
        print(f"\n  {lab}")
        print(t.groupby(["firm", "year"])[col].median().unstack().reindex(TABLE_FIRMS)
              .round(3).to_string())
    for col, lab in (("net_mw", "as built"), ("net_exp_mw", "EXPOSED (pass-through excluded)")):
        print(f"\nSHARE OF FIRM-PERIODS AS A NET BUYER, {lab}")
        nb = t.assign(buyer=t[col] < 0).groupby(["firm", "year"]).buyer.mean().unstack()
        print(nb.reindex(TABLE_FIRMS).round(2).to_string())
    print("\nPASS-THROUGH VOLUME by firm (mean MW over firm-periods; nonzero only for EDP, IBERDROLA)")
    print(t.groupby("firm")[["pt_net_mw", "pt_q_mw", "pt_sell_h5", "pt_buy_h5"]].mean()
          .reindex(TABLE_FIRMS).round(1).to_string())
    print("\nCHECKS")
    for h in BANDWIDTHS:
        print(f"  h={h:g}: slope_net below {MIN_SLOPE:g} on {(f[f'slope_net_h{h:g}'] < MIN_SLOPE).mean():.4f} "
              f"of firm-periods (index undefined there); median slope_net/slope_i "
              f"{(f[f'slope_net_h{h:g}'] / f[f'slope_i_h{h:g}']).median():.3f}")
    # Enel Green Power Espana is Endesa's; build_owner_groups.GROUP_MERGES folds it in.
    print(f"  firm-periods still labelled ENEL: {(f.firm == 'ENEL').sum():,} (0 expected)")
    print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(f):,} firm-periods)")
    bad = []
    for h in BANDWIDTHS:
        v = (f[f"slope_exp_h{h:g}"] < f[f"slope_net_h{h:g}"] - 1e-6).mean()
        print(f"  h={h:g}: slope_exp below slope_net on {v:.6f} of firm-periods (must be 0)")
        if v > 0:
            bad.append(f"slope_exp < slope_net at h={h:g}")
    other = t[~t.firm.isin(["EDP", "IBERDROLA"])]
    if (other.pt_net_mw.abs() > 0).any():
        bad.append("pass-through volume attributed outside EDP and IBERDROLA")
    for b_ in bad:
        print(f"  FAIL {b_}")
    return not bad


def main() -> int:
    return 0 if report(build()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
