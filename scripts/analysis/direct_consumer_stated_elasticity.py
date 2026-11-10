#!/usr/bin/env python3
"""Step 1 of notes/rq-direct-consumers.md: E2, the price response read off the direct consumers' own stated curves.

    .venv/bin/python scripts/analysis/direct_consumer_stated_elasticity.py

No estimation of behaviour: each unit-hour's offered buy curve is held fixed and evaluated at p* +/- dp, where dp is
the price change one standard deviation of the D-1 wind forecast (ESIOS 1777) moves the price by, in that regime:

    first stage   daily mean price_es on daily mean wind forecast (GW), demand forecast (1775, GW),
                  year-month and weekday fixed effects;  dp = |beta| x sd(wind forecast net of the same FE)

The curve is known at p* + {-50, -10, 0, +10, +50}; q(p* +/- dp) is interpolated linearly between those points.
Per unit-hour with demand at the price q_p > 0:

    resp  = (q(p* - dp) - q(p* + dp)) / (2 q_p)       share of demand that moves per dp of price
    elast = resp x p* / dp                             arc elasticity (hours with p* >= 20)

Before 2021-07-07 an hour enters only if p* + dp < 180.30 (bids above the old cap cannot exist). Means are weighted by
q_p. Regimes: 2019-01 -> 2021-06, 2021-07 -> 2022-12, 2023-01 -> 2026-05. Samples from direct_consumers.parquet
(own + represented): process, weather_exposed, refinery, unclassified. Reported with the top-5 units' weight share,
without the top 5, and on a balanced panel (units with q_p > 0 on >= 180 days in every year 2019-2024).

Writes outputs/tables/direct_consumer_stated_elasticity.csv.
"""
from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
T = ROOT / "outputs" / "tables"
CAP_OLD, LIMIT_CHANGE = 180.30, pd.Timestamp("2021-07-07")
REGIMES = [("2019-21H1", "2019-01-01", "2021-06-30"), ("2021H2-22", "2021-07-01", "2022-12-31"),
           ("2023-26", "2023-01-01", "2026-05-31")]
OFF = np.array([-50.0, -10.0, 0.0, 10.0, 50.0])
QCOLS = ["q_m50", "q_m10", "q_p", "q_p10", "q_p50"]


def daily(i: int) -> pd.Series:
    d = pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet", columns=["value", "datetime"])
    d["date"] = d.datetime.str[:10]
    return d.groupby("date").value.mean() / 1e3  # GW


def demean(x: pd.DataFrame, fe: list[str], cols: list[str]) -> pd.DataFrame:
    x = x.copy()
    for _ in range(20):  # alternating projections for two sets of fixed effects
        for f in fe:
            x[cols] = x[cols] - x.groupby(f)[cols].transform("mean")
    return x


def first_stage() -> pd.DataFrame:
    p = pd.read_parquet(ROOT / "data/omie/prices/omie_day_ahead_prices.parquet", columns=["date", "price_es"])
    p["date"] = pd.to_datetime(p.date).dt.date.astype(str)
    d = pd.DataFrame({"p": p.groupby("date").price_es.mean(), "w": daily(1777), "dem": daily(1775)}).dropna()
    d.index = pd.to_datetime(d.index)
    d["ym"], d["wd"] = d.index.to_period("M").astype(str), d.index.weekday
    rows = []
    for name, a, b in REGIMES:
        x = demean(d.loc[a:b], ["ym", "wd"], ["p", "w", "dem"])
        X = x[["w", "dem"]].to_numpy()
        beta, *_ = np.linalg.lstsq(X, x.p.to_numpy(), rcond=None)
        e = x.p.to_numpy() - X @ beta
        XtXi = np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(XtXi @ (X.T * e**2) @ X @ XtXi))
        sd_w = x.w.std()
        rows.append(dict(regime=name, beta=beta[0], se=se[0], F=(beta[0] / se[0]) ** 2, sd_wind_gw=sd_w,
                         dp=abs(beta[0]) * sd_w, days=len(x)))
    return pd.DataFrame(rows).set_index("regime")


