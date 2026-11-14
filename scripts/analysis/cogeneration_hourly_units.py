"""Who responds within the day? Unit-level and subtype probe of the hourly cogeneration price response (note rq-cogeneration.md, C3).

Same set-up as cogeneration_hourly.py (hourly price instrumented with the hourly wind forecast, date, hour x month and hour x weekday
effects). The fitted price is orthogonal to the effects, so a unit's coefficient is p_hat . y_unit / (p_hat . p_tilde). Reports, per fuel
group and biomass subtype (Biogas, Biomasa, Residuos varios, Residuos domesticos): the capacity-weighted coefficient, the number of
units, the share of units with a positive coefficient, the units' distribution, and the five biggest contributors' share of the
group's response. With --pdbf, the same on the day-ahead base schedule (PDBF) instead of the final schedule (P48).
Writes outputs/tables/cogeneration_hourly_units{,_pdbf}.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cogeneration_hourly import hourly_drivers  # noqa: E402
from cogeneration_price_response import OUT  # noqa: E402


def load(pdbf):
    sub, col = ("hourly_pdbf", "pdbf_mwh") if pdbf else ("hourly", "p48_mwh")
    d = pd.concat(pd.read_parquet(f) for f in sorted((OUT / "cogeneration_ree" / sub).glob("h_*.parquet")))
    d["date"] = pd.to_datetime(d.date)
    return d.rename(columns={col: "mwh"})


def main(pdbf=False):
    u = pd.read_parquet(OUT / "cogeneration_ree" / "ree_units.parquet")
    u = u[u.fuel.notna()].copy()
    u["cap"] = u.max_power_mw.where(u.max_power_mw > 0, u.peak_mw)
    u = u[u.cap > 0].set_index("unit")
    d = load(pdbf)
    d = d[d.unit.isin(u.index)]
    d["mw"] = np.minimum(d.mwh.clip(lower=0), d.unit.map(u.cap))
    wide = d.pivot_table(index=["date", "hour"], columns="unit", values="mw", aggfunc="sum").fillna(0.0)
    dv = hourly_drivers().set_index(["date", "hour"])
    M = wide.join(dv, how="inner").reset_index()
    key = M.date
    W = pd.concat([pd.get_dummies(M.hour.astype(str) + "_" + M.date.dt.month.astype(str), dtype=float),
                   pd.get_dummies(M.hour.astype(str) + "_" + M.date.dt.dayofweek.astype(str), dtype=float)], axis=1).to_numpy()
    Wd = W - pd.DataFrame(W).groupby(key.to_numpy()).transform("mean").to_numpy()
    res = {}
    for c in ("price", "wind"):
        v = (M[c] - M.groupby(key)[c].transform("mean")).to_numpy()
        res[c] = v - Wd @ np.linalg.lstsq(Wd, v, rcond=None)[0]
    z, p = res["wind"], res["price"]
    ph = (z @ p) / (z @ z) * z
    den = ph @ p
    rows = []
    for unit in wide.columns:
        y = M[unit].to_numpy()
        rows.append(dict(unit=unit, b10=10 * (ph @ y) / den, mean_mw=y.mean(), cap=u.cap[unit], fuel=u.fuel[unit], tech=u.tech[unit]))
    r = pd.DataFrame(rows)
    r["per_cap"] = r.b10 / r.cap  # change in load factor per EUR 10
    r["per_mean"] = r.b10 / r.mean_mw.replace(0, np.nan)
    r.round(5).to_csv(OUT / ("cogeneration_hourly_units_pdbf.csv" if pdbf else "cogeneration_hourly_units.csv"), index=False)
    out = []
    for lab, sel in (("gas", r.fuel == "gas"), ("other_fossil", r.fuel == "other_fossil"), ("biomass_waste", r.fuel == "biomass_waste"),
                     *[(f"  {t}", (r.fuel == "biomass_waste") & (r.tech == t)) for t in r[r.fuel == "biomass_waste"].tech.unique()]):
        g = r[sel & (r.mean_mw > 0.05)]
        group = g.b10.sum() / g.cap.sum()
        top5 = g.b10.abs().nlargest(5).sum() / g.b10.abs().sum()
        out.append(dict(group=lab, units=len(g), cap_mw=g.cap.sum(), group_per_cap_10eur=group, share_positive=(g.b10 > 0).mean(),
                        median_unit_per_cap=g.per_cap.median(), p10=g.per_cap.quantile(.1), p90=g.per_cap.quantile(.9), top5_share_abs=top5))
    o = pd.DataFrame(out)
    pd.set_option("display.width", 220)
    print(("PDBF" if pdbf else "P48"), "schedule\n", o.round(4).to_string(index=False))
    o.round(5).to_csv(OUT / ("cogeneration_hourly_groups_pdbf.csv" if pdbf else "cogeneration_hourly_groups.csv"), index=False)


if __name__ == "__main__":
    main("--pdbf" in sys.argv)
