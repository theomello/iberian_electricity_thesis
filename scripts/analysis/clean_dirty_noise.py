"""Step zero of the clean-dirty CES (docs/specs/2026-11-16-clean-dirty-ces-design.md): checks C1-C4. No slope is printed, only variation, shares, first stages and standard errors.

    .venv/bin/python scripts/analysis/clean_dirty_noise.py

Daily: Q_C = REE realtime hydro (not pumped), Q_D = coal + combined cycle, R = demand - wind - solar - nuclear - cogeneration; P_D = capacity-weighted bid-time cost of the available gas and coal units
(step cache `cost`, not withdrawn); P_C = mean 30-day water value of non-pumped hydro (hydro_cost_daily). Instruments for ln P_C: 90-day trailing national rainfall anomaly (mean of the Spanish basins)
and national reservoir fill lagged 30 days (MITECO, hydro-flagged). Month effects in every step. Writes outputs/tables/clean_dirty_noise.csv.
Deviation from the spec text: C4 uses the equation's own controls (month effects, spline in ln R) instead of the LASSO residual; C4 = 2.8 x the week-clustered IV standard error of the slope (never the slope itself).
"""
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_did as T  # noqa: E402

ROOT = T.ROOT
WINDOWS = {"pre-cap": ("2019-01-01", "2022-06-14"), "post-cap": ("2022-06-15", "2023-12-31")}
LOCK = ("2020-03-01", "2020-06-30")


def realtime():
    r = pd.read_parquet(ROOT / "data/ree/ree_realtime_5min.parquet")
    r["date"] = pd.to_datetime(r.local_date)
    cols = ["demand", "wind", "nuclear", "coal", "combined_cycle", "hydro", "solar_total", "cogeneration_other"]
    n = r.groupby("date").ts.count()
    d = r.groupby("date")[cols].mean() * 24
    d = d[n.reindex(d.index) >= 276]
    d["R"] = d.demand - d.wind - d.solar_total - d.nuclear - d.cogeneration_other
    d["QC"], d["QD"] = d.hydro, d.coal + d.combined_cycle
    return d


def thermal_cost():
    out = []
    for f in sorted(glob.glob(str(ROOT / "outputs/cache/step/units_20*.parquet"))):
        ym = Path(f).stem.split("_")[1]
        if ym < "201901" or ym > "202312":
            continue
        u = pd.read_parquet(f, columns=["hid", "fuel", "cap_mw", "cost", "withdrawn"])
        u = u[u.fuel.isin(["gas", "coal"]) & ~u.withdrawn & (u.cap_mw > 0) & u.cost.notna()]
        h = pd.read_parquet(Path(f).with_name(f"hours_{ym}.parquet"), columns=["hid", "date", "valid"])
        h = h[h.valid]
        u = u.merge(h[["hid", "date"]], on="hid")
        u["w"] = u.cap_mw
        u["cw"] = u.cost * u.cap_mw
        g = u.groupby("date")[["w", "cw"]].sum()
        out.append(g.cw / g.w)
    s = pd.concat(out)
    s.index = pd.to_datetime(s.index)
    return s.rename("PD")


def hydro_cost():
    h = pd.read_parquet(ROOT / "outputs/tables/hydro_cost_daily.parquet")
    h = h[~h.pumped & h.cost_eur_mwh.notna() & (h.cost_eur_mwh > 0)]
    return h.groupby("date").cost_eur_mwh.mean().rename("PC")


def instruments():
    p = pd.read_parquet(ROOT / "data/weather/precipitation_basins_daily.parquet")
    p = p[~p.basin.str.startswith("pt_")].groupby("date").precipitation_sum.mean()
    p = p.sort_index().asfreq("D")
    tr = p.rolling(90, min_periods=60).sum()
    doy = tr.index.dayofyear
    clim = tr.groupby(doy).transform("mean")
    rain = (tr - clim).rename("rain90")
    e = pd.read_parquet(ROOT / "data/miteco/embalses_historico.parquet")
    e = e[e.hydro_flag]
    w = e.groupby("date")[["stored_hm3", "capacity_hm3"]].sum()
    fill = (w.stored_hm3 / w.capacity_hm3)
    fill = fill.asfreq("D").interpolate(limit=10).shift(30).rename("fill30")
    return pd.concat([rain, fill], axis=1)


def ols_resid(y, X):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ b


def run(df, name, rows):
    a, b = WINDOWS[name]
    d = df[(df.index >= a) & (df.index <= b) & ~((df.index >= LOCK[0]) & (df.index <= LOCK[1]))].dropna(subset=["QC", "QD", "R", "PC", "PD", "rain90", "fill30"]).copy()
    d = d[(d.QC > 0) & (d.QD > 0) & (d.R > 0)]
    d["lp"], d["lr"] = np.log(d.PC / d.PD), np.log(d.QC / d.QD)
    M = pd.get_dummies(d.index.month, dtype=float).to_numpy()
    lnR = np.log(d.R.to_numpy())
    S = np.column_stack([lnR, lnR ** 2])
    X = np.column_stack([M, S])
    c1 = float(ols_resid(d.lp.to_numpy(), M).std(ddof=1))
    c2 = float(((d.QC / d.R >= 0.05) & (d.QD / d.R >= 0.05)).mean())
    lp_r = ols_resid(d.lp.to_numpy(), X)
    Z = np.column_stack([ols_resid(d.rain90.to_numpy(), X), ols_resid(d.fill30.to_numpy(), X)])
    wk = d.index.to_period("W").astype(str).to_numpy()
    # first stage F (week-clustered Wald on the two instruments, controls partialled)
    b, *_ = np.linalg.lstsq(Z, lp_r, rcond=None)
    e = lp_r - Z @ b
    A = np.linalg.inv(Z.T @ Z)
    meat = sum(np.outer(Z[wk == g].T @ e[wk == g], Z[wk == g].T @ e[wk == g]) for g in np.unique(wk))
    V = A @ meat @ A
    F = float(b @ np.linalg.inv(V) @ b / 2)
    # IV standard error of the slope of ln(QC/QD) on ln(PC/PD) (slope never printed)
    y = ols_resid(d.lr.to_numpy(), X)
    fit = Z @ b
    beta = float(fit @ y / (fit @ lp_r))
    u = y - beta * lp_r
    sc = {g: float(fit[wk == g] @ u[wk == g]) for g in np.unique(wk)}
    se = float(np.sqrt(sum(v ** 2 for v in sc.values())) / abs(fit @ lp_r))
    rows.append(dict(window=name, days=len(d), C1_sd_lnPCoverPD=c1, C2_share_days_both_ge5pct=c2, C3_first_stage_F=F, C4_se_slope=se, C4_detectable_sigma=2.8 * se,
                     mean_hydro_share=float((d.QC / d.R).mean()), mean_thermal_share=float((d.QD / d.R).mean())))
    print(rows[-1], flush=True)


def main():
    df = realtime().join(thermal_cost(), how="left").join(hydro_cost(), how="left").join(instruments(), how="left")
    rows = []
    for name in WINDOWS:
        run(df, name, rows)
    R = pd.DataFrame(rows)
    R["C1"] = R.C1_sd_lnPCoverPD >= 0.15
    R["C2"] = R.C2_share_days_both_ge5pct >= 0.70
    R["C3"] = R.C3_first_stage_F >= 10
    R["C4"] = R.C4_detectable_sigma <= 1.5
    R.round(4).to_csv(T.OUT / "clean_dirty_noise.csv", index=False)
    print(R.round(4).T.to_string())


if __name__ == "__main__":
    main()
