"""Run of docs/specs/2026-11-17-industry-iv-instrument-settlement-design.md (rules S1-S5, with the pre-run amendments in that file).

    .venv/bin/python scripts/analysis/industry_iv_instrument_settlement.py

Scores five instrument candidates for the industrial impact elasticity on first stage and placebo only; no elasticity on the real outcome is computed or stored.
Common sample: the rows of the bid-curve sets (data/cache_tou/industry_iv_curve_sets.pkl, 21,636 weekday hours 2019-2023) for which every candidate exists.
V3 recipe: week-on-week differences, boosted double ML (N.gb_resid, 10 time blocks) with predictors hour, weekday, month, day of year, d temp, d demand forecast, d ln load and d price at lags 7/14/28, gas.
C0 d wind and solar forecasts (+ squares). C1 d power-curve transform of national mean 100 m wind speed (+ square). C2 bid-curve instruments d_dpw, d_dps, each divided by its hour-of-day sd in 2019.
C3 C2 plus C2 x one-week-lagged offer-curve slope. C4 d planned and d fault outage MW (outage_event_hours). Placebo outcome: ln load of the same hour 7 days earlier, differenced.
F1 date-clustered first-stage F; F2 permutation p of the placebo IV t (1,000 permutations across days within year-month, seed 20261117); F3 first stage of the wind component on rows with national mean wind speed
below 5 m/s in both weeks (permutation p; ratio to full-sample coefficient). Blocks: full, 2019-21H1, 2021H2-23. Writes outputs/tables/industry_iv_instrument_settlement{,_rules}.csv.
"""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_iv_estimation as E  # noqa: E402
import industry_iv_noise_reducers as N  # noqa: E402
import tou_did as T  # noqa: E402

ROOT, H, SEED, NPERM = T.ROOT, N.H, N.SEED, 1000
IDLE_WS, MIN_IDLE = 5.0, 800


def local(ts):
    loc = ts.dt.tz_convert("Europe/Madrid")
    return pd.to_datetime(loc.dt.date), loc.dt.hour


def build_frame():
    sets, _ = pickle.load(open(ROOT / "data/cache_tou/industry_iv_curve_sets.pkl", "rb"))
    d = sets["V3 curve"]["d"].copy()
    df = N.build()
    a = pd.read_parquet(ROOT / "data/weather/weather_spain_aggregate.parquet")
    dt_, hr_ = local(a.utc_timestamp)
    w = pd.DataFrame({"date": dt_, "hour": hr_, "ws": a.wind_speed_100m_wind_sites}).drop_duplicates(["date", "hour"]).set_index(["date", "hour"]).ws
    grid = df.set_index(["date", "hour"]).index
    df["ws"] = w.reindex(grid).to_numpy()
    df["pc"] = np.minimum(df.ws / 12.0, 1.0) ** 3
    o = pd.read_parquet(ROOT / "outputs/tables/outage_event_hours.parquet")
    od, oh = local(pd.Series(o.utc))
    o = o.assign(date=od.to_numpy(), hour=oh.to_numpy())
    for cls in ("planned", "fault"):
        s = o[o.cls == cls].groupby(["date", "hour"]).lost_mw.sum()
        df[f"out_{cls}"] = s.reindex(grid).fillna(0.0).to_numpy()
    for c in ("wind", "solar", "ws", "pc", "out_planned", "out_fault", "slope"):
        if c in df:
            df[f"d_{c}"] = df[c] - df[c].shift(H)
    K = df[["date", "hour", "ws", "d_wind", "d_solar", "d_pc", "d_ws", "d_out_planned", "d_out_fault"]]
    d = d.merge(K, on=["date", "hour"], how="left")
    ws7 = df.set_index(["date", "hour"]).ws.shift(H)
    d["ws7"] = pd.Series(ws7.to_numpy(), index=grid).reindex(pd.MultiIndex.from_arrays([d.date, d.hour])).to_numpy()
    sl7 = d[["date", "hour", "slope"]].assign(date=lambda x: x.date + pd.Timedelta(days=7)).rename(columns={"slope": "slope7"})
    d = d.merge(sl7, on=["date", "hour"], how="left")
    sd = d[d.date.dt.year == 2019].groupby("hour")[["d_dpw", "d_dps"]].std()
    d["c2w"] = d.d_dpw / d.hour.map(sd.d_dpw)
    d["c2s"] = d.d_dps / d.hour.map(sd.d_dps)
    d["slope7z"] = (d.slope7 - d.slope7.mean()) / d.slope7.std()
    need = ["d_wind", "d_solar", "d_pc", "d_ws", "d_out_planned", "d_out_fault", "c2w", "c2s", "slope7z", "ws", "ws7"]
    n0 = len(d)
    d = d.dropna(subset=need).reset_index(drop=True)
    print(f"common sample {len(d)} of {n0} rows", flush=True)
    return d


