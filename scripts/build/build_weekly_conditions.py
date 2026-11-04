#!/usr/bin/env python3
"""Weekly conditions known at bid time, for the within-Iberia counterfactual (notes/rq-crisis-quantity.md, H8).

    .venv/bin/python scripts/build/build_weekly_conditions.py

One row per Monday-start week, 2021-09-27 -> 2023-06-26 (the B1 matrix weeks), each variable the mean over the week's seven delivery days of what was known
by 12:00 on D-1: prices with the D-2 rule and a five-day forward fill over weekends (as the `_bid` costs), ESIOS day-ahead forecasts of the same day (published before 11:00 on D-1).
  psv_bid       PSV (GME MGP-GAS reference price, sessions up to D-2) -- the gas price not changed by the Iberian cap
  mibgas_bid    MIBGAS index, D-2 (kept for reference only: the cap moved it; not a predictor in H8)
  eua_bid       EUA carbon, D-2
  netload_fc    ESIOS 1775 - 1777 - 1779 (demand - wind - PV forecasts), MW, Spanish local days
  temp_es / temp_it   population-weighted temperature (ERA5, realised, so a forecast proxy)
Reads data/ only; writes outputs/tables/gas_cap_weekly_conditions.parquet.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs" / "tables" / "gas_cap_weekly_conditions.parquet"
D0, D1 = "2021-09-13", "2023-07-09"
DAYS = pd.date_range(D0, D1, freq="D")
WEEKS = pd.date_range("2021-09-27", "2023-06-26", freq="W-MON")


def weekly(s: pd.Series) -> pd.Series:
    s = s.reindex(DAYS)
    return s.groupby(s.index.to_period("W-SUN").start_time).mean().reindex(WEEKS)


def lagged(s: pd.Series, lag: int, ffill: int = 5) -> pd.Series:
    s = s.copy()
    s.index = pd.to_datetime(s.index)
    s = s[~s.index.duplicated()].reindex(pd.date_range("2021-01-01", D1)).ffill(limit=ffill)
    return s.shift(lag)


def local_daily(df: pd.DataFrame, col: str, tz: str) -> pd.Series:
    x = pd.Series(df[col].to_numpy(), index=df["utc_timestamp"].dt.tz_convert(tz).dt.tz_localize(None))
    return x.groupby(x.index.normalize()).mean()


def main() -> int:
    W = pd.DataFrame(index=WEEKS)
    f = {}
    for i, n in ((1775, "dem"), (1777, "wind"), (1779, "pv")):
        f[n] = local_daily(pd.read_parquet(DATA / f"esios/esios_{i}.parquet"), "value", "Europe/Madrid")
    W["netload_fc"] = weekly(f["dem"] - f["wind"] - f["pv"])
    m = pd.read_parquet(DATA / "mibgas/mibgas_price_index_daily.parquet").set_index("date")["mibgas_es_eur_mwh"]
    W["mibgas_bid"] = weekly(lagged(m, 2))
    eua = pd.read_parquet(DATA / "investing/eua_carbon_price_daily.parquet").set_index("date")["close"]
    W["eua_bid"] = weekly(lagged(eua, 2))
    g = pd.read_parquet(DATA / "gme/gas/gme_mgp_gas_daily.parquet")
    gg = g[g.session <= g.gas_day - pd.Timedelta(days=2)].sort_values("session").groupby("gas_day").last()["price_ref"]
    gg.index = pd.to_datetime(gg.index)
    W["psv_bid"] = weekly(gg.reindex(pd.date_range("2021-01-01", D1)).ffill(limit=5))
    t = pd.read_parquet(DATA / "weather/temperature_population_index.parquet")
    W["temp_es"] = weekly(local_daily(t, "temp_pop_es", "Europe/Madrid"))
    ti = pd.read_parquet(DATA / "weather/temperature_population_italy.parquet")
    W["temp_it"] = weekly(local_daily(ti, "temp_pop_it", "Europe/Rome"))
    W.index.name = "w"
    W.to_parquet(OUT)
    print(f"{len(W)} weeks {W.index.min().date()} -> {W.index.max().date()}; NaN per column: {W.isna().sum().to_dict()}")
    pre = W.index <= "2022-06-06"
    print(W[pre].describe().loc[["min", "max"]].round(1).to_string())
    print(W[~pre].describe().loc[["min", "max"]].round(1).to_string())
    print("pre-cap correlations:\n" + W[pre].corr().round(2).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
