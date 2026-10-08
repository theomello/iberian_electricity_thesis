#!/usr/bin/env python3
"""Fetch REE's I90DIA workbooks (ESIOS archive 34): per-unit detail, 90 days after the day.

    .venv/bin/python scripts/fetch/fetch_esios_i90.py                      # the 15th of each month
    .venv/bin/python scripts/fetch/fetch_esios_i90.py --dates 2023-06-15
    .venv/bin/python scripts/fetch/fetch_esios_i90.py --parse                # the hourly table

One workbook per day: about 37 sheets, each by programming unit (UP), among them the
secondary regulation band allocated (I90DIA05), the P48 final schedule (I90DIA02) and the
PHFC final intraday schedule (I90DIA36). Sheet I90DIA00 lists them for that day's file.
REE's UP codes for hydro are OMIE's (`DUER`, `EBRFEN`).

A SAMPLE, NOT THE ARCHIVE. A day is about 6.7 MB zipped (2023), so 2019-01 → 2025-09 in
full is about 16 GB. The default fetches the 15th of every month, 81 files, approved by the
user on 2026-10-08.

Needs ``ESIOS_TOKEN`` (`x-api-key`). REE issues the token on condition that data already
downloaded is not requested again, so each day is requested once and kept as returned in
``data/esios/raw/archives/34/I90DIA_YYYYMMDD.zip``; a day on disk is never requested
again. ``date`` in the request is the DATA day: the zip's one member is
``I90DIA_YYYYMMDD.xls`` for that day, and the script checks it. **From August 2025 REE
sends one CSV per sheet instead** (``I90DIA00_YYYYMMDD.csv`` … ``I90DIA42_…``; semicolon,
comma decimal, all quarter-hourly), which is accepted too. Anything else (an HTML or JSON
answer, a different day) is saved as ``.bad`` and the run stops, so a wrong answer is
never re-requested in a loop. Requests are 3 s apart.

**The band (I90DIA05) is by programming unit to 2024-11-15 and by market participant from
2024-12-15** (``END`` Endesa, ``GN`` Naturgy, ``HC`` EDP's Hidrocantábrico, …), so per-unit
reserve stops there; the schedules stay by unit.

Reading the .xls needs xlrd (added to .venv 2026-10-08).

PARSE (``--parse``) writes ``data/esios/i90/i90_sample_hourly.parquet``: date, hour (0-23,
Madrid local), unit, level (unit or participant), sheet, kind, mw, for every unit in four sheets of every day on disk:
  band   I90DIA05, secondary regulation band allocated; kind Subir (up) / Bajar (down)
  pdbf   I90DIA26, the day-ahead base schedule; kind Mercado / Bilateral / ...
  phfc   I90DIA36, the final intraday schedule (auction sessions and continuous trading)
  p48    I90DIA02, the final schedule after every market and REE's real-time processes
Periods are hourly ("00-01") or quarter-hourly (1..96) depending on sheet and year, read
from the header. The schedules are MWh per period, so quarter-hours are summed to the hour
(MWh in an hour = MW on average); the band is MW, so quarter-hours are averaged. Several
rows of a unit and kind (offer numbers) are added. In 2023 P48 is quarter-hourly while
PDBF and PHFC are hourly; P48 summed to the hour equals PHFC where nothing changed after
the intraday market (Duero, 2023-06-15, 00-01: 4 × 249.05 = 996.2).
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import time
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from config import require_token  # noqa: E402
from fetch_esios_spain import BASE, esios_session  # noqa: E402
from omie_common import DATA  # noqa: E402

RAW = DATA / "esios/raw/archives/34"
OUT = DATA / "esios/i90/i90_sample_hourly.parquet"
SHEETS = {"band": "I90DIA05", "pdbf": "I90DIA26", "phfc": "I90DIA36", "p48": "I90DIA02"}
MEAN = {"band"}                       # MW; the others are MWh per period
FIRST, LAST, DAY = "2019-01", "2025-09", 15
PAUSE_S = 3


def sample_days(first: str, last: str, day: int) -> list[date]:
    return [date(p.year, p.month, day) for p in pd.period_range(first, last, freq="M")]


def members_ok(names: list[str], d: date) -> bool:
    """One .xls for the day (to July 2025), or one CSV per sheet (from August 2025)."""
    if names == [f"I90DIA_{d:%Y%m%d}.xls"]:
        return True
    want = re.compile(rf"I90DIA\d\d_{d:%Y%m%d}\.csv")
    return bool(names) and all(want.fullmatch(n) for n in names) and f"I90DIA00_{d:%Y%m%d}.csv" in names


def fetch_day(sess, d: date) -> Path:
    """The day's zip on disk, requesting it only if absent."""
    out = RAW / f"I90DIA_{d:%Y%m%d}.zip"
    if out.exists():
        return out
    r = sess.get(f"{BASE}/archives/34/download",
                 params={"date": f"{d:%Y-%m-%d}T23:59:59+02:00", "locale": "es"}, timeout=600)
    ok = r.status_code == 200 and r.content[:2] == b"PK"
    if ok:
        ok = members_ok(zipfile.ZipFile(io.BytesIO(r.content)).namelist(), d)
    if not ok:
        bad = out.with_suffix(".bad")
        bad.write_bytes(r.content)
        raise SystemExit(f"{d}: HTTP {r.status_code}, not a zip of that day's I90DIA; saved as {bad.name}. Stopping.")
    out.write_bytes(r.content)
    return out


