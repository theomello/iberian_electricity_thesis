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

COVERAGE DRIFT CAN INFLATE hhi_margin -- SIGN CHECKED, NOT JUST FLAGGED
(ambiguity resolution 2, corrected after review round 1)

Firm-mapping coverage is not stable over this window, and the direction
matters: renormalising HHI over a SHRINKING mapped set mechanically RAISES
it, because the shares that get renormalised away are treated as if they
belonged entirely to the firms that remain. corr(hhi_margin_h5,
mapped_share_margin_h5) is negative in this data (~-0.29): lower coverage
periods read as MORE concentrated, not less. A coverage-adjusted bound
follows directly -- if unmapped in-band volume were atomistic (i.e. spread
across many small unmapped players rather than concentrated in one), then

    HHI_true ~= HHI_measured * coverage^2

(each of the two shares in every cross-term of the HHI sum picks up one
factor of the true, lower coverage-scaled share). This bound is reported by
year in the panel's companion report rather than baked into the saved
columns, since it is a sensitivity check on `mapped_share_margin_h5`, not a
new primitive. Read `mapped_share_margin_h5` by year -- its MEAN and p10,
not just its median, since the low-coverage tail is exactly where the bound
bites hardest -- alongside the HHI trend, not after it.

FILTERS -- match residual_demand_firm.py's block exactly, applied
SEQUENTIALLY so the three drop counts are disjoint and sum to the total
(review round 1: an earlier version counted the identity-gap drop on the
still-unfiltered panel, over-stating it by counting periods a second time
that market-splitting had already removed):
  * market splitting (price_es != price_pt): no single curve to take a
    margin from when the two zones clear separately.
  * clearing-identity violation (unit dropouts), evaluated only on what
    survives the split filter: matched buy != matched sell beyond
    tolerance signals missing units, not a real market state.
  * p_star <= ZERO_PRICE, evaluated only on what survives both filters
    above: a near-zero clearing price is not economically meaningful for
    "who sets the margin".

These drops are NOT stable over the window either -- see the per-year drop
table this script prints during `--full`, and the report. The retained
fraction falls sharply in the last two years of the archive, driven mainly
by p_star <= ZERO_PRICE periods becoming much more common (near-zero and
negative prices from VRE oversupply) and, to a lesser extent, by more
market splitting. Late years are meaningfully thinned, and not randomly --
any trend read off the pooled panel should be re-checked per year rather
than trusted from the aggregate drop counts alone.

BAND-THINNING AT HIGH PRICE LEVELS -- CAVEAT AND THE CHECK THAT ANSWERS IT

scripts/lib/residual_demand.py's own docstring flags that a fixed +/-h
EUR/MWh band is a narrower *relative* window when the price level is high,
which mechanically thins the band and could inflate hhi_margin in
high-price years for a reason that has nothing to do with concentration.
This is a real caveat for hhi_margin_h{h} as computed here. It is answered,
not just noted: median p* is essentially unchanged across the window ends
(60.4 EUR/MWh in 2018, 63.0 in 2026 on the retained periods), so the
relative-band-width channel cannot be doing much work here on its own. The
sharper test is to hold price level fixed and let the years vary: restrict
to periods where p* falls in a single common band (e.g. [55, 70] EUR/MWh,
chosen to bracket both years' medians) and recompute hhi_margin_h5 by year
on that constant-relative-band-width subsample. In this data the rise is
LARGER on that price-matched subsample than on the unrestricted panel, not
smaller -- see the report for the by-year numbers. That is the opposite of
what band-thinning at high prices would predict if it were driving the
result, and is the single most persuasive check against the "it's just the
band, not concentration" reading.

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
    mapped_share is reported alongside so the renormalisation is visible --
    and see the module docstring for why a SHRINKING mapped set mechanically
    RAISES this number, which is the opposite of what an earlier version of
    this repo's report claimed.
    """
    s = shares / shares.sum()
    return float((s ** 2).sum() * 10000)


def concentration_month(bids: pd.DataFrame, px_m: pd.DataFrame,
                         agents: pd.DataFrame) -> pd.DataFrame:
    """One row per (date, period): p_star plus both HHIs, unfiltered.

    Carries mkt's split/identity_gap/p_star/resolution_min columns through so
    the caller can apply the standard filter block after concatenating
    months, exactly as residual_demand_firm.py does.
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


def apply_filters(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Sequential, DISJOINT filtering: split, then identity-gap (on what
    survived split), then zero-price (on what survived both). Each count is
    taken on the population it actually removed from, so the four numbers
    (n_split, n_gap, n_zero, n_keep) sum exactly to n_all -- unlike an
    earlier version that counted n_gap on the still-unfiltered panel and
    double-counted periods that were both split AND identity-gap-violating.
    """
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
    """Per-year breakdown of the filter drops -- printed because the pooled
    counts conceal a severe late-window trend (review round 1, finding 3):
    the retained fraction falls from ~95% in 2018 to ~66% in 2026, driven
    mostly by p_star <= ZERO_PRICE periods (near-zero/negative prices from
    VRE oversupply) becoming far more common, and secondarily by more
    market splitting."""
    print("\nPER-YEAR DROP TABLE (disjoint, sequential: split -> gap -> zero)")
    hdr = f"  {'year':>6} {'n_all':>8} {'split%':>7} {'gap%':>6} {'zero%':>7} {'keep%':>7} {'n_keep':>8}"
    print(hdr)
    for yr, grp in panel.groupby(panel.date.dt.year):
        _, c = apply_filters(grp)
        n = c["n_all"]
        print(f"  {yr:>6} {n:>8,} {c['n_split']/n:>6.1%} {c['n_gap']/n:>6.1%} "
              f"{c['n_zero']/n:>6.1%} {c['n_keep']/n:>6.1%} {c['n_keep']:>8,}")


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
    # gap (on what survives splitting), then price <= ZERO_PRICE (on what
    # survives both). Disjoint, sequential -- see apply_filters().
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

    cols = (["date", "period", "resolution_min", "p_star", "hhi_total"]
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
