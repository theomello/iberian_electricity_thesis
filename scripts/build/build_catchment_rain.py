#!/usr/bin/env python3
"""Daily rain over the upstream catchment of every hydro plant in Spain and Portugal.

    .venv/bin/python scripts/fetch/fetch_hydrobasins.py          # input: sub-basins
    .venv/bin/python scripts/fetch/fetch_eobs_precipitation.py   # input: rain grid
    .venv/bin/python scripts/build/build_catchment_rain.py

For the own-basin rainfall design (notes/rq-hydro-rain-first-stage.md): rain in a
firm's own catchments moves its hydro output, and so its net position, for reasons
it does not choose. This builds that rain, complete, for all 387 plants of the JRC
Hydro-power database (`jrc_hydro_plants.parquet`, 342 Spanish, 45 Portuguese).

CATCHMENT. A plant sits in one HydroBASINS level-12 sub-basin (point in polygon;
a plant on a coast or border off every polygon takes the nearest one within 5 km).
Its catchment is that sub-basin plus every sub-basin draining into it, following
NEXT_DOWN upstream, less endorheic sub-basins (ENDO > 0): closed lagoons such as
Gallocanta and the Monegros carry a NEXT_DOWN link but their water never reaches the
river (697 km2 of them upstream of Mequinenza on the Ebro). The area must then equal
HydroBASINS' own UP_AREA for the sub-basin, which `qa/check_catchment_rain.py` checks.

RAIN. Each sub-basin's overlap with each 0.25-degree E-OBS cell is computed once,
in km2 (degree area x cos latitude x 111.32^2), keeping only cells E-OBS reports. A
catchment's weight on a cell is the sum of its sub-basins' overlaps, and its daily
rain is the weighted mean of the cells' rain, so a catchment smaller than a cell
still gets the cells it touches, in proportion.

OUTPUTS (data/eobs/, gitignored like all of data/):
  plant_catchments.parquet  plant_id, name, type, country, capacity_mw, lat, lon,
                            hybas_id, snapped_km (0 unless snapped), n_subbasins,
                            catch_km2, up_area_km2 (HydroBASINS), n_cells
  catchment_cells.parquet   plant_id, lat, lon, weight (km2 of the catchment in the cell)
  catchment_rain_daily.parquet  plant_id, date, rr (mm/day), 1991-01-01 onwards

The plant's location is JRC's; for a derivation plant that may be the powerhouse
rather than the dam, which adds the sub-basins between the two to the catchment.
"""
from __future__ import annotations

import sys
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Point, box

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
BASINS = DATA / "hydrosheds/hybas_iberia_lev12.parquet"
GRID = DATA / "eobs/eobs_rr_iberia_daily.parquet"
PLANTS = DATA / "jrc_hydro/jrc_hydro_plants.parquet"
CATCH = DATA / "eobs/plant_catchments.parquet"
WEIGHTS = DATA / "eobs/catchment_cells.parquet"
RAIN = DATA / "eobs/catchment_rain_daily.parquet"
HALF = 0.125           # half a 0.25-degree cell
KM_PER_DEG = 111.32
SNAP_KM = 5.0


def upstream(net: pd.DataFrame, start: int) -> set[int]:
    """The sub-basin `start` and every sub-basin draining into it (HYBAS_ID / NEXT_DOWN).
    With an ENDO column, endorheic sub-basins other than `start` are left out."""
    up = defaultdict(list)
    for h, nd in zip(net.HYBAS_ID, net.NEXT_DOWN):
        up[nd].append(h)
    seen, q = {start}, deque([start])
    while q:
        for c in up.get(q.popleft(), []):
            if c not in seen:
                seen.add(c)
                q.append(c)
    if "ENDO" in net:
        endo = set(net.loc[net.ENDO > 0, "HYBAS_ID"]) - {start}
        seen -= endo
    return seen


def locate(plants: pd.DataFrame, geoms, ids: np.ndarray) -> pd.DataFrame:
    """plant -> the level-12 sub-basin containing it, else the nearest within SNAP_KM."""
    tree = shapely.STRtree(geoms)
    out = []
    for p in plants.itertuples():
        pt = Point(p.lon, p.lat)
        hit = [i for i in tree.query(pt) if geoms[i].covers(pt)]
        if hit:
            out.append((p.id, int(ids[hit[0]]), 0.0))
            continue
        j = tree.nearest(pt)
        km = geoms[j].distance(pt) * KM_PER_DEG * np.cos(np.radians(p.lat))
        out.append((p.id, int(ids[j]) if km <= SNAP_KM else None, round(float(km), 2)))
    return pd.DataFrame(out, columns=["plant_id", "hybas_id", "snapped_km"])


