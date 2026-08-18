#!/usr/bin/env python3
"""Fetch MITECO's historical reservoir-level bulletin -- the missing input
for the hydro water-value probe.

    .venv/bin/python scripts/fetch/fetch_hydro_reservoirs.py
    .venv/bin/python scripts/fetch/fetch_hydro_reservoirs.py --verify

Writes data/miteco/embalses_historico.parquet, one row per reservoir per
week. Not resumable in the per-day sense the OMIE fetchers are -- MITECO
publishes one bulk historical file, not a daily archive -- so this just
re-downloads and re-parses unless the output already exists.

WHY

`notes/hydro-water-value-design.md` and the cheap probe in
`hydro_water_value_precip.py` both point at the same gap: hydro's opportunity
cost of water is a function of the reservoir's *state* (how much water it
holds), not of rainfall directly. Rainfall is only one input into that state
-- a large reservoir buffers a wet or dry quarter without its marginal value
moving much -- and testing rainfall against offers came back with the wrong
sign, insignificant. This fetches the actual state variable instead: `Vol` in
Arzhintar, Leslie, Neill and Wyrwoll's opportunity-cost function c(pf, Vol,
Snow). `pf` (OMIP forwards) and `Snow` (ERA5, fetch_hydro_precipitation.py)
are already in hand; this is the piece that was still missing.

SOURCE

MITECO's Boletín Hidrológico Semanal, the same official weekly bulletin
whose PDF summaries have run since 1988:

    https://www.miteco.gob.es/es/agua/temas/evaluacion-de-los-recursos-hidricos/boletin-hidrologico.html

The page's own historical-download link is a zipped Access database:

    https://www.miteco.gob.es/content/dam/miteco/es/agua/temas/evaluacion-de-los-recursos-hidricos/boletin-hidrologico/Historico-de-embalses/BD-Embalses.zip

Confirmed 2026-08-18: no CSV/API distribution exists (checked the
datos.gob.es catalogue entry too), only this MDB. Token-free, no
registration. MITECO's own label is "provisional, unvalidated" -- the same
caveat every other series in this repo already carries for its own reasons.

ONE TABLE, SIX COLUMNS

`T_Datos Embalses 1988-2026` -- confirmed 720,099 rows, 401 reservoirs
across 16 hydrographic demarcations, 1987-10-06 to the current fetch date,
weekly. Columns, renamed on the way in:

    FECHA           -> date              (weekly, Tuesdays in practice)
    AMBITO_NOMBRE    -> ambito            (hydrographic demarcation, e.g. "Duero")
    EMBALSE_NOMBRE   -> embalse           (individual reservoir name)
    AGUA_TOTAL       -> capacity_hm3      (comma-decimal, like curva_pbc_uof --
                                            NOT the dot-decimal OMIE uses elsewhere)
    AGUA_ACTUAL      -> stored_hm3        (comma-decimal, same trap)
    ELECTRICO_FLAG    -> hydro_flag       ("1." / "0." -- whether this reservoir
                                            feeds hydroelectric generation, not
                                            merely irrigation/supply)

DEPENDENCY

Parsing a .mdb needs a driver. `mdbtools` via Homebrew pulls in a slow
from-source build chain (cmake et al.) on this machine; `access_parser`
(`.venv/bin/python -m pip install access_parser`) is a pure-Python MDB
reader with no system dependency and handles this file directly. Not yet
added to any tracked requirements file -- this repo has none; see
scripts/README.md.

RAW FILE

The zip (~11 MB) and the extracted .mdb (~220 MB) are kept under
data/miteco/raw/ rather than discarded, per the "raw downloads are never
modified" convention -- re-parsing is cheap, re-downloading a government
bulletin repeatedly is not polite.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, session  # noqa: E402

OUT_DIR = DATA / "miteco"
RAW_DIR = OUT_DIR / "raw"
OUT = OUT_DIR / "embalses_historico.parquet"
ZIP_URL = ("https://www.miteco.gob.es/content/dam/miteco/es/agua/temas/"
           "evaluacion-de-los-recursos-hidricos/boletin-hidrologico/"
           "Historico-de-embalses/BD-Embalses.zip")
TABLE = "T_Datos Embalses 1988-2026"


def download(sess) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = RAW_DIR / "BD-Embalses.zip"
    mdb_path = RAW_DIR / "BD-Embalses.mdb"
    if mdb_path.exists():
        print(f"  raw mdb cached at {mdb_path}")
        return mdb_path

    r = sess.get(ZIP_URL, timeout=300)
    r.raise_for_status()
    zip_path.write_bytes(r.content)
    print(f"  downloaded {len(r.content):,} bytes")

    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".mdb")]
        if len(names) != 1:
            raise RuntimeError(f"expected exactly one .mdb in the zip, found {names}")
        with z.open(names[0]) as src, open(mdb_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
    print(f"  extracted {mdb_path.name}")
    return mdb_path


def parse_comma_decimal(s: pd.Series) -> pd.Series:
    """AGUA_TOTAL / AGUA_ACTUAL use a comma decimal, like curva_pbc_uof and
    unlike marginalpdbc -- CLAUDE.md's decimal-separator trap, one more
    source that needs it."""
    return pd.to_numeric(s.str.replace(",", ".", regex=False), errors="coerce")


def parse_mdb(mdb_path: Path) -> pd.DataFrame:
    from access_parser import AccessParser

    db = AccessParser(str(mdb_path))
    if TABLE not in db.catalog:
        raise RuntimeError(f"table {TABLE!r} not found; catalogue is "
                            f"{list(db.catalog.keys())}")
    t = db.parse_table(TABLE)
    df = pd.DataFrame(t)
    df = df.rename(columns={
        "FECHA": "date", "AMBITO_NOMBRE": "ambito", "EMBALSE_NOMBRE": "embalse",
        "AGUA_TOTAL": "capacity_hm3", "AGUA_ACTUAL": "stored_hm3",
        "ELECTRICO_FLAG": "hydro_flag",
    })
    df["date"] = pd.to_datetime(df.date, errors="coerce")
    df["capacity_hm3"] = parse_comma_decimal(df.capacity_hm3)
    df["stored_hm3"] = parse_comma_decimal(df.stored_hm3)
    df["hydro_flag"] = df.hydro_flag.str.strip().str.rstrip(".") == "1"
    df = df.dropna(subset=["date", "ambito", "embalse"])
    return df.sort_values(["ambito", "embalse", "date"]).reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true",
                     help="re-derive coverage facts from the written parquet")
    ap.add_argument("--refresh", action="store_true",
                     help="re-parse even if the output parquet already exists")
    args = ap.parse_args()

    if OUT.exists() and not args.refresh and not args.verify:
        print(f"  {OUT} already exists; pass --refresh to re-parse")
        df = pd.read_parquet(OUT)
    else:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        mdb_path = download(session())
        df = parse_mdb(mdb_path)
        df.to_parquet(OUT, index=False)
        print(f"  wrote {OUT}")

    print(f"\n{len(df):,} rows, {df.embalse.nunique()} reservoirs, "
          f"{df.ambito.nunique()} demarcations")
    print(f"  date range {df.date.min().date()} -> {df.date.max().date()}")
    print(f"  hydroelectric-flagged rows: {df.hydro_flag.mean():.1%}")
    dupe = df.duplicated(["ambito", "embalse", "date"]).sum()
    print(f"  duplicate (ambito, embalse, date) rows: {dupe}")
    bad_ratio = ((df.stored_hm3 > df.capacity_hm3 * 1.05)).sum()
    print(f"  rows where stored > 1.05x capacity (parse check): {bad_ratio}")
    print("\n  ambitos:")
    for a, n in df.ambito.value_counts().items():
        print(f"    {a:<30}{n:>8,}")

    if args.verify:
        assert dupe == 0, "duplicate (ambito, embalse, date) rows -- parse is not a key"
        assert df.date.min().year <= 1988, "historical series should reach 1988"
        print("\n  --verify passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
