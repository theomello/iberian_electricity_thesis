#!/usr/bin/env python3
"""Leg B: does a cascade's daily water value rise with the day's markup term?

    .venv/bin/python scripts/analysis/water_value_revealed.py   # input
    .venv/bin/python scripts/analysis/water_value_across_days.py

`docs/specs/2026-09-29-thesis-framework-design.md` §4, leg B;
`notes/rq-midday-hydro.md` §7, item 10.

THE IDEA

EDP's stable cascades submit one offer curve for the whole day (§3.13), so if
they exercise market power it is in the day's LEVEL, not its shape. The
first-order condition at the day level reads

    lambda50(u, d)  =  lambda(u, d)  +  beta * Xbar(d)

with lambda50 the unit-day's volume-weighted median offer price
(`water_value_revealed.py`), lambda the true water value and Xbar the day's mean
markup term for EDP, X = n / |RD'_net| (§3.9). Under the martingale rule
(spec §2) lambda moves only with news, so within a unit-WEEK it is close to
constant: unit x week fixed effects absorb it. What is left is day-to-day
variation in Xbar, instrumented by the day's offered solar (z_offered, §3.10),
which moves X and is known when the offer is made.

beta = 0 is price-taking across days; beta = 1 is supply-function Nash.

THE CONFOUNDER, AND WHY THE TEST IS SPLIT BY STORAGE

A sunny day displaces hydro, the water stays in the reservoir, and more water
means a lower water value -- the same sign as market power. Its size falls with
storage: a day's output is 1-7% of storage for Guadiana, Tejo-Mondego and
Cavado/Lima, and an eighth to a fifth for Douro and Mondego (§3.17). So the
test is read on the LARGE units; the SMALL ones are the contrast. Market power
predicts both groups respond; the confounder predicts the small ones respond
more.

A second confounder runs the other way: cloudy days are rainy days, and rain
lowers the water value while less solar raises X. Trailing rainfall is
controlled.

Controls: the forward price and gas (last value before d), the day's mean REE
demand forecast, 7-day trailing precipitation over the four western basins, and
day-of-week dummies. Errors clustered by week. Anderson-Rubin sets in closed
form, as in `midday_hydro_iv.py`.

TWO VERSIONS OF Xbar. `X_bar` averages the periods the firm panel keeps; it
drops periods priced at or below 1 EUR/MWh, the sunny middays, so on the sunniest
days it is an average over fewer, dearer periods and the first stage weakens
exactly where solar should act (2024-26, F = 12). `X_bar_all` averages every
clean period (no split, clearing identity holds), zero-price ones included, from
`edp_x_all_periods.py`, which reproduces the panel's X where the panel has it.
Days where under half the periods carry X are dropped, per version.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from midday_hydro_iv import ar_closed, ols, tsls  # noqa: E402
from solar_first_stage import demean  # noqa: E402

DATA = ROOT / "data"
LAMBDA = ROOT / "outputs/tables/water_value_revealed.parquet"
PANEL = ROOT / "outputs/tables/edp_hydro_panel.parquet"
SOLAR = ROOT / "outputs/tables/solar_instrument.parquet"
X_ALL = ROOT / "outputs/tables/edp_x_all_periods.parquet"   # edp_x_all_periods.py
PRICE_OUT = 300.0
LARGE = ["GUADIA", "TEMON", "ACAVADO", "ALIMA"]   # >= 2 weeks of storage (§3.17)
SMALL = ["ADOURO", "MONDEGO"]                     # ~5 days
RAIN_BASINS = ["duero", "tajo", "guadiana", "galicia_sil_mino"]
DOW = [f"dow{i}" for i in range(1, 7)]
CONTROLS = ["forward", "gas", "fcst_gw", "rain7"] + DOW


def daily_x() -> pd.DataFrame:
    p = pd.read_parquet(PANEL, columns=["date", "period", "group", "X"])
    p = p[p.group == "EDP"].drop_duplicates(["date", "period"])
    p["date"] = pd.to_datetime(p.date)
    return p.groupby("date").agg(X_bar=("X", "mean"), x_cover=("X", lambda s: s.notna().mean())).reset_index()


def daily_x_all() -> pd.DataFrame:
    x = pd.read_parquet(X_ALL, columns=["date", "period", "X", "clean"])
    x["date"] = pd.to_datetime(x.date)
    x["Xc"] = x.X.where(x.clean)
    return x.groupby("date").agg(X_bar_all=("Xc", "mean"),
                                 x_cover_all=("Xc", lambda s: s.notna().mean())).reset_index()


def daily_solar() -> pd.DataFrame:
    s = pd.read_parquet(SOLAR, columns=["date", "z_offered", "z_offered_indep"])
    s["date"] = pd.to_datetime(s.date)
    d = s.groupby("date")[["z_offered", "z_offered_indep"]].mean() / 1000   # GW
    return d.reset_index()


def daily_forecast() -> pd.DataFrame:
    f = pd.read_parquet(DATA / "ree/ree_demand_forecast_5min.parquet",
                        columns=["local_date", "demand_forecast_mw"])
    f["date"] = pd.to_datetime(f.local_date)
    return (f.groupby("date").demand_forecast_mw.mean() / 1000).rename("fcst_gw").reset_index()


def daily_rain() -> pd.DataFrame:
    r = pd.read_parquet(DATA / "weather/precipitation_basins_daily.parquet",
                        columns=["date", "basin", "precipitation_sum"])
    r = r[r.basin.isin(RAIN_BASINS)]
    r["date"] = pd.to_datetime(r.date)
    s = r.groupby("date").precipitation_sum.mean().sort_index()
    # Known at D-1: the seven days up to and including the day before delivery.
    return s.shift(1).rolling(7, min_periods=5).sum().rename("rain7").reset_index()


def sample() -> pd.DataFrame:
    d = pd.read_parquet(LAMBDA)
    for k in ("lambda25", "lambda50", "lambda75"):
        d.loc[d[k] >= PRICE_OUT, k] = np.nan
    d = d[d.unit.isin(LARGE + SMALL)]
    for f in (daily_x(), daily_x_all(), daily_solar(), daily_forecast(), daily_rain()):
        d = d.merge(f, on="date", how="left")
    d.loc[d.x_cover < 0.5, "X_bar"] = np.nan
    d.loc[d.x_cover_all < 0.5, "X_bar_all"] = np.nan
    wk = d.date.dt.isocalendar()
    d["uw"] = d.unit + "_" + wk.year.astype(str) + "_" + wk.week.astype(str)
    d["cl"] = (wk.year * 100 + wk.week).astype(int).to_numpy()
    dow = d.date.dt.dayofweek
    for i in range(1, 7):
        d[f"dow{i}"] = (dow == i).astype(float)
    return d


def iv_row(d: pd.DataFrame, y: str, label: str, z: str = "z_offered", x: str = "X_bar") -> None:
    cols = [y, x, z] + CONTROLS
    d = d.dropna(subset=cols)
    if len(d) < 300:
        print(f"    {label:34s} too few ({len(d)})")
        return
    w = demean(d, cols, ["uw"])
    cl = d.cl.to_numpy()
    Y, X, Z = w[y].to_numpy(), w[x].to_numpy(), w[z].to_numpy()
    W = w[CONTROLS].to_numpy()
    b_fs, se_fs = ols(X, np.column_stack([Z, W]), cl)
    b, se = tsls(Y, X, Z, W, cl)
    ar = ar_closed(Y, X, Z, W, cl)
    b_ols, se_ols = ols(Y, np.column_stack([X, W]), cl)
    print(f"    {label:34s} n={len(d):>6,} wk={len(np.unique(cl)):>4}  "
          f"FS {b_fs[0]:+.2f}/GW F {(b_fs[0] / se_fs[0]) ** 2:6.1f}  "
          f"beta {b:+.3f} ({se:.3f})  AR95 {ar:16s}  OLS {b_ols[0]:+.3f} ({se_ols[0]:.3f})")


def section(d: pd.DataFrame, x: str) -> None:
    for name, us in (("LARGE STORAGE (>= 2 weeks): Guadiana, Tejo-Mondego, Cavado, Lima", LARGE),
                     ("SMALL STORAGE (~5 days): Douro, Mondego -- the confounder's contrast", SMALL)):
        print(name)
        g = d[d.unit.isin(us)]
        for y in ("lambda25", "lambda50", "lambda75"):
            iv_row(g, y, f"{y}, pooled", x=x)
        iv_row(g, "lambda50", "lambda50, independent-owner solar", z="z_offered_indep", x=x)
        for era, (lo, hi) in {"2018-20": (2018, 2020), "2021-23": (2021, 2023),
                              "2024-26": (2024, 2026)}.items():
            iv_row(g[g.year.between(lo, hi)], "lambda50", f"lambda50, {era}", x=x)
        print()
    print("BY UNIT, lambda50, pooled")
    for u, g in d.groupby("unit"):
        iv_row(g, "lambda50", u, x=x)


def main() -> int:
    d = sample()
    print("LEG B: unit-day water value (volume-weighted offer-price quantile) on EDP's day-mean X,")
    print("instrumented by the day's offered solar. Unit x week FE; forward, gas, demand forecast,")
    print("trailing rain and day-of-week controls; clustered by week. beta: 0 price-taking, 1 Nash.\n")
    for x, lab in (("X_bar", "X_bar: FIRM-PANEL PERIODS ONLY (zero-price middays dropped)"),
                   ("X_bar_all", "X_bar_all: EVERY CLEAN PERIOD (zero-price middays included)")):
        sd = d.groupby("uw")[x].transform(lambda s: s - s.mean())
        print("=" * 100)
        print(f"{lab}   within-week sd {sd.std():.2f} EUR/MWh")
        print("=" * 100)
        section(d, x)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
