#!/usr/bin/env python3
"""Do net-buyer firms actually offer below marginal cost? A test, and a null.

    .venv/bin/python scripts/analysis/markdown_contract_test.py
    .venv/bin/python scripts/analysis/markdown_contract_test.py --save

THE PREDICTION

With contract position theta and auction sales q, the first-order condition is

    p - MC = (q - theta) * |dp/dq|

so a firm that has sold MORE forward than it generates (q < theta) is a net
buyer: it should offer BELOW marginal cost, pushing the price down, because it
must buy the shortfall at the spot price. That is the mirror image of a markup,
and rq-descriptive-price-formation.md section 4.5 establishes that four of the
seven largest Iberian firms sit in net-buyer territory for long stretches. This
script asks whether they act on it.

THE VERDICT: NOT IDENTIFIED. Do not read the coefficients as evidence either way.

Three specifications, three different reasons why not:

1. `frac = (q - theta) / q`  ->  beta = -51.7 (t = -3.09), the WRONG sign.
   This is mechanical, not economic. `q` is the firm's CLEARED volume, so a
   unit that marks down clears more, which raises `frac`. Low markup and high
   frac are linked by construction and the regression recovers that link.
   Simultaneity, and it dominates.

2. `frac_cap = (cap - theta) / cap`, capacity being predetermined -> beta = +232
   (t = 0.35). Right sign, standard error three times the coefficient. Once the
   mechanical channel is removed there is nothing left to identify with: theta
   is highly persistent within a firm, and unit + year-month fixed effects
   absorb nearly all of what remains.

3. Cross-firm levels contradict the prediction outright -- Iberdrola, Endesa and
   Naturgy are the most net-buyer firms and post the HIGHEST median markups.
   That comparison is worthless: it sets Iberdrola's CCGTs against Cepsa's
   cogeneration, different plants with different efficiencies and fuels.

WHAT THE RESIDUAL BELOW-COST SHARE ACTUALLY IS (diagnosed 2026-09-04)

Valuing capped plants at the reference price cut the 2022 below-cost share from
53.2% to 47.2%, against a 32.9% baseline in 2018-2021. The residual is **not**
markdown. Three findings, in order of how much they explain:

1. **It is the SHAPE of the offer curve, not its level.** Against the capped MC
   in 2022, the price at 25% of nameplate is below cost 67.9% of the time
   (median gap -91.1), at 50% 47.4% (median gap **+9.5**), at 75% 38.7%
   (+14.2). The typical offer at half capacity is ABOVE capped cost. The 47% is
   the lower half of a wide distribution, and reading it as "half of offers are
   markdowns" mistakes a dispersion statistic for a location one.

2. **The cheap tranche is a START-UP cost, and this repo can prove it.** Units
   declaring a minimum-income condition in `cab` -- a firm's own statement that
   it has a fixed daily cost to recover -- price below cost far more often at
   every quantile:

       declares a min-income condition   p25 59.7%   p50 32.1%   p75 18.8%
       declares none                     p25 31.7%   p50 13.1%   p75  6.2%

   A plant avoiding a shutdown-and-restart rationally offers its first tranche
   below marginal cost and recovers the fixed cost over the day. That is exactly
   Jha & Leslie's argument -- a STATIC marginal-cost benchmark misreads DYNAMIC
   costs as market conduct -- and it means this benchmark cannot separate the
   two, in either direction.

3. **Efficiency imprecision amplifies both, and scales with the gas price.**
   Below-cost share by efficiency tercile x gas price tercile runs 5.5-15.5%
   for high-efficiency units against 18.8-31.7% for low-efficiency ones. Since
   `MC = (gas + 0.202 * co2) / eff`, an error of 0.03 in `eff` moves MC by about
   11 EUR/MWh at 2022 gas prices -- the same order as the markup being measured.
   The below-cost share tracks the gas price LEVEL (45.0% in the top MIBGAS
   decile against 17-27% mid-range) and NOT deviations from its 30-day mean,
   which is the signature of a multiplicative cost-model error rather than of
   plants reacting to price moves.

Two things it is NOT. It is not a handful of bad units: only 4 of 46 gas units
sit above 50% below-cost, and they are 5.5% of unit-periods. And it is not
coal, which contributes 97 observations in 2022.

One economic residual worth keeping. When the cap BINDS, 77.8% of p25 sits
below the capped MC against 57.3% when it does not. The RDL 10/2022 adjustment
is paid only on dispatched energy, so a capped plant has an extra reason to
price its first tranche low. That is conduct, not a benchmark error -- but it
means even the capped MC is not the plant's true opportunity cost.

RERUN AGAINST THE DECLARED COST (`--floor declared`, 2026-09-04)

`cab` publishes what the firm says it needs, so this drops the efficiency
assumption and the gas cap entirely. 24,401 unit-days, 108 units, 16 firms,
2018-2024. Two results.

**The cost-model artefact was real.** The wrong-signed, significant coefficient
on the engineering benchmark (-51.7, t = -3.09) falls to -35.9, t = -1.43. Part
of what looked like a finding there was the efficiency error described above.

**At the margin, the median unit prices at exactly its declared cost.** Offer
minus declared variable term, median gap by quantile of nameplate:

    p25   -57.7   below on 82.3%
    p50   -12.7   below on 63.0%
    p75    +0.0   below on 46.3%

The curve rises from far below the declared cost to exactly it. That is the
same shape the start-up-cost diagnosis predicts -- cheap tranches to secure
dispatch, the marginal tranche priced at declared cost -- and at p75 there is
neither markup nor markdown for declaring units.

**Still not identified.** Every specification is insignificant: the
predetermined-denominator versions have the predicted positive sign at p50 and
p75 (+273, +411) with standard errors two orders larger. 16 clusters instead of
11 and 108 units instead of 68 is an improvement, not a fix. What remains is a
clean null with the cost-measurement objection removed, which is worth more than
the original wrong-signed estimate.

FOUR REASONS THE TEST CANNOT WORK AS SPECIFIED, IN ORDER OF SEVERITY

* **The 2022 cost benchmark was broken and is now FIXED** (2026-09-04). It had
  53.2% of 2022 offers below implied MC against 33.0% before, with a negative
  median markup -- not a markdown but the **gas cap**: from 15 June 2022 a
  capped plant offers on the reference gas price PRGN while the panel valued it
  at the market price, so compliance read as strategic markdown.
  `build_implied_marginal_cost.py` now carries `marginal_cost_capped_eur_mwh`
  and this script uses it. 2022's median markup goes **-8.5 -> +9.7 EUR/MWh**
  and the negative median disappears. A residual gap remains -- 47.2% of 2022
  offers still sit below cost against 32.9% in 2018-2021 -- which is worth
  understanding but is no longer a benchmark error: candidates are the coal
  units, which stay uncapped here, and the compensation mechanics.
  **Fixing it does not rescue the test**: frac_cap moves 232 -> 244 with the
  same standard error. The identification problem is separate from the
  benchmark problem, and only the second one is solved.
* **Eleven clusters.** Only 11 firms own a unit with a plant-specific
  efficiency. Cluster-robust inference on 11 groups is weak whatever the point
  estimate.
* **The sample is the wrong fleet.** 68 thermal units carry a trustworthy
  efficiency, but the net-buyer position is driven by RETAIL books. These
  firms' CCGTs are a small and unrepresentative slice of what makes them net
  buyers.
* **theta is a lower bound.** It captures physical bilateral contracts only and
  misses financial hedges, so true theta is larger and the true net-buyer
  position stronger. That biases against finding the effect, which is at least
  the conservative direction.

WHAT WOULD IDENTIFY IT

An instrument for the contract position. The house instrument in this repo --
VRE share and net load -- is **not excludable here**: renewable output shifts
the residual demand slope and the merit order, and both enter the markup
equation directly, so it cannot isolate the theta channel.

The one credible candidate in hand is **RDL 17/2021's contract exemption**. The
2021 clawback taxed inframarginal revenue on non-emitting generation but
exempted volume sold forward at a fixed price, creating a policy-driven reason
to raise theta. The exclusion argument is cross-fleet: it moves a firm's
contract position through its HYDRO AND NUCLEAR assets, which is unrelated to
its CCGTs' fuel costs -- and the CCGT offers are the outcome. See
levy_contract_exposure.py, which already builds the exposure measure.
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs" / "tables" / "markdown_contract_panel.parquet"
SUPPLY_ROLES = {"generation", "generation_large", "storage_mixed", "pumping"}

sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_owner import owner_group  # noqa: E402


def load() -> pd.DataFrame:
    off = pq.read_table(ROOT / "outputs/tables/capacity_quantile_offer.parquet",
                        columns=["date", "period", "unit", "cap", "p50",
                                 "vre_share", "p_star"]).to_pandas()
    mc = pq.read_table(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet",
                       columns=["unit", "date", "marginal_cost_eur_mwh",
                                "marginal_cost_capped_eur_mwh", "cap_binding",
                                "fuel", "eff_is_generic"]).to_pandas()
    mc = mc[~mc.eff_is_generic]          # plant-specific efficiency only
    ua = pq.read_table(DATA / "omie/registry/unit_agents.parquet",
                       columns=["unit", "agent_owner", "role",
                                "max_power_mw"]).to_pandas()
    ua["firm"] = ua.agent_owner.map(owner_group)
    rd = pq.read_table(ROOT / "outputs/tables/firm_residual_demand_full_owner.parquet",
                       columns=["date", "period", "firm", "q_firm_mw", "theta_mw",
                                "ability_h5", "incentive_h5"]).to_pandas()
    for f in (off, mc, rd):
        f["date"] = pd.to_datetime(f.date)

    d = (off.merge(mc, on=["unit", "date"], how="inner")
            .merge(ua[["unit", "firm"]], on="unit", how="left")
            .merge(rd, on=["date", "period", "firm"], how="inner"))
    cap = ua[ua.role.isin(SUPPLY_ROLES)].groupby("firm").max_power_mw.sum()
    d["cap_firm"] = d.firm.map(cap)
    # Default to the CAPPED cost: under RDL 10/2022 a capped plant offers on
    # the reference gas price, so the market price is the wrong benchmark
    # exactly where the interesting variation is. `markup_uncapped` is kept
    # only to show what the bug did.
    d["markup"] = d.p50 - d.marginal_cost_capped_eur_mwh
    d["markup_uncapped"] = d.p50 - d.marginal_cost_eur_mwh
    d["frac"] = ((d.q_firm_mw - d.theta_mw) / d.q_firm_mw).clip(-5, 1)
    d["frac_cap"] = (d.cap_firm - d.theta_mw) / d.cap_firm
    d["year"] = d.date.dt.year
    d["ym"] = d.date.dt.to_period("M").astype(str)
    return d.dropna(subset=["markup", "frac", "frac_cap"])


def load_declared() -> pd.DataFrame:
    """The same test against the firm's OWN declared cost, from `cab`.

    Two benchmarks live in the declaration and they are not interchangeable:

    * `var` (EUR/MWh) is the firm's declared **marginal** cost. This is what an
      offer should be compared against.
    * `var + fixed / q_max` is **average** avoidable cost including start-up.
      Offers routinely sit below it and that is not a markdown: the
      minimum-income condition is a DAY-level safety net, so a firm can price
      individual steps low and still refuse the whole day if total revenue does
      not cover the fixed term.

    Wide `cab` layout only, so 2018-01-01 to 2025-03-18.
    """
    parts = []
    for f in sorted(glob.glob(str(DATA / "omie/cab/parquet/cab_*.parquet"))):
        t = pq.read_table(f, columns=["date", "unit", "side",
                                      "min_income_fixed_eur",
                                      "min_income_var_eur_mwh",
                                      "max_power_mw"]).to_pandas()
        t = t[t.side == "V"]
        parts.append(t.groupby(["date", "unit"], as_index=False).agg(
            fixed=("min_income_fixed_eur", "max"),
            var=("min_income_var_eur_mwh", "max"),
            cap=("max_power_mw", "max")))
    cab = pd.concat(parts, ignore_index=True)
    cab["date"] = pd.to_datetime(cab.date)
    cab = cab[(cab.date <= "2025-03-18") & (cab["var"].fillna(0) > 0) & (cab.cap > 0)]
    cab["ac_best"] = cab["var"] + cab["fixed"].fillna(0) / (cab.cap * 24.0)

    o = pq.read_table(ROOT / "outputs/tables/capacity_quantile_offer.parquet",
                      columns=["date", "period", "unit", "p25", "p50",
                               "p75"]).to_pandas()
    o["date"] = pd.to_datetime(o.date)
    day = o.groupby(["date", "unit"], as_index=False)[["p25", "p50", "p75"]].median()

    ua = pq.read_table(DATA / "omie/registry/unit_agents.parquet",
                       columns=["unit", "agent_owner", "role",
                                "max_power_mw"]).to_pandas()
    ua["firm"] = ua.agent_owner.map(owner_group)
    cap_firm = ua[ua.role.isin(SUPPLY_ROLES)].groupby("firm").max_power_mw.sum()

    rd = pq.read_table(ROOT / "outputs/tables/firm_residual_demand_full_owner.parquet",
                       columns=["date", "period", "firm", "q_firm_mw",
                                "theta_mw"]).to_pandas()
    rd["date"] = pd.to_datetime(rd.date)
    rd = rd.groupby(["date", "firm"], as_index=False).agg(
        q=("q_firm_mw", "mean"), th=("theta_mw", "mean"))

    d = (day.merge(cab, on=["date", "unit"], how="inner")
            .merge(ua[["unit", "firm"]], on="unit", how="left")
            .merge(rd, on=["date", "firm"], how="inner"))
    d["cap_firm"] = d.firm.map(cap_firm)
    d["frac"] = ((d.q - d.th) / d.q).clip(-5, 1)
    d["frac_cap"] = (d.cap_firm - d.th) / d.cap_firm
    d["ym"] = d.date.dt.to_period("M").astype(str)
    for c in ("p25", "p50", "p75"):
        d[f"mk_{c}"] = d[c] - d["var"]
    return d


def fe_ols(df, y, xs, fes, cluster, iters=6):
    """Within estimator by sequential demeaning, cluster-robust SEs."""
    w = df[[y] + xs + fes + [cluster]].dropna().copy()
    for _ in range(iters):
        for f in fes:
            g = w.groupby(f)
            for c in [y] + xs:
                w[c] = w[c] - g[c].transform("mean")
    X = np.column_stack([np.ones(len(w))] + [w[c].values for c in xs])
    b, *_ = np.linalg.lstsq(X, w[y].values, rcond=None)
    e = w[y].values - X @ b
    Xi = np.linalg.pinv(X.T @ X)
    meat = np.zeros((X.shape[1],) * 2)
    for _, idx in w.groupby(cluster).indices.items():
        s = X[idx].T @ e[idx]
        meat += np.outer(s, s)
    return (list(zip(["const"] + xs, b, np.sqrt(np.diag(Xi @ meat @ Xi)))),
            len(w), w[cluster].nunique())


def run_declared(args) -> int:
    d = load_declared()
    lo, hi = d.mk_p50.quantile([0.01, 0.99])
    d = d[(d.mk_p50 >= lo) & (d.mk_p50 <= hi)]
    print(f"{len(d):,} unit-days, {d.unit.nunique()} units, {d.firm.nunique()} "
          f"firms, {d.date.dt.year.min()}-{d.date.dt.year.max()}")
    print(f"declared variable term: median {d['var'].median():.1f} EUR/MWh\n")

    print("offer vs the firm's OWN declared marginal cost")
    for c in ("p25", "p50", "p75"):
        v = d[c] - d["var"]
        print(f"  {c}: below on {(v < 0).mean():6.1%}   median gap {v.median():8.1f}")
    v = d.p50 - d.ac_best
    print(f"  p50 vs AVERAGE avoidable cost (var + fixed/q_max): "
          f"below on {(v < 0).mean():.1%}, median gap {v.median():.1f} "
          f"-- see load_declared() on why this is not a markdown")

    print("\nPREDICTION: beta > 0 -- nearer net-seller offers further above cost")
    for out in ("mk_p25", "mk_p50", "mk_p75"):
        for lab, xs in (("frac (q cleared)", ["frac"]),
                        ("frac_cap (predetermined)", ["frac_cap"])):
            r, n, nc = fe_ols(d, out, xs, ["unit", "ym"], "firm")
            for nm, b, se in r:
                if nm == "const":
                    continue
                print(f"  {out:7s} {lab:26s} beta={b:9.2f} se={se:8.2f} "
                      f"t={b/se if se else float('nan'):6.2f}  n={n:,} clusters={nc}")
    if args.save:
        out = ROOT / "outputs" / "tables" / "markdown_declared_panel.parquet"
        out.parent.mkdir(parents=True, exist_ok=True)
        d.to_parquet(out, index=False)
        print(f"\nwrote {out.relative_to(ROOT)}  ({len(d):,} rows)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--floor", choices=["mc", "declared"], default="mc",
                    help="mc: implied engineering marginal cost. declared: the "
                         "firm's own variable term from cab -- no efficiency "
                         "assumption and no gas-cap contamination.")
    args = ap.parse_args()

    if args.floor == "declared":
        return run_declared(args)

    d = load()
    lo, hi = d.markup.quantile([0.01, 0.99])
    d = d[(d.markup >= lo) & (d.markup <= hi)].copy()
    print(f"{len(d):,} unit-periods, {d.unit.nunique()} units, {d.firm.nunique()} "
          f"firms, {d.date.min().date()} .. {d.date.max().date()}")
    print(f"markup trimmed to 1-99%: [{lo:.0f}, {hi:.0f}] EUR/MWh\n")

    print("PREDICTION: beta > 0 -- a firm nearer net-seller offers a HIGHER markup")
    for lab, xs in (("frac      (q CLEARED -> simultaneous)", ["frac"]),
                    ("frac_cap  (theta only, cap predetermined)", ["frac_cap"]),
                    ("incentive_h5 = ability x frac", ["incentive_h5"])):
        r, n, nc = fe_ols(d, "markup", xs, ["unit", "ym"], "firm")
        for name, b, se in r:
            if name == "const":
                continue
            print(f"  {lab:42s} beta={b:9.2f}  se={se:8.2f}  "
                  f"t={b/se if se else float('nan'):6.2f}  n={n:,} clusters={nc}")

    print("\nTHE 2022 BENCHMARK, capped vs uncapped (RDL 10/2022)")
    print(f"  {'period':12s}{'n':>9}{'median (capped)':>17}{'below MC':>10}"
          f"{'median (uncapped)':>19}{'below MC':>10}")
    for lab, m in (("2018-2021", d.year <= 2021), ("2022", d.year == 2022),
                   ("2023", d.year == 2023), ("2024-2026", d.year >= 2024)):
        s = d[m]
        print(f"  {lab:12s}{len(s):9,}{s.markup.median():17.1f}"
              f"{(s.markup < 0).mean():10.1%}{s.markup_uncapped.median():19.1f}"
              f"{(s.markup_uncapped < 0).mean():10.1%}")

    print("\nCross-firm levels, which the docstring explains are not comparable")
    g = d.groupby("firm").agg(n=("markup", "size"), units=("unit", "nunique"),
                              med=("markup", "median"),
                              below=("markup", lambda s: (s < 0).mean()),
                              frac=("frac", "mean")).sort_values("frac")
    for f, r in g.iterrows():
        print(f"  {f:<15}{int(r.n):8,}{int(r.units):5d} units  median "
              f"{r.med:7.1f}  below MC {r.below:6.1%}  mean frac {r.frac:6.2f}")

    if args.save:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        d.to_parquet(OUT, index=False)
        print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(d):,} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
