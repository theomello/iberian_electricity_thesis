#!/usr/bin/env python3
"""Fetch OMIE's interconnection capacity and occupation after the day-ahead market.

    .venv/bin/python scripts/fetch/fetch_omie_interconnection.py [--start 2018-01-01] [--end 2026-05-31]
    .venv/bin/python scripts/fetch/fetch_omie_interconnection.py --parse-only

Source
------
OMIE `capacidad_inter_pbc`, "Capacidad y ocupación de las interconexiones tras la
casación del mercado diario", token-free. Like `marginalpdbc`, 2018-2022 exist only
as **yearly zips** and 2023 onward as daily files `capacidad_inter_pbc_YYYYMMDD.<rev>`
(the highest revision is kept). A day's file is published the day before delivery,
so unlike the bid curves there is no publication lag.

Format
------
Semicolon-delimited, latin-1, CRLF, and a COMMA decimal with a DOT thousands
separator (as `curva_pbc_uof`, unlike `marginalpdbc`). The layout changes twice, and
the header does not tell the resolution -- the period labels do:

    2018-01-01 -> 2025-03-18   Hora;...      1..23/24/25   hourly (MWh per hour)
    2025-03-19 -> 2025-09-30   Periodo;...   1..23/24      hourly (OMIE's platform migration)
    2025-10-01 ->              Periodo;...   HhQq          quarter-hour (MW)

plus ONE quarter-hour file inside the hourly era, 2025-07-15 (96 periods), kept as
published. `HhQq` counts hours within the local day (H1..H25 on the autumn DST day),
so the period is (h - 1) * 4 + q. An hourly MWh figure is numerically the average MW.

The six numbers per row are import capacity, import occupation, free import capacity,
export capacity, export occupation and free export capacity. **Import figures are
negative as published, and kept so.** Free capacity nets the counter-flow: a scheduled
export frees import room, so free import capacity can exceed the import capacity.

Border codes (`Frontera`), identified from the data on 2026-10-01, not assumed:

    2  PT  scheduled net export correlates 0.904 with REN's measured Portuguese net
           import (Jan 2024) and 0.908 with REE's measured flow (Nov 2025)
    3  FR  0.884 with REE's measured flow to France (Nov 2025)
    5  MA  0.985 with REE's measured flow to Morocco (Nov 2025)
    4  AD  Andorra, by elimination (about 135 MW)

An unknown code raises rather than being guessed.

Output
------
data/omie/interconnection/omie_interconnection_capacity.parquet, one row per
date x period x border: date, period, resolution_min, border, import_capacity_mw,
import_occupied_mw, import_free_mw, export_capacity_mw, export_occupied_mw,
export_free_mw. Raw files are kept in data/omie/interconnection/raw/.
`scripts/qa/check_omie_interconnection.py` checks the parse, the coverage, and that
market splitting coincides with a full Spain-Portugal link.
"""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, END, OMIE_LIST, START, omie_url, parse_bid_number, session  # noqa: E402

DATASET = "capacidad_inter_pbc"
RAW = DATA / "omie" / "interconnection" / "raw"
OUT = DATA / "omie" / "interconnection" / "omie_interconnection_capacity.parquet"
BORDERS = {"2": "PT", "3": "FR", "4": "AD", "5": "MA"}
VALUES = ["import_capacity_mw", "import_occupied_mw", "import_free_mw",
          "export_capacity_mw", "export_occupied_mw", "export_free_mw"]
QUARTER = re.compile(r"^H(\d+)Q([1-4])$")


def parse_text(text: str) -> pd.DataFrame:
    """Rows of one daily file. Raises on an unknown layout or border code."""
    lines = text.splitlines()
    head = next((i for i, ln in enumerate(lines) if ln.startswith(("Hora;", "Periodo;"))), None)
    if head is None:
        raise ValueError("no 'Hora;' or 'Periodo;' header line")
    rows = []
    for ln in lines[head + 1:]:
        parts = ln.split(";")
        if len(parts) < 9 or not parts[0].strip():
            continue
        code = parts[2].strip()
        if code not in BORDERS:
            raise ValueError(f"unknown border code {code!r} in {ln!r}")
        label = parts[0].strip()
        m = QUARTER.match(label)
        if label.isdigit():
            period, res = int(label), 60
        elif m:
            period, res = (int(m.group(1)) - 1) * 4 + int(m.group(2)), 15
        else:
            raise ValueError(f"unexpected period label {label!r}")
        rows.append([datetime.strptime(parts[1].strip(), "%d/%m/%Y").date(), period, res, BORDERS[code],
                     *(parse_bid_number(x) for x in parts[3:9])])
    d = pd.DataFrame(rows, columns=["date", "period", "resolution_min", "border", *VALUES])
    if d.resolution_min.nunique() > 1:
        raise ValueError("hourly and quarter-hour labels mixed in one file")
    return d


