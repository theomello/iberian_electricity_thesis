"""Area-panel replication per regulated consumer (docs/specs/2026-11-12-area-panel-percapita-design.md).

Same design as tou_area_panel.py (paper LASSO per area and hour; errors on post x Spain x period type; Equation 4), with log load per regulated domestic supply point. Spanish counts: CNMC quarterly
regulated domestic points by group (outputs/tables/cnmc_regulated_points_quarterly.csv), monotone cubic (PCHIP) to daily between 2018-03-31 and 2021-09-30; Portugal: ERSE regulated (CUR) clients by month
(erse_regulated_clients_monthly.csv), PCHIP across the missing months. Sample from 2018-04-01. Version M: Portuguese regulated unit per consumer as control; version F: Portuguese national consumption (REN).
Robustness: counts shifted by +-0.5 points of regulated share in the whole-percent quarters (2018-03 .. 2019-09), the Q3 2019 count dropped, PDBF stage, unweighted. Placebo: 18 windows of 106 days (2018-04 .. 2019-09 starts).
Writes outputs/tables/tou_area_panel_pc_*.csv and prints the eight pre-registered rules.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.interpolate import PchipInterpolator

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_area_panel as AP  # noqa: E402
import tou_did as T  # noqa: E402
import tou_elasticity_paper as EL  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_lasso_paper as L  # noqa: E402

AREAS = AP.AREAS
POST0, POST1 = AP.POST0, AP.POST1
START = pd.Timestamp("2018-04-01")
CACHE = T.ROOT / "data" / "cache_tou"


def daily(s):
    s = s.dropna().sort_index()
    f = PchipInterpolator(s.index.map(pd.Timestamp.toordinal).to_numpy(float), s.to_numpy(float))
    idx = pd.date_range(s.index.min(), s.index.max())
    return pd.Series(f(idx.map(pd.Timestamp.toordinal).to_numpy(float)), index=idx)


def spain_counts(shift=0.0, drop_q3_2019=False):
    c = pd.read_csv(T.OUT / "cnmc_regulated_points_quarterly.csv", parse_dates=["quarter_end"])
    out = {}
    for a in AREAS:
        g = c[c.area == a].set_index("quarter_end")
        share = g.regulated_share_domestic.copy()
        if shift:
            share[g.share_decimals == 0] += shift
        pts = g.domestic_supply_points * share
        if drop_q3_2019:
            pts = pts.drop(pd.Timestamp("2019-09-30"))
        out[a] = daily(pts)
    return out


def pt_counts():
    e = pd.read_csv(T.OUT / "erse_regulated_clients_monthly.csv")
    s = pd.Series(e.regulated_clients_cur.to_numpy(), index=pd.to_datetime(e.month) + pd.offsets.MonthEnd(0))
    return daily(s[s.index <= "2021-12-31"])


def add_pc(x, counts, suffix, stage="p48", ptc=None):
    for a in AREAS:
        x[f"pc_{a}_{stage}{suffix}"] = x[f"load_{a}_{stage}"] / x.date.map(counts[a])
    if ptc is not None:
        x["pc_PTU"] = x.load_PTU / x.date.map(ptc)


def one_task(name, x, load, temp, hol, excl):
    xx = x[x[load] > 0]
    return name, excl, L.area_errors(xx, load, temp, hol, excl)


def get_errors(x):
    path = CACHE / "area_panel_pc_errors.parquet"
    if path.exists() and "--refit" not in sys.argv:
        c = pd.read_parquet(path)
        return {tuple(k.split("|", 1)): c[k] for k in c.columns}
    tasks = []
    for ex in ((), (2018,), (2019,)):
        for a in AREAS:
            tasks.append((f"{a}_p48", x, f"pc_{a}_p48", "temp_es", "hol_es", ex))
        tasks.append(("PTU", x, "pc_PTU", "temp_pt", "hol_pt", ex))
        tasks.append(("PTREN", x, "load_pt", "temp_pt", "hol_pt", ex))
    for a in AREAS:
        tasks.append((f"{a}_pdbf", x, f"pc_{a}_pdbf", "temp_es", "hol_es", ()))
        tasks.append((f"{a}_up", x, f"pc_{a}_p48_up", "temp_es", "hol_es", ()))
        tasks.append((f"{a}_dn", x, f"pc_{a}_p48_dn", "temp_es", "hol_es", ()))
        tasks.append((f"{a}_nq3", x, f"pc_{a}_p48_nq3", "temp_es", "hol_es", ()))
    tasks.append(("E352", x, "load_352", "temp_es", "hol_es", ()))
    res = Parallel(n_jobs=min(4, os.cpu_count() or 1), verbose=5)(delayed(one_task)(*t) for t in tasks)
    errs = {(n, str(ex)): e for n, ex, e in res}
    CACHE.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({f"{k[0]}|{k[1]}": v for k, v in errs.items()}).to_parquet(path)
    return errs


def compute(get_errors_fn, prefix="tou_area_panel_pc", prep=None):
    """Fit (or load) the errors, estimate every specification and write the CSVs.

    Reusable for any variant of the design: `get_errors_fn(x)` returns the area errors (a variant can change the
    temperature source, the window or the controls), `prep(x, counts, ptc)` may add columns to x first, and
    `prefix` names the output files. Returns the pieces the rule reports read."""
    x = AP.load_frame()
    x = x[(x.date >= START) & (x.date <= POST1)].copy()
    cs, ptc = spain_counts(), pt_counts()
    add_pc(x, cs, "", "p48", ptc)
    add_pc(x, cs, "", "pdbf")
    add_pc(x, spain_counts(+0.005), "_up", "p48")
    add_pc(x, spain_counts(-0.005), "_dn", "p48")
    add_pc(x, spain_counts(drop_q3_2019=True), "_nq3", "p48")
    if prep is not None:
        prep(x, cs, ptc)
    print(f"rows {len(x)}", flush=True)

    # rule 1: counts valid
    c = pd.read_csv(T.OUT / "cnmc_regulated_points_quarterly.csv", parse_dates=["quarter_end"])
    q = c.pivot(index="quarter_end", columns="area", values="regulated_points_domestic")[AREAS]
    qq = q.pct_change().dropna().abs().max().max()
    print(f"RULE 1 largest quarter-on-quarter change in a count: {100 * qq:.1f}% (<= 10% needed); sum check 99.1-99.9% (at build):", bool(qq <= 0.10), flush=True)

    errs = get_errors_fn(x)
    print("errors ready", flush=True)
    covid = x.date.between(*EV.COVID)
    pre = (x.date >= START) & (x.date <= "2020-12-31") & ~covid
    w = {a: float(x.loc[pre, f"date"].map(cs[a]).mean()) for a in AREAS}
    w["PT"] = float(x.loc[pre, "date"].map(ptc).mean())
    print("pre-window mean regulated points:", {k: round(v) for k, v in w.items()}, flush=True)
    ea = {a: errs[(f"{a}_p48", "()")] for a in AREAS}
    ptu, ptr = errs[("PTU", "()")], errs[("PTREN", "()")]
    real_mask = pre | ((x.date >= POST0) & (x.date <= POST1))
    TY = ["wd_peak", "wd_mid", "wd_off", "we_peak", "we_mid", "we_off"]
    out = []

    def add(spec, S, weighted=True):
        for k, (b, se) in AP.did_types(S, POST0, POST1, weighted).items():
            out.append(dict(spec=spec, term=k, b=b, se=se, t=b / se))
    SM = AP.long_stack(x, ea, ptu, AREAS, w, real_mask)
    add("M weighted", SM, True)
    add("M unweighted", SM, False)
    SF = AP.long_stack(x, ea, ptr, AREAS, w, real_mask)
    add("F REN control", SF, True)
    for a in AREAS:
        add(f"area {a}", AP.long_stack(x, {a: ea[a]}, ptu, [a], {a: w[a], "PT": w["PT"]}, real_mask), True)
    n2 = [a for a in AREAS if a != "ENDESA"]
    add("drop Endesa", AP.long_stack(x, {a: ea[a] for a in n2}, ptu, n2, w, real_mask), True)
    for tag, suf in (("PDBF stage", "pdbf"), ("share +0.5 pts", "up"), ("share -0.5 pts", "dn"), ("drop Q3 2019 count", "nq3")):
        add(tag, AP.long_stack(x, {a: errs[(f"{a}_{suf}", "()")] for a in AREAS}, ptu, AREAS, w, real_mask), True)
    R = pd.DataFrame(out)
    pd.set_option("display.width", 200)
    print(R[R.term.isin(TY) & R.spec.isin(["M weighted", "M unweighted", "F REN control", "PDBF stage", "drop Endesa"])].assign(b=lambda d: 100 * d.b, se=lambda d: 100 * d.se).round(2).to_string(index=False), flush=True)

    # placebo windows
    def cf(name):
        a, b = errs[(name, "(2018,)")], errs[(name, "(2019,)")]
        return pd.concat([a[x.date.reindex(a.index).dt.year == 2018], b[x.date.reindex(b.index).dt.year == 2019]])
    eac = {a: cf(f"{a}_p48") for a in AREAS}
    pmask = (x.date >= START) & (x.date <= "2019-12-31")
    pl = []
    for lab, ctl in (("M", cf("PTU")), ("F", cf("PTREN"))):
        Sc = AP.long_stack(x, eac, ctl, AREAS, w, pmask)
        for s0 in pd.date_range("2018-04-01", "2019-09-01", freq="MS"):
            e0 = s0 + pd.Timedelta(days=105)
            if e0 > pd.Timestamp("2019-12-31"):
                continue
            r = AP.did_types(Sc, s0, e0, True)
            pl.append(dict(version=lab, start=s0.date(), wd_peak=r["wd_peak"][0], wd_peak_t=r["wd_peak"][0] / r["wd_peak"][1], wd_mid=r["wd_mid"][0], wd_off=r["wd_off"][0]))
    PL = pd.DataFrame(pl)
    PLm = PL[PL.version == "M"]
    print(PLm.assign(wd_peak=lambda d: 100 * d.wd_peak, wd_mid=lambda d: 100 * d.wd_mid, wd_off=lambda d: 100 * d.wd_off).round(2).to_string(index=False), flush=True)

    # evening-vs-night DDD
    ep = AP.pooled_error(ea, AREAS, w, x.index)
    e352 = errs[("E352", "()")]
    ddd = {}
    for lab, err in (("pooled areas per consumer vs Portuguese unit per consumer", ep - ptu.reindex(x.index)), ("352 vs Portuguese unit per consumer", e352.reindex(x.index) - ptu.reindex(x.index)),
                     ("pooled areas per consumer vs REN", ep - ptr.reindex(x.index)), ("352 vs REN", e352.reindex(x.index) - ptr.reindex(x.index))):
        b, se = L.cell_ddd(x, err, POST0, POST1)
        ddd[lab] = (b, se)
        print(f"DDD evening vs night {lab}: {100 * b:.2f}% (se {100 * se:.2f})", flush=True)

    # elasticity
    p, ebar = EL.prices()
    cols_all = {}
    for lab, ctl, ctlcf in (("M", ptu, cf("PTU")), ("F", ptr, cf("PTREN"))):
        ESP = AP.long_stack(x, ea, ctl, AREAS, w, real_mask).merge(p, on=["date", "hour"], how="left")
        ESP["lnp"] = np.where(ESP.spain == 1, np.log(ESP.price), 0.0)
        ESP["z"] = np.where(ESP.spain == 1, np.log(ESP.charge + ebar), 0.0)
        ESP = ESP.dropna(subset=["lnp", "z"]).reset_index(drop=True)
        g = pd.factorize(ESP.area.astype(str) + "_" + ESP.ym)[0]
        cols = EL.fit_columns(ESP, g)
        real = p[(p.date >= POST0) & (p.date <= POST1)].copy()
        real["m"], real["wk"] = real.date.dt.month, (real.date.dt.dayofweek >= 5).astype(int)
        pat = real.groupby(["m", "hour", "wk"]).charge.mean()
        PS = AP.long_stack(x, eac, ctlcf, AREAS, w, pmask)
        PS["z"] = np.where(PS.spain == 1, np.log(EL.OLD + ebar), 0.0)
        inwin = (PS.spain == 1) & (PS.date >= "2019-06-01") & (PS.date <= "2019-09-14")
        idx = pd.MultiIndex.from_arrays([PS.date.dt.month[inwin], PS.hour[inwin], PS.wk[inwin]])
        cp = pd.Series(pat.reindex(idx).to_numpy(), index=PS.index[inwin])
        ok = cp.notna()
        PS.loc[cp.index[ok], "z"] = np.log(cp[ok] + ebar)
        PS["lnp"] = PS.z
        gp = pd.factorize(PS.area.astype(str) + "_" + PS.ym)[0]
        Fp = EL.fe_matrix(PS, 1)
        bp, sep, _ = EL.iv(EL.resid(Fp, PS.e), EL.resid(Fp, PS.lnp), EL.resid(Fp, PS.lnp), gp)
        print(f"elasticity ({lab}) placebo 2019: eta {bp[0]:.3f} (se {sep[0]:.3f}, t {bp[0] / sep[0]:.2f})", flush=True)
        cols_all[lab] = (cols, bp[0], sep[0])

    R.round(5).to_csv(T.OUT / f"{prefix}_effects.csv", index=False)
    PL.round(5).to_csv(T.OUT / f"{prefix}_placebo.csv", index=False)
    pd.concat([pd.DataFrame(v[0]).assign(version=k, placebo_eta=v[1], placebo_se=v[2]) for k, v in cols_all.items()]).round(5).to_csv(T.OUT / f"{prefix}_elasticity.csv", index=False)
    pd.DataFrame([dict(comparison=k, ddd=v[0], se=v[1]) for k, v in ddd.items()]).round(5).to_csv(T.OUT / f"{prefix}_ddd.csv", index=False)
    return dict(x=x, R=R, PL=PL, PLm=PLm, ddd=ddd, cols_all=cols_all, errs=errs)


def report(o):
    """The eight rules of the per-capita design (docs/specs/2026-11-12-area-panel-percapita-design.md)."""
    R, PL, PLm, ddd, cols_all = o["R"], o["PL"], o["PLm"], o["ddd"], o["cols_all"]
    ok = {}
    g_ = lambda spec, term: R[(R.spec == spec) & (R.term == term)].iloc[0]
    pk, md, off = g_("M weighted", "wd_peak"), g_("M weighted", "wd_mid"), g_("M weighted", "wd_off")
    r2 = bool(pk.t <= -2 and -0.15 <= pk.b <= -0.03 and md.b < 0 and md.t <= -2 and abs(off.b) < 0.03)
    ok[2] = r2
    print(f"\nRULE 2 (M) weekday peak {100 * pk.b:.2f}% (t {pk.t:.1f}), mid {100 * md.b:.2f}% (t {md.t:.1f}), off {100 * off.b:.2f}% (t {off.t:.1f}):", r2)
    for v, lab in (("M weighted", "M"), ("F REN control", "F")):
        a, b_, c_ = g_(v, "wd_peak"), g_(v, "wd_mid"), g_(v, "wd_off")
        print(f"   ({lab}) peak {100 * a.b:.2f}, mid {100 * b_.b:.2f}, off {100 * c_.b:.2f}; peak-off {100 * (a.b - c_.b):.2f}")
    rank = int((PLm.wd_peak.abs() >= abs(pk.b)).sum()) + 1
    c4, bp, sep = [c for c in cols_all["M"][0] if c["col"] == 4][0], cols_all["M"][1], cols_all["M"][2]
    print(f"RULE 3 (M) rank of the real weekday peak effect: {rank} of {len(PLm) + 1} (top 3 needed); elasticity placebo t {bp / sep:.2f} (> -2 needed):", ok.setdefault(3, bool(rank <= 3 and bp / sep > -2)))
    neg = {a: bool(g_(f"area {a}", "wd_peak").b < 0) for a in AREAS}
    print("RULE 4 areas with negative weekday peak:", neg, sum(neg.values()), "of 5 (>= 4 needed)")
    ok[4] = sum(neg.values()) >= 4
    ok[5] = bool(c4["eta"] < 0 and c4["t"] <= -2 and -0.20 <= c4["eta"] <= -0.05 and c4["first_stage_F"] >= 10)
    print(f"RULE 5 (M) column 4 eta {c4['eta']:.3f} (se {c4['se']:.3f}, t {c4['t']:.1f}, F {c4['first_stage_F']:.1f}):", ok[5])
    print("   all columns (M):", [(c["col"], round(c["eta"], 3), round(c["t"], 1), round(c["first_stage_F"], 0)) for c in cols_all["M"][0]], "| (F):", [(c["col"], round(c["eta"], 3), round(c["t"], 1), round(c["first_stage_F"], 0)) for c in cols_all["F"][0]])
    d6 = abs(ddd["pooled areas per consumer vs Portuguese unit per consumer"][0] - ddd["352 vs Portuguese unit per consumer"][0])
    ok[6] = bool(d6 < 0.015)
    print(f"RULE 6 pooled areas minus 352 DDD: {100 * d6:.2f} points (< 1.5 needed):", ok[6])
    dev = {k: abs(g_(s, "wd_peak").b - pk.b) for k, s in (("drop Endesa", "drop Endesa"), ("unweighted", "M unweighted"), ("PDBF", "PDBF stage"), ("REN control", "F REN control"))}
    sh = {k: abs(g_(s, "wd_peak").b - pk.b) for k, s in (("share +0.5", "share +0.5 pts"), ("share -0.5", "share -0.5 pts"), ("drop Q3 2019", "drop Q3 2019 count"))}
    print("RULE 7 deviations of the weekday peak effect (points):", {k: round(100 * v, 2) for k, v in dev.items()}, "(each < 2) and", {k: round(100 * v, 2) for k, v in sh.items()}, "(each < 1):",
          bool(max(dev.values()) < 0.02 and max(sh.values()) < 0.01))
    old = pd.read_csv(T.OUT / "tou_area_panel_placebo.csv")
    sd_old, sd_new_m, sd_new_f = old.wd_off.std(), PLm.wd_off.std(), PL[PL.version == "F"].wd_off.std()
    print(f"RULE 8 sd of weekday off-peak placebo effects: without counts {100 * sd_old:.2f} pts; per consumer (M) {100 * sd_new_m:.2f}, (F) {100 * sd_new_f:.2f} (must fall by at least half):",
          bool(sd_new_m <= 0.5 * sd_old))
    ok[7] = bool(max(dev.values()) < 0.02 and max(sh.values()) < 0.01)
    ok[8] = bool(sd_new_m <= 0.5 * sd_old)
    return ok


def main():
    report(compute(get_errors))


if __name__ == "__main__":
    main()
