#!/usr/bin/env python3
"""Parse OMIE's dated *Listado de Unidades Ofertantes* PDFs.

    .venv/bin/python scripts/build/build_omie_unit_lists.py

Reads data/omie/unit_lists/LISTA_UNIDADES_*.PDF, writes
data/omie/registry/omie_unit_lists.parquet -- one row per unit per snapshot.

WHY THIS MATTERS

This is the **authoritative** unit registry, and it settles the two mappings
this repo has been reconstructing by hand:

- `agent_owner` -- the owning company, published directly, with an ownership
  **percentage**. Everything in build_unit_agents.py below the `esios` layer is
  inference from plant-name text and hand-checked code prefixes; this is OMIE
  stating it.
- `technology` -- OMIE's own technology label, which reaches units ESIOS never
  registers. Technology coverage from `cab` plant names tops out near 41% of
  generation volume.

OMIE's own reply (ticket #12541, 14 Aug 2026) says the listings are regenerated
daily and that **no complete historical unit-to-agent correspondence with
validity dates is published**. These twelve dated snapshots are the closest
substitute: 2014-09-24, 2016-12-05, 2018-01-09, 2018-07-23, 2018-08-03,
2019-07-18, 2019-11-27, 2020-03-09, 2022-02-08, 2023-05-16, 2023-12-30 and
2025-01-31. Ten fall inside the 2018-2026 study window.

**They are snapshots, not spells.** A unit's agent between two snapshots is
unobserved, and an ownership change is only locatable to the interval that
brackets it. Interpolating is a modelling choice, not a fact -- carry the
snapshot date with anything derived here, and prefer the nearest *preceding*
snapshot when attributing a bid.

The `ESTADO` column marks deregistered units `BAJA`. A unit can be BAJA in a
late snapshot and active in an early one, which is exactly the entry/exit
information the ESIOS registry lacks -- but note BAJA is a *state at the
snapshot date*, not a deregistration date.

FORMAT

Landscape PDFs, ~115 pages, one table with fixed column positions. The header
words are centred over their columns, so header positions do **not** give the
column edges; the boundaries below were read off the x-positions of the data
words themselves and verified stable across snapshots.

Descriptions and company names contain spaces, so a whitespace split is wrong.
Words are bucketed into columns by their x-coordinate and joined in x order,
per line, per page. Lines are grouped by rounded `top` **within a page** -- the
same `top` recurs on every page, so grouping across pages silently merges
unrelated rows.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "data" / "omie" / "unit_lists"
OUT = ROOT / "data" / "omie" / "registry" / "omie_unit_lists.parquet"

# Column geometry is NOT fixed across snapshots and must not be hardcoded.
# The 2022 report is "LISTADO DE UNIDADES OFERTANTES" with an ESTADO column;
# the 2023 and 2025 reports are "... OFERTANTES VIGENTES" -- active units only,
# no ESTADO -- and every x-position differs. Hardcoding 2022's edges silently
# wrote "ZONA" into status and split technology across two columns for the
# other vintages.
#
# So: read the column NAMES and their order from the header, then locate the
# left EDGES from the data itself. Headers are centred over their columns while
# data is left-aligned, so header positions cannot be used as edges -- but every
# data row starts a cell at the same x, which makes column starts the most
# frequent x0 values on the page by a wide margin.
HEADER_CANON: dict[str, str] = {
    "CODIGO": "unit",
    "DESCRIPCIÓN": "descr", "DESCRIPCION": "descr",
    "AGENTE": "agent_owner",
    "PORCENTAJE": "ownership_pct",
    "TIPO": "unit_type",
    "ESTADO": "status",
    "ZONA/FRONTERA": "zone",
    "TECNOLOGÍA": "technology", "TECNOLOGIA": "technology",
}

DATE_RE = re.compile(r"LISTA_UNIDADES_(\d{4})_(\d{2})_(\d{2})")
UNIT_RE = re.compile(r"^[A-Z0-9][A-Z0-9_\-]{1,11}$")

SCHEMA = pa.schema([
    ("snapshot", pa.date32()),
    ("unit", pa.string()),
    ("descr", pa.string()),
    ("agent_owner", pa.string()),
    ("ownership_pct", pa.float64()),
    ("unit_type", pa.string()),
    ("status", pa.string()),
    ("zone", pa.string()),
    ("technology", pa.string()),
])


def snapshot_date(path: Path) -> date | None:
    m = DATE_RE.search(path.name)
    if not m:
        return None
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def header_columns(pages) -> list[str]:
    """Column names in x order, read from whichever page carries the header."""
    for page in pages:
        ws = [w for w in page.extract_words() if w["top"] < 135]
        if not any(w["text"] == "CODIGO" for w in ws):
            continue
        seen, names = set(), []
        for w in sorted(ws, key=lambda z: z["x0"]):
            c = HEADER_CANON.get(w["text"].rstrip(":"))
            if c and c not in seen:
                seen.add(c)
                names.append(c)
        if len(names) >= 6:
            return names
    return []


def pct_column_x(pages) -> float:
    """x-position of the PORCENTAJE header, used to find the percentage cell.

    The percentage cannot be located as "the first numeric token": plant names
    routinely end in a unit number -- "C.N. ASCO 1", "C.C. ESCOMBRERAS 1" -- and
    that digit matches any percentage pattern. Pivoting on it truncated the
    description and threw away the owner for every such unit, silently, for
    21-42% of rows depending on the snapshot. Anchor on the column instead.
    """
    for page in pages:
        for w in page.extract_words():
            if w["top"] < 135 and w["text"].startswith("PORCENTAJE"):
                return w["x0"]
    return 0.0


def descr_agent_split(pages) -> float:
    """x-coordinate separating DESCRIPCIÓN from AGENTE PROPIETARIO.

    This is the one boundary that cannot be recovered semantically -- both
    fields are free text with spaces and no controlled vocabulary. The header
    words sit centred over their columns, so the midpoint between the two
    header *starts* separates them reliably: on the 2022 sheet DESCRIPCIÓN
    content ends at x=222 and AGENTE content begins at x=237, with the midpoint
    at 229.
    """
    for page in pages:
        ws = [w for w in page.extract_words() if w["top"] < 135]
        d = next((w for w in ws if w["text"].startswith(("DESCRIPCI",))), None)
        a = next((w for w in ws if w["text"] == "AGENTE"), None)
        if d and a:
            return (d["x0"] + a["x0"]) / 2.0
    return 0.0


# Everything to the right of the ownership percentage has controlled vocabulary,
# so it is parsed by content rather than by position -- which is what makes this
# work across three different column geometries.
ZONE_HEAD = ("ZONA", "FRONTERA")
PCT_RE = re.compile(r"^\d{1,3}(?:[.,]\d+)?$")


def split_tail(tokens: list[str]) -> dict[str, str | None]:
    """Split the tokens after the percentage into type / status / zone / tech.

    Layout: <unit type> [BAJA] <ZONA x | FRONTERA x> <technology...>. The zone
    is the anchor: it always starts with ZONA or FRONTERA and always spans two
    tokens. BAJA appears only for deregistered units, which is precisely why a
    positional parser drops it -- the column is empty on most rows.
    """
    zi = next((i for i, t in enumerate(tokens) if t.upper() in ZONE_HEAD), None)
    if zi is None:
        return {"unit_type": " ".join(tokens) or None, "status": None,
                "zone": None, "technology": None}
    head = tokens[:zi]
    status = "BAJA" if any(t.upper() == "BAJA" for t in head) else None
    unit_type = " ".join(t for t in head if t.upper() != "BAJA") or None
    zone = " ".join(tokens[zi:zi + 2]) or None
    tech = " ".join(tokens[zi + 2:]) or None
    return {"unit_type": unit_type, "status": status,
            "zone": zone, "technology": tech}


def parse_pdf(path: Path, snap: date) -> list[dict]:
    import pdfplumber

    rows: list[dict] = []
    with pdfplumber.open(path) as pdf:
        names = header_columns(pdf.pages)
        if not names:
            raise ValueError(f"{path.name}: no CODIGO header found -- "
                             "layout changed, or the PDF has no text layer")
        split_x = descr_agent_split(pdf.pages)
        if split_x <= 0:
            raise ValueError(f"{path.name}: could not locate the "
                             "DESCRIPCION/AGENTE boundary")
        pct_x = pct_column_x(pdf.pages)
        if pct_x <= 0:
            raise ValueError(f"{path.name}: could not locate the "
                             "PORCENTAJE column")

        for page in pdf.pages:
            words = page.extract_words()
            if not words:
                continue
            # Group into lines WITHIN this page. The same `top` recurs on every
            # page, so grouping across pages merges unrelated rows.
            lines: dict[float, list] = defaultdict(list)
            for w in words:
                if w["top"] < 135:          # page title and column headers
                    continue
                lines[round(w["top"], 1)].append(w)

            for _, ws in sorted(lines.items()):
                ws = sorted(ws, key=lambda z: z["x0"])
                toks = [w["text"] for w in ws]
                if not toks or not UNIT_RE.match(toks[0]):
                    continue
                # The percentage is the pivot: free text to its left, controlled
                # vocabulary to its right. Pick it by proximity to its column,
                # never by "first numeric token" -- see pct_column_x.
                cands = [i for i, w in enumerate(ws)
                         if i and PCT_RE.match(w["text"])
                         and abs(w["x0"] - pct_x) < 70]
                if not cands:
                    continue
                pi = min(cands, key=lambda i: abs(ws[i]["x0"] - pct_x))
                mid = [(w["text"], w["x0"]) for w in ws[1:pi]]
                rec: dict = {
                    "snapshot": snap,
                    "unit": toks[0],
                    "descr": " ".join(t for t, x in mid if x < split_x) or None,
                    "agent_owner": " ".join(t for t, x in mid
                                            if x >= split_x) or None,
                    "ownership_pct": float(toks[pi].replace(",", ".")),
                }
                rec.update(split_tail(toks[pi + 1:]))
                rows.append(rec)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", help="parse a single PDF")
    args = ap.parse_args()

    pdfs = ([Path(args.file)] if args.file
            else sorted(p for p in SRC.glob("LISTA_UNIDADES_*")
                        if p.suffix.lower() == ".pdf"))
    if not pdfs:
        print(f"no PDFs in {SRC}", file=sys.stderr)
        return 1

    frames = []
    for p in pdfs:
        snap = snapshot_date(p)
        if snap is None:
            print(f"  {p.name}: no date in filename, skipped")
            continue
        rows = parse_pdf(p, snap)
        df = pd.DataFrame(rows)
        frames.append(df)
        gen = df[df.technology.notna()]
        print(f"  {snap}  {len(df):5,} units  "
              f"{df.agent_owner.notna().sum():5,} with an owner  "
              f"{gen.technology.nunique():3d} technologies  "
              f"{(df.status == 'BAJA').sum():5,} BAJA")

    out = pd.concat(frames, ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(out[list(SCHEMA.names)], schema=SCHEMA,
                                        preserve_index=False),
                   OUT, compression="zstd")
    print(f"\n{len(out):,} rows, {out.unit.nunique():,} distinct units, "
          f"{out.snapshot.nunique()} snapshots -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