def available_files(sess) -> tuple[dict[date, str], set[int]]:
    """Daily files (highest revision per day) and yearly zips OMIE lists."""
    r = sess.get(OMIE_LIST, params={"parents[0]": DATASET, "realdir": DATASET}, timeout=90)
    r.raise_for_status()
    years = {int(y) for y in re.findall(rf"{DATASET}_(\d{{4}})\.zip", r.text)}
    daily: dict[date, str] = {}
    for stamp, rev in re.findall(rf"{DATASET}_(\d{{8}})\.(\d+)", r.text):
        d = datetime.strptime(stamp, "%Y%m%d").date()
        prev = daily.get(d)
        if prev is None or int(rev) > int(prev.rsplit(".", 1)[1]):
            daily[d] = f"{DATASET}_{stamp}.{rev}"
    return daily, years


def fetch_year_zip(sess, year: int) -> int:
    """Download a yearly zip once and extract its daily members into RAW."""
    zpath = RAW.parent / f"{DATASET}_{year}.zip"
    if not (zpath.exists() and zipfile.is_zipfile(zpath)):
        r = sess.get(omie_url(DATASET, zpath.name), timeout=300, allow_redirects=True)
        if r.status_code != 200 or not r.content.startswith(b"PK"):
            print(f"  {zpath.name}: not available", file=sys.stderr)
            return 0
        zpath.write_bytes(r.content)
    n = 0
    with zipfile.ZipFile(zpath) as zf:
        for member in zf.namelist():
            if member.endswith("/"):
                continue
            dest = RAW / Path(member).name
            if not dest.exists():
                dest.write_bytes(zf.read(member))
            n += 1
    return n


def fetch_day(sess, fname: str) -> bool:
    """Download one daily file unless it is already on disk."""
    dest = RAW / fname
    if dest.exists() and dest.stat().st_size > 100:
        return True
    r = sess.get(omie_url(DATASET, fname), timeout=60, allow_redirects=True)
    # OMIE answers a missing file with a 200 HTML page, so check the content.
    if r.status_code != 200 or not r.content.startswith(b"OMIE"):
        return False
    dest.write_bytes(r.content)
    return True


def latest_raw(start: date, end: date) -> list[Path]:
    """The highest-revision raw file for each day in [start, end]."""
    best: dict[date, tuple[int, Path]] = {}
    for p in RAW.glob(f"{DATASET}_*"):
        m = re.fullmatch(rf"{DATASET}_(\d{{8}})\.(\d+)", p.name)
        if not m:
            continue
        d = datetime.strptime(m.group(1), "%Y%m%d").date()
        if start <= d <= end and (d not in best or int(m.group(2)) > best[d][0]):
            best[d] = (int(m.group(2)), p)
    return [p for _, p in sorted(best.values(), key=lambda t: t[1].name)]


def parse_all(start: date, end: date) -> pd.DataFrame:
    files = latest_raw(start, end)
    d = pd.concat([parse_text(p.read_text(encoding="latin-1")) for p in files], ignore_index=True)
    d = d[(d.date >= start) & (d.date <= end)].sort_values(["date", "border", "period"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(DATA.parent)}  ({len(d):,} rows, {len(files):,} days, "
          f"{d.date.min()} -> {d.date.max()})")
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", type=date.fromisoformat, default=START)
    ap.add_argument("--end", type=date.fromisoformat, default=END)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--parse-only", action="store_true", help="re-parse raw files, no network")
    a = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    if not a.parse_only:
        sess = session()
        daily, years = available_files(sess)
        print(f"OMIE lists {len(years)} yearly zips and {len(daily):,} daily files")
        for y in sorted(years):
            if a.start.year <= y <= a.end.year:
                print(f"  {y}: {fetch_year_zip(sess, y)} daily members")
        todo = [f for d, f in sorted(daily.items()) if a.start <= d <= a.end]
        with ThreadPoolExecutor(a.workers) as ex:
            ok = list(ex.map(lambda f: fetch_day(sess, f), todo))
        print(f"  daily files: {sum(ok):,} of {len(todo):,} on disk")
        if not all(ok):
            print("  missing: " + ", ".join(f for f, k in zip(todo, ok) if not k)[:400], file=sys.stderr)
    parse_all(a.start, a.end)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
