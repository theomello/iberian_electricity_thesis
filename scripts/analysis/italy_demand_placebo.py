"""Placebo: does Italian demand respond to the Iberian wind-moved price?

Spanish day-ahead price, moved by the Spanish wind forecast (ESIOS 1777), against log hourly Italian demand (GME accepted
purchases in national zones, data/gme/italy_demand_hourly.parquet) and, for comparison on the same hours, log Spanish
measured demand (ESIOS 10269). Window 2021-06-01 -> 2023-06-30. Controls (both outcomes): both countries' heating and
cooling degree hours, the two gas prices (MIBGAS, PSV), hour x month, hour x weekday and year-month effects. Also the
first stage of Italy's PUN on the Spanish wind forecast. Pass rule, set before the run: if Italian demand responds to the
Spanish price within two standard errors of zero, the placebo passes and says the wind instrument is not picking up a
common Iberian-Italian demand pattern; if it responds like Spanish demand, it fails. Clustered by day.
Writes outputs/tables/italy_demand_placebo.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from demand_reduced_form import ROOT, OUT, load  # noqa: E402
from demand_placebo_diagnosis import resid_mat, iv  # noqa: E402


def italy_side(index_utc):
    it = pd.read_parquet(ROOT / "data/gme/italy_demand_hourly.parquet")[["utc_timestamp", "demand_mwh", "pun"]]
    it = it.drop_duplicates("utc_timestamp")
    t = pd.read_parquet(ROOT / "data/weather/temperature_population_italy.parquet")[["utc_timestamp", "cdh_it", "hdh_it"]]
    g = pd.read_parquet(ROOT / "data/gme/gas/gme_mgp_gas_daily.parquet")
    g["gas_day"], g["session"] = pd.to_datetime(g.gas_day), pd.to_datetime(g.session)
    psv = g[(g.gas_day - g.session).dt.days == 1].dropna(subset=["price_ref"]).groupby("gas_day").price_ref.last().rename("psv")
    return it, t, psv


def main():
    d = load()
    d = d[(d.utc_timestamp >= "2021-06-01") & (d.utc_timestamp < "2023-07-01")]
    it, t, psv = italy_side(d.utc_timestamp)
    d = d.merge(it, on="utc_timestamp", how="inner").merge(t, on="utc_timestamp", how="left")
    d["psv"] = pd.to_datetime(d.date).map(psv)
    d = d.rename(columns={"gas": "mibgas"}).dropna(subset=["wind_fc", "price_es", "demand_mwh", "total_10269", "cdh_es", "hdh_es",
                                                          "cdh_it", "hdh_it", "mibgas", "psv", "pun"]).reset_index(drop=True)
    print(f"{len(d)} hours, {d.utc_timestamp.min()} -> {d.utc_timestamp.max()}; mean ES price {d.price_es.mean():.0f}, PUN {d.pun.mean():.0f}")
    parts = [d[["cdh_es", "hdh_es", "cdh_it", "hdh_it", "mibgas", "psv"]]]
    for a, b in [("hour", "month"), ("hour", "dow")]:
        parts.append(pd.get_dummies(d[a].astype(str) + "_" + d[b].astype(str), drop_first=True, dtype=float))
    parts.append(pd.get_dummies(d.ym, drop_first=True, dtype=float))
    W = pd.concat(parts, axis=1)
    W = np.column_stack([np.ones(len(d)), W.loc[:, W.std() > 0].to_numpy()])
    g = d.date.factorize()[0]
    rp = resid_mat(d.price_es.to_numpy()[:, None], W)[:, 0]
    Z = resid_mat(d[["wind_fc"]].to_numpy(), W)
    Y = pd.DataFrame({"ln_italy_demand": np.log(d.demand_mwh), "ln_spain_demand_measured": np.log(d.total_10269),
                      "ln_italy_pun": np.log(d.pun.clip(lower=1)), "ln_spain_price": np.log(d.price_es.clip(lower=1))})
    Ym = resid_mat(Y.to_numpy(), W)
    F, res = iv(Ym, rp, Z, g)
    mp = d.price_es.mean()
    rows = []
    # reduced form on wind
    rf = [(np.linalg.lstsq(Z, Ym[:, j], rcond=None)[0][0]) for j in range(Ym.shape[1])]
    for (b, se), k, r in zip(res, Y.columns, rf):
        rows.append(dict(outcome=k, n=len(d), first_stage_F=F, per_eur_pct=100 * b, se=100 * se, t=b / se,
                         elasticity_at_mean=b * mp, reduced_form_wind_pct_per_gw=100 * r))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "italy_demand_placebo.csv", index=False)
    pd.set_option("display.width", 200)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