def rows_of(z: zipfile.ZipFile, sheet: str, day: pd.Timestamp, wb=None) -> list[list[str]] | None:
    """A sheet as rows of strings, from the .xls (wb) or the day's CSV member."""
    if wb is not None:
        if sheet not in wb.sheet_names():
            return None
        sh = wb.sheet_by_name(sheet)
        rows = [[str(sh.cell_value(r, c)).strip() for c in range(sh.ncols)] for r in range(sh.nrows)]
        wb.unload_sheet(sheet)
        return rows
    name = f"{sheet}_{day:%Y%m%d}.csv"
    if name not in z.namelist():
        return None
    return [[c.strip() for c in line.split(";")] for line in z.read(name).decode("utf-8-sig").splitlines()]


def number(x: pd.Series) -> pd.Series:
    """Dot decimal in the .xls, comma decimal in the CSVs (no thousands separator)."""
    return pd.to_numeric(x.astype(str).str.replace(",", ".", regex=False), errors="coerce").fillna(0.0)


def read_sheet(rows: list[list[str]], what: str) -> pd.DataFrame:
    """hour, unit, level, kind, mw for one sheet of one day. The band (I90DIA05) is by
    programming unit to 2024-11-15 and by market participant from 2024-12-15 (level)."""
    ids = ("Unidad de Programación", "Participante del Mercado")
    h = next(r for r in range(12) if rows[r] and rows[r][0] in ("Sentido", *ids))
    head = rows[h]
    idc = next(c for c in head if c in ids)
    d = pd.DataFrame([r + [""] * (len(head) - len(r)) for r in rows[h + 1:]], columns=head)
    d = d[d[idc].str.strip() != ""]
    hourly = [c for c in head if len(c) == 5 and c[2] == "-"]
    quarter = [c for c in head if c.replace(".0", "").isdigit()]
    per = hourly or quarter
    kind = {"band": "Sentido", "pdbf": "Tipo Transacción"}.get(what)
    d["kind"] = d[kind] if kind else ""
    long = d.melt(id_vars=[idc, "kind"], value_vars=per, var_name="p", value_name="mw")
    long["mw"] = number(long.mw)
    if hourly:
        long["hour"] = long.p.str[:2].astype(int)
        q = long.groupby([idc, "kind", "hour"]).mw.sum()
    else:
        long["hour"] = (long.p.astype(float).astype(int) - 1) // (len(per) // 24)
        q = long.groupby([idc, "kind", "hour", "p"]).mw.sum()
        q = q.groupby(level=[0, 1, 2]).mean() if what in MEAN else q.groupby(level=[0, 1, 2]).sum()
    q = q.rename_axis(["unit", "kind", "hour"]).reset_index()
    return q.assign(level="unit" if idc == ids[0] else "participant")


def parse() -> pd.DataFrame:
    import xlrd
    parts = []
    for f in sorted(RAW.glob("I90DIA_*.zip")):
        z = zipfile.ZipFile(f)
        day = pd.Timestamp(f.stem[7:15])
        names = z.namelist()
        wb = xlrd.open_workbook(file_contents=z.read(names[0]), on_demand=True) if names[0].endswith(".xls") else None
        for what, sheet in SHEETS.items():
            rows = rows_of(z, sheet, day, wb)
            if rows is not None:
                parts.append(read_sheet(rows, what).assign(date=day, sheet=what))
    d = pd.concat(parts, ignore_index=True)[["date", "hour", "unit", "level", "sheet", "kind", "mw"]]
    d["unit"] = d.unit.astype(str).str.strip()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(DATA.parent)}: {len(d):,} rows, {d.date.nunique()} days, {d.unit.nunique()} units")
    print(d.groupby(["sheet", "level"]).agg(units=("unit", "nunique"), days=("date", "nunique"),
                                            first=("date", "min"), last=("date", "max")).to_string())
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dates", nargs="*", type=date.fromisoformat, help="explicit data days")
    ap.add_argument("--first", default=FIRST)
    ap.add_argument("--last", default=LAST)
    ap.add_argument("--day", type=int, default=DAY, help="day of the month to sample")
    ap.add_argument("--parse", action="store_true", help="write the hourly table from the days on disk")
    args = ap.parse_args()
    if args.parse:
        parse()
        return 0
    RAW.mkdir(parents=True, exist_ok=True)
    days = args.dates or sample_days(args.first, args.last, args.day)
    todo = [d for d in days if not (RAW / f"I90DIA_{d:%Y%m%d}.zip").exists()]
    print(f"{len(days)} days, {len(days) - len(todo)} on disk, {len(todo)} to request")
    sess = esios_session(require_token("ESIOS_TOKEN"))
    sess.headers["Accept"] = "*/*"
    total = 0
    for i, d in enumerate(todo, 1):
        p = fetch_day(sess, d)
        total += p.stat().st_size
        print(f"  {d}: {p.stat().st_size / 1e6:.1f} MB ({i}/{len(todo)}, {total / 1e6:.0f} MB so far)", flush=True)
        time.sleep(PAUSE_S)
    print(f"done: {len(days)} days in {RAW.relative_to(DATA.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
