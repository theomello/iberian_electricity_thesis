"""Reduced form and IV for the demand-elasticity design: does demand by segment move with the wind-driven price?

Hourly era 2019-01-01 -> 2025-09-30. Outcome: log hourly demand of a segment (PBF scheduled 351 free-market retail,
352 reference/PVPC retail, 353 direct consumers; measured by voltage level 1201 E0 ... 1207 E6, 10269 total).
Instruments: ESIOS 1777 wind and 1779 solar day-ahead forecasts. Controls: demand forecast 1775, temperature
(heating, cooling degree hours), gas price, hour x month, hour x day-of-week and year-month effects.
Reports the price coefficient (semi-elasticity: % change in demand per EUR/MWh), the elasticity at the mean price,
and the reduced-form coefficients. Standard errors clustered by day. Ratios (PVPC over free-market, industrial over
low voltage) difference out what weather does to everyone. Writes outputs/tables/demand_reduced_form.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables"
SEG = {"free_retail_351": 351, "pvpc_352": 352, "direct_353": 353, "E0_lowvolt_1201": 1201, "E1_1202": 1202,
       "E2_1203": 1203, "E3_1204": 1204, "E4_1205": 1205, "E5_1206": 1206, "E6_1207": 1207, "total_10269": 10269}


def series(i):
    f = pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet")[["utc_timestamp", "value"]]
    return f.drop_duplicates("utc_timestamp").set_index("utc_timestamp").value


def load() -> pd.DataFrame:
    p = pd.read_parquet(ROOT / "data/omie/prices/omie_day_ahead_prices.parquet")
    p = p[p.resolution_min == 60][["date", "utc_timestamp", "price_es"]].set_index("utc_timestamp")
    for i, n in [(1775, "dem_fc"), (1777, "wind_fc"), (1779, "solar_fc")]:
        p[n] = series(i)
    for n, i in SEG.items():
        p[n] = series(i)
    t = pd.read_parquet(ROOT / "data/weather/temperature_population_index.parquet").set_index("utc_timestamp")
    p[["cdh_es", "hdh_es"]] = t[["cdh_es", "hdh_es"]]
    g = pd.read_parquet(ROOT / "data/mibgas/mibgas_price_index_daily.parquet").set_index("date").mibgas_es_eur_mwh
    p["gas"] = p.date.map(g)
    p = p.reset_index()
    loc = p.utc_timestamp.dt.tz_convert("Europe/Madrid")
    p["hour"], p["month"], p["dow"], p["ym"] = loc.dt.hour, loc.dt.month, loc.dt.dayofweek, loc.dt.strftime("%Y-%m")
    for c in ["dem_fc", "wind_fc", "solar_fc"]:
        p[c] = p[c] / 1000.0
    p["E1_6"] = p[["E1_1202", "E2_1203", "E3_1204", "E4_1205", "E5_1206", "E6_1207"]].sum(axis=1, min_count=6)
    return p[p.utc_timestamp < "2025-10-01"]


def controls(d):
    parts = [d[["dem_fc", "cdh_es", "hdh_es", "gas"]]]
    for a, b in [("hour", "month"), ("hour", "dow")]:
        parts.append(pd.get_dummies(d[a].astype(str) + "_" + d[b].astype(str), drop_first=True, dtype=float))
    parts.append(pd.get_dummies(d.ym, drop_first=True, dtype=float))
    W = pd.concat(parts, axis=1).to_numpy()
    return np.column_stack([np.ones(len(d)), W])


def resid(v, W):
    return v - W @ np.linalg.lstsq(W, v, rcond=None)[0]


def cluster_se(x, e, g):
    """Sandwich for a single regressor x (possibly fitted) with residual e, clustered by g."""
    s = pd.Series(x * e).groupby(g).sum().to_numpy()
    return np.sqrt((s ** 2).sum()) / (x @ x)


def one(d, W, ycol):
    y = np.log(d[ycol].to_numpy())
    return one_y(d, W, y)


def one_y(d, W, y):
    g = d.date.factorize()[0]
    ry, rp = resid(y, W), resid(d.price_es.to_numpy(), W)
    Z = np.column_stack([resid(d.wind_fc.to_numpy(), W), resid(d.solar_fc.to_numpy(), W)])
    pi = np.linalg.lstsq(Z, rp, rcond=None)[0]
    ph = Z @ pi
    b = (ph @ ry) / (ph @ rp)
    e = ry - rp * b
    se = cluster_se(ph, e, g) * (ph @ ph) / (ph @ rp)
    rf = np.linalg.lstsq(Z, ry, rcond=None)[0]
    rfe = ry - Z @ rf
    # reduced-form wind coefficient and its clustered se
    zw = Z[:, 0]
    M = np.linalg.inv(Z.T @ Z)
    sc = pd.DataFrame(Z * rfe[:, None]).groupby(g).sum().to_numpy()
    V = M @ (sc.T @ sc) @ M
    return b, se, rf[0], np.sqrt(V[0, 0])


def main():
    d0 = load()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    eras = {"2019-2025": (2019, 2025), "2019-2021": (2019, 2021), "2022-2023": (2022, 2023), "2024-2025": (2024, 2025)}
    for en, (a, b) in eras.items():
        yr = d0.ym.str[:4].astype(int)
        d = d0[(yr >= a) & (yr <= b)].dropna().reset_index(drop=True)
        W = controls(d)
        mp = d.price_es.mean()
        outs = {k: np.log(d[k].to_numpy()) for k in list(SEG) + ["E1_6"]}
        outs["ratio_pvpc_over_free"] = np.log(d.pvpc_352.to_numpy() / d.free_retail_351.to_numpy())
        outs["ratio_E1_6_over_E0"] = np.log(d.E1_6.to_numpy() / d.E0_lowvolt_1201.to_numpy())
        for k, y in outs.items():
            if not np.isfinite(y).all():
                m = np.isfinite(y)
                dd, WW, yy = d[m].reset_index(drop=True), W[m], y[m]
            else:
                dd, WW, yy = d, W, y
            bb, se, rfw, rfse = one_y(dd, WW, yy)
            rows.append(dict(era=en, outcome=k, n=len(dd), mean_price=mp, semi_elast_pct_per_eur=100 * bb,
                             se=100 * se, elasticity_at_mean=bb * mp, rf_wind_pct_per_gw=100 * rfw, rf_se=100 * rfse))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "demand_reduced_form.csv", index=False)
    pd.set_option("display.width", 220)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
