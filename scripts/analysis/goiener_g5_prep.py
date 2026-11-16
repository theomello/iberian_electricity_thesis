"""G5 data prep (docs/specs/2026-11-17-goiener-household-design.md): household responses and covariates for the regression forest. No estimate is evaluated here.

    .venv/bin/python scripts/analysis/goiener_g5_prep.py

Real window (2021-06-01 -> 2021-09-15): y_i = mean over the household's window weekdays of (peak - off) LASSO error, minus Portugal's mean contrast of the window (a constant, so it does not affect ranks or spreads);
households with fewer than 10 window days dropped. Placebo windows: the 26 season-matched windows of the RI run (starts within +-45 days of 1 June in 2018 and 2019), same construction from the pre-only placebo errors
(g_placebo_errors_pre.parquet), households with fewer than 10 days in that window dropped. Covariates (all pre-lockdown, never window days): contracted power p1 and p2, contract-data tenure (years of data), mean daily kWh,
peak, mid and night shares of daily kWh, temperature slope of ln daily kWh (Madrid/Bilbao/Pamplona daily mean), share of missing days, province code, activity-code group (first two digits of the CNAE, -1 missing).
Declared self-consumption is constant by selection and is dropped. Writes data/goiener/daily/g5_real.parquet, g5_placebo.parquet.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goiener_household as GH  # noqa: E402
import goiener_noise as G  # noqa: E402
import tou_did as T  # noqa: E402
import tou_randomization_inference as RI  # noqa: E402

ROOT = T.ROOT


def main():
    meta = pd.read_parquet(ROOT / "data/goiener/daily/selected_metadata.parquet").set_index("user")
    daily = pd.read_parquet(ROOT / "data/goiener/daily/daily.parquet")
    daily["date"] = pd.to_datetime(daily.date)
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    hpt = set(pd.to_datetime(hol[hol.area == "PT"].date))
    temps = G.daily_temps()
    E = pd.read_parquet(ROOT / "data/goiener/daily/g2_household_window.parquet")
    E["date"] = pd.to_datetime(E.date)
    P = pd.read_parquet(ROOT / "data/goiener/daily/g_placebo_errors_pre.parquet")
    P["date"] = pd.to_datetime(P.date)
    P["contrast"] = P.peak - P.off
    users = sorted(set(E.user) & set(P.user))
    wd = daily[(daily.date.dt.dayofweek < 5) & ~daily.date.isin(hes) & (daily.date < "2020-03-01") & daily.user.isin(users)].copy()
    wd["tot"] = wd.kwh_peak + wd.kwh_mid + wd.kwh_off
    rows = []
    for u, g in wd.groupby("user"):
        g = g[g.tot > 0]
        t = temps[G.CITY[meta.loc[u, "province"]]].tmean.reindex(g.date).to_numpy()
        ok = np.isfinite(t)
        slope = float(np.polyfit(t[ok], np.log(g.tot.to_numpy()[ok]), 1)[0]) if ok.sum() >= 60 else np.nan
        s = g[["kwh_peak", "kwh_mid", "kwh_off"]].sum()
        m = meta.loc[u]
        rows.append(dict(user=u, p1=m.p1, p2=m.p2, years_data=m.length_years, mean_kwh=float(g.tot.mean()), share_peak=float(s.kwh_peak / s.sum()), share_mid=float(s.kwh_mid / s.sum()), share_night=float(s.kwh_off / s.sum()),
                         temp_slope=slope, missing_pct=m.missing_samples_pct, province=int(pd.Categorical([m.province], categories=sorted(meta.province.dropna().unique())).codes[0]),
                         cnae2=int(m.cnae // 100) if pd.notna(m.cnae) else -1))
    X = pd.DataFrame(rows)
    # Portugal contrast by window, same pipeline as goiener_g6.py
    x = RI.D.prep(T.build("e0", end="2021-09-15"))
    d = x[~x.date.isin(hpt) & (x.date.dt.dayofweek < 5)].copy()
    d["per"] = np.where(d.hour.isin(GH.PEAK), "kwh_peak", np.where(d.hour < 8, "kwh_off", "kwh_mid"))
    d = d[(d.date < "2020-03-01") | ((d.date >= GH.W0) & (d.date <= GH.W1))]
    cnt = d.groupby("date").size()
    pv = d.pivot_table(index="date", columns="per", values="load_pt", aggfunc="sum")[["kwh_peak", "kwh_off"]]
    pv = pv[cnt.reindex(pv.index) == 24]
    pt_win = GH.series_window(pv, temps["pt"]).set_index("date").contrast
    pt_pl = G.one_household("PT", pv[pv.index < "2020-03-01"].reset_index(), temps["pt"]).set_index("date").contrast
    real = E.groupby("user").contrast.agg(y="mean", n="size").reset_index()
    real = real[real.n >= 10]
    real["y"] -= float(pt_win.mean())
    real = real.merge(X, on="user")
    wins = [(k, a, b) for k, a, b in RI.windows() if a.year in (2018, 2019) and abs((a - pd.Timestamp(year=a.year, month=6, day=1)).days) <= 45]
    pl = []
    for k, a, b in wins:
        w = P[(P.date >= a) & (P.date <= b)]
        r = w.groupby("user").contrast.agg(y="mean", n="size").reset_index()
        r = r[r.n >= 10]
        r["y"] -= float(pt_pl[(pt_pl.index >= a) & (pt_pl.index <= b)].mean())
        r["window"] = k
        pl.append(r.merge(X, on="user"))
    pl = pd.concat(pl, ignore_index=True)
    real.to_parquet(ROOT / "data/goiener/daily/g5_real.parquet")
    pl.to_parquet(ROOT / "data/goiener/daily/g5_placebo.parquet")
    print(f"real: {len(real)} households (days per household median {real.n.median():.0f}); placebo: {pl.window.nunique()} windows, median {pl.groupby('window').size().median():.0f} households per window", flush=True)
    print("covariate NaN counts (real):", real.drop(columns=["user", "y", "n"]).isna().sum()[lambda s: s > 0].to_dict(), flush=True)


if __name__ == "__main__":
    main()
