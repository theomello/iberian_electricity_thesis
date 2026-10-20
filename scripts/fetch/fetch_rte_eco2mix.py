#!/usr/bin/env python3
"""Fetch RTE's eco2mix national data (France): demand, its D-1 forecast, output by fuel and
the commercial exchange with Spain, as hourly UTC means.

    .venv/bin/python scripts/fetch/fetch_rte_eco2mix.py [--force]

Writes data/rte/eco2mix_national.parquet: utc, consommation, prevision_j1, nucleaire,
eolien, solaire, ech_comm_espagne (MW). The raw export is kept in data/rte/raw/ and
re-downloaded only with --force.

Source: RTE's éCO2mix, national, consolidated and definitive data (`eco2mix-national-cons-def`)
on ODRÉ (Open Data Réseaux Énergies), Etalab open licence 2.0; no token. Rows are quarter-hours
and half-hours in UTC (`date_heure`); some fields (realised output) are filled only on the
half-hours, so the hour is the mean of whatever is filled. Coverage 2012-01-01 → 2026-08-30 as
of 2026-10-20; later months are in `eco2mix-national-tr`, not fetched here.

Note that `date` is a text field on ODRÉ: filter on `date_heure` with a `date'…'` literal.

Exists for the France-link design (docs/specs/2026-10-20-france-link-design.md §3.2): France's
D-1 demand forecast and nuclear output predict whether the line to Spain will be full.
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "rte" / "raw" / "eco2mix_national_cons_def.csv"
OUT = ROOT / "data" / "rte" / "eco2mix_national.parquet"
FIELDS = ["consommation", "prevision_j1", "nucleaire", "eolien", "solaire", "ech_comm_espagne"]
URL = ("https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/eco2mix-national-cons-def/exports/csv"
       "?where=date_heure%3E%3Ddate'2017-12-01'&select=date_heure," + ",".join(FIELDS) + "&delimiter=%3B")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="download the export again")
    args = ap.parse_args()
    if args.force or not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(URL, timeout=900)
        r.raise_for_status()
        RAW.write_bytes(r.content)
    t = pd.read_csv(io.BytesIO(RAW.read_bytes()), sep=";", encoding="utf-8-sig")
    missing = set(["date_heure"] + FIELDS) - set(t.columns)
    if missing:
        raise SystemExit(f"export lacks {sorted(missing)}")
    t["utc"] = pd.to_datetime(t.date_heure, utc=True).dt.floor("h")
    h = t.groupby("utc")[FIELDS].mean().reset_index()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    h.to_parquet(OUT, index=False)
    print(f"  {len(t):,} rows → {len(h):,} hours, {h.utc.min()} → {h.utc.max()}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
