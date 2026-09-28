"""Build a unit registry for the OMIE bid data: unit -> country, role, group.

Why this exists
---------------
The bid archive is keyed on unit codes (`ABA1`, `NXVD312`, `GESTVD4`) with no
attributes attached, and the `country` column inside those files does **not**
identify a unit's nationality -- only ~4.7% of matched rows carry `ES`/`PT`,
a share that tracks the market-splitting rate, so the tag marks splitting
events rather than unit attributes. Without a registry the 354 M bid rows are
anonymous.

Sources (all OMIE, all token-free)
----------------------------------
=========  ===========================================  ======================
dataset    content                                      what it contributes
=========  ===========================================  ======================
`pdbc`     day-ahead cleared schedule, Spanish units    the ES unit set
`pdbcpt`   same, Portuguese units                       the PT unit set
`pdbce`    same, broken out by company                  role code + group tag
=========  ===========================================  ======================

The ES and PT unit sets are **disjoint** (verified 2026-05-01: 2,715 ES units,
95 PT units, zero overlap), so membership is a clean country assignment.

`pdbce` adds two per-unit attributes, both constant within a unit:

* **field 7 — market role.** Ten values, decoded from cleared-quantity sign
  and volume on 2026-05-01: ``10`` generation (2,192 units, always selling),
  ``1`` large conventional generation (78), ``8`` retail/purchase (383,
  always buying), ``7`` smaller purchase (108), ``3`` pumping (16, the ``…B``
  suffix units), ``11`` pumped storage / batteries (19, mixed sign), plus
  ``6``/``9``/``17``/``19`` in small numbers. This separates *generators from
  retailers*, which any supply-curve or bidding analysis needs.
* **field 6 — corporate group tag** (``IB``, ``REP``, ``GE``, …), populated
  only for some units.

What this does NOT give
-----------------------
**Fuel/technology (gas vs wind vs solar) and nameplate capacity are not in
these files.** The role code separates generation from demand and isolates
storage, but it does not distinguish a CCGT from a wind farm. That mapping
needs ESIOS or ENTSO-E (both token-gated) or a name-matching exercise against
a plant list, and is deliberately left out rather than guessed at.

Sampling
--------
Parsing every day of `pdbc`+`pdbce` is ~1 billion rows and hours of CPU for
what is a slowly-changing attribute table. By default two days per month
(the 1st and 16th) are parsed, giving unit presence at roughly monthly
resolution; `--full` parses every day. The sampled days are recorded in the
output so the resolution is never implicit.

Zips are streamed and deleted after parsing unless `--keep-zips`: the cleared
schedule they carry is already available from the bid archive's
`status == 'C'` rows, so only the derived attributes are new.

Usage
-----
    .venv/bin/python scripts/build_unit_registry.py
    .venv/bin/python scripts/build_unit_registry.py --full --keep-zips
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
import zipfile
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import (  # noqa: E402
    DATA, END, START, month_range, monthly_zip_may_grow, omie_url, session,
)

OUTDIR = DATA / "omie" / "registry"
TMP = OUTDIR / "_zips"
OUT = OUTDIR / "unit_registry.parquet"

SAMPLE_DAYS = (1, 16)

ROLE_LABELS = {
    "1": "generation_large",
    "10": "generation",
    "8": "purchase_retail",
    "7": "purchase_other",
    "6": "purchase_other",
    "19": "purchase_other",
    "3": "pumping",
    "11": "storage_mixed",
    "9": "purchase_other",
    "17": "purchase_other",
}


def fetch_zip(sess, dataset: str, ym: str) -> Path | None:
    TMP.mkdir(parents=True, exist_ok=True)
    dest = TMP / f"{dataset}_{ym}.zip"
    # A zip kept by --keep-zips or an interrupted run may be a frontier
    # snapshot; reusing it would silently cut `last_seen` short.
    have = dest.exists() and zipfile.is_zipfile(dest)
    if have and not monthly_zip_may_grow(dest, ym):
        return dest
    tmp = dest.with_suffix(".part")
    with sess.get(omie_url(dataset, f"{dataset}_{ym}.zip"), timeout=900,
                  stream=True, allow_redirects=True) as r:
        if r.status_code != 200:
            return dest if have else None
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    if not zipfile.is_zipfile(tmp):
        tmp.unlink(missing_ok=True)
        return dest if have else None
    tmp.replace(dest)
    return dest


def scan(zpath: Path, full: bool, want_attrs: bool, acc: dict) -> None:
    """Accumulate per-unit facts from one monthly zip."""
    with zipfile.ZipFile(zpath) as zf:
        for name in sorted(zf.namelist()):
            if name.endswith("/"):
                continue
            stem = Path(name).name
            digits = "".join(ch for ch in stem if ch.isdigit())[:8]
            if len(digits) != 8:
                continue
            try:
                d = datetime.strptime(digits, "%Y%m%d").date()
            except ValueError:
                continue
            if not full and d.day not in SAMPLE_DAYS:
                continue
            with zf.open(name) as fh:
                for rec in csv.reader(io.StringIO(fh.read().decode("latin-1")),
                                      delimiter=";"):
                    if len(rec) < 8 or not rec[0].strip().isdigit():
                        continue
                    unit = rec[4].strip()
                    if not unit:
                        continue
                    e = acc[unit]
                    if e["first"] is None or d < e["first"]:
                        e["first"] = d
                    if e["last"] is None or d > e["last"]:
                        e["last"] = d
                    e["days"].add(d)
                    if want_attrs:
                        role, grp = rec[7].strip(), rec[6].strip()
                        if role:
                            e["roles"][role] += 1
                        if grp:
                            e["groups"][grp] += 1
                        try:
                            e["mwh"] += float(rec[5])
                        except ValueError:
                            pass


def new_acc():
    return defaultdict(lambda: {"first": None, "last": None, "days": set(),
                                "roles": defaultdict(int),
                                "groups": defaultdict(int), "mwh": 0.0})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--full", action="store_true", help="parse every day, not a sample")
    ap.add_argument("--keep-zips", action="store_true")
    ap.add_argument("--start", type=date.fromisoformat, default=START)
    ap.add_argument("--end", type=date.fromisoformat, default=END)
    args = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    sess = session()
    months = month_range(args.start, args.end)
    print(f"unit registry: {len(months)} months, "
          f"{'every day' if args.full else f'days {SAMPLE_DAYS} of each month'}",
          flush=True)

    es, pt, ce = new_acc(), new_acc(), new_acc()
    for i, ym in enumerate(months, 1):
        for dataset, acc, attrs in (("pdbc", es, False),
                                    ("pdbcpt", pt, False),
                                    ("pdbce", ce, True)):
            z = fetch_zip(sess, dataset, ym)
            if z is None:
                continue
            try:
                scan(z, args.full, attrs, acc)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {dataset} {ym}: {exc}", flush=True)
            finally:
                if not args.keep_zips:
                    z.unlink(missing_ok=True)
        if i % 12 == 0:
            print(f"  {i}/{len(months)} months  "
                  f"(ES {len(es)}, PT {len(pt)}, attrs {len(ce)})", flush=True)

    overlap = set(es) & set(pt)
    rows = []
    for unit in sorted(set(es) | set(pt) | set(ce)):
        if unit in es and unit in pt:
            country = "BOTH"
        elif unit in es:
            country = "ES"
        elif unit in pt:
            country = "PT"
        else:
            country = None
        a = ce.get(unit)
        role = max(a["roles"], key=a["roles"].get) if a and a["roles"] else None
        grp = max(a["groups"], key=a["groups"].get) if a and a["groups"] else None
        src = es.get(unit) or pt.get(unit) or a
        rows.append({
            "unit": unit,
            "country": country,
            "role_code": role,
            "role": ROLE_LABELS.get(role) if role else None,
            "group_tag": grp,
            "first_seen": src["first"] if src else None,
            "last_seen": src["last"] if src else None,
            "days_observed": len(src["days"]) if src else 0,
            "net_cleared_mwh": round(a["mwh"], 1) if a else None,
        })

    df = pd.DataFrame(rows)
    df.to_parquet(OUT, index=False)
    if not args.keep_zips:
        for p in TMP.glob("*.zip"):
            p.unlink(missing_ok=True)

    print(f"\nwrote {OUT}  units={len(df):,}")
    print(f"  country : {df['country'].value_counts(dropna=False).to_dict()}")
    print(f"  ES/PT overlap: {len(overlap)} (expected 0)")
    print(f"  roles   : {df['role'].value_counts(dropna=False).to_dict()}")
    print(f"  groups  : {df['group_tag'].nunique()} distinct tags")
    print(f"  span    : {df['first_seen'].min()} -> {df['last_seen'].max()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
