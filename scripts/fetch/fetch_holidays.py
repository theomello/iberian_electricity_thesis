#!/usr/bin/env python3
"""Fetch Spain's labour holidays by region (BOE) and add Portugal's national holidays.

    .venv/bin/python scripts/fetch/fetch_holidays.py            # fetch what is missing, then parse
    .venv/bin/python scripts/fetch/fetch_holidays.py --parse-only

Source
------
Spain: the Dirección General de Trabajo's yearly *Resolución … por la que se publica
la relación de fiestas laborales para el año <Y>*, in the BOE each October, one per
holiday year (ids in `BOE_IDS`). Fetched as the BOE's own XML,
`https://www.boe.es/diario_boe/xml.php?id=<id>`, and kept in `data/holidays/raw/`.
A file whose text does not name its year is refused.

The annex is one table: a header cell per region (`id="andalucia"` … `id="melilla"`,
19 of them, the 17 regions plus Ceuta and Melilla), then one row per date with
`id="fDDMM"` and 19 cells, each empty or marked

    *     national holiday, not replaceable            -> mark "national"
    **    national holiday the region chose to keep    -> mark "national_chosen"
    ***   the region's own holiday                     -> mark "regional"

Day and month come from the row id, not from the cells' `headers` attribute, which
names the wrong month in places (2019: Holy Thursday's cells say "marzo").
Municipal holidays (two per municipality) and island-level days in the footnotes
(each Canary island's patron) are not in the table and are left out.

Portugal: national holidays by law (Código do Trabalho, art. 234; Lei 8/2016
restored 5 October, 1 November, 1 December and Corpus Christi from 2016): 1 January,
Good Friday, Easter Sunday, 25 April, 1 May, Corpus Christi, 10 June, 15 August,
5 October, 1 November, 1 December, 8 December, 25 December. Carnival is not a
holiday by law and is left out, as are municipal holidays (Lisbon 13 June, Porto
24 June).

Output
------
data/holidays/holidays_es_pt.parquet, one row per date and area: date, area (ISO
3166-2:ES region code, or PT), mark, name, source. Spanish holidays falling on a
weekend are kept as published. `lib/holidays.py` reads it.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests
from dateutil.easter import easter

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "data" / "holidays"
RAW = OUT_DIR / "raw"
OUT = OUT_DIR / "holidays_es_pt.parquet"
URL = "https://www.boe.es/diario_boe/xml.php?id={id}"

BOE_IDS = {  # holiday year -> BOE id of the resolution publishing it
    2018: "BOE-A-2017-11639",
    2019: "BOE-A-2018-14369",
    2020: "BOE-A-2019-14552",
    2021: "BOE-A-2020-13343",
    2022: "BOE-A-2021-17113",
    2023: "BOE-A-2022-16755",
    2024: "BOE-A-2023-22014",
    2025: "BOE-A-2024-21316",
    2026: "BOE-A-2025-21667",
}

# keyword in a region's header text (accents, case and punctuation stripped) -> ISO
# 3166-2:ES code. Order matters: "mancha" before "leon" is irrelevant, but each header
# must match exactly one keyword, which parse_boe checks.
REGION = [
    ("andaluc", "AN"), ("aragon", "AR"), ("asturias", "AS"), ("balear", "IB"),
    ("canarias", "CN"), ("cantabria", "CB"), ("mancha", "CM"), ("leon", "CL"),
    ("catalu", "CT"), ("valencia", "VC"), ("extremadura", "EX"), ("galicia", "GA"),
    ("madrid", "MD"), ("murcia", "MC"), ("navarra", "NC"), ("vasco", "PV"),
    ("rioja", "RI"), ("ceuta", "CE"), ("melilla", "ML"),
]
# The layout differs by year: 2018 marks region headers axis="comunidad" and dates
# id="headerDDMM"; from 2019 axis="CA" and id="fDDMM". A date with two named rows
# carries a letter suffix (2019: f2304a San Jorge for Aragón, f2304b Villalar for
# Castilla y León; 2018: header0906R, header0809E); without it they were skipped silently.
DATE_ID = re.compile(r'id="(?:f|header)(\d{2})(\d{2})[A-Za-z]?"')
MARK = {"*": "national", "**": "national_chosen", "***": "regional"}
PT_SOURCE = "PT Código do Trabalho art. 234"


def _key(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())


def _text(cell: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", cell)).strip()


def fetch(year: int, force: bool = False) -> Path:
    path = RAW / f"{BOE_IDS[year]}.xml"
    if path.exists() and not force:
        return path
    r = requests.get(URL.format(id=BOE_IDS[year]), timeout=60,
                     headers={"User-Agent": "Mozilla/5.0 (research; vre_spain_thesis)"})
    r.raise_for_status()
    if f"fiestas laborales para el año {year}" not in r.text:
        raise SystemExit(f"{BOE_IDS[year]} does not name holiday year {year}; refusing it")
    RAW.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    print(f"  fetched {path.name} ({len(r.content) / 1e3:.0f} kB)")
    time.sleep(2)
    return path


def parse_boe(year: int, path: Path) -> pd.DataFrame:
    x = path.read_text(encoding="utf-8")
    table = re.search(r"<table.*?</table>", x, flags=re.S).group(0)
    cols = []
    for attrs, body in re.findall(r"<th([^>]*)>(.*?)</th>", table, flags=re.S):
        if 'axis="CA"' in attrs or 'axis="comunidad"' in attrs:
            k = _key(_text(body))
            hits = [code for kw, code in REGION if kw in k]
            if len(hits) != 1:
                raise SystemExit(f"{year}: region header {k!r} matches {hits}")
            cols.append(hits[0])
    if sorted(cols) != sorted(code for _, code in REGION):
        raise SystemExit(f"{year}: region columns {cols}")
    rows = []
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", table, flags=re.S)
    dated = [tr for tr in trs if 'axis="fecha"' in tr]
    if sum(bool(DATE_ID.search(tr)) for tr in dated) != len(dated):
        bad = [re.search(r'id="([^"]*)"[^>]*axis="fecha"|axis="fecha"[^>]*id="([^"]*)"', tr) for tr in dated
               if not DATE_ID.search(tr)]
        raise SystemExit(f"{year}: date rows with an unread id: {[b.group(0) for b in bad if b]}")
    for tr in trs:
        m = DATE_ID.search(tr)
        if not m:
            continue  # a month header row
        day, month = int(m.group(1)), int(m.group(2))
        cells = re.findall(r"<t[dh]([^>]*)>(.*?)</t[dh]>", tr, flags=re.S)
        first = next(i for i, (attrs, _) in enumerate(cells) if DATE_ID.search(f" {attrs}"))
        name = re.sub(r"^\d+\s*", "", _text(cells[first][1]))
        marks = [_text(body) for _, body in cells[first + 1:]]
        if len(marks) != len(cols):
            raise SystemExit(f"{year}-{month:02d}-{day:02d}: {len(marks)} cells for {len(cols)} regions")
        for area, mk in zip(cols, marks):
            if not mk:
                continue
            if mk not in MARK:
                raise SystemExit(f"{year}-{month:02d}-{day:02d} {area}: unknown mark {mk!r}")
            rows.append((pd.Timestamp(year, month, day), area, MARK[mk], name, BOE_IDS[year]))
    return pd.DataFrame(rows, columns=["date", "area", "mark", "name", "source"])


def portugal(year: int) -> pd.DataFrame:
    e = pd.Timestamp(easter(year))
    days = {
        (1, 1): "Ano Novo", (4, 25): "Dia da Liberdade", (5, 1): "Dia do Trabalhador",
        (6, 10): "Dia de Portugal", (8, 15): "Assunção", (10, 5): "Implantação da República",
        (11, 1): "Todos os Santos", (12, 1): "Restauração da Independência",
        (12, 8): "Imaculada Conceição", (12, 25): "Natal",
    }
    rows = [(pd.Timestamp(year, m, d), n) for (m, d), n in days.items()]
    rows += [(e - pd.Timedelta(days=2), "Sexta-feira Santa"), (e, "Páscoa"),
             (e + pd.Timedelta(days=60), "Corpo de Deus")]
    return pd.DataFrame([(d, "PT", "pt_national", n, PT_SOURCE) for d, n in rows],
                        columns=["date", "area", "mark", "name", "source"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parse-only", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-fetch files already on disk")
    a = ap.parse_args()
    parts = []
    for year in BOE_IDS:
        path = RAW / f"{BOE_IDS[year]}.xml" if a.parse_only else fetch(year, a.force)
        parts += [parse_boe(year, path), portugal(year)]
    h = pd.concat(parts, ignore_index=True).sort_values(["date", "area"], ignore_index=True)
    if h.duplicated(["date", "area"]).any():
        raise SystemExit(f"duplicate date-area rows: {h[h.duplicated(['date', 'area'], keep=False)]}")
    h["date"] = h.date.astype("datetime64[ns]")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    h.to_parquet(OUT, index=False)
    n = h.assign(year=h.date.dt.year).groupby(["year", h.area.eq("PT")]).size().unstack()
    print(f"wrote {OUT.relative_to(ROOT)}: {len(h):,} rows\n{n.rename(columns={False: 'Spain', True: 'PT'})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
