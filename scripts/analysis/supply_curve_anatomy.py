#!/usr/bin/env python3
"""Shape of the submitted day-ahead supply curve, 2018-2026.

    .venv/bin/python scripts/analysis/supply_curve_anatomy.py --verify
    .venv/bin/python scripts/analysis/supply_curve_anatomy.py --full --save

WHERE THIS FITS

`concentration_margin.py` and `residual_demand_slope.py` already show that
residual-demand elasticity fell (1.83 -> 0.45) and that concentration among
near-marginal suppliers roughly doubled, over 2018-2026. This script measures
the MECHANISM behind that number: how the shape of the SUBMITTED sell curve
itself changed --

  * `share_at_zero` / `share_below_p` -- how much volume is offered at or
    below zero, and at or below the clearing price, i.e. how much of the
    curve is flat and inframarginal (wind/solar with no fuel cost).
  * `band_density_h{h}` -- how much total offer volume (both sides -- see
    below) sits within +/-h EUR/MWh of the clearing price, i.e. how dense
    the curve is exactly where price is set. This is the same object
    `residual_demand.py`'s docstring defines: |RD'(p*)| ~= band MW / 2h.
    A denser band is a flatter, more elastic residual demand; a thinner one
    is the mechanical reason elasticity fell.
  * `marginal_tech` / `marginal_regime` -- the technology and regulatory
    regime of the cleared sell offer whose price sits closest to p* from
    below, i.e. which technology is setting the price.

`band_density_h{h}` is NOT restricted to the sell side. `band_offers()` in
residual_demand.py sums submitted MW on both sides of the auction within the
band, matching how residual_demand_slope.py already uses it
(|RD'| = (sell MW + buy MW in band) / 2h). Restricting to sell alone would
make this panel's band density incomparable to the elasticity work it is
meant to explain.

TECHNOLOGY COVERAGE IS WEAK -- ALWAYS READ WITH ITS OWN COVERAGE SERIES
(ambiguity resolution 2)

Per CLAUDE.md, technology (`tech`) reaches only 41.2% of generation volume;
`regime` (Regimen Especial vs Ordinario) reaches 63.3%. Both are far short of
the 89.1% ownership mapping, because they come from parsing `cab` plant-name
strings, not a maintained registry. `marginal_tech` and `marginal_regime` are
therefore null on a large and NOT necessarily representative share of
periods. This script prints the non-null share of both BY YEAR
(`print_year_table()`) precisely so a marginal-technology trend is never read
without its own coverage alongside it -- a trend line computed on a shrinking
or drifting-coverage subsample can move for reasons that have nothing to do
with which technology is actually on the margin.

SELECTION EFFECT ON share_at_zero -- READ AS A LOWER BOUND, NOT A LEVEL
(ambiguity resolution 3)

The retained panel drops periods where p_star <= ZERO_PRICE (1 EUR/MWh) --
see FILTERS below, shared with concentration_margin.py. Per CLAUDE.md and
concentration_margin.py's own drop table, those periods grew from ~0% of
2018 to ~17.8% of 2026, and they are exactly the high-renewable hours where
offered-at-zero volume is largest (wind/solar oversupply pushing price to or
below zero). So `share_at_zero`, computed only on what survives that filter,
is measured on a sample that is INCREASINGLY SELECTED AGAINST the very
phenomenon it describes. Any rise in `share_at_zero` across the window is
therefore a LOWER BOUND on the true growth of zero-priced offered volume --
the true rise is at least as large, and probably larger, than what this
panel shows on the retained sample alone.

FILTERS -- match concentration_margin.py's block exactly, applied
SEQUENTIALLY so the three drop counts are disjoint and sum to the total:
  * market splitting (price_es != price_pt): no single curve to take a
    margin from when the two zones clear separately.
  * clearing-identity violation (unit dropouts), evaluated only on what
    survives the split filter: matched buy != matched sell beyond
    tolerance signals missing units, not a real market state.
  * p_star <= ZERO_PRICE, evaluated only on what survives both filters
    above: a near-zero clearing price is not economically meaningful for
    "where the curve is dense", and it is also the direct cause of the
    share_at_zero selection effect above.

DO NOT TUNE TO THE EXPECTED SHAPE (ambiguity resolution 4)

If `share_at_zero` does not rise, or `band_density_h5` does not fall, across
the window, that is reported plainly in the by-year table this script
prints and in the accompanying report -- bandwidths and filters are fixed at
the values above and are not retuned to produce an expected trend.

O/C AND V/C ARE NOT THE SAME AXIS

status "O" (Ofertada) is the full submitted curve; status "C" (Casada) is
the cleared portion -- summing them double-counts. side "V" (Venta) is sell,
side "C" (Compra) is buy -- the two "C"s mean different things. `verify()`'s
`cleared > offered` check is this trap turned into an assertion: it can only
fire if the two statuses were summed together somewhere upstream.
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
OUT = ROOT / "outputs/tables/supply_anatomy_panel.parquet"

VERIFY_MONTH = "202401"   # the month every other verification in this repo uses

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from residual_demand import (  # noqa: E402
    BANDWIDTHS, IDENTITY_TOL, KEY, ZERO_PRICE, band_offers,
    cleared_by_period,
)

BID_COLS = ["date", "period", "unit", "side", "status", "power_mw", "price_eur_mwh"]


def load_prices() -> pd.DataFrame:
    px = pq.read_table(DATA / "omie/prices/omie_day_ahead_prices.parquet").to_pandas()
    px["split"] = px.price_es != px.price_pt
    return px


def load_agents() -> pd.DataFrame:
    """unit -> tech, regime. Not restricted to SUPPLY_ROLES: technology/regime
    are attached to every bid row (sell and buy) via a left merge below, and
    only cleared SELL offers are ever used to read off marginal_tech/regime,
    which by construction can only be supply-side units."""
    return pq.read_table(AGENTS, columns=["unit", "tech", "regime"]).to_pandas()


def month_bounds(ym: str) -> tuple:
    lo = pd.Timestamp(f"{ym[:4]}-{ym[4:]}-01").date()
    hi = (pd.Timestamp(lo) + pd.offsets.MonthEnd(1)).date()
    return lo, hi


def load_bids_month(ym: str, lo, hi) -> pd.DataFrame:
    flt = (pc.field("date") >= lo) & (pc.field("date") <= hi)
    tbl = ds.dataset(BIDS / f"bids_{ym}.parquet").to_table(filter=flt, columns=BID_COLS)
    return tbl.to_pandas()


def anatomy_month(bids: pd.DataFrame, px_m: pd.DataFrame,
                   agents: pd.DataFrame) -> pd.DataFrame:
    """One row per (date, period): p_star, offered/cleared sell volume, the
    zero-price and below-clearing-price shares, band density at each
    bandwidth, and the marginal unit's technology/regime -- unfiltered.

    Carries mkt's split/identity_gap/p_star/resolution_min columns through so
    the caller can apply the standard filter block after concatenating
    months, exactly as concentration_margin.py does.
    """
    px_m = px_m[KEY + ["price_es", "split", "resolution_min", "utc_timestamp"]]
    mkt = cleared_by_period(bids).merge(px_m, on=KEY, how="inner").rename(
        columns={"price_es": "p_star", "sell_matched": "mw_cleared_sell"})

    b = bids.merge(agents, on="unit", how="left")
    sell_o = b[(b.status == "O") & (b.side == "V")]

    off = sell_o.groupby(KEY).power_mw.sum().rename("mw_offered_sell")
    zero = (sell_o[sell_o.price_eur_mwh <= 0.0]
            .groupby(KEY).power_mw.sum().rename("mw_at_zero"))
    out = mkt.merge(off, on=KEY, how="left").merge(zero, on=KEY, how="left")
    out["share_at_zero"] = out.mw_at_zero.fillna(0) / out.mw_offered_sell

    below = (sell_o.merge(mkt[KEY + ["p_star"]], on=KEY)
             .query("price_eur_mwh <= p_star")
             .groupby(KEY).power_mw.sum().rename("mw_below_p"))
    out = out.merge(below, on=KEY, how="left")
    out["share_below_p"] = out.mw_below_p.fillna(0) / out.mw_offered_sell

    for h in BANDWIDTHS:
        dens = (band_offers(b, mkt.rename(columns={"mw_cleared_sell": "q"}), h)
                .groupby(KEY).power_mw.sum().rename(f"band_density_h{h:g}"))
        out = out.merge(dens, on=KEY, how="left")

    # Marginal unit: the cleared SELL offer whose price is closest to p* from
    # below. Technology coverage is only 41.2% of volume, so marginal_tech is
    # null far more often than marginal_regime (63.3%). Both are kept.
    cl = b[(b.status == "C") & (b.side == "V")].merge(mkt[KEY + ["p_star"]], on=KEY)
    cl = cl[cl.price_eur_mwh <= cl.p_star]
    idx = cl.groupby(KEY).price_eur_mwh.idxmax()
    marg = cl.loc[idx, KEY + ["tech", "regime"]].rename(
        columns={"tech": "marginal_tech", "regime": "marginal_regime"})
    out = out.merge(marg, on=KEY, how="left")
    return out.drop(columns=["mw_at_zero", "mw_below_p"])


def verify(panel: pd.DataFrame) -> int:
    """The O/C additivity trap turned into an assertion, plus the range
    invariant share_at_zero must satisfy by construction."""
    bad = 0
    viol = (panel.mw_cleared_sell > panel.mw_offered_sell + 1e-6).mean()
    print(f"    cleared > offered on {viol:.4%} of periods (must be 0)")
    print("      -- if nonzero, 'O' and 'C' rows have been summed together")
    bad |= int(viol > 0)
    s = panel.share_at_zero.dropna()
    print(f"    share_at_zero range [{s.min():.3f}, {s.max():.3f}] (must be [0,1])")
    bad |= int(s.min() < 0 or s.max() > 1 + 1e-9)
    return bad


def apply_filters(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Sequential, DISJOINT filtering: split, then identity-gap (on what
    survived split), then zero-price (on what survived both) -- copied from
    concentration_margin.py so the two panels are filtered identically and
    comparable period-for-period."""
    n_all = len(panel)
    after_split = panel[~panel.split]
    n_split = n_all - len(after_split)
    after_gap = after_split[after_split.identity_gap <= IDENTITY_TOL]
    n_gap = len(after_split) - len(after_gap)
    keep = after_gap[after_gap.p_star > ZERO_PRICE]
    n_zero = len(after_gap) - len(keep)
    counts = dict(n_all=n_all, n_split=n_split, n_gap=n_gap, n_zero=n_zero,
                  n_keep=len(keep))
    return keep, counts


