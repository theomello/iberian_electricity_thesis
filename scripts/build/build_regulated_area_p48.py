#!/usr/bin/env python3
"""The regulated retailers' hourly demand at REE's final-schedule stage (P48, sheet I90DIA02) and day-ahead stage (PDBF, I90DIA26), from the daily I90DIA workbooks (ESIOS archive 34).

Same units as build_regulated_area_panel.py (Endesa EE21C01, Iberdrola IBCUC01, Naturgy GNSUC01, EDP HCURC01, Repsol EONUC01, other CHCOC01; Portugal's unit is not in REE's archive, so it
stays the OMIE PDBF series). Every day on disk 2018-01-01 -> 2021-12-31. Sign flipped (purchases negative). Hours are Madrid local hours as REE's columns label them (the autumn repeated hour is
summed into one, the spring skipped hour is absent). Writes outputs/tables/regulated_area_panel/regulated_area_p48_hourly.parquet: date, hour, area, p48_mwh, pdbf_mwh.
"""
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "fetch"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import fetch_esios_i90 as F  # noqa: E402

UNITS = {"EE21C01": "ENDESA", "IBCUC01": "IBERDROLA", "GNSUC01": "NATURGY", "HCURC01": "EDP", "EONUC01": "REPSOL", "CHCOC01": "OTHER"}
OUT = ROOT / "outputs" / "tables" / "regulated_area_panel" / "regulated_area_p48_hourly.parquet"


def one_day(f):
    import xlrd
    day = pd.Timestamp(f.stem[7:15])
    try:
        z = zipfile.ZipFile(f)
        names = z.namelist()
        wb = xlrd.open_workbook(file_contents=z.read(names[0]), on_demand=True) if names[0].endswith(".xls") else None
        out = []
        for what in ("p48", "pdbf"):
            rows = F.rows_of(z, F.SHEETS[what], day, wb)
            if rows is None:
                return day, None, "sheet missing"
            d = F.read_sheet(rows, what)
            d = d[d.unit.isin(UNITS)].groupby(["unit", "hour"], as_index=False).mw.sum()
            out.append(d.rename(columns={"mw": f"{what}_mwh"}).set_index(["unit", "hour"]))
        r = out[0].join(out[1], how="outer").reset_index().assign(date=day)
        return day, r, ""
    except Exception as e:  # noqa: BLE001
        return day, None, repr(e)[:120]


def main():
    files = [f for f in sorted(F.RAW.glob("I90DIA_*.zip")) if "20180101" <= f.stem[7:15] <= "20211231"]
    print(len(files), "days", flush=True)
    res = Parallel(n_jobs=4, verbose=2)(delayed(one_day)(f) for f in files)
    bad = [(d.date(), m) for d, r, m in res if r is None]
    d = pd.concat([r for _, r, _ in res if r is not None], ignore_index=True)
    d["area"] = d.unit.map(UNITS)
    d[["p48_mwh", "pdbf_mwh"]] = -d[["p48_mwh", "pdbf_mwh"]]
    d = d[["date", "hour", "area", "p48_mwh", "pdbf_mwh"]].sort_values(["date", "hour", "area"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(d):,} rows, {d.date.nunique()} days; failed days: {len(bad)}", bad[:10])
    d["ym"] = d.date.dt.strftime("%Y-%m")
    m = d.groupby(["ym", "area"])[["p48_mwh", "pdbf_mwh"]].mean().unstack("area")
    r = (m["p48_mwh"] / m["pdbf_mwh"]).round(3)
    print("P48 / PDBF monthly ratio by area:\n", r.iloc[::6].to_string())


if __name__ == "__main__":
    main()
