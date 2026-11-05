#!/usr/bin/env python3
"""Nuclear cuts, sharpened: snapshot days only, and split at the gas cap.

    .venv/bin/python scripts/analysis/nuclear_cuts_snapshot_split.py

Rules are in notes/rq-nuclear-cuts.md §7.0 (written before this ran). Reads the stored T3
panel (nuclear_cuts_conduct_panel.parquet) and T2's reactor-days; rebuilds neither.
Estimators are imported from nuclear_cuts_conduct.py (iv, matrices, shares, firm_hours,
local_date) and nuclear_cuts_benchmark.py (compare, simulate). The slope test's panel
preparation (1/|RD'|, P, the cut-opportunity controls) is inline in conduct.slope_test(),
so it is restated in slope_panel(); the full-sample run is checked against the stored
nuclear_cuts_slope_test.csv (to 0.5% of each standard error: firm_x.parquet was rebuilt after
that CSV) and the script stops if it does not reproduce.

PART 1  SNAPSHOT DAYS. A snapshot day is a local date on which OMIE's indisp holds a
        snapshot (the set build_reactor_outages.declarations() uses to mark
        `undeclared_gap`). Recount cut volume by snapshot / gap day; the slope test, the T3
        IV, its null band and T2's comparison on all, snapshot and gap days.
PART 2  GAS CAP. Slope test by period (pre-cap, cap 2022-06-15 -> 2023-12-31, post-cap) and
        operator; reservation price on partial-cut days by operator and period, differences
        with week-block bootstrap intervals, and the within-period slope on p_exp.

NASH VALUE. P_N = gamma_N x lambda. gamma_N = minus the slope of the c_acct price-taker's
simulated cut on p_exp in the cell; lambda = the loading of the owners' X on P_plan under the
same regressors (primary: full sample, all days; in-cell carried beside it). beta-equivalent
= P / P_N (1 = Nash, 0 = price-taking). MDE (5% size, 80% power) = 2.8 se.

OUTPUTS: outputs/tables/nuclear_cuts_snapshot_split_{coverage,t2,t3,nullband,slope,gapdiff,
resv,resv_diff,resv_slope}.csv
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import faulthandler  # noqa: E402
import glob  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import norm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
import nuclear_cuts_benchmark as B  # noqa: E402
import nuclear_cuts_conduct as C  # noqa: E402
from midday_hydro_iv import ols  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
PFX = TABLES / "nuclear_cuts_snapshot_split"
WINDOWS = {"2019-2026": ("2019-01-01", "2026-05-31"), "pre-cap": ("2019-01-01", "2022-06-14"),
           "cap": ("2022-06-15", "2023-12-31"), "post-cap (2024-2026)": ("2024-01-01", "2026-05-31")}
OPERATORS = {"all": None, "CNAT": ["ALZ1", "ALZ2", "TRL1"], "ANAV": ["ASC1", "ASC2", "VAN2"], "Iberdrola": ["COF1"]}
SPECS = {
    "refuelling": ["Z_plan", "P_plan", "Z_wind", "inv", "Z_unpl", "Z_rain"],
    "refuelling, cut opportunity controlled": ["Z_plan", "P_plan", "Z_wind", "simcut", "margin", "Zp_simcut",
                                               "Zp_margin", "inv", "Z_unpl", "Z_rain"],
}
MAIN_SPEC = "refuelling, cut opportunity controlled"
MIN_DOSED = 100
Z80 = 1.96 + 0.84
RESV_MIN_DAYS = 20
BOOT = 2000


def rearm(sec: int = 900) -> None:
    faulthandler.cancel_dump_traceback_later()
    faulthandler.dump_traceback_later(sec, exit=True)


def snapshot_dates() -> set:
    """Local dates indisp holds a snapshot for (as build_reactor_outages.declarations)."""
    s = pd.concat([pd.read_parquet(f, columns=["snapshot"]) for f in sorted(glob.glob(str(DATA / "omie/indisp/parquet/indisp_*.parquet")))])
    return set(pd.to_datetime(s.snapshot).dt.normalize())


def in_window(d: pd.DataFrame, w: str) -> pd.DataFrame:
    a, b = WINDOWS[w]
    return d[(d.date >= a) & (d.date <= b)]


# ---------------------------------------------------------------- coverage
def coverage(covered: set) -> pd.DataFrame:
    """Reactor-days and cut volume (TWh) by year, form and snapshot / gap day (T1's file)."""
    t = pd.read_parquet(TABLES / "nuclear_cuts_daily.parquet")
    t["snapshot_day"] = t.date.isin(covered)
    bad = t[t.gap & t.snapshot_day]
    assert bad.empty, f"{len(bad)} reactor-days flagged undeclared_gap fall on a snapshot day"
    g = t.groupby(["year", "form", "snapshot_day"]).agg(reactor_days=("unit", "size"), cut_twh=("cut_mw", lambda x: x.sum() * 24 / 1e6))
    g = g.reset_index()
    tot = g.groupby(["year", "form"]).cut_twh.transform("sum")
    g["share_of_form_twh"] = np.where(tot > 0, g.cut_twh / tot, np.nan)
    return g.round(4)


# ---------------------------------------------------------------- slope-test panel
def slope_panel() -> pd.DataFrame:
    """The T3 panel with the slope test's regressors (conduct.slope_test, restated)."""
    d = pd.read_parquet(C.OUT_PANEL)
    sh = C.shares(d[["unit", "date"]].drop_duplicates())
    f = C.firm_hours()
    f["inv"] = (1.0 / f.slope).where(f.slope > 0)
    f["date"] = C.local_date(f.utc)
    fd = f.groupby(["firm", "date"]).inv.mean().rename("inv").reset_index()
    r = sh.merge(fd, on=["firm", "date"], how="left").dropna(subset=["inv"])
    r["w"] = r.inv * r.share
    g = r.groupby(["unit", "date"]).agg(w=("w", "sum"), cov=("share", "sum"))
    d = d.merge((g.w / g["cov"]).rename("inv").reset_index(), on=["unit", "date"], how="left")
    d["inv"] = d.inv * 1000.0
    d["P_plan"] = d.Z_plan * d.inv
    d["simcut"] = (d.sim_c_acct > 0).astype(float)
    d["margin"] = d.p_exp - d.c_acct
    d["Zp_simcut"], d["Zp_margin"] = d.Z_plan * d.simcut, d.Z_plan * d.margin
    return d


def fit(s: pd.DataFrame, y: str, xs: list[str]) -> dict:
    """OLS of y on xs, reactor x month + day-of-week effects, week clusters. A regressor with no
    variation left after the effects is dropped (NaN); a singular design returns {}."""
    s = s.dropna(subset=[y, *xs]).reset_index(drop=True)
    if len(s) < 30:
        return {}
    M = C.matrices(s, [y, *xs])
    raw = s[xs].to_numpy(float).std(axis=0)
    keep = [k for k in range(len(xs)) if raw[k] > 0 and M[:, 1 + k].std() > 1e-6 * raw[k]]
    R = M[:, [1 + k for k in keep]]
    if R.shape[1] == 0 or np.linalg.cond(R.T @ R) > 1e12:
        return {}
    b, se = ols(M[:, 0], R, s.wk.to_numpy())
    out = {"n": len(s)}
    for j, k in enumerate(keep):
        out[xs[k]] = (float(b[j]), float(se[j]))
    return out


def slope_cell(s: pd.DataFrame, spec: str, lam_pool: dict) -> dict:
    """The slope test on one cell, with Nash value, beta-equivalent, MDE."""
    xs = SPECS[spec]
    row = {"n": len(s), "n_dosed": int((s.Z_plan > 0).sum()), "reactors": s.unit.nunique()}
    if row["n_dosed"] < MIN_DOSED:
        return row | {"verdict": f"too few dosed days (<{MIN_DOSED})"}
    r = fit(s, "dev", xs)
    if "P_plan" not in r:
        return row | {"verdict": "P not identified in the cell"}
    fs = fit(s, "X", xs)
    pt = fit(s.assign(_one=1.0), "sim_c_acct", ["p_exp"])
    P, seP = r["P_plan"]
    Z, seZ = r.get("Z_plan", (np.nan, np.nan))
    gam = -pt["p_exp"][0] if "p_exp" in pt else np.nan
    lam_c, lam_c_se = fs.get("P_plan", (np.nan, np.nan))
    PN = gam * lam_pool[spec]
    PN_c = gam * lam_c
    row |= {"n": r["n"], "Z_b": Z, "Z_se": seZ, "P_b": P, "P_se": seP,
            "P_lo": P - 1.96 * seP, "P_hi": P + 1.96 * seP, "mde_P": Z80 * seP,
            "gamma_N": gam, "lam_pool": lam_pool[spec], "lam_cell": lam_c, "lam_cell_se": lam_c_se,
            "P_Nash_pool": PN, "P_Nash_cell": PN_c,
            "beta": P / PN, "beta_lo": min((P - 1.96 * seP) / PN, (P + 1.96 * seP) / PN),
            "beta_hi": max((P - 1.96 * seP) / PN, (P + 1.96 * seP) / PN),
            "mde_beta": Z80 * seP / abs(PN),
            "p_nash_pool": 2 * norm.sf(abs((P - PN) / seP)), "p_nash_cell": 2 * norm.sf(abs((P - PN_c) / seP)),
            "p_zero": 2 * norm.sf(abs(P / seP))}
    informative = row["mde_beta"] <= 1
    nash_rej = row["p_nash_pool"] < 0.05
    row["informative"] = informative
    # "uninformative" qualifies a failure to reject only: a rejection is a result at any power
    row["verdict"] = "Nash rejected" if nash_rej else \
        "Nash not rejected" + ("" if informative else "; uninformative (MDE_beta>1)")
    row["price_taking_claim"] = bool(row["beta_lo"] <= 0 <= row["beta_hi"] and row["beta_hi"] < 0.5 and informative)
    row["nash_verdicts_agree"] = bool(nash_rej == (row["p_nash_cell"] < 0.05)) if np.isfinite(PN_c) else np.nan
    return row


def slope_part(d: pd.DataFrame, covered: set) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = d.assign(snap=d.date.isin(covered))
    # reproduce the stored slope CSV on the full sample, every spec and term
    ref = pd.read_csv(C.OUT_SLOPE)
    worst = 0.0
    for lab, w in (("2019-2026", "2019-2026"), ("2024-2026", "post-cap (2024-2026)")):
        s0 = in_window(d, w)
        for spec, xs in SPECS.items():
            r = fit(s0, "dev", xs)
            e = ref[(ref["sample"] == lab) & (ref.spec == spec) & (ref.y == "dev")].set_index("term")
            for x in xs:
                worst = max(worst, abs(r[x][0] - e.loc[x, "b"]) / e.loc[x, "se"], abs(r[x][1] - e.loc[x, "se"]) / e.loc[x, "se"])
            assert r["n"] == e.n.iloc[0]
    # 1/|RD'| is restated from firm_x.parquet, rebuilt 2026-10-22 (after the stored slope CSV, 2026-10-19),
    # so agreement to 6 digits is impossible; the revised rule is 0.5% of the standard error (note §7).
    print(f"\nreproduction of nuclear_cuts_slope_test.csv (dev, both specs, 2019-2026 and 2024-2026): worst diff {worst:.2e} of the se")
    assert worst < 0.005, "full-sample slope test does not reproduce the stored CSV: stop"

    full = d
    lam_pool = {}
    for spec, xs in SPECS.items():
        fs = fit(full, "X", xs)
        lam_pool[spec] = fs["P_plan"][0]
    print("pooled lambda (X on P_plan, full sample, all days):", {k: round(v, 3) for k, v in lam_pool.items()})
    pt = fit(full, "sim_c_acct", ["p_exp"])
    pt24 = fit(in_window(d, "post-cap (2024-2026)"), "sim_c_acct", ["p_exp"])
    print(f"price-taker slope on p_exp: full {pt['p_exp'][0]:.3f} (§6: 1.5), 2024-26 {pt24['p_exp'][0]:.3f} (§6: 3.3)")

    rows = []
    for sample in ("all days", "snapshot days", "gap days"):
        ds = d if sample == "all days" else d[d.snap] if sample == "snapshot days" else d[~d.snap]
        for w in WINDOWS:
            dw = in_window(ds, w)
            for op, units in OPERATORS.items():
                dc = dw if units is None else dw[dw.unit.isin(units)]
                for spec in SPECS:
                    rows.append({"sample": sample, "window": w, "operator": op, "spec": spec} | slope_cell(dc, spec, lam_pool))
    res = pd.DataFrame(rows)

    # gap days against snapshot days: z on the difference in P
    dd = []
    for (w, op, spec), g in res.groupby(["window", "operator", "spec"]):
        a = g[g["sample"] == "snapshot days"].iloc[0]
        b = g[g["sample"] == "gap days"].iloc[0]
        if pd.notna(a.get("P_b")) and pd.notna(b.get("P_b")):
            diff = b.P_b - a.P_b
            z = diff / np.hypot(a.P_se, b.P_se)
            dd.append({"window": w, "operator": op, "spec": spec, "P_snapshot": a.P_b, "se_snapshot": a.P_se,
                       "P_gap": b.P_b, "se_gap": b.P_se, "diff_gap_minus_snapshot": diff, "z": z,
                       "differs_5pct": abs(z) > 1.96})
    return res, pd.DataFrame(dd)


# ---------------------------------------------------------------- T3 IV and null band
def t3_part(d: pd.DataFrame, covered: set) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = d.assign(snap=d.date.isin(covered))
    specs = [("all four instruments", C.INST), ("reactor outages", ["Z_unpl", "Z_plan"]), ("regional wind", ["Z_wind"])]
    rows = []
    for sample in ("all days", "snapshot days", "gap days"):
        ds = d if sample == "all days" else d[d.snap] if sample == "snapshot days" else d[~d.snap]
        for w in ("2019-2026", "post-cap (2024-2026)"):
            dw = in_window(ds, w)
            for lab, zs in specs:
                name = f"{sample}, {w}: {lab}"
                try:
                    r = C.iv(dw, "dev", zs, name)
                except Exception as e:  # noqa: BLE001  (a degenerate cell is reported, not hidden)
                    print(f"  {name}: failed ({type(e).__name__}: {e})")
                    r = {"spec": name, "n": len(dw), "error": f"{type(e).__name__}: {e}"}
                rows.append({"sample": sample, "window": w, "label": lab} | r)
    t3 = pd.DataFrame(rows)

    # null band: price-takers with cost c_acct + delta + eps, simulated on the full panel
    rearm(1500)
    lim = C._limits()
    full = d.sort_values(["unit", "date"]).reset_index(drop=True)
    base = B.simulate(full, lim, "c_acct")
    print(f"null band: re-simulated c_acct price-taker vs stored sim_c_acct, max abs diff {np.abs(base - full.sim_c_acct.to_numpy()).max():.2e}")
    nulls = []
    for delta in C.DELTAS:
        for seed in C.SEEDS:
            rng = np.random.default_rng(seed)
            t = full.copy()
            t["c_null"] = t.c_acct + delta + rng.normal(0, C.SIGMA, len(t))
            t["dev_null"] = B.simulate(t, lim, "c_null") - base
            for sample in ("all days", "snapshot days"):
                ts = t if sample == "all days" else t[t.snap]
                for w in ("2019-2026", "post-cap (2024-2026)"):
                    r = C.iv(in_window(ts, w), "dev_null", C.INST, "null", quiet=True)
                    nulls.append({"sample": sample, "window": w, "delta": delta, "seed": seed, "b": r["b"], "se": r["se"], "F": r["F"]})
    nb = pd.DataFrame(nulls)
    band = nb.groupby(["sample", "window"]).agg(b_min=("b", "min"), b_max=("b", "max"), se_mean=("se", "mean")).reset_index()
    print(band.round(2).to_string())
    return t3, band


# ---------------------------------------------------------------- T2 on snapshot days
def t2_part(covered: set) -> pd.DataFrame:
    b = pd.read_parquet(TABLES / "nuclear_cuts_benchmark_daily.parquet")
    b["snap"] = b.date.isin(covered)
    b["window"] = np.select([b.date < "2022-06-15", b.date <= "2023-12-31"], ["pre-cap", "cap"], "post-cap (2024-2026)")
    out = []
    for sample, m in (("all days", b.snap | ~b.snap), ("snapshot days", b.snap), ("gap days", ~b.snap)):
        x = b[m]
        for by in (["year"], ["window"]):
            c = B.compare(x, "sim_c_acct", by).reset_index()
            c.columns = ["period"] + list(c.columns[1:])
            corr = x.groupby(by).apply(lambda g: g.cut_mw.corr(g.sim_c_acct) if len(g) > 2 and g.cut_mw.std() > 0 and g.sim_c_acct.std() > 0 else np.nan, include_groups=False)
            c["daily_corr"] = c.period.map(corr).round(3)
            c["reactor_days"] = c.period.map(x.groupby(by).size())
            out.append(c.assign(sample=sample, by=by[0]))
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------- reservation price
def resv_part() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    t = pd.read_parquet(TABLES / "nuclear_cuts_daily.parquet")
    t = t[t.date >= "2019-01-01"].copy()
    t["period"] = np.select([t.date < "2022-06-15", t.date <= "2023-12-31"], ["pre-cap", "cap"], "post-cap")
    t["wk"] = t.date.dt.strftime("%G%V")
    pc = t[t.form == "partial"]
    rv = pc[pc.resv_price.notna()]
    ops = {"all three": None, "CNAT": "CNAT", "ANAV": "ANAV", "Iberdrola (Cofrentes)": "Iberdrola"}
    order = ["pre-cap", "cap", "post-cap"]
    lev, slopes = [], []
    groups = {}
    for on, o in ops.items():
        for p in order:
            a = pc[(pc.period == p) & ((pc.operator == o) if o else True)]
            r = rv[(rv.period == p) & ((rv.operator == o) if o else True)]
            row = {"operator": on, "period": p, "partial_cut_days": len(a), "days_with_reservation": len(r),
                   "share_offering": len(r) / len(a) if len(a) else np.nan,
                   "mean_p_exp": a.p_exp.mean(), "mean_p_real": a.p_real.mean(), "mean_c_acct": a.c_acct.mean()}
            if len(r) >= RESV_MIN_DAYS:
                row |= {"median": r.resv_price.median(), "q25": r.resv_price.quantile(.25), "q75": r.resv_price.quantile(.75),
                        "median_minus_c_acct": (r.resv_price - r.c_acct).median()}
                groups[(on, p)] = [g.resv_price.to_numpy() for _, g in r.groupby("wk")]
                q = r.dropna(subset=["p_exp"]).reset_index(drop=True)
                if len(q) > 30 and q.p_exp.std() > 0:
                    M = C.demean(q[["resv_price", "p_exp"]].to_numpy(float), [pd.factorize(q.unit)[0]])
                    if M[:, 1].std() > 1e-6:
                        b, se = ols(M[:, 0], M[:, [1]], q.wk.to_numpy())
                        slopes.append({"operator": on, "period": p, "slope_on_p_exp": b[0], "se": se[0],
                                       "lo": b[0] - 1.96 * se[0], "hi": b[0] + 1.96 * se[0], "n": len(q), "sd_p_exp": q.p_exp.std()})
            lev.append(row)
    lev = pd.DataFrame(lev)
    rng = np.random.default_rng(0)
    diff = []
    for on in ops:
        for p0, p1 in (("pre-cap", "cap"), ("cap", "post-cap"), ("pre-cap", "post-cap")):
            if (on, p0) not in groups or (on, p1) not in groups:
                continue
            g0, g1 = groups[(on, p0)], groups[(on, p1)]
            d_ = []
            for _ in range(BOOT):
                m0 = np.median(np.concatenate([g0[i] for i in rng.integers(0, len(g0), len(g0))]))
                m1 = np.median(np.concatenate([g1[i] for i in rng.integers(0, len(g1), len(g1))]))
                d_.append(m1 - m0)
            a, b = lev[(lev.operator == on) & (lev.period == p0)].iloc[0], lev[(lev.operator == on) & (lev.period == p1)].iloc[0]
            lo, hi = np.percentile(d_, [2.5, 97.5])
            dp = b.mean_p_exp - a.mean_p_exp
            moved = (lo > 0 or hi < 0) and np.sign(b["median"] - a["median"]) == np.sign(dp)
            fixed = (lo >= -5 and hi <= 5)
            diff.append({"operator": on, "from": p0, "to": p1, "median_from": a["median"], "median_to": b["median"],
                         "change": b["median"] - a["median"], "lo": lo, "hi": hi, "weeks_from": len(g0), "weeks_to": len(g1),
                         "change_mean_p_exp": dp, "change_mean_p_real": b.mean_p_real - a.mean_p_real,
                         "change_mean_c_acct": b.mean_c_acct - a.mean_c_acct,
                         "moved_with_price": bool(moved), "did_not_move_within_5": bool(fixed)})
    return lev, pd.DataFrame(diff), pd.DataFrame(slopes)


# ---------------------------------------------------------------- main
def main() -> int:
    rearm()
    covered = snapshot_dates()
    cov = coverage(covered)
    cov.to_csv(f"{PFX}_coverage.csv", index=False)
    print("\nCOVERAGE: share of reactor-days on snapshot days, and cut volume (TWh) by form")
    pv = cov.pivot_table(index="year", columns=["form", "snapshot_day"], values="cut_twh", aggfunc="sum").round(2)
    print(pv.to_string())
    e = cov[cov.year >= 2024].groupby(["form", "snapshot_day"]).cut_twh.sum().unstack().round(2)
    e["share_on_snapshot_days"] = (e[True] / (e[True] + e[False])).round(3)
    print("\n2024-2026 cut volume, TWh, by form and snapshot day:\n" + e.to_string())

    rearm()
    d = slope_panel()
    res, gd = slope_part(d, covered)
    res.to_csv(f"{PFX}_slope.csv", index=False)
    gd.to_csv(f"{PFX}_gapdiff.csv", index=False)
    cols = ["sample", "window", "operator", "n", "n_dosed", "P_b", "P_se", "P_lo", "P_hi", "mde_P", "gamma_N", "P_Nash_pool",
            "beta", "beta_lo", "beta_hi", "mde_beta", "p_nash_pool", "p_nash_cell", "verdict"]
    pd.set_option("display.width", 250)
    print("\nSLOPE TEST, main spec (cut opportunity controlled)")
    print(res[res.spec == MAIN_SPEC][cols].round(3).to_string(index=False))
    print("\nGAP vs SNAPSHOT days, main spec")
    print(gd[gd.spec == MAIN_SPEC].round(3).to_string(index=False))

    rearm()
    t3, band = t3_part(d, covered)
    t3.to_csv(f"{PFX}_t3.csv", index=False)
    band.to_csv(f"{PFX}_nullband.csv", index=False)

    rearm()
    t2 = t2_part(covered)
    t2.to_csv(f"{PFX}_t2.csv", index=False)
    print("\nT2 at c_acct, 2024-2026 window and by sample")
    print(t2[(t2.by == "window") & (t2.period == "post-cap (2024-2026)")].to_string(index=False))

    rearm()
    lev, diff, sl = resv_part()
    lev.to_csv(f"{PFX}_resv.csv", index=False)
    diff.to_csv(f"{PFX}_resv_diff.csv", index=False)
    sl.to_csv(f"{PFX}_resv_slope.csv", index=False)
    print("\nRESERVATION PRICE on partial-cut days")
    print(lev.round(2).to_string(index=False))
    print(diff.round(2).to_string(index=False))
    print(sl.round(3).to_string(index=False))
    print(f"\nwrote {PFX.relative_to(ROOT)}_*.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
