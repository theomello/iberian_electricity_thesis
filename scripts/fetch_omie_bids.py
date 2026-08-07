"""Fetch OMIE unit-level day-ahead bid curves (`curva_pbc_uof`).

This is the whole reason Spain is interesting as a setting: every offer
submitted by every unit, accepted or not.

Source
------
OMIE public file set `curva_pbc_uof`, one **monthly zip** per month
(``curva_pbc_uof_YYYYMM.zip``), no token. The archive runs 2018-01 to
2026-05. Each zip holds one file per day, ~17 MB zipped / ~108 MB raw per
month, ~82k rows and ~2,000 distinct units per day.

Format (semicolon-delimited, latin-1)::

    Hora;Fecha;Pais;Unidad;Tipo Oferta;Energia C/V;Precio C/V;Ofertada (O)/Casada (C);
    1;01/01/2024;MI;TOTRM01;C;380,7;1.500,00;O;

THE CRITICAL TRAP -- `O` and `C` rows are NOT additive
-----------------------------------------------------
The final field flags each row as Ofertada (``O``) or Casada (``C``). These
are two parallel views of the same auction, not disjoint parts of it:

* ``O`` rows are the **full submitted curve**
* ``C`` rows are the **cleared portion**

Verified on 2024-01-01 h12: offered sell = 63,599 MWh, matched sell = 24,872
MWh, matched buy = 24,872 MWh. Matched buy equalling matched sell exactly is
the market-clearing identity, which confirms the reading. Summing ``O + C``
double-counts every accepted bid.

So: filter to ``status == 'O'`` for the supply/demand function, and to
``status == 'C'`` for cleared quantities. Never aggregate across both.

`Pais` is only meaningfully populated on matched rows (offered rows are
mostly tagged ``MI`` for the joint MIBEL market).

Numbers use a COMMA decimal and DOT thousands separator (``1.500,00`` =
1500.0) -- unlike `marginalpdbc`, which uses a dot decimal.

Disk
----
Zips are kept (~1.7 GB) as the reproducible archive; each month is streamed
straight from the zip into parquet without ever unpacking to disk, so peak
usage stays near the zip + parquet total rather than the ~11 GB raw size.

Usage
-----
    .venv/bin/python scripts/fetch_omie_bids.py               # full archive
    .venv/bin/python scripts/fetch_omie_bids.py --months 202401 202402
    .venv/bin/python scripts/fetch_omie_bids.py --list        # what's available
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
import zipfile
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from omie_common import (  # noqa: E402
    DATA,
    END,
    OMIE_LIST,
    START,
    month_range,
    omie_url,
    parse_bid_number,
    session,
)

ZIPS = DATA / "omie" / "bids" / "zips"
PARQUET = DATA / "omie" / "bids" / "parquet"

SCHEMA = pa.schema(
    [
        ("date", pa.date32()),
        ("hour", pa.int8()),
        ("country", pa.dictionary(pa.int8(), pa.string())),
        ("unit", pa.dictionary(pa.int32(), pa.string())),
        ("side", pa.dictionary(pa.int8(), pa.string())),      # V=sell, C=buy
        ("energy_mwh", pa.float32()),
        ("price_eur_mwh", pa.float32()),
        ("status", pa.dictionary(pa.int8(), pa.string())),    # O=offered, C=matched
    ]
)


def available_months(sess) -> list[str]:
    """Scrape OMIE's own listing for the months that actually exist."""
    r = sess.get(
        OMIE_LIST,
        params={"parents[0]": "curva_pbc_uof", "realdir": "curva_pbc_uof"},
        timeout=90,
    )
    r.raise_for_status()
    import re

    return sorted(set(re.findall(r"curva_pbc_uof_(\d{6})\.zip", r.text)))


def download_month(sess, ym: str) -> Path | None:
    dest = ZIPS / f"curva_pbc_uof_{ym}.zip"
    if dest.exists() and zipfile.is_zipfile(dest):
        return dest
    url = omie_url("curva_pbc_uof", f"curva_pbc_uof_{ym}.zip")
    tmp = dest.with_suffix(".zip.part")
    with sess.get(url, timeout=600, stream=True, allow_redirects=True) as r:
        if r.status_code != 200:
            return None
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    if not zipfile.is_zipfile(tmp):
        tmp.unlink(missing_ok=True)
        return None
    tmp.rename(dest)
    return dest


