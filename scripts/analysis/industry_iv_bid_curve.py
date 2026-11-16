"""Run of docs/specs/2026-11-17-industry-iv-bid-curve-design.md (rules B1-B10).

    .venv/bin/python scripts/analysis/industry_iv_bid_curve.py

Instrument: simulated price effect of the D-1 forecast miss on the day's effective offer curve (outputs/cache/step): dp_w = clear(d_tot + wind forecast - realised wind) - clear(d_tot), dp_s likewise for PV.
V3 (week-on-week difference + boosted double ML) primary, V1 secondary, Variant S (demand forecast in place of cleared demand), placebo outcome (7-day-lagged differenced load). B1 and B2 are gates:
if B1 fails no estimation; if B2 fails no slope is computed or stored. Inference as in industry_iv_estimation.py. Writes outputs/tables/industry_iv_bid_curve.csv and industry_iv_bid_curve_checks.csv. Seed 20261117.
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_iv_estimation as E  # noqa: E402
import industry_iv_forecast_error as FE  # noqa: E402
import industry_iv_noise_reducers as N  # noqa: E402
import tou_did as T  # noqa: E402
import tou_price_effect as PE  # noqa: E402

ROOT, H, SEED = T.ROOT, N.H, N.SEED
CACHE = ROOT / "data/cache_tou/industry_iv_curve_sets.pkl"


def instruments(df):
    months = [f"{y}{m:02d}" for y in range(2019, 2024) for m in range(1, 13)]
    cv = PE.Curves(months)
    h = cv.h[cv.h.valid.astype(bool)].copy()
    cnt = cv.h.groupby("date").period.transform("count")
    h = h[h.index.isin(cv.h.index[cnt == 24])].copy()
    h["hour"] = h.period - 1
    m = df[["date", "hour", "wind", "solar", "wr", "sr", "p"]].copy()
    h = h.merge(m, on=["date", "hour"], how="inner").dropna(subset=["wind", "solar", "wr", "sr"]).reset_index(drop=True)
    ew, es = (h.wind - h.wr).to_numpy() * 1000, (h.solar - h.sr).to_numpy() * 1000
    ratio = h.assign(ym=h.date.dt.to_period("M")).groupby(["ym", "hour"]).apply(lambda g: g.d_tot.mean() / g.F_demand.mean(), include_groups=False)
    dpred = h.F_demand.to_numpy() * ratio.reindex(pd.MultiIndex.from_arrays([h.date.dt.to_period("M"), h.hour])).to_numpy()
    hid, dt = h.hid.to_numpy(), h.d_tot.to_numpy()
    out = {k: np.empty(len(h)) for k in ("p0", "dpw", "dps", "dpw_s", "dps_s", "slope", "a0")}
    for j in range(len(h)):
        p0 = cv.clear(hid[j], dt[j])
        out["p0"][j] = p0
        out["dpw"][j], out["dps"][j] = cv.clear(hid[j], dt[j] + ew[j]) - p0, cv.clear(hid[j], dt[j] + es[j]) - p0
        q = dpred[j]
        p1 = cv.clear(hid[j], q)
        out["dpw_s"][j], out["dps_s"][j] = cv.clear(hid[j], q + ew[j]) - p1, cv.clear(hid[j], q + es[j]) - p1
        out["slope"][j] = (cv.clear(hid[j], dt[j] + 500) - cv.clear(hid[j], dt[j] - 500)) / 1000
        s, e = cv.start[hid[j]], cv.end[hid[j]]
        out["a0"][j] = cv.a[s:e][max(np.searchsorted(cv.price[s:e], 0.0, side="right") - 1, 0)]
    I = pd.DataFrame({"date": h.date, "hour": h.hour, "omie": h.p, **out})
    return I


def build_sets():
    df = N.build()
    rl = FE.realised()
    grid = df.set_index(["date", "hour"]).index
    df["wr"], df["sr"] = rl.wr.reindex(grid).to_numpy(), rl.sr.reindex(grid).to_numpy()
    I = instruments(df)
    b1 = float((np.abs(I.p0 - I.omie) <= 0.5).mean())
    print(f"B1 re-cleared price within EUR 0.50 of OMIE in {b1:.3f} of {len(I)} valid hours", flush=True)
    K = I.set_index(["date", "hour"])
    for c in ("dpw", "dps", "dpw_s", "dps_s", "slope", "a0"):
        df[c] = K[c].reindex(grid).to_numpy()
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
    sets = {"_b1": b1, "_corr_b3": None}

    def v3(zc, placebo=False):
        d3 = df[base & partner_ok].copy()
        for c in ["lnL", "p", "temp", "dem", "wr", "sr"] + zc:
            d3[f"d_{c}"] = d3[c] - df[c].shift(H).loc[d3.index]
        for s in ("lnL", "p"):
            d3[f"d_{s}_7"] = df[f"{s}_7"].loc[d3.index] - df[f"{s}_14"].loc[d3.index]
            d3[f"d_{s}_14"] = df[f"{s}_14"].loc[d3.index] - df[f"{s}_21"].loc[d3.index]
            d3[f"d_{s}_28"] = df[f"{s}_28"].loc[d3.index] - df[s].shift(35 * 24).loc[d3.index]
        d3["gas"] = df["gas"].loc[d3.index]
        need = ["d_lnL", "d_p", "d_temp", "d_dem", "d_wr", "d_sr", "d_lnL_7", "d_lnL_14", "d_lnL_28", "d_p_7", "d_p_14", "d_p_28", "gas", "temp", "wr", "sr", "slope", "a0"] + [f"d_{c}" for c in zc]
        d3 = d3.dropna(subset=need).reset_index(drop=True)
        g = d3.groupby("date")
        tmean, tmin, tmax = g.temp.transform("mean"), g.temp.transform("min"), g.temp.transform("max")
        wm, sm, slm, a0m = g.wr.transform("mean"), g.sr.transform("mean"), g.slope.transform("mean"), g.a0.transform("mean")
        names = ["hour", "dow", "month", "doy", "d_temp", "temp", "tmean", "tmin", "tmax", "d_dem", "d_wr", "d_sr", "wr", "sr", "wm", "sm", "slope", "a0", "slm", "a0m",
                 "d_lnL_7", "d_lnL_14", "d_lnL_28", "d_p_7", "d_p_14", "d_p_28", "gas"]
        cols = dict(hour=d3.hour, dow=d3.dow, month=d3.date.dt.month, doy=d3.date.dt.dayofyear, d_temp=d3.d_temp, temp=d3.temp, tmean=tmean, tmin=tmin, tmax=tmax, d_dem=d3.d_dem, d_wr=d3.d_wr, d_sr=d3.d_sr,
                    wr=d3.wr, sr=d3.sr, wm=wm, sm=sm, slope=d3.slope, a0=d3.a0, slm=slm, a0m=a0m, d_lnL_7=d3.d_lnL_7, d_lnL_14=d3.d_lnL_14, d_lnL_28=d3.d_lnL_28, d_p_7=d3.d_p_7, d_p_14=d3.d_p_14,
                    d_p_28=d3.d_p_28, gas=d3.gas)
        keep = [n for n in names if not (placebo and n == "d_lnL_7")]
        X = np.column_stack([cols[n] for n in keep])
        order = d3.date.rank(method="dense").to_numpy()
        blocks = np.minimum((order / order.max() * 10).astype(int), 9)
        y = d3.d_lnL_7 if placebo else d3.d_lnL
        Y = np.column_stack([y, d3.d_p] + [d3[f"d_{c}"] for c in zc])
        R = N.gb_resid(Y, X, blocks, d3.date.to_numpy())
        return dict(d=d3, y=R[:, 0], p=R[:, 1], Z=R[:, 2:], W=np.column_stack([d3.d_temp, d3.d_temp ** 2, d3.temp, d3.temp ** 2, tmean, tmin, tmax]), raw_p=d3.d_p.to_numpy(), raw_z=np.column_stack([d3[f"d_{c}"] for c in zc]),
                    lvl=(d3.p.to_numpy(), d3[zc[0]].to_numpy() + d3[zc[1]].to_numpy()))

    sets["V3 curve"] = v3(["dpw", "dps"])
    print("V3 curve residuals done", flush=True)
    sets["V3 curve placebo"] = v3(["dpw", "dps"], placebo=True)
    sets["V3 curve S"] = v3(["dpw_s", "dps_s"])
    print("V3 S residuals done", flush=True)
    cols = ["lnL", "p", "temp", "wr", "sr", "dpw", "dps"]
    d1 = df[base & partner_ok].copy()
    for c in cols:
        d1[f"d_{c}"] = d1[c] - df[c].shift(H).loc[d1.index]
    d1 = d1.dropna(subset=[f"d_{c}" for c in cols] + ["slope", "a0"]).reset_index(drop=True)
    ym1, hd1 = N.fe_matrix(d1, False)
    X1 = np.column_stack([ym1, hd1[:, 1:], d1.d_temp, d1.d_temp ** 2, d1.d_wr, d1.d_sr, d1.d_wr ** 2, d1.d_sr ** 2, d1.slope, d1.a0])
    sets["V1 curve"] = dict(d=d1, y=N.ols_resid(d1.d_lnL.to_numpy(), X1), p=N.ols_resid(d1.d_p.to_numpy(), X1), Z=np.column_stack([N.ols_resid(d1[f"d_{c}"].to_numpy(), X1) for c in ("dpw", "dps")]))
    return sets, pbar


def main():
    if CACHE.exists():
        sets, pbar = pickle.load(open(CACHE, "rb"))
    else:
        sets, pbar = build_sets()
        CACHE.parent.mkdir(exist_ok=True)
        pickle.dump((sets, pbar), open(CACHE, "wb"))
    b1 = sets["_b1"]
    print(f"B1 {'PASS' if b1 >= 0.95 else 'FAIL, stop'} ({b1:.3f})", flush=True)
    if b1 < 0.95:
        pd.DataFrame([dict(rule="B1", share=b1, passed=False)]).to_csv(T.OUT / "industry_iv_bid_curve_checks.csv", index=False)
        return
    rng = np.random.default_rng(SEED)
    s = sets["V3 curve"]
    d = s["d"]
    full = E.Sub(d, s["y"], s["p"], s["Z"], np.ones(len(d), bool), [0, 1])
    F = full.first_stage_F(full.Z0)
    se_el = full.fast(full.Z0)[1] * pbar
    b2 = bool(F >= 10 and 2.8 * se_el <= 0.25)
    print(f"B2 first stage F {F:.2f}, se_elasticity {se_el:.4f}, detectable {2.8 * se_el:.4f} -> {'PASS' if b2 else 'FAIL, stop'}", flush=True)
    if not b2:
        pd.DataFrame([dict(rule="B1", share=b1, passed=True), dict(rule="B2", F=F, se_elasticity=se_el, detectable=2.8 * se_el, passed=False)]).to_csv(T.OUT / "industry_iv_bid_curve_checks.csv", index=False)
        return
    # B3: unresidualised first stage, price level on the simulated effect (date-clustered OLS with constant), and the differenced version
    def ols_slope(y, x, dates):
        X = np.column_stack([np.ones(len(x)), x])
        A = np.linalg.inv(X.T @ X)
        b = A @ X.T @ y
        e = y - X @ b
        sc = np.add.reduceat(X * e[:, None], E.starts_of(dates), axis=0)
        return float(b[1]), float(np.sqrt((A @ (sc.T @ sc) @ A)[1, 1]))
    b3_lvl = ols_slope(s["lvl"][0], s["lvl"][1], d.date.to_numpy())
    b3_dif = ols_slope(s["raw_p"], s["raw_z"].sum(1), d.date.to_numpy())
    b3 = bool(0.5 <= b3_lvl[0] <= 1.5 and b3_lvl[0] > 0)
    print(f"B3 price on simulated effect: levels {b3_lvl[0]:.3f} (se {b3_lvl[1]:.3f}), differenced {b3_dif[0]:.3f} (se {b3_dif[1]:.3f})", flush=True)
    pq2, ps = FE.balance(d, s["Z"], s["W"])
    print(f"B4 balance Bonferroni p {pq2:.4f}", flush=True)
    rows = []
    jobs = {"V1 curve": ["full"], "V3 curve S": ["full"], "V3 curve placebo": ["full"],
            "V3 curve": ["full", "wind only", "solar only", "2019", "2020", "2021", "2022", "2023", "night 0-7", "day 8-17", "evening 18-23"]}
    for name, blocks in jobs.items():
        st = sets[name]
        dd = st["d"]
        assert dd.date.is_monotonic_increasing
        srcs = E.perm_sources(dd, rng, E.NPERM)
        yr, hr = dd.date.dt.year.to_numpy(), dd.hour.to_numpy()
        all2 = [0, 1]
        masks = {"full": (np.ones(len(dd), bool), all2), "wind only": (np.ones(len(dd), bool), [0]), "solar only": (np.ones(len(dd), bool), [1]),
                 **{str(y): (yr == y, all2) for y in (2019, 2020, 2021, 2022, 2023)}, "night 0-7": (hr <= 7, all2), "day 8-17": ((hr >= 8) & (hr <= 17), all2), "evening 18-23": (hr >= 18, all2)}
        for b in blocks:
            m, cols = masks[b]
            sub = E.Sub(dd, st["y"], st["p"], st["Z"], m, cols)
            sub.Zfull = st["Z"]
            r, _ = E.run_sub(sub, srcs, pbar, grid_scale=40.0)
            if name == "V3 curve" and b == "full":
                r["hansen_J"], r["hansen_p"] = sub.hansen(sub.Z0)
            rows.append(dict(variant=name, block=b, **r))
            print(name, b, {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in r.items() if k in ("F", "elasticity", "se_elasticity", "rand_lo", "rand_hi", "p_t_rank", "p_ar0_rank")}, flush=True)
    R = pd.DataFrame(rows)
    R.round(5).to_csv(T.OUT / "industry_iv_bid_curve.csv", index=False)
    g = lambda v, b: R[(R.variant == v) & (R.block == b)].iloc[0]
    M, P = g("V3 curve", "full"), g("V3 curve placebo", "full")
    ch = [("B1 curve check", True, f"share {b1:.3f}"), ("B2 first stage", True, f"F {F:.1f}, detectable {2.8 * se_el:.4f}"),
          ("B3 first-stage economics", b3, f"levels coefficient {b3_lvl[0]:.3f} (se {b3_lvl[1]:.3f}); differenced {b3_dif[0]:.3f} (se {b3_dif[1]:.3f})"), ("B4 balance", bool(pq2 > 0.05), f"Bonferroni p {pq2:.4f}")]
    ch.append(("B5 placebo outcome", bool(P.p_t_rank > 0.05 and abs(P.elasticity) < 0.01), f"elasticity {P.elasticity:.4f} [{P.rand_lo:.4f},{P.rand_hi:.4f}], p_t {P.p_t_rank:.3f}"))
    ch.append(("B6 estimate", bool(M.elasticity < 0 and abs(M.elasticity) <= 1 and M.p_t_rank <= 0.05 and (M.rand_hi < 0 or M.rand_lo > 0)), f"elasticity {M.elasticity:.4f} [{M.rand_lo:.4f},{M.rand_hi:.4f}], p_t {M.p_t_rank:.3f}, p_AR0 {M.p_ar0_rank:.3f}"))
    w, so = g("V3 curve", "wind only"), g("V3 curve", "solar only")
    inside = lambda a, b: bool(b.rand_lo <= a.elasticity <= b.rand_hi)
    weak = bool(min(w.F, so.F) < 10)
    ok7 = bool(M.hansen_p > 0.05 and (weak or (inside(w, so) and inside(so, w))))
    ch.append(("B7 overidentification", ok7, f"J {M.hansen_J:.2f} p {M.hansen_p:.3f}; wind {w.elasticity:.4f} [{w.rand_lo:.4f},{w.rand_hi:.4f}] F {w.F:.1f}; solar {so.elasticity:.4f} [{so.rand_lo:.4f},{so.rand_hi:.4f}] F {so.F:.1f}"))
    ys = [g("V3 curve", y) for y in ("2019", "2020", "2021", "2022", "2023")]
    b_, s_ = np.array([y.slope for y in ys]), np.array([y.se_slope for y in ys])
    wb = np.sum(b_ / s_ ** 2) / np.sum(1 / s_ ** 2)
    wp = float(stats.chi2.sf(np.sum((b_ - wb) ** 2 / s_ ** 2), 4))
    ch.append(("B8 stability over years", bool(len(set(np.sign(b_))) == 1 and wp > 0.05), "elasticities " + ", ".join(f"{y.elasticity:.4f}" for y in ys) + f"; equality p {wp:.3f}"))
    v1, sv = g("V1 curve", "full"), g("V3 curve S", "full")
    ch.append(("B9 sensitivity", bool(M.rand_lo <= v1.elasticity <= M.rand_hi and M.rand_lo <= sv.elasticity <= M.rand_hi), f"V1 {v1.elasticity:.4f}, S {sv.elasticity:.4f} vs V3 [{M.rand_lo:.4f},{M.rand_hi:.4f}]"))
    prev = pd.read_csv(T.OUT / "industry_iv_estimation.csv")
    prev = prev[(prev.variant == "V3 difference + double ML") & (prev.block == "full")].iloc[0]
    ch.append(("B10 comparison and hour blocks (exploratory)", None, f"forecast design {prev.elasticity:.4f} [{prev.rand_lo:.4f},{prev.rand_hi:.4f}]; " + "; ".join(f"{b} {g('V3 curve', b).elasticity:.4f} [{g('V3 curve', b).rand_lo:.4f},{g('V3 curve', b).rand_hi:.4f}]" for b in ("night 0-7", "day 8-17", "evening 18-23"))))
    C = pd.DataFrame(ch, columns=["rule", "pass", "detail"])
    C.to_csv(T.OUT / "industry_iv_bid_curve_checks.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 230)
    print("\n", R[["variant", "block", "n", "F", "elasticity", "se_elasticity", "rand_lo", "rand_hi", "p_t_rank", "p_ar0_rank"]].round(4).to_string(index=False))
    print("\n", C.to_string(index=False))


if __name__ == "__main__":
    main()
