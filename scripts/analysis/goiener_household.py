"""G2 of docs/specs/2026-11-17-goiener-household-design.md (replication of the household elasticity), run after step zero.

    .venv/bin/python scripts/analysis/goiener_household.py

Same 3,000-household 2.0TD subsample, same period types (peak 10-14 and 18-22, off-peak 0-8), same per-household LASSO (paper specification, 10-fold one-SE) as goiener_noise.py, but trained on ALL the household's
pre-lockdown weekdays and used out of sample on the window 2021-06-01 -> 2021-09-15 (non-holiday weekdays). Pooled response = mean household (peak - off) error minus Portugal's (REN, same pipeline). Contrast
elasticity = response / dose contrast (pure 2.0TD, E 100.8-style window mean price, weekday peak minus off-peak). Randomization inference against the 26 season-matched placebo windows of goiener_step_zero_windows.csv:
eta_RI = eta_real - mean placebo eta, one-sided p = (1+#{placebo eta <= eta_real})/27, Fisher-style interval eta_real - [q97.5, q2.5] of the placebo etas. E0 (aggregate, Spanish regulated load) through the same
transformation (Madrid temperature) for comparison, with placebo windows from the same leave-year-out pipeline. Writes outputs/tables/goiener_g2.csv and data/goiener/daily/g2_household_window.parquet.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.preprocessing import PolynomialFeatures  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goiener_noise as G  # noqa: E402
import tou_cross_tariff as CT  # noqa: E402
import tou_did as T  # noqa: E402
import tou_lasso_paper as L  # noqa: E402
import tou_randomization_inference as RI  # noqa: E402

ROOT = T.ROOT
W0, W1 = pd.Timestamp("2021-06-01"), pd.Timestamp("2021-09-15")
PEAK = [10, 11, 12, 13, 18, 19, 20, 21]


def errors_window(y, temp):
    """y: log period-sum indexed by weekday dates (pre-lockdown and window). Train on pre-lockdown days, predict the window days."""
    y = y.dropna()
    tr = y.index < "2020-03-01"
    te = (y.index >= W0) & (y.index <= W1)
    if tr.sum() < 250 or te.sum() < 60:
        return pd.Series(dtype=float)
    P = G.design(temp, y.index)
    mu, sd = P[tr].mean(), P[tr].std()
    keep = sd > 0
    Z = ((P.loc[:, keep] - mu[keep]) / sd[keep]).to_numpy()
    m = L.fit_one_se(Z[tr], y.to_numpy()[tr])
    return pd.Series(y.to_numpy()[te] - m.predict(Z[te]), index=y.index[te])


def one_household_window(u, g, temp):
    g = g.set_index("date").sort_index()
    res = {per: errors_window(np.log(g[per].where(g[per] > 0)), temp) for per in ("kwh_peak", "kwh_off")}
    if any(len(v) == 0 for v in res.values()):
        return pd.DataFrame(columns=["user", "date", "peak", "off", "contrast"])
    e = pd.concat(res, axis=1).dropna()
    e.columns = ["peak", "off"]
    e["contrast"] = e.peak - e.off
    e["user"] = u
    e.index.name = "date"
    return e.reset_index()[["user", "date", "peak", "off", "contrast"]]


def series_window(pv, temp):
    """Aggregate series (columns kwh_peak, kwh_off indexed by date): window contrast errors by the all-pre pipeline."""
    g = pv.reset_index()
    return one_household_window("agg", g, temp)


def rank_stats(eta_real, eta_plc):
    eta_plc = np.asarray(eta_plc)
    p = (1 + np.sum(eta_plc <= eta_real)) / (1 + len(eta_plc))
    lo, hi = eta_real - np.quantile(eta_plc, 0.975), eta_real - np.quantile(eta_plc, 0.025)
    return dict(eta_real=eta_real, eta_RI=eta_real - eta_plc.mean(), mean_placebo=eta_plc.mean(), p_one_sided=p, fisher_lo=lo, fisher_hi=hi)


def main():
    daily = pd.read_parquet(ROOT / "data/goiener/daily/daily.parquet")
    meta = pd.read_parquet(ROOT / "data/goiener/daily/selected_metadata.parquet").set_index("user")
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    hpt = set(pd.to_datetime(hol[hol.area == "PT"].date))
    daily["date"] = pd.to_datetime(daily.date)
    wd = daily[(daily.date.dt.dayofweek < 5) & ~daily.date.isin(hes)].copy()
    pre = wd[wd.date < "2020-03-01"]
    win = wd[(wd.date >= W0) & (wd.date <= W1)]
    npre, nwin = pre.groupby("user").size(), win.groupby("user").size()
    imp = wd[wd.user.isin(win.user)].groupby("user").n_imputed.sum() / (24 * wd.groupby("user").size())
    g0 = (npre.reindex(meta.index).fillna(0) >= 250) & (nwin.reindex(meta.index).fillna(0) >= 60) & (imp.reindex(meta.index).fillna(1) <= 0.10)
    elig = meta.index[g0]
    temps = G.daily_temps()
    rng = np.random.default_rng(G.SEED)
    e20 = [u for u in elig if meta.loc[u, "contracted_tariff"] == "2.0TD"]
    sub = list(rng.choice(e20, size=min(G.NSUB, len(e20)), replace=False))
    both = wd[(wd.date < "2020-03-01") | ((wd.date >= W0) & (wd.date <= W1))]
    grp = {u: g for u, g in both[both.user.isin(sub)].groupby("user")}
    res = Parallel(n_jobs=4, verbose=0)(delayed(one_household_window)(u, grp[u], temps[G.CITY[meta.loc[u, "province"]]]) for u in sub if u in grp)
    E = pd.concat(res, ignore_index=True)
    E.to_parquet(ROOT / "data/goiener/daily/g2_household_window.parquet")
    print(f"window errors: {len(E)} household-days from {E.user.nunique()} households", flush=True)

    # Portugal and E0 through the same pipeline
    x = RI.D.prep(T.build("e0", end="2021-09-15"))

    def agg(load, holi):
        d = x[~x.date.isin(holi) & (x.date.dt.dayofweek < 5)].copy()
        d["per"] = np.where(d.hour.isin(PEAK), "kwh_peak", np.where(d.hour < 8, "kwh_off", "kwh_mid"))
        d = d[(d.date < "2020-03-01") | ((d.date >= W0) & (d.date <= W1))]
        cnt = d.groupby("date").size()
        pv = d.pivot_table(index="date", columns="per", values=load, aggfunc="sum")[["kwh_peak", "kwh_off"]]
        return pv[cnt.reindex(pv.index) == 24]

    pt_pv, es_pv = agg("load_pt", hpt), agg("load_es", hes)
    pt_c = series_window(pt_pv, temps["pt"]).set_index("date").contrast
    es_c = series_window(es_pv, temps["madrid"]).set_index("date").contrast
    pooled_real = E.contrast.mean() - pt_c.mean()
    e0_real = es_c.mean() - pt_c.mean()
    print(f"window pooled response households {pooled_real:+.4f} ({E.user.nunique()} households, {len(E)} household-days); E0 {e0_real:+.4f}; Portugal window mean {pt_c.mean():+.4f}", flush=True)

    # doses
    dates = list(pd.date_range(W0, W1))
    tabs = CT.old_new_tables(dates)
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= W0) & (eh.index.get_level_values(0) <= W1)].mean())
    dp = CT.dp_tariff(tabs["2.0"], ebar).reset_index()
    dp["date"] = pd.to_datetime(dp.date)
    dpw = dp[(dp.date.dt.dayofweek < 5) & ~dp.date.isin(hes)]
    dose20 = float(dpw[dpw.hour.isin(PEAK)].iloc[:, -1].mean() - dpw[dpw.hour < 8].iloc[:, -1].mean())
    sd0 = CT.series_dose("E0", tabs, ebar).reset_index()
    sd0.columns = ["date", "hour", "dp"]
    sd0["date"] = pd.to_datetime(sd0.date)
    sd0 = sd0[(sd0.date.dt.dayofweek < 5) & ~sd0.date.isin(hes)]
    doseE0 = float(sd0[sd0.hour.isin(PEAK)].dp.mean() - sd0[sd0.hour < 8].dp.mean())
    print(f"dose contrasts: pure 2.0TD {dose20:+.3f}, E0 mix {doseE0:+.3f} (mean window price {ebar:.1f})", flush=True)

    # placebo windows
    Wd = pd.read_csv(T.OUT / "goiener_step_zero_windows.csv")
    eta_plc_h = Wd.pooled.to_numpy() / dose20
    wins = [(k, a, b) for k, a, b in RI.windows() if a.year in (2018, 2019) and abs((a - pd.Timestamp(year=a.year, month=6, day=1)).days) <= 45]
    es_pl = G.one_household("E0", es_pv[es_pv.index < "2020-03-01"].reset_index(), temps["madrid"]).set_index("date").contrast
    pt_pl = G.one_household("PT", pt_pv[pt_pv.index < "2020-03-01"].reset_index(), temps["pt"]).set_index("date").contrast
    e0_pl = np.array([es_pl[(es_pl.index >= a) & (es_pl.index <= b)].mean() - pt_pl[(pt_pl.index >= a) & (pt_pl.index <= b)].mean() for k, a, b in wins])
    out = []
    hh = rank_stats(pooled_real / dose20, eta_plc_h)
    out.append(dict(series="GoiEner 2.0TD households", dose=dose20, response_real=pooled_real, **hh))
    e0 = rank_stats(e0_real / doseE0, e0_pl / doseE0)
    out.append(dict(series="E0 aggregate (mix dose)", dose=doseE0, response_real=e0_real, **e0))
    e0b = rank_stats(e0_real / dose20, e0_pl / dose20)
    out.append(dict(series="E0 aggregate (pure 2.0TD dose)", dose=dose20, response_real=e0_real, **e0b))
    R = pd.DataFrame(out)
    R.round(5).to_csv(T.OUT / "goiener_g2.csv", index=False)
    pd.set_option("display.width", 220)
    print(R.round(4).to_string(index=False))
    ok = bool(-0.20 <= hh["eta_RI"] <= -0.03 and hh["p_one_sided"] <= 0.05)
    print(f"G2: household eta_RI {hh['eta_RI']:+.4f} in [-0.20, -0.03] and p {hh['p_one_sided']:.3f} <= 0.05: {ok}; raw eta {hh['eta_real']:+.4f}; difference to E0 (mix dose) {hh['eta_RI'] - e0['eta_RI']:+.4f}", flush=True)


if __name__ == "__main__":
    main()
