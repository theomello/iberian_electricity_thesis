#!/usr/bin/env python3
"""What does self-supply cost? Book balancing priced at each plant's cost.

    .venv/bin/python scripts/analysis/self_supply_cost.py --build      # the panel
    .venv/bin/python scripts/analysis/self_supply_cost.py --describe   # step 1a

Design `docs/specs/2026-10-21-self-supply-cost-design.md`; plan
`docs/plans/2026-10-21-self-supply-cost-step1a.md`; check `qa/check_self_supply_cost.py`.

THE MEASURE. For each of the five firms, date and hour, over the units it owns that day
(largest exposed owner, as in `holiday_quantity_test.py`):

    m = sum over units of q x (p - c)          € per hour

q the unit's scheduled MW in PDBF (auction and bilateral legs apart), p the day-ahead price in
the unit's country, c its cost that day. Generation is exactly the quantity test's `gen`: a
unit-hour-leg with MW > 0 whose role is not retail or pumping.

CLASSES, by precedence (a cost source beats the technology label):
  nuclear         reactors of `nuclear_cuts_benchmark_daily`; c = c_acct (fuel at book value)
  pumped          `hydro_cost_daily` units flagged pumped, or labelled pumped storage; no cost
  hydro_storage   other `hydro_cost_daily` units; c = the water value λ* (cost_eur_mwh)
  gas, coal       `implied_marginal_cost_daily` with a plant-specific efficiency;
                  c = marginal_cost_capped_bid_eur_mwh (known when offers close; gas cap in)
  wind, solar     by label (tech_omie, else tech_omie_early); c = 0
  hydro_other     other hydro by label (run-of-river); c = 0
  thermal_nocost  combined cycles and coal with no plant-specific efficiency; no cost
  generic         OMIE's generic units (listing unit type GENERICA*): no plant behind them. A
                  generic sale unit resells, under a bilateral contract, what its twin generic
                  purchase unit bought (Naturgy GGNCOV1 / GGNCOC1, EDP GEDPGV2 / GEDPGC2: equal
                  and opposite, July 2020). Not output; left out of the costed share's base.
  nocost          everything else: cogeneration, biomass, unlabelled
A unit-day whose class has a cost source but no cost that day is uncosted: it counts in mwh
and pq, not in costed_mwh, m or above_*.

VARIANTS for step 1b's checks: m_nuc_lo (nuclear at c_lo), m_nuc_hi (c_hi), m_hyd90 (hydro at
cost_90_eur_mwh); each equals m outside its class.

OUTPUTS (gitignored):
  outputs/tables/self_supply_panel.parquet           group, date, hour, cls, leg, mwh, costed_mwh,
                                                     pq, pbarq, m, m_nuc_lo, m_nuc_hi, m_hyd90,
                                                     above_mwh, above_eur
  outputs/tables/self_supply_hydro_unitday.parquet   unit, group, date, q_auction, q_bilateral, pq, pbarq
pq = sum p q and pbarq = sum p_bar q, p_bar the day's mean price in the unit's country, so
pq / pbarq is a capture ratio (above 1: output in the day's dearer hours).
"""
from __future__ import annotations

import re
import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
for sub in ("lib", "analysis"):
    sys.path.insert(0, str(ROOT / "scripts" / sub))
from midday_hydro_iv import cluster_meat  # noqa: E402
from step_estimator import wdemean  # noqa: E402
from unit_ownership import majority_group, spells  # noqa: E402

DATA = ROOT / "data"
T = ROOT / "outputs" / "tables"
PANEL = T / "self_supply_panel.parquet"
UNITDAY = T / "self_supply_hydro_unitday.parquet"
FIRMS = ["ENDESA", "IBERDROLA", "NATURGY", "EDP", "REPSOL"]
START, END = pd.Timestamp("2019-01-01"), pd.Timestamp("2025-09-30")
ZERO_COST = {"wind", "solar", "hydro_other"}
COSTS = ["c", "c_nuc_lo", "c_nuc_hi", "c_hyd90"]
SUMS = ["mwh", "costed_mwh", "pq", "pbarq", "m", "m_nuc_lo", "m_nuc_hi", "m_hyd90", "above_mwh", "above_eur"]
COSTED = ["nuclear", "hydro_storage", "hydro_other", "wind", "solar", "gas", "coal"]
Z80 = 1.96 + 0.84
OUT = {k: T / f"self_supply_{k}.csv" for k in ("composition", "above_cost", "hydro_timing", "generic", "power")}


