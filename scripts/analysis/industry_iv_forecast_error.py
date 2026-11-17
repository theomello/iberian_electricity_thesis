"""Run of docs/specs/2026-11-17-industry-iv-forecast-error-design.md (rules Q1-Q8).

    .venv/bin/python scripts/analysis/industry_iv_forecast_error.py

Instruments: D-1 forecast error of wind and PV (forecast - realised, GW) and squares; controls include realised wind and PV (levels, day means) in the boosted learner (V3, differenced week-on-week) and as OLS
terms in V1. Q1 is a stop rule: if first-stage F < 10 or detectable elasticity > 0.25, no slope is computed or stored. Inference as in industry_iv_estimation.py (1,000 permutations, rank of |t|, permutation
Anderson-Rubin interval, grid +-40 SE). Writes outputs/tables/industry_iv_forecast_error.csv and industry_iv_forecast_error_checks.csv. Seed 20261117.
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_iv_estimation as E  # noqa: E402
import industry_iv_noise_reducers as N  # noqa: E402
import tou_did as T  # noqa: E402

ROOT, H, SEED = T.ROOT, N.H, N.SEED
CACHE = ROOT / "data/cache_tou/industry_iv_error_sets.pkl"


def realised():
    r = pd.read_parquet(ROOT / "data/ree/ree_realtime_5min.parquet", columns=["utc_timestamp", "wind", "solar_pv"])
    loc = pd.DatetimeIndex(r.utc_timestamp).tz_convert("Europe/Madrid")
    r["date"], r["hour"] = pd.to_datetime(loc.date), loc.hour
    h = r.groupby(["date", "hour"])[["wind", "solar_pv"]].mean() / 1000
    return h.rename(columns={"wind": "wr", "solar_pv": "sr"})


def build_sets():
    df = N.build()
    rl = realised()
    grid = df.set_index(["date", "hour"]).index
    df["wr"], df["sr"] = rl.wr.reindex(grid).to_numpy(), rl.sr.reindex(grid).to_numpy()
    df["ew"], df["es"] = df.wind - df.wr, df.solar - df.sr
    for s in ("lnL", "p"):
        for k in (7, 14, 21, 28):
            df[f"{s}_{k}"] = df[s].shift(k * 24)
    df["dow"] = df.date.dt.dayofweek
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    covid = df.date.between("2020-03-01", "2020-06-30")
    base = (df.date >= "2019-01-01") & (df.dow < 5) & ~df.date.isin(hes) & ~covid
    partner_ok = ~(df.date - pd.Timedelta(days=7)).isin(hes) & ~(df.date - pd.Timedelta(days=7)).between("2020-03-01", "2020-06-30")
    pbar = float(df.loc[base, "p"].mean())
    Zm = lambda e, s: np.column_stack([e, s, e ** 2, s ** 2])
    sets = {}

    # V1: week-on-week difference, OLS controls incl. realised wind and PV
    cols = ["lnL", "p", "temp", "ew", "es", "wr", "sr"]
    d1 = df[base & partner_ok].copy()
    for c in cols:
        d1[f"d_{c}"] = d1[c] - df[c].shift(H).loc[d1.index]
    d1 = d1.dropna(subset=[f"d_{c}" for c in cols]).reset_index(drop=True)
    ym1, hd1 = N.fe_matrix(d1, False)
    X1 = np.column_stack([ym1, hd1[:, 1:], d1.d_temp, d1.d_temp ** 2, d1.d_wr, d1.d_sr, d1.d_wr ** 2, d1.d_sr ** 2])
    sets["V1 error"] = dict(d=d1, y=N.ols_resid(d1.d_lnL.to_numpy(), X1), p=N.ols_resid(d1.d_p.to_numpy(), X1),
                            Z=np.column_stack([N.ols_resid(c, X1) for c in Zm(d1.d_ew.to_numpy(), d1.d_es.to_numpy()).T]))

    # V3: differenced + boosted double ML, controls incl. realised wind and PV
    d3 = df[base & partner_ok].copy()
    for c in ("lnL", "ew", "es", "p", "temp", "dem", "wr", "sr"):
        d3[f"d_{c}"] = d3[c] - df[c].shift(H).loc[d3.index]
    for s in ("lnL", "p"):
        d3[f"d_{s}_7"] = df[f"{s}_7"].loc[d3.index] - df[f"{s}_14"].loc[d3.index]
        d3[f"d_{s}_14"] = df[f"{s}_14"].loc[d3.index] - df[f"{s}_21"].loc[d3.index]
        d3[f"d_{s}_28"] = df[f"{s}_28"].loc[d3.index] - df[s].shift(35 * 24).loc[d3.index]
    d3["gas"] = df["gas"].loc[d3.index]
    need = ["d_lnL", "d_ew", "d_es", "d_p", "d_temp", "d_dem", "d_wr", "d_sr", "d_lnL_7", "d_lnL_14", "d_lnL_28", "d_p_7", "d_p_14", "d_p_28", "gas", "temp", "wr", "sr"]
    d3 = d3.dropna(subset=need).reset_index(drop=True)
    g = d3.groupby("date")
    tmean, tmin, tmax = g.temp.transform("mean"), g.temp.transform("min"), g.temp.transform("max")
    wm, sm = g.wr.transform("mean"), g.sr.transform("mean")
    X3 = np.column_stack([d3.hour, d3.dow, d3.date.dt.month, d3.date.dt.dayofyear, d3.d_temp, d3.temp, tmean, tmin, tmax, d3.d_dem, d3.d_wr, d3.d_sr, d3.wr, d3.sr, wm, sm,
                          d3.d_lnL_7, d3.d_lnL_14, d3.d_lnL_28, d3.d_p_7, d3.d_p_14, d3.d_p_28, d3.gas])
    order = d3.date.rank(method="dense").to_numpy()
    blocks = np.minimum((order / order.max() * 10).astype(int), 9)
    Y3 = np.column_stack([d3.d_lnL, d3.d_p, d3.d_ew, d3.d_es, d3.d_ew ** 2, d3.d_es ** 2])
    R3 = N.gb_resid(Y3, X3, blocks, d3.date.to_numpy())
    sets["V3 error"] = dict(d=d3, y=R3[:, 0], p=R3[:, 1], Z=R3[:, 2:])
    print("V3 error residuals done", flush=True)
    keep = [i for i in range(X3.shape[1]) if i != 16]  # drop d_lnL_7 (placebo outcome)
    Y3p = np.column_stack([d3.d_lnL_7, d3.d_p, d3.d_ew, d3.d_es, d3.d_ew ** 2, d3.d_es ** 2])
    R3p = N.gb_resid(Y3p, X3[:, keep], blocks, d3.date.to_numpy())
    sets["V3 error placebo"] = dict(d=d3, y=R3p[:, 0], p=R3p[:, 1], Z=R3p[:, 2:])
    sets["_weather"] = dict(W=np.column_stack([d3.d_temp, d3.d_temp ** 2, d3.temp, d3.temp ** 2, tmean, tmin, tmax]))
    return sets, pbar


def balance(sub_d, Z, W):
    """Q2: cluster-robust Wald test of the residualised instruments on weather; Bonferroni over columns."""
    g = pd.factorize(sub_d.date)[0]
    st = E.starts_of(sub_d.date.to_numpy())
    X = np.column_stack([np.ones(len(W)), W])
    ps = []
    A = np.linalg.inv(X.T @ X)
    for j in range(Z.shape[1]):
        b = A @ X.T @ Z[:, j]
        e = Z[:, j] - X @ b
        sc = np.add.reduceat(X * e[:, None], st, axis=0)
        V = A @ (sc.T @ sc) @ A
        w = float(b[1:] @ np.linalg.inv(V[1:, 1:]) @ b[1:])
        ps.append(float(stats.chi2.sf(w, W.shape[1])))
    return min(1.0, min(ps) * len(ps)), ps


def main():
    if CACHE.exists():
        sets, pbar = pickle.load(open(CACHE, "rb"))
    else:
        sets, pbar = build_sets()
        CACHE.parent.mkdir(exist_ok=True)
        pickle.dump((sets, pbar), open(CACHE, "wb"))
    rng = np.random.default_rng(SEED)
    s = sets["V3 error"]
    d = s["d"]
    full = E.Sub(d, s["y"], s["p"], s["Z"], np.ones(len(d), bool), [0, 1, 2, 3])
    F = full.first_stage_F(full.Z0)
    se_el = full.fast(full.Z0)[1] * pbar
    q1 = bool(F >= 10 and 2.8 * se_el <= 0.25)
    print(f"Q1 first stage F {F:.2f}, se_elasticity {se_el:.4f}, detectable {2.8 * se_el:.4f} -> {'PASS' if q1 else 'FAIL, stop'}", flush=True)
    if not q1:
        pd.DataFrame([dict(rule="Q1", F=F, se_elasticity=se_el, detectable=2.8 * se_el, passed=False)]).to_csv(T.OUT / "industry_iv_forecast_error_checks.csv", index=False)
        return
    pq2, ps = balance(d, s["Z"], sets["_weather"]["W"])
    print(f"Q2 balance Bonferroni p {pq2:.4f} (columns {np.round(ps, 4).tolist()})", flush=True)
    rows = []
    all4 = [0, 1, 2, 3]
    jobs = {"V1 error": ["full"], "V3 error placebo": ["full"], "V3 error": ["full", "wind only", "solar only", "2019", "2021", "2022", "2023", "night 0-7", "day 8-17", "evening 18-23"]}
    for name, blocks in jobs.items():
        st = sets[name]
        dd = st["d"]
        assert dd.date.is_monotonic_increasing
        srcs = E.perm_sources(dd, rng, E.NPERM)
        yr, hr = dd.date.dt.year.to_numpy(), dd.hour.to_numpy()
        masks = {"full": (np.ones(len(dd), bool), all4), "wind only": (np.ones(len(dd), bool), [0, 2]), "solar only": (np.ones(len(dd), bool), [1, 3]),
                 **{str(y): (yr == y, all4) for y in (2019, 2021, 2022, 2023)}, "night 0-7": (hr <= 7, all4), "day 8-17": ((hr >= 8) & (hr <= 17), all4), "evening 18-23": (hr >= 18, all4)}
        for b in blocks:
            m, cols = masks[b]
            sub = E.Sub(dd, st["y"], st["p"], st["Z"], m, cols)
            sub.Zfull = st["Z"]
            r, _ = E.run_sub(sub, srcs, pbar, grid_scale=40.0)
            if name == "V3 error" and b == "full":
                r["hansen_J"], r["hansen_p"] = sub.hansen(sub.Z0)
            rows.append(dict(variant=name, block=b, **r))
            print(name, b, {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in r.items() if k in ("F", "elasticity", "se_elasticity", "rand_lo", "rand_hi", "p_t_rank", "p_ar0_rank")}, flush=True)
    R = pd.DataFrame(rows)
    R.round(5).to_csv(T.OUT / "industry_iv_forecast_error.csv", index=False)
    g = lambda v, b: R[(R.variant == v) & (R.block == b)].iloc[0]
    M, P = g("V3 error", "full"), g("V3 error placebo", "full")
    prev = pd.read_csv(T.OUT / "industry_iv_estimation.csv")
    prev = prev[(prev.variant == "V3 difference + double ML") & (prev.block == "full")].iloc[0]
    ch = [("Q1 first stage", True, f"F {F:.1f}, detectable {2.8 * se_el:.4f}"), ("Q2 balance", bool(pq2 > 0.05), f"Bonferroni p {pq2:.4f}")]
    ch.append(("Q3 placebo outcome", bool(P.p_t_rank > 0.05 and abs(P.elasticity) < 0.01), f"elasticity {P.elasticity:.4f} [{P.rand_lo:.4f},{P.rand_hi:.4f}], p_t {P.p_t_rank:.3f}"))
    ch.append(("Q4 estimate", bool(M.elasticity < 0 and abs(M.elasticity) <= 1 and M.p_t_rank <= 0.05 and (M.rand_hi < 0 or M.rand_lo > 0)), f"elasticity {M.elasticity:.4f} [{M.rand_lo:.4f},{M.rand_hi:.4f}], p_t {M.p_t_rank:.3f}, p_AR0 {M.p_ar0_rank:.3f}"))
    w, so = g("V3 error", "wind only"), g("V3 error", "solar only")
    inside = lambda a, b: bool(b.rand_lo <= a.elasticity <= b.rand_hi)
    weak = bool(so.F < 10)
    ok5 = bool(M.hansen_p > 0.05 and (weak or (inside(w, so) and inside(so, w))))
    ch.append(("Q5 overidentification", ok5, f"J {M.hansen_J:.2f} p {M.hansen_p:.3f}; wind {w.elasticity:.4f} [{w.rand_lo:.4f},{w.rand_hi:.4f}] F {w.F:.1f}; solar {so.elasticity:.4f} [{so.rand_lo:.4f},{so.rand_hi:.4f}] F {so.F:.1f}"))
    ys = [g("V3 error", y) for y in ("2019", "2021", "2022", "2023")]
    b_, s_ = np.array([y.slope for y in ys]), np.array([y.se_slope for y in ys])
    wb = np.sum(b_ / s_ ** 2) / np.sum(1 / s_ ** 2)
    wp = float(stats.chi2.sf(np.sum((b_ - wb) ** 2 / s_ ** 2), 3))
    ch.append(("Q6 stability over years", bool(len(set(np.sign(b_))) == 1 and wp > 0.05), "elasticities " + ", ".join(f"{y.elasticity:.4f}" for y in ys) + f"; equality p {wp:.3f}"))
    v1 = g("V1 error", "full")
    ch.append(("Q7 comparison with forecast design (description)", None, f"error design {M.elasticity:.4f} vs forecast-design interval [{prev.rand_lo:.4f},{prev.rand_hi:.4f}] inside {bool(prev.rand_lo <= M.elasticity <= prev.rand_hi)}; V1 error {v1.elasticity:.4f} inside V3-error interval {bool(M.rand_lo <= v1.elasticity <= M.rand_hi)}"))
    ch.append(("Q8 hour blocks (exploratory)", None, "; ".join(f"{b} {g('V3 error', b).elasticity:.4f} [{g('V3 error', b).rand_lo:.4f},{g('V3 error', b).rand_hi:.4f}]" for b in ("night 0-7", "day 8-17", "evening 18-23"))))
    C = pd.DataFrame(ch, columns=["rule", "pass", "detail"])
    C.to_csv(T.OUT / "industry_iv_forecast_error_checks.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 220)
    print("\n", R[["variant", "block", "n", "F", "elasticity", "se_elasticity", "rand_lo", "rand_hi", "p_t_rank", "p_ar0_rank"]].round(4).to_string(index=False))
    print("\n", C.to_string(index=False))


if __name__ == "__main__":
    main()
