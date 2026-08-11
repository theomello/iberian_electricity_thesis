#!/usr/bin/env python3
"""Price impact at the clearing price, from submitted day-ahead bid curves.

    .venv/bin/python scripts/analysis/residual_demand_slope.py
    .venv/bin/python scripts/analysis/residual_demand_slope.py --save

Prototype on a sample: one day per month across the window (~101 days), which
is enough to see whether the slope series moves and to settle the bandwidth
before committing to a 354 M-row sweep. Nothing is written unless --save.

WHAT IS COMPUTED
----------------
Residual demand facing an infinitesimal participant is RD(p) = D(p) - S(p),
built from the *submitted* curves (status 'O'). Its slope at the clearing price

    |RD'(p*)| = |D'(p*)| + S'(p*)

and the reciprocal, 1 / |RD'|, is price impact: how far the clearing price
moves per MW withheld. Because S'_{-i} only shrinks as a firm gets larger,
every real firm faces a residual demand weakly steeper than this one -- so this
is a lower bound on price impact for every participant, and it needs no
ownership data. Multiplying by a firm's own cleared quantity turns it into a
markup, which is the step that waits on the unit->firm mapping.

SMOOTHING
---------
The curves are step functions and have no derivative. Differencing the
cumulative curve over a price window h is equivalent to counting offered MW
within +/- h of the clearing price:

    |RD'(p*)| ~= (sell MW in band + buy MW in band) / 2h

so the "derivative" is literally the density of offers near the clearing price,
and h is the only tuning knob. Reported for several h so the sensitivity is
visible rather than buried.

FILTERS (each one drops periods, and each count is reported)
------------------------------------------------------------
* Market splitting -- when price_es != price_pt the two zones clear separately
  and there is no single curve to take a slope of. Dropped here. NOTE for later
  work: these are ~6.7% of periods and are not random -- they are exactly the
  congested hours, when residual demand is steepest and market power is most
  concentrated. Dropping them biases price impact *downward*. Any final design
  should model them, not discard them.
* Unit dropouts -- on some days a block of units is absent from the file all
  day, so matched buy no longer equals matched sell. Detected from the
  clearing identity rather than hardcoded dates, so new cases are caught too.
* Empty bands -- if no offers sit within +/- h of the clearing price the slope
  is zero and price impact infinite. Dropped and counted.
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

SAMPLE_DAY = 15          # mid-month; exists in every month
BANDWIDTHS = (1.0, 2.0, 5.0, 10.0)   # euro/MWh
IDENTITY_TOL = 0.001     # relative gap between matched buy and matched sell
ZERO_PRICE = 1.0         # euro/MWh; at or below this, eta is not meaningful


def load_prices() -> pd.DataFrame:
    px = pq.read_table(DATA / "omie/prices/omie_day_ahead_prices.parquet").to_pandas()
    px["split"] = px.price_es != px.price_pt
    return px


def load_system() -> pd.DataFrame:
    """Hourly net load and VRE share from the REE 5-minute series, keyed on UTC.

    Joined on UTC rather than local time because the two sources use different
    clocks and DST days have 23 or 25 hours.
    """
    rt = pq.read_table(
        DATA / "ree/ree_realtime_5min.parquet",
        columns=["utc_timestamp", "demand", "wind", "solar_total"]).to_pandas()
    rt["hour_utc"] = rt.utc_timestamp.dt.floor("h")
    g = rt.groupby("hour_utc").agg(demand=("demand", "mean"),
                                   wind=("wind", "mean"),
                                   solar=("solar_total", "mean"),
                                   n=("demand", "size")).reset_index()
    g = g[g.n >= 10]
    g["net_load"] = g.demand - g.wind - g.solar
    g["vre_share"] = (g.wind + g.solar) / g.demand * 100
    return g[["hour_utc", "demand", "net_load", "vre_share"]]


def month_slopes(bids: pd.DataFrame, px_m: pd.DataFrame) -> pd.DataFrame:
    """Vectorised equivalent of period_slopes over a whole month.

    The per-period loop is O(rows x periods) and does not survive the full
    archive (~89,000 periods). Merging the clearing price onto the offer rows
    turns the band test into one boolean column, after which every bandwidth is
    a single groupby. Verified against period_slopes on the sample.
    """
    key = ["date", "period"]
    px_m = px_m[key + ["price_es", "split", "resolution_min", "utc_timestamp"]]

    mat = bids[bids.status == "C"]
    m = (mat.groupby(key + ["side"])["power_mw"].sum()
            .unstack("side").reindex(columns=["V", "C"]).fillna(0.0))
    m.columns = ["sell_matched", "buy_matched"]
    m = m[m.sell_matched > 0].reset_index()
    m["identity_gap"] = (m.sell_matched - m.buy_matched).abs() / m.sell_matched

    out = m.merge(px_m, on=key, how="inner").rename(
        columns={"price_es": "p_star", "sell_matched": "q_cleared"})

    off = bids[bids.status == "O"].merge(
        out[key + ["p_star"]], on=key, how="inner")
    dev = (off.price_eur_mwh - off.p_star).abs()

    for h in BANDWIDTHS:
        mw = (off.loc[dev <= h].groupby(key)["power_mw"].sum()
                 .rename(f"mw_h{h:g}"))
        out = out.merge(mw, on=key, how="left")
        slope = out[f"mw_h{h:g}"].fillna(0.0) / (2 * h)
        out[f"slope_h{h:g}"] = slope
        out[f"impact_h{h:g}"] = np.where(slope > 0, 1 / slope.replace(0, np.nan), np.nan)
        out[f"eta_h{h:g}"] = np.where(
            (slope > 0) & (out.p_star > 0), slope * out.p_star / out.q_cleared, np.nan)
    return out.drop(columns=[f"mw_h{h:g}" for h in BANDWIDTHS])


def period_slopes(bids: pd.DataFrame, px_day: pd.DataFrame) -> list[dict]:
    """One row per period of one day."""
    out = []
    off = bids[bids.status == "O"]
    mat = bids[bids.status == "C"]

    for period, pxrow in px_day.set_index("period").iterrows():
        p_star = pxrow.price_es
        o = off[off.period == period]
        m = mat[mat.period == period]
        if o.empty or m.empty:
            continue

        sell_matched = m.loc[m.side == "V", "power_mw"].sum()
        buy_matched = m.loc[m.side == "C", "power_mw"].sum()
        if sell_matched <= 0:
            continue
        identity_gap = abs(sell_matched - buy_matched) / sell_matched

        rec = {
            "date": None,                            # filled by caller
            "period": int(period),
            "utc_timestamp": pxrow.utc_timestamp,
            "p_star": float(p_star),
            "q_cleared": float(sell_matched),
            "split": bool(pxrow.split),
            "identity_gap": float(identity_gap),
            "resolution_min": int(pxrow.resolution_min),
        }

        sell_p = o.loc[o.side == "V", "price_eur_mwh"].to_numpy()
        sell_q = o.loc[o.side == "V", "power_mw"].to_numpy()
        buy_p = o.loc[o.side == "C", "price_eur_mwh"].to_numpy()
        buy_q = o.loc[o.side == "C", "power_mw"].to_numpy()

        for h in BANDWIDTHS:
            in_s = np.abs(sell_p - p_star) <= h
            in_b = np.abs(buy_p - p_star) <= h
            mw = sell_q[in_s].sum() + buy_q[in_b].sum()
            slope = mw / (2 * h)                      # MW per euro/MWh
            rec[f"slope_h{h:g}"] = float(slope)
            rec[f"impact_h{h:g}"] = float(1 / slope) if slope > 0 else np.nan
            # Scale-free version. eta = |RD'| * p / Q is the residual demand
            # elasticity evaluated at market scale; a firm with share s faces
            # Lerner = s / eta. Price impact alone is NOT comparable across
            # years, because a fixed +/-h euro band is a *narrower relative*
            # window when the price level is 200 than when it is 50, which
            # mechanically thins the band and inflates impact in 2022.
            rec[f"eta_h{h:g}"] = (float(slope * p_star / sell_matched)
                                  if slope > 0 and p_star > 0 else np.nan)
        out.append(rec)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true",
                    help="write the per-period table to outputs/tables/ (off by default)")
    ap.add_argument("--day", type=int, default=SAMPLE_DAY)
    ap.add_argument("--full", action="store_true",
                    help="every day in the archive, not one per month")
    args = ap.parse_args()

    if not BIDS.is_dir():
        print(f"no bid archive at {BIDS}", file=sys.stderr)
        return 1

    px = load_prices()
    months = sorted(p.stem.replace("bids_", "") for p in BIDS.glob("bids_*.parquet"))

    cols = ["date", "period", "side", "status", "power_mw", "price_eur_mwh"]
    frames: list[pd.DataFrame] = []
    for i, ym in enumerate(months, 1):
        if args.full:
            lo = pd.Timestamp(f"{ym[:4]}-{ym[4:]}-01").date()
            hi = (pd.Timestamp(lo) + pd.offsets.MonthEnd(1)).date()
            px_m = px[(px.date >= lo) & (px.date <= hi)]
            flt = (pc.field("date") >= lo) & (pc.field("date") <= hi)
        else:
            day = pd.Timestamp(f"{ym[:4]}-{ym[4:]}-{args.day:02d}").date()
            px_m = px[px.date == day]
            flt = pc.field("date") == day
        if px_m.empty:
            continue
        tbl = ds.dataset(BIDS / f"bids_{ym}.parquet").to_table(filter=flt, columns=cols)
        if tbl.num_rows == 0:
            continue
        frames.append(month_slopes(tbl.to_pandas(), px_m))
        print(f"  [{i:3d}/{len(months)}] {ym}  {tbl.num_rows:>10,} rows",
              end="\r", flush=True)

    if not frames:
        print("no periods computed", file=sys.stderr)
        return 1
    d = pd.concat(frames, ignore_index=True)
    d["date"] = pd.to_datetime(d["date"])
    d["year"] = d.date.dt.year

    n_all = len(d)
    n_split = int(d.split.sum())
    n_drop = int((d.identity_gap > IDENTITY_TOL).sum())
    keep = d[(~d.split) & (d.identity_gap <= IDENTITY_TOL)].copy()
    n_empty = int(keep["impact_h5"].isna().sum())
    keep = keep[keep["impact_h5"].notna()]

    # eta = |RD'| p / Q is mechanically zero when the market clears at zero, so
    # zero-price hours would masquerade as infinitely steep residual demand.
    # The Lerner index is not defined at p = 0 either -- a proportional markup
    # over a zero price is meaningless -- so these hours are a different
    # question, not a harder version of this one. Excluded, and counted: the
    # share is a result in its own right.
    n_zero = int((keep.p_star <= ZERO_PRICE).sum())
    zero_share = keep.groupby("year").apply(
        lambda g: (g.p_star <= ZERO_PRICE).mean(), include_groups=False)
    keep = keep[keep.p_star > ZERO_PRICE]

    print(" " * 40, end="\r")
    print("=" * 72)
    print(f"SAMPLE: day {args.day} of each month, {d.date.nunique()} days, "
          f"{n_all:,} periods")
    print("=" * 72)
    print(f"  dropped, market splitting (ES != PT) : {n_split:5,}  "
          f"({n_split/n_all:5.1%})")
    print(f"  dropped, clearing identity violated  : {n_drop:5,}  "
          f"({n_drop/n_all:5.1%})")
    print(f"  dropped, no offers within +/-5 EUR   : {n_empty:5,}")
    print(f"  dropped, cleared at <= {ZERO_PRICE:g} EUR/MWh     : {n_zero:5,}  "
          f"({n_zero/n_all:5.1%})   <- see note in docstring")
    print(f"  retained                             : {len(keep):5,}")
    print("\n  share of periods clearing at <= 1 EUR/MWh, by year:")
    print("   " + "  ".join(f"{y}:{v:5.1%}" for y, v in zero_share.items()))

    bad_days = d.loc[d.identity_gap > IDENTITY_TOL, "date"].dt.date.unique()
    if len(bad_days):
        print(f"\n  identity-violating days in sample: "
              f"{', '.join(str(x) for x in bad_days[:6])}"
              f"{' ...' if len(bad_days) > 6 else ''}")

    # Attach system conditions so the slope can be read against VRE.
    sysdf = load_system()
    keep["hour_utc"] = pd.to_datetime(keep.utc_timestamp, utc=True).dt.floor("h")
    keep = keep.merge(sysdf, on="hour_utc", how="left")

    print("\n" + "-" * 72)
    print("RESIDUAL DEMAND ELASTICITY  eta = |RD'| p / Q, median by year")
    print("  scale-free; a firm with market share s faces Lerner = s / eta")
    print("-" * 72)
    ecols = [f"eta_h{h:g}" for h in BANDWIDTHS]
    by_year = keep.groupby("year")[ecols].median()
    by_year.columns = [f"h={h:g}" for h in BANDWIDTHS]
    by_year.insert(0, "periods", keep.groupby("year").size())
    by_year["Lerner @ s=.20"] = 0.20 / by_year["h=5"]
    print(by_year.round(3).to_string())

    print("\n" + "-" * 72)
    print("PRICE IMPACT  (EUR/MWh per 100 MW withheld), median by year")
    print("  NOT comparable across years -- a fixed euro band is a narrower")
    print("  relative window when prices are high. Shown for reference only.")
    print("-" * 72)
    cols = [f"impact_h{h:g}" for h in BANDWIDTHS]
    imp = keep.groupby("year")[cols].median() * 100
    imp.columns = [f"h={h:g}" for h in BANDWIDTHS]
    imp.insert(0, "median p*", keep.groupby("year").p_star.median())
    print(imp.round(3).to_string())

    print("\n" + "-" * 72)
    print("BANDWIDTH SENSITIVITY  (eta, whole sample)")
    print("-" * 72)
    for h in BANDWIDTHS:
        s = keep[f"eta_h{h:g}"]
        print(f"  h={h:4g} EUR   median {s.median():7.3f}   p25 {s.quantile(.25):7.3f}"
              f"   p75 {s.quantile(.75):7.3f}")
    print("\n  Spearman rank correlation across bandwidths:")
    print(keep[ecols].corr(method="spearman").round(3).to_string())

    print("\n" + "-" * 72)
    print("DISPERSION  (eta, h=5): low eta = steep residual demand = more power")
    print("-" * 72)
    g = keep.groupby("year")["eta_h5"]
    disp = pd.DataFrame({
        "median": g.median(),
        "p10": g.quantile(.10),
        "p01": g.quantile(.01),
        "median/p10": g.median() / g.quantile(.10),
    })
    print(disp.round(3).to_string())

    print("\n" + "-" * 72)
    print("SHAPE, WITHIN YEAR: eta by net-load tercile (h=5)")
    print("  pooling across years would confound the fuel-cost level shift")
    print("-" * 72)
    w = keep[keep.net_load.notna()].copy()
    w["nl_tercile"] = w.groupby("year").net_load.transform(
        lambda s: pd.qcut(s, 3, labels=["low", "mid", "high"], duplicates="drop"))
    tab = w.pivot_table(index="year", columns="nl_tercile",
                        values="eta_h5", aggfunc="median", observed=False)
    tab["high/low"] = tab["high"] / tab["low"]
    print(tab.round(3).to_string())

    print("\n" + "-" * 72)
    print("ETA AGAINST VRE SHARE, within year (h=5, median)")
    print("-" * 72)
    w["vre_tercile"] = w.groupby("year").vre_share.transform(
        lambda s: pd.qcut(s, 3, labels=["low", "mid", "high"], duplicates="drop"))
    tab2 = w.pivot_table(index="year", columns="vre_tercile",
                         values="eta_h5", aggfunc="median", observed=False)
    tab2["high/low"] = tab2["high"] / tab2["low"]
    print(tab2.round(3).to_string())
    print(f"\n  pooled within-year correlation of eta with VRE share: "
          f"{w.groupby('year')[['eta_h5', 'vre_share']].corr(method='spearman').unstack().iloc[:, 1].mean():.3f}"
          f"   (mean of per-year Spearman)")

    if args.save:
        outdir = ROOT / "outputs" / "tables"
        outdir.mkdir(parents=True, exist_ok=True)
        # Name the scope: a full-archive run and a one-day-a-month sample are
        # different objects and must not overwrite one another. Parquet rather
        # than CSV -- 79k rows x 25 float columns is ~25 MB as text and loses
        # precision on the way out.
        scope = "full" if args.full else f"sample_day{args.day:02d}"
        path = outdir / f"residual_demand_slope_{scope}.parquet"
        keep.to_parquet(path, index=False)
        print(f"\nwrote {path.relative_to(ROOT)}  "
              f"({len(keep):,} rows, {path.stat().st_size/1e6:.1f} MB)")
    else:
        print("\n(nothing written; pass --save to keep the per-period table)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
