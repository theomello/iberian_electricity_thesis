"""Unit-level dispatch logit and the fuel-switching elasticity it implies (docs/specs/2026-11-13-unit-dispatch-design.md).

    .venv/bin/python scripts/analysis/unit_dispatch.py [--quick]

Model 1: logit of 1[cleared > 0] on unit effects, beta_f x (x = ln p* - ln c, by fuel), delta_f y_{t-1}, a spline in ln p*, residual demand and month effects, clustered by day.
Model 2: linear probability with unit and hour effects (Frisch-Waugh: demeaned within hour). Placebo: common circular shifts of the daily cost series. The elasticity of substitution at fixed
thermal output is sigma = [A_c A_g / (A_c + A_g)] (1/Q_c + 1/Q_g), A_f = beta_f S_f, from the fitted probabilities. Writes outputs/tables/unit_dispatch_*.csv and prints U1-U7.

Reusable: the fuels, the window and the cost column are the cache's; the closed form needs only the fitted slopes and probabilities.
"""
import gc
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fuel_switching as F  # noqa: E402

warnings.filterwarnings("ignore")
OUT = F.OUT
SEED = 20261113
NSHIFT = 200
NBOOT = 200
QUICK = "--quick" in sys.argv
RESUME = "--u6" in sys.argv   # skip the U4 placebo (read its saved file) and re-run U6-U7; the rng stream is advanced as in the full run
if QUICK:
    NSHIFT, NBOOT = 6, 6


def prepare(uh):
    uh = uh.copy()
    uh["y"] = (uh.cl > 0).astype(float)
    tc = uh.groupby("hid").cap.transform("sum")
    uh["Rcap"] = (uh.F_demand - uh.F_wind - uh.F_solar) / tc
    prev = uh[["unit", "hid", "y"]].rename(columns={"y": "ylag"}).assign(hid=lambda x: x.hid + 1)
    uh = uh.merge(prev, on=["unit", "hid"], how="left")
    ok = (uh.p_star > 0) & (uh.cost > 0)
    uh["lnp"] = np.where(ok, np.log(uh.p_star.where(ok, 1.0)), np.nan)
    uh["x"] = uh.lnp - np.log(uh.cost.where(ok, 1.0))
    uh["coal"] = (uh.fuel == "coal").astype(float)
    uh["day"] = pd.factorize(uh.date)[0]
    uh["week"] = pd.factorize(uh.date.dt.to_period("W").astype(str))[0]
    uh["month"] = uh.date.dt.month
    return uh


def sample(uh, x=None):
    xx = uh.x if x is None else x
    ok = (uh.p_star > 0) & (uh.cost > 0) & (~uh.wd.astype(bool)) & (xx.abs() <= 0.75) & uh.ylag.notna() & uh.Rcap.notna()
    s = uh[ok].copy()
    if x is not None:
        s["x"] = xx[ok]
    var = s.groupby("unit").y.agg(["min", "max"])
    keep = var[(var["min"] == 0) & (var["max"] == 1)].index
    return s[s.unit.isin(keep)].reset_index(drop=True)


def spline_cols(lnp, ref=None):
    z = (lnp - lnp.mean()) / lnp.std()
    k = np.quantile(z, [1 / 3, 2 / 3])
    return np.column_stack([z, z ** 2, z ** 3, np.clip(z - k[0], 0, None) ** 3, np.clip(z - k[1], 0, None) ** 3])


def design1(s, fuels=("gas", "coal")):
    units = pd.get_dummies(s.unit, dtype=float)
    cols = [units.to_numpy()]
    names = list(units.columns)
    for f in fuels:
        m = (s.fuel == f).to_numpy().astype(float)
        cols += [(s.x.to_numpy() * m)[:, None], (s.ylag.to_numpy() * m)[:, None]]
        names += [f"beta_{f}", f"delta_{f}"]
    cols += [spline_cols(s.lnp), s.Rcap.to_numpy()[:, None], (s.Rcap.to_numpy() ** 2)[:, None], pd.get_dummies(s.month, drop_first=True, dtype=float).to_numpy()]
    X = np.column_stack(cols)
    return X, names