def print_drop_table(panel: pd.DataFrame) -> None:
    """Per-year breakdown of the filter drops -- copied from
    concentration_margin.py. The p_star <= ZERO_PRICE column here is also the
    direct driver of the share_at_zero selection effect documented in the
    module docstring: those are the periods where offered-at-zero volume is
    largest, and they are the ones being dropped."""
    print("\nPER-YEAR DROP TABLE (disjoint, sequential: split -> gap -> zero)")
    hdr = f"  {'year':>6} {'n_all':>8} {'split%':>7} {'gap%':>6} {'zero%':>7} {'keep%':>7} {'n_keep':>8}"
    print(hdr)
    for yr, grp in panel.groupby(panel.date.dt.year):
        _, c = apply_filters(grp)
        n = c["n_all"]
        print(f"  {yr:>6} {n:>8,} {c['n_split']/n:>6.1%} {c['n_gap']/n:>6.1%} "
              f"{c['n_zero']/n:>6.1%} {c['n_keep']/n:>6.1%} {c['n_keep']:>8,}")


def print_year_table(panel: pd.DataFrame) -> None:
    """Per-year median of the anatomy measures alongside the NON-NULL share
    of marginal_tech/marginal_regime -- ambiguity resolution 2 requires the
    technology trend never be read without its own coverage series."""
    print("\nPER-YEAR ANATOMY (medians on the RETAINED panel; "
          "share_at_zero is a LOWER bound -- see module docstring)")
    hdr = (f"  {'year':>6} {'share_zero':>10} {'share_belowP':>12} "
           f"{'dens_h5':>10} {'tech_cov':>9} {'regime_cov':>10}")
    print(hdr)
    for yr, grp in panel.groupby(panel.date.dt.year):
        print(f"  {yr:>6} {grp.share_at_zero.median():>10.3f} "
              f"{grp.share_below_p.median():>12.3f} "
              f"{grp.band_density_h5.median():>10.1f} "
              f"{grp.marginal_tech.notna().mean():>9.3f} "
              f"{grp.marginal_regime.notna().mean():>10.3f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true",
                    help=f"run the invariant checks on {VERIFY_MONTH} and exit")
    ap.add_argument("--full", action="store_true",
                    help="every month in the bid archive, not just the verify month")
    ap.add_argument("--save", action="store_true",
                    help="write the anatomy panel to outputs/tables/ (needs --full)")
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
        panel = anatomy_month(bids, px_m, agents)
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
        out = anatomy_month(bids, px_m, agents)
        frames.append(out)
        print(f"  [{i:3d}/{len(months)}] {ym}  {len(bids):>10,} bid rows  "
              f"{len(out):>8,} periods", end="\r", flush=True)

    print(" " * 60, end="\r")
    if not frames:
        print("no periods computed", file=sys.stderr)
        return 1

    panel = pd.concat(frames, ignore_index=True)
    panel["date"] = pd.to_datetime(panel["date"])

    # Same filters as concentration_margin.py / residual_demand_firm.py:
    # market splitting, then the clearing-identity gap (on what survives
    # splitting), then price <= ZERO_PRICE (on what survives both).
    keep, c = apply_filters(panel)
    n_all = c["n_all"]

    print("=" * 72)
    print(f"FULL SWEEP: {panel.date.nunique()} days, {n_all:,} periods")
    print("=" * 72)
    print(f"  dropped, market splitting (ES != PT) : {c['n_split']:7,}  "
          f"({c['n_split']/n_all:5.1%})")
    print(f"  dropped, clearing identity violated  : {c['n_gap']:7,}  "
          f"({c['n_gap']/n_all:5.1%})  (of what survived splitting)")
    print(f"  dropped, cleared at <= {ZERO_PRICE:g} EUR/MWh     : {c['n_zero']:7,}  "
          f"({c['n_zero']/n_all:5.1%})  (of what survived both above)")
    print(f"  retained periods                     : {c['n_keep']:7,}")
    assert c["n_split"] + c["n_gap"] + c["n_zero"] + c["n_keep"] == n_all, \
        "drop counts must be disjoint and sum to the total"

    print_drop_table(panel)
    print_year_table(keep)

    cols = (KEY + ["resolution_min", "p_star", "mw_offered_sell", "mw_cleared_sell",
                   "share_at_zero", "share_below_p"]
            + [f"band_density_h{h:g}" for h in BANDWIDTHS]
            + ["marginal_tech", "marginal_regime"])
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
