"""Step zero of an hourly-spot-price IV for industrial load (proposed 2026-11-16; thresholds set before this run): first stage and noise only, no slope printed.

    .venv/bin/python scripts/analysis/industry_iv_noise.py

Sample: non-holiday weekdays 2019-01-01 -> 2023-12-31 (lockdown 2020-03-01 -> 2020-06-30 out), 24 hours. Outcome: ln of ESIOS 1204-1207 (E3-E6 industrial) hourly load; endogenous: OMIE day-ahead price
(EUR/MWh); instruments: D-1 wind forecast (1777), solar forecast (1779) and their squares; controls: year-month and hour-by-weekday effects, mean temperature, heating and cooling degree terms.
Rules (set now): F >= 10 (date-clustered Wald on the instruments, controls partialled) and detectable elasticity 2.8 x SE(elasticity at the mean price) <= 0.25. Writes outputs/tables/industry_iv_noise.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_did as T  # noqa: E402


def hourly(i):
    s = pd.read_parquet(T.ROOT / f"data/esios/esios_{i}.parquet")[["utc_timestamp", "value"]].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value
    loc = s.index.tz_convert("Europe/Madrid")
    return pd.DataFrame({"date": pd.to_datetime(loc.date), "hour": loc.hour, "v": s.to_numpy()}).drop_duplicates(["date", "hour"]).set_index(["date", "hour"]).v


def resid(y, X):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ b


def main():
    load = sum(hourly(i) for i in (1204, 1205, 1206, 1207)).rename("load")
    d = pd.concat([load, hourly(1777).rename("wind"), hourly(1779).rename("solar"), CT.omie_hourly().rename("p")], axis=1).dropna().reset_index()
    t = pd.read_parquet(T.ROOT / "data/weather/temperature_population_hourly.parquet", columns=["country", "utc_timestamp", "temperature_2m"])
    te = t[t.country == "ES"].groupby("utc_timestamp").temperature_2m.mean()
    loc = te.index.tz_convert("Europe/Madrid")
    tt = pd.DataFrame({"date": pd.to_datetime(loc.date), "hour": loc.hour, "temp": te.to_numpy()}).drop_duplicates(["date", "hour"])
    d = d.merge(tt, on=["date", "hour"])
    hol = pd.read_parquet(T.ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    d = d[(d.date >= "2019-01-01") & (d.date <= "2023-12-31") & (d.date.dt.dayofweek < 5) & ~d.date.isin(hes) & ~d.date.between("2020-03-01", "2020-06-30") & (d.load > 0)].reset_index(drop=True)
    y = np.log(d.load.to_numpy())
    pbar = float(d.p.mean())
    ym = pd.get_dummies(d.date.dt.strftime("%Y-%m"), dtype=float).to_numpy()
    hd = pd.get_dummies(d.hour * 10 + d.date.dt.dayofweek, dtype=float).to_numpy()
    X = np.column_stack([ym, hd[:, 1:], d.temp, np.maximum(18 - d.temp, 0), np.maximum(d.temp - 22, 0)])
    w, s = d.wind.to_numpy() / 1000, d.solar.to_numpy() / 1000
    Zr = np.column_stack([resid(c, X) for c in (w, s, w ** 2, s ** 2)])
    p_r, y_r = resid(d.p.to_numpy(), X), resid(y, X)
    g = d.date.to_numpy()
    ug, inv = np.unique(g, return_inverse=True)

    def cl(M):  # sum of rows by cluster
        out = np.zeros((len(ug), M.shape[1]))
        np.add.at(out, inv, M)
        return out

    b, *_ = np.linalg.lstsq(Zr, p_r, rcond=None)
    e = p_r - Zr @ b
    A = np.linalg.inv(Zr.T @ Zr)
    sc = cl(Zr * e[:, None])
    V = A @ (sc.T @ sc) @ A
    F = float(b @ np.linalg.inv(V) @ b / Zr.shape[1])
    fit = Zr @ b
    beta = float(fit @ y_r / (fit @ p_r))
    u = y_r - beta * p_r
    se_beta = float(np.sqrt(((cl(fit * u[:, None])) ** 2).sum()) / abs(fit @ p_r))
    se_el = se_beta * pbar
    R = pd.DataFrame([dict(obs=len(d), days=len(ug), mean_price=pbar, first_stage_F=F, se_elasticity=se_el, detectable_elasticity=2.8 * se_el, F_ok=F >= 10, noise_ok=2.8 * se_el <= 0.25)])
    R.round(4).to_csv(T.OUT / "industry_iv_noise.csv", index=False)
    print(R.round(4).T.to_string())


if __name__ == "__main__":
    main()