def fit1(s, fuels=("gas", "coal"), start=None):
    X, names = design1(s, fuels)
    m = sm.Logit(s.y.to_numpy(), X).fit(disp=0, maxiter=60, cov_type="cluster", cov_kwds={"groups": s.day.to_numpy()}, start_params=start)
    ix = {n: i for i, n in enumerate(names)}
    P = m.predict(X)
    out = dict(model=m, P=P, ix=ix)
    for f in fuels:
        b = m.params[ix[f"beta_{f}"]]
        se = np.sqrt(m.cov_params()[ix[f"beta_{f}"], ix[f"beta_{f}"]])
        out[f"beta_{f}"], out[f"se_{f}"], out[f"t_{f}"] = float(b), float(se), float(b / se)
        out[f"delta_{f}"] = float(m.params[ix[f"delta_{f}"]])
        mk = (s.fuel == f).to_numpy()
        out[f"ame_{f}"] = float(b * (P[mk] * (1 - P[mk])).mean())
    if len(fuels) == 2:
        i, j = ix["beta_gas"], ix["beta_coal"]
        V = m.cov_params()
        w = (m.params[i] - m.params[j]) ** 2 / (V[i, i] + V[j, j] - 2 * V[i, j])
        out["p_equal"] = float(1 - stats.chi2.cdf(w, 1))
    return out


def fit2(s):
    """Linear probability model with unit and hour effects: every column demeaned within hour."""
    units = pd.get_dummies(s.unit, dtype=float).iloc[:, 1:]
    df = pd.DataFrame({"y": s.y, "x_gas": s.x * (s.fuel == "gas"), "x_coal": s.x * (s.fuel == "coal"), "l_gas": s.ylag * (s.fuel == "gas"), "l_coal": s.ylag * (s.fuel == "coal")})
    df = pd.concat([df, units.reset_index(drop=True)], axis=1)
    dm = df - df.groupby(s.hid.to_numpy()).transform("mean")
    m = sm.OLS(dm.y.to_numpy(), dm.drop(columns="y").to_numpy()).fit(cov_type="cluster", cov_kwds={"groups": s.day.to_numpy()})
    names = list(dm.drop(columns="y").columns)
    r = {}
    for f in ("gas", "coal"):
        i = names.index(f"x_{f}")
        r[f"beta2_{f}"], r[f"t2_{f}"] = float(m.params[i]), float(m.params[i] / m.bse[i])
    return r


def sigma_hours(uh_all, s, res, windowD):
    """sigma_fuel(h) per hour from the fitted probabilities (sample) and observed states (outside the sample)."""
    ins = uh_all.merge(s[["unit", "hid"]].assign(ins=True), on=["unit", "hid"], how="left")
    ins["ins"] = ins.ins.fillna(False).astype(bool)
    P = pd.Series(res["P"], index=pd.MultiIndex.from_frame(s[["unit", "hid"]]))
    ins["P"] = np.where(ins.ins, P.reindex(pd.MultiIndex.from_frame(ins[["unit", "hid"]])).to_numpy(), ins.y)
    ins["Q"] = ins.cap * ins.P
    ins["S"] = np.where(ins.ins, ins.cap * ins.P * (1 - ins.P), 0.0)
    g = ins.groupby(["hid", "fuel"]).agg(Q=("Q", "sum"), S=("S", "sum")).unstack("fuel")
    Qc, Qg, Sc, Sg = g[("Q", "coal")], g[("Q", "gas")], g[("S", "coal")], g[("S", "gas")]
    Ac, Ag = res["beta_coal"] * Sc, res["beta_gas"] * Sg
    sig = (Ac * Ag / (Ac + Ag)) * (1 / Qc + 1 / Qg)
    out = pd.DataFrame({"sigma": sig, "w": Qc + Qg}).replace([np.inf, -np.inf], np.nan).dropna()
    out = out[(Sc.reindex(out.index) > 0) & (Qc.reindex(out.index) > 0)]
    date = uh_all.drop_duplicates("hid").set_index("hid").date
    out["date"] = date.reindex(out.index).to_numpy()
    out["r"] = windowD.r.reindex(out.date).to_numpy()
    return out.dropna()


