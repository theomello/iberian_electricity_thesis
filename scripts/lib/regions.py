"""Country and region of a coordinate in Spain or Portugal, from Eurostat's NUTS 2021.

    from regions import locate
    r = locate(lat, lon)        # nuts_id, country, region, esios_geo_id, how

Needs data/gisco/nuts2_iberia.parquet (`fetch/fetch_gisco_nuts.py`). NUTS level 2 is
Spain's autonomous communities and Portugal's seven regions; `esios_geo_id` is the
region's id in ESIOS's installed capacity by region (Spain only, 19 regions).

A point inside a region polygon gets it (`how` = "inside"). At 1:1 million a coastline
sits within about a kilometre of the true line, so a point outside every polygon but
within NEAR_DEG of one gets the nearest ("near": coastal turbines, a few on the
Miño and Guadiana banks). Anything farther is left blank ("outside": France, Morocco,
offshore).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from shapely import STRtree

ROOT = Path(__file__).resolve().parent.parent.parent
NUTS = ROOT / "data/gisco/nuts2_iberia.parquet"
NEAR_DEG = 0.05          # about 5.5 km north-south and 4 km east-west at 40 N
ESIOS_GEO = {"ES61": 4, "ES24": 5, "ES13": 6, "ES42": 7, "ES41": 8, "ES51": 9, "ES21": 10, "ES12": 11,
             "ES63": 12, "ES30": 13, "ES22": 14, "ES52": 15, "ES43": 16, "ES11": 17, "ES53": 18, "ES70": 19,
             "ES23": 20, "ES62": 21, "ES64": 8746}


def locate(lat, lon) -> pd.DataFrame:
    """One row per point, in input order: nuts_id, country, region, esios_geo_id, how."""
    if not NUTS.exists():
        raise SystemExit(f"{NUTS.relative_to(ROOT)} is missing: run scripts/fetch/fetch_gisco_nuts.py")
    n = pd.read_parquet(NUTS)
    polys = shapely.from_wkb(n.wkb.to_numpy())
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    pts = shapely.points(lon, lat)
    idx = np.full(len(pts), -1)
    how = np.full(len(pts), "outside", dtype=object)
    ok = ~(np.isnan(lat) | np.isnan(lon))
    tree = STRtree(polys)
    p, g = tree.query(pts[ok], predicate="intersects")
    sel = np.flatnonzero(ok)
    idx[sel[p]] = g
    how[sel[p]] = "inside"
    rest = np.flatnonzero(ok & (idx < 0))
    if len(rest):
        p, g = tree.query_nearest(pts[rest], max_distance=NEAR_DEG, all_matches=False)
        idx[rest[p]] = g
        how[rest[p]] = "near"
    how[~ok] = "no coordinates"
    take = idx >= 0
    out = pd.DataFrame({"nuts_id": pd.Series(np.where(take, n.nuts_id.to_numpy()[idx], None), dtype="string"),
                        "country": pd.Series(np.where(take, n.country.to_numpy()[idx], None), dtype="string"),
                        "region": pd.Series(np.where(take, n.name.to_numpy()[idx], None), dtype="string"),
                        "how": how})
    out["esios_geo_id"] = out.nuts_id.map(ESIOS_GEO).astype("Int64")
    return out
