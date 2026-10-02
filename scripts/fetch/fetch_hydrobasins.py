#!/usr/bin/env python3
"""Fetch HydroBASINS Europe and keep the Iberian sub-basins, with their river network.

    .venv/bin/python scripts/fetch/fetch_hydrobasins.py

HydroBASINS (HydroSHEDS v1c; Lehner & Grill 2013) nests sub-basins in 12 levels.
Each polygon carries HYBAS_ID and NEXT_DOWN, the sub-basin it drains into, so a
dam's upstream catchment is the sub-basin it sits in plus everything that drains
into it. Used to average E-OBS rainfall over each hydro plant's catchment.

FILE (downloaded 2026-10-02 on the user's approval): hybas_eu_lev01-12_v1c.zip,
361 MB, from data.hydrosheds.org. Free for scientific, educational and commercial
use under the HydroSHEDS licence; cite Lehner & Grill (2013).

OUTPUT: data/hydrosheds/hybas_iberia_lev{LEVEL}.parquet for the levels in LEVELS:
HYBAS_ID, NEXT_DOWN, MAIN_BAS, SUB_AREA, UP_AREA (km2), PFAF_ID, ORDER, ENDO, and
the polygon as WKB (shapely). Iberian = the sub-basin's bounding box intersects
35.8-44.0 N, 9.6 W - 3.4 E; the river network inside the peninsula is closed, so
no catchment of a Spanish or Portuguese dam leaves the selection. The raw zip
stays in data/hydrosheds/raw/.
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import shapefile  # pyshp
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, session  # noqa: E402

URL = "https://data.hydrosheds.org/file/hydrobasins/standard/hybas_eu_lev01-12_v1c.zip"
OUT = DATA / "hydrosheds"
RAW = OUT / "raw"
ZIP = RAW / "hybas_eu_lev01-12_v1c.zip"
LEVELS = (8, 10, 12)
BBOX = (-9.6, 35.8, 3.4, 44.0)  # lon_min, lat_min, lon_max, lat_max
# ENDO: 0 not endorheic, 1 part of an endorheic basin, 2 its sink. An endorheic
# sub-basin can carry a NEXT_DOWN link while its water never reaches that river.
FIELDS = ["HYBAS_ID", "NEXT_DOWN", "MAIN_BAS", "SUB_AREA", "UP_AREA", "PFAF_ID", "ORDER", "ENDO"]


def download(sess) -> None:
    size = int(sess.head(URL, timeout=60, allow_redirects=True).headers["Content-Length"])
    if ZIP.exists() and ZIP.stat().st_size == size:
        print(f"  {ZIP.name}: on disk ({size / 1e6:.0f} MB)")
        return
    part = ZIP.with_suffix(".part")
    with sess.get(URL, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(part, "wb") as f:
            for chunk in r.iter_content(1 << 22):
                f.write(chunk)
    if part.stat().st_size != size:
        raise RuntimeError(f"got {part.stat().st_size} bytes, expected {size}")
    part.rename(ZIP)
    print(f"  {ZIP.name}: downloaded ({size / 1e6:.0f} MB)")


def level(zf: zipfile.ZipFile, lev: int) -> pd.DataFrame:
    stem = f"hybas_eu_lev{lev:02d}_v1c"
    names = {Path(n).suffix: n for n in zf.namelist() if Path(n).stem == stem}
    r = shapefile.Reader(shp=io.BytesIO(zf.read(names[".shp"])), dbf=io.BytesIO(zf.read(names[".dbf"])),
                         shx=io.BytesIO(zf.read(names[".shx"])))
    keep = []
    for rec, shp in zip(r.iterRecords(fields=FIELDS), r.iterShapes()):
        x0, y0, x1, y1 = shp.bbox
        if x1 < BBOX[0] or x0 > BBOX[2] or y1 < BBOX[1] or y0 > BBOX[3]:
            continue
        # By name: pyshp returns the requested fields in the FILE's order, not FIELDS'.
        d = rec.as_dict()
        keep.append({f: d[f] for f in FIELDS} | {"wkb": shape(shp.__geo_interface__).wkb})
    return pd.DataFrame(keep)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    download(session())
    with zipfile.ZipFile(ZIP) as zf:
        for lev in LEVELS:
            d = level(zf, lev)
            out = OUT / f"hybas_iberia_lev{lev:02d}.parquet"
            d.to_parquet(out, index=False)
            ids = set(d.HYBAS_ID)
            dangling = (~d.NEXT_DOWN.isin(ids) & (d.NEXT_DOWN != 0)).sum()
            print(f"  level {lev:2d}: {len(d):,} sub-basins, {d.SUB_AREA.sum():,.0f} km2, "
                  f"{dangling} draining outside the selection -> {out.relative_to(DATA.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
