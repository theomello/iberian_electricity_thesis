#!/usr/bin/env python3
"""The declared minimum-income condition as an avoidable-cost floor — and as an
outcome in its own right.

    .venv/bin/python scripts/analysis/min_income_conduct.py

Inputs: data/omie/cab/parquet/, outputs/tables/heat_demand_panel.parquet,
implied_marginal_cost_daily.parquet, the weather/net-load instruments.
Prints; writes outputs/tables/min_income_panel.parquet with --save.

WHY

Six conduct tests in this repo have now returned null or wrong-signed estimates,
and the diagnosis in `rq-heat-demand-conduct.md` §8.3 is that the **cost
measure**, not the shock, is the binding constraint. `implied_marginal_cost_daily`
is `gas/eff + 0.2020*co2/eff`: a full-load engineering figure that omits O&M,
part-load derating and above all **start-up costs**. On it, 73% of periods look
"in the money" and the median unit-day shows a 100% withholding rate — a measure
that fires almost always and separates nothing.

`cab` publishes the missing primitive. Per unit per day, a firm states what it
needs to earn to run: a fixed term in EUR/day and a variable term in EUR/MWh.
Jha & Leslie build a dynamic competitive benchmark specifically to *estimate*
start-up costs, and show static markups overstate market power when they are
ignored. Reguant (2014) models the optimal declaration of this same condition in
order to identify them structurally. Here it is published.

TWO USES, AND THEY ARE DIFFERENT CLAIMS

**1. As an avoidable-cost floor (a bound, not a measurement).** A firm that
declares it needs `fixed + variable * q` will not accept less, so its avoidable
cost is *at most* that, and

    AC(q)  =  variable  +  fixed / q

is the per-MWh threshold the firm itself says it needs at output q. Evaluating
at the unit's **full-day capacity** `q_max = max_power_mw * 24` gives the most
favourable threshold the unit could ever face, so a unit whose price is below
`AC(q_max)` cannot possibly have met its own declared requirement — it is
genuinely uneconomic, not withholding. That is exactly the exclusion the implied
marginal cost could not make.

**2. As an outcome.** The declaration is a *strategic choice* — that is why
Reguant models it. So it can be tested directly: does a firm raise its declared
minimum income when it expects a tight market? That question needs no cost model
at all, because the object being explained is the firm's own stated requirement,
not a markup over an estimated cost. If conduct responds to scarcity anywhere in
this market, it should be visible here.

THE SAMPLE IS SMALL, NON-RANDOM, AND TIME-LIMITED — ALL THREE MATTER

* Only units that **declare** a condition appear. On 2024-01-15 that is 53 units,
  48 of them combined cycle — the marginal technology, but a narrow slice.
* The condition binds on **daily** revenue, not per period.
* Declaring units are precisely those with binding start-up costs, so the sample
  is selected on the variable of interest.
* The variable term is published only to **2025-03-18** — `cab` switched to a
  94-character layout on 2025-03-19 that carries two numerics where the old one
  carried nine. Everything here therefore runs 2018-01-01 to 2025-03-18.

VALIDATION FIRST

Before either use, the declared variable term is compared against the
independently constructed `gas/eff + carbon` marginal cost for the same
unit-days. These are built from entirely different sources — a firm's own
declaration versus JRC efficiency times MIBGAS times EUA — so agreement is a
genuine cross-validation of both, and disagreement locates which one to distrust.
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
from net_load_iv import instruments, net_load_daily, tsls  # noqa: E402

MIC_END = pd.Timestamp("2025-03-18")   # cab layout change on the 19th


def load_mic() -> pd.DataFrame:
    fs = sorted(glob.glob(str(DATA / "omie/cab/parquet/cab_*.parquet")))
    keep = ["date", "unit", "side", "min_income_fixed_eur",
            "min_income_var_eur_mwh", "max_power_mw"]
    d = pd.concat([pd.read_parquet(f, columns=keep) for f in fs],
                  ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    d = d[(d.side == "V") & (d.date <= MIC_END)]
    d = d.rename(columns={"min_income_fixed_eur": "mic_fixed",
                          "min_income_var_eur_mwh": "mic_var"})
    d["declares"] = ((d.mic_fixed.fillna(0) > 0)
                     | (d.mic_var.fillna(0) > 0)).astype(float)
    return d.drop_duplicates(subset=["date", "unit"])


def fit(d, y, xs, j, fe1="unit", fe2="ym", cl="ym"):
    cols = list(dict.fromkeys([y] + xs + [fe1, fe2, cl]))
    s = d[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 200:
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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    mic = load_mic()
    dec = mic[mic.declares > 0]
    print("=" * 106)
    print("THE DECLARED MINIMUM-INCOME CONDITION")
    print("=" * 106)
    print(f"  {len(mic):,} sell-side unit-days to {MIC_END.date()}; "
          f"{len(dec):,} declare a condition ({len(dec)/len(mic):.1%})")
    print(f"  declaring units: {dec.unit.nunique():,}  |  "
          f"fixed term: median {dec.mic_fixed.median():,.0f} EUR/day, "
          f"p90 {dec.mic_fixed.quantile(.9):,.0f}")
    print(f"  variable term: median {dec.mic_var.median():.1f} EUR/MWh, "
          f"p10 {dec.mic_var.quantile(.1):.1f}, p90 {dec.mic_var.quantile(.9):.1f}")

    # ---------------- validation against the engineering cost ----------------
    imc = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet")
    imc = imc[~imc.eff_is_generic].copy()
    imc["date"] = pd.to_datetime(imc.date)
    v = dec.merge(imc[["unit", "date", "marginal_cost_eur_mwh", "fuel"]],
                  on=["unit", "date"], how="inner")
    v = v[(v.mic_var > 0) & (v.marginal_cost_eur_mwh > 0)]
    print("\n" + "-" * 106)
    print("VALIDATION — declared variable term vs independently built "
          "gas/eff + carbon")
    print("-" * 106)
    print(f"  {len(v):,} unit-days on {v.unit.nunique()} units overlap")
    if len(v) > 100:
        print(f"  corr(declared variable, implied MC)       "
              f"{v.mic_var.corr(v.marginal_cost_eur_mwh):+.3f}")
        print(f"  corr in logs                              "
              f"{np.log(v.mic_var).corr(np.log(v.marginal_cost_eur_mwh)):+.3f}")
        r = v.mic_var / v.marginal_cost_eur_mwh
        print(f"  ratio declared/implied: median {r.median():.2f}, "
              f"p25 {r.quantile(.25):.2f}, p75 {r.quantile(.75):.2f}")
        print("  (a ratio near 1 means the two sources agree on fuel cost; "
              "above 1 means\n   the declaration carries more than fuel — "
              "which is what it is meant to)")

    # ---------------- the avoidable-cost floor ----------------
    mk = pd.read_parquet(OUT / "heat_demand_panel.parquet")
    mk["date"] = pd.to_datetime(mk.date)
    d = dec.merge(mk, on=["date", "unit"], how="inner")
    d = d.merge(imc[["unit", "date", "marginal_cost_eur_mwh"]],
                on=["unit", "date"], how="left")
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "price_es"])
    px["date"] = pd.to_datetime(px.date)
    pxd = px.groupby("date", as_index=False).agg(p_mean=("price_es", "mean"),
                                                 p_max=("price_es", "max"))
    d = d.merge(pxd, on="date", how="left")

    # AC at FULL-DAY capacity: the most favourable threshold the unit can face.
    # A price below this cannot meet the unit's own declared requirement at ANY
    # output, so failing it is genuine unprofitability, not withholding.
    d["q_max"] = d.max_power_mw * 24.0
    d = d[d.q_max > 0]
    d["ac_best"] = d.mic_var + d.mic_fixed / d.q_max
    d["ran"] = (d.q_cl.fillna(0) > 0).astype(float)
    d["itm_mic"] = (d.ac_best < d.p_max).astype(float)
    d["itm_mc"] = (d.marginal_cost_eur_mwh < d.p_max).astype(float)
    d["wh_mic"] = np.where(d.itm_mic > 0, (d.ran == 0).astype(float), np.nan)
    d["wh_mc"] = np.where(d.itm_mc > 0, (d.ran == 0).astype(float), np.nan)
    # declared-lower-bound markup: price minus the firm's OWN stated requirement
    d["markup_mic"] = d.marg_acc - d.ac_best
    lo, hi = d.markup_mic.quantile([0.01, 0.99])
    d["markup_mic"] = d.markup_mic.clip(lo, hi)

    print("\n" + "-" * 106)
    print("WHAT THE FLOOR CHANGES — the same units, two cost measures")
    print("-" * 106)
    print(f"  {len(d):,} unit-days, {d.unit.nunique()} declaring units, "
          f"{d.date.nunique():,} days")
    print(f"  AC at full-day capacity: median {d.ac_best.median():.1f} EUR/MWh "
          f"vs implied MC median {d.marginal_cost_eur_mwh.median():.1f}")
    print(f"  fixed term adds {(d.mic_fixed / d.q_max).median():.2f} EUR/MWh "
          f"at full output — the start-up component the engineering cost omits")
    print(f"  in the money on implied MC:     {d.itm_mc.mean():.1%}")
    print(f"  in the money on declared floor: {d.itm_mic.mean():.1%}   "
          f"<- the exclusion the MC could not make")
    print(f"  withholding rate | ITM on MC:      {d.wh_mc.mean():.1%}")
    print(f"  withholding rate | ITM on floor:   {d.wh_mic.mean():.1%}")

    # ---------------- the tests ----------------
    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                         columns=["unit", "firm"])
    d = d.merge(ua, on="unit", how="left")
    d["size"] = d.firm.map(firm_size())
    d = d.merge(weather_daily(), on="date", how="inner")
    d = d.merge(net_load_daily(), on="date", how="inner")
    d = d.merge(instruments(), on="date", how="inner", suffixes=("", "_i"))
    d["ym"] = d.date.dt.to_period("M").astype(str)
    d["cdh_x_size"] = d.cdh * d["size"]
    sysd = pd.read_parquet(OUT / "residual_demand_slope_full.parquet",
                           columns=["date", "vre_share"])
    sysd["date"] = pd.to_datetime(sysd.date)
    d = d.merge(sysd.groupby("date", as_index=False).vre_share.mean(),
                on="date", how="left")

    hdr = (f"\n{'specification':<48}{'beta':>12}{'se':>10}{'t':>7}"
           f"{'obs':>10}{'clust':>8}")
    base = ["cdh", "hdh", "vre_share"]

    print("\n" + "=" * 106)
    print("TEST A — withholding, now measured against the DECLARED floor")
    print("=" * 106 + hdr)
    for lbl, y in (("vs implied MC (old measure)", "wh_mc"),
                   ("vs declared floor (new)", "wh_mic")):
        row(f"CDH -> withholding {lbl}", fit(d, y, base, "cdh"))
    row("CDH x size -> withholding vs declared floor",
        fit(d, "wh_mic", base + ["cdh_x_size"], "cdh_x_size"))

    print("\n" + "=" * 106)
    print("TEST B — the DECLARATION ITSELF as the outcome (Reguant 2014's object)")
    print("  no cost model needed: this explains the firm's own stated "
          "requirement.\n  Market power predicts a firm raises it when the "
          "market is tight.")
    print("=" * 106 + hdr)
    d["l_ac"] = np.log(d.ac_best.clip(lower=0.01))
    d["l_fixed"] = np.log(d.mic_fixed.clip(lower=1.0))
    for lbl, y in (("log AC at capacity", "l_ac"),
                   ("log fixed term (EUR/day)", "l_fixed"),
                   ("variable term (EUR/MWh)", "mic_var")):
        row(f"CDH -> {lbl}", fit(d, y, base, "cdh"))
        row(f"hot day -> {lbl}", fit(d, y, ["hot", "hdh", "vre_share"], "hot"))
    row("CDH x size -> log AC at capacity",
        fit(d, "l_ac", base + ["cdh_x_size"], "cdh_x_size"))

    print("\n" + "=" * 106)
    print("TEST C — the same, instrumented: net load, all five instruments")
    print("=" * 106)
    print(f"\n{'specification':<44}{'beta':>12}{'se':>10}{'t':>7}"
          f"{'F(1st)':>9}{'obs':>10}{'clust':>7}")
    ALL = ["cdh", "hdh", "wind3", "rad", "resv"]
    for lbl, y in (("log AC at capacity", "l_ac"),
                   ("log fixed term", "l_fixed"),
                   ("variable term", "mic_var"),
                   ("markup over declared floor", "markup_mic"),
                   ("withholding vs declared floor", "wh_mic")):
        rowiv(f"net load -> {lbl}",
              tsls(d, y, "net_load", ALL, [], "unit", "ym", "ym"))

    if args.save:
        d.to_parquet(OUT / "min_income_panel.parquet", index=False)
        print(f"\nwrote {OUT / 'min_income_panel.parquet'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
