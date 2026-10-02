#!/usr/bin/env python3
"""The concentration side of Ito & Reguant — and where heat and rainfall finally
have an outcome worth testing.

    .venv/bin/python scripts/analysis/sequential_premium_concentration.py

Inputs: outputs/tables/{sequential_premium_panel,firm_shares_hourly_all,
residual_demand_slope_full}.parquet, published intraday prices, the weather
instruments. Prints; writes nothing.

WHY

`sequential_market_premium.py` establishes the premium: +0.950 EUR/MWh, t = 5.84
on month clusters, surviving 10% trimming. But a positive premium is **necessary,
not sufficient** — risk premia, forecast errors and unit commitment all generate
one under competition. Ito & Reguant's identification is not the premium's
existence but **how it varies with market power and with arbitrage capacity**:

    dπ/d|RD'|  < 0     steeper residual demand for the dominant firm -> larger π
    dπ/d|A'|   < 0     more arbitrage capacity -> smaller π

This file builds both sides.

THE MARKET-POWER SIDE

Three measures, weakest to strongest:

* `hhi`      — Herfindahl over day-ahead cleared shares of mapped firms. Crude,
               and 18% of generation volume is unattributed, so it is a share of
               what could be mapped rather than a true market HHI.
* `1/eta`    — the inverse residual-demand elasticity at the clearing price. The
               object that actually appears in the first-order condition, and it
               needs no ownership data at all.
* `max_lerner` — the largest firm-level `share / eta` in the period. Closest to
               the mechanism, since their story is a *dominant firm* withholding
               forward, not a diffusely concentrated market.

THE ARBITRAGE SIDE

`n_units` and `id_vol`, the count of units and volume traded in the intraday
session. Both are endogenous to the premium — a larger premium attracts entry —
which is exactly why the weather instruments below matter.

AND THIS IS WHERE HEAT AND RAINFALL COME BACK

Four hydro probes and two heat designs failed in this repo, all of them on the
marginal-cost measure. The premium needs no cost measure, so the same shocks can
be re-used against an outcome that can actually carry them:

* **Heat** raises net load, which tightens the market and steepens residual
  demand. If the market-power channel operates, `dπ/dCDH > 0`.
* **Wind** is the arbitrageur. `dπ/dwind < 0` is the same prediction the VRE
  share already delivered, now with an exogenous instrument rather than a
  realised share.
* **Rainfall** shifts hydro's availability, and hydro is the *other* flexible
  arbitrageur between the two auctions. A basin inflow shock is an exogenous
  shifter of arbitrage capacity that has nothing to do with wind.

Each enters twice: as a reduced form on the premium, and as an instrument for
the endogenous concentration and arbitrage measures.

WHAT THIS STILL CANNOT SEPARATE

**Wind forecast error.** If wind is systematically under-forecast at gate
closure, intraday supply is higher and its price lower, producing a premium with
no conduct at all — and that error is correlated with wind itself, so it mimics
the arbitrage channel exactly. Separating them needs a published day-ahead wind
forecast: ESIOS 1777, REE's D+1 wind forecast, on disk from 2019 since 2026-10-02
(not 541, which REE updates hourly up to delivery). Until this design is rerun
with it, `dπ/dwind < 0` is consistent with both stories and should be reported
as such. The heat channel is *not* subject to this, which is a reason to weight
it more heavily than its size would suggest.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs" / "tables"
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from hydro_spill_window_did import demean, ols_cluster  # noqa: E402
from net_load_iv import instruments, net_load_daily, tsls  # noqa: E402


def concentration() -> pd.DataFrame:
    f = pd.read_parquet(OUT / "firm_shares_hourly_all.parquet",
                        columns=["date", "period", "firm", "share", "eta_h5",
                                 "lerner"])
    f["date"] = pd.to_datetime(f.date)
    g = (f.groupby(["date", "period"], as_index=False)
           .agg(hhi=("share", lambda x: float((x ** 2).sum())),
                top_share=("share", "max"),
                max_lerner=("lerner", "max"),
                n_firms=("firm", "nunique"),
                eta=("eta_h5", "first")))
    g["inv_eta"] = 1.0 / g.eta.replace(0, np.nan)
    return g


def fit(d, y, xs, j, fe1, fe2, cl):
    cols = list(dict.fromkeys([y] + xs + [fe1, fe2, cl]))
    s = d[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 300:
        return None
    M = demean(s[[y] + xs].to_numpy(float),
               pd.factorize(s[fe1])[0], pd.factorize(s[fe2])[0])
    k = xs.index(j)
    if M[:, 1 + k].std() < 1e-9:
        return None
    g = pd.factorize(s[cl])[0]
    b, se, _ = ols_cluster(M[:, 0], M[:, 1:], g)
    return dict(beta=b[k], se=se[k], t=b[k] / se[k], n=len(s),
                nclust=len(np.unique(g)))


def row(lbl, r, w=48):
    if r is None:
        print(f"{lbl:<{w}}{'insufficient obs':>42}")
        return
    print(f"{lbl:<{w}}{r['beta']:>12.4f}{r['se']:>10.4f}{r['t']:>7.2f}"
          f"{r['n']:>10,}{r['nclust']:>8}")


def rowiv(lbl, r, w=44):
    if r is None:
        print(f"{lbl:<{w}}{'insufficient obs':>46}")
        return
    print(f"{lbl:<{w}}{r['beta']:>12.4f}{r['se']:>10.4f}"
          f"{r['beta']/r['se']:>7.2f}{r['F']:>9.1f}{r['n']:>10,}{r['nclust']:>7}")


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()

    d = pd.read_parquet(OUT / "sequential_premium_panel.parquet")
    d["date"] = pd.to_datetime(d.date)
    q = pd.read_parquet(DATA / "omie/intraday_prices/omie_intraday_prices.parquet")
    q["date"] = pd.to_datetime(q.date)
    q = q.rename(columns={"price_a": "id_pt", "price_b": "id_es"})
    q["id_split"] = q.id_pt != q.id_es
    d = d.merge(q[["date", "session", "period", "id_es", "id_split"]],
                on=["date", "session", "period"], how="inner")
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "price_es", "price_pt",
                                  "resolution_min", "utc_timestamp"])
    px["date"] = pd.to_datetime(px.date)
    px["split"] = px.price_es != px.price_pt
    d = d.merge(px, on=["date", "period"], how="inner")
    d = d[(d.res == d.resolution_min) & (~d.split) & (~d.id_split)]
    d["premium"] = d.price_es - d.id_es

    d = d.merge(concentration(), on=["date", "period"], how="left")
    rd = pd.read_parquet(OUT / "residual_demand_slope_full.parquet",
                         columns=["date", "period", "vre_share", "demand"])
    rd["date"] = pd.to_datetime(rd.date)
    d = d.merge(rd, on=["date", "period"], how="left")
    d = d.merge(net_load_daily(), on="date", how="left")
    d = d.merge(instruments(), on="date", how="left")

    # basin rainfall: hydro is the OTHER flexible arbitrageur, and its shifter
    # has nothing to do with wind
    p = pd.read_parquet(DATA / "weather/precipitation_basins_daily.parquet")
    p["date"] = pd.to_datetime(p.date)
    nat = (p.groupby("date", as_index=False)
             .agg(rain=("precipitation_sum", "mean")))
    nat = nat.sort_values("date")
    nat["rain3"] = nat.rain.rolling(3, min_periods=3).sum()
    nat["mon"] = nat.date.dt.month
    nat["rain_shock"] = (nat.groupby("mon").rain3.rank(pct=True) >= 0.90).astype(float)
    d = d.merge(nat[["date", "rain3", "rain_shock"]], on="date", how="left")

    d["ldem"] = np.log(d.demand.clip(lower=1))
    d["hh"] = pd.to_datetime(d.utc_timestamp).dt.hour
    d["ym"] = d.date.dt.to_period("M").astype(str)
    d["l_units"] = np.log(d.n_units.clip(lower=1))
    s1 = d[d.session == 1].copy()

    print("=" * 106)
    print("THE CONCENTRATION SIDE — does the premium rise with market power?")
    print("=" * 106)
    print(f"  {len(d):,} period-sessions; session 1 only: {len(s1):,}")
    print(f"  premium mean {d.premium.mean():+.3f} | HHI mean {d.hhi.mean():.4f}"
          f" | top firm share {d.top_share.mean():.1%} | firms/period "
          f"{d.n_firms.mean():.0f}")
    print(f"  eta mean {d.eta.mean():.3f} | max firm Lerner mean "
          f"{d.max_lerner.mean():.3f}")

    hdr = (f"\n{'specification':<48}{'beta':>12}{'se':>10}{'t':>7}"
           f"{'obs':>10}{'clust':>8}")
    ctrl = ["ldem", "vre_share"]

    print("\n" + "-" * 106)
    print("A. MARKET POWER -> PREMIUM.  Prediction: beta > 0 on every measure")
    print("   hour + year-month FE, SE clustered on month, session 1")
    print("-" * 106 + hdr)
    for lbl, x in (("HHI (mapped firms)", "hhi"),
                   ("top firm share", "top_share"),
                   ("1 / eta (inverse RD elasticity)", "inv_eta"),
                   ("max firm-level Lerner", "max_lerner")):
        row(f"{lbl} -> premium", fit(s1, "premium", [x] + ctrl, x, "hh", "ym", "ym"))

    print("\n" + "-" * 106)
    print("B. ARBITRAGE CAPACITY -> PREMIUM.  Prediction: beta < 0")
    print("-" * 106 + hdr)
    for lbl, x in (("log units trading in intraday", "l_units"),
                   ("intraday volume (MWh)", "id_vol")):
        row(f"{lbl} -> premium", fit(s1, "premium", [x] + ctrl, x, "hh", "ym", "ym"))

    print("\n" + "-" * 106)
    print("C. WEATHER, REDUCED FORM — the shocks that failed on markups, now on")
    print("   an outcome that needs no cost measure")
    print("   heat: beta > 0 (tightens the market).  wind and rain: beta < 0")
    print("   (they are the two flexible arbitrageurs).")
    print("-" * 106 + hdr)
    for lbl, x in (("cooling degree hours", "cdh"),
                   ("heating degree hours", "hdh"),
                   ("wind speed cubed", "wind3"),
                   ("3-day national rainfall", "rain3"),
                   ("extreme-rain day (top decile in month)", "rain_shock"),
                   ("reservoir fill anomaly", "resv")):
        row(f"{lbl} -> premium", fit(s1, "premium", [x, "ldem"], x, "hh", "ym", "ym"))

    print("\n" + "-" * 106)
    print("D. INSTRUMENTED — weather as instruments for the endogenous")
    print("   concentration and arbitrage measures (both respond to the premium)")
    print("-" * 106)
    print(f"\n{'specification':<44}{'beta':>12}{'se':>10}{'t':>7}"
          f"{'F(1st)':>9}{'obs':>10}{'clust':>7}")
    Z = ["cdh", "hdh", "wind3", "rad", "resv"]
    for lbl, x in (("1 / eta", "inv_eta"), ("max firm Lerner", "max_lerner"),
                   ("log intraday units", "l_units")):
        rowiv(f"{lbl} -> premium (2SLS)",
              tsls(s1.assign(unit=1), "premium", x, Z, ["ldem"], "hh", "ym", "ym"))

    print("\nRead: A and B are the identification. C answers whether the weather")
    print("shocks that failed on markups do anything here. A wind result is NOT")
    print("clean — forecast error mimics it exactly; a HEAT result would be.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
