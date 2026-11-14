"""Hourly within-day cogeneration price response by window: pre-cap, cap (outside the subsidy), opt-in (notes/rq-cogeneration.md).

Windows: pre-cap 2021-01-01 -> 2022-06-14 (hourly P48 in outputs/.../hourly), cap 2022-06-15 -> 2022-09-30 and opt-in 2022-10-01 ->
2023-03-31 (outputs/.../hourly_postcap, P48 quarter-hours summed to hours). Groups: gas, large biomass and waste (20 MW and over),
small biomass and waste (under 20 MW). Specification of cogeneration_hourly.py (hourly price moved by the hourly wind forecast, date,
hour x month, hour x weekday effects, clustered by week). Difference from the pre-cap coefficient = the windows' difference with
independent standard errors. Shifted-price placebo (20 shifts, +-10 days) for each group and window. Writes
outputs/tables/cogeneration_postcap_hourly.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cogeneration_hourly import fit, hourly_drivers, shifted  # noqa: E402
from cogeneration_price_response import OUT  # noqa: E402

REE = OUT / "cogeneration_ree"
WINDOWS = [("pre-cap 2021-01 -> 2022-06-14", "2021-01-01", "2022-06-14"), ("cap 2022-06-15 -> 2022-09-30", "2022-06-15", "2022-09-30"),
           ("opt-in 2022-10-01 -> 2023-03-31", "2022-10-01", "2023-03-31")]


def main():
    u = pd.read_parquet(REE / "ree_units.parquet")
    u = u[u.fuel.notna()].copy()
    u["cap"] = u.max_power_mw.where(u.max_power_mw > 0, u.peak_mw)
    u = u[u.cap > 0].set_index("unit")
    pre = pd.concat(pd.read_parquet(f) for f in sorted((REE / "hourly").glob("h_*.parquet")))
    post = pd.concat(pd.read_parquet(f, columns=["date", "unit", "hour", "p48_mwh"]) for f in sorted((REE / "hourly_postcap").glob("h_*.parquet")))
    h = pd.concat([pre, post])
    h["date"] = pd.to_datetime(h.date)
    h = h[h.unit.isin(u.index)]
    h["mw"] = np.minimum(h.p48_mwh.clip(lower=0), h.unit.map(u.cap))
    groups = {"gas": u.fuel == "gas", "large biomass and waste (20 MW and over)": (u.fuel == "biomass_waste") & (u.cap >= 20),
              "small biomass and waste (under 20 MW)": (u.fuel == "biomass_waste") & (u.cap < 20)}
    dv = hourly_drivers()
    rows = []
    for gname, sel in groups.items():
        units = u.index[sel]
        g = h[h.unit.isin(units)]
        lf_all = g.groupby(["date", "hour"]).mw.sum().div(u.cap[units].sum()).rename("lf").reset_index()
        for wname, lo, hi in WINDOWS:
            lf = lf_all[(lf_all.date >= lo) & (lf_all.date <= hi)]
            M = lf.merge(dv, on=["date", "hour"], how="inner")
            wk = pd.Series(M.date.dt.to_period("W").astype(str).factorize()[0], index=M.index)
            r = fit(M, "lf", wk)
            row = dict(group=gname, window=wname, days=M.date.nunique(), **r)
            sh = []
            for k in [j for j in range(-10, 11) if j != 0]:
                Ms = lf.merge(shifted(dv, k), on=["date", "hour"], how="inner")
                rs = fit(Ms, "lf", pd.Series(Ms.date.dt.to_period("W").astype(str).factorize()[0], index=Ms.index))
                if rs:
                    sh.append(rs["coef_per_10eur"])
            sh = pd.Series(sh)
            row.update(shift_median=sh.median(), shift_p05=sh.quantile(.05), shift_p95=sh.quantile(.95), rank_of_real=int((sh.abs() >= abs(r["coef_per_10eur"])).sum()) + 1)
            rows.append(row)
            print({k: (round(float(v), 4) if not isinstance(v, str) else v) for k, v in row.items()}, flush=True)
    r = pd.DataFrame(rows)
    pre_ = r[r.window.str.startswith("pre")].set_index("group")
    r["diff_from_pre"] = r.coef_per_10eur - r.group.map(pre_.coef_per_10eur)
    r["se_diff"] = np.sqrt(r.se ** 2 + r.group.map(pre_.se) ** 2)
    r.round(5).to_csv(OUT / "cogeneration_postcap_hourly.csv", index=False)
    pd.set_option("display.width", 220)
    print(r[["group", "window", "days", "coef_per_10eur", "se", "t", "F", "diff_from_pre", "se_diff", "rank_of_real"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
