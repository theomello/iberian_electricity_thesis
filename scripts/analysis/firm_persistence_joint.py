"""docs/specs/2026-11-26-persistence-joint-design.md: persistence 2022-25 (Part A, summers) with counterfactual-calendar controls.

    .venv/bin/python scripts/analysis/firm_persistence_joint.py

Same cells, years, placebo and post sets, statistic and inference as firm_persistence.py (registered 2026-11-23); every year's cell regression
additionally contains J principal components of the screened shifted-calendar steps d_k(c) (shift k in +-3..+-9 hours, |corr(d_k, d)| <= 0.5
over the group's summer cells; components covering 90% of their variance, at most 5; computed once per group). P0 gate: with no controls the
code reproduces the registered main statistic. Writes outputs/tables/firm_persistence_joint{,_summary}.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import firm_persistence as FP  # noqa: E402
import firm_persistence_step0 as F  # noqa: E402
import mf_period_calendar_estimate as MFE  # noqa: E402
import tou_tariff_schedule as TS  # noqa: E402

OUT = F.OUT
POST = F.POST
SHIFTS = [k for k in range(-9, 10) if abs(k) >= 3]


def fit_c(c, form, ctrl):
    """Coefficient on d with optional control columns (same effects as firm_persistence.fit)."""
    if form == "fe":
        key = c.series.astype(str) + "|" + c.hour.astype(str)
        cols = [(key == k).astype(float).to_numpy() for k in sorted(key.unique())]
    else:
        cols = [np.ones(len(c))]
    n_eff = len(cols)
    cols.append(c.d.to_numpy())
    for x in ctrl:
        cols.append(c[x].to_numpy())
    return float(np.linalg.lstsq(np.column_stack(cols), c.s.to_numpy(), rcond=None)[0][n_eff])


def var_left(c, form, ctrl):
    if form == "fe":
        key = c.series.astype(str) + "|" + c.hour.astype(str)
        cols = [(key == k).astype(float).to_numpy() for k in sorted(key.unique())]
    else:
        cols = [np.ones(len(c))]
    for x in ctrl:
        cols.append(c[x].to_numpy())
    A, d = np.column_stack(cols), c.d.to_numpy()
    r = d - A @ np.linalg.lstsq(A, d, rcond=None)[0]
    return float(r.var() / d.var())


def controls(g, spec, hol, holy):
    june_split = g == "medium"
    dts = pd.date_range("2021-06-01", "2021-09-30")
    n0 = list(spec["series"])[0]
    tar = spec["tariff"] if spec["tariff"] else n0
    d0 = F.d_table(tar, dts, hol | holy, june_split)
    orig = TS.new_period_6
    ks = {}
    for k in SHIFTS:
        TS.new_period_6 = lambda d, h, hl, k=k: orig(d, (h + k) % 24, hl)
        try:
            dk = F.d_table(tar, dts, hol | holy, june_split)
        finally:
            TS.new_period_6 = orig
        if abs(float(np.corrcoef(d0.to_numpy(), dk.reindex(d0.index).to_numpy())[0, 1])) <= 0.5:
            ks[k] = dk.reindex(d0.index)
    M = pd.DataFrame(ks)
    Z = M.to_numpy() - M.to_numpy().mean(0)
    U, sv, Vt = np.linalg.svd(Z, full_matrices=False)
    cum = np.cumsum(sv ** 2) / (sv ** 2).sum()
    J = int(min(5, np.searchsorted(cum, 0.90) + 1))
    pcs = pd.DataFrame(U[:, :J] * sv[:J], index=M.index, columns=[f"pc{j + 1}" for j in range(J)]).reset_index()
    return pcs, sorted(ks), J, float(cum[J - 1])


def run_joint(g, spec, loads, ps, hol, holy, drop, use_ctrl, pcs):
    june_split = g == "medium"
    main_form = "fe" if spec["fe"] else "int"
    tar_of = (lambda n: spec["tariff"]) if spec["tariff"] else (lambda n: n)
    dts = pd.date_range("2021-06-01", "2021-09-30")
    dt = {n: F.d_table(tar_of(n), dts, hol | holy, june_split) for n in loads}
    years = spec["years"]
    C = {}
    for y in years + POST + [2021]:
        d0, d1 = pd.Timestamp(f"{y}-06-01"), pd.Timestamp(f"{y}-09-30")
        c = pd.concat([FP.cells_ps(F.frame(x, d0, d1, drop, [6, 7, 8, 9]), dt[n], june_split, n, ps) for n, x in loads.items()], ignore_index=True)
        C[y] = c.merge(pcs, on=["part", "hour"], how="left") if use_ctrl else c
    ctrl = [c for c in pcs.columns if c.startswith("pc")] if use_ctrl else []

    def bset(fun):
        return {y: fun(C[y]) for y in C}

    def wrong(c):
        fake = c[c.hour.between(8, 23)].groupby(["series", "part"]).d.mean()
        w = c[c.hour.between(1, 4)].copy()
        w["d"] = [fake[(s_, p_)] for s_, p_ in zip(w.series, w.part)]
        return fit_c(w, "fe", ctrl)

    B = {"main": bset(lambda c: fit_c(c, main_form, ctrl)),
         "solar_robust": bset(lambda c: fit_c(c[~c.hour.isin(F.SOLAR)], main_form, ctrl)),
         "no_august": bset(lambda c: fit_c(c[c.part != "08"], main_form, ctrl)),
         "wrong_hours": bset(wrong)}
    # price control with controls: price share as one more column
    def price(c):
        c = c.copy()
        return fit_c(c, main_form, ctrl + ["ps"])
    B["price_control"] = bset(price)
    if g == "large":
        for n in loads:
            B[f"series_{n}"] = bset(lambda c, n=n: fit_c(c[c.series == n], "int", ctrl))
    res = {}
    for name, b in B.items():
        r = FP.stats_of([b[y] for y in POST], [b[y] for y in years], years)
        r["trend_effect"], r["p_trend"] = FP.trend([b[y] for y in POST], POST, [b[y] for y in years], years)
        r["slope_se"] = r["s_e"] / np.sqrt(((np.asarray(years, float) - np.mean(years)) ** 2).sum())
        for y in POST + [2021]:
            r[f"eff_{y}"] = b[y] - r["m"]
        res[name] = r
    mn = res["main"]
    drops = {y: FP.stats_of([B["main"][z] for z in POST if z != y], [B["main"][z] for z in years], years)["p"] for y in POST}
    vleft = var_left(C[2022], main_form, ctrl)
    return res, drops, vleft, B["main"]


def main():
    pd.set_option("display.width", 250)
    hol = TS.holidays()
    holy = F.holy_days(range(2014, 2027))
    drop = hol | holy | {pd.Timestamp(f"{y}-01-01") for y in range(2014, 2027)}
    ps = MFE.price_share()
    reg = pd.read_csv(OUT / "firm_persistence.csv")
    rows, summ = [], []
    for g, spec in F.GROUPS.items():
        loads = {n: FP.load_all(ids) for n, ids in spec["series"].items()}
        pcs, ks, J, cum = controls(g, spec, hol, holy)
        print(f"\n=== {g}: {len(ks)} screened calendars {ks}; J = {J} ({cum:.2f} of variance)", flush=True)
        r0, _, _, _ = run_joint(g, spec, loads, ps, hol, holy, drop, False, pcs)
        rg = reg[(reg.group == g) & (reg.part == "A") & (reg.statistic == "main")].iloc[0]
        p0 = abs(r0["main"]["effect"] - rg.effect) < 1e-4 and abs(r0["main"]["p"] - rg.p) < 1e-4 and abs(r0["main"]["s"] - rg.s) < 1e-4
        print(f"P0 reproduction: effect {r0['main']['effect']:+.4f} (registered {rg.effect:+.4f}), p {r0['main']['p']:.4f} ({rg.p:.4f}), s {r0['main']['s']:.4f} ({rg.s:.4f}) -> {'pass' if p0 else 'FAIL'}", flush=True)
        if not p0:
            print("stop: P0 failed"); continue
        res, drops, vleft, bm = run_joint(g, spec, loads, ps, hol, holy, drop, True, pcs)
        mn = res["main"]
        for name, r in res.items():
            rows.append(dict(group=g, statistic=name, **r))
        sl_est = abs(mn["slope"]) >= 1.5 * mn["slope_se"]
        P = {"P1": vleft >= 0.20, "P2": not sl_est, "P3": mn["s"] <= rg.s,
             "P4": mn["effect"] < 0 and mn["p"] <= 0.05 and mn["p_conservative"] <= 0.10,
             "P5": (mn["trend_effect"] < 0 and mn["p_trend"] <= 0.10) and all(p <= 0.10 for p in drops.values()) and all(mn[f"eff_{y}"] < 0 for y in POST),
             "P6": rg.lo <= mn["effect"] <= rg.hi}
        robust = P["P1"] and P["P2"] and P["P4"] and P["P5"] and P["P6"]
        print(f"main with controls: effect {mn['effect']:+.4f} p {mn['p']:.4f} [{mn['lo']:+.4f}, {mn['hi']:+.4f}]  conservative p {mn['p_conservative']:.4f}; "
              f"trend effect {mn['trend_effect']:+.4f} p {mn['p_trend']:.4f}; placebo m {mn['m']:+.3f} s {mn['s']:.4f} slope {mn['slope']:+.4f} (se {mn['slope_se']:.4f})")
        print("per year effects: " + " ".join(f"{y}:{mn[f'eff_{y}']:+.3f}" for y in POST) + f" | 2021 {mn['eff_2021']:+.3f} | drop-one p " + " ".join(f"{y}:{p:.3f}" for y, p in drops.items()))
        print(f"registered: effect {rg.effect:+.4f} p {rg.p:.4f} [{rg.lo:+.4f}, {rg.hi:+.4f}] s {rg.s:.4f}")
        print(f"P1 var left {vleft:.2f}: {P['P1']} | P2 slope not established: {P['P2']} | P3 s {mn['s']:.4f} <= {rg.s:.4f}: {P['P3']} | P4: {P['P4']} | P5: {P['P5']} | P6: {P['P6']} -> robust to the drift: {robust}")
        print("reported, no verdict: " + " | ".join(f"{n}: {r['effect']:+.3f} (p {r['p']:.3f})" for n, r in res.items() if n != "main"))
        summ.append(dict(group=g, J=J, var_expl=cum, effect=mn["effect"], p=mn["p"], lo=mn["lo"], hi=mn["hi"], placebo_sd=mn["s"], registered_effect=rg.effect,
                         registered_lo=rg.lo, registered_hi=rg.hi, registered_s=rg.s, **P, robust=robust))
    pd.DataFrame(rows).to_csv(OUT / "firm_persistence_joint.csv", index=False)
    pd.DataFrame(summ).to_csv(OUT / "firm_persistence_joint_summary.csv", index=False)


if __name__ == "__main__":
    main()