def sigma_cache(uh_all, s, windowD):
    """Everything in sigma_hours that does not depend on the fitted slopes, computed once (the bootstrap calls the rest 200 times)."""
    key = pd.MultiIndex.from_frame(s[["unit", "hid"]])
    pos = pd.Series(np.arange(len(s)), index=key).reindex(pd.MultiIndex.from_frame(uh_all[["unit", "hid"]])).to_numpy()
    hid = uh_all.hid.to_numpy()
    uh_h, hcode = np.unique(hid, return_inverse=True)
    date = uh_all.drop_duplicates("hid").set_index("hid").date
    return dict(ins=np.isfinite(pos), pos=np.nan_to_num(pos).astype(int), y=uh_all.y.to_numpy(), cap=uh_all.cap.to_numpy(), coal=(uh_all.fuel == "coal").to_numpy(),
                code=hcode, nh=len(uh_h), hids=uh_h, r=windowD.r.reindex(date.reindex(uh_h).to_numpy()).to_numpy())


def sigma_hours_fast(c, P, b_gas, b_coal):
    Pf = np.where(c["ins"], P[c["pos"]], c["y"])
    Q = c["cap"] * Pf
    S_ = np.where(c["ins"], c["cap"] * Pf * (1 - Pf), 0.0)
    g = lambda v, m: np.bincount(c["code"][m], weights=v[m], minlength=c["nh"])
    co, ga = c["coal"], ~c["coal"]
    Qc, Qg, Sc, Sg = g(Q, co), g(Q, ga), g(S_, co), g(S_, ga)
    Ac, Ag = b_coal * Sc, b_gas * Sg
    with np.errstate(all="ignore"):
        sig = (Ac * Ag / (Ac + Ag)) * (1 / Qc + 1 / Qg)
    ok = np.isfinite(sig) & (Sc > 0) & (Qc > 0) & np.isfinite(c["r"])
    return pd.DataFrame({"sigma": sig[ok], "w": (Qc + Qg)[ok], "r": c["r"][ok]})


def band(out, lo, hi):
    q = out.r.quantile([lo, hi]).to_numpy()
    m = out[(out.r >= q[0]) & (out.r <= q[1])]
    return float(np.average(m.sigma, weights=m.w)) if len(m) else np.nan


