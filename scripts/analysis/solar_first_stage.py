#!/usr/bin/env python3
"""First stage: do the solar instruments move EDP's markup term X?

    .venv/bin/python scripts/build/build_solar_instrument.py      # input
    .venv/bin/python scripts/analysis/edp_hydro_panel.py          # input
    .venv/bin/python scripts/analysis/solar_first_stage.py

`notes/rq-midday-hydro.md` §4: the test regresses the offer (on price-setting
periods, p*) on X = net / |RD'| within a day, and X is endogenous -- it is built
from the auction's own outcome. This checks whether each candidate from
`build_solar_instrument.py` moves X once the design's fixed effects are in.

SPECIFICATION

    X_t = pi * Z_t + gamma * demand_forecast_t + day FE + hour x month FE + e_t

on two samples:

* ALL EDP PERIODS -- one row per period (X is a firm-level quantity), day FE.
* PRICE-SETTING -- EDP unit-periods whose top cleared step is the zone price,
  in unit-days with 2+ of them; unit-day FE. The sample the test itself uses.

THE TREND TEST. Calendar-month x hour fixed effects leave the growth of solar
capacity across years in the instrument, and a trend is a weak exclusion
restriction -- it moves with everything else that trends. Each first stage is
therefore repeated with hour x YEAR-month fixed effects, which absorb capacity
growth at every hour of the day. What survives is day-to-day variation within a
month: weather. An instrument that collapses under them was identifying from the
trend.

Standard errors clustered on date. The first-stage F is the cluster-robust Wald
statistic over the excluded instruments divided by their number, with no
small-sample correction -- a rule-of-thumb read (F > 10), not a formal weak-
instrument test.

The demand forecast is REE's day-ahead `demand_forecast_mw`, averaged over each
period: sunny days are hotter, and heat moves prices through demand
(`build_solar_instrument.py`, EXCLUSION).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
PANEL = ROOT / "outputs/tables/edp_hydro_panel.parquet"
SOLAR = ROOT / "outputs/tables/solar_instrument.parquet"
INSTRUMENTS = ["z_clear", "z_weather", "z_offered"]


def demean(df: pd.DataFrame, cols: list[str], fes: list[str],
           tol: float = 1e-9, maxit: int = 200) -> pd.DataFrame:
    """Partial out several fixed effects by alternating projections."""
    x = df[cols].astype(float).copy()
    codes = [pd.factorize(df[f])[0] for f in fes]
    for _ in range(maxit):
        prev = x.to_numpy().copy()
        for c in codes:
            x -= x.groupby(c).transform("mean")
        if np.max(np.abs(x.to_numpy() - prev)) < tol * (1 + np.max(np.abs(prev))):
            break
    return x


def cluster_ols(y: np.ndarray, X: np.ndarray, cl: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    inv = np.linalg.inv(X.T @ X)
    b = inv @ X.T @ y
    e = y - X @ b
    s = np.zeros((X.shape[1], X.shape[1]))
    order = np.argsort(cl, kind="stable")
    cl_s, X_s, e_s = cl[order], X[order], e[order]
    bounds = np.flatnonzero(np.r_[True, cl_s[1:] != cl_s[:-1], True])
    for a, z in zip(bounds[:-1], bounds[1:]):
        g = X_s[a:z].T @ e_s[a:z]
        s += np.outer(g, g)
    return b, inv @ s @ inv


def first_stage(df: pd.DataFrame, zs: list[str], fes: list[str], label: str) -> None:
    cols = ["X"] + zs + ["fcst"]
    d = df.dropna(subset=cols)
    w = demean(d, cols, fes)
    y = w["X"].to_numpy()
    Xm = w[zs + ["fcst"]].to_numpy()
    # Scale each regressor to GW so coefficients are readable.
    b, V = cluster_ols(y, Xm, d["date"].to_numpy().astype("datetime64[D]").astype(np.int64))
    k = len(zs)
    bz, Vz = b[:k], V[:k, :k]
    wald = float(bz @ np.linalg.solve(Vz, bz))
    se = np.sqrt(np.diag(Vz))
    terms = ", ".join(f"{z} {bz[i]*1000:+.3f} (t {bz[i]/se[i]:+.1f})" for i, z in enumerate(zs))
    print(f"  {label:34s} n={len(d):>8,}  F={wald / k:8.1f}   {terms}")


def load_edp_sample(panel_cols: tuple[str, ...] = ()) -> pd.DataFrame:
    """EDP's unit-periods with the instruments, the demand forecast and FE keys.

    Shared with `midday_hydro_iv.py`, so the first and second stage run on
    exactly the same rows.
    """
    s = pd.read_parquet(SOLAR)
    s["date"] = pd.to_datetime(s.date)
    fc = pd.read_parquet(DATA / "ree/ree_demand_forecast_5min.parquet",
                         columns=["utc_timestamp", "demand_forecast_mw"])
    fc["ts"] = pd.to_datetime(fc.utc_timestamp, utc=True)
    s["start"] = pd.to_datetime(s.utc_timestamp, utc=True)
    parts = []
    for res, g in s.groupby("resolution_min"):
        m = fc.set_index("ts").demand_forecast_mw.resample(f"{res}min").mean()
        parts.append(pd.Series(m.reindex(pd.DatetimeIndex(g.start)).to_numpy(), index=g.index))
    s["fcst"] = pd.concat(parts)
    zcols = [c for c in s.columns if c.startswith("z_")]

    cols = ["unit", "date", "period", "hour", "group", "era", "X", "marginal", *panel_cols]
    p = pd.read_parquet(PANEL, columns=list(dict.fromkeys(cols)))
    p = p[p.group == "EDP"]
    p["date"] = pd.to_datetime(p.date)
    p = p.merge(s[["date", "period", "fcst"] + zcols], on=["date", "period"], how="left")
    p["month"] = p.date.dt.month
    p["hm"] = p.hour.astype(str) + "_" + p.month.astype(str)
    p["hym"] = p.hour.astype(str) + "_" + p.date.dt.strftime("%Y%m")
    p["ud"] = p.unit + "_" + p.date.dt.strftime("%Y%m%d")
    return p


def price_setting(p: pd.DataFrame) -> pd.DataFrame:
    """Unit-periods whose top cleared step is the zone price, in unit-days with 2+."""
    mg = p[p.marginal]
    return mg[mg.groupby("ud").period.transform("size") >= 2]


def main() -> int:
    p = load_edp_sample()
    firm = p.drop_duplicates(["date", "period"])
    mg = price_setting(p)

    print("FIRST STAGE: X on each instrument (coefficient per GW), controls: demand forecast;")
    print("             FE: day (all periods) or unit-day (price-setting) + hour x month;")
    print("             SE clustered on date; F = cluster-robust Wald / #instruments\n")
    for sample, df, day in (("ALL EDP PERIODS", firm, "date"), ("PRICE-SETTING", mg, "ud")):
        for tag, hfe in (("hour x month FE", "hm"), ("hour x YEAR-month FE (trend test)", "hym")):
            fes = [day, hfe]
            print(f"{sample} -- {tag}")
            for z in INSTRUMENTS:
                first_stage(df, [z], fes, z)
            first_stage(df, ["z_weather", "z_offered"], fes, "z_weather + z_offered")
            for era, g in df.groupby("era", observed=True):
                first_stage(g, ["z_offered"], fes, f"z_offered, {era}")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
