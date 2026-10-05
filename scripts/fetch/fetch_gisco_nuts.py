#!/usr/bin/env python3
"""Fetch Eurostat's NUTS 2021 regions and keep Spain's and Portugal's.

    .venv/bin/python scripts/fetch/fetch_gisco_nuts.py

Gives a coordinate its country and region. The OSM files carry only a crude country
guess from a longitude cut, which calls about 1,050 Spanish border turbines
Portuguese. NUTS level 2 is Spain's autonomous communities (19, Ceuta and Melilla
included), the regions of ESIOS's installed capacity by region, and Portugal's seven
regions (Açores and Madeira included).

Source: Eurostat GISCO, NUTS 2021, 1:1 million, WGS84 (EPSG:4326), one GeoJSON for
all of Europe (18 MB), cached in data/gisco/raw/ and not re-downloaded. Attribution:
"© EuroGeographics for the administrative boundaries". At 1:1 million a coastline or
border sits within about a kilometre of the true line.

OUTPUT: data/gisco/nuts2_iberia.parquet: nuts_id, country (ES/PT), name, wkb
(shapely geometry, WGS84).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, session  # noqa: E402

URL = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2021_4326_LEVL_2.geojson"
RAW = DATA / "gisco/raw/NUTS_RG_01M_2021_4326_LEVL_2.geojson"
OUT = DATA / "gisco/nuts2_iberia.parquet"
COUNTRIES = ("ES", "PT")


def main() -> int:
    if not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        r = session().get(URL, timeout=300)
        r.raise_for_status()
        RAW.write_bytes(r.content)
    gj = json.loads(RAW.read_text(encoding="utf-8"))
    rows = []
    for f in gj["features"]:
        p = f["properties"]
        if p["CNTR_CODE"] in COUNTRIES and p["LEVL_CODE"] == 2:
            g = shape(f["geometry"])
            if not g.is_valid:
                raise SystemExit(f"invalid geometry for {p['NUTS_ID']}")
            rows.append({"nuts_id": p["NUTS_ID"], "country": p["CNTR_CODE"], "name": p["NAME_LATN"], "wkb": g.wkb})
    d = pd.DataFrame(rows).sort_values("nuts_id")
    if d.groupby("country").size().to_dict() != {"ES": 19, "PT": 7}:
        raise SystemExit(f"expected 19 Spanish and 7 Portuguese regions, got {d.groupby('country').size().to_dict()}")
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(DATA.parent)}: {len(d)} regions")
    print(d[["nuts_id", "country", "name"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
