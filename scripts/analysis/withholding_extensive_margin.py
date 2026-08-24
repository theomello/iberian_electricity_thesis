#!/usr/bin/env python3
"""In-the-money withholding: the extensive-margin conduct test.

    .venv/bin/python scripts/analysis/withholding_extensive_margin.py

Inputs: outputs/tables/heat_demand_panel.parquet (built by
heat_demand_conduct.py --rebuild), implied_marginal_cost_daily.parquet,
data/omie/indisp/parquet/, prices, unit_agents. Prints; writes nothing.

WHY THE EXTENSIVE MARGIN IS THE BETTER PLACE TO LOOK

`heat_demand_conduct.py` found nothing on the price margin: a thermal unit's
markup over its own plant-specific marginal cost does not move with weather-
driven demand, and the size interaction that market power requires to be
positive is negative in every specification. The one robust response to heat was
that units **clear more often** — which reads as merit order, not conduct.

But that reading is too quick, because **withholding is an extensive-margin
decision**. A firm exercising market power need not raise its offer price at
all: it can withdraw capacity outright, or price a tranche above the clearing
price. Both appear in the data the same way — the unit did not clear. The whole
capacity-withholding literature (Wolfram; Borenstein, Bushnell & Wolak) looks
here rather than at the markup, and this repo has never tested it.

THE OUTCOME

Not "did the unit clear" — that is mechanical, and rises with demand for
uninteresting reasons. The object is **in-the-money non-clearing**:

    itm_it       = 1 if the unit's marginal cost that day was below the price
                   it could have cleared at
    withheld_it  = 1 if itm_it and the unit cleared NOTHING that day
                   and no outage was declared for it

A unit that is in the money and does not run is either withholding, or
constrained. `indisp` is what separates the two, and it is the reason that
dataset was fetched: 55 of these 68 marginal-cost units carry declared outage
records, so declared unavailability can be netted out rather than assumed away.

Two thresholds are reported because the daily resolution forces a choice.
`itm_max` uses the day's **highest** clearing price — the unit could have run in
at least one period — and is the permissive definition. `itm_mean` uses the
day's mean and is the strict one. A withholding result that appears under only
one of them is a threshold artefact, not a finding.

THE TEST

    withheld_it = b1*Shock_t + b2*(Shock_t x size_i) + alpha_i + tau_ym + ...

with the same framework as the price-margin test: shock defined within calendar
month, size predetermined on 2018-2020 generation share, unit and year-month
fixed effects, and a stacked event study over heat-episode onsets as the
mandatory diagnostic.

Market power predicts b1 > 0 and b2 > 0 — withholding rises when demand is
tight, and more so for firms large enough for it to pay.

WHAT A POSITIVE RESULT WOULD AND WOULD NOT MEAN

Would not: prove withholding. Three innocent explanations survive —
undeclared outages (declaration is not universal), start-up costs and minimum
run times (a unit in the money for two hours may still not be worth starting),
and the daily aggregation itself, which counts a unit that ran in no period the
same whether it was in the money for one hour or twenty-four.

Would: locate the effect the price margin could not find, and tell us the
question is worth the period-level build that would settle it.
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs" / "tables"
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from hydro_spill_window_did import demean, ols_cluster  # noqa: E402
from heat_demand_conduct import firm_size, weather_daily  # noqa: E402


def unavailable_days(units: set[str]) -> pd.DataFrame:
    """Unit-days with a declared outage, expanded from indisp intervals.

    A record is counted only where the declared remaining capacity is zero:
    partial deratings mean the unit could still have offered something, so
    treating them as full unavailability would absolve real withholding.
    """
    fs = sorted(glob.glob(str(DATA / "omie/indisp/parquet/indisp_*.parquet")))
    d = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    d = d[d.unit.isin(units) & (d.available_mw <= 0.0)]
    d = d.drop_duplicates(subset=["unit", "start", "end"])
    rows = []
    for u, s, e in zip(d.unit, d.start, d.end):
        if pd.isna(s) or pd.isna(e) or e < s:
            continue
        span = (e - s).days
        if span > 400:                      # guard against open-ended records
            continue
        for day in pd.date_range(s.normalize(), e.normalize(), freq="D"):
            rows.append((u, day))
    out = pd.DataFrame(rows, columns=["unit", "date"]).drop_duplicates()
    out["declared_out"] = 1.0
    return out


def fit(d, y, xs, j, fe1="unit", fe2="ym", cl="ym"):
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


def row(lbl, r, w=50):
    if r is None:
        print(f"{lbl:<{w}}{'insufficient obs':>40}")
        return
    print(f"{lbl:<{w}}{r['beta']:>12.4f}{r['se']:>10.4f}{r['t']:>7.2f}"
          f"{r['n']:>10,}{r['nclust']:>8}")


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()

    d = pd.read_parquet(OUT / "heat_demand_panel.parquet")
    d["date"] = pd.to_datetime(d.date)
    mc = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet")
    mc = mc[~mc.eff_is_generic].copy()
    mc["date"] = pd.to_datetime(mc.date)
    d = d.merge(mc[["unit", "date", "marginal_cost_eur_mwh", "fuel"]],
                on=["unit", "date"], how="inner")

    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "price_es"])
    px["date"] = pd.to_datetime(px.date)
    pxd = px.groupby("date", as_index=False).agg(
        p_mean=("price_es", "mean"), p_max=("price_es", "max"))
    d = d.merge(pxd, on="date", how="left")

    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                         columns=["unit", "firm"])
    d = d.merge(ua, on="unit", how="left")
    d["size"] = d.firm.map(firm_size())

    units = set(d.unit)
    ud = unavailable_days(units)
    d = d.merge(ud, on=["unit", "date"], how="left")
    d["declared_out"] = d.declared_out.fillna(0.0)

    d = d.merge(weather_daily(), on="date", how="inner")
    sysd = pd.read_parquet(OUT / "residual_demand_slope_full.parquet",
                           columns=["date", "vre_share"])
    sysd["date"] = pd.to_datetime(sysd.date)
    d = d.merge(sysd.groupby("date", as_index=False).vre_share.mean(),
                on="date", how="left")
    d["ym"] = d.date.dt.to_period("M").astype(str)
    d = d[(d.date >= "2018-01-01") & (d.date <= "2026-05-08")]

    d["ran"] = (d.q_cl.fillna(0) > 0).astype(float)
    d["itm_max"] = (d.marginal_cost_eur_mwh < d.p_max).astype(float)
    d["itm_mean"] = (d.marginal_cost_eur_mwh < d.p_mean).astype(float)
    for tag in ("max", "mean"):
        d[f"wh_{tag}"] = np.where(
            d[f"itm_{tag}"] > 0, (d.ran == 0).astype(float), np.nan)
        d[f"wh_{tag}_av"] = np.where(
            (d[f"itm_{tag}"] > 0) & (d.declared_out == 0),
            (d.ran == 0).astype(float), np.nan)
    d["cdh_x_size"] = d.cdh * d["size"]
    d["hot_x_size"] = d.hot * d["size"]

    print("=" * 106)
    print("IN-THE-MONEY WITHHOLDING — the extensive-margin conduct test")
    print("=" * 106)
    print(f"  {len(d):,} unit-days, {d.unit.nunique()} units, "
          f"{d.firm.nunique()} firms, {d.date.nunique():,} days")
    print(f"  declared outage (indisp, zero remaining capacity): "
          f"{d.declared_out.mean():.1%} of unit-days")
    print(f"  in the money on the day's MAX price:  {d.itm_max.mean():.1%};  "
          f"on the MEAN price: {d.itm_mean.mean():.1%}")
    for tag, lbl in (("max", "permissive"), ("mean", "strict")):
        s = d[d[f"itm_{tag}"] > 0]
        print(f"  [{lbl}] of in-the-money unit-days, cleared nothing: "
              f"{(s.ran == 0).mean():.1%}  |  and no declared outage: "
              f"{d[f'wh_{tag}_av'].mean():.1%}")

    hdr = (f"\n{'specification':<50}{'beta':>12}{'se':>10}{'t':>7}"
           f"{'obs':>10}{'clust':>8}")
    base = ["cdh", "hdh", "vre_share"]

    print("\n" + "-" * 106)
    print("TEST — does in-the-money withholding rise with weather-driven demand?")
    print("  unit + year-month FE, SE clustered on month. Market power => beta > 0")
    print("-" * 106 + hdr)
    for lbl, y in (("withheld | ITM at day max price", "wh_max"),
                   ("  ... and no declared outage", "wh_max_av"),
                   ("withheld | ITM at day mean price", "wh_mean"),
                   ("  ... and no declared outage", "wh_mean_av")):
        row(f"CDH -> {lbl}", fit(d, y, base, "cdh"))
    print()
    for lbl, y in (("withheld | ITM at day max, available", "wh_max_av"),
                   ("withheld | ITM at day mean, available", "wh_mean_av")):
        row(f"hot day -> {lbl}", fit(d, y, ["hot", "hdh", "vre_share"], "hot"))

    print("\n" + "-" * 106)
    print("SIZE INTERACTION — market power requires beta > 0")
    print("-" * 106 + hdr)
    for lbl, y in (("withheld | ITM max, available", "wh_max_av"),
                   ("withheld | ITM mean, available", "wh_mean_av")):
        row(f"CDH x size -> {lbl}",
            fit(d, y, base + ["cdh_x_size"], "cdh_x_size"))
        row(f"CDH x size -> {lbl} [firm-clustered]",
            fit(d, y, base + ["cdh_x_size"], "cdh_x_size", cl="firm"))

    print("\n" + "-" * 106)
    print("PLACEBO — the same regression on DECLARED OUTAGE itself.")
    print("  A real outage is a physical event and should NOT respond to demand.")
    print("  If it does, either outages are being declared strategically or the")
    print("  shock is picking up something mechanical — either way the main")
    print("  result cannot be read as conduct.")
    print("-" * 106 + hdr)
    row("CDH -> declared outage", fit(d, "declared_out", base, "cdh"))
    row("hot day -> declared outage",
        fit(d, "declared_out", ["hot", "hdh", "vre_share"], "hot"))

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
    d = d.merge(w[["date"] + cols], on="date", how="left")
    use = [c_ for c_ in cols if c_ != "K-1"]
    for y, yl in (("wh_max_av", "withheld | ITM max, available"),
                  ("wh_mean_av", "withheld | ITM mean, available")):
        s = d[[y] + use + ["hdh", "vre_share", "unit", "ym"]] \
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
