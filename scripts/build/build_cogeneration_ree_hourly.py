"""Hourly final schedule (P48, sheet I90DIA02) of REE's cogeneration programming units, pre-cap window.

Same workbooks and unit filter as build_cogeneration_ree_panel.py, but keeps the hour. Days 2021-01-01 -> 2022-06-14 on disk (the
pre-cap window), DST days skipped (the column position then is not the clock hour). Writes
outputs/tables/cogeneration_ree/hourly/h_YYYYMMDD.parquet: date, unit, hour (0-23, local), p48_mwh.
"""
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cogeneration_ree_panel import RAW, OUT, _periods, _sheet  # noqa: E402

DST = {"20210328", "20211031", "20220327"}


def main():
    units = pd.read_parquet(OUT / "ree_units.parquet")
    keep = set(units[units.fuel.notna()].unit)
    (OUT / "hourly").mkdir(exist_ok=True)
    files = [f for f in sorted(RAW.glob("I90DIA_*.zip")) if "20210101" <= f.stem[7:15] <= "20220614" and f.stem[7:15] not in DST]
    import xlrd
    for i, f in enumerate(files):
        o = OUT / "hourly" / f"h_{f.stem[7:15]}.parquet"
        if o.exists():
            continue
        z = zipfile.ZipFile(f)
        wb = xlrd.open_workbook(file_contents=z.read(z.namelist()[0]), on_demand=True)
        p = _sheet(wb, "I90DIA02")
        p = p[p.unit.isin(keep)]
        per = _periods(p)
        if len(per) != 24:
            print("skip", f.stem[7:15], len(per), flush=True)
            continue
        v = p[per].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        v.columns = range(24)
        v["unit"] = p.unit.values
        long = v.groupby("unit").sum().stack().rename("p48_mwh").reset_index().rename(columns={"level_1": "hour"})
        long.insert(0, "date", f.stem[7:11] + "-" + f.stem[11:13] + "-" + f.stem[13:15])
        long.to_parquet(o, index=False)
        if i % 40 == 0:
            print(f.stem[7:15], i + 1, "of", len(files), flush=True)


if __name__ == "__main__":
    main()
