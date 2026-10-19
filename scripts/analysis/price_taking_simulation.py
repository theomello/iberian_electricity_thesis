#!/usr/bin/env python3
"""Do the step estimators find a negative β where there is none? Simulated price-takers.

    scripts/analysis/price_taking_sim.sh hydro SEED [FROM TO]   # step_engine.py --kind hydro --sim SEED, every month
    .venv/bin/python scripts/analysis/price_taking_simulation.py --kind hydro --seeds 1 [2 ...]
    (the same with thermal)

THE QUESTION. Leg B's at-cost estimate is β = −0.22 with unit × month effects (−0.37 with
unit × day), negative only within months and days and only for net sellers
(`leg_b_levels.py --atcost`); the thermal one is −0.27 (unit × month), −0.08 (unit × day)
(`step_estimator.py`). Rows are a firm's price points that set the price in at least one
resampled draw, and X̃ = Σn / Σ|RD′| is read in those draws. A high step sets the price
only in draws with high residual demand, where the firm's n is large, so the selection
and X̃ both depend on the step's own price. Could that alone produce the negative sign?

THE TEST. `step_engine.py --sim` moves every firm's hydro (thermal) steps to cost plus noise
drawn from the unit's own offers in the month, independent of the hour it lands in
(`step_engine.simulate`): price-taking offers, β = 0 within the month by construction, as
dispersed as the unit's own. Rivals' curves and the draws are as offered; the at-cost
instruments (Zb, Zc) and the reactor-outage doses do not depend on the firm's offer prices
and are reused. The rows, X̃, fixed effects and weights are the actual estimates' own.
A correct estimator returns β ≈ 0 wherever the fixed effects include unit × month; if it
returns the actual estimate's sign and size, that estimate is the estimator, not the firms.
The simulated offers keep each unit's actual monthly mean gap, so estimates with unit
effects only ("unit | …") are not a clean null and are flagged.

Writes outputs/tables/price_taking_simulation_{kind}.csv: every simulated estimate (one row
per seed) beside the actual estimate with the same label.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
import leg_b_levels as lb  # noqa: E402
import step_estimator as se  # noqa: E402
import step_estimator_hydro as sh  # noqa: E402

TABLES = ROOT / "outputs/tables"


def hydro(seed: int) -> list[dict]:
    d = lb.at_cost(lb.load(sim=seed))
    lb.describe(d)
    res = lb.at_cost_estimates(d)
    for fe in ("unit × day", "unit × month"):
        y = "price" if fe == "unit × day" else "gap30"
        res.append(sh.est(d, f"{fe} | reactor outages", lb.ZSETS["reactor outages"], y=y, fe=lb.FES[fe])
                   | {"fe": fe, "z": "reactor outages", "y": y})
    res.append(sh.est(d[~d.sim_out], "unit × month | Zb | simulated prices within the unit's offers", ["Zb"],
                      y="gap30", fe=lb.UNIT_MONTH) | {"fe": "unit × month", "z": "Zb", "y": "gap30"})
    return res


def thermal(seed: int) -> list[dict]:
    d = se.rows(sim=seed)
    d = d[d.m_n > 0].assign(r_n=np.nan, r_s=np.nan)      # the realised draw is not simulated
    d = se.at_cost(se.derive(se.instruments(d)))
    se.describe(d)
    p = d
    zb = ("Zb",)
    specs = [
        (p, "all, least squares", dict(zs=())),
        (p, "all, doses", {}),
        (p, "at cost, all", dict(zs=zb)),
        (p, "at cost (unit's own cost), all", dict(zs=("Zc",))),
        (p, "at cost + doses (overidentified)", dict(zs=("Zb", "dose_unpl", "dose_plan"))),
        (p, "at cost, fuel×date + hour effects", dict(zs=zb, fe="date")),
        (p, "at cost, unit × day effects", dict(zs=zb, fe="unitday")),
        (p[p.date < "2021-07-01"], "at cost, unit × day effects, 2019 – 2021 H1", dict(zs=zb, fe="unitday")),
        (p[p.date >= "2021-07-01"], "at cost, unit × day effects, 2021 H2 – 2023", dict(zs=zb, fe="unitday")),
        (p[p.date < "2021-07-01"], "at cost, 2019 – 2021 H1", dict(zs=zb)),
        (p[p.date >= "2021-07-01"], "at cost, 2021 H2 – 2023", dict(zs=zb)),
        (p[p.five], "at cost, five firms", dict(zs=zb)),
        (p[~p.five], "at cost, other owners", dict(zs=zb)),
        (p[p.fuel == "gas"], "at cost, gas", dict(zs=zb)),
        (p[~p.sim_out], "at cost, simulated prices within the unit's offers", dict(zs=zb)),
    ]
    return [se.est(s, "mk", "Xt", "m_n", label, **kw) for s, label, kw in specs]


SEL = {"hydro": "hcompcostprice", "thermal": "compcostprice"}
# columns given a slope per unit, and the period the slope may change with (None: whole sample).
# The last two were added after the first four failed the rule on the simulated offers (2026-10-08).
CONTROLS = {"none": ([], None), "level": (["P_rel"], None), "level, squared": (["P_rel", "P_rel2"], None),
            "level, spread": (["P_rel", "cp_sd"], None),
            "level, by year": (["P_rel"], "%Y"), "level, by month": (["P_rel"], "%Y%m")}


def selection(d: pd.DataFrame, kind: str, cost: str) -> pd.DataFrame:
    """The selection index of the correction: where the hour's prices sit above the unit's
    cost, read on the draws with the firm at cost (`step_engine.py --comp-price`), so the
    firm's own offers cannot enter it. P_rel = draws' mean price − cost; cp_sd their spread."""
    fs = sorted(se.CACHE.glob(f"{SEL[kind]}_2*.parquet"))
    c = pd.concat([pd.read_parquet(f, columns=["hid", "group", "cp_mean", "cp_sd"]) for f in fs], ignore_index=True)
    d = d.merge(c.drop_duplicates(["hid", "group"]), on=["hid", "group"], how="left")
    d["P_rel"] = d.cp_mean - d[cost]
    d["P_rel2"] = d.P_rel ** 2 / 100
    print(f"selection index: {len(fs)} months, defined on {d.P_rel.notna().mean():.3f} of rows", flush=True)
    return d


def hydro_corrected(seed: int, variants: list[str], only: list[str] | None = None) -> list[dict]:
    """The main hydro specifications with each selection control (a slope for every unit);
    seed 0 = the actual offers."""
    d = lb.load(sim=seed or None)
    d = lb.at_cost(d[d.m_n > 0])
    d = selection(d, "hydro", "lam30s").dropna(subset=["P_rel", "cp_sd"])
    um, ud = lb.UNIT_MONTH, lb.UNIT_DAY
    early, mid, late = d.date < "2021-07-01", (d.date >= "2021-07-01") & (d.date < "2024-01-01"), d.date >= "2024-01-01"
    specs = [
        (d, "unit × month | Zb", ["Zb"], um, "gap30", None),
        (d, "unit × day | Zb", ["Zb"], ud, "price", None),
        (d, "unit × month | reactor outages", lb.ZSETS["reactor outages"], um, "gap30", None),
        (d[early], "unit × month | Zb | 2019–2021H1", ["Zb"], um, "gap30", None),
        (d[mid], "unit × month | Zb | 2021H2–2023", ["Zb"], um, "gap30", None),
        (d[late], "unit × month | Zb | 2024 – 2025-09", ["Zb"], um, "gap30", None),
        (d, "unit × month | Zb⁺, Zb⁻ | two slopes", ["Zbp", "Zbm"], um, "gap30", ("Xp", "Xm")),
    ]
    specs = [sp for sp in specs if only is None or sp[1] in only]
    if not specs:
        raise SystemExit(f"--only matches no specification: {only}")
    res = []
    for variant in variants:
        sl, by = CONTROLS[variant]
        print(f"\nselection control: {variant}")
        for s, label, zs, fe, y, xs2 in specs:
            res.append(sh.est(s, f"{label} | sel: {variant}", zs, y=y, fe=fe, xs2=xs2, slopes=sl, slopes_by=by)
                       | {"base": label, "control": variant})
    return res


def thermal_corrected(seed: int, variants: list[str], only: list[str] | None = None) -> list[dict]:
    """The main thermal specifications with each selection control (a slope for every unit);
    seed 0 = the actual offers."""
    if seed:
        d = se.rows(sim=seed)
        d = d[d.m_n > 0].assign(r_n=np.nan, r_s=np.nan)
    else:
        d = pd.read_parquet(se.ROWS).drop(columns=se.INSTRUMENTS)
        d = d[d.m_n > 0]
    d = se.at_cost(se.derive(se.instruments(d)))
    d = selection(d, "thermal", "cost").dropna(subset=["P_rel", "cp_sd"])
    zb = ("Zb",)
    early = d.date < "2021-07-01"
    specs = [
        (d, "at cost, all", dict(zs=zb)),
        (d, "at cost, unit × day effects", dict(zs=zb, fe="unitday")),
        (d, "at cost, fuel×date + hour effects", dict(zs=zb, fe="date")),
        (d, "all, doses", {}),
        (d[early], "at cost, 2019 – 2021 H1", dict(zs=zb)),
        (d[~early], "at cost, 2021 H2 – 2023", dict(zs=zb)),
        (d[d.five], "at cost, five firms", dict(zs=zb)),
    ]
    specs = [sp for sp in specs if only is None or sp[1] in only]
    if not specs:
        raise SystemExit(f"--only matches no specification: {only}")
    res = []
    for variant in variants:
        sl, by = CONTROLS[variant]
        print(f"\nselection control: {variant}")
        for s, label, kw in specs:
            res.append(se.est(s, "mk", "Xt", "m_n", f"{label} | sel: {variant}", slopes=sl, slopes_by=by, **kw)
                       | {"base": label, "control": variant})
    return res


def actual(kind: str) -> pd.DataFrame:
    if kind == "hydro":
        a = pd.concat([pd.read_csv(TABLES / "leg_b_atcost_results.csv"), pd.read_csv(TABLES / "leg_b_levels_results.csv")])
        a = a.rename(columns={"b_iv_Xt": "b_iv", "se_iv_Xt": "se_iv", "F_Xt": "F", "b_ls_Xt": "b_ls"})
        cols = ["b_iv", "se_iv", "F", "b_ls", "ar_set", "b_iv_Xp", "b_iv_Xm"]
    else:
        a = pd.read_csv(TABLES / "step_estimator_results.csv").rename(columns={"b_ols": "b_ls"})
        cols = ["b_iv", "se_iv", "F", "b_ls", "ar_set"]
    a = a.drop_duplicates("sample", keep="first").set_index("sample")[cols]
    return a.add_prefix("actual_")


def intervals(ar: str) -> list[tuple[float, float]]:
    """An Anderson–Rubin set as printed ("[-0.05, 0.09]", "[-inf, 0.49] U [1.91, +inf]", "empty")."""
    if not isinstance(ar, str) or ar == "empty":
        return []
    return [tuple(float(v) for v in part.strip(" []").split(",")) for part in ar.split(" U ")]


DELTA = 0.1     # largest β still called price-taking (fixed by the user 2026-10-08, before the test was read)


def reading(t: pd.DataFrame, control: str = "level", by: tuple = ("base",)) -> pd.DataFrame:
    """The reading rule fixed before the actual offers were run (notes §5): the null band is
    [min, max] of the simulated estimates with the same control; the actual offers differ from
    price-takers only if the actual AR set does not touch it.
    Equivalence (notes §7): β's set allowing any bias in the null band is [lo − null_hi,
    hi − null_lo]; price-taking is accepted when its upper end is below DELTA (one-sided:
    market power means β > 0; the 95% set's upper end makes it a 2.5% test)."""
    by = list(by)
    c = t[t.control == control]
    sim = c[c.seed > 0].groupby(by).b_iv.agg(["min", "max", "mean"])
    act = c[c.seed == 0].set_index(by)[["b_iv", "ar_set"]]
    r = act.join(sim, how="inner")
    r["differs"] = [not any(lo <= hi_band and hi >= lo_band for lo, hi in intervals(ar))
                    if isinstance(ar, str) else None
                    for ar, lo_band, hi_band in zip(r.ar_set, r["min"], r["max"])]
    r["actual_minus_null"] = r.b_iv - r["mean"]
    one = [iv[0] if len(iv) == 1 else (np.nan, np.nan) for iv in map(intervals, r.ar_set)]
    r["beta_lo_adj"] = [lo - h for (lo, _), h in zip(one, r["max"])]
    r["beta_hi_adj"] = [hi - l for (_, hi), l in zip(one, r["min"])]
    r["price_taking_within_delta"] = [h < DELTA if np.isfinite(h) else None for h in r.beta_hi_adj]
    return r.rename(columns={"b_iv": "actual", "min": "null_lo", "max": "null_hi", "mean": "null_mean"})


def hydro_level_rows(seed: int | str) -> tuple[pd.DataFrame, dict]:
    """The rows of the hydro splits (with their selection index) and the three periods."""
    d = lb.load(sim=seed or None)
    d = lb.at_cost(d[d.m_n > 0])
    d = selection(d, "hydro", "lam30s").dropna(subset=["P_rel", "cp_sd"])
    periods = {"unit × month | Zb": d.date.notna(), "unit × month | Zb | 2019–2021H1": d.date < "2021-07-01",
               "unit × month | Zb | 2024 – 2025-09": d.date >= "2024-01-01"}
    return d, periods


def hydro_firms(seed: int, only: list[str] | None = None) -> list[dict]:
    """Which firms carry the hydro departures: the pooled within-month specification and the
    two departing periods without each firm in turn, control `level`; seed 0 = the actual offers.
    Not firm by firm: Zb is one value per firm and hour, so within one firm the class × hour
    effects absorb it (first-stage F 0, tried 2026-10-08); β comes from comparing firms in the
    same hour."""
    d, periods = hydro_level_rows(seed)
    sl, by = CONTROLS["level"]
    n = d.group.value_counts()
    print("rows by firm:", n.to_dict(), flush=True)
    res = []
    for g in sorted(n[n >= 5000].index):          # the rest hold under 1% of the rows
        for label, keep in periods.items():
            if only and label not in only:
                continue
            s = d[keep & (d.group != g)]
            res.append(sh.est(s, f"{label} | without {g}", ["Zb"], y="gap30", fe=lb.UNIT_MONTH, slopes=sl, slopes_by=by)
                       | {"base": label, "without": g, "control": "level"})
    return res


# Six-hour blocks of the Madrid clock hour a period starts in (fixed 2026-10-08, before the split was read)
HOUR_BLOCKS = {"00–05 h": (0, 6), "06–11 h": (6, 12), "12–17 h": (12, 18), "18–23 h": (18, 24)}


def hydro_hours(seed: int, only: list[str] | None = None) -> list[dict]:
    """Where in the day the hydro departures sit: the same three specifications within each
    six-hour block, control `level`; seed 0 = the actual offers. Within a block the unit ×
    month effect is the unit's own mean over those hours, so a firm-specific water value that
    differs between blocks (water kept for the evening) goes into it; β still compares firms in
    the same hour."""
    d, periods = hydro_level_rows(seed)
    sl, by = CONTROLS["level"]
    hour = d.utc.dt.tz_convert("Europe/Madrid").dt.hour
    print("rows by block:", {b: int(hour.between(lo, hi - 1).sum()) for b, (lo, hi) in HOUR_BLOCKS.items()}, flush=True)
    res = []
    for b, (lo, hi) in HOUR_BLOCKS.items():
        for label, keep in periods.items():
            if only and label not in only:
                continue
            s = d[keep & hour.between(lo, hi - 1)]
            res.append(sh.est(s, f"{label} | {b}", ["Zb"], y="gap30", fe=lb.UNIT_MONTH, slopes=sl, slopes_by=by)
                       | {"base": label, "hours": b, "control": "level"})
    return res


# Near a reservoir bound: the unit's fill in its own bottom or top FILL_TAIL over the estimation
# window (fixed 2026-10-09, before the split was read)
FILL_TAIL = 0.10


def hydro_bounds(seed: int, only: list[str] | None = None) -> list[dict]:
    """Reservoir bounds: λ* moves with the fill but not with its bounds (a full reservoir must
    spill, an empty one must ration). Units with a fill series only (MITECO basin, SNIRH own
    reservoirs); a unit-day is near a bound when its fill is in the unit's own bottom or top
    decile over 2019-01 → 2025-09, read from the water-value table so that actual and simulated
    rows split alike. The same three specifications on all of these rows, on the interior days
    and near the bounds; control `level`; seed 0 = the actual offers."""
    d, periods = hydro_level_rows(seed)
    sl, by = CONTROLS["level"]
    w = pd.read_parquet(lb.WV, columns=["unit", "date", "fill"])
    w = w[(pd.to_datetime(w.date) >= "2019-01-01") & (pd.to_datetime(w.date) < "2025-10-01")]
    q = w.groupby("unit").fill.quantile([FILL_TAIL, 1 - FILL_TAIL]).unstack()
    lo, hi = d.unit.map(q[FILL_TAIL]), d.unit.map(q[1 - FILL_TAIL])
    has = (d.storage != "none") & d.fill.notna() & lo.notna()
    near = has & ((d.fill <= lo) | (d.fill >= hi))
    subsets = {"with fill": has, "interior": has & ~near, "near a bound": near}
    print("rows:", {k: int(v.sum()) for k, v in subsets.items()}, f"of {len(d):,};",
          f"near full {(has & (d.fill >= hi)).sum():,}, near empty {(has & (d.fill <= lo)).sum():,}", flush=True)
    res = []
    for b, sub in subsets.items():
        for label, keep in periods.items():
            if only and label not in only:
                continue
            s = d[keep & sub]
            res.append(sh.est(s, f"{label} | {b}", ["Zb"], y="gap30", fe=lb.UNIT_MONTH, slopes=sl, slopes_by=by)
                       | {"base": label, "days": b, "control": "level"})
    return res


# Iberdrola's Tâmega scheme is classed as storage hydro, but Gouvães (pumped, ~880 of its 1,158 MW)
# dominates it; in the main pumped split it counts as pumped (fixed 2026-10-09, before the split was read)
PUMPED_TOO = ("TAMEGA",)


def hydro_pumped(seed: int, only: list[str] | None = None) -> list[dict]:
    """Pumped against conventional storage: for pumped storage λ* is an arbitrage value and its
    bounds are the upper reservoir's own daily or weekly cycle, which no public series gives.
    The same three specifications on each kind, control `level`; seed 0 = the actual offers.
    Main: Tâmega counted as pumped (its class moved too, so that its steps meet the other
    pumped units' in the class × hour effects); check: the classes as coded."""
    d, periods = hydro_level_rows(seed)
    sl, by = CONTROLS["level"]
    moved = d.assign(cls=d.cls.where(~d.unit.isin(PUMPED_TOO), "pumped"))
    kinds = {"pumped (Tâmega in)": (moved, moved.cls == "pumped"), "conventional (Tâmega out)": (moved, moved.cls == "hydro"),
             "pumped (as coded)": (d, d.cls == "pumped"), "conventional (as coded)": (d, d.cls == "hydro")}
    print("rows:", {k: int(v.sum()) for k, (_, v) in kinds.items()}, flush=True)
    res = []
    for k, (dd, sub) in kinds.items():
        for label, keep in periods.items():
            if only and label not in only:
                continue
            s = dd[keep & sub]
            res.append(sh.est(s, f"{label} | {k}", ["Zb"], y="gap30", fe=lb.UNIT_MONTH, slopes=sl, slopes_by=by)
                       | {"base": label, "kind": k, "control": "level"})
    return res


# split → (estimates of one seed, the column naming the subsample, cache part name, table name)
SPLITS = {"firms": (hydro_firms, "without", "dropfirm", "without_firm"),
          "hours": (hydro_hours, "hours", "hourblock", "by_hour"),
          "bounds": (hydro_bounds, "days", "bounds", "by_fill"),
          "pumped": (hydro_pumped, "kind", "pumped", "by_kind")}


def split(name: str, seeds: list[int], only: list[str] | None, combine_only: bool) -> int:
    """Each seed's part goes to the cache (seeds can run in parallel); the parts on disk are then
    combined into the table and read subsample by subsample."""
    fn, col, part, table = SPLITS[name]
    for seed in [] if combine_only else seeds:
        print(f"\n=== {'ACTUAL OFFERS' if seed == 0 else f'SEED {seed}: simulated price-takers'} ===", flush=True)
        p = pd.DataFrame([r | {"seed": seed} for r in fn(seed, only)])
        p.rename(columns={"b_iv_Xt": "b_iv", "se_iv_Xt": "se_iv", "F_Xt": "F", "b_ls_Xt": "b_ls"}).to_csv(
            se.CACHE / f"price_taking_{part}_s{seed}.csv", index=False)
    parts = sorted(se.CACHE.glob(f"price_taking_{part}_s*.csv"))
    t = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True)
    t.to_csv(TABLES / f"price_taking_simulation_hydro_{table}.csv", index=False)
    print(f"\ncombined {len(parts)} seed parts: {sorted(t.seed.unique())}")
    if (t.seed == 0).any() and (t.seed > 0).any():
        r = reading(t[t.b_iv.notna()], by=("base", col))
        r.to_csv(TABLES / f"price_taking_simulation_hydro_{table}_reading.csv")
        pd.set_option("display.width", 250)
        print(r.round(3).to_string())
    return 0


