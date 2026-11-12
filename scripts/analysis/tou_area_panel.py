"""Replication of Enrich, Li, Mizrahi and Reguant on the rebuilt regulated-retailer area panel (docs/specs/2026-11-12-area-panel-design.md and its amendment).

Areas: Endesa, Iberdrola, Naturgy, EDP, Repsol (REE final schedule P48, build_regulated_area_p48.py; PDBF version as robustness), Portugal = OMIE PDBF of the regulated supplier (SU Eletricidade, Lisbon clock).
Step 1: the paper's LASSO per area and hour (tou_lasso_paper.area_errors), 2018-01-01 -> 2020-12-31 without March-June 2020, log load. Step 2: errors on post x Spain x period type (weekday peak/mid/off,
weekend fake types) with area x hour x weekend and month-of-sample x weekend effects, weighted by pre-window mean load, clustered by area x month-of-sample. Post window 2021-06-01 -> 2021-09-14.
Placebo: 21 windows of 106 days (2018-01 ... 2019-09 starts) on errors cross-fitted by leaving 2018 and 2019 out in turn. Elasticity: the paper's Equation 4 on the area panel (tou_elasticity_paper machinery).
Writes outputs/tables/tou_area_panel_*.csv and prints the seven pre-registered rules.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from joblib import Parallel, delayed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402  (esios_load)
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_elasticity_paper as EL  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_lasso_paper as L  # noqa: E402

TSP = pd.Timestamp
POST0, POST1 = TSP("2021-06-01"), TSP("2021-09-14")
AREAS = ["ENDESA", "IBERDROLA", "NATURGY", "EDP", "REPSOL"]
PANEL = T.OUT / "regulated_area_panel"
CACHE = T.ROOT / "data" / "cache_tou"
TYPES = ["peak", "mid", "off"]


# ---------- data ----------
def load_frame():
    x = D.prep(T.build("e0", end="2021-09-14"))
    p = pd.read_parquet(PANEL / "regulated_area_p48_hourly.parquet")
    p["date"] = pd.to_datetime(p.date)
    for a in AREAS:
        s = p[p.area == a].drop_duplicates(["date", "hour"])
        for col, nm in (("p48_mwh", "p48"), ("pdbf_mwh", "pdbf")):
            v = s[["date", "hour", col]].rename(columns={col: f"load_{a}_{nm}"})
            v.loc[v[f"load_{a}_{nm}"] <= 0, f"load_{a}_{nm}"] = np.nan
            x = x.merge(v, on=["date", "hour"], how="left")
    q = pd.read_parquet(PANEL / "regulated_area_hourly.parquet")
    q = q[q.area == "PORTUGAL"]
    loc = q.utc_timestamp.dt.tz_convert("Europe/Lisbon")
    pt = pd.DataFrame({"date": pd.to_datetime(loc.dt.date.to_numpy()), "hour": loc.dt.hour.to_numpy(), "load_PTU": q.load_mw.to_numpy()}).drop_duplicates(["date", "hour"])
    x = x.merge(pt, on=["date", "hour"], how="left")
    x = x.merge(CT.esios_load([352]).rename(columns={"v": "load_352"}), on=["date", "hour"], how="left")
    return x


def one_task(name, x, load, temp, hol, excl):
    xx = x[x[load] > 0]
    return name, excl, L.area_errors(xx, load, temp, hol, excl)


def get_errors(x):
    path = CACHE / "area_panel_errors.parquet"
    if path.exists() and "--refit" not in sys.argv:
        c = pd.read_parquet(path)
        return {tuple(k.split("|", 1)): c[k] for k in c.columns}
    CACHE.mkdir(parents=True, exist_ok=True)
    tasks = []
    for ex in ((), (2018,), (2019,)):
        for a in AREAS:
            tasks.append((f"{a}_p48", x, f"load_{a}_p48", "temp_es", "hol_es", ex))
        tasks.append(("PTU", x, "load_PTU", "temp_pt", "hol_pt", ex))
    for a in AREAS:
        tasks.append((f"{a}_pdbf", x, f"load_{a}_pdbf", "temp_es", "hol_es", ()))
    tasks.append(("PTREN", x, "load_pt", "temp_pt", "hol_pt", ()))
    tasks.append(("E352", x, "load_352", "temp_es", "hol_es", ()))
    res = Parallel(n_jobs=min(4, os.cpu_count() or 1), verbose=5)(delayed(one_task)(*t) for t in tasks)
    errs = {(n, str(ex)): e for n, ex, e in res}
    pd.DataFrame({f"{k[0]}|{k[1]}": v for k, v in errs.items()}).to_parquet(path)
    return errs


# ---------- regression on errors ----------
def onehot(*cols):
    code = pd.factorize(pd.Series(list(zip(*cols))))[0]
    return sp.csr_matrix((np.ones(len(code)), (np.arange(len(code)), code)), shape=(len(code), code.max() + 1))


def long_stack(x, ea, ept, names, w, mask):
    """Rows of every Spanish area and the Portuguese unit; ea: dict name -> error Series; weights w: dict."""
    parts = []
    for i, a in enumerate(names):
        e = ea[a]
        d = x.loc[mask & e.reindex(x.index).notna()]
        parts.append(pd.DataFrame({"area": i, "date": d.date, "hour": d.hour, "wk": d.weekend.astype(int), "e": e.reindex(d.index), "spain": 1, "kind": d.kind, "w": w[a],
                                   "hdh": np.maximum(18 - d.temp_es, 0), "cdh": np.maximum(d.temp_es - 18, 0)}))
    d = x.loc[mask & ept.reindex(x.index).notna()]
    parts.append(pd.DataFrame({"area": len(names), "date": d.date, "hour": d.hour, "wk": ((d.dow >= 5) | (d.hol_pt == 1)).astype(int), "e": ept.reindex(d.index), "spain": 0, "kind": d.kind,
                               "w": w["PT"], "hdh": np.maximum(18 - d.temp_pt, 0), "cdh": np.maximum(d.temp_pt - 18, 0)}))
    s = pd.concat(parts, ignore_index=True)
    s["ym"] = s.date.dt.strftime("%Y-%m")
    s["moy"] = s.date.dt.month
    s["type"] = np.where(s.hour < 8, "off", np.where(s.hour.isin([10, 11, 12, 13, 18, 19, 20, 21]), "peak", "mid"))
    return s


def cluster_ols(y, X, g):
    Ai = np.linalg.inv(X.T @ X)
    b = Ai @ (X.T @ y)
    u = y - X @ b
    sums = pd.DataFrame(X * u[:, None]).groupby(g).sum().to_numpy()
    G = len(sums)
    return b, Ai @ (sums.T @ sums) @ Ai * G / (G - 1)


def did_types(s, p0, p1, weighted=True):
    sw = np.sqrt(s.w.to_numpy()) if weighted else np.ones(len(s))
    F = sp.hstack([onehot(s.area, s.hour, s.wk), onehot(s.ym, s.wk)]).tocsr()
    Fw = sp.diags(sw) @ F
    post = ((s.date >= p0) & (s.date <= p1) & (s.spain == 1)).to_numpy()
    cols, names = [], []
    for kind, lab in (("work", "wd"), ("wknd", "we")):
        for t in TYPES:
            cols.append((post & (s.kind.to_numpy() == kind) & (s["type"].to_numpy() == t)).astype(float))
            names.append(f"{lab}_{t}")
    y = EL.resid(Fw, s.e.to_numpy() * sw)
    X = np.column_stack([EL.resid(Fw, c * sw) for c in cols])
    g = pd.factorize(s.area.astype(str) + "_" + s.ym)[0]
    b, V = cluster_ols(y, X, g)
    return {n: (b[i], np.sqrt(V[i, i])) for i, n in enumerate(names)}


def pooled_error(ea, names, w, index):
    num = sum(w[a] * ea[a].reindex(index).fillna(0) for a in names)
    den = sum(w[a] * ea[a].reindex(index).notna() for a in names)
    return (num / den.replace(0, np.nan))


def main():
    x = load_frame()
    print(f"rows {len(x)}; missing by area p48:", {a: int(x[f'load_{a}_p48'].isna().sum()) for a in AREAS}, "PTU", int(x.load_PTU.isna().sum()), flush=True)
    errs = get_errors(x)
    print("errors ready", flush=True)
    covid = x.date.between(*EV.COVID)
    pre = (x.date >= "2018-01-01") & (x.date <= "2020-12-31") & ~covid
    w = {a: float(x.loc[pre, f"load_{a}_p48"].mean()) for a in AREAS}
    w["PT"] = float(x.loc[pre, "load_PTU"].mean())
    print("pre-window mean MW:", {k: round(v, 1) for k, v in w.items()}, flush=True)
    ea = {a: errs[(f"{a}_p48", "()")] for a in AREAS}
    ept = errs[("PTU", "()")]
    real_mask = (pre | ((x.date >= POST0) & (x.date <= POST1)))

    out = []
    # --- main (weighted) and unweighted, P48
    S = long_stack(x, ea, ept, AREAS, w, real_mask)
    for lab, wt in (("weighted", True), ("unweighted", False)):
        r = did_types(S, POST0, POST1, wt)
        for k, (b, se) in r.items():
            out.append(dict(spec=f"P48 {lab}", term=k, b=b, se=se, t=b / se))
    main_r = {r["term"]: r for r in out if r["spec"] == "P48 weighted"}
    # --- by area
    for i, a in enumerate(AREAS):
        Sa = long_stack(x, {a: ea[a]}, ept, [a], {a: w[a], "PT": w["PT"]}, real_mask)
        r = did_types(Sa, POST0, POST1, True)
        for k, (b, se) in r.items():
            out.append(dict(spec=f"area {a}", term=k, b=b, se=se, t=b / se))
    # --- drop Endesa
    names2 = [a for a in AREAS if a != "ENDESA"]
    S2 = long_stack(x, {a: ea[a] for a in names2}, ept, names2, w, real_mask)
    for k, (b, se) in did_types(S2, POST0, POST1, True).items():
        out.append(dict(spec="drop Endesa", term=k, b=b, se=se, t=b / se))
    # --- PDBF stage
    eap = {a: errs[(f"{a}_pdbf", "()")] for a in AREAS}
    Sp = long_stack(x, eap, ept, AREAS, w, real_mask)
    for k, (b, se) in did_types(Sp, POST0, POST1, True).items():
        out.append(dict(spec="PDBF stage", term=k, b=b, se=se, t=b / se))
    # --- Portugal national (REN) in place of the regulated unit
    Sr = long_stack(x, ea, errs[("PTREN", "()")], AREAS, w, real_mask)
    for k, (b, se) in did_types(Sr, POST0, POST1, True).items():
        out.append(dict(spec="Portugal REN", term=k, b=b, se=se, t=b / se))
    R = pd.DataFrame(out)
    pd.set_option("display.width", 200)
    print(R[R.term.isin(["wd_peak", "wd_mid", "wd_off", "we_peak", "we_mid", "we_off"])].assign(b=lambda d: 100 * d.b, se=lambda d: 100 * d.se).round(2).to_string(index=False), flush=True)

    # --- placebo windows (cross-fitted 2018, 2019)
    def cf(name):
        a, b = errs[(name, "(2018,)")], errs[(name, "(2019,)")]
        return pd.concat([a[x.date.reindex(a.index).dt.year == 2018], b[x.date.reindex(b.index).dt.year == 2019]])
    eac = {a: cf(f"{a}_p48") for a in AREAS}
    eptc = cf("PTU")
    pmask = (x.date >= "2018-01-01") & (x.date <= "2019-12-31")
    Sc = long_stack(x, eac, eptc, AREAS, w, pmask)
    pl = []
    for s0 in pd.date_range("2018-01-01", "2019-09-01", freq="MS"):
        e0 = s0 + pd.Timedelta(days=105)
        if e0 > TSP("2019-12-31"):
            continue
        r = did_types(Sc, s0, e0, True)
        pl.append(dict(start=s0.date(), wd_peak=r["wd_peak"][0], wd_peak_t=r["wd_peak"][0] / r["wd_peak"][1], wd_mid=r["wd_mid"][0], wd_off=r["wd_off"][0]))
    PL = pd.DataFrame(pl)
    print(PL.assign(wd_peak=lambda d: 100 * d.wd_peak, wd_mid=lambda d: 100 * d.wd_mid, wd_off=lambda d: 100 * d.wd_off).round(2).to_string(index=False), flush=True)

    # --- evening-vs-night DDD, pooled areas, 352
    ep = pooled_error(ea, AREAS, w, x.index)
    ddd = {}
    for lab, err in (("pooled areas vs Portuguese unit", ep - ept.reindex(x.index)), ("352 vs Portuguese unit", errs[("E352", "()")].reindex(x.index) - ept.reindex(x.index)),
                     ("352 vs REN", errs[("E352", "()")].reindex(x.index) - errs[("PTREN", "()")].reindex(x.index)),
                     ("pooled areas vs REN", ep - errs[("PTREN", "()")].reindex(x.index))):
        b, se = L.cell_ddd(x, err, POST0, POST1)
        ddd[lab] = (b, se)
        print(f"DDD evening vs night {lab}: {100 * b:.2f}% (se {100 * se:.2f})", flush=True)

    # --- elasticity (Equation 4) on the area panel
    p, ebar = EL.prices()
    ESP = long_stack(x, ea, ept, AREAS, w, real_mask)
    ESP = ESP.merge(p, on=["date", "hour"], how="left")
    ESP["lnp"] = np.where(ESP.spain == 1, np.log(ESP.price), 0.0)
    ESP["z"] = np.where(ESP.spain == 1, np.log(ESP.charge + ebar), 0.0)
    ESP = ESP.dropna(subset=["lnp", "z"]).reset_index(drop=True)
    g = pd.factorize(ESP.area.astype(str) + "_" + ESP.ym)[0]
    cols = EL.fit_columns(ESP, g)
    # placebo for the elasticity: real charge pattern laid on 2019-06-01 -> 2019-09-14, errors cross-fitted
    real = p[(p.date >= POST0) & (p.date <= POST1)].copy()
    real["m"], real["wk"] = real.date.dt.month, (real.date.dt.dayofweek >= 5).astype(int)
    pat = real.groupby(["m", "hour", "wk"]).charge.mean()
    PS = long_stack(x, eac, eptc, AREAS, w, pmask)
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
    print(f"elasticity placebo 2019: eta {bp[0]:.3f} (se {sep[0]:.3f}, t {bp[0] / sep[0]:.2f})", flush=True)

    # ---- outputs
    R.round(5).to_csv(T.OUT / "tou_area_panel_effects.csv", index=False)
    PL.round(5).to_csv(T.OUT / "tou_area_panel_placebo.csv", index=False)
    pd.DataFrame(cols).assign(placebo_eta=bp[0], placebo_se=sep[0]).round(5).to_csv(T.OUT / "tou_area_panel_elasticity.csv", index=False)
    pd.DataFrame([dict(comparison=k, ddd=v[0], se=v[1]) for k, v in ddd.items()]).round(5).to_csv(T.OUT / "tou_area_panel_ddd.csv", index=False)

    # ---- rules
    g_ = lambda spec, term: R[(R.spec == spec) & (R.term == term)].iloc[0]
    pk, md, off = g_("P48 weighted", "wd_peak"), g_("P48 weighted", "wd_mid"), g_("P48 weighted", "wd_off")
    print("\nRULE 1 panel validity: checked at build (areas sum to 352 within 1.0%)")
    r2 = bool(pk.t <= -2 and -0.15 <= pk.b <= -0.03 and md.b < 0 and md.t <= -2 and abs(off.b) < 0.03)
    print(f"RULE 2 weekday peak {100 * pk.b:.2f}% (t {pk.t:.1f}), mid {100 * md.b:.2f}% (t {md.t:.1f}), off {100 * off.b:.2f}% (t {off.t:.1f}):", r2)
    rank = int((PL.wd_peak.abs() >= abs(pk.b)).sum()) + 1
    print(f"RULE 3 placebo rank of the real weekday peak effect: {rank} of {len(PL) + 1} (top 3 needed); elasticity placebo t {bp[0] / sep[0]:.2f} (> -2 needed):", bool(rank <= 3 and bp[0] / sep[0] > -2))
    neg = {a: bool(g_(f"area {a}", "wd_peak").b < 0) for a in AREAS}
    print("RULE 4 areas with negative weekday peak:", neg, sum(neg.values()), "of 5 (>= 4 needed)")
    c4 = [c for c in cols if c["col"] == 4][0]
    print(f"RULE 5 column 4 eta {c4['eta']:.3f} (se {c4['se']:.3f}, t {c4['t']:.1f}, F {c4['first_stage_F']:.1f}): ", bool(c4["eta"] < 0 and c4["t"] <= -2 and -0.20 <= c4["eta"] <= -0.05 and c4["first_stage_F"] >= 10))
    d6 = abs(ddd["pooled areas vs Portuguese unit"][0] - ddd["352 vs Portuguese unit"][0])
    print(f"RULE 6 pooled-areas DDD minus 352 DDD (both vs Portuguese unit): {100 * d6:.2f} points (< 1.5 needed):", bool(d6 < 0.015))
    de = abs(g_("drop Endesa", "wd_peak").b - pk.b)
    dw = abs(g_("P48 unweighted", "wd_peak").b - pk.b)
    dr = abs(g_("Portugal REN", "wd_peak").b - pk.b)
    dp = abs(g_("PDBF stage", "wd_peak").b - pk.b)
    print(f"RULE 7 robustness (points of weekday peak effect): drop Endesa {100 * de:.2f}, unweighted {100 * dw:.2f}, Portugal REN {100 * dr:.2f}, PDBF {100 * dp:.2f} (each < 2 needed):", bool(max(de, dw, dr, dp) < 0.02))


if __name__ == "__main__":
    main()