def load() -> pd.DataFrame:
    cols = ["date", "unit", "p"] + QCOLS
    h = pd.concat(pd.read_parquet(f, columns=cols) for f in sorted(glob.glob(str(T / "direct_consumer_panel/panel_*.parquet"))))
    h["date"] = pd.to_datetime(h.date)
    reg = pd.read_parquet(ROOT / "data/omie/registry/direct_consumers.parquet", columns=["unit", "kind", "sample"])
    h = h.merge(reg[reg.kind.isin(["own", "represented"])], on="unit")
    return h[h.q_p > 0]


def interp(q: np.ndarray, x: np.ndarray) -> np.ndarray:
    """q: n x 5 curve at OFF; x: n offsets. Linear between the bracketing points."""
    j = np.clip(np.searchsorted(OFF, x) - 1, 0, len(OFF) - 2)
    r = np.arange(len(x))
    lo, hi = OFF[j], OFF[j + 1]
    w = (x - lo) / (hi - lo)
    return q[r, j] * (1 - w) + q[r, j + 1] * w


def measure(h: pd.DataFrame, dp: float) -> pd.DataFrame:
    h = h.copy()
    q = h[QCOLS].to_numpy()
    n = len(h)
    h["resp"] = (interp(q, np.full(n, -dp)) - interp(q, np.full(n, dp))) / (2 * h.q_p)
    h["ok"] = (h.date >= LIMIT_CHANGE) | (h.p + dp < CAP_OLD)
    h["ok_e"] = h.ok & (h.p >= 20)
    h["elast"] = h.resp * h.p / dp
    return h


def stats(x: pd.DataFrame) -> dict:
    a, e = x[x.ok], x[x.ok_e]
    unit_w = a.groupby("unit").q_p.sum().sort_values(ascending=False)
    top5 = unit_w.index[:5]
    no5 = a[~a.unit.isin(top5)]
    return dict(units=a.unit.nunique(), twh=a.q_p.sum() / 1e6, share_hours_kept=x.ok.mean(),
                resp=np.average(a.resp, weights=a.q_p) if len(a) else np.nan,
                elast=np.average(e.elast, weights=e.q_p) if len(e) else np.nan,
                top5_share=unit_w.iloc[:5].sum() / unit_w.sum() if len(unit_w) else np.nan,
                elast_no_top5=np.average(no5.elast[no5.ok_e], weights=no5.q_p[no5.ok_e]) if no5.ok_e.any() else np.nan,
                share_units_any=((a.resp * a.q_p).groupby(a.unit).sum() / a.q_p.groupby(a.unit).sum() > 0.005).mean())


def main() -> int:
    fs = first_stage()
    pd.set_option("display.width", 200)
    print("first stage (daily price on D-1 wind forecast, GW):")
    print(fs.round(3).to_string())
    h = load()
    days = h.assign(y=h.date.dt.year).groupby(["unit", "y"]).date.nunique().unstack()
    balanced = set(days.index[(days.reindex(columns=range(2019, 2025)).fillna(0) >= 180).all(axis=1)])
    out = []
    for name, a, b in REGIMES:
        x = measure(h[(h.date >= a) & (h.date <= b)], fs.loc[name, "dp"])
        for s, g in [("all", x)] + list(x.groupby("sample")) + [("balanced", x[x.unit.isin(balanced)]),
                                                                 ("process_balanced", x[x.unit.isin(balanced) & (x["sample"] == "process")])]:
            out.append(dict(regime=name, sample=s, dp=fs.loc[name, "dp"], **stats(g)))
    o = pd.DataFrame(out).set_index(["regime", "sample"])
    o.to_csv(T / "direct_consumer_stated_elasticity.csv")
    print(f"\nbalanced panel: {len(balanced)} units")
    print("\nstated response (curve fixed, price moved by +/- dp):")
    print(o.round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
