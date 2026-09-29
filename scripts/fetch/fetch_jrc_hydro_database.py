#!/usr/bin/env python3
"""Fetch the JRC Hydro-power plants database -- storage capacity per plant.

    .venv/bin/python scripts/fetch/fetch_jrc_hydro_database.py
    .venv/bin/python scripts/fetch/fetch_jrc_hydro_database.py --force   # re-download

Writes data/jrc_hydro/jrc_hydro_plants.parquet, one row per Spanish or
Portuguese hydro plant, and keeps the raw CSV and its datapackage.json under
data/jrc_hydro/raw/. Static database, so this re-downloads only with --force.

WHY

A storage unit's water value is constant within the day only if its reservoir
holds many hours of full output (assumption A1 of
`docs/specs/2026-09-29-water-value-design.md`), and the day-level conduct test
(`notes/rq-midday-hydro.md` §7, item 10) has to split cascades by that ratio.
Nothing on disk gives it. MITECO publishes reservoir volume in hm3 with no head,
so volume cannot be turned into energy, and it covers Spain only; the Portuguese
file on disk (`data/snirh/`) has fill levels and no capacities. This database
publishes `storage_capacity_MWh` and `installed_capacity_MW` per plant, for both
countries.

SOURCE

De Felice, M., JRC Hydro-power plants database, European Commission Joint
Research Centre, CC-BY 4.0, no registration:

    https://github.com/energy-modelling-toolkit/hydro-power-database

`type` is HDAM (reservoir), HPHS (pumped storage) or HROR (run-of-river). The
storage figure is the JRC's own compilation and is not reported for every plant;
check coverage on the plants you use, not on the file.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "data" / "jrc_hydro"
RAW = OUT_DIR / "raw"
OUT = OUT_DIR / "jrc_hydro_plants.parquet"
BASE = "https://raw.githubusercontent.com/energy-modelling-toolkit/hydro-power-database/master/data/"
FILES = ["jrc-hydro-power-plant-database.csv", "datapackage.json"]
COUNTRIES = {"ES", "PT"}


def download(force: bool) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        dest = RAW / name
        if dest.exists() and not force:
            continue
        r = requests.get(BASE + name, timeout=60)
        r.raise_for_status()
        dest.write_bytes(r.content)
        print(f"  downloaded {name}  ({len(r.content):,} bytes)")


def parse() -> pd.DataFrame:
    d = pd.read_csv(RAW / FILES[0])
    d = d[d.country_code.isin(COUNTRIES)].copy()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    return d


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    download(args.force)
    d = parse()
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(d):,} plants)")
    print(d.groupby(["country_code", "type"]).agg(
        plants=("name", "size"), mw=("installed_capacity_MW", "sum"),
        storage_reported=("storage_capacity_MWh", lambda s: s.notna().mean()))
        .round(2).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
