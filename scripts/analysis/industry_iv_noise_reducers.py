"""Step zero of docs/specs/2026-11-17-industry-iv-noise-reducers-design.md (rules I1-I4). No slope is printed: first-stage F, standard error, detectable elasticity and a size check only.

    .venv/bin/python scripts/analysis/industry_iv_noise_reducers.py

Hourly ln load of ESIOS 1204-1207 on the OMIE day-ahead price, instruments D-1 wind and solar forecasts and their squares, non-holiday weekdays 2019-01-01 -> 2023-12-31 without 2020-03-01 -> 2020-06-30.
V0 baseline (year-month, hour-by-weekday effects, temperature terms); V1 same-hour-last-week difference; V2 double ML (HistGradientBoostingRegressor, time-blocked cross-fitting, 10 blocks, 14 days
removed on each side) with predictors incl. load and price 7/14/28 days earlier; V3 V1's differenced variables residualised as V2. Standard errors clustered by date.
Size check I3 (variants passing I1 and I2): 200 permutations of the residualised instruments across dates within year-month. Writes outputs/tables/industry_iv_noise_reducers.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_did as T  # noqa: E402

ROOT = T.ROOT
SEED = 20261117
H = 168  # hours in a week


def hourly(i):
    s = pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet")[["utc_timestamp", "value"]].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value
    loc = s.index.tz_convert("Europe/Madrid")
    return pd.DataFrame({"date": pd.to_datetime(loc.date), "hour": loc.hour, "v": s.to_numpy()}).drop_duplicates(["date", "hour"]).set_index(["date", "hour"]).v


def build():
    grid = pd.MultiIndex.from_product([pd.date_range("2018-10-01", "2023-12-31"), range(24)], names=["date", "hour"])
    df = pd.DataFrame(index=grid)
    df["load"] = sum(hourly(i) for i in (1204, 1205, 1206, 1207)).reindex(grid)
    df["wind"] = hourly(1777).reindex(grid) / 1000
    df["solar"] = hourly(1779).reindex(grid) / 1000
    df["dem"] = hourly(1775).reindex(grid) / 1000
    df["p"] = CT.omie_hourly().reindex(grid)
    t = pd.read_parquet(ROOT / "data/weather/temperature_population_hourly.parquet", columns=["country", "utc_timestamp", "temperature_2m"])
    te = t[t.country == "ES"].groupby("utc_timestamp").temperature_2m.mean()
    loc = te.index.tz_convert("Europe/Madrid")
    tt = pd.DataFrame({"date": pd.to_datetime(loc.date), "hour": loc.hour, "t": te.to_numpy()}).drop_duplicates(["date", "hour"]).set_index(["date", "hour"]).t
    df["temp"] = tt.reindex(grid)
    mg = pd.read_parquet(ROOT / "data/mibgas/mibgas_price_index_daily.parquet")
    mg["date"] = pd.to_datetime(mg.date)
    gm = mg.set_index("date").mibgas_es_eur_mwh.resample("MS").mean()
    dts = grid.get_level_values(0)
    df["gas"] = gm.reindex(dts.to_period("M").to_timestamp()).to_numpy()
    df = df.reset_index()
    df["lnL"] = np.log(df.load.where(df.load > 0))
    return df


def iv(y, p, Z, g):
    """2SLS of y on p with instruments Z (all already residualised); returns beta, se(beta), first-stage F (clustered)."""
    ug, inv = np.unique(g, return_inverse=True)

    def cl(M):
        out = np.zeros((len(ug), M.shape[1]))
        np.add.at(out, inv, M)
        return out
    b, *_ = np.linalg.lstsq(Z, p, rcond=None)
    e = p - Z @ b
    A = np.linalg.inv(Z.T @ Z)
    sc = cl(Z * e[:, None])
    V = A @ (sc.T @ sc) @ A
    F = float(b @ np.linalg.inv(V) @ b / Z.shape[1])
    fit = Z @ b
    beta = float(fit @ y / (fit @ p))
    u = y - beta * p
    se = float(np.sqrt((cl(fit * u[:, None]) ** 2).sum()) / abs(fit @ p))
    return beta, se, F


def ols_resid(v, X):
    b, *_ = np.linalg.lstsq(X, v, rcond=None)
    return v - X @ b


def fe_matrix(d, hour_dow):
    ym = pd.get_dummies(d.date.dt.strftime("%Y-%m"), dtype=float).to_numpy()
    hd = pd.get_dummies((d.hour * 10 + d.date.dt.dayofweek) if hour_dow else d.hour, dtype=float).to_numpy()
    return ym, hd


def gb_resid(Y, X, blocks, dates):
    """Cross-fitted residuals of each column of Y on X; blocks: block id per row; 14 days removed on either side of the held-out block."""
    R = np.zeros_like(Y)
    for k in np.unique(blocks):
        te = blocks == k
        d0, d1 = dates[te].min() - pd.Timedelta(days=14), dates[te].max() + pd.Timedelta(days=14)
        tr = ~((dates >= d0) & (dates <= d1))
        for j in range(Y.shape[1]):
            m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=50, l2_regularization=1.0, early_stopping=False, random_state=SEED)
            m.fit(X[tr], Y[tr, j])
            R[te, j] = Y[te, j] - m.predict(X[te])
    return R


def main():
    df = build()
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    for s in ("lnL", "wind", "solar", "dem", "p", "temp"):
        for k, nm in ((7, "7"), (14, "14"), (21, "21"), (28, "28")):
            df[f"{s}_{nm}"] = df[s].shift(k * 24)
    df["dow"] = df.date.dt.dayofweek
    covid = df.date.between("2020-03-01", "2020-06-30")
    base = (df.date >= "2019-01-01") & (df.dow < 5) & ~df.date.isin(hes) & ~covid
    partner_ok = ~(df.date - pd.Timedelta(days=7)).isin(hes) & ~(df.date - pd.Timedelta(days=7)).between("2020-03-01", "2020-06-30")
    pbar = float(df.loc[base, "p"].mean())
    rng = np.random.default_rng(SEED)
    rows = []

    def Zmat(w, s):
        return np.column_stack([w, s, w ** 2, s ** 2])

    # ---- V0 baseline
    d = df[base].dropna(subset=["lnL", "wind", "solar", "p", "temp"]).reset_index(drop=True)
    ym, hd = fe_matrix(d, True)
    X0 = np.column_stack([ym, hd[:, 1:], d.temp, np.maximum(18 - d.temp, 0), np.maximum(d.temp - 22, 0)])
    sets = {"V0 baseline": dict(d=d, y=ols_resid(np.log(d.load), X0), p=ols_resid(d.p.to_numpy(), X0), Z=np.column_stack([ols_resid(c, X0) for c in Zmat(d.wind.to_numpy() / 1, d.solar.to_numpy()).T]))}

    # ---- V1 week-on-week difference
    cols1 = ["lnL", "wind", "solar", "p", "temp"]
    d1 = df[base & partner_ok].copy()
    for c in cols1:
        d1[f"d_{c}"] = d1[c] - df[c].shift(H).loc[d1.index]
    d1 = d1.dropna(subset=[f"d_{c}" for c in cols1]).reset_index(drop=True)
    ym1, hd1 = fe_matrix(d1, False)
    X1 = np.column_stack([ym1, hd1[:, 1:], d1.d_temp, d1.d_temp ** 2])
    sets["V1 week-on-week difference"] = dict(d=d1, y=ols_resid(d1.d_lnL.to_numpy(), X1), p=ols_resid(d1.d_p.to_numpy(), X1),
                                              Z=np.column_stack([ols_resid(c, X1) for c in Zmat(d1.d_wind.to_numpy(), d1.d_solar.to_numpy()).T]))

    # ---- V2 double ML with gradient boosting
    d2 = df[base].dropna(subset=["lnL", "wind", "solar", "p", "temp", "dem", "lnL_7", "lnL_14", "lnL_28", "p_7", "p_14", "p_28", "gas"]).reset_index(drop=True)
    tmean = d2.groupby("date").temp.transform("mean")
    tmin, tmax = d2.groupby("date").temp.transform("min"), d2.groupby("date").temp.transform("max")
    X2 = np.column_stack([d2.hour, d2.dow, d2.date.dt.month, d2.date.dt.dayofyear, d2.temp, tmean, tmin, tmax, d2.dem, d2.lnL_7, d2.lnL_14, d2.lnL_28, d2.p_7, d2.p_14, d2.p_28, d2.gas])
    order = d2.date.rank(method="dense").to_numpy()
    blocks2 = np.minimum((order / order.max() * 10).astype(int), 9)
    Y2 = np.column_stack([d2.lnL, d2.p, d2.wind, d2.solar, d2.wind ** 2, d2.solar ** 2])
    R2 = gb_resid(Y2, X2, blocks2, d2.date.to_numpy())
    sets["V2 double ML (boosting)"] = dict(d=d2, y=R2[:, 0], p=R2[:, 1], Z=R2[:, 2:])
    print("V2 residuals done", flush=True)

    # ---- V3 both
    d3 = df[base & partner_ok].copy()
    for c in ("lnL", "wind", "solar", "p", "temp", "dem"):
        d3[f"d_{c}"] = d3[c] - df[c].shift(H).loc[d3.index]
    for s in ("lnL", "p"):
        d3[f"d_{s}_7"] = df[f"{s}_7"].loc[d3.index] - df[f"{s}_14"].loc[d3.index]
        d3[f"d_{s}_14"] = df[f"{s}_14"].loc[d3.index] - df[f"{s}_21"].loc[d3.index]
        d3[f"d_{s}_28"] = df[f"{s}_28"].loc[d3.index] - df[s].shift(35 * 24).loc[d3.index]
    d3["gas"] = df["gas"].loc[d3.index]
    need = ["d_lnL", "d_wind", "d_solar", "d_p", "d_temp", "d_dem", "d_lnL_7", "d_lnL_14", "d_lnL_28", "d_p_7", "d_p_14", "d_p_28", "gas"]
    d3 = d3.dropna(subset=need).reset_index(drop=True)
    X3 = np.column_stack([d3.hour, d3.dow, d3.date.dt.month, d3.date.dt.dayofyear, d3.d_temp, d3.d_dem, d3.d_lnL_7, d3.d_lnL_14, d3.d_lnL_28, d3.d_p_7, d3.d_p_14, d3.d_p_28, d3.gas])
    order3 = d3.date.rank(method="dense").to_numpy()
    blocks3 = np.minimum((order3 / order3.max() * 10).astype(int), 9)
    Y3 = np.column_stack([d3.d_lnL, d3.d_p, d3.d_wind, d3.d_solar, d3.d_wind ** 2, d3.d_solar ** 2])
    R3 = gb_resid(Y3, X3, blocks3, d3.date.to_numpy())
    sets["V3 difference + double ML"] = dict(d=d3, y=R3[:, 0], p=R3[:, 1], Z=R3[:, 2:])
    print("V3 residuals done", flush=True)

    for name, s in sets.items():
        g = s["d"].date.to_numpy()
        beta, se, F = iv(s["y"], s["p"], s["Z"], g)
        se_el = se * pbar
        det = 2.8 * se_el
        row = dict(variant=name, n=len(s["y"]), days=len(np.unique(g)), first_stage_F=F, se_elasticity=se_el, detectable_elasticity=det, I1=F >= 10, I2=det <= 0.25, share_perm_gt2=np.nan, I3=np.nan)
        if row["I1"] and row["I2"]:
            ym_id = s["d"].date.dt.strftime("%Y-%m").to_numpy()
            ud, first = np.unique(g, return_index=True)
            day_ym = ym_id[first]
            idx_by_day = {dd: np.where(g == dd)[0] for dd in ud}
            cnt = 0
            for _ in range(200):
                perm_day = {}
                for m in np.unique(day_ym):
                    days = ud[day_ym == m]
                    sh = rng.permutation(days)
                    perm_day.update(dict(zip(days, sh)))
                Zp = s["Z"].copy()
                for dd in ud:  # take the instrument residuals of another day of the same month, hour by hour
                    src, dst = idx_by_day[perm_day[dd]], idx_by_day[dd]
                    h_src, h_dst = s["d"].hour.to_numpy()[src], s["d"].hour.to_numpy()[dst]
                    m_ = {h: i for h, i in zip(h_src, src)}
                    for h, i in zip(h_dst, dst):
                        if h in m_:
                            Zp[i] = s["Z"][m_[h]]
                bp, sp_, _ = iv(s["y"], s["p"], Zp, g)
                if abs(bp / sp_) > 2:
                    cnt += 1
            row["share_perm_gt2"] = cnt / 200
            row["I3"] = cnt / 200 <= 0.10
        rows.append(row)
        print({k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in row.items()}, flush=True)
    R = pd.DataFrame(rows)
    R.round(5).to_csv(T.OUT / "industry_iv_noise_reducers.csv", index=False)
    ok = R[(R.I1) & (R.I2) & (R.I3 == True)]  # noqa: E712
    print("\nI4:", "variants passing I1-I3:", ok.variant.tolist(), "| primary (smallest SE):", ok.sort_values("se_elasticity").variant.iloc[0] if len(ok) else "none -> close the industrial IV")
    print(R[["variant", "n", "first_stage_F", "se_elasticity", "detectable_elasticity", "I1", "I2", "share_perm_gt2", "I3"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
