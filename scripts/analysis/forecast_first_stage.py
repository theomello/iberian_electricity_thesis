#!/usr/bin/env python3
"""First stage of REE's day-ahead forecasts on the five firms' n, |RD'|, X and p.

    .venv/bin/python scripts/analysis/forecast_first_stage.py

Step-offer design (docs/specs/2026-10-01-step-offer-design.md) §5.1 and §10 step 3:
do the forecasts REE publishes before 11:00 on D-1 move what the firm's markup
condition p - c = beta * n / |RD'| needs moved?

    y_ft = a_W W_t + a_S S_t + a_D D_t + FE + e_ft,   per firm f, y in {n, |RD'|, X, p}

W, S, D are REE's D+1 wind, solar and demand forecasts (ESIOS 1777, 1779, 1775), GW,
hourly; a quarter-hour period takes its hour's value. n is the price-exposed net
position (`net_mw`), |RD'| the slope of rivals' supply within +/-5 EUR/MWh of p*
(`slope_net`), X = n / |RD'|, all from `firm_x.parquet`, on the periods the legs use
(`clean & ~zero_price`), 2019-01-01 -> 2026-05-31.

Fixed effects: year-month x local hour (absorbs the build-out of capacity and the
seasonal shape of solar, leaving weather relative to that month-hour), and day of
week. Standard errors clustered by week. F is the cluster-robust Wald statistic for
the three forecasts jointly, divided by three. Two samples: all periods, and the
hourly era alone (to 2025-09-30), since from 2025-10-01 each hour has four
quarter-hour rows and the last eight months would carry about 28% of the weight.

Own versus rivals' fleets. With one national forecast per technology, a firm with
fixed shares s_W, s_S of national wind and solar has own exposure s_W W + s_S S and
rivals' (1 - s_W) W + (1 - s_S) S: two different combinations of W and S whenever
s_W != s_S. Regressing on W and S is that split, reparametrised; it does not need
the shares. The shares (each firm's offered wind and solar over all offered, from
`rival_{wind,solar}.parquet`) are printed to read the coefficients against.
Portugal's own forecast is not in this probe (ENTSO-E token pending).

Writes outputs/tables/forecast_first_stage.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from midday_hydro_iv import cluster_meat  # noqa: E402
from solar_first_stage import demean  # noqa: E402

TABLES = ROOT / "outputs/tables"
ESIOS = ROOT / "data/esios"
PRICES = ROOT / "data/omie/prices/omie_day_ahead_prices.parquet"
OUT = TABLES / "forecast_first_stage.csv"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")
FORECASTS = {"W": 1777, "S": 1779, "D": 1775}   # wind, solar, demand: GW
START = "2019-01-01"
Y = {"n": "net_mw", "slope": "slope_net", "X": "X", "p": "p_star"}
FES = ["ym_hour", "dow"]
HOURLY_END = "2025-09-30"


def forecasts() -> pd.DataFrame:
    """The three forecasts by UTC hour, GW."""
    out = None
    for name, ind in FORECASTS.items():
        f = pd.read_parquet(ESIOS / f"esios_{ind}.parquet", columns=["utc_timestamp", "value"])
        f = f.rename(columns={"value": name}).set_index("utc_timestamp")[name] / 1000.0
        out = f.to_frame() if out is None else out.join(f, how="outer")
    return out


def panel() -> pd.DataFrame:
    x = pd.read_parquet(TABLES / "firm_x.parquet",
                        columns=["date", "period", "resolution_min", "firm", "p_star", "net_mw",
                                 "slope_net", "X", "clean", "zero_price"])
    x = x[x.clean & ~x.zero_price & (x.date >= START)].copy()
    px = pd.read_parquet(PRICES, columns=["date", "period", "resolution_min", "utc_timestamp"])
    px["date"] = pd.to_datetime(px.date)
    d = x.merge(px, on=["date", "period", "resolution_min"], how="left", validate="many_to_one")
    assert d.utc_timestamp.notna().all(), "a firm_x period has no UTC timestamp"
    d["hour_utc"] = d.utc_timestamp.dt.floor("h")
    d = d.join(forecasts(), on="hour_utc")
    missing = d[list(FORECASTS)].isna().any(axis=1)
    assert not missing.any(), f"{missing.sum()} periods without a forecast, e.g. {d.loc[missing, 'date'].min()}"
    local = d.utc_timestamp.dt.tz_convert("Europe/Madrid")
    d["ym_hour"] = local.dt.strftime("%Y-%m") + "_" + local.dt.hour.astype(str)
    d["dow"] = local.dt.dayofweek
    d["wk"] = (d.date - pd.to_timedelta(d.date.dt.dayofweek, unit="D")).dt.strftime("%Y%m%d").astype(int)
    return d


def shares() -> pd.DataFrame:
    """Each firm's offered wind and solar over all offered, 2019 on (the reading key)."""
    rows = {}
    for tech in ("wind", "solar"):
        r = pd.read_parquet(TABLES / f"rival_{tech}.parquet")
        r = r[pd.to_datetime(r.date) >= START]
        rows[tech] = {f: r[f"own_{f}"].sum() / r.z_all.sum() for f in FIRMS}
    return pd.DataFrame(rows)