def unit_classes(nuclear: set | None = None, hydro: pd.DataFrame | None = None,
                 thermal: pd.DataFrame | None = None, labels: pd.DataFrame | None = None,
                 generic: set | None = None) -> pd.DataFrame:
    """unit, cls: each unit's class, a cost source first, then OMIE's generic units, then the
    technology label."""
    if nuclear is None:
        nuclear = set(pd.read_parquet(T / "nuclear_cuts_benchmark_daily.parquet", columns=["unit"]).unit)
    if hydro is None:
        hydro = pd.read_parquet(T / "hydro_cost_daily.parquet", columns=["unit", "pumped"])
    if thermal is None:
        thermal = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet",
                                  columns=["unit", "fuel", "eff_is_generic"])
        thermal = thermal[~thermal.eff_is_generic]
    if labels is None:
        a = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["unit", "tech_omie", "tech_omie_early"])
        labels = pd.DataFrame({"unit": a.unit, "tech": a.tech_omie.fillna(a.tech_omie_early)})
    if generic is None:
        lst = pd.read_parquet(DATA / "omie/registry/omie_unit_lists.parquet", columns=["unit", "unit_type"])
        generic = set(lst.unit[lst.unit_type.fillna("").str.startswith("GENERICA")])
    by_label = {"wind": "wind", "solar": "solar", "hydro": "hydro_other", "pumped storage": "pumped",
                "gas CCGT": "thermal_nocost", "coal": "thermal_nocost"}
    out = labels.set_index("unit").tech.map(by_label).fillna("nocost")
    pumped = hydro.groupby("unit").pumped.any()
    fuel = thermal.drop_duplicates("unit").set_index("unit").fuel
    extra = pd.Index(sorted(set(nuclear) | set(pumped.index) | set(fuel.index) | set(generic))).difference(out.index)
    out = pd.concat([out, pd.Series("nocost", index=extra)])
    out.loc[list(generic)] = "generic"
    out.loc[fuel.index] = fuel.to_numpy()
    out.loc[pumped.index] = np.where(pumped.to_numpy(), "pumped", "hydro_storage")
    out.loc[list(nuclear)] = "nuclear"
    return out.rename("cls").rename_axis("unit").reset_index()


