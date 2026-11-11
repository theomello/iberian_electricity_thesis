"""Outcome-independent placebo rules for biomass and waste (notes/rq-cogeneration.md, rules set before the run).

R1: bilateral share of PDBF energy over the pre-cap days with hourly data; placebo = share >= 0.5. R2: placebo = under 20 MW.
Hourly final-schedule (P48) load factor of each group on the hourly day-ahead price moved by the hourly wind forecast (the C3
specification: date, hour x month, hour x weekday effects, clustered by week), the placebo groups also with the 20 shifted prices
(+-10 days). Gas and the other biomass group are reported for comparison. Writes outputs/tables/cogeneration_placebo_rules.csv.
"""
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cogeneration_hourly import fit, hourly_drivers, shifted  # noqa: E402
from cogeneration_price_response import OUT  # noqa: E402

REE = OUT / "cogeneration_ree"


def main():
    u = pd.read_parquet(REE / "ree_units.parquet")
    u = u[u.fuel.notna()].copy()
    u["cap"] = u.max_power_mw.where(u.max_power_mw > 0, u.peak_mw)
    u = u[u.cap > 0].set_index("unit")
    days = {f[-16:-8] for f in glob.glob(str(REE / "hourly/h_*.parquet"))}
    dd = pd.concat(pd.read_parquet(f, columns=["unit", "pdbf_mwh", "pdbf_bilateral_mwh"]) for f in sorted(glob.glob(str(REE / "days/ree_*.parquet"))) if f[-16:-8] in days)
    s = dd.groupby("unit")[["pdbf_mwh", "pdbf_bilateral_mwh"]].sum()
    u["bil"] = (s.pdbf_bilateral_mwh / s.pdbf_mwh.where(s.pdbf_mwh > 0)).reindex(u.index)
    h = pd.concat(pd.read_parquet(f) for f in sorted((REE / "hourly").glob("h_*.parquet")))
    h["date"] = pd.to_datetime(h.date)
    h = h[h.unit.isin(u.index)]
    bio = u.fuel == "biomass_waste"
    groups = {"gas": u.fuel == "gas",
              "R1 placebo: biomass, bilateral share >= 0.5": bio & (u.bil >= 0.5), "R1 other biomass (share < 0.5)": bio & (u.bil < 0.5),
              "R2 placebo: biomass under 20 MW": bio & (u.cap < 20), "R2 other biomass (20 MW and over)": bio & (u.cap >= 20),
              "all biomass and waste": bio}
    dv = hourly_drivers()
    rows = []
    for gname, sel in groups.items():
        units = u.index[sel.fillna(False)]
        g = h[h.unit.isin(units)].copy()
        g["mw"] = np.minimum(g.p48_mwh.clip(lower=0), g.unit.map(u.cap))
        lf = g.groupby(["date", "hour"]).mw.sum().div(u.cap[units].sum()).rename("lf").reset_index()
        M = lf.merge(dv, on=["date", "hour"], how="inner")
        wk = pd.Series(M.date.dt.to_period("W").astype(str).factorize()[0], index=M.index)
        r = fit(M, "lf", wk)
        row = dict(group=gname, units=len(units), cap_mw=u.cap[units].sum(), coef_per_10eur=r["coef_per_10eur"], se=r["se"], t=r["t"], F=r["F"])
        if gname.startswith("R") and "placebo" in gname:
            sh = []
            for k in [j for j in range(-10, 11) if j != 0]:
                Ms = lf.merge(shifted(dv, k), on=["date", "hour"], how="inner")
                wks = pd.Series(Ms.date.dt.to_period("W").astype(str).factorize()[0], index=Ms.index)
                rs = fit(Ms, "lf", wks)
                if rs:
                    sh.append(rs["coef_per_10eur"])
            sh = pd.Series(sh)
            row.update(shift_median=sh.median(), shift_p05=sh.quantile(.05), shift_p95=sh.quantile(.95), rank_of_real=int((sh.abs() >= abs(r["coef_per_10eur"])).sum()) + 1, n_shifts=len(sh))
        rows.append(row)
        print({k: (round(float(v), 4) if not isinstance(v, str) else v) for k, v in row.items()}, flush=True)
    pd.DataFrame(rows).round(5).to_csv(OUT / "cogeneration_placebo_rules.csv", index=False)


if __name__ == "__main__":
    main()
