#!/usr/bin/env python3
"""The holiday quantity test: do firms cut output on their customers' holidays in proportion to
the dose's price effect (market power) or to the dose itself (book balancing)?

    .venv/bin/python scripts/analysis/holiday_quantity_test.py --panel
    .venv/bin/python scripts/analysis/holiday_quantity_test.py --test --step 1
    .venv/bin/python scripts/analysis/holiday_quantity_test.py --test --step 2

Spec `docs/specs/2026-10-20-holiday-quantity-test-design.md`; plan
`docs/plans/2026-10-20-holiday-quantity-test.md`.

PANEL (`--panel` → outputs/tables/holiday_quantity_panel.parquet, gitignored). The five firms by
date and local hour, weekdays, 2019-01-01 → 2025-09-30, days with a full set of periods:
  legs        PDBF schedule in MW (sold +, bought −) by leg, as in `holiday_schedule_legs.py`:
              retail (registry role purchase_retail), pumping, generation (any other unit selling
              in that hour), other purchases; each in the auction and in bilateral contracts (role
              code 4). Quarter-hourly PDBF (from 2025-03-19) is averaged to the hour. A unit's firm
              is its largest owner that day, regulated pass-through suppliers out.
  dose_mw     the firm's holiday dose (`holiday_dose.parquet`, step 2 of the holiday design)
  slope       its residual-demand slope, MW per €/MWh (`firm_x.slope_net`, clean rows, ≥ FLOOR)
  P           dose_mw / slope, €/MWh: the dose as a move along the firm's residual demand
  s, offered_mw  its own sell offers within ±€5 of the hour's price per €/MWh, and all its offered
              sell MW (step cache `own`, effective curve)
  slope_cost  its slope at cost (`hcompcost` kb_s / NEAR), for step 2's check

STEP 1 (`--test --step 1` → outputs/tables/holiday_quantity_step1.csv). With date × hour and firm ×
month effects and 1/slope as a control, errors clustered by date: the retail legs on the dose (the
first stage), generation on the dose, and the standard error the test would have on P, computed
under b_P = 0 from the residual of generation on the dose and the control, so that b_P itself is
not formed. Stop if generation (sum) does not respond to the dose (|t| < 2), or if se(b_P) exceeds
s̄ / 2.8 (s̄ the dose-weighted mean of s): the test could not tell β = 0 from β = 1.

STEP 2 (`--test --step 2` → outputs/tables/holiday_quantity_test.csv). The slope test, spec §2:
  main        y = b_Z · dose + b_P · P + c · 1/slope + effects; β = −b_P / s̄ (the spec's test, its
              predictions fixed before the run: book balancing b_P = 0, Nash b_P = −s̄)
  s·P         y = b_Z · dose + γ · s·P + c · 1/slope + d · s + effects; β = −γ (step 1's refinement:
              s varies by hour and is zero in 30% of them, so Nash predicts −s · P hour by hour)
  by firm     dose and P interacted with Endesa, Iberdrola and the others, in one regression
for generation (sum, auction, bilateral), with the spec's checks on the sum: the slope at cost,
a flat daily profile for the dose, undosed days next to a dosed one dropped, Spain-wide days
(four or more mainland regions off) and regional days apart, March–June 2020 out, week clusters.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
for sub in ("lib", "analysis"):
    sys.path.insert(0, str(ROOT / "scripts" / sub))
from midday_hydro_iv import cluster_meat  # noqa: E402
from step_engine import NEAR  # noqa: E402
from step_estimator import wdemean  # noqa: E402
from step_estimator_hydro import FLOOR  # noqa: E402
from unit_ownership import majority_group, spells  # noqa: E402

DATA = ROOT / "data"
T = ROOT / "outputs" / "tables"
CACHE = ROOT / "outputs" / "cache" / "step"
PANEL = T / "holiday_quantity_panel.parquet"
STEP1 = T / "holiday_quantity_step1.csv"
FIRMS = ["ENDESA", "IBERDROLA", "NATURGY", "EDP", "REPSOL"]
START, END = pd.Timestamp("2019-01-01"), pd.Timestamp("2025-09-30")
HALF = 5.0
Z80 = 1.96 + 0.84
KEY = ["group", "date", "hour"]


def month_legs(f: Path, role: pd.Series, sp: pd.DataFrame) -> pd.DataFrame:
    p = pd.read_parquet(f, columns=["date", "period", "resolution_min", "unit", "schedule_mw", "role_code"])
    p["date"] = pd.to_datetime(p.date)
    p = p[(p.date >= START) & (p.date <= END) & (p.date.dt.dayofweek < 5)]
    if p.empty:
        return p
    per = p.groupby("date").agg(n=("period", "max"), res=("resolution_min", "first"))
    full = per.index[((per.res == 60) & (per.n == 24)) | ((per.res == 15) & (per.n == 96))]
    p = p[p.date.isin(full)].copy()
    p["hour"] = np.where(p.resolution_min == 60, p.period - 1, (p.period - 1) // 4)
    p["mw"] = p.schedule_mw * p.resolution_min / 60          # summed over the hour: mean MW
    p["bil"] = p.role_code == "4"
    u = p.groupby(["unit", "date", "hour", "bil"], as_index=False).mw.sum()
    keys = u[["unit", "date"]].drop_duplicates()
    keys["group"] = majority_group(keys, sp, exposed=True).to_numpy()
    u = u.merge(keys, on=["unit", "date"])
    u = u[u.group.isin(FIRMS)]
    r = u.unit.map(role)
    u["leg"] = np.select([r.eq("purchase_retail"), r.eq("pumping"), u.mw > 0], ["retail", "pumping", "gen"], "other_buy")
    u["leg"] = u.leg + np.where(u.bil, "_bilateral", "_auction")
    return u.groupby(KEY + ["leg"]).mw.sum().unstack(fill_value=0.0).reset_index()


def own_slopes() -> pd.DataFrame:
    parts = []
    for f in sorted(CACHE.glob("own_2*.parquet")):
        ym = f.stem.split("_")[1]
        h = pd.read_parquet(CACHE / f"hours_{ym}.parquet", columns=["hid", "date", "period", "p_star"])
        o = pd.read_parquet(f, columns=["hid", "group", "price", "v_sell"]).merge(h, on="hid")
        o = o[o.group.isin(FIRMS)]
        o["near"] = o.v_sell.where((o.price - o.p_star).abs() <= HALF, 0.0)
        g = o.groupby(["group", "date", "period"]).agg(s=("near", "sum"), offered_mw=("v_sell", "sum")).reset_index()
        g["s"] = g.s / (2 * HALF)
        c = pd.read_parquet(CACHE / f"hcompcost_{ym}.parquet", columns=["hid", "group", "kb_s"]).drop_duplicates(["hid", "group"])
        c = c.merge(h[["hid", "date", "period"]], on="hid")
        c["slope_cost"] = c.kb_s / NEAR
        parts.append(g.merge(c[["group", "date", "period", "slope_cost"]], on=["group", "date", "period"], how="outer"))
    s = pd.concat(parts, ignore_index=True)
    s["date"] = pd.to_datetime(s.date)
    s["hour"] = s.period - 1
    return s.drop(columns="period")


def build_panel() -> int:
    reg = pd.read_parquet(DATA / "omie/registry/unit_registry.parquet", columns=["unit", "role"])
    role = reg.set_index("unit").role
    sp = spells()
    parts = []
    for f in sorted((DATA / "omie/pdbf/parquet").glob("pdbf_*.parquet")):
        ym = f.stem.split("_")[1]
        if not ("201901" <= ym <= "202509"):
            continue
        parts.append(month_legs(f, role, sp))
        print(f"  {ym}", flush=True)
    d = pd.concat(parts, ignore_index=True).fillna(0.0)
    d["gen"] = d.gen_auction + d.gen_bilateral
    d["retail"] = d.retail_auction + d.retail_bilateral
    dose = pd.read_parquet(T / "holiday_dose.parquet")
    dose["date"] = pd.to_datetime(dose.date)
    d = d.merge(dose[KEY + ["dose_mw"]], on=KEY, how="left").fillna({"dose_mw": 0.0})
    fx = pd.read_parquet(T / "firm_x.parquet", columns=["date", "period", "resolution_min", "firm", "slope_net", "clean"])
    fx = fx[fx.clean & (fx.resolution_min == 60) & (fx.slope_net >= FLOOR)].rename(columns={"firm": "group", "slope_net": "slope"})
    fx["date"] = pd.to_datetime(fx.date)
    fx["hour"] = fx.period - 1
    d = d.merge(fx[KEY + ["slope"]], on=KEY, how="left")
    d = d.merge(own_slopes(), on=KEY, how="left")
    d["P"] = d.dose_mw / d.slope
    d["inv_slope"] = 1.0 / d.slope
    d.to_parquet(PANEL, index=False)
    print(f"wrote {PANEL.relative_to(ROOT)}: {len(d):,} firm-hours, {d.date.nunique():,} days, "
          f"{int((d.dose_mw > 0).sum()):,} with a dose; slope on {d.slope.notna().mean():.1%}, s on {d.s.notna().mean():.1%}")
    return 0


def resid(d: pd.DataFrame, cols: list[str]) -> np.ndarray:
    codes = [pd.factorize(d.date.dt.strftime("%Y%m%d") + "|" + d.hour.astype(str))[0],
             pd.factorize(d.group + d.date.dt.strftime("%Y%m"))[0]]
    return wdemean(d[cols].to_numpy(float), codes, np.ones(len(d)))


def ols(y: np.ndarray, X: np.ndarray, cl: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    A = np.linalg.inv(X.T @ X)
    b = A @ X.T @ y
    V = A @ cluster_meat(X, y - X @ b, cl) @ A
    return b, np.sqrt(np.diag(V))


def fit(d: pd.DataFrame, y: str, regs: list[str], controls: list[str], cluster: str = "date") -> dict:
    """y on regs and controls after date × hour and firm × month effects; {reg: (b, se)}, se
    clustered by date (or ISO week)."""
    M = resid(d, [y] + regs + controls)
    X = M[:, 1:]
    cl = (d.date.dt.strftime("%G%V") if cluster == "week" else d.date.dt.strftime("%Y%m%d")).to_numpy()
    b, se = ols(M[:, 0], X, cl)
    return {r: (float(b[i]), float(se[i])) for i, r in enumerate(regs)}


def national_dates() -> pd.DatetimeIndex:
    """Dates with four or more mainland regions off on a holiday not shared by the whole market."""
    sys.path.insert(0, str(ROOT / "scripts" / "lib"))
    from holidays import ES_MAINLAND, unshared
    days = pd.date_range(START, END, freq="D")
    n = unshared(days)[list(ES_MAINLAND)].sum(axis=1)
    return n.index[n >= 4]


def step2() -> int:
    d = pd.read_parquet(PANEL)
    d = d[d.slope.notna() & d.s.notna()].copy()
    d["sP"] = d.s * d.P
    w = (d.dose_mw > 0)
    s_bar = float(np.average(d.s[w], weights=d.dose_mw[w]))
    rows = []

    def main_rows(x: pd.DataFrame, spec: str, outcomes: list[str], P: str = "P", inv: str = "inv_slope",
                  dose: str = "dose_mw", cluster: str = "date") -> None:
        sb = float(np.average(x.s[x[dose] > 0], weights=x[dose][x[dose] > 0]))
        for y in outcomes:
            r = fit(x, y, [dose, P], [inv], cluster)
            bP, se = r[P]
            rows.append({"spec": spec, "outcome": y, "term": "P", "b_Z": r[dose][0], "se_Z": r[dose][1],
                         "b": bP, "se": se, "s_bar": sb, "beta": -bP / sb, "beta_lo": (-bP - 1.96 * se) / sb,
                         "beta_hi": (-bP + 1.96 * se) / sb, "p_beta0": _p(bP / se), "p_nash": _p((bP + sb) / se),
                         "n": len(x), "dosed": int((x[dose] > 0).sum())})

    gens = ["gen", "gen_auction", "gen_bilateral"]
    main_rows(d, "main", gens)
    for y in gens:                                   # the s·P refinement
        r = fit(d, y, ["dose_mw", "sP"], ["inv_slope", "s"])
        g, se = r["sP"]
        rows.append({"spec": "s·P", "outcome": y, "term": "s·P", "b_Z": r["dose_mw"][0], "se_Z": r["dose_mw"][1],
                     "b": g, "se": se, "s_bar": s_bar, "beta": -g, "beta_lo": -g - 1.96 * se, "beta_hi": -g + 1.96 * se,
                     "p_beta0": _p(g / se), "p_nash": _p((g + 1) / se), "n": len(d), "dosed": int(w.sum())})
    # by firm: Endesa, Iberdrola, the rest
    for f in ("ENDESA", "IBERDROLA"):
        x = d.copy()
        own = x.group == f
        x["dose_f"], x["P_f"] = x.dose_mw.where(own, 0.0), x.P.where(own, 0.0)
        x["dose_o"], x["P_o"] = x.dose_mw.where(~own, 0.0), x.P.where(~own, 0.0)
        r = fit(x, "gen", ["dose_f", "P_f", "dose_o", "P_o"], ["inv_slope"])
        sb = float(np.average(x.s[own & (x.dose_mw > 0)], weights=x.dose_mw[own & (x.dose_mw > 0)]))
        bP, se = r["P_f"]
        rows.append({"spec": f"firm {f}", "outcome": "gen", "term": "P", "b_Z": r["dose_f"][0], "se_Z": r["dose_f"][1],
                     "b": bP, "se": se, "s_bar": sb, "beta": -bP / sb, "beta_lo": (-bP - 1.96 * se) / sb,
                     "beta_hi": (-bP + 1.96 * se) / sb, "p_beta0": _p(bP / se), "p_nash": _p((bP + sb) / se),
                     "n": len(x), "dosed": int((own & (x.dose_mw > 0)).sum())})
    # checks, on total generation
    c = d[d.slope_cost.notna() & (d.slope_cost >= FLOOR)].copy()
    c["P_cost"], c["inv_cost"] = c.dose_mw / c.slope_cost, 1 / c.slope_cost
    main_rows(c, "check: slope at cost", ["gen"], P="P_cost", inv="inv_cost")
    x = d.copy()
    x["dose_flat"] = x.groupby(["group", "date"]).dose_mw.transform("mean")
    x["P_flat"] = x.dose_flat / x.slope
    main_rows(x, "check: flat profile", ["gen"], P="P_flat", dose="dose_flat")
    dosed = d[d.dose_mw > 0][["group", "date"]].drop_duplicates()
    near = pd.concat([dosed.assign(date=dosed.date + pd.Timedelta(days=k)) for k in (-1, 1)]).drop_duplicates()
    x = d.merge(near.assign(near=True), on=["group", "date"], how="left")
    x = x[~(x.near.fillna(False).astype(bool) & (x.dose_mw == 0))]
    main_rows(x, "check: adjacent days out", ["gen"])
    nat = d.date.isin(national_dates())
    main_rows(d[nat | (d.dose_mw == 0)], "check: Spain-wide days only", ["gen"])
    main_rows(d[~nat | (d.dose_mw == 0)], "check: regional days only", ["gen"])
    main_rows(d[~d.date.between("2020-03-01", "2020-06-30")], "check: without Mar–Jun 2020", ["gen"])
    main_rows(d, "check: week clusters", ["gen"], cluster="week")

    out = pd.DataFrame(rows)
    out.to_csv(T / "holiday_quantity_test.csv", index=False)
    with pd.option_context("display.width", 200, "display.float_format", "{:.3f}".format):
        print(out[["spec", "outcome", "term", "b_Z", "se_Z", "b", "se", "s_bar", "beta", "beta_lo", "beta_hi",
                   "p_beta0", "p_nash", "dosed"]].to_string(index=False))
    m = out[(out.spec == "main") & (out.outcome == "gen")].iloc[0]
    print(f"\nmain test, generation: b_P {m.b:+.2f} (se {m.se:.2f}) against Nash −{m.s_bar:.1f}: "
          f"β {m.beta:+.2f} [{m.beta_lo:+.2f}, {m.beta_hi:+.2f}]; p(β = 0) {m.p_beta0:.3f}, p(β = 1) {m.p_nash:.3g}")
    return 0


def _p(z: float) -> float:
    import math
    return math.erfc(abs(z) / math.sqrt(2.0))


def step1() -> int:
    d = pd.read_parquet(PANEL)
    d = d[d.slope.notna()].copy()
    cl = d.date.dt.strftime("%Y%m%d").to_numpy()
    rows = []
    outcomes = ["retail_auction", "retail_bilateral", "retail", "gen_auction", "gen_bilateral", "gen"]
    M = resid(d, outcomes + ["dose_mw", "inv_slope", "P"])
    y = {c: M[:, i] for i, c in enumerate(outcomes)}
    Z, C, P = M[:, len(outcomes)], M[:, len(outcomes) + 1], M[:, len(outcomes) + 2]
    X = np.column_stack([Z, C])
    Pt = P - X @ np.linalg.lstsq(X, P, rcond=None)[0]          # P net of the dose and the control
    s_bar = float(np.average(d.s[(d.dose_mw > 0) & d.s.notna()], weights=d.dose_mw[(d.dose_mw > 0) & d.s.notna()]))
    for c in outcomes:
        b, se = ols(y[c], X, cl)
        e0 = y[c] - X @ np.linalg.lstsq(X, y[c], rcond=None)[0]   # the residual under b_P = 0
        se_p = float(np.sqrt(cluster_meat(Pt[:, None], e0, cl)[0, 0]) / (Pt @ Pt))
        rows.append({"outcome": c, "b_Z": b[0], "se_Z": se[0], "t_Z": b[0] / se[0], "se_bP_null": se_p,
                     "mde_beta": Z80 * se_p / s_bar, "n": len(d), "dosed": int((d.dose_mw > 0).sum())})
    out = pd.DataFrame(rows)
    out["s_bar"] = s_bar
    out.to_csv(STEP1, index=False)
    with pd.option_context("display.width", 140, "display.float_format", "{:.3f}".format):
        print(out.to_string(index=False))
    g = out.set_index("outcome").loc["gen"]
    print(f"  s̄ (dose-weighted own offer slope) {s_bar:.1f} MW per €/MWh; P on dosed hours: "
          f"median {d.P[d.dose_mw > 0].median():.2f}, p90 {d.P[d.dose_mw > 0].quantile(.9):.2f} €/MWh")
    stops = {f"generation on the dose |t| {abs(g.t_Z):.1f} < 2": abs(g.t_Z) < 2,
             f"se(b_P) {g.se_bP_null:.1f} > s̄/2.8 = {s_bar / Z80:.1f} (smallest detectable β {g.mde_beta:.2f})":
                 g.se_bP_null > s_bar / Z80}
    for k, v in stops.items():
        print(f"  {'STOP' if v else 'ok  '} {k}")
    print(f"stop rule (step 1): {'STOP' if any(stops.values()) else 'CONTINUE'}")
    return 0


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--panel", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--step", type=int, default=1)
    args = ap.parse_args()
    if args.panel:
        return build_panel()
    if args.test and args.step == 1:
        return step1()
    if args.test and args.step == 2:
        return step2()
    raise SystemExit("--panel, or --test --step 1|2")


if __name__ == "__main__":
    sys.exit(main())
