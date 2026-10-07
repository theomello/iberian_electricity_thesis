#!/usr/bin/env python3
"""Leg B in levels: the price of hydro offer steps against the price-taking water value λ*.

    .venv/bin/python scripts/build/build_water_value_forward.py      # λ*, with storage
    .venv/bin/python scripts/analysis/step_estimator_hydro.py         # rows (step_estimator_hydro_rows)
    .venv/bin/python scripts/analysis/leg_b_levels.py

Framework spec §2.2, leg B. A storage unit's cost is its water value λ, so the step
condition of `step_estimator_hydro.py` is

    b_k − λ_ud = β · X̃_k

There λ_ud was removed by unit × day effects, which also removes the across-day margin:
a firm that holds water back raises the level of λ for the whole day, and unit × day
effects absorb exactly that (leg A). Here λ_ud is replaced by the price-taking benchmark
λ*30s(u, d) of `build_water_value_forward.py` (forward prices, last year's hourly shape,
the unit's capacity factor adjusted for its reservoir fill), so the day's level stays in
the regression:

    b_k − λ*_ud = β · X̃_k + e,     e = (λ_ud − λ*_ud) + error

β now uses how a unit's step prices, measured from the benchmark, move across days as
well as hours with the firm's X̃. The benchmark's own error (option value, risk premium,
a wrong capacity factor) sits in e, so instruments must not move it: reactor outages
(multi-week, known at D−2 and so partly in the forward too), regional wind deviation
and the firm × forecast instruments, all known when offers close.

FIXED EFFECTS, from the leg A reference to pure levels:
  unit × day        leg A, as `step_estimator_hydro.py` §6: λ* cancels
  unit × month      days within a month: the day's level, slow withholding absorbed
  unit              every day: slow withholding kept
  each with class × hour-of-sample (common shocks: every unit's λ* moves with the same
  forward) and class × ladder position; and "unit, no hour effects", class × clock hour
  instead, in which λ* alone carries the common cost.
Flat unit-days (one curve for all 24 hours: EDP's cascades) are KEPT: their choice is the
day's level, which is leg B's margin.

THE PAPER'S METHOD ON THE SAME DATA (Arzhintar, Leslie, Neill & Wyrwoll 2025, SSRN
5736763). They infer the water value from the offers: on intervals where the scheme's
own unit sets the price, λ̂ = p − n / |RD′| (the static first-order condition with full
market power, β = 1, contracts estimated), then fit λ̂ by OLS on the forward price,
reservoir volume and snow. Here: steps that set the realised price (r_event = 1),
λ̂₁ = p − X_realised, λ̂₀ = p (price-taking), each fitted on the D−2 forward and the fill
anomaly with unit effects. Compared with λ*.

Writes outputs/tables/leg_b_levels_results.csv and leg_b_paper_method.csv. `--checks` reruns
only the checks, `--paper` only the paper's method.

AT-COST INSTRUMENT (`--atcost`, after `step_engine.py --kind hydro --comp`): X evaluated on
the same resampled draws with the firm's hydro steps moved to λ*30s, as for thermal plant
(`rq-step-estimator.md` §7; Berry, Levinsohn & Pakes 1999 approximate optimal
instruments). Zb reads X at the day's median λ* of the hydro class, so a unit's own
benchmark error cannot enter it; Zc at the unit's own λ*. Writes leg_b_atcost_results.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from midday_hydro_iv import cluster_meat  # noqa: E402
from regional_wind_offer_test import FORECASTS  # noqa: E402
from step_engine import NEAR  # noqa: E402
from step_estimator import INSTRUMENTS, wdemean  # noqa: E402
import step_estimator_hydro as sh  # noqa: E402

TABLES = ROOT / "outputs/tables"
OUT = TABLES / "leg_b_levels_results.csv"
OUT_PAPER = TABLES / "leg_b_paper_method.csv"
OUT_ATCOST = TABLES / "leg_b_atcost_results.csv"
WV = TABLES / "water_value_forward.parquet"
SIX = ["EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL", "MOVHERA"]


def codes(*cols):
    def f(s: pd.DataFrame) -> list[np.ndarray]:
        return [pd.factorize(c(s))[0] for c in cols]
    return f


UNIT_DAY = codes(lambda s: s.unit + s.date.dt.strftime("%Y%m%d"), lambda s: s.cls + s.hid.astype(str),
                 lambda s: s.cls + s.pos.astype(str))
UNIT_MONTH = codes(lambda s: s.unit + s.date.dt.strftime("%Y%m"), lambda s: s.cls + s.hid.astype(str),
                   lambda s: s.cls + s.pos.astype(str))
UNIT = codes(lambda s: s.unit, lambda s: s.cls + s.hid.astype(str), lambda s: s.cls + s.pos.astype(str))
UNIT_CLOCK = codes(lambda s: s.unit, lambda s: s.cls + s.period.astype(str), lambda s: s.cls + s.pos.astype(str))
FES = {"unit × day": UNIT_DAY, "unit × month": UNIT_MONTH, "unit": UNIT, "unit, no hour effects": UNIT_CLOCK}
ZSETS = {"firm × forecast": "firm forecasts", "reactor outages": ["dose_unpl", "dose_plan"],
         "regional wind": ["Wdev_fc"], "outages + wind": ["dose_unpl", "dose_plan", "Wdev_fc"]}


def load() -> pd.DataFrame:
    d = sh.add_instruments(pd.read_parquet(sh.ROWS).drop(columns=INSTRUMENTS + list(FORECASTS)))
    d = sh.derive(d)
    w = pd.read_parquet(WV, columns=["unit", "date", "lam30", "lam30s", "lam90s", "fwd", "fill", "fill_anom",
                                     "storage", "cf_s"])
    w["date"] = pd.to_datetime(w.date)
    d = d.merge(w, on=["unit", "date"], how="inner")
    d["gap30"] = d.price - d.lam30s
    d["gap90"] = d.price - d.lam90s
    d["gap30_nostore"] = d.price - d.lam30
    print(f"hydro steps with λ*: {len(d):,}, setting the price in a draw {(d.m_n > 0).sum():,} ({d.unit.nunique()} units); "
          f"with storage {(d.storage != 'none').mean():.3f}; flat unit-days {d.flat.mean():.3f}")
    return d


def describe(d: pd.DataFrame) -> None:
    g = d[d.m_n > 0].groupby("group").apply(lambda x: pd.Series({
        "steps": len(x), "units": x.unit.nunique(), "flat": x.flat.mean(),
        "price": np.average(x.price, weights=x.m_n), "lam30s": np.average(x.lam30s, weights=x.m_n),
        "gap": np.average(x.gap30, weights=x.m_n), "X_tilde": np.average(x.Xt.fillna(0), weights=x.m_n)}),
        include_groups=False)
    print("\nprice-setting hydro steps, weighted by marginal draws:")
    print(g.sort_values("steps", ascending=False).round(2).to_string())


def levels(d: pd.DataFrame) -> list[dict]:
    res = []
    for fe_name, fe in FES.items():
        y = "price" if fe_name == "unit × day" else "gap30"
        print(f"\n{fe_name}: {y} on X̃")
        for z_name, z in ZSETS.items():
            res.append(sh.est(d, f"{fe_name} | {z_name}", z, y=y, fe=fe) | {"fe": fe_name, "z": z_name, "y": y})
    return res


def checks(d: pd.DataFrame) -> list[dict]:
    """Unit × month effects, with the two instrument sets whose exclusion is plausible
    (the firm × forecast instruments fail the overidentification test in every sample)."""
    res = []
    um = UNIT_MONTH
    for z_name in ("reactor outages", "outages + wind"):
        z = ZSETS[z_name]
        print(f"\nchecks, unit × month, {z_name}:")
        for label, s, y in [
            ("λ*90 instead of λ*30", d, "gap90"),
            ("λ* without storage", d, "gap30_nostore"),
            ("units with a storage series", d[d.storage != "none"], "gap30"),
            ("flat unit-days left out", d[~d.flat], "gap30"),
            ("storage hydro only (no pumped)", d[d.cls == "hydro"], "gap30"),
            ("six owners only", d[d.group.isin(SIX)], "gap30"),
            ("2019–2023", d[d.date < "2024-01-01"], "gap30"),
            ("2024 – 2025-09", d[d.date >= "2024-01-01"], "gap30"),
        ]:
            res.append(sh.est(s, f"unit × month | {z_name} | {label}", z, y=y, fe=um)
                       | {"fe": "unit × month", "z": z_name, "y": y})
    print("\nby sign of X̃ (unit × month, outages + wind):")
    res.append(sh.est(d, "unit × month | outages + wind | two slopes", ZSETS["outages + wind"],
                      xs2=("Xp", "Xm"), y="gap30", fe=um) | {"fe": "unit × month", "z": "outages + wind", "y": "gap30"})
    return res


def at_cost(d: pd.DataFrame) -> pd.DataFrame:
    """Zb, Zc: X on the curve with the firm's hydro steps at λ*30s (`step_engine.py --kind
    hydro --comp`), over the NEAR draws nearest the day's median λ* of the class (Zb) or the
    unit's own λ* (Zc); NaN below the slope floor."""
    cols = ["hid", "group", "unit", "kn_sn", "kn_s", "kb_sn", "kb_s"]
    fs = sorted(sh.CACHE.glob("hcompcost_2*.parquet"))
    c = pd.concat([pd.read_parquet(f, columns=cols) for f in fs], ignore_index=True)
    d = d.merge(c.drop_duplicates(["hid", "group", "unit"]), on=["hid", "group", "unit"], how="left")
    d["Zc"] = np.where(d.kn_s / NEAR >= sh.FLOOR, d.kn_sn / d.kn_s.where(d.kn_s > 0), np.nan)
    d["Zb"] = np.where(d.kb_s / NEAR >= sh.FLOOR, d.kb_sn / d.kb_s.where(d.kb_s > 0), np.nan)
    d["Zbp"], d["Zbm"] = d.Zb.clip(lower=0), d.Zb.clip(upper=0)
    p = d[d.m_n > 0]
    print(f"at-cost instrument: {len(fs)} months; joined on {p.kn_s.notna().mean():.3f} of price-setting rows, "
          f"Zb defined on {p.Zb.notna().mean():.3f}; corr(X̃, Zb) {p[['Xt', 'Zb']].corr().iat[0, 1]:.2f}")
    return d


def at_cost_estimates(d: pd.DataFrame) -> list[dict]:
    res = []
    print("\nAT-COST INSTRUMENT (X̃ instrumented by its value with the firm's hydro at λ*):")
    for fe_name in ("unit × day", "unit × month", "unit"):
        y = "price" if fe_name == "unit × day" else "gap30"
        for z_name, z in [("at cost, day median λ* (Zb)", ["Zb"]), ("at cost, own λ* (Zc)", ["Zc"]),
                          ("Zb + outages", ["Zb", "dose_unpl", "dose_plan"])]:
            res.append(sh.est(d, f"{fe_name} | {z_name}", z, y=y, fe=FES[fe_name])
                       | {"fe": fe_name, "z": z_name, "y": y})
    um = UNIT_MONTH
    for label, s in [("units with a storage series", d[d.storage != "none"]), ("flat unit-days left out", d[~d.flat]),
                     ("storage hydro only (no pumped)", d[d.cls == "hydro"]), ("six owners only", d[d.group.isin(SIX)]),
                     ("2019–2021H1", d[d.date < "2021-07-01"]), ("2021H2–2023", d[(d.date >= "2021-07-01") & (d.date < "2024-01-01")]),
                     ("2024 – 2025-09", d[d.date >= "2024-01-01"])]:
        res.append(sh.est(s, f"unit × month | Zb | {label}", ["Zb"], y="gap30", fe=um)
                   | {"fe": "unit × month", "z": "Zb", "y": "gap30"})
    res.append(sh.est(d[d.date >= "2024-01-01"], "unit × day | Zb | 2024 – 2025-09", ["Zb"], y="price", fe=UNIT_DAY)
               | {"fe": "unit × day", "z": "Zb", "y": "price"})
    res.append(sh.est(d, "unit × month | Zb⁺, Zb⁻ | two slopes", ["Zbp", "Zbm"], xs2=("Xp", "Xm"), y="gap30", fe=um)
               | {"fe": "unit × month", "z": "Zbp, Zbm", "y": "gap30"})
    res.append(sh.est(d[d.date >= "2024-01-01"], "unit × month | Zb⁺, Zb⁻ | two slopes, 2024 – 2025-09",
                      ["Zbp", "Zbm"], xs2=("Xp", "Xm"), y="gap30", fe=um)
               | {"fe": "unit × month", "z": "Zbp, Zbm", "y": "gap30"})
    return res


def ols(s: pd.DataFrame, y: str, xs: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """OLS with unit effects, week clusters."""
    M = wdemean(s[[y, *xs]].to_numpy(float), [pd.factorize(s.unit)[0]], np.ones(len(s)))
    Y, X = M[:, 0], M[:, 1:]
    inv = np.linalg.inv(X.T @ X)
    b = inv @ X.T @ Y
    V = inv @ cluster_meat(X, Y - X @ b, s.date.dt.strftime("%G%V").to_numpy()) @ inv
    return b, np.sqrt(np.diag(V))


def paper_method(d: pd.DataFrame) -> pd.DataFrame:
    """λ̂ inferred from the offers as in Arzhintar et al.: realised price-setting steps,
    λ̂₁ = p − n/|RD′| (β = 1), λ̂₀ = p (β = 0); against λ*30s; and fitted on the forward
    price and the fill anomaly with unit effects."""
    r = d[(d.r_event == 1) & (d.cls == "hydro") & (d.r_s >= sh.FLOOR)].copy()
    r = r.drop_duplicates(["hid", "unit", "price"])
    r["X_real"] = r.r_n / r.r_s
    r["lam1"] = r.r_p - r.X_real
    r["lam0"] = r.r_p
    print(f"\nTHE PAPER'S METHOD: {len(r):,} hours in which a storage unit's step set the realised price "
          f"({r.unit.nunique()} units)")
    rows = []
    for g, x in [("all", r), *r.groupby("group")]:
        if len(x) < 300:
            continue
        row = {"group": g, "hours": len(x), "units": x.unit.nunique(), "X_real": x.X_real.median(),
               "lam_star": x.lam30s.median(), "lam0_p": x.lam0.median(), "lam1_paper": x.lam1.median(),
               "lam1_below_0": (x.lam1 < 0).mean(), "corr_lam1_star": x[["lam1", "lam30s"]].corr().iat[0, 1],
               "corr_lam0_star": x[["lam0", "lam30s"]].corr().iat[0, 1]}
        f = x.dropna(subset=["fwd", "fill_anom"])
        if len(f) >= 300 and f.unit.nunique() >= 1:
            for lam in ("lam1", "lam0", "lam30s"):
                b, se = ols(f, lam, ["fwd", "fill_anom"])
                row |= {f"{lam}_fwd": b[0], f"{lam}_fwd_se": se[0], f"{lam}_fill": b[1], f"{lam}_fill_se": se[1]}
            row["n_fit"] = len(f)
        rows.append(row)
    t = pd.DataFrame(rows)
    pd.set_option("display.width", 240)
    print(t[["group", "hours", "units", "X_real", "lam_star", "lam0_p", "lam1_paper", "lam1_below_0",
             "corr_lam1_star", "corr_lam0_star"]].round(2).to_string(index=False))
    v = pd.read_parquet(TABLES / "water_value_revealed.parquet", columns=["unit", "date", "lambda50"])
    v["date"] = pd.to_datetime(v.date)
    e = r.merge(v, on=["unit", "date"])
    allv = v[v.date >= "2019-01-01"].groupby("unit").lambda50.median().rename("revealed_all_days")
    same = e.groupby("unit").agg(hours=("lam1", "size"), price=("r_p", "median"), lam1_paper=("lam1", "median"),
                                 revealed_same_day=("lambda50", "median"), lam_star=("lam30s", "median"))
    print("\nagainst EDP's and Movhera's revealed λ̂50 (water_value_revealed) on the same days:")
    print(same.join(allv).round(1).to_string())
    print(f"paper λ̂ / revealed λ̂50, same day: median {(e.lam1 / e.lambda50).median():.2f}, "
          f"corr {e[['lam1', 'lambda50']].corr().iat[0, 1]:.2f}; revealed / λ*: on these days "
          f"{(e.lambda50 / e.lam30s).median():.2f}")
    cols = [c for c in t.columns if c.endswith(("_fwd", "_fill")) and not c.endswith("_se")]
    print("\nfitted on the D−2 forward and the fill anomaly, unit effects (week-clustered se in the csv):")
    print(t[["group", "n_fit", *cols]].round(2).to_string(index=False))
    return t


def main() -> int:
    d = load()
    if "--atcost" in sys.argv:                  # the at-cost instrument (needs hcompcost_YYYYMM)
        pd.DataFrame(at_cost_estimates(at_cost(d))).to_csv(OUT_ATCOST, index=False)
        print(f"\nwrote {OUT_ATCOST.relative_to(ROOT)}")
        return 0
    if "--paper" in sys.argv:                   # rerun only the paper's method
        paper_method(d).to_csv(OUT_PAPER, index=False)
        print(f"wrote {OUT_PAPER.relative_to(ROOT)}")
        return 0
    if "--checks" in sys.argv:                  # rerun only the checks, appended to the results
        old = pd.read_csv(OUT)
        old = old[old.z.isin(list(ZSETS)) & (old["sample"].str.count(r"\|") == 1)]   # the main grid
        pd.concat([old, pd.DataFrame(checks(d))]).to_csv(OUT, index=False)
        print(f"\nwrote {OUT.relative_to(ROOT)}")
        return 0
    describe(d)
    res = levels(d) + checks(d)
    pd.DataFrame(res).to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    paper_method(d).to_csv(OUT_PAPER, index=False)
    print(f"wrote {OUT_PAPER.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
