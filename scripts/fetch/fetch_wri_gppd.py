#!/usr/bin/env python3
"""Fetch WRI's Global Power Plant Database and keep Spain and Portugal.

    .venv/bin/python scripts/fetch/fetch_wri_gppd.py

A second source of wind and solar farm locations beside OpenStreetMap
(`fetch_osm_renewables.py`), for `build/build_renewable_locations.py`. GPPD v1.3.0
(Byers et al., World Resources Institute, 2021; CC BY 4.0) gives each plant's name,
capacity, fuel, coordinates and, for some, owner. It predates most of Spain's solar
build-out: 243 Spanish solar plants (4.9 GW) and 342 wind farms (11.3 GW, about a third
of REE's wind); for Portugal 224 wind farms (4.9 GW).

The CSV (12 MB) is cached in data/wri/raw/ and not re-downloaded.
OUTPUT: data/wri/wri_gppd_iberia.parquet, one row per plant (country ESP or PRT).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, session  # noqa: E402

URL = ("https://raw.githubusercontent.com/wri/global-power-plant-database/master/"
       "output_database/global_power_plant_database.csv")
RAW = DATA / "wri/raw/global_power_plant_database.csv"
OUT = DATA / "wri/wri_gppd_iberia.parquet"


def main() -> int:
    if not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        r = session().get(URL, timeout=300)
        r.raise_for_status()
        RAW.write_bytes(r.content)
    g = pd.read_csv(RAW, low_memory=False)
    g = g[g.country.isin(["ESP", "PRT"])][["country", "name", "gppd_idnr", "capacity_mw", "latitude", "longitude",
                                          "primary_fuel", "commissioning_year", "owner", "source"]]
    g.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(DATA.parent)}: {len(g):,} plants")
    print(g.groupby(["country", "primary_fuel"]).agg(n=("name", "size"), mw=("capacity_mw", "sum")).round(0).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
