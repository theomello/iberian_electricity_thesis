#!/usr/bin/env python3
"""Population-weighted hourly MERRA-2 2 m temperature per regulated-retailer area, 2018-2021.

    .venv/bin/python scripts/build/build_area_weather_merra2.py

Reads data/merra2/raw/T2M_*.nc4 (fetch_merra2_t2m.py), interpolates the 0.5 x 0.625 degree
grid bilinearly to the 21 cities of fetch_population_temperature.py, weights by city
population with the same city-to-area assignment as build_area_weather.py, and writes
outputs/tables/regulated_area_panel/area_temperature_merra2_hourly.parquet
(utc_timestamp, area, temp_c). Compares with the ERA5 version.
"""
import glob
from pathlib import Path
import pandas as pd, xarray as xr

ROOT = Path(__file__).resolve().parent.parent.parent
AREAS = {
    "ENDESA":    {"barcelona": 1, "zaragoza": 1, "sevilla": 1, "malaga": 1, "granada": 1, "cordoba": 1},
    "IBERDROLA": {"madrid": 0.7, "valencia": 1, "alicante": 1, "bilbao": 1, "valladolid": 1,
                  "murcia": 1, "pamplona": 1},
    "NATURGY":   {"a_coruna": 1, "vigo": 1, "madrid": 0.3},
    "EDP":       {"gijon": 1},
    "REPSOL":    {"santander": 1},
    "PT":        {"lisboa": 1, "porto": 1, "braga": 1, "coimbra": 1},
}
cities = (pd.read_parquet(ROOT / "data/weather/temperature_population_hourly.parquet")
          .drop_duplicates("city")[["city", "lat", "lon", "population"]].set_index("city"))
parts = []
for f in sorted(glob.glob(str(ROOT / "data/merra2/raw/T2M_*.nc4"))):
    with xr.open_dataset(f) as x:
        parts.append(x[["T2M"]].load())
ds = xr.concat(parts, dim="time")
t = ds["T2M"].interp(lat=xr.DataArray(cities.lat.values, dims="city", coords={"city": cities.index}),
                     lon=xr.DataArray(cities.lon.values, dims="city", coords={"city": cities.index}))
t = (t - 273.15).to_pandas()          # time x city, degrees C
t.index = pd.to_datetime(t.index, utc=True).floor("h")  # MERRA-2 hourly means are stamped HH:30; label by hour start
rows = []
for area, cs in AREAS.items():
    w = pd.Series({c: cities.population[c] * s for c, s in cs.items()})
    rows.append(pd.DataFrame({"utc_timestamp": t.index, "area": area,
                              "temp_c": (t[list(cs)] * w).sum(axis=1).values / w.sum()}))
out = pd.concat(rows, ignore_index=True)
out.to_parquet(ROOT / "outputs/tables/regulated_area_panel/area_temperature_merra2_hourly.parquet")
print("hours", t.shape[0], t.index.min(), t.index.max(), "dups", t.index.duplicated().sum())
era = pd.read_parquet(ROOT / "outputs/tables/regulated_area_panel/area_temperature_hourly.parquet")
era = era.assign(utc_timestamp=pd.to_datetime(era.utc_timestamp, utc=True))
m = out.merge(era, on=["utc_timestamp", "area"], suffixes=("_m", "_e"))
print(m.groupby("area").apply(lambda g: pd.Series({"corr": g.temp_c_m.corr(g.temp_c_e),
      "bias_m_minus_e": (g.temp_c_m - g.temp_c_e).mean(), "rmse": ((g.temp_c_m - g.temp_c_e) ** 2).mean() ** .5})).round(2))
p = out.pivot(index="utc_timestamp", columns="area", values="temp_c")
print(p.corr().round(2))
