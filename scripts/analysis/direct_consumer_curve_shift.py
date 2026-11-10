#!/usr/bin/env python3
"""Step 2 of notes/rq-direct-consumers.md: E3, do the direct consumers' curves shift with the expected price?
Reduced form on the D-1 wind forecast, 2019-01 -> 2021-06, with the gates fixed in the design.

    .venv/bin/python scripts/analysis/direct_consumer_curve_shift.py

Unit-day panel (daily means of the hourly panel), own + represented units of a sample (main: process). Regression
    y_ud = b W_d + controls_d + unit x year-month FE + weekday FE,   SE clustered by week
W_d: D-1 wind forecast (ESIOS 1777, daily mean GW). Controls: demand forecast (1775), population-weighted temperature,
heating and cooling degree hours, share of regions on a holiday. Outcomes:
    q_a50       offered MW at a bid >= EUR 50 (the fixed price nearest the regime's mean price, EUR 45): E3's outcome
    q_a20, q_a80, q_offered, q_cleared, total_buy_mw
E3 as an elasticity: shift per EUR of expected price = b / beta_fs (beta_fs = -1.963 EUR per GW, step 1), times
mean price / mean q_a50. Negative = buyers bid for more when they expect a lower price.

Gates (design): G1 F >= 50 (step 1: 501). G2 weather: (a) the weather-exposed sample must not respond more than
process, (b) placebos: the wind forecast for D+7 and realised wind on D-7 (ESIOS 1159, summed over provinces) must
not move q_D (|t| < 2); (c) the provincial wind check needs each consumer's site, which the registry does not hold:
not run. G3 power: 2.8 se(E3) < |E2| (E2 = 0.364, process, step 1). G4: sign of b survives dropping each top-5 unit.
G5: if total purchases offset >= 50% of the auction (q_cleared) response, it is re-routing.
"""
from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
T = ROOT / "outputs" / "tables"
A, B = "2019-01-01", "2021-06-30"
BETA_FS, E2_PROCESS = -1.963, 0.364
OUTCOMES = ["q_a50", "q_a20", "q_a80", "q_offered", "q_cleared", "total_buy_mw"]


def esios_daily(i: int) -> pd.Series:
    d = pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet", columns=["value", "datetime"])
    return d.groupby(d.datetime.str[:10]).value.mean() / 1e3


def days() -> pd.DataFrame:
    d = pd.DataFrame({"W": esios_daily(1777), "dem": esios_daily(1775)})
    d.index = pd.to_datetime(d.index)
    t = pd.read_parquet(ROOT / "data/weather/temperature_population_index.parquet")
    t["date"] = t.utc_timestamp.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize()
    d = d.join(t.groupby("date")[["temp_pop_es", "cdh_es", "hdh_es"]].mean())
    h = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    h = h[h.area != "PT"]
    d["hol"] = h.groupby("date").area.nunique().reindex(d.index).fillna(0) / h.area.nunique()
    m = pd.read_parquet(ROOT / "data/esios/esios_measured_generation_province.parquet",
                        columns=["indicator_id", "value", "datetime"])
    m = m[m.indicator_id == 1159]
    real = m.groupby(m.datetime.str[:13]).value.sum()
    real = real.groupby(real.index.str[:10]).mean() / 1e3
    real.index = pd.to_datetime(real.index)
    d["W_lead7"] = d.W.shift(-7, freq="D").reindex(d.index)
    d["R_lag7"] = real.shift(7, freq="D").reindex(d.index)
    return d


def panel() -> pd.DataFrame:
    cols = ["date", "unit", "p"] + OUTCOMES
    fs = [f for f in sorted(glob.glob(str(T / "direct_consumer_panel/panel_*.parquet")))
          if "201901" <= Path(f).stem[-6:] <= "202106"]
    h = pd.concat(pd.read_parquet(f, columns=cols) for f in fs)
    h = h.groupby(["unit", "date"], as_index=False).mean()
    h["date"] = pd.to_datetime(h.date)
    reg = pd.read_parquet(ROOT / "data/omie/registry/direct_consumers.parquet", columns=["unit", "kind", "sample"])
    return h.merge(reg[reg.kind.isin(["own", "represented"])], on="unit")


