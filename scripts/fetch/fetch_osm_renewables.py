#!/usr/bin/env python3
"""Fetch wind and solar plants (and wind turbines) in Spain and Portugal from OpenStreetMap.

    .venv/bin/python scripts/fetch/fetch_osm_renewables.py
    .venv/bin/python scripts/fetch/fetch_osm_renewables.py --refresh

Framework spec §9.3, rank 3: each firm's own regional wind and solar needs every
farm's location. No dataset on disk has them (REE's unit registers carry none, JRC
none for Spanish wind). OpenStreetMap maps plants as `power=plant` with
`plant:source=wind|solar`, often with a name, capacity (`plant:output:electricity`)
and operator, and wind turbines one by one as `power=generator` +
`generator:source=wind`. Farms are matched to REE's register by name downstream.

SOURCE: the public Overpass API (a mirror first, then overpass-api.de), no registration,
one query per tile of the peninsula and object type, results cached in data/osm/raw/ and never re-requested
unless --refresh. Data (c) OpenStreetMap contributors, ODbL 1.0: cite it.

A tile no server answers is skipped, not fatal: the run goes on, the tiles still
missing are listed in data/osm/missing_tiles.json, the parquets are written from what
is cached, and the exit code is 2. Re-running fetches only what is missing.

COUNTRY AND REGION come from Eurostat's NUTS 2021 polygons (`lib/regions.py`; run
`fetch_gisco_nuts.py` first): `country` is ES or PT, blank for the parts of the tiles
in France, Morocco and Algeria and for offshore turbines; `nuts_id` and `region` are the
autonomous community or Portuguese region; `esios_geo_id` is ESIOS's id of that region.

OUTPUTS (data/osm/):
  osm_renewable_plants.parquet   osm_type, osm_id, country, source (wind/solar), lat, lon
                                 (the centre for ways and relations), name, operator,
                                 output (the raw capacity tag), mw (parsed), start_date, tags,
                                 nuts_id, region, esios_geo_id, region_how
  osm_wind_turbines.parquet      the same columns, one row per turbine
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, session  # noqa: E402
from regions import locate  # noqa: E402

# On 2026-10-05 the main server answered 504 to every query and two mirrors timed out;
# the mail.ru mirror answered. Tried in this order.
URLS = ["https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"]
OUT = DATA / "osm"
RAW = OUT / "raw"
# The peninsula in tiles, queried by bounding box: an area filter (inside a country's
# boundary) made every query time out on the public servers. The tiles reach into
# France, Morocco and Algeria; `country` is set afterwards from the NUTS polygons.
LATS = [(35.8, 38.5), (38.5, 41.0), (41.0, 44.0)]
LONS = [(-9.6, -6.0), (-6.0, -3.0), (-3.0, 0.0), (0.0, 4.4)]
TILES = [(s_, w_, n_, e_) for (s_, n_) in LATS for (w_, e_) in LONS]
MAX_SPLIT = 3
# Overpass admits a query only if its declared timeout and memory fit the server's free
# capacity, so under load a modest declaration is admitted where the defaults are not
# (504). Every cached tile is under 0.4 MB.
HEAD = "[out:json][timeout:90][maxsize:67108864];"
QUERIES = {
    "plants": HEAD + '(nwr["power"="plant"]["plant:source"~"wind|solar"]({s},{w},{n},{e}););'
              'out center tags;',
    "turbines": HEAD + '(node["power"="generator"]["generator:source"="wind"]({s},{w},{n},{e}););'
                'out body;',            # body: a node's coordinates; 'out tags' drops them
}


MISSING: list[tuple] = []


def raw_path(kind: str, tile: tuple) -> Path:
    s_, w, n_, e = tile
    return RAW / f"{kind}_{s_:.2f}_{w:+.2f}_{n_:.2f}_{e:+.2f}.json"


def quarters(tile: tuple) -> list[tuple]:
    s_, w, n_, e = tile
    mlat, mlon = (s_ + n_) / 2, (w + e) / 2
    return [(s_, w, mlat, mlon), (s_, mlon, mlat, e), (mlat, w, n_, mlon), (mlat, mlon, n_, e)]


def split_before(kind: str, tile: tuple, depth: int) -> bool:
    """True if an earlier run already split this tile (some part of it is cached)."""
    if depth >= MAX_SPLIT:
        return False
    return any(raw_path(kind, q).exists() or split_before(kind, q, depth + 1) for q in quarters(tile))


def fetch_tile(kind: str, tile: tuple, refresh: bool, depth: int = 0) -> dict:
    """One tile; if every server fails on it, its four quarters instead (down to
    MAX_SPLIT levels). A tile that fails at the last level is recorded in MISSING and
    contributes nothing."""
    RAW.mkdir(parents=True, exist_ok=True)
    path = raw_path(kind, tile)
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    if not refresh and split_before(kind, tile, depth):
        return {"elements": [el for q4 in quarters(tile) for el in fetch_tile(kind, q4, refresh, depth + 1)["elements"]]}
    s_, w, n_, e = tile
    sess = session()
    q = QUERIES[kind].format(s=s_, w=w, n=n_, e=e)
    tries = len(URLS) if depth < MAX_SPLIT else 2 * len(URLS)
    for attempt in range(tries):
        url = URLS[attempt % len(URLS)]
        try:
            r = sess.post(url, data={"data": q}, timeout=150)
            if r.status_code == 200 and r.text.lstrip().startswith("{"):
                path.write_text(r.text)
                print(f"  {kind} {tile}: {len(r.content) / 1e6:.1f} MB from {url}", flush=True)
                time.sleep(5)           # be polite to a shared public server
                return r.json()
            print(f"  {kind} {tile}: HTTP {r.status_code} from {url}", flush=True)
        except Exception as ex:  # noqa: BLE001 -- network errors: try the next server
            print(f"  {kind} {tile}: {type(ex).__name__} from {url}", flush=True)
        time.sleep(15)
    if depth >= MAX_SPLIT:
        print(f"  {kind} {tile}: every server failed; skipped", flush=True)
        MISSING.append((kind, *tile))
        return {"elements": []}
    print(f"  {kind} {tile}: splitting into quarters", flush=True)
    return {"elements": [el for q4 in quarters(tile) for el in fetch_tile(kind, q4, refresh, depth + 1)["elements"]]}


def fetch(kind: str, refresh: bool) -> dict:
    """Every tile, elements de-duplicated (a plant's centre can sit near a tile edge)."""
    seen, els = set(), []
    for tile in TILES:
        for el in fetch_tile(kind, tile, refresh).get("elements", []):
            k = (el["type"], el["id"])
            if k not in seen:
                seen.add(k)
                els.append(el)
    return {"elements": els}


def parse_mw(v) -> float | None:
    """'49.5 MW', '2000 kW', '1,5 MW', 'yes' -> MW or None."""
    if not isinstance(v, str):
        return None
    m = re.search(r"([\d.,]+)\s*(GW|MW|kW|W)?", v.replace(" ", " "), re.I)
    if not m:
        return None
    x = m.group(1)
    x = x.replace(",", ".") if x.count(",") == 1 and "." not in x else x.replace(",", "")
    try:
        val = float(x)
    except ValueError:
        return None
    unit = (m.group(2) or "MW").upper()
    return val * {"GW": 1000, "MW": 1, "KW": 1e-3, "W": 1e-6}[unit]


def rows(js: dict, kind: str) -> list[dict]:
    out = []
    for e in js.get("elements", []):
        t = e.get("tags", {})
        lat = e.get("lat", e.get("center", {}).get("lat"))
        lon = e.get("lon", e.get("center", {}).get("lon"))
        output = t.get("plant:output:electricity") if kind == "plants" else t.get("generator:output:electricity")
        out.append({"osm_type": e["type"], "osm_id": e["id"],
                    "source": t.get("plant:source", t.get("generator:source")), "lat": lat, "lon": lon,
                    "name": t.get("name"), "operator": t.get("operator"), "output": output, "mw": parse_mw(output),
                    "start_date": t.get("start_date"), "tags": json.dumps(t, ensure_ascii=False)})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-query Overpass even if a raw file exists")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for kind, name in (("plants", "osm_renewable_plants.parquet"), ("turbines", "osm_wind_turbines.parquet")):
        d = pd.DataFrame(rows(fetch(kind, args.refresh), kind))
        r = locate(d.lat, d.lon)
        d = pd.concat([d, r.drop(columns="how").assign(region_how=r.how)], axis=1)
        d.insert(2, "country", d.pop("country"))
        d.to_parquet(OUT / name, index=False)
        print(f"wrote data/osm/{name}: {len(d):,} rows")
        if kind == "plants":
            g = d.groupby(["country", "source"], dropna=False).agg(n=("osm_id", "size"), named=("name", lambda x: x.notna().sum()),
                                                     with_mw=("mw", lambda x: x.notna().sum()), mw=("mw", "sum"))
            print(g.round(0).to_string())
        else:
            print(d.groupby(["country", "region"], dropna=False).agg(
                n=("osm_id", "size"), named=("name", lambda x: x.notna().sum())).to_string())
    miss = OUT / "missing_tiles.json"
    if MISSING:
        miss.write_text(json.dumps(MISSING, indent=1))
        print(f"\nINCOMPLETE: {len(MISSING)} tile(s) no server answered, listed in {miss.relative_to(DATA.parent)}; "
              f"re-run to fetch them")
        return 2
    miss.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
