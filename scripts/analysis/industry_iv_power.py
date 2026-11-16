"""Run of docs/specs/2026-11-17-industry-iv-power-design.md (rules P1-P10).

    .venv/bin/python scripts/analysis/industry_iv_power.py

Bid-curve instrument (dp_w, dp_s) on an extended sample: all days (weekends and national holidays included; lockdown block out), 2019-01-01 -> 2025-09-30. V3 pipeline (week-on-week difference, boosted
double ML, partner day must have the same holiday status). The two residualised effects are combined with weights from the first stage on the OTHER half (odd/even ISO weeks); 1-instrument 2SLS, rank of |t|
and permutation Anderson-Rubin. P1 and P2 are gates. Writes outputs/tables/industry_iv_power.csv and industry_iv_power_checks.csv. Seed 20261117.
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_iv_bid_curve as BC  # noqa: E402
import industry_iv_estimation as E  # noqa: E402
import industry_iv_forecast_error as FE  # noqa: E402
import industry_iv_noise_reducers as N  # noqa: E402
import tou_did as T  # noqa: E402

ROOT, H, SEED = T.ROOT, N.H, N.SEED
CACHE = ROOT / "data/cache_tou/industry_iv_power_sets.pkl"
END = "2025-09-30"


def other_half_weights(R2, p, wk):
    """Combined instrument: rows of even ISO weeks use weights fitted on odd weeks and vice versa."""
    z = np.zeros(len(p))
    for par in (0, 1):
        tr = wk % 2 != par
        b, *_ = np.linalg.lstsq(R2[tr], p[tr], rcond=None)
        z[wk % 2 == par] = R2[wk % 2 == par] @ b
    return z


def build_sets():
    df = N.build(END)
    rl = FE.realised()
    grid = df.set_index(["date", "hour"]).index
    df["wr"], df["sr"] = rl.wr.reindex(grid).to_numpy(), rl.sr.reindex(grid).to_numpy()
    months = [f"{y}{m:02d}" for y in range(2019, 2026) for m in range(1, 13) if not (y == 2025 and m > 9)]
    I = BC.instruments(df, months)
    b1 = float((np.abs(I.p0 - I.omie) <= 0.5).mean())
    print(f"P1 re-cleared price within EUR 0.50 of OMIE in {b1:.3f} of {len(I)} valid hours", flush=True)
    K = I.set_index(["date", "hour"])
    for c in ("dpw", "dps", "slope", "a0"):
        df[c] = K[c].reindex(grid).to_numpy()
    for s in ("lnL", "p"):
        for k in (7, 14, 21, 28):
            df[f"{s}_{k}"] = df[s].shift(k * 24)
    df["dow"] = df.date.dt.dayofweek
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    df["hol"] = df.date.isin(hes).astype(float)
    df["hol_7"] = df.date.sub(pd.Timedelta(days=7)).isin(hes).astype(float)
    covid = df.date.between("2020-03-01", "2020-06-30")
    base = (df.date >= "2019-01-01") & ~covid
    partner_ok = (df.hol == df.hol_7) & ~(df.date - pd.Timedelta(days=7)).between("2020-03-01", "2020-06-30")
    pbar = float(df.loc[base, "p"].mean())
    sets = {"_b1": b1}

    def pipeline(sel, placebo=False):
        d3 = df[sel].copy()
        for c in ["lnL", "p", "temp", "dem", "wr", "sr", "dpw", "dps"]:
            d3[f"d_{c}"] = d3[c] - df[c].shift(H).loc[d3.index]
        for s in ("lnL", "p"):
            d3[f"d_{s}_7"] = df[f"{s}_7"].loc[d3.index] - df[f"{s}_14"].loc[d3.index]
            d3[f"d_{s}_14"] = df[f"{s}_14"].loc[d3.index] - df[f"{s}_21"].loc[d3.index]
            d3[f"d_{s}_28"] = df[f"{s}_28"].loc[d3.index] - df[s].shift(35 * 24).loc[d3.index]
        d3["gas"] = df["gas"].loc[d3.index]
        need = ["d_lnL", "d_p", "d_temp", "d_dem", "d_wr", "d_sr", "d_dpw", "d_dps", "d_lnL_7", "d_lnL_14", "d_lnL_28", "d_p_7", "d_p_14", "d_p_28", "gas", "temp", "wr", "sr", "slope", "a0"]
        d3 = d3.dropna(subset=need).reset_index(drop=True)
        g = d3.groupby("date")
        tmean, tmin, tmax = g.temp.transform("mean"), g.temp.transform("min"), g.temp.transform("max")
        wm, sm, slm, a0m = g.wr.transform("mean"), g.sr.transform("mean"), g.slope.transform("mean"), g.a0.transform("mean")
        cols = dict(hour=d3.hour, dow=d3.dow, hol=d3.hol, month=d3.date.dt.month, doy=d3.date.dt.dayofyear, d_temp=d3.d_temp, temp=d3.temp, tmean=tmean, tmin=tmin, tmax=tmax, d_dem=d3.d_dem,
                    d_wr=d3.d_wr, d_sr=d3.d_sr, wr=d3.wr, sr=d3.sr, wm=wm, sm=sm, slope=d3.slope, a0=d3.a0, slm=slm, a0m=a0m, d_lnL_7=d3.d_lnL_7, d_lnL_14=d3.d_lnL_14, d_lnL_28=d3.d_lnL_28,
                    d_p_7=d3.d_p_7, d_p_14=d3.d_p_14, d_p_28=d3.d_p_28, gas=d3.gas)
        keep = [n for n in cols if not (placebo and n == "d_lnL_7")]
        X = np.column_stack([cols[n] for n in keep])
        order = d3.date.rank(method="dense").to_numpy()
        blocks = np.minimum((order / order.max() * 10).astype(int), 9)
        y = d3.d_lnL_7 if placebo else d3.d_lnL
        Y = np.column_stack([y, d3.d_p, d3.d_dpw, d3.d_dps])
        R = N.gb_resid(Y, X, blocks, d3.date.to_numpy())
        wk = d3.date.dt.isocalendar().week.to_numpy().astype(int)
        zc = other_half_weights(R[:, 2:4], R[:, 1], wk)
        # ML first stage: cross-fitted boosting of the residualised price on the residualised effects and the curve variables
        Xz = np.column_stack([R[:, 2], R[:, 3], d3.slope, d3.a0, d3.hour, d3.date.dt.month])
        zml = R[:, 1] - N.gb_resid(R[:, [1]], Xz, blocks, d3.date.to_numpy())[:, 0]
        return dict(d=d3, y=R[:, 0], p=R[:, 1], Z=np.column_stack([R[:, 2], R[:, 3], zc, zml]),
                    W=np.column_stack([d3.d_temp, d3.d_temp ** 2, d3.temp, d3.temp ** 2, tmean, tmin, tmax]))

    sets["main"] = pipeline(base & partner_ok)
    print("main residuals done", flush=True)
    sets["placebo"] = pipeline(base & partner_ok, placebo=True)
    print("placebo residuals done", flush=True)
    orig = base & partner_ok & (df.dow < 5) & (df.hol == 0) & (df.date <= "2023-12-31")
    sets["orig"] = pipeline(orig)
    print("original-sample residuals done", flush=True)
    return sets, pbar


def main():
    if CACHE.exists():
        sets, pbar = pickle.load(open(CACHE, "rb"))
    else:
        sets, pbar = build_sets()
        CACHE.parent.mkdir(exist_ok=True)
        pickle.dump((sets, pbar), open(CACHE, "wb"))
    b1 = sets["_b1"]
    print(f"P1 {'PASS' if b1 >= 0.95 else 'FAIL, stop'} ({b1:.3f})", flush=True)
    if b1 < 0.95:
        pd.DataFrame([dict(rule="P1", share=b1, passed=False)]).to_csv(T.OUT / "industry_iv_power_checks.csv", index=False)
        return
    rng = np.random.default_rng(SEED)
    s = sets["main"]
    d = s["d"]
    full = E.Sub(d, s["y"], s["p"], s["Z"], np.ones(len(d), bool), [2])
    F = full.first_stage_F(full.Z0)
    se_el = full.fast(full.Z0)[1] * pbar
    p2 = bool(F >= 10 and 2.8 * se_el <= 0.25)
    print(f"P2 first stage F {F:.2f}, n {len(d)}, se_elasticity {se_el:.4f}, detectable {2.8 * se_el:.4f} -> {'PASS' if p2 else 'FAIL, stop'}", flush=True)
    if not p2:
        pd.DataFrame([dict(rule="P1", share=b1, passed=True), dict(rule="P2", F=F, n=len(d), se_elasticity=se_el, detectable=2.8 * se_el, passed=False)]).to_csv(T.OUT / "industry_iv_power_checks.csv", index=False)
        return
    pq4, _ = FE.balance(d, s["Z"][:, [2]], s["W"])
    print(f"P4 balance Bonferroni p {pq4:.4f}", flush=True)
    rows = []
    jobs = {"placebo": ["full"], "orig": ["full"], "main": ["full", "ML instrument", "wind only", "solar only", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "weekend+holiday", "2024-25",
                                                       "night 0-7", "day 8-17", "evening 18-23"]}
    for name, blocks in jobs.items():
        st = sets[name]
        dd = st["d"]
        assert dd.date.is_monotonic_increasing
        srcs = E.perm_sources(dd, rng, E.NPERM)
        yr, hr = dd.date.dt.year.to_numpy(), dd.hour.to_numpy()
        nw = ((dd.dow >= 5) | (dd.hol > 0)).to_numpy()
        ones = np.ones(len(dd), bool)
        masks = {"full": (ones, [2]), "ML instrument": (ones, [3]), "wind only": (ones, [0]), "solar only": (ones, [1]), **{str(y): (yr == y, [2]) for y in range(2019, 2026)},
                 "weekend+holiday": (nw, [2]), "2024-25": (yr >= 2024, [2]), "night 0-7": (hr <= 7, [2]), "day 8-17": ((hr >= 8) & (hr <= 17), [2]), "evening 18-23": (hr >= 18, [2])}
        for b in blocks:
            m, cols = masks[b]
            sub = E.Sub(dd, st["y"], st["p"], st["Z"], m, cols)
            sub.Zfull = st["Z"]
            r, _ = E.run_sub(sub, srcs, pbar, grid_scale=40.0)
            rows.append(dict(variant=name, block=b, **r))
            print(name, b, {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in r.items() if k in ("n", "F", "elasticity", "se_elasticity", "rand_lo", "rand_hi", "p_t_rank", "p_ar0_rank")}, flush=True)
    R = pd.DataFrame(rows)
    R.round(5).to_csv(T.OUT / "industry_iv_power.csv", index=False)
    g = lambda v, b: R[(R.variant == v) & (R.block == b)].iloc[0]
    M, P, O, ML = g("main", "full"), g("placebo", "full"), g("orig", "full"), g("main", "ML instrument")
    prev = pd.read_csv(T.OUT / "industry_iv_bid_curve.csv")
    prev = prev[(prev.variant == "V3 curve") & (prev.block == "full")].iloc[0]
    ch = [("P1 curve check", True, f"share {b1:.3f}"), ("P2 first stage", True, f"F {F:.1f}, n {len(d)}, detectable {2.8 * se_el:.4f}"), ("P4 balance", bool(pq4 > 0.05), f"Bonferroni p {pq4:.4f}")]
    ch.insert(2, ("P3 placebo outcome", bool(P.p_t_rank > 0.05 and abs(P.elasticity) < 0.01), f"elasticity {P.elasticity:.4f} [{P.rand_lo:.4f},{P.rand_hi:.4f}], p_t {P.p_t_rank:.3f}, F {P.F:.1f}"))
    ok5 = bool(M.elasticity < 0 and abs(M.elasticity) <= 1 and M.p_t_rank <= 0.05 and M.p_ar0_rank <= 0.05 and (M.rand_hi < 0 or M.rand_lo > 0))
    ch.append(("P5 estimate", ok5, f"elasticity {M.elasticity:.4f} [{M.rand_lo:.4f},{M.rand_hi:.4f}], p_t {M.p_t_rank:.3f}, p_AR0 {M.p_ar0_rank:.3f}"))
    ch.append(("P6 consistency with earlier sample", bool(prev.rand_lo <= O.elasticity <= prev.rand_hi), f"original-sample combined {O.elasticity:.4f} [{O.rand_lo:.4f},{O.rand_hi:.4f}] F {O.F:.1f}; earlier {prev.elasticity:.4f} [{prev.rand_lo:.4f},{prev.rand_hi:.4f}]"))
    ch.append(("P7 where new hours matter (description)", None, "; ".join(f"{b} {g('main', b).elasticity:.4f} [{g('main', b).rand_lo:.4f},{g('main', b).rand_hi:.4f}] F {g('main', b).F:.1f} n {int(g('main', b).n)}" for b in ("weekend+holiday", "2024-25"))))
    ys = [g("main", str(y)) for y in range(2019, 2026)]
    use = [y for y in ys if y.F >= 10]
    if len(use) >= 2:
        b_, s_ = np.array([y.slope for y in use]), np.array([y.se_slope for y in use])
        wb = np.sum(b_ / s_ ** 2) / np.sum(1 / s_ ** 2)
        wp = float(stats.chi2.sf(np.sum((b_ - wb) ** 2 / s_ ** 2), len(use) - 1))
    else:
        wp = np.nan
    ch.append(("P8 stability over years", bool(wp > 0.05) if not np.isnan(wp) else None, "elasticities (F) " + ", ".join(f"{y.elasticity:.4f} ({y.F:.1f})" for y in ys) + f"; equality p over years with F>=10: {wp:.3f}"))
    ch.append(("P9 ML first stage", bool(M.rand_lo <= ML.elasticity <= M.rand_hi and ML.F >= 10), f"ML instrument {ML.elasticity:.4f} [{ML.rand_lo:.4f},{ML.rand_hi:.4f}] F {ML.F:.1f}"))
    ch.append(("P10 hour blocks (exploratory)", None, "; ".join(f"{b} {g('main', b).elasticity:.4f} [{g('main', b).rand_lo:.4f},{g('main', b).rand_hi:.4f}] F {g('main', b).F:.1f}" for b in ("night 0-7", "day 8-17", "evening 18-23"))))
    C = pd.DataFrame(ch, columns=["rule", "pass", "detail"])
    C.to_csv(T.OUT / "industry_iv_power_checks.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 230)
    print("\n", R[["variant", "block", "n", "F", "elasticity", "se_elasticity", "rand_lo", "rand_hi", "p_t_rank", "p_ar0_rank"]].round(4).to_string(index=False))
    print("\n", C.to_string(index=False))


if __name__ == "__main__":
    main()