def overlaps(geoms, ids: np.ndarray, cells: pd.DataFrame) -> pd.DataFrame:
    """hybas_id, lat, lon, km2: each sub-basin's area inside each reported cell."""
    boxes = [box(lo - HALF, la - HALF, lo + HALF, la + HALF) for la, lo in zip(cells.lat, cells.lon)]
    tree = shapely.STRtree(boxes)
    rows = []
    for g, h in zip(geoms, ids):
        for k in tree.query(g):
            a = g.intersection(boxes[k]).area
            if a > 0:
                la, lo = cells.lat.iat[k], cells.lon.iat[k]
                rows.append((int(h), la, lo, a * KM_PER_DEG ** 2 * np.cos(np.radians(la))))
    return pd.DataFrame(rows, columns=["hybas_id", "lat", "lon", "km2"])


def main() -> int:
    b = pd.read_parquet(BASINS)
    geoms = shapely.from_wkb(b.wkb.to_numpy())
    ids = b.HYBAS_ID.to_numpy()
    plants = pd.read_parquet(PLANTS)
    loc = locate(plants, geoms, ids)
    print(f"{len(plants)} plants: {(loc.snapped_km == 0).sum()} inside a sub-basin, "
          f"{((loc.snapped_km > 0) & loc.hybas_id.notna()).sum()} snapped within {SNAP_KM:g} km, "
          f"{loc.hybas_id.isna().sum()} not located")

    rain = pd.read_parquet(GRID)
    cells = rain[["lat", "lon"]].drop_duplicates().reset_index(drop=True)
    ov = overlaps(geoms, ids, cells)
    print(f"sub-basin x cell overlaps: {len(ov):,} over {ov.hybas_id.nunique():,} sub-basins and {len(cells)} cells")

    area = dict(zip(b.HYBAS_ID, b.SUB_AREA))
    up_area = dict(zip(b.HYBAS_ID, b.UP_AREA))
    catch_rows, weight_rows = [], []
    memo: dict[int, set[int]] = {}
    for p, l in zip(plants.itertuples(), loc.itertuples()):
        row = {"plant_id": p.id, "name": p.name, "type": p.type, "country": p.country_code,
               "capacity_mw": p.installed_capacity_MW, "lat": p.lat, "lon": p.lon,
               "hybas_id": l.hybas_id, "snapped_km": l.snapped_km}
        if pd.isna(l.hybas_id):
            catch_rows.append(row)
            continue
        h = int(l.hybas_id)
        if h not in memo:
            memo[h] = upstream(b[["HYBAS_ID", "NEXT_DOWN", "ENDO"]], h)
        ups = memo[h]
        w = ov[ov.hybas_id.isin(ups)].groupby(["lat", "lon"]).km2.sum().reset_index()
        weight_rows.append(w.assign(plant_id=p.id).rename(columns={"km2": "weight"}))
        catch_rows.append(row | {"n_subbasins": len(ups), "catch_km2": sum(area[u] for u in ups),
                                 "up_area_km2": up_area[h], "n_cells": len(w)})
    catch = pd.DataFrame(catch_rows)
    wts = pd.concat(weight_rows, ignore_index=True)[["plant_id", "lat", "lon", "weight"]]
    CATCH.parent.mkdir(parents=True, exist_ok=True)
    catch.to_parquet(CATCH, index=False)
    wts.to_parquet(WEIGHTS, index=False)

    # Daily rain: weighted mean over each catchment's cells. Pivot the grid once.
    grid = rain.pivot_table(index="date", columns=["lat", "lon"], values="rr")
    out = []
    for pid, g in wts.groupby("plant_id"):
        cols = list(zip(g.lat, g.lon))
        m = grid[cols].to_numpy()
        wv = g.weight.to_numpy()
        ok = ~np.isnan(m)
        rr = (np.where(ok, m, 0.0) @ wv) / (np.where(ok, 1.0, 0.0) @ wv)
        out.append(pd.DataFrame({"plant_id": pid, "date": grid.index, "rr": rr.astype("float32")}))
    r = pd.concat(out, ignore_index=True)
    r.to_parquet(RAIN, index=False)
    print(f"wrote {CATCH.relative_to(ROOT)} ({len(catch)} plants), {WEIGHTS.relative_to(ROOT)} ({len(wts):,} "
          f"plant-cells), {RAIN.relative_to(ROOT)} ({len(r):,} plant-days)")
    big = catch.sort_values("catch_km2", ascending=False).head(5)[["name", "country", "catch_km2", "n_cells"]]
    print("largest catchments:\n" + big.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