def parse_member(raw: bytes) -> list[tuple]:
    """Parse one daily bid file from raw zip bytes."""
    rows: list[tuple] = []
    text = io.StringIO(raw.decode("latin-1"))
    for rec in csv.reader(text, delimiter=";"):
        # Data rows start with the hour index; headers and the title line do not.
        if len(rec) < 8 or not rec[0].strip().isdigit():
            continue
        try:
            hour = int(rec[0])
            d = datetime.strptime(rec[1].strip(), "%d/%m/%Y").date()
            rows.append(
                (
                    d,
                    hour,
                    rec[2].strip(),
                    rec[3].strip(),
                    rec[4].strip(),
                    parse_bid_number(rec[5]),
                    parse_bid_number(rec[6]),
                    rec[7].strip(),
                )
            )
        except (ValueError, IndexError):
            continue
    return rows


def convert_month(zpath: Path, ym: str, force: bool = False) -> Path | None:
    """Stream a monthly zip into one parquet file without unpacking to disk."""
    out = PARQUET / f"bids_{ym}.parquet"
    if out.exists() and not force:
        return out
    rows: list[tuple] = []
    with zipfile.ZipFile(zpath) as zf:
        for name in sorted(zf.namelist()):
            if name.endswith("/"):
                continue
            with zf.open(name) as fh:
                rows.extend(parse_member(fh.read()))
    if not rows:
        return None
    cols = list(zip(*rows))
    tbl = pa.table(
        {
            "date": pa.array(cols[0], pa.date32()),
            "hour": pa.array(cols[1], pa.int8()),
            "country": pa.array(cols[2]).dictionary_encode(),
            "unit": pa.array(cols[3]).dictionary_encode(),
            "side": pa.array(cols[4]).dictionary_encode(),
            "energy_mwh": pa.array(cols[5], pa.float32()),
            "price_eur_mwh": pa.array(cols[6], pa.float32()),
            "status": pa.array(cols[7]).dictionary_encode(),
        }
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(tbl, out, compression="zstd", compression_level=3)
    return out


def verify_month(path: Path) -> dict:
    """Re-check the clearing identity: matched buy == matched sell, per hour."""
    df = pd.read_parquet(path, columns=["date", "hour", "side", "energy_mwh", "status"])
    m = df[df["status"] == "C"]
    g = m.groupby(["date", "hour", "side"])["energy_mwh"].sum().unstack(fill_value=0.0)
    sell, buy = g.get("V"), g.get("C")
    if sell is None or buy is None:
        return {"rows": len(df), "checked": 0, "max_gap_pct": float("nan")}
    gap = ((sell - buy).abs() / sell.replace(0, pd.NA)).dropna()
    return {
        "rows": len(df),
        "checked": len(gap),
        "max_gap_pct": float(gap.max() * 100) if len(gap) else float("nan"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*", help="explicit YYYYMM list")
    ap.add_argument("--list", action="store_true", help="list available months and exit")
    ap.add_argument("--force", action="store_true", help="re-parse existing parquet")
    ap.add_argument("--verify", action="store_true", help="run the clearing-identity check")
    args = ap.parse_args()

    ZIPS.mkdir(parents=True, exist_ok=True)
    PARQUET.mkdir(parents=True, exist_ok=True)
    sess = session()

    avail = available_months(sess)
    if args.list:
        print(f"{len(avail)} months available: {avail[0]} .. {avail[-1]}")
        return 0

    wanted = args.months or month_range(START, END)
    months = [m for m in wanted if m in avail]
    skipped = sorted(set(wanted) - set(avail))
    print(f"OMIE bids: {len(months)} months to process"
          + (f" ({len(skipped)} unavailable: {skipped[:4]}...)" if skipped else ""),
          flush=True)

    done, failed = [], []
    for i, ym in enumerate(months, 1):
        try:
            z = download_month(sess, ym)
            if z is None:
                failed.append(ym)
                print(f"  [{i}/{len(months)}] {ym}: download failed", flush=True)
                continue
            out = convert_month(z, ym, force=args.force)
            if out is None:
                failed.append(ym)
                print(f"  [{i}/{len(months)}] {ym}: no rows", flush=True)
                continue
            size = out.stat().st_size / 1e6
            msg = f"  [{i}/{len(months)}] {ym}: {size:6.1f} MB parquet"
            if args.verify:
                v = verify_month(out)
                msg += f"  rows={v['rows']:>9,}  max clearing gap={v['max_gap_pct']:.4f}%"
            print(msg, flush=True)
            done.append(ym)
        except Exception as exc:  # noqa: BLE001
            failed.append(ym)
            print(f"  [{i}/{len(months)}] {ym}: ERROR {exc}", flush=True)

    zb = sum(p.stat().st_size for p in ZIPS.glob("*.zip")) / 1e9
    pb = sum(p.stat().st_size for p in PARQUET.glob("*.parquet")) / 1e9
    print(f"\ndone={len(done)}  failed={len(failed)}")
    print(f"  zips    : {zb:.2f} GB")
    print(f"  parquet : {pb:.2f} GB")
    if failed:
        print(f"  failed  : {failed}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
