"""Download the Barcelona City Council electricity-consumption CSVs (postal code, sector, time band; Datadis source; CC BY 4.0).

    .venv/bin/python scripts/fetch/fetch_barcelona_electricity.py

Seven files, 2019-2025, about 99 MB in total, from the dataset's CKAN metadata (resource ids read from
https://opendata-ajuntament.barcelona.cat/data/api/3/action/package_show?id=consum-electricitat-bcn on 2026-11-16). Output data/barcelona_electricity/raw/ (gitignored). Resumable: skips files
whose size matches the size in the metadata. The 2025 file grows while the year is published, so a size mismatch is reported, not treated as an error.
"""
import ssl
import urllib.request

import certifi
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "data" / "barcelona_electricity" / "raw"
BASE = "https://opendata-ajuntament.barcelona.cat/data/dataset/d9479057-781f-42b4-85e6-721bd0284130/resource/{id}/download"
FILES = [
    ("635923fe-9e3b-40d3-857d-aaa9a6913531", "2025_consum_electricitat_BCN.csv", 12376371),
    ("6f3a256a-dba6-46ac-88a4-546b93cb46da", "2024_consum_electricitat_bcn.csv", 13588121),
    ("25caee3a-a9f2-4e1a-8c8b-1b5fcac4f152", "2023_consum_electricitat_bcn.csv", 14313373),
    ("e685fa1a-9fbe-41a4-98a0-173464cd0c5f", "2022_consum_electricitat_bcn.csv", 14947159),
    ("2b6ef2c2-cbd0-437c-a229-889e992e1dd6", "2021_consum_electricitat_bcn.csv", 14484539),
    ("3c45a329-0414-4055-8f17-82456fc78dea", "2020_consum_electricitat_bcn.csv", 14574966),
    ("41b9a3e0-f079-4a4a-a8c3-670adc6bfb95", "2019_consum_electricitat_bcn.csv", 14590134),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for rid, name, size in FILES:
        path = OUT / name
        if path.exists() and path.stat().st_size == size:
            print("have", name)
            continue
        req = urllib.request.Request(BASE.format(id=rid), headers={"User-Agent": "research-data-fetch"})
        with urllib.request.urlopen(req, timeout=300, context=ssl.create_default_context(cafile=certifi.where())) as r, open(path, "wb") as f:
            f.write(r.read())
        print(name, "got", path.stat().st_size, "expected", size)


if __name__ == "__main__":
    main()
