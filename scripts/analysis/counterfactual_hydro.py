#!/usr/bin/env python3
"""The day-ahead price with every firm's storage hydro offered at its price-taking water value.

    .venv/bin/python scripts/analysis/step_curves.py            # input: re-clearable curves
    .venv/bin/python scripts/build/build_hydro_cost.py          # input: the hydro cost
    .venv/bin/python scripts/analysis/counterfactual_hydro.py [--months 201906 ...]

Framework spec §7, for hydro. The spec's counterfactual shifts each firm's offers down by
β̂·X; β is small and its sign unsettled (`rq-leg-b-levels.md` §5), so that shift moves
little. The larger lever is hydro offered away from its water value. This re-clears each
hour with the hydro moved to the frozen hydro cost (`hydro_cost_daily.parquet`).

THE IDEA, WITH AN EXAMPLE. In an evening hour the price is €110, set by a Naturgy hydro
step at €110 whose water value is €85. Moved to €85, that step clears earlier; the next
offers on the curve now meet demand at, say, €104. The hour's counterfactual price is
€104 and the hydro effect is −€6. A step offered below its water value moves up instead.

THE CLEARING. Each hour's effective curve (`step_curves.py`): `a`, all MW offered at or
below each price on both sides, against d_tot, all buy MW. The price is the lowest price
at which a ≥ d_tot; with nothing moved this reproduces the cached re-clear in every valid
hour (checked on every run). A move takes a step's MW out at its offered price and puts it
back at the unit's cost. Hydro steps priced below the clearing price are always fully
accepted in the files, so this is consistent with the effective curve. Ties at the new
price are split pro rata, as OMIE does.

VARIANTS (non-withdrawn steps of units with a cost that day):
  main            storage hydro steps above €1, moved to the 30-day cost (both ways)
  down only       only steps offered above the cost: the hydro markup alone
  90-day cost     the check cost
  with pumped     pumped-storage turbines too (their cost is an arbitrage value)
  zero offers too storage hydro steps at €1 or below also moved up to the cost
  <GROUP>         main, one owner group's units only (six groups)
  same water      each unit's movable steps at k × its cost, one k per unit and month: the
                  k at which a price-taker releasing the unit's actual auction water would
                  run, in the hours where price over cost is highest; k and prices found
                  together (iterated).
                  The water released is held as it was; only how it is priced across the
                  month's hours changes. The main reading; `main` releases 11–19% more
                  water than Iberdrola and Naturgy did in 2022–2025, so it overstates.
  same water, <GROUP>  the same for one owner group's units only

WATER BUDGET. A static re-clear does not keep each reservoir to its water: lower offers
clear in more hours. Dispatch of the moved units under the counterfactual is compared with
their actual dispatch and with the dispatch the cost itself assumes (the running share
cf_s × max power), by group and year. Much of Iberdrola's and Endesa's hydro, and from
2023 nearly all of Naturgy's, is delivered under bilateral contracts (PDBF role 4), outside
the auction and its curves: the auction offers cover the capacity left in each hour. So
the budget counts total output, bilateral plus auction; the counterfactual leaves the
bilateral volume as it was.

Valid hours only (unsplit, clearing identity, re-clear within €0.5 of the price): the
counterfactual is for the Iberian price when Spain and Portugal share one. Rivals' offers
are held as offered: no other firm reacts. 2019-01 → 2025-09, hourly.

WRITES outputs/tables/counterfactual_hydro_hourly.parquet (gitignored) and
counterfactual_hydro.csv (by variant and year; hour of day; the water budget).
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
TABLES = ROOT / "outputs/tables"
CACHE = ROOT / "outputs/cache/step"
COST = TABLES / "hydro_cost_daily.parquet"
OUT_H = TABLES / "counterfactual_hydro_hourly.parquet"
OUT = TABLES / "counterfactual_hydro.csv"
FIRST, LAST = "201901", "202509"
EPOCH = pd.Timestamp("2018-01-01")
ZERO = 1.0
TOL = 1e-6
ITER, DAMP = 12, 0.5                       # same water: rounds of k against prices; damping on log k
K_MIN, K_MAX = 0.2, 5.0
SIX = ["EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL", "MOVHERA"]


def months() -> list[str]:
    return [m for m in sorted(p.stem.split("_")[1] for p in CACHE.glob("hydro_2*.parquet")) if FIRST <= m <= LAST]


def reclear(mk: pd.DataFrame, d_tot: pd.Series, mv: pd.DataFrame | None) -> pd.DataFrame:
    """hid, p, frac: the lowest price at which cumulative MW reaches d_tot, after taking each
    move's MW out at `price` and putting it in at `new`; frac: share accepted of the MW at p."""
    inc = mk[["hid", "price", "da"]]
    if mv is not None and len(mv):
        inc = pd.concat([inc, pd.DataFrame({"hid": mv.hid, "price": mv.price, "da": -mv.mw}),
                         pd.DataFrame({"hid": mv.hid, "price": mv.new, "da": mv.mw})], ignore_index=True)
    g = inc.groupby(["hid", "price"], sort=True).da.sum().reset_index()
    g["cum"] = g.groupby("hid").da.cumsum()
    g["need"] = d_tot.reindex(g.hid).to_numpy()
    first = g[g.cum >= g.need - TOL].groupby("hid").head(1)
    lo = first.cum - first.da
    frac = ((first.need - lo) / first.da.where(first.da > 0)).clip(0, 1).fillna(1.0)
    return pd.DataFrame({"hid": first.hid.to_numpy(), "p": first.price.to_numpy(), "frac": frac.to_numpy()})


