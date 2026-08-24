#!/usr/bin/env python3
"""Does a thermal plant's markup respond to weather-driven demand? A conduct test.

    .venv/bin/python scripts/analysis/heat_demand_conduct.py --rebuild
    .venv/bin/python scripts/analysis/heat_demand_conduct.py

Inputs: data/omie/bids/parquet/, data/jrc_ppdb/implied_marginal_cost_daily.parquet,
data/weather/temperature_population_index.parquet, unit_agents.parquet.
Caches outputs/tables/heat_demand_panel.parquet.

THE TEST

Under competition a firm offers its marginal cost, so its markup is invariant to
demand: `offer - MC` should not move when a heatwave raises load. Under market
power the markup is `q_i / |RD_i'|`, which rises with the firm's own output and
with the steepness of its residual demand — both of which rise with demand. So

    markup_it = b1 * CDH_t + b2 * (CDH_t x size_i) + alpha_i + tau_ym + ...

    competition   =>  b1 = 0 and b2 = 0
    market power  =>  b1 > 0, and b2 > 0 because the markup scales with q_i

`CDH` is cooling degree hours (population-weighted temperature above 18 C) and
`HDH` its heating mirror, entered separately because demand responds
asymmetrically either side of comfort. `size_i` is the firm's share of cleared
generation in **2018-2020**, predetermined relative to every heat event used.

WHY THIS DIRECTION, AFTER FOUR FAILURES ON THE SUPPLY SIDE

Four hydro probes tried to use weather to shift a supply-side state variable
(water value) and read it off offers. All four failed, three with the wrong
sign, and the diagnosis was the same each time: the state variable is also the
firm's own choice variable, so reverse causality was always available, and
weather's effect on the price *level* swamped its effect on anything else.

Demand inverts all three problems. It is not a firm's choice variable. A demand
shifter is the classical instrument for tracing out supply — and since the bid
files *are* the supply functions, the shifter is not needed to recover a curve
but to test whether the curve moves when it should not. And anticipation flips
from a defect to a requirement: bids are submitted at noon on D-1 against a
forecast, so an anticipated temperature shock is exactly the state the firm
conditions on, where an "unexpected rainfall" story needed a surprise it never
had.

MARGINAL COST IS OBSERVED HERE, NOT INFERRED

Restricted to the 68 units in `implied_marginal_cost_daily.parquet` carrying a
**plant-specific** JRC efficiency (`eff_is_generic == False`) — 46 gas, 22 coal.
Marginal cost is `gas/eff + 0.2020 * co2/eff`, daily. Units on a generic
technology-class efficiency are excluded outright: a cogeneration plant's
default 0.23 divides the 2022 gas spike into an implied cost over 1,000 EUR/MWh,
which would dominate any markup regression it entered.

The cost measure is a **bound, not a measurement** — it omits O&M, water,
start-up amortisation and part-load derating, so the markup level is overstated.
That is fine for this test, which is about how the markup *moves*, not its
level: every omitted component is absorbed by the unit fixed effect unless it
correlates with temperature within a month.

THREE THREATS, AND WHICH ONE THIS FILE CAN ADDRESS

1. **Heat is also a supply shock.** It derates gas turbines and binds
   cooling-water limits; Ascó and Vandellós are river-cooled on the Ebro. A heat
   coefficient blends conduct with lost availability. `indisp` (fetched
   separately by `fetch_omie_unavailability.py`) is the control; it is NOT yet
   wired in here, so read `b1` as an upper bound on the conduct response.
2. **Start-up costs.** A competitive firm facing start-up costs also conditions
   its offer on expected demand (Jha & Leslie), so non-invariance alone does not
   prove market power. `cab`'s declared minimum-income condition is the primitive
   that separates them and is likewise not yet wired in.
3. **Composition.** Hot days change which units run. Unit fixed effects handle
   the level; the extensive margin is reported separately as an outcome.

So a positive `b1` here is necessary, not sufficient. A null closes the question
cheaply, which is why it is run first.

THE EVENT STUDY IS NOT OPTIONAL

The spill-window design (2026-08-21) produced a correctly signed interaction
that cleared a wild cluster bootstrap and was still wrong: the event study
showed the entire effect sitting in the arm where the mechanism predicted
nothing. Single coefficients from this family are not to be believed without
one. Heat episodes are defined as runs of days in the top decile of daily mean
CDH **within calendar month**, and coefficients are traced from five days before
onset to ten days after — 135 episodes, 48 of them three days or longer, in all
nine years. Stacking that many episodes is also what makes the design robust to
any single event's coincident confounds: one heatwave shares its gas-price path,
135 do not.
"""

