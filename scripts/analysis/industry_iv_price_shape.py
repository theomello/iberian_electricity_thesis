"""docs/specs/2026-11-17-industry-iv-price-shape-design.md (rules Q0-Q10).

    .venv/bin/python scripts/analysis/industry_iv_price_shape.py --sample primary --step 0
    .venv/bin/python scripts/analysis/industry_iv_price_shape.py --sample primary --step 1     # refuses to run if Q0 or Q2 failed in step 0
    .venv/bin/python scripts/analysis/industry_iv_price_shape.py --sample ext --step 0         # extension E1, spread form, 2024-01 -> 2025-09-30

One row per day. y = week-on-week change in ln(L_E / L_M) (industrial load ESIOS 1204-1207; E = hours 19-22, M = hours 11-15, Madrid time); x = week-on-week change in ln(p_E / p_M) (primary, log form) or in
(p_E - p_M) / pbar (extension, spread form). sigma = -slope of y on x. Instruments (week-on-week, standardised): W1 = change in (pc_E - pc_M), pc = min(ws/12, 1)^3 block means; S1 = change in the midday block's
mean solar radiation. Double ML (10 time blocks, 14 days purged) on weekday, month, day of year, E and M block temperature and demand-forecast changes, own lags of y and x at 7/14/28 days and gas; no realised
wind or solar. Inference: 1,000 permutations of the residualised instruments across days within year-month, seed 20261117 (`industry_iv_estimation.run_sub`). Step 0 prints no real-outcome slope: first stage F,
the idle test (S1 on ln(p_E / p_V)) and the planted-sigma gate (planted estimates contain the real component, as in the earlier planted tests). Outputs outputs/tables/industry_iv_price_shape_<sample>*.csv.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_iv_day_level as DL  # noqa: E402
import industry_iv_estimation as E  # noqa: E402
import industry_iv_noise_reducers as N  # noqa: E402
import tou_did as T  # noqa: E402

BLK = {**{h: "E" for h in range(19, 23)}, **{h: "M" for h in range(11, 16)}, **{h: "V" for h in range(1, 6)}}
SAMPLES = {"primary": dict(first="2019-01-01", last="2023-12-31", end="2023-12-31", form="log", regimes=(("2019-21H1", "2021-07-01", True), ("2021H2-23", "2021-07-01", False))),
           "ext": dict(first="2024-01-01", last="2025-09-30", end="2025-09-30", form="spread", mask_days=("2025-04-28", "2025-04-30"), regimes=(("2024", "2025-01-01", True), ("2025", "2025-01-01", False)))}
PLANTS = (0.05, 0.10, 0.15, 0.30)
GATE = 0.15
METHODS = ("N1", "N2", "N3")


def lin_matrix(d):
    dm = pd.get_dummies(d.date.dt.dayofweek, dtype=float).to_numpy()[:, 1:]
    mm = pd.get_dummies(d.date.dt.month, dtype=float).to_numpy()[:, 1:]
    return np.column_stack([dm, mm, d.d_tempE, d.d_tempM, d.d_demE, d.d_demM, d.d_y_7, d.d_y_14, d.d_y_28, d.d_x_7, d.d_x_14, d.d_x_28, d.gas])


def resid(Y, Xb, Xl, bl, dates, method):
    """Cross-fitted residuals (10 time blocks, 14 days purged each side) with learner N1 (boosting as the other designs), N2 (OLS on Xl) or N3 (regularised boosting)."""
    if method == "N1":
        return N.gb_resid(Y, Xb, bl, dates)
    R = np.zeros_like(Y)
    for k in np.unique(bl):
        te = bl == k
        d0, d1 = dates[te].min() - pd.Timedelta(days=14), dates[te].max() + pd.Timedelta(days=14)
        tr = ~((dates >= d0) & (dates <= d1))
        for j in range(Y.shape[1]):
            if method == "N2":
                m = LinearRegression().fit(Xl[tr], Y[tr, j])
                R[te, j] = Y[te, j] - m.predict(Xl[te])
            else:
                m = HistGradientBoostingRegressor(max_iter=100, learning_rate=0.05, max_leaf_nodes=8, min_samples_leaf=100, l2_regularization=5.0, early_stopping=False, random_state=N.SEED)
                m.fit(Xb[tr], Y[tr, j])
                R[te, j] = Y[te, j] - m.predict(Xb[te])
    return R


LITERATURE = "Boisvert et al. 0.10-0.18 (0.20-0.27 more exposed); Niagara Mohawk industrial 0.11; Patrick-Wolak 0-0.27; exposed share s 0.32-0.50"


def shape_days(df):
    cols = ["load", "p", "temp", "dem", "pc", "rad"]
    ok = df[cols].notna().all(axis=1).groupby(df.date).all()
    d = df.assign(blk=df.hour.map(BLK))
    g = d[d.blk.notna()].groupby(["date", "blk"])[cols].mean().unstack("blk")
    day = pd.DataFrame(index=g.index)
    for b in "EMV":
        for c in cols:
            day[f"{c}{b}"] = g[(c, b)]
    day["gas"] = df.groupby("date").gas.first()
    day = day[ok.reindex(day.index).fillna(False)]
    day = day.reindex(pd.date_range(df.date.min(), df.date.max()))
    day.index.name = None
    return day


def shape_frame(day, cfg):
    hes = DL.holiday_set()
    day = day.copy()
    day["date"] = day.index
    day["dow"] = day.date.dt.dayofweek
    day["y"] = np.log(day.loadE / day.loadM)
    pos = (day.pE > 0) & (day.pM > 0)
    day["x"] = np.log(day.pE / day.pM).where(pos) if cfg["form"] == "log" else day.pE - day.pM
    day["xev"] = np.log(day.pE / day.pV).where((day.pE > 0) & (day.pV > 0))
    day["w"] = day.pcE - day.pcM
    day["s"] = day.radM
    if "mask_days" in cfg:  # 2025-04-28 blackout and its restoration days: y, x and their lags are unavailable (rows 7, 14, 21, 28 and 35 days later drop out)
        bad = (day.date >= cfg["mask_days"][0]) & (day.date <= cfg["mask_days"][1])
        day.loc[bad, ["y", "x", "xev"]] = np.nan
    day = pd.concat([day, DL._lags(day, ("y", "x"), 1)], axis=1)
    m = DL._sample_flags(day.date, hes) & (day.date >= cfg["first"]) & (day.date <= cfg["last"])
    d = day[m].copy()
    for c in ("y", "x", "xev", "w", "s", "tempE", "tempM", "demE", "demM"):
        d[f"d_{c}"] = d[c] - day[c].shift(7).loc[d.index]
    for s in ("y", "x"):
        d[f"d_{s}_7"] = day[f"{s}_7"].loc[d.index] - day[f"{s}_14"].loc[d.index]
        d[f"d_{s}_14"] = day[f"{s}_14"].loc[d.index] - day[f"{s}_21"].loc[d.index]
        d[f"d_{s}_28"] = day[f"{s}_28"].loc[d.index] - day[f"{s}_35"].loc[d.index]
    need = ["d_y", "d_x", "d_xev", "d_w", "d_s", "d_tempE", "d_tempM", "d_demE", "d_demM", "d_y_7", "d_y_14", "d_y_28", "d_x_7", "d_x_14", "d_x_28", "gas"]
    d = d.dropna(subset=need).reset_index(drop=True)
    d["hour"] = 0
    if cfg["form"] == "spread":
        pbar = float(((d.pE + d.pM) / 2).mean())
        d["d_x"] = d.d_x / pbar
    for c in ("d_w", "d_s"):
        d[c] = d[c] / d[c].std()
    return d


def build(sample, method="N1"):
    cfg = SAMPLES[sample]
    df = DL.hourly_base(end=cfg["end"])
    d = shape_frame(shape_days(df), cfg)
    X = np.column_stack([d.dow, d.date.dt.month, d.date.dt.dayofyear, d.d_tempE, d.d_tempM, d.d_demE, d.d_demM, d.d_y_7, d.d_y_14, d.d_y_28, d.d_x_7, d.d_x_14, d.d_x_28, d.gas])
    bl, dates = DL.blocks_of(d), d.date.to_numpy()
    Y = np.column_stack([d.d_y, d.d_x, d.d_xev, d.d_w, d.d_s]).astype(float)
    XL = lin_matrix(d)
    R = dict(zip(["y", "x", "xev", "w", "s"], resid(Y, X, XL, bl, dates, method).T))
    keep = [i for i in range(X.shape[1]) if i != 7]  # drop d_y_7, the placebo outcome
    keepl = [i for i in range(XL.shape[1]) if i != XL.shape[1] - 7]  # d_y_7 column of lin_matrix
    R["yplac"] = resid(np.asarray(d.d_y_7, float)[:, None], X[:, keep], XL[:, keepl], bl, dates, method)[:, 0]
    R["Z"] = np.column_stack([R["w"], R["s"]])
    srcs = E.perm_sources(d, np.random.default_rng(N.SEED), E.NPERM)
    print(f"{sample}: {len(d)} days {d.date.min().date()} -> {d.date.max().date()}, form {cfg['form']}", flush=True)
    return cfg, d, X, R, srcs, XL


def fs_F(d, R, cols, endog="x"):
    sub = E.Sub(d, R["y"], R[endog], R["Z"], np.ones(len(d), bool), cols)
    return sub.first_stage_F(sub.Z0)


def sig(r):
    """Slope -> sigma = -slope (pbar = 1 in run_sub): returns sigma, lo, hi."""
    return dict(sigma=-r["elasticity"], sig_lo=-r["rand_hi"], sig_hi=-r["rand_lo"], p_t_rank=r["p_t_rank"], F=r["F"], n=r["n"])


def run(d, R, srcs, y, cols, mask=None):
    m = np.ones(len(d), bool) if mask is None else mask
    sub = E.Sub(d, y, R["x"], R["Z"], m, cols)
    sub.Zfull = R["Z"]
    r, _ = E.run_sub(sub, srcs, 1.0)
    if len(cols) > 1 and m.all():
        r["hansen_J"], r["hansen_p"] = sub.hansen(sub.Z0)
    return r


def detected(s):
    return bool(s["p_t_rank"] <= 0.05 and (s["sig_lo"] > 0 or s["sig_hi"] < 0))


def tag(sample, name, method="N1"):
    suffix = "" if method == "N1" else f"_{method}"
    return T.OUT / f"industry_iv_price_shape_{sample}{suffix}{name}.csv"


def step0(sample, method):
    cfg, d, X, R, srcs, XL = build(sample, method)
    F = {"W1": fs_F(d, R, [0]), "S1": fs_F(d, R, [1]), "W1+S1": fs_F(d, R, [0, 1])}
    Fidle = fs_F(d, R, [1], endog="xev")
    ch = [("Q0 first stage W1 (F at least 10)", bool(F["W1"] >= 10), f"F W1 {F['W1']:.1f}; S1 {F['S1']:.1f}; W1+S1 {F['W1+S1']:.1f}"),
          ("Q1 idle test for S1 (first stage on ln(pE/pV) F below 10)", bool(Fidle < 10), f"F {Fidle:.1f}")]
    s1_ok = bool(F["S1"] >= 10 and Fidle < 10)
    primary = "W1" if F["W1"] >= 10 else ("S1" if s1_ok else None)
    pd.DataFrame([dict(primary=primary or "none", s1_eligible=s1_ok)]).to_csv(tag(sample, "_step0_choice", method), index=False)
    if primary is None:
        ch.append(("Q2 planted gate", False, "not run: no eligible instrument (Q0 failed for W1 and S1); stop"))
        pd.DataFrame(ch, columns=["rule", "pass", "detail"]).to_csv(tag(sample, "_step0_checks", method), index=False)
        print(pd.DataFrame(ch, columns=["rule", "pass", "detail"]).to_string(index=False))
        return
    cols = [0] if primary == "W1" else [1]
    one = np.ones(len(d), bool)
    h1 = (d.date < cfg["regimes"][0][1]).to_numpy()
    plants = [("pooled", b, one) for b in PLANTS] + [(f"half {cfg['regimes'][0][0]}", 0.30, h1), (f"half {cfg['regimes'][1][0]}", 0.30, ~h1)]
    bl, dates = DL.blocks_of(d), d.date.to_numpy()
    rows = []
    for name, s0, m in plants:
        yp = np.asarray(d.d_y, float) - np.where(m, s0, 0.0) * np.asarray(d.d_x, float)
        yres = resid(yp[:, None], X, XL, bl, dates, method)[:, 0]
        s = sig(run(d, R, srcs, yres, cols))
        rows.append(dict(plant=name, construction="refit", sigma0=s0, expected=s0 * (m.mean() if name != "pooled" else 1.0), instrument=primary, **s))
        print(name, s0, {k: round(float(v), 4) for k, v in s.items()}, flush=True)
    for b in PLANTS:  # diagnostic only: plant on the residual scale (no refit)
        s = sig(run(d, R, srcs, R["y"] - b * R["x"], cols))
        rows.append(dict(plant="pooled", construction="residual-scale (diagnostic)", sigma0=b, expected=b, instrument=primary, **s))
        print("residual-scale", b, {k: round(float(v), 4) for k, v in s.items()}, flush=True)
    P = pd.DataFrame(rows)
    P.round(5).to_csv(tag(sample, "_step0", method), index=False)
    pooled = P[(P.plant == "pooled") & (P.construction == "refit")]
    g = pooled[np.isclose(pooled.sigma0, GATE)].iloc[0]
    rec = bool(g.sig_lo <= g.sigma0 <= g.sig_hi and abs(g.sigma - g.sigma0) <= max(0.02, 0.3 * g.sigma0))
    dets = [r.sigma0 for r in pooled.itertuples() if detected(r._asdict())]
    ch.append((f"Q2 planted gate [{method}]: sigma0 {GATE} detected and recovered (instrument {primary})", bool(detected(g.to_dict()) and rec), f"est {g.sigma:.4f} [{g.sig_lo:.4f},{g.sig_hi:.4f}], p {g.p_t_rank:.3f}"))
    ch.append(("detectable sigma (no pass/fail)", None, "smallest detected pooled plant: " + (str(min(dets)) if dets else "none")))
    hs = P[P.plant != "pooled"]
    dg = P[P.construction != "refit"]
    ch.append(("diagnostic: residual-scale plants (no pass/fail)", None, "; ".join(f"{r.sigma0}: {r.sigma:.4f} [{r.sig_lo:.4f},{r.sig_hi:.4f}]" for r in dg.itertuples())))
    ch.append(("regime weights (no pass/fail)", None, "; ".join(f"{r.plant}: {r.sigma / r.sigma0:.2f}" for r in hs.itertuples())))
    C = pd.DataFrame(ch, columns=["rule", "pass", "detail"])
    C.to_csv(tag(sample, "_step0_checks", method), index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 250)
    print(P[["plant", "sigma0", "expected", "F", "sigma", "sig_lo", "sig_hi", "p_t_rank"]].round(4).to_string(index=False))
    print(C.to_string(index=False))


def step1(sample):
    method = None
    for mth in METHODS:  # fixed order: the first learner whose step-0 gate passed (spec amendment 2)
        f0, fc = tag(sample, "_step0_checks", mth), tag(sample, "_step0_choice", mth)
        if not f0.exists() or not fc.exists():
            continue
        g, ch0 = pd.read_csv(f0), pd.read_csv(fc).iloc[0]
        if ch0.primary != "none" and bool(g[g.rule.str.startswith("Q2")]["pass"].iloc[0]):
            method = mth
            break
    if method is None:
        sys.exit("no learner passed Q0 and Q2 in step 0 (or step 0 has not been run): stop (spec rules Q0, Q2, amendment 2)")
    print(f"learner {method}", flush=True)
    cfg, d, X, R, srcs, XL = build(sample, method)
    prim, s1_ok = ch0.primary, bool(ch0.s1_eligible)
    cols = [0] if prim == "W1" else [1]
    one = np.ones(len(d), bool)
    out, rows = [], []

    def go(name, y, cs, mask=None, block="full"):
        r = run(d, R, srcs, y, cs, mask)
        s = sig(r)
        rows.append(dict(variant=name, block=block, loo_share=r["loo_share_p_lt05"], perm_share_t196=r["perm_share_t_gt196"], hansen_p=r.get("hansen_p", np.nan), **s))
        print(name, block, {k: round(float(v), 4) for k, v in s.items()}, flush=True)
        return s, r

    m, rm = go(f"primary ({prim})", R["y"], cols)
    pl, _ = go("placebo", R["yplac"], cols)
    reg = []
    for name, cut, first in cfg["regimes"]:
        mask = (d.date < cut).to_numpy() if first else (d.date >= cut).to_numpy()
        reg.append(go(f"primary ({prim})", R["y"], cols, mask, block=name)[0])
    q = [("Q3 placebo outcome", bool(pl["p_t_rank"] > 0.05 and abs(pl["sigma"]) < 0.02), f"sigma {pl['sigma']:.4f}, p_t {pl['p_t_rank']:.3f}"),
         ("Q4 sign and plausibility (0 < sigma <= 2)", bool(0 < m["sigma"] <= 2), f"sigma {m['sigma']:.4f}"),
         ("Q5 detection", bool(detected(m) and m["sigma"] > 0), f"sigma {m['sigma']:.4f} [{m['sig_lo']:.4f},{m['sig_hi']:.4f}], p_t {m['p_t_rank']:.3f}, F {m['F']:.1f}"),
         ("Q7 regimes (no pass/fail)", None, "; ".join(f"{b[0]} {s['sigma']:.4f} [{s['sig_lo']:.4f},{s['sig_hi']:.4f}]" for b, s in zip(cfg["regimes"], reg))),
         ("Q9 calibration", bool(0.02 <= rm["loo_share_p_lt05"] <= 0.10), f"leave-one-out share p<0.05 {rm['loo_share_p_lt05']:.3f}; share |t|>1.96 {rm['perm_share_t_gt196']:.3f}")]
    if s1_ok:
        w, _ = go("W1 only", R["y"], [0])
        s_, _ = go("S1 only", R["y"], [1])
        both, rb = go("W1+S1", R["y"], [0, 1])
        inside = lambda a, b: bool(b["sig_lo"] <= a["sigma"] <= b["sig_hi"])
        q.append(("Q6 overidentification", bool(rb["hansen_p"] > 0.05 and inside(w, s_) and inside(s_, w)), f"Hansen p {rb['hansen_p']:.3f}; W1 {w['sigma']:.4f}, S1 {s_['sigma']:.4f}, both {both['sigma']:.4f}"))
    else:
        q.append(("Q6 overidentification", None, "not run: S1 not eligible (Q0/Q1)"))
    lo, hi = m["sig_lo"], m["sig_hi"]
    q.append(("Q10 context and exposed-share translation (no pass/fail)", None, f"{LITERATURE}; if only the exposed share responded the exposed-customer interval is [{lo / 0.50:.3f}, {hi / 0.50:.3f}] (s 0.50) to [{lo / 0.32:.3f}, {hi / 0.32:.3f}] (s 0.32)"))
    q.insert(0, ("learner (the first of N1, N2, N3 whose planted gate passed)", None, f"{method}; N1 gate failed in the first step 0" if method != "N1" else "N1"))
    pd.DataFrame(rows).round(5).to_csv(tag(sample, "", method), index=False)
    C = pd.DataFrame(q, columns=["rule", "pass", "detail"])
    C.to_csv(tag(sample, "_checks", method), index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 300)
    print(pd.DataFrame(rows)[["variant", "block", "n", "F", "sigma", "sig_lo", "sig_hi", "p_t_rank"]].round(4).to_string(index=False))
    print(C.to_string(index=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", choices=tuple(SAMPLES), required=True)
    ap.add_argument("--step", type=int, choices=(0, 1), required=True)
    ap.add_argument("--method", choices=METHODS, default="N1", help="nuisance learner for step 0 (step 1 picks it from the step-0 files)")
    a = ap.parse_args()
    step0(a.sample, a.method) if a.step == 0 else step1(a.sample)


if __name__ == "__main__":
    main()