def dispatch(steps: pd.DataFrame, col: str, clr: pd.DataFrame) -> pd.Series:
    """MW accepted per (hid, unit): steps priced (column `col`) below the hour's price in
    full, at it pro rata."""
    s = steps.merge(clr, on="hid")
    below = s[col] < s.p - 0.005
    at = (s[col] - s.p).abs() <= 0.005
    s["acc"] = np.where(below, s.mw, np.where(at, s.mw * s.frac, 0.0))
    return s.groupby(["hid", "unit"]).acc.sum()


def bilateral(ym: str, units: list[str]) -> pd.Series:
    """(hid, unit) -> MWh the unit delivers under bilateral contracts in the hour (PDBF role
    4, outside the auction), hourly hid as in the step caches."""
    p = pd.read_parquet(ROOT / f"data/omie/pdbf/parquet/pdbf_{ym}.parquet",
                        columns=["date", "period", "unit", "role_code", "schedule_mw", "resolution_min"],
                        filters=[("unit", "in", units), ("role_code", "==", "4")])
    if p.empty:
        return pd.Series(dtype=float, name="bilateral")
    hour = (p.period - 1) // (60 // p.resolution_min)
    p["hid"] = (pd.to_datetime(p.date) - EPOCH).dt.days * 24 + hour
    p["mwh"] = p.schedule_mw * p.resolution_min / 60
    return p.groupby(["hid", "unit"]).mwh.sum().rename("bilateral")


def threshold_k(units: pd.DataFrame, movable: np.ndarray, clr: pd.DataFrame, target: pd.Series) -> pd.Series:
    """Per unit, the k at which a price-taker releases its target water against the prices
    of `clr`: it runs its movable MW in the hours where price over cost is highest, so k is
    that ratio in the marginal hour. Its steps at €1 or below run whenever the price is
    above them, so they count against the target first."""
    p = clr.set_index("hid").p
    fixed = dispatch(units[~movable].assign(new=units.price[~movable]), "new", clr).groupby(level="unit").sum()
    m = units[movable].groupby(["unit", "hid"]).agg(mw=("mw", "sum"), cost=("cost", "first")).reset_index()
    m["ratio"] = p.reindex(m.hid).to_numpy() / m.cost.where(m.cost > 0)
    m = m.sort_values(["unit", "ratio"], ascending=[True, False])
    m["cum"] = m.groupby("unit").mw.cumsum()
    need = (target - fixed.reindex(target.index).fillna(0.0)).clip(lower=0.0)
    m["need"] = need.reindex(m.unit).to_numpy()
    k = {}
    for unit, g in m.groupby("unit", sort=False):
        r, c, n = g.ratio.to_numpy(), g.cum.to_numpy(), g.need.iat[0]
        if n <= 0:
            k[unit] = r[0] * 1.01                    # run in no hour
        elif n >= c[-1]:
            k[unit] = r[-1] * 0.99                   # run in every hour
        else:
            k[unit] = r[np.searchsorted(c, n)]       # the marginal hour
    return pd.Series(k).clip(K_MIN, K_MAX)


