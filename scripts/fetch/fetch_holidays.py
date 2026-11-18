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
    2014: "BOE-A-2013-12147",  # 2014-2017 found 2026-11-18 via the BOE daily-summary API (titles checked)
    2015: "BOE-A-2014-10823",
    2016: "BOE-A-2015-11348",
    2017: "BOE-A-2016-9244",
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


MONTHS = {m: i + 1 for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
                                           "agosto", "septiembre", "octubre", "noviembre", "diciembre"])}


def parse_boe_old(year: int, table: str) -> pd.DataFrame:
    """2014-2017 layout: no axis/id attributes; region names in the second header row; each body row is a
    month block whose cells hold one <p> per line (line 0 the month name, then one line per holiday)."""
    ths = re.findall(r"<th[^>]*>(.*?)</th>", table, flags=re.S)
    cols = []
    for body in ths:
        k = _key(_text(body))
        hits = [code for kw, code in REGION if kw in k]
        if len(hits) == 1:
            cols.append(hits[0])
    if sorted(cols) != sorted(code for _, code in REGION):
        raise SystemExit(f"{year}: old-layout region columns {cols}")
    rows, month = [], None
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table, flags=re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)
        if not tds:
            continue
        if len(tds) == len(cols) + 2:  # 2015-2017 variant: one row per holiday (day, name, marks)
            day_txt, name = _text(tds[0]), _text(tds[1])
            if not re.fullmatch(r"\d{1,2}", day_txt) or month is None:
                raise SystemExit(f"{year}: unread holiday row {day_txt!r} {name!r} (month {month})")
            for area, cell in zip(cols, tds[2:]):
                mk = _text(cell)
                if not mk:
                    continue
                if mk not in MARK:
                    raise SystemExit(f"{year}-{month:02d}-{int(day_txt):02d} {area}: unknown mark {mk!r}")
                rows.append((pd.Timestamp(year, month, int(day_txt)), area, MARK[mk], name, BOE_IDS[year]))
            continue
        if MONTHS.get(_key(_text(tds[0]))) and not any(_text(c) for c in tds[1:]):  # a month header row
            month = MONTHS[_key(_text(tds[0]))]
            continue
        # the first holiday of a month sits in <p> lines under the month name; later ones are plain cell text
        lines = [[_text(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", td, flags=re.S)] or ([_text(td)] if _text(td) else []) for td in tds]
        if len(lines) != len(cols) + 1:
            raise SystemExit(f"{year}: old-layout row with {len(lines)} cells for {len(cols)} regions")
        n = len(lines[0])
        if any(len(c) not in (0, n) for c in lines[1:]):
            raise SystemExit(f"{year}: old-layout cells misaligned in row {lines[0][:2]}")
        for i, label in enumerate(lines[0]):
            mo = MONTHS.get(_key(label))
            if mo:
                month = mo
                continue
            m = re.match(r"(\d{1,2})\s+(.*)", label)
            if not m:
                if label:
                    raise SystemExit(f"{year}: unread line {label!r}")
                continue
            day, name = int(m.group(1)), m.group(2)
            for area, cell in zip(cols, lines[1:]):
                mk = cell[i] if cell else ""
                if not mk:
                    continue
                if mk not in MARK:
                    raise SystemExit(f"{year}-{month:02d}-{day:02d} {area}: unknown mark {mk!r}")
                rows.append((pd.Timestamp(year, month, day), area, MARK[mk], name, BOE_IDS[year]))
    return pd.DataFrame(rows, columns=["date", "area", "mark", "name", "source"])


def parse_boe(year: int, path: Path) -> pd.DataFrame:
    x = path.read_text(encoding="utf-8")
    table = re.search(r"<table.*?</table>", x, flags=re.S).group(0)
    if 'axis="CA"' not in table and 'axis="comunidad"' not in table:
        return parse_boe_old(year, table)
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


# 2016 and 2017: the BOE resolutions (BOE-A-2015-11348, BOE-A-2016-9244) publish their tables only in the PDF,
# whose text loses column alignment for regional days. Hand-read from page 3 of each PDF (data/holidays/raw/*.pdf)
# for ANDALUCÍA ONLY, the column the analysis reads (national = "*"); other regions are absent for these years.
HAND_AN = {2016: [((1, 1), "*", "Año Nuevo"), ((1, 6), "**", "Epifanía del Señor"),
                ((2, 29), "***", "Día de Andalucía"), ((3, 24), "**", "Jueves Santo"),
                ((3, 25), "*", "Viernes Santo"), ((5, 2), "**", "Lunes siguiente a la Fiesta del Trabajo"),
                ((8, 15), "*", "Asunción de la Virgen"), ((10, 12), "*", "Fiesta Nacional de España"),
                ((11, 1), "*", "Todos los Santos"), ((12, 6), "*", "Día de la Constitución Española"),
                ((12, 8), "*", "La Inmaculada Concepción"), ((12, 26), "**", "Lunes siguiente a la Natividad del Señor")],
           2017: [((1, 2), "**", "Lunes siguiente a Año Nuevo"), ((1, 6), "**", "Epifanía del Señor"),
                  ((2, 28), "***", "Día de Andalucía"), ((4, 13), "**", "Jueves Santo"),
                  ((4, 14), "*", "Viernes Santo"), ((5, 1), "*", "Fiesta del Trabajo"),
                  ((8, 15), "*", "Asunción de la Virgen"), ((10, 12), "*", "Fiesta Nacional de España"),
                  ((11, 1), "*", "Todos los Santos"), ((12, 6), "*", "Día de la Constitución Española"),
                  ((12, 8), "*", "La Inmaculada Concepción"), ((12, 25), "*", "Natividad del Señor")]}


def hand_an(year: int) -> pd.DataFrame:
    return pd.DataFrame([(pd.Timestamp(year, m, d), "AN", MARK[mk], n, BOE_IDS[year] + " (PDF, hand-read, AN only)")
                         for (m, d), mk, n in HAND_AN[year]], columns=["date", "area", "mark", "name", "source"])


def portugal(year: int) -> pd.DataFrame:
    e = pd.Timestamp(easter(year))
    days = {
        (1, 1): "Ano Novo", (4, 25): "Dia da Liberdade", (5, 1): "Dia do Trabalhador",
        (6, 10): "Dia de Portugal", (8, 15): "Assunção", (10, 5): "Implantação da República",
        (11, 1): "Todos os Santos", (12, 1): "Restauração da Independência",
        (12, 8): "Imaculada Conceição", (12, 25): "Natal",
    }
    # Lei 23/2012 suspended four national holidays for 2013-2015; Lei 8/2016 restored them from 2016
    suspended = {(10, 5), (11, 1), (12, 1)} if 2013 <= year <= 2015 else set()
    rows = [(pd.Timestamp(year, m, d), n) for (m, d), n in days.items() if (m, d) not in suspended]
    rows += [(e - pd.Timedelta(days=2), "Sexta-feira Santa"), (e, "Páscoa")]
    if not 2013 <= year <= 2015:
        rows.append((e + pd.Timedelta(days=60), "Corpo de Deus"))
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
        parts += [hand_an(year) if year in HAND_AN else parse_boe(year, path), portugal(year)]
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
