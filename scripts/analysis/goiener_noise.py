"""Step zero (G0, G1) of docs/specs/2026-11-17-goiener-household-design.md. No window (2021) response is computed or printed.

    .venv/bin/python scripts/analysis/goiener_noise.py

G0: households with >= 250 complete weekdays before 2020-03-01, >= 60 complete weekdays in 2021-06-01 -> 2021-09-15 and at most 10% imputed hours on those days; median imputed share.
G1: per household and period type (peak, off-peak), a LASSO of the log daily kWh on month dummies, mean/min/max temperature and their squares and products (paper-style, one-SE) trained on the
household's weekdays of the other pre-lockdown days and used out of sample on the weekdays of 2018 and 2019 (leave-year-out); Portugal (REN, same pipeline) as control; pooled response of a placebo
window = mean over households and window weekdays of (peak - off error) minus the Portuguese one; sd across the 26 season-matched placebo windows; detectable contrast elasticity = 2.8 sd / dose
contrast (weekday peak minus off-peak log price change of the pure 2.0 tariff, paper convention). Deviation clarified before the run: the sample rule for placebo years is >= 60 weekdays in April-October
of the placebo year and >= 150 weekdays outside that year; G1 is computed on a random subsample of 3,000 eligible households (conservative: it overstates idiosyncratic noise).
Writes outputs/tables/goiener_step_zero.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.preprocessing import PolynomialFeatures

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_did as T  # noqa: E402
import tou_lasso_paper as L  # noqa: E402
import tou_randomization_inference as RI  # noqa: E402

ROOT = T.ROOT
SEED, NSUB = 20261117, 3000
CITY = {"Gipuzkoa": "bilbao", "Bizkaia": "bilbao", "Araba/Alava": "bilbao", "Navarra": "pamplona", "Madrid": "madrid"}


def daily_temps():
    t = pd.read_parquet(ROOT / "data/weather/temperature_population_hourly.parquet", columns=["city", "country", "utc_timestamp", "temperature_2m"])
    out = {}
    for city in ("bilbao", "pamplona", "madrid"):
        s = t[t.city == city].set_index("utc_timestamp").temperature_2m
        loc = s.index.tz_convert("Europe/Madrid")
        d = pd.DataFrame({"date": pd.to_datetime(loc.date), "t": s.to_numpy()}).groupby("date").t.agg(tmean="mean", tmin="min", tmax="max")
        out[city] = d
    pt = t[t.country == "PT"].groupby("utc_timestamp").temperature_2m.mean()
    loc = pt.index.tz_convert("Europe/Lisbon")
    out["pt"] = pd.DataFrame({"date": pd.to_datetime(loc.date), "t": pt.to_numpy()}).groupby("date").t.agg(tmean="mean", tmin="min", tmax="max")
    return out


def design(temp, dates):
    d = temp.reindex(dates)
    B = pd.concat([pd.get_dummies(pd.Series(dates.month, index=dates).astype(str), prefix="m", dtype=float), d], axis=1)
    P = pd.DataFrame(PolynomialFeatures(2, include_bias=False).fit_transform(B.to_numpy()), index=dates)
    return P.loc[:, ~P.T.duplicated().to_numpy()]


def errors_leave_year(y, temp, years=(2018, 2019)):
    """y: Series of log daily kWh indexed by weekday date (pre-lockdown). Returns Series of out-of-sample errors for the days of each placebo year (Apr-Oct)."""
    out = []
    if len(y) < 210:
        return pd.Series(dtype=float)
    P = design(temp, y.index)
    for yr in years:
        te = (y.index.year == yr) & (y.index.month >= 4) & (y.index.month <= 10)
        tr = y.index.year != yr
        if te.sum() < 60 or tr.sum() < 150:
            continue
        mu, sd = P[tr].mean(), P[tr].std()
        keep = sd > 0
        Z = ((P.loc[:, keep] - mu[keep]) / sd[keep]).to_numpy()
        m = L.fit_one_se(Z[tr], y.to_numpy()[tr])
        out.append(pd.Series(y.to_numpy()[te] - m.predict(Z[te]), index=y.index[te]))
    return pd.concat(out) if out else pd.Series(dtype=float)


def one_household(u, g, temp):
    g = g.set_index("date").sort_index()
    res = {}
    for per in ("kwh_peak", "kwh_off"):
        y = np.log(g[per].where(g[per] > 0))
        y = y.dropna()
        res[per] = errors_leave_year(y, temp)
    if any(len(v) == 0 for v in res.values()):
        return pd.DataFrame(columns=["user", "date", "contrast"])
    e = pd.concat(res, axis=1).dropna()
    e["contrast"] = e.kwh_peak - e.kwh_off
    e["user"] = u
    e.index.name = "date"
    return e.reset_index()[["user", "date", "contrast"]]


def main():
    daily = pd.read_parquet(ROOT / "data/goiener/daily/daily.parquet")
    meta = pd.read_parquet(ROOT / "data/goiener/daily/selected_metadata.parquet").set_index("user")
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    hpt = set(pd.to_datetime(hol[hol.area == "PT"].date))
    daily["date"] = pd.to_datetime(daily.date)
    wd = daily[(daily.date.dt.dayofweek < 5) & ~daily.date.isin(hes)].copy()
    pre = wd[wd.date < "2020-03-01"]
    win = wd[(wd.date >= "2021-06-01") & (wd.date <= "2021-09-15")]
    npre, nwin = pre.groupby("user").size(), win.groupby("user").size()
    imp = (wd[wd.user.isin(win.user)].groupby("user").n_imputed.sum() / (24 * wd.groupby("user").size()))
    g0 = (npre.reindex(meta.index).fillna(0) >= 250) & (nwin.reindex(meta.index).fillna(0) >= 60) & (imp.reindex(meta.index).fillna(1) <= 0.10)
    elig = meta.index[g0]
    print(f"G0 selected {len(meta)}; usable {len(elig)} (>= 8,000: {len(elig) >= 8000}); median imputed share {imp.reindex(elig).median():.3f} (<= 0.10: {bool(imp.reindex(elig).median() <= 0.10)})", flush=True)
    print("  usable by tariff:", meta.loc[elig].contracted_tariff.value_counts().to_dict(), flush=True)

    temps = daily_temps()
    rng = np.random.default_rng(SEED)
    e20 = [u for u in elig if meta.loc[u, "contracted_tariff"] == "2.0TD"]
    sub = list(rng.choice(e20, size=min(NSUB, len(e20)), replace=False))
    pre_g = {u: g for u, g in pre[pre.user.isin(sub)].groupby("user")}
    res = Parallel(n_jobs=4, verbose=0)(delayed(one_household)(u, pre_g[u], temps[CITY[meta.loc[u, "province"]]]) for u in sub if u in pre_g)
    E = pd.concat(res, ignore_index=True)
    print(f"G1 household errors: {len(E)} household-days from {E.user.nunique()} households", flush=True)

    # Portugal (REN) through the same pipeline
    x = RI.D.prep(T.build("e0", end="2021-09-15"))
    ptd = x[~x.date.isin(hpt) & (x.date.dt.dayofweek < 5) & (x.date < "2020-03-01")].copy()
    ptd["per"] = np.where(ptd.hour.isin([10, 11, 12, 13, 18, 19, 20, 21]), "kwh_peak", np.where(ptd.hour < 8, "kwh_off", "kwh_mid"))
    cnt = ptd.groupby("date").size()
    pv = ptd.pivot_table(index="date", columns="per", values="load_pt", aggfunc="sum")[["kwh_peak", "kwh_off"]]
    pv = pv[cnt.reindex(pv.index) == 24]
    ptr = one_household("PT", pv.reset_index(), temps["pt"])
    pt_c = ptr.set_index("date").contrast

    # placebo windows
    W = [(k, a, b) for k, a, b in RI.windows() if a.year in (2018, 2019) and abs((a - pd.Timestamp(year=a.year, month=6, day=1)).days) <= 45]
    rows = []
    for k, a, b in W:
        e = E[(E.date >= a) & (E.date <= b)]
        p = pt_c[(pt_c.index >= a) & (pt_c.index <= b)]
        rows.append(dict(k=k, start=a.date(), n_obs=len(e), households=e.user.nunique(), pooled=e.contrast.mean() - p.mean()))
    R = pd.DataFrame(rows)
    sd = float(R.pooled.std(ddof=1))
    dates = list(pd.date_range("2021-06-01", "2021-09-15"))
    tabs = CT.old_new_tables(dates)
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= "2021-06-01") & (eh.index.get_level_values(0) <= "2021-09-15")].mean())
    dp = CT.dp_tariff(tabs["2.0"], ebar).reset_index()
    dp["date"] = pd.to_datetime(dp.date)
    dpw = dp[(dp.date.dt.dayofweek < 5) & ~dp.date.isin(hes)]
    dose = float(dpw[dpw.hour.isin([10, 11, 12, 13, 18, 19, 20, 21])].iloc[:, -1].mean() - dpw[dpw.hour < 8].iloc[:, -1].mean())
    det = 2.8 * sd / abs(dose)
    print(R.round(4).to_string(index=False))
    print(f"G1 placebo sd of the pooled response {sd:.4f} over {len(R)} windows; weekday peak-minus-off dose (2.0, E {ebar:.1f}) {dose:+.3f}; detectable contrast elasticity {det:.3f} (<= 0.05: {det <= 0.05})", flush=True)
    pd.DataFrame([dict(usable=len(elig), median_imputed=float(imp.reindex(elig).median()), subsample=len(sub), windows=len(R), placebo_sd=sd, dose_contrast=dose, detectable_elasticity=det)]).round(5).to_csv(T.OUT / "goiener_step_zero.csv", index=False)
    R.round(5).to_csv(T.OUT / "goiener_step_zero_windows.csv", index=False)


if __name__ == "__main__":
    main()