from __future__ import annotations

import argparse
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
from hydro_spill_window_did import demean, ols_cluster, wq  # noqa: E402

PANEL = OUT / "heat_demand_panel.parquet"


def mc_units() -> pd.DataFrame:
    m = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet")
    m = m[~m.eff_is_generic].copy()
    m["date"] = pd.to_datetime(m.date)
    return m[["unit", "date", "marginal_cost_eur_mwh", "fuel", "eff"]]


def build_panel(units: set[str]) -> pd.DataFrame:
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
        t["q"] = t.power_mw * t.resolution_min / 60.0

        off = t[(t.status == "O") & (t.price_eur_mwh > 0)
                & (t.price_eur_mwh < 3000)]
        a = (off.groupby(["date", "unit"])
                .apply(lambda x: pd.Series({
                    "offer_med": wq(x.price_eur_mwh.to_numpy(float),
                                    x.q.to_numpy(float), 0.5),
                    "offer_p25": wq(x.price_eur_mwh.to_numpy(float),
                                    x.q.to_numpy(float), 0.25),
                    "q_off": float(x.q.sum())}), include_groups=False)
                .reset_index())
        acc = t[(t.status == "C") & (t.price_eur_mwh > 0)]
        mrg = (acc.groupby(["date", "unit", "period"]).price_eur_mwh.max()
                  .groupby(level=["date", "unit"]).mean()
                  .rename("marg_acc").reset_index())
        cl = (t[t.status == "C"].groupby(["date", "unit"], as_index=False)
                .q.sum().rename(columns={"q": "q_cl"}))
        out.append(a.merge(mrg, on=["date", "unit"], how="outer")
                    .merge(cl, on=["date", "unit"], how="outer"))
        print(f"  [{i}/{len(files)}] {f.stem}", end="\r", flush=True)
    d = pd.concat(out, ignore_index=True)
    print(f"\n  {len(d):,} unit-days, {d.unit.nunique()} units")
    return d


def weather_daily() -> pd.DataFrame:
    w = pd.read_parquet(DATA / "weather/temperature_population_index.parquet")
    w["date"] = pd.to_datetime(w.utc_timestamp).dt.tz_convert(None).dt.normalize()
    d = (w.groupby("date", as_index=False)
           .agg(cdh=("cdh_es", "mean"), hdh=("hdh_es", "mean"),
                temp=("temp_pop_es", "mean"), tmax=("temp_pop_es", "max")))
    # extremes are defined WITHIN calendar month: a 30 C day is unremarkable in
    # August and a genuine shock in May, and only the second is news to anyone's
    # dispatch plan. Pooling them is what a raw decile would do.
    d["mon"] = d.date.dt.month
    d["cdh_pct"] = d.groupby("mon").cdh.rank(pct=True)
    d["hot"] = (d.cdh_pct >= 0.90).astype(int)
    return d


def firm_size() -> pd.Series:
    """Firm share of cleared generation, 2018-2020 — predetermined."""
    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                         columns=["unit", "firm", "net_cleared_mwh"])
    ua = ua[ua.firm.notna() & (ua.net_cleared_mwh > 0)]
    sh = ua.groupby("firm").net_cleared_mwh.sum()
    return sh / sh.sum()


def fit(d, y, xs, j, fe1="unit", fe2="ym", cl="ym"):
    cols = list(dict.fromkeys([y] + xs + [fe1, fe2, cl]))
    s = d[cols].replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 300:
        return None
    M = demean(s[[y] + xs].to_numpy(float),
               pd.factorize(s[fe1])[0], pd.factorize(s[fe2])[0])
    if M[:, 1 + xs.index(j)].std() < 1e-9:
        return None
    g = pd.factorize(s[cl])[0]
    b, se, _ = ols_cluster(M[:, 0], M[:, 1:], g)
    k = xs.index(j)
    return dict(beta=b[k], se=se[k], t=b[k] / se[k], n=len(s),
                nclust=len(np.unique(g)))


