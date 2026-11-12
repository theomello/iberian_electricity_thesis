#!/usr/bin/env python3
"""Hourly demand of the regulated retailers' purchase units, by area: the unit of observation of Enrich, Li, Mizrahi and Reguant (JEEM 2024).

The paper's Spanish data are REE's hourly demand of the programming units of the regulated (reference) retailers, one per distribution group (Endesa, Iberdrola, Naturgy, EDP, Repsol);
Portugal's is the regulated supplier's purchase unit (SU Eletricidade, ex EDP Servico Universal). Here: OMIE PDBF (daily operating schedule) of the same purchase units, all role codes summed,
sign flipped (purchases are negative), hourly, peninsular (the Balearic link units EE21CEB, GNSUCEB, HCURCEB, IBCUCEB are left out: a separate system).
Units (OMIE listing 'COMERCIALIZADOR ULTIMO RECURSO' purchase units, checked against ESIOS 352): EE21C01 Endesa (Energia XXI), IBCUC01 Iberdrola (Curenergia), GNSUC01 Naturgy (Comercializadora
Regulada Gas & Power), HCURC01 EDP (Baser Comercializadora de Referencia), EONUC01 Repsol (Regsiti, ex E.ON/Viesgo), CHCOC01 other (Comercializador de Referencia Energetico, ~8 MW), EDPUC2 Portugal.
Writes outputs/tables/regulated_area_panel/regulated_area_hourly.parquet (utc_timestamp, area, load_mw) and prints coverage and the comparison with ESIOS 352.
"""
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_common import day_periods_utc  # noqa: E402

UNITS = {"EE21C01": "ENDESA", "IBCUC01": "IBERDROLA", "GNSUC01": "NATURGY", "HCURC01": "EDP", "EONUC01": "REPSOL", "CHCOC01": "OTHER", "EDPUC2": "PORTUGAL"}
START, END = "2018-01", "2021-12"
OUT = ROOT / "outputs" / "tables" / "regulated_area_panel"


def main():
    parts = []
    for m in pd.period_range(START, END, freq="M"):
        d = pd.read_parquet(ROOT / f"data/omie/pdbf/parquet/pdbf_{m.strftime('%Y%m')}.parquet", columns=["date", "period", "unit", "schedule_mw"])
        d = d[d.unit.isin(UNITS)]
        d = d.groupby(["date", "period", "unit"], as_index=False).schedule_mw.sum()
        parts.append(d)
    d = pd.concat(parts, ignore_index=True)
    d["area"] = d.unit.map(UNITS)
    d["load_mw"] = -d.schedule_mw
    npd = d.groupby("date").period.transform("max")
    d["date"] = pd.to_datetime(d.date)
    rows = []
    for day, g in d.groupby("date"):
        n = int(g.period.max())
        ts = day_periods_utc(day.date(), n)
        g = g.assign(utc_timestamp=[ts[p - 1] for p in g.period])
        rows.append(g)
    d = pd.concat(rows, ignore_index=True)
    a = d.groupby(["utc_timestamp", "area"], as_index=False).load_mw.sum()
    a["utc_timestamp"] = pd.to_datetime(a.utc_timestamp, utc=True)
    OUT.mkdir(parents=True, exist_ok=True)
    a.to_parquet(OUT / "regulated_area_hourly.parquet", index=False)
    a["ym"] = a.utc_timestamp.dt.strftime("%Y-%m")
    mm = a.pivot_table(index="ym", columns="area", values="load_mw", aggfunc="mean")
    e = pd.read_parquet(ROOT / "data/esios/esios_352.parquet").drop_duplicates("utc_timestamp")
    e["ym"] = e.utc_timestamp.dt.strftime("%Y-%m")
    mm["Spain_sum"] = mm.drop(columns="PORTUGAL").sum(axis=1)
    mm["ESIOS_352"] = e.groupby("ym").value.mean().reindex(mm.index)
    mm["ratio"] = mm.Spain_sum / mm.ESIOS_352
    pd.set_option("display.width", 200)
    print(mm.round(2).to_string())
    cnt = a.groupby("area").size()
    print("hours per area:", cnt.to_dict(), "expected about", int((pd.Timestamp('2022-01-01', tz='UTC') - pd.Timestamp('2018-01-01', tz='UTC')).total_seconds() / 3600))


if __name__ == "__main__":
    main()
