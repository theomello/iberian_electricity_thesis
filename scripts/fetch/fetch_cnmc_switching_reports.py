#!/usr/bin/env python3
"""Fetch the CNMC's reports on retailer switching (Informes de supervision de los cambios de comercializador), expedientes IS/DE/014/18 .. 014/25 (2018-2025), public PDFs.

Each quarterly report holds, as images inside the PDF, the supply points by market type and by retailer group (Tabla 2 free versus regulated, Tabla 6 by segment, Tabla 7 by group and market type),
the counts that Enrich, Li, Mizrahi and Reguant divide by (their section 3). Raw PDFs go to data/cnmc/raw_reports/ named <expediente>_<n>.pdf in the order the CNMC page lists them (newest first); the
listing is kept in _expedientes.json. Requests are 4 s apart; a file on disk is not requested again.
"""
import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "data" / "cnmc" / "raw_reports"
H = {"User-Agent": "Mozilla/5.0 (academic thesis research)"}
EXPEDIENTES = ["isde01418", "isde01419", "isde01420", "isde01421", "isde01422", "isde01423", "isde01424", "isde01425"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    listing = {}
    for e in EXPEDIENTES:
        r = requests.get(f"https://www.cnmc.es/expedientes/{e}", timeout=60, headers=H)
        time.sleep(4)
        listing[e] = sorted(set(re.findall(r'href="(/sites/default/files/[^"]+\.pdf)"', r.text)), key=r.text.find)
    json.dump(listing, open(OUT / "_expedientes.json", "w"), indent=1)
    for e, files in listing.items():
        for i, href in enumerate(files, 1):
            f = OUT / f"{e}_{i}.pdf"
            if f.exists():
                continue
            r = requests.get("https://www.cnmc.es" + href, timeout=300, headers=H)
            if r.status_code != 200 or r.content[:4] != b"%PDF":
                print("FAILED", e, i, href, r.status_code)
                continue
            f.write_bytes(r.content)
            print(f.name, href, f"{len(r.content) / 1e6:.1f} MB", flush=True)
            time.sleep(4)


if __name__ == "__main__":
    main()
