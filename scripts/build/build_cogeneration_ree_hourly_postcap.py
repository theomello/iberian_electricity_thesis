"""Hourly schedule stages of REE's cogeneration programming units, post-cap days (2022-06-15 -> 2023-03-31).

Per day, per unit, per hour: p48_mwh (sheet I90DIA02, quarter-hourly from June 2022: four quarters summed), pdbf_mwh (I90DIA26),
pvp_mwh (I90DIA01), phfc_mwh (I90DIA36), all hourly except P48. DST days (2022-10-30, 2023-03-26) out. Writes
outputs/tables/cogeneration_ree/hourly_postcap/h_YYYYMMDD.parquet.
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cogeneration_ree_panel import RAW, OUT, _periods, _sheet  # noqa: E402

DST = {"20221030", "20230326"}


def hourly(wb, name, keep, col):
    b = _sheet(wb, name)
    b = b[b.unit.isin(keep)]
    per = _periods(b)
    n = len(per)
    if n not in (24, 96):
        return None
    v = b[per].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    v.columns = range(n)
    v["unit"] = b.unit.values
    long = v.groupby("unit").sum().stack().rename(col).reset_index().rename(columns={"level_1": "q"})
    long["hour"] = long.q // (n // 24)
    return long.groupby(["unit", "hour"], as_index=False)[col].sum()


def main():
    import xlrd
    units = pd.read_parquet(OUT / "ree_units.parquet")
    keep = set(units[units.fuel.notna()].unit)
    (OUT / "hourly_postcap").mkdir(exist_ok=True)
    files = [f for f in sorted(RAW.glob("I90DIA_*.zip")) if "20220615" <= f.stem[7:15] <= "20230331" and f.stem[7:15] not in DST]
    for i, f in enumerate(files):
        o = OUT / "hourly_postcap" / f"h_{f.stem[7:15]}.parquet"
        if o.exists():
            continue
        z = zipfile.ZipFile(f)
        wb = xlrd.open_workbook(file_contents=z.read(z.namelist()[0]), on_demand=True)
        parts = [hourly(wb, s, keep, c) for s, c in (("I90DIA02", "p48_mwh"), ("I90DIA26", "pdbf_mwh"), ("I90DIA01", "pvp_mwh"), ("I90DIA36", "phfc_mwh"))]
        if any(p is None for p in parts):
            print("skip", f.stem[7:15], flush=True)
            continue
        out = parts[0]
        for p in parts[1:]:
            out = out.merge(p, on=["unit", "hour"], how="outer")
        out = out.fillna(0.0)
        out.insert(0, "date", f.stem[7:11] + "-" + f.stem[11:13] + "-" + f.stem[13:15])
        out.to_parquet(o, index=False)
        if i % 40 == 0:
            print(f.stem[7:15], i + 1, "of", len(files), flush=True)


if __name__ == "__main__":
    main()
