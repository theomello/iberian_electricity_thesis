"""Diagnose why the fixed-price placebo (free-market retail, ESIOS 351) responds to the wind-driven price.

Variants of demand_reduced_form.py, same outcomes, 2019-01-01 -> 2025-09-30:
  V0 baseline: both forecasts, temperature index, hour x month, hour x weekday, year-month, gas
  V1 night only (local 00-06, solar zero): the solar forecast and self-consumption drop out
  V2 wind forecast alone as instrument
  V3 wind alone + richer weather: every Spanish city's temperature, 24 h and 72 h trailing means of the index, its
     square, and mean shortwave radiation at the ten weather points (cloud, lighting, self-consumption)
  V4 = V3 at night
Pass rule set before the run: the placebo (351) semi-elasticity within two standard errors of zero.
Writes outputs/tables/demand_placebo_diagnosis.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from demand_reduced_form import ROOT, OUT, load  # noqa: E402


def weather(d):
    h = pd.read_parquet(ROOT / "data/weather/temperature_population_hourly.parquet")
    h = h[h.country.astype(str).str.upper().isin(["ES", "SPAIN", "ESP"])]
    city = h.pivot_table(index="utc_timestamp", columns="city", values="temperature_2m")
    city.columns = ["t_" + str(c) for c in city.columns]
    w = pd.read_parquet(ROOT / "data/weather/weather_spain_hourly.parquet")
    rad = w.groupby("utc_timestamp").shortwave_radiation.mean().rename("rad")
    x = d[["utc_timestamp"]].merge(city.reset_index(), on="utc_timestamp", how="left").merge(
        rad.reset_index(), on="utc_timestamp", how="left")
    idx = pd.read_parquet(ROOT / "data/weather/temperature_population_index.parquet").set_index("utc_timestamp").temp_pop_es
    idx = idx.sort_index()
    lag = pd.DataFrame({"t24": idx.rolling(24, min_periods=24).mean(), "t72": idx.rolling(72, min_periods=72).mean()})
    x = x.merge(lag.reset_index(), on="utc_timestamp", how="left")
    x["t2"] = d.set_index("utc_timestamp").index.map(idx).to_numpy() ** 2
    return x.drop(columns="utc_timestamp")


def design(d, rich):
    parts = [d[["dem_fc", "cdh_es", "hdh_es", "gas"]]]
    if rich:
        parts.append(weather(d))
    for a, b in [("hour", "month"), ("hour", "dow")]:
        parts.append(pd.get_dummies(d[a].astype(str) + "_" + d[b].astype(str), drop_first=True, dtype=float))
    parts.append(pd.get_dummies(d.ym, drop_first=True, dtype=float))
    W = pd.concat(parts, axis=1)
    W = W.loc[:, W.std() > 0]
    return np.column_stack([np.ones(len(d)), W.to_numpy()])


def resid_mat(M, W):
    return M - W @ np.linalg.lstsq(W, M, rcond=None)[0]


def csum(a, g):
    return pd.DataFrame(a).groupby(g).sum().to_numpy()


def iv(Y, rp, Z, g):
    """Y: n x k residualised outcomes; rp: residualised price; Z: n x m residualised instruments."""
    pi = np.linalg.lstsq(Z, rp, rcond=None)[0]
    e1 = rp - Z @ pi
    M = np.linalg.inv(Z.T @ Z)
    s = csum(Z * e1[:, None], g)
    V = M @ (s.T @ s) @ M
    F = float(pi @ np.linalg.solve(V, pi) / len(pi))
    ph = Z @ pi
    den = ph @ rp
    out = []
    for j in range(Y.shape[1]):
        y = Y[:, j]
        b = (ph @ y) / den
        e = y - rp * b
        se = np.sqrt((csum(ph * e, g) ** 2).sum()) / abs(den)
        out.append((b, se))
    return F, out


def main():
    d0 = load()
    d0 = d0.dropna().reset_index(drop=True)
    d0 = d0.dropna(subset=["pvpc_352", "free_retail_351", "E0_lowvolt_1201"])
    d0 = d0.reset_index(drop=True)
    Yd = {"free_retail_351": np.log(d0.free_retail_351), "pvpc_352": np.log(d0.pvpc_352),
          "direct_353": np.log(d0.direct_353.where(d0.direct_353 > 0)),
          "E0_lowvolt_1201": np.log(d0.E0_lowvolt_1201), "total_10269": np.log(d0.total_10269),
          "ratio_pvpc_over_free": np.log(d0.pvpc_352 / d0.free_retail_351),
          "ratio_E1_6_over_E0": np.log(d0.E1_6 / d0.E0_lowvolt_1201)}
    Yall = pd.DataFrame(Yd)
    variants = {"V0 baseline": (False, False, ["wind_fc", "solar_fc"]),
                "V1 night": (True, False, ["wind_fc"]),
                "V2 wind only": (False, False, ["wind_fc"]),
                "V3 wind only + rich weather": (False, True, ["wind_fc"]),
                "V4 night + rich weather": (True, True, ["wind_fc"])}
    rows = []
    for vn, (night, rich, zc) in variants.items():
        m = (d0.hour <= 6).to_numpy() if night else np.ones(len(d0), bool)
        d = d0[m].reset_index(drop=True)
        Y = Yall[m].reset_index(drop=True)
        ok = np.isfinite(Y).all(axis=1).to_numpy()
        d, Y = d[ok].reset_index(drop=True), Y[ok].reset_index(drop=True)
        W = design(d, rich)
        keep = np.isfinite(W).all(axis=1)
        d, Y, W = d[keep].reset_index(drop=True), Y[keep].reset_index(drop=True), W[keep]
        g = d.date.factorize()[0]
        Ym = resid_mat(Y.to_numpy(), W)
        rp = resid_mat(d.price_es.to_numpy()[:, None], W)[:, 0]
        Z = resid_mat(d[zc].to_numpy(), W)
        F, res = iv(Ym, rp, Z, g)
        mp = d.price_es.mean()
        for (b, se), k in zip(res, Y.columns):
            rows.append(dict(variant=vn, outcome=k, n=len(d), first_stage_F=F, semi_elast_pct_per_eur=100 * b,
                             se=100 * se, elasticity_at_mean=b * mp, t=b / se))
        print(vn, "n", len(d), "F", round(F, 1), "mean price", round(mp, 1), flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "demand_placebo_diagnosis.csv", index=False)
    pd.set_option("display.width", 200)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
