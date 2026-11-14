"""Cogeneration price response, checks against the common demand component (notes/rq-cogeneration.md, open item 1).

The Italian demand placebo showed the wind-forecast instrument carries a common demand pattern (+0.3% demand per GW of forecast wind in
both Italy and Spain). If cogeneration hosts' electricity demand follows that pattern, the baseline +0.012 per EUR 10 (pre-cap, gas) could
run through demand and not the price. Checks, pre-cap window (2021-01-01 -> 2022-06-14, days on disk), 2SLS as in
cogeneration_price_response.py, HAC 7 lags:
  C0 baseline: price on wind forecast, controls gas price, degree hours, weekday, month.
  C1 + REE's day-ahead demand forecast (ESIOS 1775, daily mean, GW) as a control.
  C2a solar forecast alone as the instrument (with the demand control); C2b wind purged of demand (residual of wind on the demand
      forecast, degree hours, weekday, month) as the instrument; C2c wind and solar together, with the demand control.
Outcomes: gas load factor, biomass-and-waste load factor (placebo), gas minus biomass. Writes outputs/tables/cogeneration_demand_checks.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cogeneration_price_response import ROOT, OUT, drivers, groups_daily, tsls  # noqa: E402


def demand_forecast():
    x = pd.read_parquet(ROOT / "data/esios/esios_1775.parquet")[["utc_timestamp", "value"]].drop_duplicates("utc_timestamp")
    x["d"] = pd.to_datetime(x.utc_timestamp.dt.tz_convert("Europe/Madrid").dt.date)
    return (x.groupby("d").value.mean() / 1000).rename("dem")


def main():
    lf = groups_daily()
    d = lf.join(drivers(), how="left").join(demand_forecast(), how="left").dropna().sort_index()
    d["diff_gas_minus_bio"] = d.lf_gas - d.lf_biomass_waste
    s = d[d.index <= "2022-06-14"].copy()
    print(f"{len(s)} days {s.index.min().date()} -> {s.index.max().date()}")
    dow = pd.get_dummies(s.index.dayofweek, drop_first=True, dtype=float).to_numpy()
    mon = pd.get_dummies(s.index.month, drop_first=True, dtype=float).to_numpy()
    base = [np.ones(len(s)), s.gas, s.cdh_es, s.hdh_es]
    X0 = np.column_stack(base + [dow, mon])
    X1 = np.column_stack(base + [s.dem, dow, mon])
    # wind purged of demand
    A = np.column_stack([np.ones(len(s)), s.dem, s.cdh_es, s.hdh_es, dow, mon])
    s["wind_pur"] = s.wind - A @ np.linalg.lstsq(A, s.wind, rcond=None)[0]
    print(f"corr(wind, demand forecast) {s.wind.corr(s.dem):+.2f}; corr(wind_purged, wind) {s.wind_pur.corr(s.wind):+.2f}")
    specs = [("C0 baseline (wind)", X0, s[["wind"]]), ("C1 + demand control (wind)", X1, s[["wind"]]),
             ("C2a solar alone, demand control", X1, s[["solar"]]), ("C2b wind purged of demand", X1, s[["wind_pur"]]),
             ("C2c wind + solar, demand control", X1, s[["wind", "solar"]])]
    rows = []
    for name, X, Z in specs:
        for y in ["lf_gas", "lf_biomass_waste", "diff_gas_minus_bio"]:
            b, se, F = tsls(s[y].to_numpy(), s.price.to_numpy(), Z.to_numpy(), X)
            rows.append(dict(spec=name, outcome=y, n=len(s), d_lf_per_10eur=10 * b, se=10 * se, t=b / se, first_stage_F=F))
    r = pd.DataFrame(rows)
    r.round(4).to_csv(OUT / "cogeneration_demand_checks.csv", index=False)
    pd.set_option("display.width", 200)
    print(r.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
