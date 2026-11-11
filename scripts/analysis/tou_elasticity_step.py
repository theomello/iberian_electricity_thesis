"""Elasticity step of the time-of-use replication (docs/specs/2026-11-11-tou-hardening-design.md, step 4), run after step 2 passed.

Relative price of a period against off-peak, before and after the reform, on the same wholesale energy cost: the post-reform energy term
is ESIOS 1001 minus the charges component 1876 (EUR/MWh, peninsular, working days, June-September 2021, by clock class); the
pre-reform charge is the old flat 44.0 (tou_price_shape.csv), the post-reform charges are ESIOS 1876 by day and clock class (they fall in September and October 2021 when system charges were cut). Change in
ln(p_class / p_off), the mean over days of ln((E_class + new charge) / (E_off + new charge off)) - ln((E_class + 44) / (E_off + 44)). Elasticity of substitution
between a period and off-peak = the triple-difference effect on ln(load_class / load_off) divided by that change (the DDD is the
policy-specific part, from outputs/tables/tou_ddd_e0.csv). Not the paper's own-price elasticity (-0.08 to -0.135), an object of the
same kind. Writes outputs/tables/tou_elasticity_step.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables"
PEAK = [10, 11, 12, 13, 18, 19, 20, 21]
OLD = 44.0


def hourly(i):
    d = pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet")
    d = d[d.geo_name.isin(["Península", "España"])].drop_duplicates("utc_timestamp")
    loc = d.utc_timestamp.dt.tz_convert("Europe/Madrid")
    return pd.DataFrame({"date": loc.dt.tz_localize(None).dt.normalize().to_numpy(), "hour": loc.dt.hour.to_numpy(), f"v{i}": d.value.to_numpy()})


def main():
    p = hourly(1001).merge(hourly(1876), on=["date", "hour"])
    p = p[(p.date >= "2021-06-01") & (p.date <= "2021-09-30") & (p.date.dt.dayofweek < 5)].copy()
    p["E"] = p.v1001 - p.v1876
    p["cls"] = np.where(p.hour < 8, "off", np.where(p.hour.isin(PEAK), "peak", "mid"))
    day = p.groupby(["date", "cls"])[["E", "v1876"]].mean().unstack()
    print("mean charges by class (EUR/MWh), working days June-September 2021:", p.groupby("cls").v1876.mean().round(1).to_dict(),
          "| monthly peak charge:", p.groupby(p.date.dt.month).apply(lambda g: g[g.cls == "peak"].v1876.mean()).round(1).to_dict())
    ddd = pd.read_csv(OUT / "tou_ddd_e0.csv")
    rows = []
    for cls in ("peak", "mid"):
        new_ratio = np.log((day[("E", cls)] + day[("v1876", cls)]) / (day[("E", "off")] + day[("v1876", "off")]))
        old_ratio = np.log((day[("E", cls)] + OLD) / (day[("E", "off")] + OLD))
        dln = float((new_ratio - old_ratio).mean())
        for est in ("DiD V1 (hour, weekday, month effects)", "LASSO errors"):
            r = ddd[(ddd.est == est) & (ddd.contrast == f"DDD {cls}")].iloc[0]
            rows.append(dict(period=cls, estimator=est, d_ln_relative_price=dln, ddd_effect_pct=r.effect_pct, se_pct=r.se_pct,
                             elasticity=r.effect_pct / 100 / dln, se_elasticity=r.se_pct / 100 / abs(dln)))
    o = pd.DataFrame(rows)
    o.round(4).to_csv(OUT / "tou_elasticity_step.csv", index=False)
    pd.set_option("display.width", 200)
    print(o.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
