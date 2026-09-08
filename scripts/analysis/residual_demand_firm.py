#!/usr/bin/env python3
"""Firm-specific residual demand, ability and incentive.

    .venv/bin/python scripts/analysis/residual_demand_firm.py --verify
    .venv/bin/python scripts/analysis/residual_demand_firm.py --full --save

The market-level script measures residual demand facing an *infinitesimal*
participant -- a lower bound on every real firm's steepness. This measures the
firm-specific object the theory is actually about:

    RD_i(p) = D(p) - sum_{j != i} S_j(p)

Removing firm i's own supply from the sum removes its contribution to the
slope, so the whole firm-level computation is one extra groupby inside the same
band, not one sweep per firm.

INDICES (McRae & Wolak, eqs. 3.4 and 3.10)

    ability   eta_i   = q_i / (100 |RD'_i|)             EUR/MWh per 1% withheld
    incentive eta_i^C = eta_i (q_i - theta_i) / q_i

Ability is what the stack makes possible; incentive scales it by the share of
output not already sold forward. theta comes from
outputs/tables/contract_position_panel.parquet and is a PHYSICAL contract
proxy -- it misses financial hedges, so incentive is an upper bound.

UNMAPPED
--------
The contract panel (and the unit -> firm mapping feeding this script) both
carry an explicit "UNMAPPED" bucket for units/theta that could not be
attributed to a real firm. It is not a firm and is excluded from every
firm-level index and from the firm rows of the saved panel -- but its
footprint is kept visible rather than silently averaged away:

    theta_coverage  mapped theta_mw / total theta_mw, per (date, period)
    q_unmapped_mw   UNMAPPED's own cleared SELL volume, per (date, period)

Both are computed BEFORE the UNMAPPED exclusion and broadcast onto every real
firm's row for that period, so the coverage drift documented in CLAUDE.md
(71.5% in 2018-01, 95.7% in 2024-01, 76.9% in 2026-05) stays measurable.
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
BIDS = DATA / "omie/bids/parquet"
AGENTS = DATA / "omie/registry/unit_agents.parquet"
THETA = ROOT / "outputs/tables/contract_position_panel.parquet"
THETA_OWNER = ROOT / "outputs/tables/contract_position_panel_owner.parquet"
OUT = ROOT / "outputs/tables/firm_residual_demand_full.parquet"
OUT_OWNER = ROOT / "outputs/tables/firm_residual_demand_full_owner.parquet"

# Set from --tier in main(); module-level so load_agents/load_theta stay
# single-argument, as the rest of this file assumes.
TIER = "firm"

VERIFY_MONTH = "202401"   # the month every other verification in this repo uses

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_owner import owner_group  # noqa: E402
# slope_from_band_mw is deliberately NOT imported. The firm arithmetic below is
# inline because eta_i divides by the FIRM's cleared volume and so needs a
# q_firm_mw > 0 guard that the shared function does not have (it guards only
# slope > 0 and p_star > 0, which is right at market level where q is the
# market's). Everything the two levels must share -- the band, the bandwidths,
# the zero-price floor -- still comes from the library, which is what keeps
# them from drifting apart.
from residual_demand import (  # noqa: E402
    BANDWIDTHS, IDENTITY_TOL, KEY, ZERO_PRICE, band_offers,
    cleared_by_period,
)

# Every role that offers energy. `generation` alone is WRONG -- see CLAUDE.md:
# it drops all combined-cycle, nuclear, hydro-cascade and pumped-storage
# units, leaving only wind/solar (which offer at zero).
SUPPLY_ROLES = ("generation", "generation_large", "storage_mixed", "pumping")

BID_COLS = ["date", "period", "unit", "side", "status", "power_mw", "price_eur_mwh"]


def load_prices() -> pd.DataFrame:
    px = pq.read_table(DATA / "omie/prices/omie_day_ahead_prices.parquet").to_pandas()
    px["split"] = px.price_es != px.price_pt
    return px


def load_agents() -> pd.DataFrame:
    """unit -> firm, restricted to units that can actually supply energy.

    Under `--tier owner` the label is OMIE's published `agent_owner` rolled up
    by lib/omie_owner.owner_group, instead of the inference chain's `firm`.
    Unlike theta, this side may read `unit_agents` directly: the q_firm
    arithmetic below is over supply units, which are exactly the registry the
    file covers.
    """
    cols = ["unit", "role"] + (["agent_owner"] if TIER == "owner" else ["firm"])
    a = pq.read_table(AGENTS, columns=cols).to_pandas()
    if TIER == "owner":
        a["firm"] = a.agent_owner.map(owner_group)
    return a.loc[a.role.isin(SUPPLY_ROLES), ["unit", "firm"]]


def load_theta() -> pd.DataFrame:
    """Firm-level bilateral contract position, date recast to match the bid
    archive's date32 -> datetime.date reading (contract_position_panel.parquet
    stores date as a timestamp; merging that against the object-dtype date
    the bid/price files produce silently matches nothing)."""
    src = THETA_OWNER if TIER == "owner" else THETA
    th = pd.read_parquet(src, columns=KEY + ["firm", "theta_mw"])
    th["date"] = pd.to_datetime(th.date).dt.date
    return th


def month_bounds(ym: str) -> tuple:
    lo = pd.Timestamp(f"{ym[:4]}-{ym[4:]}-01").date()
    hi = (pd.Timestamp(lo) + pd.offsets.MonthEnd(1)).date()
    return lo, hi


def load_bids_month(ym: str, lo, hi) -> pd.DataFrame:
    flt = (pc.field("date") >= lo) & (pc.field("date") <= hi)
    tbl = ds.dataset(BIDS / f"bids_{ym}.parquet").to_table(filter=flt, columns=BID_COLS)
    return tbl.to_pandas()


def compute_month(bids, px_m, agents, theta):
    """(market rows, firm rows) for one month."""
    px_m = px_m[KEY + ["price_es", "split", "resolution_min", "utc_timestamp"]]
    mkt = cleared_by_period(bids).merge(px_m, on=KEY, how="inner").rename(
        columns={"price_es": "p_star", "sell_matched": "q_cleared"})

    b = bids.merge(agents, on="unit", how="left")
    b["firm"] = b.firm.fillna("UNMAPPED")

    # Firm's own cleared SELL volume at p*: this is RD_i(p*) by market clearing.
    own = (b[(b.status == "C") & (b.side == "V")]
           .groupby(KEY + ["firm"])["power_mw"].sum().rename("q_firm_mw").reset_index())

    # UNMAPPED's own cleared sell volume per period -- kept visible on the
    # auction side even after UNMAPPED is dropped from the firm rows below.
    q_unmapped = (own.loc[own.firm == "UNMAPPED", KEY + ["q_firm_mw"]]
                  .rename(columns={"q_firm_mw": "q_unmapped_mw"}))

    out = own.merge(mkt[KEY + ["p_star", "q_cleared", "resolution_min"]], on=KEY, how="inner")

    for h in BANDWIDTHS:
        band = band_offers(b, mkt, h)
        total = band.groupby(KEY)["power_mw"].sum().rename("band_mw")
        own_sell = (band[band.side == "V"].groupby(KEY + ["firm"])["power_mw"]
                    .sum().rename("own_band_mw"))

        # Market-level total-band slope, kept on `mkt` -- verify()'s invariant
        # 1 needs it to compare against slope_i, and it would otherwise only
        # ever exist as a value merged onto `out` and immediately dropped.
        mkt = mkt.merge(total, on=KEY, how="left")
        mkt[f"slope_h{h:g}"] = mkt.band_mw.fillna(0.0) / (2 * h)
        mkt = mkt.drop(columns=["band_mw"])

        out = out.merge(total, on=KEY, how="left").merge(
            own_sell, on=KEY + ["firm"], how="left")
        out["own_band_mw"] = out.own_band_mw.fillna(0.0)
        # Removing firm i's own supply from the curve facing it.
        slope_i = (out.band_mw.fillna(0.0) - out.own_band_mw) / (2 * h)
        out[f"slope_i_h{h:g}"] = slope_i
        ok = (slope_i > 0) & (out.p_star > ZERO_PRICE) & (out.q_firm_mw > 0)
        out[f"eta_i_h{h:g}"] = np.where(ok, slope_i * out.p_star / out.q_firm_mw, np.nan)
        out[f"lerner_bound_h{h:g}"] = np.where(
            ok, out.q_firm_mw / (slope_i * out.p_star), np.nan)
        out[f"ability_h{h:g}"] = np.where(ok, out.q_firm_mw / (100 * slope_i), np.nan)
        out = out.drop(columns=["band_mw", "own_band_mw"])

    out = out.merge(theta, on=KEY + ["firm"], how="left")
    out["theta_mw"] = out.theta_mw.fillna(0.0)
    frac = ((out.q_firm_mw - out.theta_mw) / out.q_firm_mw).clip(lower=-5, upper=1)
    for h in BANDWIDTHS:
        out[f"incentive_h{h:g}"] = out[f"ability_h{h:g}"] * frac

    # theta_coverage: mapped theta / total theta, per period. Computed on
    # theta BEFORE the UNMAPPED exclusion below, so the drift stays visible.
    tot_theta = theta.groupby(KEY)["theta_mw"].sum().rename("theta_total")
    mapped_theta = (theta[theta.firm != "UNMAPPED"]
                    .groupby(KEY)["theta_mw"].sum().rename("theta_mapped"))
    cov = pd.concat([tot_theta, mapped_theta], axis=1)
    cov["theta_mapped"] = cov.theta_mapped.fillna(0.0)
    cov["theta_coverage"] = np.where(cov.theta_total > 0,
                                     cov.theta_mapped / cov.theta_total, np.nan)
    cov = cov.reset_index()[KEY + ["theta_coverage"]]

    out = out.merge(cov, on=KEY, how="left")
    out = out.merge(q_unmapped, on=KEY, how="left")
    out["q_unmapped_mw"] = out.q_unmapped_mw.fillna(0.0)

    # UNMAPPED is not a firm -- exclude from all firm-level indices and from
    # the saved firm rows (ambiguity resolutions 2 & 3).
    out = out[out.firm != "UNMAPPED"].reset_index(drop=True)

    return mkt, out


def verify(bids, px_m, agents, theta) -> int:
    """Three invariants that hold by construction. Each can fail loudly."""
    mkt, firm = compute_month(bids, px_m, agents, theta)
    bad = 0

    # 1. A firm's residual demand is weakly STEEPER than the market's, because
    #    its own supply is removed from the curve facing it.
    j = firm.merge(mkt[["date", "period", "slope_h5"]], on=["date", "period"])
    viol = (j.slope_i_h5 > j.slope_h5 + 1e-6).mean()
    print(f"    slope_i > slope_market on {viol:.4%} of firm-periods (must be 0)")
    bad |= int(viol > 0)

    # 2. Firms' own cleared volume cannot exceed market cleared volume.
    tot = firm.groupby(["date", "period"]).q_firm_mw.sum().rename("q_sum")
    j2 = mkt.set_index(["date", "period"]).join(tot, how="inner")
    viol2 = (j2.q_sum > j2.q_cleared * 1.0001).mean()
    print(f"    sum(q_firm) > q_cleared on {viol2:.4%} of periods (must be 0)")
    bad |= int(viol2 > 0)

    # 3. lerner_bound is exactly 1/eta_i wherever both are defined.
    m = firm.dropna(subset=["eta_i_h5", "lerner_bound_h5"])
    gap = (m.lerner_bound_h5 - 1 / m.eta_i_h5).abs().max()
    print(f"    max |lerner - 1/eta| = {gap:.2e} (must be ~0)")
    bad |= int(gap > 1e-9)
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=["firm", "owner"], default="firm",
                    help="owner: OMIE's published agent_owner; removes the "
                         "theta_coverage drift documented in section 4.5")
    ap.add_argument("--verify", action="store_true",
                    help=f"run the three invariants on {VERIFY_MONTH} and exit")
    ap.add_argument("--full", action="store_true",
                    help="every month in the bid archive, not just the verify month")
    ap.add_argument("--save", action="store_true",
                    help="write the firm panel to outputs/tables/ (needs --full)")
    args = ap.parse_args()

    if not BIDS.is_dir():
        print(f"no bid archive at {BIDS}", file=sys.stderr)
        return 1
    if not THETA.exists():
        print(f"no contract-position panel at {THETA} -- run build_contract_position.py "
              f"--save first", file=sys.stderr)
        return 1

    px = load_prices()
    global TIER
    TIER = args.tier
    agents = load_agents()
    theta_all = load_theta()

    if args.verify:
        lo, hi = month_bounds(VERIFY_MONTH)
        bids = load_bids_month(VERIFY_MONTH, lo, hi)
        px_m = px[(px.date >= lo) & (px.date <= hi)]
        theta_m = theta_all[(theta_all.date >= lo) & (theta_all.date <= hi)]
        print(f"verifying on {VERIFY_MONTH}  ({len(bids):,} bid rows, "
              f"{len(px_m):,} periods)")
        return verify(bids, px_m, agents, theta_m)

    if not args.full:
        print("nothing to do; pass --verify or --full [--save]")
        return 0

    months = sorted(p.stem.replace("bids_", "") for p in BIDS.glob("bids_*.parquet"))
    mkt_frames: list[pd.DataFrame] = []
    firm_frames: list[pd.DataFrame] = []
    for i, ym in enumerate(months, 1):
        lo, hi = month_bounds(ym)
        px_m = px[(px.date >= lo) & (px.date <= hi)]
        if px_m.empty:
            continue
        bids = load_bids_month(ym, lo, hi)
        if bids.empty:
            continue
        theta_m = theta_all[(theta_all.date >= lo) & (theta_all.date <= hi)]
        mkt, firm = compute_month(bids, px_m, agents, theta_m)
        mkt_frames.append(mkt)
        firm_frames.append(firm)
        print(f"  [{i:3d}/{len(months)}] {ym}  {len(bids):>10,} bid rows  "
              f"{len(firm):>8,} firm-periods", end="\r", flush=True)

    print(" " * 60, end="\r")
    if not mkt_frames:
        print("no periods computed", file=sys.stderr)
        return 1

    mkt = pd.concat(mkt_frames, ignore_index=True)
    firm = pd.concat(firm_frames, ignore_index=True)
    mkt["date"] = pd.to_datetime(mkt["date"])
    firm["date"] = pd.to_datetime(firm["date"])

    # Same filters as the market panel (residual_demand_slope.py), applied to
    # `mkt` and then propagated to `firm` by an inner join on the surviving
    # (date, period) keys, so the two stay defined on the same period set.
    n_all = len(mkt)
    n_split = int(mkt.split.sum())
    n_gap = int((mkt.identity_gap > IDENTITY_TOL).sum())
    keep_mkt = mkt[(~mkt.split) & (mkt.identity_gap <= IDENTITY_TOL)].copy()
    n_zero = int((keep_mkt.p_star <= ZERO_PRICE).sum())
    keep_mkt = keep_mkt[keep_mkt.p_star > ZERO_PRICE]

    print("=" * 72)
    print(f"FULL SWEEP: {mkt.date.nunique()} days, {n_all:,} market-periods")
    print("=" * 72)
    print(f"  dropped, market splitting (ES != PT) : {n_split:7,}  "
          f"({n_split/n_all:5.1%})")
    print(f"  dropped, clearing identity violated  : {n_gap:7,}  "
          f"({n_gap/n_all:5.1%})")
    print(f"  dropped, cleared at <= {ZERO_PRICE:g} EUR/MWh     : {n_zero:7,}  "
          f"({n_zero/n_all:5.1%})")
    print(f"  retained market-periods               : {len(keep_mkt):7,}")

    keep_keys = keep_mkt[KEY].drop_duplicates()
    firm = firm.merge(keep_keys, on=KEY, how="inner")
    print(f"  retained firm-periods                 : {len(firm):7,}")

    band_cols = [f"{stat}_h{h:g}" for h in BANDWIDTHS
                 for stat in ("slope_i", "eta_i", "lerner_bound", "ability", "incentive")]
    firm = firm[["date", "period", "resolution_min", "firm", "p_star", "q_firm_mw",
                 "q_cleared", "theta_mw", "theta_coverage", "q_unmapped_mw"] + band_cols]

    if args.save:
        out_path = OUT_OWNER if TIER == "owner" else OUT
        out_path.parent.mkdir(parents=True, exist_ok=True)
        firm.to_parquet(out_path, index=False)
        print(f"\nwrote {out_path.relative_to(ROOT)}  ({len(firm):,} rows, "
              f"{out_path.stat().st_size/1e6:.1f} MB)")
    else:
        print("\n(nothing written; pass --save to keep the panel)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
