#!/usr/bin/env python3
"""Concentration on total cleared volume vs. the near-marginal band.

    .venv/bin/python scripts/analysis/concentration_margin.py --verify
    .venv/bin/python scripts/analysis/concentration_margin.py --full --save

THE PREDICTION BEING TESTED

CNMC's (Comision Nacional de los Mercados y la Competencia, the Spanish
competition/energy regulator) published shares show market concentration
falling over 2018-2026. Those shares are computed on total cleared volume,
which is dominated by inframarginal output -- a 5 GW nuclear or wind unit
offering near zero almost never sets the price and contributes nothing to
who controls the *margin*. This script computes HHI (Herfindahl-Hirschman
Index) two ways on the same periods:

    hhi_total      -- on ALL cleared sell volume, the CNMC-style object
    hhi_margin_h{h} -- on SUBMITTED sell offers within +/-h EUR/MWh of the
                        clearing price, i.e. the units actually contesting
                        who sets p*

If hhi_total falls while hhi_margin rises, the divergence resolves into one
story: concentration moved to where price is set, even as it looks like it
fell in the aggregate. If hhi_margin does NOT rise, that is a real result --
report it plainly rather than retuning the bandwidth or filters to force the
expected sign.

MAPPED VOLUME ONLY (ambiguity resolution 1)

Both HHIs are computed on volume mapped to a firm via
data/omie/registry/unit_agents.parquet's `firm` column, with shares
renormalised over that mapped volume -- NOT over total volume with unmapped
treated as one giant firm, which would invent a fictitious dominant player.
`mapped_share_total` and `mapped_share_margin_h{h}` report the mapped
fraction alongside every HHI so the renormalisation is never silently
invisible.

COVERAGE DRIFT (ambiguity resolution 2)

Firm-mapping coverage is not stable over the window -- CLAUDE.md and prior
work on this data record it drifting from about 74% in 2018 to 94% in 2023
and back to 80% in 2026. A trend in HHI can be a trend in coverage instead
of a trend in concentration. Read `mapped_share_margin_h5` by year alongside
the HHI trend, not after it.

FILTERS -- match residual_demand_firm.py's block exactly, each counted:
  * market splitting (price_es != price_pt): no single curve to take a
    margin from when the two zones clear separately.
  * clearing-identity violation (unit dropouts): matched buy != matched
    sell beyond tolerance signals missing units, not a real market state.
  * p_star <= ZERO_PRICE: a near-zero clearing price is not economically
    meaningful for "who sets the margin".

SUPPLY_ROLES, not `role == "generation"` alone -- see CLAUDE.md: the latter
drops every combined-cycle, nuclear, hydro-cascade and pumped-storage unit,
leaving only wind/solar (which offer at zero and collapse any bidding
measure to a mass point).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
AGENTS = DATA / "omie/registry/unit_agents.parquet"
OUT = ROOT / "outputs/tables/concentration_panel.parquet"

VERIFY_MONTH = "202401"   # the month every other verification in this repo uses

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from residual_demand import (  # noqa: E402
    BANDWIDTHS, IDENTITY_TOL, KEY, ZERO_PRICE, band_offers,
    cleared_by_period,
)

# Every role that offers energy. `generation` alone is WRONG -- see CLAUDE.md.
SUPPLY_ROLES = ("generation", "generation_large", "storage_mixed", "pumping")

BID_COLS = ["date", "period", "unit", "side", "status", "power_mw", "price_eur_mwh"]


def load_prices() -> pd.DataFrame:
    px = pq.read_table(DATA / "omie/prices/omie_day_ahead_prices.parquet").to_pandas()
    px["split"] = px.price_es != px.price_pt
    return px


def load_agents() -> pd.DataFrame:
    """unit -> firm, restricted to units that can actually supply energy."""
    a = pq.read_table(AGENTS, columns=["unit", "role", "firm"]).to_pandas()
    return a.loc[a.role.isin(SUPPLY_ROLES), ["unit", "firm"]]


def month_bounds(ym: str) -> tuple:
    lo = pd.Timestamp(f"{ym[:4]}-{ym[4:]}-01").date()
    hi = (pd.Timestamp(lo) + pd.offsets.MonthEnd(1)).date()
    return lo, hi


def load_bids_month(ym: str, lo, hi) -> pd.DataFrame:
    flt = (pc.field("date") >= lo) & (pc.field("date") <= hi)
    tbl = ds.dataset(BIDS / f"bids_{ym}.parquet").to_table(filter=flt, columns=BID_COLS)
    return tbl.to_pandas()


def hhi(shares: pd.Series) -> float:
    """HHI in the conventional 0-10000 scale, on the MAPPED share only.

    Shares are renormalised over mapped volume, so the HHI describes the
    attributed market rather than treating unmapped volume as one giant firm.
    mapped_share is reported alongside so the renormalisation is visible.
    """
    s = shares / shares.sum()
    return float((s ** 2).sum() * 10000)


def concentration_month(bids: pd.DataFrame, px_m: pd.DataFrame,
                         agents: pd.DataFrame) -> pd.DataFrame:
    """One row per (date, period): p_star plus both HHIs, unfiltered.

    Carries mkt's split/identity_gap/p_star columns through so the caller can
    apply the standard filter block after concatenating months, exactly as
    residual_demand_firm.py does.
    """
    px_m = px_m[KEY + ["price_es", "split", "resolution_min", "utc_timestamp"]]
    mkt = cleared_by_period(bids).merge(px_m, on=KEY, how="inner").rename(
        columns={"price_es": "p_star", "sell_matched": "q_cleared"})

    b = bids.merge(agents, on="unit", how="left")
    b["mapped"] = b.firm.notna()

    # --- total: all cleared sell volume
    sold = b[(b.status == "C") & (b.side == "V")]
    tot = sold.groupby(KEY).power_mw.sum().rename("mw_all")
    mapped = sold[sold.mapped].groupby(KEY).power_mw.sum().rename("mw_mapped")
    by_firm = sold[sold.mapped].groupby(KEY + ["firm"]).power_mw.sum()
    hhi_tot = by_firm.groupby(KEY).apply(hhi).rename("hhi_total")
    out = (mkt.merge(tot, on=KEY).merge(mapped, on=KEY, how="left")
              .merge(hhi_tot, on=KEY, how="left"))
    out["mapped_share_total"] = out.mw_mapped.fillna(0) / out.mw_all
    out = out.drop(columns=["mw_all", "mw_mapped"])

    # --- margin: submitted SELL offers inside the band
    for h in BANDWIDTHS:
        band = band_offers(b, mkt, h)
        band = band[band.side == "V"]
        t = band.groupby(KEY).power_mw.sum().rename("mw_all")
        mp = band[band.mapped].groupby(KEY).power_mw.sum().rename("mw_mapped")
        bf = band[band.mapped].groupby(KEY + ["firm"]).power_mw.sum()
        out = (out.merge(bf.groupby(KEY).apply(hhi).rename(f"hhi_margin_h{h:g}"),
                         on=KEY, how="left")
                  .merge(bf.groupby(KEY).size().rename(f"n_firms_margin_h{h:g}"),
                         on=KEY, how="left")
                  .merge(t, on=KEY, how="left").merge(mp, on=KEY, how="left"))
        out[f"mapped_share_margin_h{h:g}"] = out.mw_mapped.fillna(0) / out.mw_all
        out = out.drop(columns=["mw_all", "mw_mapped"])
    return out


def verify(panel: pd.DataFrame) -> int:
    """Range invariants that must hold by construction: every HHI in
    [0, 10000], every mapped_share in [0, 1]. Can fail loudly if the
    renormalisation or the group-by keys are wrong."""
    bad = 0
    for c in [c for c in panel.columns if c.startswith("hhi")]:
        v = panel[c].dropna()
        lo, hi = v.min(), v.max()
        print(f"    {c:22s} range [{lo:.0f}, {hi:.0f}]  (must be within [0, 10000])")
        bad |= int(lo < 0 or hi > 10000 + 1e-6)
    for c in [c for c in panel.columns if c.startswith("mapped_share")]:
        v = panel[c].dropna()
        print(f"    {c:22s} range [{v.min():.3f}, {v.max():.3f}]  (must be within [0, 1])")
        bad |= int(v.min() < 0 or v.max() > 1 + 1e-9)
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true",
                    help=f"run the range invariants on {VERIFY_MONTH} and exit")
    ap.add_argument("--full", action="store_true",
                    help="every month in the bid archive, not just the verify month")
    ap.add_argument("--save", action="store_true",
                    help="write the concentration panel to outputs/tables/ (needs --full)")
    args = ap.parse_args()

    if not BIDS.is_dir():
        print(f"no bid archive at {BIDS}", file=sys.stderr)
        return 1

    px = load_prices()
    agents = load_agents()

    if args.verify:
        lo, hi = month_bounds(VERIFY_MONTH)
        bids = load_bids_month(VERIFY_MONTH, lo, hi)
        px_m = px[(px.date >= lo) & (px.date <= hi)]
        print(f"verifying on {VERIFY_MONTH}  ({len(bids):,} bid rows, "
              f"{len(px_m):,} periods)")
        panel = concentration_month(bids, px_m, agents)
        return verify(panel)

    if not args.full:
        print("nothing to do; pass --verify or --full [--save]")
        return 0

    months = sorted(p.stem.replace("bids_", "") for p in BIDS.glob("bids_*.parquet"))
    frames: list[pd.DataFrame] = []
    for i, ym in enumerate(months, 1):
        lo, hi = month_bounds(ym)
        px_m = px[(px.date >= lo) & (px.date <= hi)]
        if px_m.empty:
            continue
        bids = load_bids_month(ym, lo, hi)
        if bids.empty:
            continue
        out = concentration_month(bids, px_m, agents)
        frames.append(out)
        print(f"  [{i:3d}/{len(months)}] {ym}  {len(bids):>10,} bid rows  "
              f"{len(out):>8,} periods", end="\r", flush=True)

    print(" " * 60, end="\r")
    if not frames:
        print("no periods computed", file=sys.stderr)
        return 1

    panel = pd.concat(frames, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"])

    # Same filters as the market panel (residual_demand_slope.py /
    # residual_demand_firm.py): market splitting, then the clearing-identity
    # gap, then price <= ZERO_PRICE. Each dropped and counted.
    n_all = len(panel)
    n_split = int(panel.split.sum())
    n_gap = int((panel.identity_gap > IDENTITY_TOL).sum())
    keep = panel[(~panel.split) & (panel.identity_gap <= IDENTITY_TOL)].copy()
    n_zero = int((keep.p_star <= ZERO_PRICE).sum())
    keep = keep[keep.p_star > ZERO_PRICE]

    print("=" * 72)
    print(f"FULL SWEEP: {panel.date.nunique()} days, {n_all:,} periods")
    print("=" * 72)
    print(f"  dropped, market splitting (ES != PT) : {n_split:7,}  "
          f"({n_split/n_all:5.1%})")
    print(f"  dropped, clearing identity violated  : {n_gap:7,}  "
          f"({n_gap/n_all:5.1%})")
    print(f"  dropped, cleared at <= {ZERO_PRICE:g} EUR/MWh     : {n_zero:7,}  "
          f"({n_zero/n_all:5.1%})")
    print(f"  retained periods                     : {len(keep):7,}")

    cols = (["date", "period", "p_star", "hhi_total"]
            + [f"hhi_margin_h{h:g}" for h in BANDWIDTHS]
            + ["mapped_share_total"]
            + [f"mapped_share_margin_h{h:g}" for h in BANDWIDTHS]
            + [f"n_firms_margin_h{h:g}" for h in BANDWIDTHS])
    keep = keep[cols].reset_index(drop=True)

    if args.save:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        keep.to_parquet(OUT, index=False)
        print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(keep):,} rows, "
              f"{OUT.stat().st_size/1e6:.1f} MB)")
    else:
        print("\n(nothing written; pass --save to keep the panel)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