def water_neutral(mk: pd.DataFrame, d_tot: pd.Series, units: pd.DataFrame, act: pd.Series,
                  movable: np.ndarray, base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Re-clear with each unit's movable steps at k_u × its cost, k_u such that the unit
    releases its actual water as a price-taker would: in the month's hours where the price
    over its cost is highest (`threshold_k`). Prices and k are found together: k against
    the last prices, re-clear, again ITER times, damped on log k. Returns the clearing and,
    per unit, k and auction dispatch actual against counterfactual."""
    ids = units.unit.unique()
    target = act.reindex(ids).fillna(0.0)
    eps = 0.01 * units.drop_duplicates(["hid", "unit"]).groupby("unit").cap_mw.sum().reindex(ids).fillna(1.0)
    scale = pd.Series(1.0, index=ids)        # a large unit lowers the price where it runs, so it is
    clr, logk = base, None                   # only partly accepted there: scale its target up
    for _ in range(ITER):
        kn = np.log(threshold_k(units, movable, clr, target * scale).reindex(ids).fillna(1.0))
        logk = kn if logk is None else DAMP * logk + (1 - DAMP) * kn
        k = np.exp(logk)
        u = units.assign(new=np.where(movable, units.cost * k.reindex(units.unit).to_numpy(), units.price))
        clr = reclear(mk, d_tot, u[movable])
        cf = dispatch(u, "new", clr).groupby(level="unit").sum().reindex(ids).fillna(0.0)
        scale = (scale * ((target + eps) / (cf + eps)) ** (1 - DAMP)).clip(0.25, 4.0)
    return clr, pd.DataFrame({"k": k, "actual": target, "cf": cf})


def month(ym: str, cost: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    h = pd.read_parquet(CACHE / f"hours_{ym}.parquet")
    h = h[h.valid].copy()
    mk = pd.read_parquet(CACHE / f"market_{ym}.parquet")
    mk = mk[mk.hid.isin(h.hid)].sort_values(["hid", "price"], ignore_index=True)
    mk["da"] = mk.groupby("hid").a.diff().fillna(mk.a)
    d_tot = h.set_index("hid").d_tot
    hy = pd.read_parquet(CACHE / f"hydro_{ym}.parquet", columns=["hid", "date", "unit", "group", "cls", "price",
                                                                  "mw", "cap_mw", "withdrawn"])
    hy = hy[hy.hid.isin(h.hid) & ~hy.withdrawn & (hy.mw > 0)].copy()
    hy["date"] = pd.to_datetime(hy.date)
    hy = hy.merge(cost, on=["unit", "date"], how="left")

    base = reclear(mk, d_tot, None).set_index("hid")
    chk = h.set_index("hid").p_clear
    err = (base.p - chk.reindex(base.index)).abs()
    assert (err < 0.006).mean() > 0.999, f"{ym}: baseline re-clear differs from p_clear in {(err >= 0.006).sum()} hours"

    stor = hy[(hy.cls == "hydro") & hy.cost.notna()]
    bil = bilateral(ym, stor.unit.unique().tolist())
    variants = {
        "main": stor[stor.price > ZERO].assign(new=lambda x: x.cost),
        "down only": stor[(stor.price > ZERO) & (stor.price > stor.cost)].assign(new=lambda x: x.cost),
        "90-day cost": stor[(stor.price > ZERO) & stor.cost_90.notna()].assign(new=lambda x: x.cost_90),
        "with pumped": hy[(hy.price > ZERO) & hy.cost.notna()].assign(new=lambda x: x.cost),
        "zero offers too": stor.assign(new=lambda x: x.cost),
    }
    for g in SIX:
        variants[g] = variants["main"][variants["main"].group == g]
    out = h[["hid", "date", "period", "p_star", "p_clear"]].set_index("hid")
    budget = []
    # the same water: each unit's monthly auction dispatch held at its actual
    act = dispatch(stor, "price", base.reset_index()).groupby(level="unit").sum()
    for name, sel in [("same water", stor.unit.notna()), *[(f"same water, {g}", stor.group == g) for g in SIX]]:
        su = stor[sel]
        if su.empty:
            out[name] = out.p_clear
            continue
        clr, kk = water_neutral(mk, d_tot, su, act, (su.price > ZERO).to_numpy(), base.reset_index())
        out[name] = clr.set_index("hid").p.reindex(out.index)
        if name == "same water":
            kk = kk.join(su.drop_duplicates("unit").set_index("unit").group)
            kk["k_act"] = kk.k * kk.actual
            budget.append(kk.groupby("group")[["actual", "cf", "k_act"]].sum().assign(variant=name, ym=ym)
                          .reset_index().assign(expected=np.nan, bilateral=np.nan))
    for name, mv in variants.items():
        clr = reclear(mk, d_tot, mv)
        out[name] = clr.set_index("hid").p.reindex(out.index)
        if name in ("main", "down only", "90-day cost"):
            units = stor[stor.unit.isin(mv.unit.unique())].copy()     # all steps of the moved units
            units["new"] = mv.new.reindex(units.index).fillna(units.price)
            act = dispatch(units, "price", base.reset_index())
            cf = dispatch(units, "new", clr)
            uh = units.drop_duplicates(["hid", "unit"]).set_index(["hid", "unit"])
            exp = (uh.cf_s * uh.cap_mw).rename("expected")                # the share the cost assumes
            bl = bil.reindex(uh.index).fillna(0.0)
            b = pd.concat([act.rename("actual"), cf.rename("cf"), exp, bl], axis=1).fillna(0.0).reset_index()
            b = b.merge(units.drop_duplicates("unit")[["unit", "group"]], on="unit")
            budget.append(b.groupby("group")[["actual", "cf", "expected", "bilateral"]].sum()
                          .assign(variant=name, ym=ym).reset_index())
    return out.reset_index(), pd.concat(budget, ignore_index=True)


def summarise(x: pd.DataFrame, budget: pd.DataFrame) -> pd.DataFrame:
    names = [c for c in x.columns if c not in ("hid", "date", "period", "p_star", "p_clear", "year", "hour")]
    rows = []
    for name in names:
        dp = x[name] - x.p_clear
        for yr, g in [("all", x), *x.groupby("year")]:
            e = dp.loc[g.index]
            rows.append({"table": "price", "variant": name, "year": yr, "hours": len(g),
                         "p_clear": g.p_clear.mean(), "p_cf": g[name].mean(), "dp_mean": e.mean(),
                         "dp_median": e.median(), "dp_p05": e.quantile(0.05), "dp_p95": e.quantile(0.95),
                         "share_down": (e < -0.5).mean(), "share_up": (e > 0.5).mean(),
                         "dp_pct": e.mean() / g.p_clear.mean()})
    dp = x["main"] - x.p_clear
    for hr, g in x.groupby("hour"):
        rows.append({"table": "hour of day, main", "variant": "main", "year": "all", "hour": hr, "hours": len(g),
                     "p_clear": g.p_clear.mean(), "p_cf": g["main"].mean(), "dp_mean": dp.loc[g.index].mean(),
                     "share_down": (dp.loc[g.index] < -0.5).mean(), "share_up": (dp.loc[g.index] > 0.5).mean()})
    budget["year"] = budget.ym.str[:4]
    sw = budget[budget.variant == "same water"]
    for (g, y), x in sw.groupby(["group", "year"]):
        rows.append({"table": "same water", "variant": "same water", "group": g, "year": y,
                     "actual_gwh": x.actual.sum() / 1000, "cf_gwh": x.cf.sum() / 1000,
                     "auction_ratio": x.cf.sum() / x.actual.sum() if x.actual.sum() else np.nan,
                     "k_mean": x.k_act.sum() / x.actual.sum() if x.actual.sum() else np.nan})
    budget = budget[budget.variant != "same water"]
    bt = budget.groupby(["variant", "group", "year"])[["actual", "cf", "expected", "bilateral"]].sum().reset_index()
    for r in bt.itertuples(index=False):
        tot_a, tot_c = r.bilateral + r.actual, r.bilateral + r.cf
        rows.append({"table": "water budget", "variant": r.variant, "group": r.group, "year": r.year,
                     "actual_gwh": r.actual / 1000, "cf_gwh": r.cf / 1000, "bilateral_gwh": r.bilateral / 1000,
                     "expected_gwh": r.expected / 1000, "auction_ratio": r.cf / r.actual if r.actual else np.nan,
                     "total_ratio": tot_c / tot_a if tot_a else np.nan,
                     "total_cf_over_expected": tot_c / r.expected if r.expected else np.nan,
                     "total_actual_over_expected": tot_a / r.expected if r.expected else np.nan})
    return pd.DataFrame(rows)


def main() -> int:
    ap = ArgumentParser()
    ap.add_argument("--months", nargs="*")
    args = ap.parse_args()
    cost = pd.read_parquet(COST, columns=["unit", "date", "cost_eur_mwh", "cost_90_eur_mwh", "cf_s"])
    cost = cost.rename(columns={"cost_eur_mwh": "cost", "cost_90_eur_mwh": "cost_90"})
    cost["date"] = pd.to_datetime(cost.date)
    hours, budget = [], []
    for ym in args.months or months():
        o, b = month(ym, cost)
        hours.append(o)
        budget.append(b)
        print(f"  {ym}: {len(o):>4} valid hours, mean price {o.p_clear.mean():6.2f}, main {o['main'].mean():6.2f} "
              f"({(o['main'] - o.p_clear).mean():+.2f}), down only {(o['down only'] - o.p_clear).mean():+.2f}", flush=True)
    x = pd.concat(hours, ignore_index=True)
    x["year"] = pd.to_datetime(x.date).dt.year
    x["hour"] = x.period - 1
    if not args.months:
        x.to_parquet(OUT_H, index=False)
    t = summarise(x, pd.concat(budget, ignore_index=True))
    pd.set_option("display.width", 240)
    p = t[t.table == "price"]
    print("\nmean price change, €/MWh (counterfactual − actual), valid hours:")
    print(p.pivot(index="variant", columns="year", values="dp_mean").round(2).to_string())
    print("\nas a share of the mean price:")
    print(p.pivot(index="variant", columns="year", values="dp_pct").round(3).to_string())
    print("\nmain, by year:")
    print(p[p.variant == "main"][["year", "hours", "p_clear", "p_cf", "dp_mean", "dp_median", "dp_p05", "dp_p95",
                                  "share_down", "share_up"]].round(2).to_string(index=False))
    hr = t[t.table == "hour of day, main"]
    print("\nmain, by hour of day:")
    print(hr[["hour", "p_clear", "dp_mean", "share_down", "share_up"]].round(2).to_string(index=False))
    wb = t[t.table == "water budget"]
    for v, lab in [("auction_ratio", "auction dispatch, counterfactual over actual"),
                   ("total_ratio", "total output (auction + bilateral), counterfactual over actual"),
                   ("total_actual_over_expected", "total output, actual over expected"),
                   ("total_cf_over_expected", "total output, counterfactual over expected")]:
        print(f"\nwater budget, main: {lab} (moved units; expected: the running share the cost assumes):")
        print(wb[wb.variant == "main"].pivot_table(index="group", columns="year", values=v).round(2).to_string())
    swt = t[(t.table == "same water") & t.group.isin(SIX)]
    print("\nsame water: counterfactual over actual auction dispatch, and k (the water value as a multiple of the "
          "cost, weighted by actual dispatch):")
    print(swt.pivot_table(index="group", columns="year", values="auction_ratio").round(2).to_string())
    print(swt.pivot_table(index="group", columns="year", values="k_mean").round(2).to_string())
    if not args.months:
        t.to_csv(OUT, index=False)
        print(f"\nwrote {OUT.relative_to(ROOT)} and {OUT_H.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