def wquant(x: pd.Series, w: pd.Series, q: float) -> float:
    o = np.argsort(x.to_numpy())
    c = np.cumsum(w.to_numpy()[o])
    return float(x.to_numpy()[o][np.searchsorted(c, q * c[-1])])


SIZE_FIRMS = ("IBERDROLA", "ENDESA", "EDP")


def size() -> int:
    """The departures in €/MWh. In the model a step's markup over its water value is β·X̃
    (X̃ = n / |RD′| over the draws in which it sets the price, €/MWh: the Cournot markup), so
    with the bias-adjusted β of each departing period (actual minus the price-takers' mean;
    range [AR low − null max, AR high − null min], the reading table) the implied markup of a
    price-setting step is β·X̃. Rows and weights are the estimate's own (control `level`):
    each step weighted by the draws in which it sets the price.
    Price effect: per hour, Σ over a firm's steps of (draws it sets the price / draws) · β·X̃,
    averaged over every hour of the period (0 where the firm's hydro never sets it). An upper
    bound: a step priced Δ higher raises the price by Δ only if no rival step lies within Δ.
    Only the part of the markup that rises with the firm's stake; its level within the month
    is in the unit × month effect and is not counted."""
    r = pd.read_csv(TABLES / "price_taking_simulation_hydro_reading.csv").set_index("base")
    d, periods = hydro_level_rows(0)
    d = d.dropna(subset=["Xt", "gap30", "Zb"])
    d = d[d.m_n > 0]
    hours = pd.concat([pd.read_parquet(f, columns=["hid", "utc"]) for f in sorted(se.CACHE.glob("hours_2*.parquet"))])
    hours["date"] = hours.utc.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize()
    rows = []
    for label in ("unit × month | Zb | 2019–2021H1", "unit × month | Zb | 2024 – 2025-09"):
        b, lo, hi = r.loc[label, ["actual_minus_null", "beta_lo_adj", "beta_hi_adj"]]
        keep = periods[label]
        p = d[keep.reindex(d.index)]
        hk = hours[(hours.date >= p.date.min()) & (hours.date <= p.date.max())].hid.nunique()
        for g in ("all",) + SIZE_FIRMS + ("others",):
            s = p if g == "all" else p[~p.group.isin(SIZE_FIRMS)] if g == "others" else p[p.group == g]
            if s.empty:
                continue
            w = s.m_n.astype(float)
            pos = s.Xt > 0
            xp = s.Xt[pos]
            share = (s.m_n / s.n_draws).sum() / hk         # hours in which the firm's hydro sets the price
            eff = (s.m_n / s.n_draws * s.Xt).sum() / hk     # Σ P(sets p)·X̃ per hour of the period
            rows.append({"period": label.split("| ")[-1], "firm": g, "rows": len(s), "units": s.unit.nunique(),
                         "beta": b, "beta_lo": lo, "beta_hi": hi,
                         "share_net_seller": np.average(pos, weights=w),
                         "x_mean": np.average(s.Xt, weights=w),
                         "x_seller_mean": np.average(xp, weights=w[pos]) if pos.any() else np.nan,
                         "x_seller_median": wquant(xp, w[pos], 0.5) if pos.any() else np.nan,
                         "x_seller_p90": wquant(xp, w[pos], 0.9) if pos.any() else np.nan,
                         "x_buyer_mean": np.average(s.Xt[~pos], weights=w[~pos]) if (~pos).any() else np.nan,
                         "gap_mean": np.average(s.gap30, weights=w),
                         "sets_price_share_of_hours": share, "x_per_hour": eff})
    t = pd.DataFrame(rows)
    for c in ("x_mean", "x_seller_mean", "x_seller_median", "x_seller_p90", "x_buyer_mean", "x_per_hour"):
        m = c.replace("x_", "markup_")
        t[m], t[m + "_lo"], t[m + "_hi"] = t.beta * t[c], t.beta_lo * t[c], t.beta_hi * t[c]
    t.to_csv(TABLES / "price_taking_simulation_hydro_size.csv", index=False)
    pd.set_option("display.width", 250)
    print("\nHYDRO DEPARTURES IN €/MWh (β bias-adjusted; X̃ weighted by draws setting the price):")
    show = ["period", "firm", "rows", "beta", "share_net_seller", "x_seller_mean", "x_seller_median", "x_seller_p90",
            "markup_seller_mean", "markup_seller_mean_lo", "markup_seller_mean_hi", "x_buyer_mean", "markup_buyer_mean",
            "markup_mean", "gap_mean",
            "sets_price_share_of_hours", "markup_per_hour", "markup_per_hour_lo", "markup_per_hour_hi"]
    print(t[show].round(3).to_string(index=False))
    return 0


