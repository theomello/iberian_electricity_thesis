"""Part A of docs/specs/2026-11-17-industry-iv-day-level-and-metered-design.md (rules A0-A6), plus the frame builders Part B reuses.

    .venv/bin/python scripts/analysis/industry_iv_day_level.py --step 0     # power gate: planted effects only
    .venv/bin/python scripts/analysis/industry_iv_day_level.py --step 1     # real outcome; refuses to run unless step 0 passed A0

Day level: outcome d ln L_day (week-on-week, same weekday, ESIOS 1204-1207 daily mean), price d P_day (daily mean day-ahead price), instruments the daily mean of d_pc and its square
(C1, realised national mean 100 m wind speed through min(ws/12, 1)^3). Double ML (time-blocked cross-fitting, 10 blocks, 14 days purged) on calendar terms, daily mean temperature, demand forecast,
own lags 7/14/28 days and gas, without realised wind. Elasticity = slope x mean daily price of the sample. Inference: 1,000 permutations of the residualised instruments across days within
year-month, seed 20261117 (`industry_iv_estimation.run_sub`). A5 (three prices, just identified) uses the same permutations for the t-rank p and robust normal intervals (a deviation from the
registered "randomization interval", recorded in the spec before the run). Step 0 plants beta in the outcome (as industry_iv_planted_effect.py); the planted estimates contain the real component, as
in that test. Writes outputs/tables/industry_iv_day_level_step0{,_checks}.csv and industry_iv_day_level{,_checks,_crossday}.csv.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_iv_estimation as E  # noqa: E402
import industry_iv_noise_reducers as N  # noqa: E402
import tou_did as T  # noqa: E402

ROOT = T.ROOT
H = 168
HOURLY_INTERVAL = (-0.021, 0.028)  # wind-speed estimation, primary, committed 2026-11-17
COVID = ("2020-03-01", "2020-06-30")


def local(ts):
    loc = ts.dt.tz_convert("Europe/Madrid")
    return pd.to_datetime(loc.dt.date), loc.dt.hour


def holiday_set():
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    return set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))


def hourly_base(load=None, end="2023-12-31"):
    """Hourly grid 2018-10-01 -> 2023-12-31 with load (default ESIOS 1204-1207; `load` = Series indexed by (date, hour) overrides it), price, temperature, forecasts, gas, wind speed and pc."""
    df = N.build(end=end)
    if load is not None:
        df["load"] = load.reindex(pd.MultiIndex.from_arrays([df.date, df.hour])).to_numpy()
        df["lnL"] = np.log(df.load.where(df.load > 0))
    a = pd.read_parquet(ROOT / "data/weather/weather_spain_aggregate.parquet")
    dt_, hr_ = local(a.utc_timestamp)
    w = pd.DataFrame({"date": dt_, "hour": hr_, "ws": a.wind_speed_100m_wind_sites}).drop_duplicates(["date", "hour"]).set_index(["date", "hour"]).ws
    df["ws"] = w.reindex(pd.MultiIndex.from_arrays([df.date, df.hour])).to_numpy()
    df["pc"] = np.minimum(df.ws / 12.0, 1.0) ** 3
    r = pd.DataFrame({"date": dt_, "hour": hr_, "rad": a.radiation_solar_sites}).drop_duplicates(["date", "hour"]).set_index(["date", "hour"]).rad
    df["rad"] = r.reindex(pd.MultiIndex.from_arrays([df.date, df.hour])).to_numpy()
    return df


def _lags(df, cols_lag, step):
    out = {}
    for s in cols_lag:
        for k in (7, 14, 21, 28):
            out[f"{s}_{k}"] = df[s].shift(k * step)
        out[f"{s}_35"] = df[s].shift(35 * step)
    return pd.DataFrame(out, index=df.index)


def _sample_flags(date, hes):
    covid = date.between(*COVID)
    partner = date - pd.Timedelta(days=7)
    partner_ok = ~partner.isin(hes) & ~partner.between(*COVID)
    base = (date.dt.dayofweek < 5) & ~date.isin(hes) & ~covid
    return base & partner_ok


def hourly_frame(df, first="2019-01-01", last="2023-12-31"):
    """Week-on-week hourly frame as industry_iv_noise_reducers V3 (hour kept; non-holiday weekdays; no COVID months)."""
    hes = holiday_set()
    df = pd.concat([df, _lags(df, ("lnL", "p"), 24)], axis=1)
    df["dow"] = df.date.dt.dayofweek
    m = _sample_flags(df.date, hes) & (df.date >= first) & (df.date <= last)
    d = df[m].copy()
    for c in ("lnL", "p", "temp", "dem", "pc", "ws"):
        d[f"d_{c}"] = d[c] - df[c].shift(H).loc[d.index]
    for s in ("lnL", "p"):
        d[f"d_{s}_7"] = df[f"{s}_7"].loc[d.index] - df[f"{s}_14"].loc[d.index]
        d[f"d_{s}_14"] = df[f"{s}_14"].loc[d.index] - df[f"{s}_21"].loc[d.index]
        d[f"d_{s}_28"] = df[f"{s}_28"].loc[d.index] - df[f"{s}_35"].loc[d.index]
    need = ["d_lnL", "d_p", "d_pc", "d_temp", "d_dem", "d_lnL_7", "d_lnL_14", "d_lnL_28", "d_p_7", "d_p_14", "d_p_28", "gas", "ws"]
    return d.dropna(subset=need).reset_index(drop=True)


def day_series(df):
    """Daily means over days with all 24 hours present; full calendar index (NaN for missing days)."""
    cols = ["load", "p", "temp", "dem", "pc"]
    ok = df.assign(_ok=df[cols].notna().all(axis=1)).groupby("date")._ok.all()
    g = df.groupby("date")
    day = g[cols].mean()
    day["gas"] = g.gas.first()
    day = day[ok.reindex(day.index).fillna(False)]
    day = day.reindex(pd.date_range(df.date.min(), df.date.max()))
    day.index.name = None
    day["lnL"] = np.log(day.load.where(day.load > 0))
    return day


def day_frame(df, first="2019-01-01", last="2023-12-31"):
    """Week-on-week daily frame (one row per date, hour set to 0) with neighbour-day differences for A5."""
    hes = holiday_set()
    day = day_series(df)
    day = pd.concat([day, _lags(day, ("lnL", "p"), 1)], axis=1)
    day["date"] = day.index
    day["dow"] = day.date.dt.dayofweek
    m = _sample_flags(day.date, hes) & (day.date >= first) & (day.date <= last)
    d = day[m].copy()
    for c in ("lnL", "p", "temp", "dem", "pc"):
        d[f"d_{c}"] = d[c] - day[c].shift(7).loc[d.index]
    for s in ("lnL", "p"):
        d[f"d_{s}_7"] = day[f"{s}_7"].loc[d.index] - day[f"{s}_14"].loc[d.index]
        d[f"d_{s}_14"] = day[f"{s}_14"].loc[d.index] - day[f"{s}_21"].loc[d.index]
        d[f"d_{s}_28"] = day[f"{s}_28"].loc[d.index] - day[f"{s}_35"].loc[d.index]
    for c in ("p", "pc"):  # x_k(d) = x(d+k) - x(d+k-7)
        d[f"d_{c}_m1"] = (day[c].shift(1) - day[c].shift(8)).loc[d.index]
        d[f"d_{c}_p1"] = (day[c].shift(-1) - day[c].shift(6)).loc[d.index]
    need = ["d_lnL", "d_p", "d_pc", "d_temp", "d_dem", "d_lnL_7", "d_lnL_14", "d_lnL_28", "d_p_7", "d_p_14", "d_p_28", "gas"]
    d = d.dropna(subset=need).reset_index(drop=True)
    d["hour"] = 0
    return d


def day_X(d):
    return np.column_stack([d.dow, d.date.dt.month, d.date.dt.dayofyear, d.d_temp, d.d_dem, d.d_lnL_7, d.d_lnL_14, d.d_lnL_28, d.d_p_7, d.d_p_14, d.d_p_28, d.gas])


def hour_X(d):
    return np.column_stack([d.hour, d.dow, d.date.dt.month, d.date.dt.dayofyear, d.d_temp, d.d_dem, d.d_lnL_7, d.d_lnL_14, d.d_lnL_28, d.d_p_7, d.d_p_14, d.d_p_28, d.gas])


def blocks_of(d):
    order = d.date.rank(method="dense").to_numpy()
    return np.minimum((order / order.max() * 10).astype(int), 9)


def residualise(d, X, own_lag_col):
    """Cross-fitted residuals of y, p, d_pc, d_pc^2 on X; placebo outcome (d_lnL_7) residualised without its own lag (column `own_lag_col` of X)."""
    bl, dates = blocks_of(d), d.date.to_numpy()
    Y = np.column_stack([d.d_lnL, d.d_p, d.d_pc, d.d_pc ** 2]).astype(float)
    R = dict(zip(["y", "p", "z1", "z2"], N.gb_resid(Y, X, bl, dates).T))
    keep = [i for i in range(X.shape[1]) if i != own_lag_col]
    R["yplac"] = N.gb_resid(np.asarray(d.d_lnL_7, float)[:, None], X[:, keep], bl, dates)[:, 0]
    R["Z"] = np.column_stack([R["z1"], R["z2"]])
    return R


def plants_list(d, betas=(-0.02, -0.03, -0.05, -0.10), halves=True):
    one = np.ones(len(d), bool)
    out = [("pooled", b, one) for b in betas]
    if halves:
        h1 = (d.date < "2021-07-01").to_numpy()
        out += [("half 2019-21H1", -0.10, h1), ("half 2021H2-23", -0.10, ~h1)]
    return out


def run_plants(d, X, R, srcs, pbar, plants, mask=None):
    rows = []
    bl, dates = blocks_of(d), d.date.to_numpy()
    allm = np.ones(len(d), bool) if mask is None else mask
    for name, beta, m in plants:
        yp = np.asarray(d.d_lnL, float) + np.where(m, beta / pbar * np.asarray(d.d_p, float), 0.0)
        yres = N.gb_resid(yp[:, None], X, bl, dates)[:, 0]
        sub = E.Sub(d, yres, R["p"], R["Z"], allm, [0, 1])
        sub.Zfull = R["Z"]
        r, _ = E.run_sub(sub, srcs, pbar)
        rows.append(dict(plant=name, beta=beta, expected=beta * (m.mean() if name != "pooled" else 1.0), **r))
        print(name, beta, {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in r.items() if k in ("n", "F", "elasticity", "rand_lo", "rand_hi", "p_t_rank")}, flush=True)
    return pd.DataFrame(rows)


def detected(r):
    return bool(r.p_t_rank <= 0.05 and (r.rand_hi < 0 or r.rand_lo > 0))


def power_checks(P, gate_beta, tag, hourly_detectable=-0.03):
    """A0 (planted gate_beta detected and recovered), A0b (smallest detected pooled plant smaller in size than hourly), regime weights."""
    pooled = P[P.plant == "pooled"]
    g = pooled[np.isclose(pooled.beta, gate_beta)].iloc[0]
    rec = bool(g.rand_lo <= g.beta <= g.rand_hi and abs(g.elasticity - g.beta) <= max(0.01, 0.3 * abs(g.beta)))
    ch = [(f"{tag}0 power: planted {gate_beta} detected and recovered", bool(detected(g) and rec), f"est {g.elasticity:.4f} [{g.rand_lo:.4f},{g.rand_hi:.4f}], p {g.p_t_rank:.3f}")]
    dets = [r.beta for r in pooled.itertuples() if detected(r)]
    small = max(dets) if dets else None
    ch.append((f"{tag}0b sharper than hourly (smallest detected pooled plant smaller than {hourly_detectable})", bool(small is not None and abs(small) < abs(hourly_detectable)), "detected pooled plants: " + (", ".join(str(b) for b in dets) if dets else "none")))
    hs = P[P.plant != "pooled"]
    if len(hs):
        w = {r.plant: r.elasticity / r.beta for r in hs.itertuples()}
        ch.append(("regime weights (no pass/fail)", None, "; ".join(f"{k}: {v:.2f}" for k, v in w.items())))
    return ch


def real_run(d, R, srcs, pbar, with_regimes=True):
    """Primary, d_pc only, placebo (and sub-periods) on the real outcome."""
    Z = R["Z"]
    allm = np.ones(len(d), bool)
    h1 = (d.date < "2021-07-01").to_numpy()
    jobs = [("primary", "full", R["y"], allm, [0, 1]), ("primary", "d_pc only", R["y"], allm, [0]), ("placebo", "full", R["yplac"], allm, [0, 1])]
    if with_regimes:
        jobs += [("primary", "2019-21H1", R["y"], h1, [0, 1]), ("primary", "2021H2-23", R["y"], ~h1, [0, 1])]
    rows = []
    for name, block, y, mask, cols in jobs:
        sub = E.Sub(d, y, R["p"], Z, mask, cols)
        sub.Zfull = Z
        r, _ = E.run_sub(sub, srcs, pbar)
        if name == "primary" and block == "full":
            r["hansen_J"], r["hansen_p"] = sub.hansen(sub.Z0)
        rows.append(dict(variant=name, block=block, **r))
        print(name, block, {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in r.items() if k in ("n", "F", "elasticity", "rand_lo", "rand_hi", "p_t_rank", "p_ar0_rank")}, flush=True)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- A5: three prices, just identified
def iv_multi(y, P, Z):
    """Just-identified 2SLS, robust (one row per date). Returns beta, covariance."""
    A = Z.T @ P
    beta = np.linalg.solve(A, Z.T @ y)
    u = y - P @ beta
    S = (Z * u[:, None]).T @ (Z * u[:, None])
    Ai = np.linalg.inv(A)
    return beta, Ai @ S @ Ai.T


def ap_conditional_F(P, Z):
    """Angrist-Pischke conditional first-stage F of each endogenous column (others partialled out of it and of Z), robust Wald."""
    out = []
    for j in range(P.shape[1]):
        oth = np.delete(P, j, axis=1)
        pj = P[:, j] - oth @ np.linalg.lstsq(oth, P[:, j], rcond=None)[0]
        Zt = Z - oth @ np.linalg.lstsq(oth, Z, rcond=None)[0]
        b = np.linalg.lstsq(Zt, pj, rcond=None)[0]
        e = pj - Zt @ b
        A = np.linalg.inv(Zt.T @ Zt)
        V = A @ ((Zt * e[:, None]).T @ (Zt * e[:, None])) @ A
        out.append(float(b @ np.linalg.inv(V) @ b / Z.shape[1]))
    return out


def cross_day(d, srcs_fn, pbar):
    """A5: ln L_d on week-on-week P_{d-1}, P_d, P_{d+1}; instruments the matching d_pc. Elasticity = coefficient x pbar."""
    s = d.dropna(subset=["d_p_m1", "d_p_p1", "d_pc_m1", "d_pc_p1"]).reset_index(drop=True)
    X = day_X(s)
    bl, dates = blocks_of(s), s.date.to_numpy()
    Y = np.column_stack([s.d_lnL, s.d_p_m1, s.d_p, s.d_p_p1, s.d_pc_m1, s.d_pc, s.d_pc_p1]).astype(float)
    R = N.gb_resid(Y, X, bl, dates)
    y, P, Z = R[:, 0], R[:, 1:4], R[:, 4:7]
    Fc = ap_conditional_F(P, Z)
    res = dict(n=len(s), F_prev=Fc[0], F_own=Fc[1], F_next=Fc[2])
    if min(Fc) < 10:
        res["stopped"] = True
        return res, None
    beta, V = iv_multi(y, P, Z)
    srcs = srcs_fn(s)
    c = np.eye(3)
    c = np.vstack([c, np.ones(3)])
    se = np.sqrt(np.einsum("ij,jk,ik->i", c, V, c))
    est = c @ beta
    tperm = np.empty((len(srcs), 4))
    for r_, src in enumerate(srcs):
        bp, Vp = iv_multi(y, P, Z[src])
        tperm[r_] = (c @ bp) / np.sqrt(np.einsum("ij,jk,ik->i", c, Vp, c))
    ptr = [(1 + np.sum(np.abs(tperm[:, i]) >= abs(est[i] / se[i]))) / (len(srcs) + 1) for i in range(4)]
    rows = [dict(term=t, elasticity=est[i] * pbar, se=se[i] * pbar, lo=(est[i] - 1.96 * se[i]) * pbar, hi=(est[i] + 1.96 * se[i]) * pbar, p_t_rank=ptr[i])
            for i, t in enumerate(["price d-1", "price d (own day)", "price d+1 (next day, public ~13:00 on d)", "sum of three"])]
    res["stopped"] = False
    return res, pd.DataFrame(rows)


def build_day_pipeline():
    df = hourly_base()
    d = day_frame(df)
    X = day_X(d)
    R = residualise(d, X, own_lag_col=5)
    pbar = float(d.p.mean())
    srcs = E.perm_sources(d, np.random.default_rng(N.SEED), E.NPERM)
    print(f"day sample {len(d)} days, mean daily price {pbar:.2f}", flush=True)
    return d, X, R, pbar, srcs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, choices=(0, 1), required=True)
    step = ap.parse_args().step
    f0 = T.OUT / "industry_iv_day_level_step0_checks.csv"
    d, X, R, pbar, srcs = build_day_pipeline()
    if step == 0:
        P = run_plants(d, X, R, srcs, pbar, plants_list(d))
        P.round(5).to_csv(T.OUT / "industry_iv_day_level_step0.csv", index=False)
        C = pd.DataFrame(power_checks(P, -0.05, "A"), columns=["rule", "pass", "detail"])
        C.to_csv(f0, index=False)
        pd.set_option("display.width", 250, "display.max_colwidth", 250)
        print(P[["plant", "beta", "expected", "F", "elasticity", "rand_lo", "rand_hi", "p_t_rank"]].round(4).to_string(index=False))
        print(C.to_string(index=False))
        return
    # ---- step 1: stop rule A0
    if not f0.exists():
        sys.exit("step 0 has not been run: no real-outcome result is produced")
    g = pd.read_csv(f0)
    if not bool(g[g.rule.str.startswith("A0 power")]["pass"].iloc[0]):
        sys.exit("A0 failed in step 0: day-level aggregation is not informative; stop (spec rule A0)")
    sharper = bool(g[g.rule.str.startswith("A0b")]["pass"].iloc[0])
    Rr = real_run(d, R, srcs, pbar)
    Rr.round(5).to_csv(T.OUT / "industry_iv_day_level.csv", index=False)
    q = lambda v, b: Rr[(Rr.variant == v) & (Rr.block == b)].iloc[0]
    m, pl, s1 = q("primary", "full"), q("placebo", "full"), q("primary", "d_pc only")
    ch = [("A0b sharper than hourly (from step 0)", sharper, "if False the result is a margin check, not a new bound"),
          ("A1 placebo outcome", bool(pl.p_t_rank > 0.05 and abs(pl.elasticity) < 0.01), f"elasticity {pl.elasticity:.4f}, p_t {pl.p_t_rank:.3f}"),
          ("A2 detection (negative, p<=0.05, interval excludes zero)", bool(m.elasticity < 0 and detected(m)), f"{m.elasticity:.4f} [{m.rand_lo:.4f},{m.rand_hi:.4f}], p_t {m.p_t_rank:.3f}, F {m.F:.1f}"),
          ("A3 agreement with hourly interval", bool(HOURLY_INTERVAL[0] <= m.elasticity <= HOURLY_INTERVAL[1]), f"day-level {m.elasticity:.4f}, hourly interval {HOURLY_INTERVAL}"),
          ("A4 regimes (no pass/fail)", None, "; ".join(f"{b} {q('primary', b).elasticity:.4f} [{q('primary', b).rand_lo:.4f},{q('primary', b).rand_hi:.4f}]" for b in ("2019-21H1", "2021H2-23"))),
          ("A6 calibration", bool(0.02 <= m.loo_share_p_lt05 <= 0.10), f"leave-one-out share p<0.05 {m.loo_share_p_lt05:.3f}; share |t|>1.96 {m.perm_share_t_gt196:.3f}"),
          ("Hansen J (no pass/fail)", None, f"J {m.hansen_J:.2f} p {m.hansen_p:.3f}; d_pc only {s1.elasticity:.4f} [{s1.rand_lo:.4f},{s1.rand_hi:.4f}]")]
    res, X5 = cross_day(d, lambda s: E.perm_sources(s, np.random.default_rng(N.SEED), E.NPERM), pbar)
    if res["stopped"]:
        ch.append(("A5 cross-day", None, f"STOPPED: conditional F prev {res['F_prev']:.1f}, own {res['F_own']:.1f}, next {res['F_next']:.1f} (n {res['n']}); the three prices cannot be separated"))
    else:
        X5.round(5).to_csv(T.OUT / "industry_iv_day_level_crossday.csv", index=False)
        nx = X5.iloc[2]
        ch.append(("A5 cross-day: intertemporal substitution (next-day price coefficient positive, p<=0.05, interval excludes zero)", bool(nx.elasticity > 0 and nx.p_t_rank <= 0.05 and nx.lo > 0),
                   f"conditional F {res['F_prev']:.1f}/{res['F_own']:.1f}/{res['F_next']:.1f}; " + "; ".join(f"{r.term} {r.elasticity:.4f} [{r.lo:.4f},{r.hi:.4f}] p {r.p_t_rank:.3f}" for r in X5.itertuples())))
    C = pd.DataFrame(ch, columns=["rule", "pass", "detail"])
    C.to_csv(T.OUT / "industry_iv_day_level_checks.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 250)
    print(Rr[["variant", "block", "n", "F", "elasticity", "rand_lo", "rand_hi", "p_t_rank"]].round(4).to_string(index=False))
    print(C.to_string(index=False))


if __name__ == "__main__":
    main()