def first_stage(d: pd.DataFrame, y: str) -> dict:
    d = d.dropna(subset=[y])
    z = list(FORECASTS)
    w = demean(d, [y, *z], FES)
    Y, Z = w[y].to_numpy(), w[z].to_numpy()
    cl = d.wk.to_numpy()
    inv = np.linalg.inv(Z.T @ Z)
    b = inv @ Z.T @ Y
    e = Y - Z @ b
    V = inv @ cluster_meat(Z, e, cl) @ inv
    F = float(b @ np.linalg.solve(V, b)) / len(z)
    r2 = 1 - (e @ e) / (Y @ Y)
    sd_y = float(Y.std())
    row = {"n_obs": len(d), "weeks": len(np.unique(cl)), "F": F, "partial_r2": r2, "sd_y_within": sd_y}
    for k, name in enumerate(z):
        row[f"b_{name}"] = b[k]
        row[f"se_{name}"] = float(np.sqrt(V[k, k]))
        # effect of one within-sd of the forecast, in within-sds of y
        row[f"std_{name}"] = b[k] * float(Z[:, k].std()) / sd_y
    return row


def main() -> int:
    d = panel()
    print(f"{len(d):,} firm-periods, {d.date.min().date()} -> {d.date.max().date()}, "
          f"{d.wk.nunique()} weeks")
    sh = shares()
    print("\nshare of national offered wind / solar, 2019 on:")
    print(sh.round(3).to_string())
    rows = []
    for sample, ds in (("hourly era", d[d.date <= HOURLY_END]), ("all", d)):
        for f in FIRMS:
            df = ds[ds.firm == f]
            for yname, col in Y.items():
                rows.append({"sample": sample, "firm": f, "y": yname} | first_stage(df, col))
    t = pd.DataFrame(rows)
    t.to_csv(OUT, index=False)
    show = t.assign(**{f"{k}": t[f"b_{k}"].round(1).astype(str) + " (" + t[f"se_{k}"].round(1).astype(str) + ")"
                       for k in FORECASTS})
    print("\ncoefficient per GW of forecast (SE clustered by week); F joint / 3; partial R2")
    print(show[["sample", "firm", "y", "W", "S", "D", "F", "partial_r2"]]
          .round({"F": 1, "partial_r2": 3}).to_string(index=False))
    print("\neffect of one within-sd of each forecast, in within-sds of y (hourly era)")
    print(t.loc[t["sample"] == "hourly era", ["firm", "y", "std_W", "std_S", "std_D"]].round(2).to_string(index=False))
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
