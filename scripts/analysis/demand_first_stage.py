"""First stage for the demand-elasticity design: does REE's day-ahead wind and solar forecast move the price?

Hourly era only (2019-01-01 -> 2025-09-30). Instruments: ESIOS 1777 (wind) and 1779 (photovoltaic), published
before 11:00 on D-1. Controls: demand forecast (1775), population-weighted temperature (heating and cooling
degree hours), hour-of-day x month-of-year effects, and in the tighter versions year-month effects and the
MIBGAS gas price. Standard errors clustered by day. Writes outputs/tables/demand_first_stage.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables"
OUT.mkdir(parents=True, exist_ok=True)


def load() -> pd.DataFrame:
    p = pd.read_parquet(ROOT / "data/omie/prices/omie_day_ahead_prices.parquet")
    p = p[p.resolution_min == 60][["date", "utc_timestamp", "price_es"]]
    for i, n in [(1775, "dem_fc"), (1777, "wind_fc"), (1779, "solar_fc")]:
        f = pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet")[["utc_timestamp", "value"]]
        p = p.merge(f.rename(columns={"value": n}).drop_duplicates("utc_timestamp"), on="utc_timestamp", how="inner")
    t = pd.read_parquet(ROOT / "data/weather/temperature_population_index.parquet")[["utc_timestamp", "cdh_es", "hdh_es"]]
    p = p.merge(t, on="utc_timestamp", how="left")
    g = pd.read_parquet(ROOT / "data/mibgas/mibgas_price_index_daily.parquet")[["date", "mibgas_es_eur_mwh"]]
    p = p.merge(g, on="date", how="left")
    loc = p.utc_timestamp.dt.tz_convert("Europe/Madrid")
    p["hour"], p["month"], p["ym"] = loc.dt.hour, loc.dt.month, loc.dt.strftime("%Y-%m")
    for c in ["dem_fc", "wind_fc", "solar_fc"]:
        p[c] = p[c] / 1000.0  # GWh per hour = GW
    return p.dropna().reset_index(drop=True)


def fit(d: pd.DataFrame, extra_fe: bool, gas: bool) -> dict:
    X = d[["wind_fc", "solar_fc", "dem_fc", "cdh_es", "hdh_es"]].copy()
    if gas:
        X["gas"] = d["mibgas_es_eur_mwh"]
    fe = pd.get_dummies((d.hour.astype(str) + "_" + d.month.astype(str)), drop_first=True, dtype=float)
    parts = [X, fe]
    if extra_fe:
        parts.append(pd.get_dummies(d.ym, drop_first=True, dtype=float))
    X = sm.add_constant(pd.concat(parts, axis=1))
    r = sm.OLS(d.price_es, X).fit(cov_type="cluster", cov_kwds={"groups": d.date.factorize()[0]})
    names = list(X.columns)
    R = np.zeros((2, len(names)))
    R[0, names.index("wind_fc")] = 1
    R[1, names.index("solar_fc")] = 1
    w = r.wald_test(R, scalar=True, use_f=True)
    # partial R2 of the instruments: residualise price and instruments on the other regressors
    others = [c for c in X.columns if c not in ("wind_fc", "solar_fc")]
    def res(y):
        return sm.OLS(y, X[others]).fit().resid
    ry = res(d.price_es)
    rz = pd.concat([res(d.wind_fc), res(d.solar_fc)], axis=1)
    pr2 = sm.OLS(ry, rz).fit().rsquared
    return dict(n=len(d), wind_eur_per_gw=r.params["wind_fc"], wind_se=r.bse["wind_fc"],
                solar_eur_per_gw=r.params["solar_fc"], solar_se=r.bse["solar_fc"],
                F=float(w.statistic), partial_R2=pr2)


def main():
    d = load()
    print(f"{len(d)} hours, {d.utc_timestamp.min()} -> {d.utc_timestamp.max()}; mean price {d.price_es.mean():.1f}")
    rows = []
    specs = {"A: hour x month, temperature": (False, False), "B: + gas price": (False, True),
             "C: + year-month effects (within-month)": (True, True)}
    eras = {"2019-2025": (2019, 2025), "2019-2021": (2019, 2021), "2022-2023": (2022, 2023), "2024-2025": (2024, 2025)}
    for en, (a, b) in eras.items():
        s = d[(d.ym.str[:4].astype(int) >= a) & (d.ym.str[:4].astype(int) <= b)]
        for sn, (fe, gas) in specs.items():
            rows.append(dict(era=en, spec=sn, **fit(s, fe, gas)))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "demand_first_stage.csv", index=False)
    pd.set_option("display.width", 200)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