def row(lbl, r, w=48):
    if r is None:
        print(f"{lbl:<{w}}{'insufficient obs':>42}")
        return
    print(f"{lbl:<{w}}{r['beta']:>12.4f}{r['se']:>10.4f}{r['t']:>7.2f}"
          f"{r['n']:>10,}{r['nclust']:>8}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()

    mc = mc_units()
    if args.rebuild or not PANEL.exists():
        print(f"building offer panel for {mc.unit.nunique()} MC-covered units...")
        d = build_panel(set(mc.unit))
        OUT.mkdir(parents=True, exist_ok=True)
        d.to_parquet(PANEL, index=False)
    d = pd.read_parquet(PANEL)
    d["date"] = pd.to_datetime(d.date)
    d = d.merge(mc, on=["unit", "date"], how="inner")

    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                         columns=["unit", "firm"])
    d = d.merge(ua, on="unit", how="left")
    d["size"] = d.firm.map(firm_size())

    w = weather_daily()
    d = d.merge(w, on="date", how="inner")
    sysd = pd.read_parquet(OUT / "residual_demand_slope_full.parquet",
                           columns=["date", "period", "demand", "vre_share"])
    sysd["date"] = pd.to_datetime(sysd.date)
    sysd = sysd.groupby("date", as_index=False).agg(
        demand=("demand", "sum"), vre_share=("vre_share", "mean"))
    d = d.merge(sysd, on="date", how="left")

    d["ym"] = d.date.dt.to_period("M").astype(str)
    # UNCLEARABLE BIDS ARE NOT MARKUPS. 15.2% of unit-days carry a submitted
    # median above 500 EUR/MWh and the 99th percentile sits at the 2,999 price
    # cap: a plant that does not want to run submits a deliberately unclearable
    # bid, and that price expresses an intention, not a cost. Pooling them is
    # what made the levy design's estimates swing from 0.13 to 1.82 depending on
    # where the sample was trimmed (see notes/rq-gas-cap-conduct.md).
    #
    # Two disciplined outcomes instead of one contaminated one:
    #   markup_acc  — the highest-priced step the unit actually CLEARED, minus
    #                 marginal cost. Revealed willingness to run. Primary.
    #   markup_run  — the submitted median, but only on unit-days when the unit
    #                 cleared at all. Conditions on intent to run without
    #                 imposing an arbitrary price threshold.
    # Both winsorised at 1/99 within the estimation sample.
    d["ran"] = (d.q_cl.fillna(0) > 0).astype(float)
    d["markup_raw"] = d.offer_med - d.marginal_cost_eur_mwh
    d["markup_acc"] = d.marg_acc - d.marginal_cost_eur_mwh
    d["markup_run"] = np.where(d.ran > 0, d.markup_raw, np.nan)

    def wins(c):
        lo, hi = d[c].quantile([0.01, 0.99])
        return d[c].clip(lo, hi)
    for c in ("markup_raw", "markup_acc", "markup_run"):
        d[c] = wins(c)
    d["lerner"] = d.markup_acc / d.marg_acc.replace(0, np.nan)
    d["markup"] = d["markup_run"]
    d["cdh_x_size"] = d.cdh * d["size"]
    d["hot_x_size"] = d.hot * d["size"]
    d = d[(d.date >= "2018-01-01") & (d.date <= "2026-05-08")]

    print("=" * 104)
    print("HEAT, DEMAND AND MARKUPS — a conduct test on plant-specific "
          "marginal cost")
    print("=" * 104)
    print(f"  {len(d):,} unit-days, {d.unit.nunique()} units "
          f"({d[d.fuel == 'gas'].unit.nunique()} gas, "
          f"{d[d.fuel == 'coal'].unit.nunique()} coal), "
          f"{d.firm.nunique()} firms, {d.date.nunique():,} days")
    print(f"  markup on marginal ACCEPTED offer: mean "
          f"{d.markup_acc.mean():+.1f}, median {d.markup_acc.median():+.1f} "
          f"EUR/MWh")
    print(f"  dropped as unclearable-intent: "
          f"{(d.offer_med > 500).mean():.1%} of unit-days have a submitted "
          f"median above 500 EUR/MWh")
    print(f"  CDH sd {d.cdh.std():.2f}, hot days {int(d.hot.sum()/max(d.unit.nunique(),1)):,} "
          f"per unit;  firm size {d['size'].min():.3f} to {d['size'].max():.3f}")

    hdr = (f"\n{'specification':<48}{'beta':>12}{'se':>10}{'t':>7}"
           f"{'obs':>10}{'clust':>8}")
    base = ["cdh", "hdh", "vre_share"]

    print("\n" + "-" * 104)
    print("TEST 1 — does the markup move with weather-driven demand at all?")
    print("  unit + year-month FE, SE clustered on month. Competition => beta = 0")
    print("-" * 104 + hdr)
    for lbl, y in (("markup, marginal accepted  <-- primary", "markup_acc"),
                   ("markup, submitted | unit ran", "markup_run"),
                   ("Lerner (markup / accepted offer)", "lerner"),
                   ("markup, submitted ALL (contaminated)", "markup_raw"),
                   ("P(unit clears at all)", "ran")):
        row(f"CDH -> {lbl}", fit(d, y, base, "cdh"))

    print("\n  same, with the EXTREME form (top-decile-within-month hot day)")
    print("  — tail effects do not extrapolate from a linear fit on ordinary days")
    print("-" * 104 + hdr)
    for lbl, y in (("markup, marginal accepted", "markup_acc"),
                   ("markup, submitted | unit ran", "markup_run"),
                   ("P(unit clears at all)", "ran")):
        row(f"hot day -> {lbl}", fit(d, y, ["hot", "hdh", "vre_share"], "hot"))

    print("\n" + "-" * 104)
    print("TEST 2 — does the response scale with firm size, as market power "
          "requires?")
    print("  size = firm share of cleared generation 2018-2020 (predetermined)")
    print("-" * 104 + hdr)
    for lbl, y in (("markup, marginal accepted", "markup_acc"),
                   ("markup, submitted | unit ran", "markup_run")):
        row(f"CDH x size -> {lbl}",
            fit(d, y, ["cdh", "hdh", "vre_share", "cdh_x_size"], "cdh_x_size"))
        row(f"hot x size -> {lbl}",
            fit(d, y, ["hot", "hdh", "vre_share", "hot_x_size"], "hot_x_size"))
    print("\n  clustered on FIRM instead of month (the interaction varies at "
          "firm level)")
    print("-" * 104 + hdr)
    row("CDH x size -> markup_acc [firm-clustered]",
        fit(d, "markup_acc", ["cdh", "hdh", "vre_share", "cdh_x_size"],
            "cdh_x_size", cl="firm"))

    print("\n" + "=" * 104)
    print("EVENT STUDY — 135 stacked heat episodes, k = -5 to +10, k=-1 omitted")
    print("  the diagnostic that killed the spill-window design. Conduct "
          "predicts a step at\n  k=0 that persists while the episode runs; a "
          "pre-trend means something else.")
    print("=" * 104)
    ev = w[["date", "hot"]].sort_values("date").copy()
    ev["onset"] = ((ev.hot == 1) & (ev.hot.shift(1).fillna(0) == 0)).astype(float)
    print(f"  {int(ev.onset.sum())} episode onsets")
    K = list(range(-5, 11))
    for k in K:
        ev[f"K{k}"] = ev.onset.shift(k)
    cols = [f"K{k}" for k in K]
    c = ev[cols].corr().to_numpy()
    iu = np.triu_indices(len(K), 1)
    assert not np.isclose(c[iu], 1.0).any(), "duplicated event-time columns"
    d = d.merge(ev[["date"] + cols], on="date", how="left")
    use = [c_ for c_ in cols if c_ != "K-1"]
    for y, yl in (("markup_acc", "markup, marginal accepted"),
                  ("markup_run", "markup, submitted | unit ran"),
                  ("ran", "P(unit clears at all)")):
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
              f"{b[use.index(f'K{k}')]:>7.2f}" for k in K))
        print("    t:  " + "".join("      ." if k == -1 else
              f"{b[use.index(f'K{k}')] / se[use.index(f'K{k}')]:>7.2f}"
              for k in K))

    print("\nRead: TEST 1 is necessary, not sufficient — heat is also a supply "
          "shock and\nstart-up costs make even a competitive firm condition on "
          "demand. A null closes it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
