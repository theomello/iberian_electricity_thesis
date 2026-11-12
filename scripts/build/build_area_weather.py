#!/usr/bin/env python3
"""Population-weighted hourly temperature for each regulated-retailer area.

    .venv/bin/python scripts/build/build_area_weather.py

Reads data/weather/temperature_population_hourly.parquet (ERA5 via Open-Meteo,
21 Iberian cities, hourly UTC) and writes
outputs/tables/regulated_area_panel/area_temperature_hourly.parquet
(utc_timestamp, area, temp_c, n_cities).

The paper uses population-weighted MERRA-2 per area. MERRA-2 needs a NASA
Earthdata login, which cannot be entered here, so ERA5 on the same 21 cities
stands in: another reanalysis of the same air temperature. The assignment of
cities to areas is APPROXIMATE (distribution territories by city, the shares
for Madrid split by hand) and is a stated limitation; only relative movement
between areas matters for the use (area-specific weather in the LASSO).
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
# area -> {city: share of the city's population served by the area's distributor group}
AREAS = {
    "ENDESA":    {"barcelona": 1, "zaragoza": 1, "sevilla": 1, "malaga": 1, "granada": 1, "cordoba": 1},
    "IBERDROLA": {"madrid": 0.7, "valencia": 1, "alicante": 1, "bilbao": 1, "valladolid": 1,
                  "murcia": 1, "pamplona": 1},
    "NATURGY":   {"a_coruna": 1, "vigo": 1, "madrid": 0.3},
    "EDP":       {"gijon": 1},
    "REPSOL":    {"santander": 1},
    "PT":        {"lisboa": 1, "porto": 1, "braga": 1, "coimbra": 1},
}

d = pd.read_parquet(ROOT / "data/weather/temperature_population_hourly.parquet")
rows = []
for area, cities in AREAS.items():
    s = d[d.city.isin(cities)].copy()
    s["w"] = s.population * s.city.map(cities)
    s["wt"] = s.w * s.temperature_2m
    g = s.groupby("utc_timestamp").agg(wt=("wt", "sum"), w=("w", "sum"), n=("city", "nunique"))
    g["temp_c"] = g.wt / g.w
    g["area"] = area
    g["n_cities"] = g.n
    rows.append(g[["area", "temp_c", "n_cities"]].reset_index())
out = pd.concat(rows, ignore_index=True)
dest = ROOT / "outputs/tables/regulated_area_panel/area_temperature_hourly.parquet"
out.to_parquet(dest)
print(out.groupby("area").temp_c.agg(["count", "mean", "min", "max"]).round(1))
print("missing hours per area:", out.groupby("area").temp_c.apply(lambda x: x.isna().sum()).to_dict())
p = out.pivot(index="utc_timestamp", columns="area", values="temp_c")
print(p.corr().round(2))
