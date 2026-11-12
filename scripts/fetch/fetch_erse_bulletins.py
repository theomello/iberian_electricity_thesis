#!/usr/bin/env python3
"""Fetch ERSE's monthly "Boletim do Mercado Liberalizado de Eletricidade" (Síntese Mensal) PDFs, December 2017 -> December 2021, public.

The listing is the ERSE library page `atos-e-documentos-da-erse` filtered on tipologia 'Mercado Liberalizado', sector Eletricidade (pages 4-7 cover these months). Each bulletin states the free-market
client count and the clients still with the last-resort supplier (CUR), Portugal's regulated segment: the paper's Portuguese consumer counts. Saved as data/erse/boletim_YYYYMM.pdf; 2.5 s between requests.
2021-03 and 2021-04 are not in the listing.
"""
import html
import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "data" / "erse"
H = {"User-Agent": "Mozilla/5.0 (academic thesis research)"}
MONTHS = {"janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    found = {}
    for pg in range(3, 9):
        u = f"https://www.erse.pt/biblioteca/atos-e-documentos-da-erse/?tipologia=----+Mercado+Liberalizado&setor=Eletricidade&page={pg}"
        t = requests.get(u, timeout=60, headers=H).text
        time.sleep(2.5)
        for h, x in re.findall(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', t, flags=re.S):
            x = html.unescape(re.sub(r"<[^>]+>|\s+", " ", x).strip())
            m = re.search(r"(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+(\d{4})", x)
            if h.startswith("/media/") and m and "mercado liberalizado" in x.lower():
                found.setdefault((int(m.group(2)), MONTHS[m.group(1)]), html.unescape(h))
    json.dump({f"{y}-{m:02d}": h for (y, m), h in sorted(found.items())}, open(OUT / "_listing_2017_2021.json", "w"), indent=1)
    for (y, m), h in sorted(found.items()):
        if not ((2017, 12) <= (y, m) <= (2021, 12)):
            continue
        f = OUT / f"boletim_{y}{m:02d}.pdf"
        if f.exists():
            continue
        r = requests.get("https://www.erse.pt" + h, timeout=120, headers=H)
        time.sleep(2.5)
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            f.write_bytes(r.content)
        else:
            print("FAILED", y, m, h, r.status_code)


if __name__ == "__main__":
    main()
