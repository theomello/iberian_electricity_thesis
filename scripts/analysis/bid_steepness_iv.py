#!/usr/bin/env python3
"""Do firms bid more steeply when renewables are high? The behavioural channel.

    .venv/bin/python scripts/analysis/bid_steepness_iv.py

THE PROBLEM THIS SOLVES

Residual demand elasticity fell from 1.83 to 0.45 as renewables grew, and the
weather instrument says that is causal. But it does not say it is *market power*.
Three channels produce the same fall:

  mechanical    renewables push the clearing point to a steeper part of the
                merit order; nobody's behaviour changes
  compositional coal exits, so fewer flexible units sit near the margin
  behavioural   firms submit steeper curves

Only the third is conduct. An instrument on market-wide eta cannot separate them,
because weather moves renewable output, which moves the clearing point
mechanically -- the IV estimate is entirely consistent with no one doing anything
differently.

THE FIX: PUT BEHAVIOUR ON THE LEFT-HAND SIDE

The mechanical channel works through *where the market clears*. It does not
change what a unit submits. So make the outcome the steepness of a unit's own
offer curve:

    steepness_it = beta * vre_share_t + unit FE + month FE + controls

A bid curve is a choice. If units submit steeper curves when renewables are high,
that is conduct -- it cannot be the clearing point sliding along a fixed stack,
because the curve *is* the stack.

`vre_share` is instrumented with wind speed at the wind sites and irradiance at
the solar sites, as in eta_vre_iv.py. Temperature enters as a control, never as
an instrument, because it shifts demand directly.

Fixed effects do real work here. `vre_share` varies hour to hour, so **month**
fixed effects absorb fuel prices, carbon and every slow-moving cost driver while
leaving the identifying variation untouched. That is the opposite of the policy
designs tried earlier, where treatment was a monthly time series and time fixed
effects absorbed it.

MEASURING STEEPNESS

Each unit submits a step function. Sort its steps by price, take the cumulative
share of its own offered volume, and fit

    price = a + b * (cumulative share of own volume)

`b` is the euro spread across the unit's whole offer curve: how much more it
demands for its last MW than its first. Scale-free, so a 2,000 MW portfolio and
a 50 MW plant are comparable. Units offering a single step have no slope and are
dropped -- they are price takers and have no bidding margin to observe.

ONE CONCEPTUAL POINT, STATED PLAINLY

A firm that steepens its curve *because* residual demand became mechanically
steeper is still behaving differently -- it resubmitted. This design does not try
to separate "rational response to a mechanical change" from "strategic
escalation", because that distinction is not identified by anything here. The
line drawn is: did the submitted curve change, or only the clearing point.
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

MONTHS = [f"{y}{m}" for y in range(2018, 2027) for m in ("04", "10")]


def steepness(g: pd.DataFrame) -> float:
    """Euro spread across a unit's own offer curve, per unit of its own volume."""
    if len(g) < 2:
        return np.nan
    g = g.sort_values("price_eur_mwh")
    w = g.power_mw.to_numpy(float)
    if w.sum() <= 0:
        return np.nan
    share = np.cumsum(w) / w.sum()
    p = g.price_eur_mwh.to_numpy(float)
    if np.ptp(share) == 0:
        return np.nan
    b, _ = np.polyfit(share, p, 1)
    return float(b)


def build(band: float | None = None) -> pd.DataFrame:
    eta = pq.read_table(ETA, columns=["date", "period", "utc_timestamp",
                                      "vre_share", "demand", "p_star"]).to_pandas()
    eta["date"] = pd.to_datetime(eta.date)
    rows = []
    for ym in MONTHS:
        f = DATA / "omie/bids/parquet" / f"bids_{ym}.parquet"
        if not f.exists():
            continue
        t = ds.dataset(f).to_table(
            filter=(pc.field("status") == "O") & (pc.field("side") == "V"),
            columns=["date", "period", "unit", "price_eur_mwh", "power_mw"]
        ).to_pandas()
        t = t[(t.price_eur_mwh >= 0) & (t.price_eur_mwh < 3000)]
        if t.empty:
            continue
        t["date"] = pd.to_datetime(t.date)
        if band is not None:
            # Restrict to the economically relevant region. Offers far above the
            # clearing price are withholding bids that express an intention not to
            # run, not a cost -- pooling them with cost-revealing offers is what
            # made the levy estimates swing with the trimming rule.
            t = t.merge(eta[["date", "period", "p_star"]], on=["date", "period"],
                        how="inner")
            t = t[(t.price_eur_mwh - t.p_star).abs() <= band].drop(columns=["p_star"])
        # Only units that actually bid a curve; single-step price takers have no
        # bidding margin and would enter as structural zeros.
        n = t.groupby(["date", "period", "unit"]).price_eur_mwh.transform("size")
        t = t[n >= 3]
        if t.empty:
            continue
        s = (t.groupby(["date", "period", "unit"])
               .apply(steepness, include_groups=False)
               .rename("steep").reset_index())
        rows.append(s.dropna(subset=["steep"]))
    d = pd.concat(rows, ignore_index=True)
    d = d.merge(eta, on=["date", "period"], how="inner")

    w = pd.read_parquet(WX)
    w["hour_utc"] = pd.to_datetime(w.utc_timestamp, utc=True)
    d["hour_utc"] = pd.to_datetime(d.utc_timestamp, utc=True).dt.floor("h")
    d = d.merge(w.drop(columns=["utc_timestamp"]), on="hour_utc", how="inner")

    d["month"] = d.hour_utc.dt.to_period("M")
    d["hour"] = d.hour_utc.dt.hour
    d["wind"] = d.wind_speed_100m_wind_sites
    d["wind3"] = d.wind ** 3 / 1000.0
    d["rad"] = d.radiation_solar_sites / 100.0
    d["temp"] = d.temperature_2m_mean
    d["log_demand"] = np.log(d.demand.clip(lower=1))
    return d.dropna(subset=["steep", "vre_share", "wind", "rad", "temp"])