def main():
    t0 = time.time()
    A0, A1 = "2019-01-01", "2020-02-29"
    uhA = F.load_unit_hours(F.months(A0, A1))
    uhA = uhA[(uhA.date >= A0) & (uhA.date <= A1)]
    DA = F.daily(uhA)
    P = prepare(uhA)
    S = sample(P)
    ncoal = S[S.fuel == "coal"].unit.nunique()
    print(f"U1 window A: {len(S)} unit-hours (gas {int((S.fuel == 'gas').sum())}, coal {int((S.fuel == 'coal').sum())}), units {S[S.fuel == 'gas'].unit.nunique()} gas / {ncoal} coal [after dropping units without variation]", flush=True)
    r1 = fit1(S)
    print(f"U2 Model 1: beta_gas {r1['beta_gas']:.3f} (se {r1['se_gas']:.3f}, t {r1['t_gas']:.1f}), beta_coal {r1['beta_coal']:.3f} (se {r1['se_coal']:.3f}, t {r1['t_coal']:.1f}); lag gas {r1['delta_gas']:.2f}, coal {r1['delta_coal']:.2f}; fit {time.time() - t0:.0f}s", flush=True)
    r2 = fit2(S)
    print(f"U3 Model 2 (hour and unit effects): beta_gas {r2['beta2_gas']:.3f} (t {r2['t2_gas']:.1f}), beta_coal {r2['beta2_coal']:.3f} (t {r2['t2_coal']:.1f}); Model 1 average marginal effects gas {r1['ame_gas']:.3f}, coal {r1['ame_coal']:.3f}; ratios {r1['ame_gas'] / r2['beta2_gas']:.2f}, {r1['ame_coal'] / r2['beta2_coal']:.2f}", flush=True)
    print(f"U5 beta_gas = beta_coal: p {r1['p_equal']:.4f}", flush=True)

    # U4 placebo: common circular shifts of the daily cost series
    rng = np.random.default_rng(SEED)
    dates = np.sort(P.date.unique())
    cost_ud = P.groupby(["unit", "date"]).cost.first()
    tg, tc = [], []
    for _ in range(NSHIFT):
        k = int(rng.integers(30, len(dates) - 29))
        if RESUME:
            continue
        mp = pd.Series(np.roll(dates, -k), index=dates)
        key = pd.MultiIndex.from_arrays([P.unit, P.date.map(mp)])
        cs = cost_ud.reindex(key).to_numpy()
        Pc = P.copy()
        Pc["cost_s"] = cs
        okc = Pc.cost_s > 0
        xs = pd.Series(np.where(okc, Pc.lnp - np.log(Pc.cost_s.where(okc, 1.0)), np.nan), index=Pc.index)
        Ss = sample(Pc.assign(cost=Pc.cost_s), x=xs)
        try:
            o = fit1(Ss)
            tg.append(abs(o["t_gas"]))
            tc.append(abs(o["t_coal"]))
        except Exception as e:  # a draw that fails to converge is skipped, and counted
            tg.append(np.nan)
            tc.append(np.nan)
    if RESUME:
        old = pd.read_csv(OUT / "unit_dispatch_placebo.csv")
        tg, tc = old.abs_t_gas.to_numpy(), old.abs_t_coal.to_numpy()
    tg, tc = np.array(tg), np.array(tc)
    rg = int(1 + np.nansum(tg >= abs(r1["t_gas"])))
    rc = int(1 + np.nansum(tc >= abs(r1["t_coal"])))
    print(f"U4 circular shifts ({int(np.isfinite(tg).sum())} converged of {NSHIFT}): real |t| gas {abs(r1['t_gas']):.1f} ranks {rg}, coal {abs(r1['t_coal']):.1f} ranks {rc}; shifted |t| 95th pct gas {np.nanpercentile(tg, 95):.1f}, coal {np.nanpercentile(tc, 95):.1f}", flush=True)
    if not RESUME:
        pd.DataFrame({"abs_t_gas": tg, "abs_t_coal": tc}).to_csv(OUT / "unit_dispatch_placebo.csv", index=False)

    # U6 implied elasticity
    sh = sigma_hours(P, S, r1, DA)
    med = band(sh, 0.4, 0.6)
    lowest = band(sh, 0.0, 1 / 3)
    highest = band(sh, 2 / 3, 1.0)
    # bootstrap over weeks: Model 1 refitted with week multiplicities as frequency weights on the same design (parameters stay aligned)
    Xs, nms = design1(S)
    ix = {n: i for i, n in enumerate(nms)}
    wk = pd.factorize(S.week)[0]
    nw = wk.max() + 1
    cache = sigma_cache(P, S, DA)
    chk = band(sigma_hours_fast(cache, r1["P"], r1["beta_gas"], r1["beta_coal"]), 0.4, 0.6)
    assert abs(chk - med) < 1e-9, (chk, med)
    ybt = S.y.to_numpy()
    boots = []
    for b in range(NBOOT):
        cnt = np.bincount(rng.integers(0, nw, size=nw), minlength=nw)
        try:
            mb = sm.GLM(ybt, Xs, family=sm.families.Binomial(), freq_weights=cnt[wk].astype(float)).fit(start_params=r1["model"].params, maxiter=40)
            shb = sigma_hours_fast(cache, np.asarray(mb.predict(Xs)), float(mb.params[ix["beta_gas"]]), float(mb.params[ix["beta_coal"]]))
            boots.append(band(shb, 0.4, 0.6))
            del mb, shb
        except Exception:
            boots.append(np.nan)
        if (b + 1) % 10 == 0:
            print(f"   bootstrap {b + 1}/{NBOOT}, {time.time() - t0:.0f}s, last {boots[-1]:.3f}", flush=True)
        gc.collect()
    boots = np.array(boots)
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    print(f"U6 sigma_fuel at the median cost ratio {med:.2f} (95% [{lo:.2f}, {hi:.2f}], {int(np.isfinite(boots).sum())} draws); lowest third {lowest:.2f}, highest third {highest:.2f}", flush=True)

    # U7 window B, gas
    B0, B1 = "2021-06-01", "2022-12-31"
    uhB = F.load_unit_hours(F.months(B0, B1))
    uhB = uhB[(uhB.date >= B0) & (uhB.date <= B1) & (uhB.fuel == "gas")]
    SB = sample(prepare(uhB))
    rB = fit1(SB, fuels=("gas",))
    print(f"U7 window B gas: {len(SB)} unit-hours, beta_gas {rB['beta_gas']:.3f} (se {rB['se_gas']:.3f}, t {rB['t_gas']:.1f}); ratio to window A {rB['beta_gas'] / r1['beta_gas']:.2f}", flush=True)

    pd.DataFrame([dict(window="A", **{k: v for k, v in r1.items() if k not in ("model", "P", "ix")}, **r2, sigma_median=med, sigma_lo=lo, sigma_hi=hi, sigma_lowest=lowest, sigma_highest=highest, unit_hours=len(S)),
                  dict(window="B gas", **{k: v for k, v in rB.items() if k not in ("model", "P", "ix")}, unit_hours=len(SB))]).round(5).to_csv(OUT / "unit_dispatch_summary.csv", index=False)
    sh.groupby(pd.qcut(sh.r, 10, duplicates="drop")).apply(lambda m: pd.Series(dict(r_mid=m.r.mean(), sigma=np.average(m.sigma, weights=m.w), hours=len(m)))).round(4).to_csv(OUT / "unit_dispatch_curve.csv")

    nB = len(SB)
    u1 = bool(len(S) >= 100000 and ncoal >= 15 and nB >= 50000)
    u2 = bool(r1["beta_gas"] > 0 and r1["beta_coal"] > 0 and r1["t_gas"] >= 3 and r1["t_coal"] >= 3)
    u3 = bool(r2["beta2_gas"] > 0 and r2["beta2_coal"] > 0 and r2["t2_gas"] >= 3 and r2["t2_coal"] >= 3 and 0.5 <= r1["ame_gas"] / r2["beta2_gas"] <= 2 and 0.5 <= r1["ame_coal"] / r2["beta2_coal"] <= 2)
    u4 = bool(rg <= 10 and rc <= 10)
    u5 = bool(r1["p_equal"] > 0.05)
    u6 = bool(lo > 0 and 2 <= med <= 20 and lowest > highest)
    u7 = bool(rB["beta_gas"] > 0 and rB["t_gas"] >= 3)
    print(f"\nU1 feasibility: {u1}\nU2 cost matters (Model 1, both slopes positive, |t| >= 3): {u2}\nU3 within-hour check (Model 2 positive, |t| >= 3, marginal effects within a factor of 2): {u3}")
    print(f"U4 placebo (both rank <= 10 of {NSHIFT + 1}): {u4}\nU5 one ranking logic (equality not rejected at 5%): {u5}\nU6 implied elasticity (interval excludes 0, median in [2, 20], hump): {u6}\nU7 crisis stability (window B gas slope positive, t >= 3): {u7}")
    print(f"total time {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
