"""Noise check for the PVPC reform of 1 Jan 2024 (RD 446/2023: energy term 75% day-ahead / 25% futures basket; 100% day-ahead before). Pre-2024 data only.

    .venv/bin/python scripts/analysis/pvpc_noise.py

Outcome: daily ln(load 19-22h / load 11-15h) of ESIOS 352 (PVPC retailers' scheduled demand) minus the same for 351 (free-market retailers), residual of the tou_ces.taste_pred LASSO trained on 2018-2020
pre-COVID days (leave-year-out inside 2018-2020, out of sample in 2021-2023, which is what the 2024 post window is). Same-weather contrast, Spain only. Noise = sd of window means of the residual
(125 and 250 weekdays); dose = evening-minus-midday change in the log PVPC energy price if 25% of the energy term is a flat futures price F (sensitivity), on 2024 day-ahead prices, with a flat
non-energy component A. Detectable effect = 2.8 x sd; detectable sigma = detectable effect / dose. Writes outputs/tables/pvpc_noise.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_ces as C  # noqa: E402
import tou_cross_tariff as CT  # noqa: E402
import tou_did as T  # noqa: E402

EVE, MID = [19, 20, 21, 22], [11, 12, 13, 14, 15]


def main():
    x = C.D.prep(T.build("e0", end="2021-09-14"))
    g = x.groupby("date")
    d = pd.DataFrame(index=sorted(x.date.unique()))
    d.index.name = "date"
    d["tmean_es"], d["tmin_es"], d["tmax_es"] = g.temp_es.mean(), g.temp_es.min(), g.temp_es.max()
    d = d.reset_index()
    # extend temperature beyond 2021-09 from the same population-weighted file
    t = pd.read_parquet(T.ROOT / "data/weather/temperature_population_hourly.parquet", columns=["country", "utc_timestamp", "temperature_2m"])
    te = t[t.country == "ES"].groupby("utc_timestamp").temperature_2m.mean()
    loc = te.index.tz_convert("Europe/Madrid")
    tt = pd.DataFrame({"date": pd.to_datetime(loc.date), "t": te.to_numpy()}).groupby("date").t.agg(tmean_es="mean", tmin_es="min", tmax_es="max").reset_index()
    d = tt[(tt.date >= "2018-01-01") & (tt.date <= "2023-12-31")].reset_index(drop=True)
    hol = pd.read_parquet(T.ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    d["es_work"] = (d.date.dt.dayofweek < 5) & ~d.date.isin(hes)
    d["month"], d["year"] = d.date.dt.month, d.date.dt.year
    covid = d.date.between(*C.EV.COVID)
    d["pre"] = d.date.between(C.PRE0, C.PRE1) & ~covid
    d["both"] = d.es_work
    out = {}
    for i in (351, 352):
        ld = CT.esios_load([i])
        gg = ld.groupby("date").hour.count()
        e, m = ld[ld.hour.isin(EVE)].groupby("date").v.sum(), ld[ld.hour.isin(MID)].groupby("date").v.sum()
        out[i] = np.log(e / m).where(gg == 24).reindex(d.date).to_numpy()
    res = {}
    for i, y in out.items():
        y = pd.Series(y, index=d.index)
        r = pd.Series(np.nan, index=d.index)
        for yr in (2018, 2019, 2020):
            s = d.year == yr
            r[s] = (y - C.taste_pred(d, y, "es", (yr,)))[s]
        s = d.year >= 2021
        r[s] = (y - C.taste_pred(d, y, "es", ()))[s]
        res[i] = r
    r = (res[352] - res[351])
    elig = d.es_work & ~covid & r.notna()
    dd = d[elig].assign(r=r[elig]).reset_index(drop=True)
    print("year means of the residual (352 minus 351 contrast):", dd.groupby("year").r.mean().round(4).to_dict(), flush=True)
    # dose
    eh = CT.omie_hourly()
    p24 = eh[(eh.index.get_level_values(0) >= "2024-01-01") & (eh.index.get_level_values(0) <= "2024-12-31")].reset_index()
    p24.columns = ["date", "hour", "s"]
    p24 = p24[p24.date.dt.dayofweek < 5]
    rows = []
    for W in (125, 250):
        v = dd.r.to_numpy()
        m = np.array([v[i:i + W].mean() for i in range(0, len(v) - W + 1, 5)])
        sd, mx = float(m.std(ddof=1)), float(np.abs(m).max())
        for F in (60.0, 90.0, 120.0):
            for A in (40.0, 70.0, 100.0):
                dp = np.log(0.75 * p24.s.clip(lower=0) + 0.25 * F + A) - np.log(p24.s.clip(lower=0) + A)
                dose = dp[p24.hour.isin(EVE)].mean() - dp[p24.hour.isin(MID)].mean()
                rows.append(dict(window=W, F=F, A=A, windows=len(m), window_mean_sd=sd, max_abs=mx, dose=dose, mde_effect=2.8 * sd, mde_sigma=2.8 * sd / abs(dose)))
    R = pd.DataFrame(rows)
    R.round(5).to_csv(T.OUT / "pvpc_noise.csv", index=False)
    print(R.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