def demean(x: pd.DataFrame, fe: list[str], cols: list[str]) -> pd.DataFrame:
    x = x.copy()
    for _ in range(30):
        for f in fe:
            x[cols] = x[cols] - x.groupby(f, observed=True)[cols].transform("mean")
    return x


def reg(x: pd.DataFrame, y: str, xs: list[str]) -> tuple[float, float]:
    """Coefficient and week-clustered se on xs[0]."""
    x = x.dropna(subset=[y] + xs)
    z = demean(x, ["uym", "wd"], [y] + xs)
    X, Y = z[xs].to_numpy(), z[y].to_numpy()
    XtXi = np.linalg.inv(X.T @ X)
    b = XtXi @ X.T @ Y
    e = Y - X @ b
    S = pd.DataFrame(X * e[:, None]).groupby(x.week.to_numpy()).sum().to_numpy()
    G = len(S)
    V = XtXi @ (S.T @ S) @ XtXi * G / (G - 1)
    return b[0], np.sqrt(V[0, 0])


CTRL = ["dem", "temp_pop_es", "cdh_es", "hdh_es", "hol"]


def main() -> int:
    d = days()
    h = panel().merge(d, left_on="date", right_index=True)
    h["uym"] = h.unit + h.date.dt.strftime("%Y%m")
    h["wd"] = h.date.dt.weekday
    h["week"] = h.date.dt.strftime("%G%V")
    rows = []

    def run(name, x, y, xs=("W",)):
        b, se = reg(x, y, list(xs) + CTRL)
        el = b / BETA_FS * x.p.mean() / x[y].mean() if y.startswith("q_a") else np.nan
        rows.append(dict(test=name, outcome=y, regressor=xs[0], units=x.unit.nunique(), n=len(x), mean_y=x[y].mean(),
                         b=b, se=se, t=b / se, elasticity=el, el_se=abs(se / BETA_FS * x.p.mean() / x[y].mean())))

    proc = h[h["sample"] == "process"]
    for y in OUTCOMES:
        run("main_process", proc, y)
    for s in ("weather_exposed", "unclassified"):
        run(f"G2a_{s}", h[h["sample"] == s], "q_a50")
    run("G2b_lead7", proc, "q_a50", ("W_lead7", "W"))
    run("G2b_lag7_realised", proc, "q_a50", ("R_lag7", "W"))
    top5 = proc.groupby("unit").q_a50.mean().sort_values(ascending=False).index[:5]
    for u in top5:
        run(f"G4_drop_{u}", proc[proc.unit != u], "q_a50")
    run("G4_drop_all_top5", proc[~proc.unit.isin(top5)], "q_a50")
    o = pd.DataFrame(rows)
    o.to_csv(T / "direct_consumer_curve_shift.csv", index=False)
    pd.set_option("display.width", 220)
    print(o.round(4).to_string(index=False))

    m = o.set_index(["test", "outcome"])
    main_ = m.loc[("main_process", "q_a50")]
    print("\nGATES")
    print(f"G1 first stage F 501 (step 1): pass")
    wx = m.loc[("G2a_weather_exposed", "q_a50")]
    print(f"G2a weather-exposed elasticity {wx.elasticity:.3f} vs process {main_.elasticity:.3f}: "
          f"{'pass' if abs(wx.elasticity) <= abs(main_.elasticity) else 'FAIL'}")
    for t_ in ("G2b_lead7", "G2b_lag7_realised"):
        r = m.loc[(t_, "q_a50")]
        print(f"{t_}: t {r.t:.2f}: {'pass' if abs(r.t) < 2 else 'FAIL'}")
    print("G2c provincial wind: not run (no consumer locations)")
    print(f"G3 power: 2.8 x se(E3) = {2.8 * main_.el_se:.3f} vs |E2| {E2_PROCESS}: "
          f"{'pass' if 2.8 * main_.el_se < E2_PROCESS else 'FAIL'}")
    signs = np.sign(o[o.test.str.startswith("G4")].b)
    print(f"G4 sign survives dropping top-5 units: {'pass' if (signs == np.sign(main_.b)).all() else 'FAIL'}")
    cl, tb = m.loc[("main_process", "q_cleared")].b, m.loc[("main_process", "total_buy_mw")].b
    off = 1 - tb / cl if cl else np.nan
    print(f"G5 auction response {cl:.3f} MW/GW, total purchases {tb:.3f}: offset {off:.0%}: "
          f"{'pass' if off < 0.5 else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