PLANTED_SPECS = ("unit × month | Zb | 2019–2021H1", "unit × month | Zb | 2024 – 2025-09")


def planted(seed: int) -> int:
    """Price-takers whose water value is m × λ* per firm (`step_engine.py --sim SEED --sim-scale`,
    hsimw<SEED>_*, simulated on the two departing periods only), estimated with λ* as the cost.
    Same random draws as seed SEED, so the difference from it is the planted water value alone.
    Could firms that simply value water differently make β look positive?"""
    rows = hydro_corrected(f"w{seed}", ["none", "level"], list(PLANTED_SPECS))
    t = pd.DataFrame([r | {"seed": seed, "planted": "firm water value m × λ*"} for r in rows]).rename(
        columns={"b_iv_Xt": "b_iv", "se_iv_Xt": "se_iv", "F_Xt": "F", "b_ls_Xt": "b_ls"})
    t.to_csv(TABLES / "price_taking_simulation_hydro_planted.csv", index=False)
    c = pd.read_csv(TABLES / "price_taking_simulation_hydro_corrected.csv")
    ref = c[c.base.isin(PLANTED_SPECS) & c.control.isin(["none", "level"])]
    show = pd.concat([ref.assign(planted=np.where(ref.seed == 0, "actual offers", "β = 0 at λ*")), t])
    pd.set_option("display.width", 250)
    print("\nPLANTED WATER VALUE against the plain null (same seed) and the actual offers:")
    print(show.sort_values(["base", "control", "planted", "seed"])[
        ["base", "control", "planted", "seed", "n", "b_iv", "se_iv", "F", "ar_set"]].round(3).to_string(index=False))
    return 0