def residualise(d):
    X = np.column_stack([d.hour, d.dow, d.date.dt.month, d.date.dt.dayofyear, d.d_temp, d.d_dem, d.d_lnL_7, d.d_lnL_14, d.d_lnL_28, d.d_p_7, d.d_p_14, d.d_p_28, d.gas])
    order = d.date.rank(method="dense").to_numpy()
    blocks = np.minimum((order / order.max() * 10).astype(int), 9)
    cands = {
        "C0": {"d_wind": d.d_wind, "d_solar": d.d_solar, "d_wind2": d.d_wind ** 2, "d_solar2": d.d_solar ** 2},
        "C1": {"d_pc": d.d_pc, "d_pc2": d.d_pc ** 2},
        "C2": {"c2w": d.c2w, "c2s": d.c2s},
        "C3": {"c3w": d.c2w * d.slope7z, "c3s": d.c2s * d.slope7z},
        "C4": {"d_planned": d.d_out_planned, "d_fault": d.d_out_fault},
    }
    cols = {"y": d.d_lnL, "p": d.d_p, "yplac": d.d_lnL_7, "ws_test": d.d_ws}
    for c, m in cands.items():
        for k, v in m.items():
            cols[f"{c}:{k}"] = v
    names = list(cols)
    Y = np.column_stack([np.asarray(cols[k], dtype=float) for k in names])
    R = N.gb_resid(Y, X, blocks, d.date.to_numpy())
    res = dict(zip(names, R.T))
    return cands, res


def t_slope(y, x, st):
    b = float(x @ y / (x @ x))
    u = y - b * x
    s = np.add.reduceat(x * u, st)
    se = float(np.sqrt((s ** 2).sum()) / (x @ x))
    return b, b / se


