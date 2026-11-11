"""Hourly day-ahead base schedule (PDBF, sheet I90DIA26, all transaction types summed) of REE's cogeneration programming units.

Companion of build_cogeneration_ree_hourly.py (P48): same days, same units, DST days out. Writes
outputs/tables/cogeneration_ree/hourly_pdbf/h_YYYYMMDD.parquet: date, unit, hour, pdbf_mwh.
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cogeneration_ree_panel import RAW, OUT, _periods, _sheet  # noqa: E402

DST = {"20210328", "20211031", "20220327"}


def main():
    import xlrd
    units = pd.read_parquet(OUT / "ree_units.parquet")
    keep = set(units[units.fuel.notna()].unit)
    (OUT / "hourly_pdbf").mkdir(exist_ok=True)
    done = {f.stem[2:] for f in (OUT / "hourly").glob("h_*.parquet")}
    files = [f for f in sorted(RAW.glob("I90DIA_*.zip")) if f.stem[7:15] in {d[2:] if False else d for d in done}]
    for i, f in enumerate(files):
        o = OUT / "hourly_pdbf" / f"h_{f.stem[7:15]}.parquet"
        if o.exists():
            continue
        wb = xlrd.open_workbook(file_contents=zipfile.ZipFile(f).read(zipfile.ZipFile(f).namelist()[0]), on_demand=True)
        b = _sheet(wb, "I90DIA26")
        b = b[b.unit.isin(keep)]
        per = _periods(b)
        if len(per) != 24:
            continue
        v = b[per].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        v.columns = range(24)
        v["unit"] = b.unit.values
        long = v.groupby("unit").sum().stack().rename("pdbf_mwh").reset_index().rename(columns={"level_1": "hour"})
        long.insert(0, "date", f.stem[7:11] + "-" + f.stem[11:13] + "-" + f.stem[13:15])
        long.to_parquet(o, index=False)
        if i % 40 == 0:
            print(f.stem[7:15], i + 1, "of", len(files), flush=True)


if __name__ == "__main__":
    main()