def corrected(kind: str, seeds: list[int], variants: list[str], only: list[str] | None = None) -> int:
    out = TABLES / f"price_taking_simulation_{kind}_corrected.csv"
    res = []
    for seed in seeds:
        print(f"\n=== {'ACTUAL OFFERS' if seed == 0 else f'SEED {seed}: simulated price-takers'} ===", flush=True)
        rows = hydro_corrected(seed, variants, only) if kind == "hydro" else thermal_corrected(seed, variants, only)
        res += [r | {"seed": seed} for r in rows]
    t = pd.DataFrame(res).rename(columns={"b_iv_Xt": "b_iv", "se_iv_Xt": "se_iv", "F_Xt": "F", "b_ls_Xt": "b_ls",
                                          "b_ols": "b_ls", "se_ols": "se_ls"})
    if out.exists():                            # keep other seeds and controls already on disk
        old = pd.read_csv(out)
        t = pd.concat([old[~(old.seed.isin(seeds) & old.control.isin(variants) & old.base.isin(t.base))], t],
                      ignore_index=True)
    t.to_csv(out, index=False)
    pd.set_option("display.width", 250)
    cols = [c for c in ["base", "control", "seed", "n", "b_iv", "se_iv", "F", "ar_set", "b_iv_Xp", "b_iv_Xm"] if c in t]
    print("\nSELECTION CONTROLS (seed 0 = actual offers):")
    print(t.sort_values(["base", "control", "seed"])[cols].round(3).to_string(index=False))
    if (t.seed == 0).any() and (t.seed > 0).any():
        r = reading(t)
        r.to_csv(TABLES / f"price_taking_simulation_{kind}_reading.csv")
        print("\nREADING RULE (control: level; null band = simulated min–max; differs = AR set misses it):")
        print(r.round(3).to_string())
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--kind", choices=["hydro", "thermal"], required=True)
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--corrected", action="store_true",
                    help="the main specifications with each selection control (seed 0: the actual offers)")
    ap.add_argument("--controls", nargs="+", choices=list(CONTROLS), default=list(CONTROLS),
                    help="with --corrected: the selection controls to run (default all)")
    ap.add_argument("--only", nargs="+", help="with --corrected: run only these specifications (base labels), "
                    "e.g. for a seed simulated on part of the months")
    ap.add_argument("--firms", action="store_true", help="hydro only: the departures without each firm in turn "
                    "(control level)")
    ap.add_argument("--hours", action="store_true", help="hydro only: the departures within each six-hour block "
                    "(control level)")
    ap.add_argument("--bounds", action="store_true", help="hydro only: the departures on interior days and near "
                    "the reservoir bounds (control level)")
    ap.add_argument("--pumped", action="store_true", help="hydro only: the departures in pumped and in conventional "
                    "storage (control level)")
    ap.add_argument("--combine", action="store_true", help="with --firms, --hours, --bounds or --pumped: only combine "
                    "the seed parts on disk")
    ap.add_argument("--planted", action="store_true",
                    help="hydro only: price-takers at a firm-specific water value (hsimw<SEED>), the two periods")
    ap.add_argument("--size", action="store_true", help="hydro only: the departures in €/MWh (actual offers; "
                    "reads the reading table)")
    args = ap.parse_args()
    if args.size:
        return size()
    if args.planted:
        return planted(args.seeds[0])
    for name in SPLITS:
        if getattr(args, name):
            return split(name, args.seeds, args.only, args.combine)
    if args.corrected:
        return corrected(args.kind, args.seeds, args.controls, args.only)
    out = TABLES / f"price_taking_simulation_{args.kind}.csv"
    res = []
    for seed in args.seeds:
        print(f"\n=== SEED {seed}: simulated price-takers (β = 0 within the month) ===", flush=True)
        rows = hydro(seed) if args.kind == "hydro" else thermal(seed)
        res += [r | {"seed": seed} for r in rows]
    t = pd.DataFrame(res).rename(columns={"b_iv_Xt": "b_iv", "se_iv_Xt": "se_iv", "F_Xt": "F", "b_ls_Xt": "b_ls",
                                          "b_ols": "b_ls", "se_ols": "se_ls"})
    t["clean_null"] = ~t["sample"].str.startswith("unit |")
    if out.exists():                            # keep other seeds already on disk
        old = pd.read_csv(out)
        t = pd.concat([old[~old.seed.isin(args.seeds)], t], ignore_index=True)
    t = t.drop(columns=[c for c in t if c.startswith("actual_")]).join(actual(args.kind), on="sample")
    t.to_csv(out, index=False)
    pd.set_option("display.width", 250)
    show = ["sample", "seed", "n", "b_iv", "se_iv", "F", "ar_set", "b_ls", "actual_b_iv", "actual_ar_set", "actual_b_ls"]
    print("\nSIMULATED (β = 0) AGAINST ACTUAL:")
    print(t[[c for c in show if c in t]].round(3).to_string(index=False))
    if "b_iv_Xp" in t:
        two = t[t["sample"].str.contains("two slopes")]
        print(two[["sample", "seed", "b_iv_Xp", "b_iv_Xm", "actual_b_iv_Xp", "actual_b_iv_Xm"]].round(3).to_string(index=False))
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
