"""Builds the forest samples (docs/specs/2026-11-17-causal-forest-design.md): real window and season-matched placebo windows, day-demeaned outcome and dose, covariates.

    .venv/bin/python scripts/analysis/tou_forest_prep.py

Writes data/cache_tou/forest/real.csv and placebo.csv (placebo has a window id `k`). Outcome y = Spain minus Portugal LASSO error (E0), dose w = Equation 4 dose of the paper's convention (window mean price, w = 0.69),
both demeaned within each complete 24-hour day. Sample days: 1 April -> 31 October (widened from 1 June so every season-matched placebo window lies inside the sample) of 2018, 2019, 2020 (COVID block removed) plus the real window 2021-06-01 -> 2021-09-15.
Missing values: the D-1 forecasts start in 2019, so 2018 rows carry NA in the three forecast covariates (grf handles NA in X).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_randomization_inference as RI  # noqa: E402

TSP = pd.Timestamp
R0, R1 = CT.POST0, CT.POST1
OUTD = T.ROOT / "data" / "cache_tou" / "forest"


def main():
    x = D.prep(T.build("e0", end="2021-09-15"))
    x = x.merge(CT.esios_load(CT.LOADS["E0"]).rename(columns={"v": "load_E0"}), on=["date", "hour"], how="left")
    errs = CT.get_errors(x)
    errs.update(RI.ri_errors(x))
    year = x.date.dt.year

    def cf(n):
        parts = [errs[(n, f"({y},)")][year.reindex(errs[(n, f"({y},)")].index) == y] for y in (2018, 2019, 2020)]
        return pd.concat(parts)

    y_cf = (cf("E0") - cf("PT")).reindex(x.index)
    y_real = (errs[("E0", "()")] - errs[("PT", "()")]).reindex(x.index)
    win_real = ((x.date >= R0) & (x.date <= R1)).to_numpy()
    x["y_cf"], x["y_real"] = y_cf, y_real.where(win_real, y_cf)

    # dose
    dates = sorted(set(pd.date_range("2018-04-01", "2020-10-31")) | set(pd.date_range(R0, R1)))
    tabs = CT.old_new_tables(dates)
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= R0) & (eh.index.get_level_values(0) <= R1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    x["dose"] = np.nan_to_num(CT.series_dose("E0", tabs, ebar).reindex(idx).to_numpy())

    # covariates
    x["price"] = eh.reindex(idx).to_numpy()
    dm = eh.groupby(level=0).mean()
    x["price_prev"] = x.date.map(lambda d: dm.get(d - pd.Timedelta(days=1), np.nan))
    for nm, i in (("f_wind", 1777), ("f_solar", 1779), ("f_demand", 1775)):
        f = CT.esios_load([i]).set_index(["date", "hour"]).v
        x[nm] = f.reindex(idx).to_numpy()
    g = x.groupby("date")
    x["tmean"], x["tmin"], x["tmax"] = g.temp_es.transform("mean"), g.temp_es.transform("min"), g.temp_es.transform("max")
    dmean = x.groupby("date").tmean.first()
    t3 = dmean.rolling(3, min_periods=1).mean()
    x["t3"] = x.date.map(t3)
    hot = (dmean.reindex(pd.date_range(dmean.index.min(), dmean.index.max())) * 0).fillna(0)
    tmaxd = x.groupby("date").tmax.first()
    hw = (tmaxd >= 35).astype(int).rolling(3, min_periods=3).sum().eq(3).astype(int)
    x["heatwave"] = x.date.map(hw).fillna(0)
    x["hdh"], x["cdh"] = np.maximum(18 - x.temp_es, 0), np.maximum(x.temp_es - 18, 0)
    nonwork = ((x.dow >= 5) | (x.hol_es == 1)).astype(int)
    nw = nonwork.groupby(x.date).first()
    prev_nw, next_nw = nw.shift(1), nw.shift(-1)
    bridge = ((nw == 0) & (prev_nw == 1) & (next_nw == 1)).astype(int)
    x["bridge"] = x.date.map(bridge).fillna(0)
    x["wkd"] = nonwork
    x["doy"] = x.date.dt.dayofyear
    x["period"] = np.where((nonwork == 1) | (x.hour < 8), 3, np.where(x.hour.isin([10, 11, 12, 13, 18, 19, 20, 21]), 1, 2))

    covid = x.date.between(*EV.COVID)
    summer = x.date.dt.month.between(4, 10)
    base = summer & (x.date.dt.year <= 2020) & ~covid
    full = x.groupby("date").hour.transform("count") == 24

    def build(ycol, mask_days, dose_fn, k=None, start=None):
        d = x[mask_days & full].copy()
        d["w"] = dose_fn(d)
        d = d.dropna(subset=[ycol]).copy()
        d = d[d.groupby("date").hour.transform("count") == 24]
        d["y_dm"] = d[ycol] - d.groupby("date")[ycol].transform("mean")
        d["w_dm"] = d.w - d.groupby("date").w.transform("mean")
        d["in_window"] = (d.w != 0).astype(int)
        d["days_since"] = np.where(d.in_window == 1, (d.date - start).dt.days, 0)
        d["week"] = d.date.dt.strftime("%G-%V")
        if k is not None:
            d["k"] = k
        return d

    cols = ["date", "hour", "y_dm", "w_dm", "in_window", "week", "wkd", "doy", "tmean", "tmin", "tmax", "temp_es", "t3", "hdh", "cdh", "heatwave", "price", "price_prev", "f_wind", "f_solar", "f_demand", "dose",
            "period", "days_since", "bridge", "month"]
    real = build("y_real", base | ((x.date >= R0) & (x.date <= R1)), lambda d: np.where((d.date >= R0) & (d.date <= R1), d.dose, 0.0), start=R0)
    real = real.assign(month=real.date.dt.month)[cols]
    real.to_csv(OUTD / "real.csv", index=False)
    print(f"real: {len(real)} rows, {real.date.nunique()} days, window days {real[real.in_window == 1].date.nunique()} ({100 * (real.in_window == 1).mean():.1f}% of rows)", flush=True)

    sm = []
    for k, a, b in RI.windows():
        s = a
        if s.year in (2018, 2019) and abs((s - TSP(year=s.year, month=6, day=1)).days) <= 45:
            sm.append((k, a, b))
    parts = []
    for k, a, b in sm:
        inw = (x.date >= a) & (x.date <= b)
        d = build("y_cf", base, lambda d, a=a, b=b: np.where((d.date >= a) & (d.date <= b), d.dose, 0.0), k=k, start=a)
        parts.append(d.assign(month=d.date.dt.month)[cols + ["k"]])
    pl = pd.concat(parts)
    pl.to_csv(OUTD / "placebo.csv", index=False)
    print(f"placebo: {len(sm)} windows, {len(pl)} rows; windows with no dose rows: {sum(1 for k in pl.k.unique() if pl[pl.k == k].in_window.sum() == 0)}", flush=True)


if __name__ == "__main__":
    main()