def daily_costs() -> pd.DataFrame:
    """unit, date, c, c_nuc_lo, c_nuc_hi, c_hyd90: each costed unit's cost that day, €/MWh."""
    n = pd.read_parquet(T / "nuclear_cuts_benchmark_daily.parquet", columns=["unit", "date", "c_lo", "c_acct", "c_hi"])
    n = pd.DataFrame({"unit": n.unit, "date": n.date, "c": n.c_acct, "c_nuc_lo": n.c_lo, "c_nuc_hi": n.c_hi,
                      "c_hyd90": n.c_acct})
    h = pd.read_parquet(T / "hydro_cost_daily.parquet", columns=["unit", "date", "pumped", "cost_eur_mwh", "cost_90_eur_mwh"])
    h = h[~h.pumped]
    h = pd.DataFrame({"unit": h.unit, "date": h.date, "c": h.cost_eur_mwh, "c_nuc_lo": h.cost_eur_mwh,
                      "c_nuc_hi": h.cost_eur_mwh, "c_hyd90": h.cost_90_eur_mwh})
    t = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet",
                        columns=["unit", "date", "eff_is_generic", "marginal_cost_capped_bid_eur_mwh"])
    t = t[~t.eff_is_generic]
    c = t.marginal_cost_capped_bid_eur_mwh
    t = pd.DataFrame({"unit": t.unit, "date": t.date, "c": c, "c_nuc_lo": c, "c_nuc_hi": c, "c_hyd90": c})
    d = pd.concat([n, h, t], ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    return d.drop_duplicates(["unit", "date"])


def margin_rows(u: pd.DataFrame) -> pd.DataFrame:
    """Adds mwh, costed_mwh, pq, pbarq, m (and its variants), above_mwh, above_eur to unit-hours
    carrying q (MW over the hour), p, pbar and the costs (NaN = uncosted)."""
    u = u.copy()
    q, p = u.q.to_numpy(float), u.p.to_numpy(float)
    costed = u.c.notna().to_numpy()
    u["mwh"] = q
    u["costed_mwh"] = np.where(costed, q, 0.0)
    u["pq"] = p * q
    u["pbarq"] = u.pbar.to_numpy(float) * q
    for col, cost in (("m", "c"), ("m_nuc_lo", "c_nuc_lo"), ("m_nuc_hi", "c_nuc_hi"), ("m_hyd90", "c_hyd90")):
        u[col] = np.where(costed, q * (p - u[cost].to_numpy(float)), 0.0)
    above = costed & (u.c.to_numpy(float) > p)
    u["above_mwh"] = np.where(above, q, 0.0)
    u["above_eur"] = np.where(above, q * (u.c.to_numpy(float) - p), 0.0)
    return u


def prices() -> pd.DataFrame:
    """date, hour, price_es, price_pt, pbar_es, pbar_pt (the day's mean price) on full hourly days."""
    p = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                        columns=["date", "period", "resolution_min", "price_es", "price_pt"])
    p["date"] = pd.to_datetime(p.date)
    p = p[(p.date >= START) & (p.date <= END) & (p.resolution_min == 60)]
    n = p.groupby("date").period.transform("count")
    p = p[n == 24].copy()
    p["hour"] = p.period - 1
    for z in ("es", "pt"):
        p[f"pbar_{z}"] = p.groupby("date")[f"price_{z}"].transform("mean")
    return p.drop(columns=["period", "resolution_min"])