def main():
    d = build_frame()
    assert d.date.is_monotonic_increasing
    cands, res = residualise(d)
    print("residuals done", flush=True)
    rng = np.random.default_rng(SEED)
    srcs = E.perm_sources(d, rng, NPERM)
    hy = np.where(d.date < "2021-07-01", "2019-21H1", "2021H2-23")
    blocks = {"full": np.ones(len(d), bool), "2019-21H1": hy == "2019-21H1", "2021H2-23": hy == "2021H2-23"}
    rows = []
    for c, m in cands.items():
        Zf = np.column_stack([res[f"{c}:{k}"] for k in m])
        for bn, mask in blocks.items():
            for outcome, key in (("real_F_only", "y"), ("placebo", "yplac")):
                sub = E.Sub(d, res[key], res["p"], Zf, mask, list(range(Zf.shape[1])))
                sub.Zfull = Zf
                F = sub.first_stage_F(sub.Z0)
                if outcome == "real_F_only":
                    b0 = np.linalg.solve(sub.Z0.T @ sub.Z0, sub.Z0.T @ sub.p)
                    rows.append(dict(candidate=c, block=bn, F1=F, partial_R2=float(1 - np.var(sub.p - sub.Z0 @ b0) / np.var(sub.p)), n=len(sub.idx)))
                    continue
                beta, se = sub.fast(sub.Z0)
                tp = np.array([(lambda r: r[0] / r[1])(sub.fast(E.Z_full_perm(sub, s))) for s in srcs])
                p_t = (1 + np.sum(np.abs(tp) >= abs(beta / se))) / (NPERM + 1)
                rows[-1].update(placebo_slope=beta, placebo_p=p_t)
        print(c, "scored", flush=True)
    # F3: first stage of the wind component on idle-wind rows (both weeks below IDLE_WS)
    wind_cols = {"C0": ["d_wind"], "C1": ["d_pc"], "C2": ["c2w"], "C3": ["c2w"], "C4": None}
    idle = ((d.ws < IDLE_WS) & (d.ws7 < IDLE_WS)).to_numpy()
    f3 = []
    for c, cl in wind_cols.items():
        if cl is None:
            f3.append(dict(candidate=c, f3_rows=int(idle.sum()), f3_status="not applicable (no wind component)"))
            continue
        z = res[f"{c}:{cl[0]}"]
        idx = np.flatnonzero(idle)
        st = E.starts_of(d.date.to_numpy()[idx])
        b_i, t_i = t_slope(res["p"][idx], z[idx], st)
        b_f, t_f = t_slope(res["p"], z, E.starts_of(d.date.to_numpy()))
        tp = np.array([t_slope(res["p"][idx], z[s[idx]], st)[1] for s in srcs])
        p3 = (1 + np.sum(np.abs(tp) >= abs(t_i))) / (NPERM + 1)
        f3.append(dict(candidate=c, f3_rows=int(len(idx)), f3_coef_idle=b_i, f3_coef_full=b_f, f3_ratio=b_i / b_f, f3_p=p3, f3_status="tested" if len(idx) >= MIN_IDLE else "too few rows"))
    R = pd.DataFrame(rows)
    F3 = pd.DataFrame(f3)
    R.round(5).to_csv(T.OUT / "industry_iv_instrument_settlement.csv", index=False)
    # rules
    out = []
    for c in cands:
        r = R[R.candidate == c].set_index("block")
        s1 = bool(r.loc["full", "F1"] >= 20 and r.loc["2019-21H1", "F1"] >= 10 and r.loc["2021H2-23", "F1"] >= 10)
        s2 = bool(all(r.loc[b, "placebo_p"] > 0.10 for b in blocks))
        f = F3[F3.candidate == c].iloc[0]
        if f.f3_status.startswith("not applicable"):
            s3 = True
        else:
            s3 = bool(f.f3_status == "tested" and f.f3_p > 0.05 and abs(f.f3_ratio) <= 0.5)
        out.append(dict(candidate=c, S1=s1, S2=s2, S3=s3, S3_note=f.f3_status, passes=s1 and s2 and s3, minF=float(min(r.loc["2019-21H1", "F1"], r.loc["2021H2-23", "F1"]))))
    Q = pd.DataFrame(out)
    ok = Q[Q.passes]
    order = ["C1", "C0", "C2", "C3", "C4"]
    if len(ok):
        top = ok.minF.max()
        tied = ok[ok.minF >= 0.9 * top].candidate.tolist()
        chosen = [x for x in order if x in tied][0]
    else:
        chosen = "NONE (S5: instrument question closed)"
    Q["chosen"] = Q.candidate == chosen
    Q.to_csv(T.OUT / "industry_iv_instrument_settlement_rules.csv", index=False)
    F3.round(5).to_csv(T.OUT / "industry_iv_instrument_settlement_f3.csv", index=False)
    pd.set_option("display.width", 250)
    print(R.round(4).to_string(index=False))
    print(F3.round(4).to_string(index=False))
    print(Q.round(3).to_string(index=False))
    print("S4 chosen:", chosen)


if __name__ == "__main__":
    main()
