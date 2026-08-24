#!/usr/bin/env python3
"""In-the-money withholding, measured period by period instead of per day.

    .venv/bin/python scripts/analysis/withholding_period_level.py --rebuild
    .venv/bin/python scripts/analysis/withholding_period_level.py

Caches outputs/tables/withholding_period_panel.parquet.

WHY THE DAILY VERSION WAS VACUOUS

`withholding_extensive_margin.py` compared each unit's daily marginal cost with
the day's *maximum* clearing price and called the unit in the money if the cost
was lower. On that definition **85.9% of unit-days are in the money and 73.7% of
those clear nothing** — a measure that fires almost always and therefore
separates almost nothing. The reason is structural, not a coding error: a
mid-merit CCGT is in the money for a handful of hours on a typical day, and
start-up costs and minimum run times make starting for those hours unprofitable.
Daily "should have run" is the wrong object.

WHAT THIS MEASURES INSTEAD

Period by period, for each unit-period:

    itm       = MC_it < p*_t                (cost below THAT period's price)
    cleared   = the unit cleared > 0 MW in that period
    offered   = the unit submitted any sell step in that period

and then, aggregated back to unit-day as **fractions of the unit's own
in-the-money periods** (fractions, not counts, because the 15-minute switch on
2025-10-01 quadruples the period count and would otherwise quadruple every
count-based measure):

    wh_rate       share of in-the-money periods the unit cleared nothing in
    wh_absent     ... of which it submitted no offer at all   (physical)
    wh_priced     ... of which it offered, but above the price (economic)

**The absent/priced split is the point.** `curva_pbc_uof` cannot tell withheld
from unavailable, but it can tell *not offered* from *offered too dear*, and
those are different actions with different interpretations. A unit that offers
its whole capacity at 180 EUR/MWh when the price is 90 has made a pricing
decision that is visible; a unit that does not appear has not.

Declared outages are netted out from `indisp` exactly as in the daily version.

THE TEST, UNCHANGED

Same framework: shock defined within calendar month, firm size predetermined on
2018-2020 generation share, unit and year-month fixed effects, stacked event
study over heat-episode onsets. Market power predicts withholding rises with
demand and rises more for large firms.

WHAT STILL WILL NOT BE SETTLED

Start-up costs and minimum run times are not observed here, and they are the
main innocent explanation for an in-the-money period with no output. `cab`'s
declared minimum-income condition is the primitive that would bound them and is
not wired in. So a positive result would still not be proof; a null is
informative because it says the sharper measure does not rescue the daily one.
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs" / "tables"
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from hydro_spill_window_did import demean, ols_cluster  # noqa: E402
from heat_demand_conduct import firm_size, weather_daily  # noqa: E402
from withholding_extensive_margin import unavailable_days  # noqa: E402

PANEL = OUT / "withholding_period_panel.parquet"


def build(units: set[str], mc: pd.DataFrame) -> pd.DataFrame:
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "price_es", "price_pt"])
    px["date"] = pd.to_datetime(px.date)
    px["split"] = px.price_es != px.price_pt

    out = []
    files = sorted((DATA / "omie/bids/parquet").glob("bids_*.parquet"))
    for i, f in enumerate(files, 1):
        t = ds.dataset(f).to_table(
            filter=(pc.field("side") == "V"),
            columns=["date", "period", "unit", "price_eur_mwh", "power_mw",
                     "resolution_min", "status"]).to_pandas()
        t = t[t.unit.isin(units)]
        if t.empty:
            continue
        t["date"] = pd.to_datetime(t.date)

        # per unit-period: did it offer, at what minimum price, did it clear
        o = (t[t.status == "O"].groupby(["date", "period", "unit"], as_index=False)
               .price_eur_mwh.min().rename(columns={"price_eur_mwh": "min_offer"}))
        c = (t[t.status == "C"].groupby(["date", "period", "unit"], as_index=False)
               .power_mw.sum().rename(columns={"power_mw": "q"}))
        up = o.merge(c, on=["date", "period", "unit"], how="outer")
        up = up.merge(px, on=["date", "period"], how="inner")
        up = up.merge(mc, on=["date", "unit"], how="inner")
        up = up[~up.split]
        if up.empty:
            continue

        up["itm"] = (up.marginal_cost_eur_mwh < up.price_es).astype(float)
        up["offered"] = up.min_offer.notna().astype(float)
        up["cleared"] = (up.q.fillna(0) > 0).astype(float)
        s = up[up.itm > 0]
        g = (s.groupby(["date", "unit"], as_index=False)
               .agg(n_itm=("itm", "size"),
                    n_notcleared=("cleared", lambda x: float((x == 0).sum())),
                    n_absent=("offered", lambda x: float((x == 0).sum())),
                    n_offered=("offered", "sum")))
        # of the in-the-money periods with no output, how many had an offer
        # sitting above the price (economic) versus no offer at all (physical)
        s2 = s[s.cleared == 0]
        g2 = (s2.groupby(["date", "unit"], as_index=False)
                .agg(nc_absent=("offered", lambda x: float((x == 0).sum())),
                     nc_priced=("offered", "sum")))
        tot = (up.groupby(["date", "unit"], as_index=False)
                 .agg(n_periods=("itm", "size"), n_itm_all=("itm", "sum")))
        out.append(g.merge(g2, on=["date", "unit"], how="left")
                    .merge(tot, on=["date", "unit"], how="left"))
        print(f"  [{i}/{len(files)}] {f.stem}", end="\r", flush=True)

    d = pd.concat(out, ignore_index=True)
    print(f"\n  {len(d):,} unit-days with at least one in-the-money period")
    return d


def fit(d, y, xs, j, fe1="unit", fe2="ym", cl="ym", weights=None):
    cols = list(dict.fromkeys([y] + xs + [fe1, fe2, cl]
                              + ([weights] if weights else [])))
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


def row(lbl, r, w=52):
    if r is None:
        print(f"{lbl:<{w}}{'insufficient obs':>40}")
        return
    print(f"{lbl:<{w}}{r['beta']:>12.4f}{r['se']:>10.4f}{r['t']:>7.2f}"
          f"{r['n']:>10,}{r['nclust']:>8}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--min-itm", type=int, default=4,
                    help="require at least this many in-the-money periods")
    args = ap.parse_args()

    mc = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet")
    mc = mc[~mc.eff_is_generic].copy()
    mc["date"] = pd.to_datetime(mc.date)
    mc = mc[["unit", "date", "marginal_cost_eur_mwh", "fuel"]]

    if args.rebuild or not PANEL.exists():
        print(f"building period-level panel for {mc.unit.nunique()} units...")
        d = build(set(mc.unit), mc)
        OUT.mkdir(parents=True, exist_ok=True)
        d.to_parquet(PANEL, index=False)
    d = pd.read_parquet(PANEL)
    d["date"] = pd.to_datetime(d.date)

    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                         columns=["unit", "firm"])
    d = d.merge(ua, on="unit", how="left")
    d["size"] = d.firm.map(firm_size())
    d = d.merge(unavailable_days(set(d.unit)), on=["unit", "date"], how="left")
    d["declared_out"] = d.declared_out.fillna(0.0)
    d = d.merge(weather_daily(), on="date", how="inner")
    sysd = pd.read_parquet(OUT / "residual_demand_slope_full.parquet",
                           columns=["date", "vre_share"])
    sysd["date"] = pd.to_datetime(sysd.date)
    d = d.merge(sysd.groupby("date", as_index=False).vre_share.mean(),
                on="date", how="left")
    d["ym"] = d.date.dt.to_period("M").astype(str)
    d = d[(d.date >= "2018-01-01") & (d.date <= "2026-05-08")]
    d = d[d.n_itm >= args.min_itm]

    # PHYSICAL ABSENCE CANNOT BE MEASURED FROM BID ROWS. A unit that submits no
    # offer at all has no row in curva_pbc_uof, so a panel built by grouping bid
    # rows contains only unit-periods where the unit was present — which made the
    # first cut report "physical withholding: 0.0%", an artefact of construction
    # rather than a fact about the market.
    #
    # The denominator has to come from the price grid instead: for each unit-day,
    # count ALL periods whose clearing price exceeded that unit's marginal cost,
    # whether or not the unit showed up. The difference against the in-the-money
    # periods it did appear in is the absent count.
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "price_es", "price_pt"])
    px["date"] = pd.to_datetime(px.date)
    px = px[px.price_es == px.price_pt]              # same non-split filter
    mcd = mc[["unit", "date", "marginal_cost_eur_mwh"]]
    grid = (px.merge(mcd, on="date", how="inner"))
    grid["itm"] = (grid.marginal_cost_eur_mwh < grid.price_es).astype(float)
    gt = (grid.groupby(["date", "unit"], as_index=False)
              .agg(n_itm_grid=("itm", "sum"), n_per_grid=("itm", "size")))
    d = d.merge(gt, on=["date", "unit"], how="left")

    d["itm_share"] = d.n_itm_grid / d.n_per_grid
    # absent = in-the-money periods the unit never appeared in
    d["n_absent_itm"] = (d.n_itm_grid - d.n_itm).clip(lower=0)
    d["wh_rate"] = ((d.n_notcleared + d.n_absent_itm)
                    / d.n_itm_grid.replace(0, np.nan))
    d["wh_absent"] = d.n_absent_itm / d.n_itm_grid.replace(0, np.nan)
    d["wh_priced"] = d.n_notcleared / d.n_itm_grid.replace(0, np.nan)
    av = d[d.declared_out == 0].copy()
    d["cdh_x_size"] = d.cdh * d["size"]
    av["cdh_x_size"] = av.cdh * av["size"]

    print("=" * 106)
    print("IN-THE-MONEY WITHHOLDING, PERIOD-LEVEL "
          f"(unit-days with >= {args.min_itm} in-the-money periods)")
    print("=" * 106)
    print(f"  {len(d):,} unit-days, {d.unit.nunique()} units, "
          f"{d.firm.nunique()} firms, {d.date.nunique():,} days")
    print(f"  share of a day's periods that are in the money: "
          f"mean {d.itm_share.mean():.1%}   "
          f"(the DAILY measure said 85.9% of unit-days)")
    print(f"  in-the-money periods per unit-day: median "
          f"{d.n_itm_grid.median():.0f} of {d.n_per_grid.median():.0f}")
    print(f"  withholding rate (ITM periods with no output): "
          f"mean {d.wh_rate.mean():.1%}, median {d.wh_rate.median():.1%}")
    print(f"    of which no offer submitted at all (physical): "
          f"{d.wh_absent.mean():.1%}")
    print(f"    of which offered above the price (economic):   "
          f"{d.wh_priced.mean():.1%}")
    print(f"  declared outage on {d.declared_out.mean():.1%} of unit-days")

    hdr = (f"\n{'specification':<52}{'beta':>12}{'se':>10}{'t':>7}"
           f"{'obs':>10}{'clust':>8}")
    base = ["cdh", "hdh", "vre_share"]

    print("\n" + "-" * 106)
    print("TEST — does period-level withholding rise with weather-driven demand?")
    print("  unit + year-month FE, SE clustered on month. Market power => beta > 0")
    print("-" * 106 + hdr)
    for lbl, y in (("withholding rate", "wh_rate"),
                   ("  ... physical (no offer)", "wh_absent"),
                   ("  ... economic (offered above price)", "wh_priced")):
        row(f"CDH -> {lbl}", fit(av, y, base, "cdh"))
    print()
    for lbl, y in (("withholding rate", "wh_rate"),
                   ("  ... economic (offered above price)", "wh_priced")):
        row(f"hot day -> {lbl}", fit(av, y, ["hot", "hdh", "vre_share"], "hot"))

    print("\n" + "-" * 106)
    print("SIZE INTERACTION — market power requires beta > 0")
    print("-" * 106 + hdr)
    for lbl, y in (("withholding rate", "wh_rate"),
                   ("economic withholding", "wh_priced")):
        row(f"CDH x size -> {lbl}",
            fit(av, y, base + ["cdh_x_size"], "cdh_x_size"))
        row(f"CDH x size -> {lbl} [firm-clustered]",
            fit(av, y, base + ["cdh_x_size"], "cdh_x_size", cl="firm"))

    print("\n" + "=" * 106)
    print("EVENT STUDY — stacked heat-episode onsets, k=-5..+10, k=-1 omitted")
    print("=" * 106)
    w = weather_daily()[["date", "hot"]].sort_values("date").copy()
    w["onset"] = ((w.hot == 1) & (w.hot.shift(1).fillna(0) == 0)).astype(float)
    K = list(range(-5, 11))
    for k in K:
        w[f"K{k}"] = w.onset.shift(k)
    cols = [f"K{k}" for k in K]
    c = w[cols].corr().to_numpy()
    iu = np.triu_indices(len(K), 1)
    assert not np.isclose(c[iu], 1.0).any(), "duplicated event-time columns"
    av = av.merge(w[["date"] + cols], on="date", how="left")
    use = [c_ for c_ in cols if c_ != "K-1"]
    for y, yl in (("wh_rate", "withholding rate"),
                  ("wh_priced", "economic withholding")):
        s = av[[y] + use + ["hdh", "vre_share", "unit", "ym"]] \
                .replace([np.inf, -np.inf], np.nan).dropna()
        if len(s) < 300:
            continue
        M = demean(s[[y] + use + ["hdh", "vre_share"]].to_numpy(float),
                   pd.factorize(s.unit)[0], pd.factorize(s.ym)[0])
        b, se, _ = ols_cluster(M[:, 0], M[:, 1:], pd.factorize(s.ym)[0])
        print(f"\n  {yl}   n={len(s):,}")
        print("    k:  " + "".join(f"{k:>7}" for k in K))
        print("    b:  " + "".join("      ." if k == -1 else
              f"{b[use.index(f'K{k}')]:>7.3f}" for k in K))
        print("    t:  " + "".join("      ." if k == -1 else
              f"{b[use.index(f'K{k}')] / se[use.index(f'K{k}')]:>7.2f}"
              for k in K))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