def month_rows(f: Path, role: pd.Series, country: pd.Series, cls: pd.Series, costs: pd.DataFrame,
               px: pd.DataFrame, sp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One PDBF month: the five firms' generation unit-hour-legs, classed, priced and costed;
    returned aggregated to the panel and to storage-hydro unit-days."""
    p = pd.read_parquet(f, columns=["date", "period", "resolution_min", "unit", "schedule_mw", "role_code"])
    p["date"] = pd.to_datetime(p.date)
    p = p[(p.date >= START) & (p.date <= END)]
    if p.empty:
        return pd.DataFrame(), pd.DataFrame()
    per = p.groupby("date").agg(n=("period", "max"), res=("resolution_min", "first"))
    full = per.index[((per.res == 60) & (per.n == 24)) | ((per.res == 15) & (per.n == 96))]
    p = p[p.date.isin(full)].copy()
    p["hour"] = np.where(p.resolution_min == 60, p.period - 1, (p.period - 1) // 4)
    p["mw"] = p.schedule_mw * p.resolution_min / 60
    p["bil"] = p.role_code == "4"
    u = p.groupby(["unit", "date", "hour", "bil"], as_index=False).mw.sum()
    keys = u[["unit", "date"]].drop_duplicates()
    keys["group"] = majority_group(keys, sp, exposed=True).to_numpy()
    u = u.merge(keys, on=["unit", "date"])
    r = u.unit.map(role)
    u = u[u.group.isin(FIRMS) & (u.mw > 0) & ~r.isin(["purchase_retail", "pumping"])].copy()
    u["leg"] = np.where(u.bil, "bilateral", "auction")
    u["cls"] = u.unit.map(cls).fillna("nocost")
    pt = u.unit.map(country).eq("PT").to_numpy()
    u = u.merge(px, on=["date", "hour"], how="left")
    if u.price_es.isna().any():
        raise ValueError(f"{f.name}: {int(u.price_es.isna().sum())} unit-hours without a price")
    u["p"] = np.where(pt, u.price_pt, u.price_es)
    u["pbar"] = np.where(pt, u.pbar_pt, u.pbar_es)
    u = u.merge(costs, on=["unit", "date"], how="left")
    zero = u.cls.isin(ZERO_COST)
    u.loc[zero, COSTS] = 0.0
    u.loc[~zero & ~u.cls.isin(["nuclear", "hydro_storage", "gas", "coal"]), COSTS] = np.nan
    u = margin_rows(u.rename(columns={"mw": "q"}))
    panel = u.groupby(["group", "date", "hour", "cls", "leg"], as_index=False)[SUMS].sum()
    h = u[u.cls == "hydro_storage"]
    ud = h.pivot_table(index=["unit", "group", "date"], columns="leg", values="q", aggfunc="sum", fill_value=0.0)
    ud = ud.reindex(columns=["auction", "bilateral"], fill_value=0.0).add_prefix("q_")
    ud = ud.join(h.groupby(["unit", "group", "date"])[["pq", "pbarq"]].sum()).reset_index()
    return panel, ud


def build() -> int:
    reg = pd.read_parquet(DATA / "omie/registry/unit_registry.parquet", columns=["unit", "role", "country"])
    role, country = reg.set_index("unit").role, reg.set_index("unit").country
    cls = unit_classes().set_index("unit").cls
    costs, px, sp = daily_costs(), prices(), spells()
    parts, uds = [], []
    for f in sorted((DATA / "omie/pdbf/parquet").glob("pdbf_*.parquet")):
        ym = f.stem.split("_")[1]
        if not (START.strftime("%Y%m") <= ym <= END.strftime("%Y%m")):
            continue
        a, b = month_rows(f, role, country, cls, costs, px, sp)
        parts.append(a)
        uds.append(b)
        print(f"  {ym}: {a.mwh.sum() / 1e6:.2f} TWh, costed {a.costed_mwh.sum() / max(a.mwh.sum(), 1):.1%}", flush=True)
    d = pd.concat(parts, ignore_index=True)
    d.to_parquet(PANEL, index=False)
    ud = pd.concat(uds, ignore_index=True)
    ud.to_parquet(UNITDAY, index=False)
    print(f"wrote {PANEL.relative_to(ROOT)} ({len(d):,} rows) and {UNITDAY.relative_to(ROOT)} ({len(ud):,} unit-days)")
    return 0


def capture(pq, pbarq) -> float:
    """Σ p q / Σ p̄ q: above 1 when output sits in the day's dearer hours."""
    return float(np.sum(pq) / np.sum(pbarq))


def fe_codes(d: pd.DataFrame, effects) -> list:
    keys = {"date": d.date.dt.strftime("%Y%m%d"),
            "group_month": d.get("group", pd.Series("", index=d.index)).astype(str) + d.date.dt.strftime("%Y%m"),
            "unit_month": d.get("unit", pd.Series("", index=d.index)).astype(str) + d.date.dt.strftime("%Y%m")}
    return [pd.factorize(keys[e])[0] for e in effects]


def _clusters(d: pd.DataFrame, cluster: str) -> np.ndarray:
    return (d.date.dt.strftime("%G%V") if cluster == "week" else d.date.dt.strftime("%Y%m%d")).to_numpy()


def fit_daily(d: pd.DataFrame, y: str, x: str, cluster: str = "date",
              effects=("date", "group_month")) -> tuple[float, float]:
    """y on x after the effects (date and group × month unless given); b and its clustered se."""
    M = wdemean(d[[y, x]].to_numpy(float), fe_codes(d, effects), np.ones(len(d)))
    yy, xx = M[:, 0], M[:, 1]
    b = float(xx @ yy / (xx @ xx))
    se = float(np.sqrt(cluster_meat(xx[:, None], yy - b * xx, _clusters(d, cluster))[0, 0]) / (xx @ xx))
    return b, se


def se_null(d: pd.DataFrame, y: str, x: str, cluster: str = "date", effects=("date", "group_month")) -> float:
    """se of y on x under b = 0, from the outcome residual only: b itself is never formed."""
    M = wdemean(d[[y, x]].to_numpy(float), fe_codes(d, effects), np.ones(len(d)))
    yy, xx = M[:, 0], M[:, 1]
    return float(np.sqrt(cluster_meat(xx[:, None], yy, _clusters(d, cluster))[0, 0]) / (xx @ xx))


def generic_units() -> pd.DataFrame:
    """The five firms' generic units with volume: TWh by unit, year and leg, and the hourly match
    of each sale unit (…V…) with its purchase twin (same code, V → C)."""
    lst = pd.read_parquet(DATA / "omie/registry/omie_unit_lists.parquet")
    lst = lst.sort_values("snapshot").drop_duplicates("unit", keep="last")
    gen = lst[lst.unit_type.fillna("").str.startswith("GENERICA")]
    parts = []
    for f in sorted((DATA / "omie/pdbf/parquet").glob("pdbf_*.parquet")):
        ym = f.stem.split("_")[1]
        if not (START.strftime("%Y%m") <= ym <= END.strftime("%Y%m")):
            continue
        p = pd.read_parquet(f, columns=["date", "period", "resolution_min", "unit", "schedule_mw", "role_code"],
                            filters=[("unit", "in", list(gen.unit))])
        p["mwh"] = p.schedule_mw * p.resolution_min / 60
        parts.append(p.groupby(["unit", "date", "period", "role_code"], as_index=False).mwh.sum())
    p = pd.concat(parts, ignore_index=True)
    p["date"] = pd.to_datetime(p.date)
    p["year"] = p.date.dt.year
    p["leg"] = np.where(p.role_code == "4", "bilateral", "other")
    vol = p.groupby(["unit", "year", "leg"]).mwh.sum().unstack("leg", fill_value=0.0)
    vol = vol.reindex(columns=["bilateral", "other"], fill_value=0.0) / 1e6
    vol = vol.reset_index().merge(gen[["unit", "descr", "agent_owner"]], on="unit")
    big = vol.groupby("unit")[["bilateral", "other"]].apply(lambda x: x.abs().max().max())
    vol = vol[vol.unit.isin(big.index[big > 0.1])]
    h = p.groupby(["unit", "date", "period"]).mwh.sum()
    rows = []
    for v in sorted(u for u in vol.unit.unique() if re.search(r"V\d*$", u)):
        c = re.sub(r"V(\d*)$", r"C\1", v)
        if v not in h.index.get_level_values(0):
            continue
        sv = h.loc[v]
        sc = h.loc[c] if c in h.index.get_level_values(0) else pd.Series(dtype=float)
        j = pd.concat([sv.rename("v"), sc.rename("c")], axis=1).fillna(0.0)
        rows.append({"unit": v, "twin": c, "sale_twh": j.v.clip(lower=0).sum() / 1e6,
                     "twin_twh": j.c.sum() / 1e6, "max_hour_gap_mwh": (j.v + j.c).abs().max(),
                     "matched_share": 1 - (j.v + j.c).abs().sum() / max(j.v.abs().sum(), 1e-9)})
    return vol, pd.DataFrame(rows)


def describe() -> int:
    d = pd.read_parquet(PANEL)
    d["year"] = d.date.dt.year
    pd.set_option("display.width", 160)
    phys = d[d.cls != "generic"]

    # 1. composition
    comp = d.groupby(["group", "year", "cls", "leg"], as_index=False)[["mwh", "costed_mwh"]].sum()
    comp["twh"], comp["costed_twh"] = comp.mwh / 1e6, comp.costed_mwh / 1e6
    comp.drop(columns=["mwh", "costed_mwh"]).to_csv(OUT["composition"], index=False)
    t = d.groupby(["cls", "leg"]).mwh.sum().unstack(fill_value=0.0) / 1e6
    t["bilateral_share"] = t.bilateral / t.sum(axis=1)
    print("\n1. OWN OUTPUT, five firms 2019-01 → 2025-09, TWh by class and leg")
    print(t.sort_values("bilateral", ascending=False).round(3).to_string())
    f = phys.groupby(["group", "leg"]).mwh.sum().unstack(fill_value=0.0)
    print("\nbilateral share of each firm's output (generic units out):")
    print((f.bilateral / f.sum(axis=1)).round(3).to_string())
    print("\ngeneric units, TWh by firm and leg:")
    print((d[d.cls == "generic"].groupby(["group", "leg"]).mwh.sum().unstack(fill_value=0.0) / 1e6).round(2).to_string())
    cov_y = phys.groupby("year")[["costed_mwh", "mwh"]].sum()
    cov_y = cov_y.costed_mwh / cov_y.mwh
    cov_gy = phys.groupby(["group", "year"])[["costed_mwh", "mwh"]].sum()
    cov_gy = (cov_gy.costed_mwh / cov_gy.mwh).unstack("year")
    print("\ncosted share of output (generic units out), by year and by firm:")
    print(cov_y.round(3).to_frame("all").T.to_string())
    print(cov_gy.round(3).to_string())

    # 2. above cost
    c = d[d.cls.isin(COSTED)]
    ab = c.groupby(["group", "year", "cls", "leg"], as_index=False)[["costed_mwh", "above_mwh", "above_eur", "m"]].sum()
    ab["above_share"] = ab.above_mwh / ab.costed_mwh
    ab.to_csv(OUT["above_cost"], index=False)
    a = c.groupby(["cls", "leg"])[["costed_mwh", "above_mwh", "above_eur", "m"]].sum()
    a = pd.DataFrame({"costed_twh": a.costed_mwh / 1e6, "above_share": a.above_mwh / a.costed_mwh,
                      "above_meur": a.above_eur / 1e6, "margin_meur": a.m / 1e6})
    print("\n2. OUTPUT ABOVE COST (c > p), pooled 2019-01 → 2025-09")
    print(a.round(3).to_string())
    b = c.groupby(["group", "year", "leg"])[["above_eur"]].sum().unstack("leg", fill_value=0.0) / 1e6
    print("\nabove-cost €M by firm, year and leg:")
    print(b.round(1).to_string())

    # 3. hydro timing
    h = d[d.cls == "hydro_storage"]
    tim = h.groupby(["group", "year", "leg"], as_index=False)[["mwh", "pq", "pbarq"]].sum()
    tot = h.groupby(["group", "year"], as_index=False)[["mwh", "pq", "pbarq"]].sum().assign(leg="all")
    tim = pd.concat([tim, tot], ignore_index=True)
    tim["capture"] = tim.pq / tim.pbarq
    ud = pd.read_parquet(UNITDAY)
    ud["q"] = ud.q_auction + ud.q_bilateral
    ud = ud[ud.q >= 24].copy()
    ud["cap"], ud["bil"] = ud.pq / ud.pbarq, ud.q_bilateral / ud.q
    slopes = []
    for g, x in ud.groupby("group"):
        if (x.bil > 0).mean() < 0.05:
            continue
        b_, se_ = fit_daily(x, "cap", "bil", effects=("unit_month",))
        slopes.append({"group": g, "year": "all", "leg": "unitday_slope", "capture": b_, "se": se_,
                       "mwh": float(x.q.sum()), "bil_mean": float(x.bil.mean()), "unit_days": len(x)})
    tim = pd.concat([tim, pd.DataFrame(slopes)], ignore_index=True)
    tim.to_csv(OUT["hydro_timing"], index=False)
    print("\n3. STORAGE HYDRO TIMING: capture ratio Σpq / Σp̄q by firm, year and leg")
    print(tim[tim.leg != "unitday_slope"].pivot_table(index=["group", "year"], columns="leg", values="capture").round(3).to_string())
    print("\nwithin unit-days (unit × month effects, date clusters): capture on the bilateral share")
    print(pd.DataFrame(slopes).round(4).to_string(index=False) if slopes else "  no firm with bilateral hydro")

    # 4. generic units
    vol, twins = generic_units()
    vol.to_csv(OUT["generic"], index=False)
    print("\n4. GENERIC UNITS with > 0.1 TWh in a year, TWh by year and leg (bilateral; other = every other role)")
    print(vol.round(3).to_string(index=False))
    print("\nsale unit against its purchase twin, hour by hour:")
    print(twins.round(4).to_string(index=False))

    # 5. power for step 1b
    w = d[d.date.dt.dayofweek < 5]
    grid = pd.MultiIndex.from_product([FIRMS, sorted(w.date.unique())], names=["group", "date"])
    G = w.pivot_table(index=["group", "date"], columns="cls", values="mwh", aggfunc="sum", fill_value=0.0).reindex(grid, fill_value=0.0)
    Mk = w.pivot_table(index=["group", "date"], columns="cls", values="m", aggfunc="sum", fill_value=0.0).reindex(grid, fill_value=0.0)
    Ck = w.pivot_table(index=["group", "date"], columns="cls", values="costed_mwh", aggfunc="sum", fill_value=0.0).reindex(grid, fill_value=0.0)
    legs = w.pivot_table(index=["group", "date"], columns="leg", values="mwh", aggfunc="sum", fill_value=0.0).reindex(grid, fill_value=0.0)
    dose = pd.read_parquet(T / "holiday_dose.parquet")
    dose["date"] = pd.to_datetime(dose.date)
    Z = dose[dose.group.isin(FIRMS)].groupby(["group", "date"]).dose_mw.sum().reindex(grid, fill_value=0.0)
    pan = G.add_prefix("g_").join(legs.add_prefix("leg_"))
    pan["g_all"] = G.sum(axis=1)
    pan["g_physical"] = G.drop(columns=["generic"], errors="ignore").sum(axis=1)
    pan["M"], pan["Z"] = Mk.sum(axis=1), Z
    pan = pan.reset_index()
    zpos = Z.clip(lower=0)
    rows = []
    for col in [c for c in pan.columns if c.startswith(("g_", "leg_"))]:
        b_, se_ = fit_daily(pan, col, "Z")
        k = col[2:]
        mbar = float((zpos * Mk[k]).sum() / (zpos * Ck[k]).sum()) if k in COSTED and (zpos * Ck[k]).sum() > 0 else np.nan
        rows.append({"outcome": col, "b": b_, "se": se_, "mbar": mbar, "contrib": b_ * mbar if k in COSTED else np.nan})
    pw = pd.DataFrame(rows)
    A = float(pw.contrib.sum())
    se0 = se_null(pan, "M", "Z")
    pw = pd.concat([pw, pd.DataFrame([{"outcome": "A (€ per MWh of dose)", "b": A},
                                      {"outcome": "se(b) under b = 0", "b": se0},
                                      {"outcome": "MDE = 2.8 se", "b": Z80 * se0}])], ignore_index=True)
    pw.to_csv(OUT["power"], index=False)
    print(f"\n5. POWER FOR STEP 1b: weekday firm-days {len(pan):,}, dosed {(pan.Z > 0).sum():,}; MWh (or €) per MWh of dose")
    print(pw.round(3).to_string(index=False))

    stops = {f"costed share of output below 80% in a year (lowest {cov_y.min():.1%}, {cov_y.idxmin()})": cov_y.min() < 0.8,
             f"MDE {Z80 * se0:.2f} > |A| {abs(A):.2f} € per MWh of dose": Z80 * se0 > abs(A)}
    low = cov_gy.stack()
    low = low[low < 0.8]
    if len(low):
        print("  flag: firm-years below 80% costed: " + ", ".join(f"{g} {y} {v:.0%}" for (g, y), v in low.items()))
    for k, v in stops.items():
        print(f"  {'STOP' if v else 'ok  '} {k}")
    print(f"stop rule (step 1a): {'STOP' if any(stops.values()) else 'CONTINUE'}")
    return 0


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--describe", action="store_true")
    args = ap.parse_args()
    if args.build:
        return build()
    if args.describe:
        return describe()
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
