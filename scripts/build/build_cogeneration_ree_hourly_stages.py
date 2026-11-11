"""Hourly schedule stages of REE's cogeneration programming units between the day-ahead and the final schedule.

I90DIA sheets (2021-22 layout): 26 PBF (day-ahead base, already extracted), 01 PVP (after day-ahead technical constraints),
36 PHFC (after the intraday auctions and the continuous market), 02 P48 (after real-time constraints, balancing energy, tertiary and
transfers between balance-responsible parties; already extracted). Same days and units as build_cogeneration_ree_hourly.py, DST days
out. Writes outputs/tables/cogeneration_ree/hourly_stages/h_YYYYMMDD.parquet: date, unit, hour, pvp_mwh, phfc_mwh.
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_cogeneration_ree_panel import RAW, OUT, _periods, _sheet  # noqa: E402


def stage(wb, name, keep, col):
    b = _sheet(wb, name)
    b = b[b.unit.isin(keep)]
    per = _periods(b)
    if len(per) != 24:
        return None
    v = b[per].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    v.columns = range(24)
    v["unit"] = b.unit.values
    return v.groupby("unit").sum().stack().rename(col).reset_index().rename(columns={"level_1": "hour"})


def main():
    import xlrd
    units = pd.read_parquet(OUT / "ree_units.parquet")
    keep = set(units[units.fuel.notna()].unit)
    (OUT / "hourly_stages").mkdir(exist_ok=True)
    days = {f.stem[2:] for f in (OUT / "hourly").glob("h_*.parquet")}
    files = [f for f in sorted(RAW.glob("I90DIA_*.zip")) if f.stem[7:15] in days]
    for i, f in enumerate(files):
        o = OUT / "hourly_stages" / f"h_{f.stem[7:15]}.parquet"
        if o.exists():
            continue
        z = zipfile.ZipFile(f)
        wb = xlrd.open_workbook(file_contents=z.read(z.namelist()[0]), on_demand=True)
        a, b = stage(wb, "I90DIA01", keep, "pvp_mwh"), stage(wb, "I90DIA36", keep, "phfc_mwh")
        if a is None or b is None:
            print("skip", f.stem[7:15], flush=True)
            continue
        out = a.merge(b, on=["unit", "hour"], how="outer").fillna(0.0)
        out.insert(0, "date", f.stem[7:11] + "-" + f.stem[11:13] + "-" + f.stem[13:15])
        out.to_parquet(o, index=False)
        if i % 40 == 0:
            print(f.stem[7:15], i + 1, "of", len(files), flush=True)


if __name__ == "__main__":
    main()