def demean(v: np.ndarray, *codes) -> np.ndarray:
    """Absorb several fixed effects by alternating projection."""
    v = v.astype(float).copy()
    for _ in range(300):
        prev = v.copy()
        for c in codes:
            v -= np.bincount(c, v)[c] / np.bincount(c)[c]
        if np.max(np.abs(v - prev)) < 1e-10:
            break
    return v


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--band", type=float, default=None,
                    help="keep only offers within this many EUR/MWh of the "
                         "clearing price")
    args = ap.parse_args()

    d = build(args.band)
    ui = pd.factorize(d.unit)[0]
    mi = pd.factorize(d.month)[0]
    hi = pd.factorize(d.hour)[0]

    y = demean(d.steep.to_numpy(), ui, mi, hi)
    x = demean(d.vre_share.to_numpy(), ui, mi, hi)
    ctrl = np.column_stack([demean(d[c].to_numpy(), ui, mi, hi)
                            for c in ("log_demand", "temp")])
    inst = np.column_stack([demean(d[c].to_numpy(), ui, mi, hi)
                            for c in ("wind", "wind3", "rad")])

    def ols(Y, X):
        b, *_ = np.linalg.lstsq(X, Y, rcond=None)
        e = Y - X @ b
        n, k = X.shape
        s2 = e @ e / max(n - k, 1)
        V = s2 * np.linalg.pinv(X.T @ X)
        return b, np.sqrt(np.diag(V))

    print(f"BID-CURVE STEEPNESS AND RENEWABLES\n")
    print(f"  {len(d):,} unit-periods, {d.unit.nunique():,} units, "
          f"{d.month.nunique()} months, {d.date.dt.year.min()}-{d.date.dt.year.max()}")
    print(f"  mean steepness {d.steep.mean():.1f} EUR/MWh across a unit's own curve")
    print(f"  absorbed: unit, month, hour-of-day fixed effects\n")

    X = np.column_stack([x, ctrl])
    b, se = ols(y, X)
    print(f"{'estimator':<12}{'beta on vre_share':>20}{'se':>10}{'t':>8}")
    print(f"{'OLS':<12}{b[0]:>20.4f}{se[0]:>10.4f}{b[0]/se[0]:>8.2f}")

    # First stage, then 2SLS.
    Z = np.column_stack([inst, ctrl])
    bz, _ = ols(x, Z)
    xhat = Z @ bz
    r = x - xhat
    F = ((x.var() - r.var()) / 3) / (r.var() / (len(x) - 3 - ctrl.shape[1]))
    X2 = np.column_stack([xhat, ctrl])
    b2, se2 = ols(y, X2)
    print(f"{'2SLS':<12}{b2[0]:>20.4f}{se2[0]:>10.4f}{b2[0]/se2[0]:>8.2f}")
    print(f"\n  first-stage partial F on the 3 weather instruments: {F:,.0f}")

    sd = d.vre_share.std()
    print(f"\n  a one-SD rise in the renewable share ({sd:.3f}) changes a unit's "
          f"own offer spread by {b2[0]*sd:+.2f} EUR/MWh")
    print(f"  against a mean spread of {d.steep.mean():.1f} EUR/MWh "
          f"({b2[0]*sd/d.steep.mean():+.1%})")

    if args.save:
        p = ROOT / "outputs" / "tables" / "bid_steepness_panel.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        d.assign(month=d.month.astype(str)).to_parquet(p, index=False)
        print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
