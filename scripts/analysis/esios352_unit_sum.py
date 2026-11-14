"""Does ESIOS 352 (reference retailers' scheduled demand) track the PDBF purchases of the regulated suppliers' own units?

The 2019 fall in ln(352 / Portugal) is specific to 352 (docs/specs/2026-11-11-tou-replication-design.md, 3c). If the sum
of the Spanish regulated-supplier purchase units' PDBF schedules (is_pass_through owners) falls with it, the change is in
the customers or in which units are counted; if it stays flat, the change is in how ESIOS defines the series.
Monthly mean MW, 2018-01 -> 2021-09, and each unit's mean MW by year. Writes outputs/tables/esios352_unit_sum*.csv.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_owner import is_pass_through  # noqa: E402

OUT = ROOT / "outputs" / "tables"


def main():
    reg = pd.read_parquet(ROOT / "data/omie/registry/unit_registry.parquet", columns=["unit", "country", "role"])
    ag = pd.read_parquet(ROOT / "data/omie/registry/unit_agents.parquet", columns=["unit", "agent_owner", "descr"])
    u = reg.merge(ag, on="unit", how="left").drop_duplicates("unit")
    u = u[u.agent_owner.map(is_pass_through).fillna(False) & (u.country == "ES")]
    units = set(u.unit)
    parts = []
    for ym in pd.period_range("2018-01", "2021-09", freq="M"):
        d = pd.read_parquet(ROOT / f"data/omie/pdbf/parquet/pdbf_{ym.strftime('%Y%m')}.parquet", columns=["date", "period", "unit", "schedule_mw"])
        d = d[d.unit.isin(units)]
        parts.append(d)
    p = pd.concat(parts)
    p["date"] = pd.to_datetime(p.date)
    p["ym"] = p.date.dt.to_period("M")
    buy = p[p.schedule_mw < 0]
    unit_hour = buy.groupby(["unit", "date", "period"]).schedule_mw.sum().mul(-1).reset_index()
    unit_hour["year"] = unit_hour.date.dt.year
    unit_hour["ym"] = unit_hour.date.dt.to_period("M")
    tot_hour = unit_hour.groupby(["date", "period"]).schedule_mw.sum()
    m_units = tot_hour.groupby(tot_hour.index.get_level_values("date").to_period("M")).mean().rename("units_mw")
    e = pd.read_parquet(ROOT / "data/esios/esios_352.parquet")[["utc_timestamp", "value"]].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value
    e = e[(e.index >= "2018-01-01") & (e.index < "2021-10-01")]
    m352 = e.groupby(e.index.tz_convert("Europe/Madrid").tz_localize(None).to_period("M")).mean().rename("esios352_mw")
    m = pd.concat([m352, m_units], axis=1).dropna()
    m["ratio"] = m.units_mw / m.esios352_mw
    m.round(3).to_csv(OUT / "esios352_unit_sum_monthly.csv")
    pd.set_option("display.width", 200)
    print(m.round(3).to_string())
    m["year"] = m.index.year
    print(m.groupby("year")[["esios352_mw", "units_mw", "ratio"]].mean().round(3))
    ann = unit_hour.groupby(["unit", "year"]).schedule_mw.sum().unstack(fill_value=0.0)
    hrs = unit_hour.groupby("year").apply(lambda g: g[["date", "period"]].drop_duplicates().shape[0])
    ann = (ann / hrs).round(1)
    ann = ann.join(u.set_index("unit")[["agent_owner", "descr"]])
    ann.to_csv(OUT / "esios352_unit_sum_by_unit.csv")
    print(ann.sort_values(2019, ascending=False).head(15).to_string())
    for a, b in ((2018, 2019), (2019, 2020)):
        d = (ann[b] - ann[a]).sort_values()
        print(f"\nbiggest changes {a}->{b} (mean MW):\n{d.head(5).round(1).to_string()}\n{d.tail(5).round(1).to_string()}")


if __name__ == "__main__":
    main()
