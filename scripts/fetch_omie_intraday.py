"""Fetch OMIE unit-level **intraday** bid curves (`curva_pibc_uof`).

The day-ahead auction (`fetch_omie_bids.py`) is only half the market. Spain
runs a sequence of intraday sessions after it, and in a system at 40%+ VRE
that is where wind and solar forecast errors get resolved: a renewable unit's
day-ahead position is a forecast, and the intraday sessions are where it is
corrected. Any question about how renewables actually bid, or what
variability costs, needs both.

Source
------
OMIE file set `curva_pibc_uof`, one **monthly zip** per month, no token.
Members are named ``curva_pibc_uof_YYYYMMDD<SS>.1`` where ``SS`` is the
**session number** — January 2024 holds 186 files = 31 days x 6 sessions.
That session index is the one dimension the day-ahead files do not have, and
it exists only in the filename, never inside the file.

Session structure is not constant over the window: Spain ran 6-7 discrete
sessions historically, and the SIDC/European intraday auction reforms plus
the 2025-10 MTU change altered both the count and the timing. The session
count is therefore read per day rather than assumed.

Row format is identical to the day-ahead files, so `parse_member` is reused
unchanged — including the `O`/`C` non-additivity trap and the comma-decimal
parsing. See `fetch_omie_bids.py` for both.

Usage
-----
    .venv/bin/python scripts/fetch_omie_intraday.py
    .venv/bin/python scripts/fetch_omie_intraday.py --months 202401
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_omie_bids import parse_member  # noqa: E402
from omie_common import (  # noqa: E402
    DATA,
    END,
    OMIE_LIST,
    START,
    month_range,
    omie_url,
    session,
)

ZIPS = DATA / "omie" / "intraday" / "zips"
PARQUET = DATA / "omie" / "intraday" / "parquet"

MEMBER_RE = re.compile(r"curva_pibc_uof_(\d{8})(\d{2})\.", re.IGNORECASE)


def available_months(sess) -> list[str]:
    r = sess.get(OMIE_LIST,
                 params={"parents[0]": "curva_pibc_uof", "realdir": "curva_pibc_uof"},
                 timeout=90)
    r.raise_for_status()
    return sorted(set(re.findall(r"curva_pibc_uof_(\d{6})\.zip", r.text)))


def download_month(sess, ym: str) -> Path | None:
    dest = ZIPS / f"curva_pibc_uof_{ym}.zip"
    if dest.exists() and zipfile.is_zipfile(dest):
        return dest
    tmp = dest.with_suffix(".zip.part")
    with sess.get(omie_url("curva_pibc_uof", f"curva_pibc_uof_{ym}.zip"),
                  timeout=900, stream=True, allow_redirects=True) as r:
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


def convert_month(zpath: Path, ym: str, force: bool = False) -> tuple[Path | None, int]:
    """Stream one monthly zip to parquet, carrying the session index."""
    out = PARQUET / f"intraday_{ym}.parquet"
    if out.exists() and not force:
        return out, 0
    rows, sessions = [], set()
    with zipfile.ZipFile(zpath) as zf:
        for name in sorted(zf.namelist()):
            if name.endswith("/"):
                continue
            m = MEMBER_RE.search(Path(name).name)
            if not m:
                continue
            sess_no = int(m.group(2))
            sessions.add(sess_no)
            with zf.open(name) as fh:
                for r in parse_member(fh.read()):
                    rows.append((sess_no,) + r)
    if not rows:
        return None, 0
    c = list(zip(*rows))
    tbl = pa.table({
        "session": pa.array(c[0], pa.int8()),
        "date": pa.array(c[1], pa.date32()),
        "period": pa.array(c[2], pa.int8()),
        "hour": pa.array(c[3], pa.int8()),
        "quarter": pa.array(c[4], pa.int8()),
        "resolution_min": pa.array(c[5], pa.int8()),
        "country": pa.array(c[6], pa.string()).dictionary_encode(),
        "unit": pa.array(c[7], pa.string()).dictionary_encode(),
        "side": pa.array(c[8], pa.string()).dictionary_encode(),
        "power_mw": pa.array(c[9], pa.float32()),
        "price_eur_mwh": pa.array(c[10], pa.float32()),
        "status": pa.array(c[11], pa.string()).dictionary_encode(),
        # explicit string type: offer_type is entirely null before 2025-10,
        # and an inferred null-typed dictionary cannot be written.
        "offer_type": pa.array(c[12], pa.string()).dictionary_encode(),
    })
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(tbl, out, compression="zstd", compression_level=3)
    return out, len(sessions)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    ZIPS.mkdir(parents=True, exist_ok=True)
    PARQUET.mkdir(parents=True, exist_ok=True)
    sess = session()
    avail = available_months(sess)
    wanted = args.months or month_range(START, END)
    months = [m for m in wanted if m in avail]
    print(f"OMIE intraday: {len(months)} months to process", flush=True)

    done, failed = [], []
    for i, ym in enumerate(months, 1):
        try:
            z = download_month(sess, ym)
            if z is None:
                failed.append(ym)
                print(f"  [{i}/{len(months)}] {ym}: download failed", flush=True)
                continue
            out, nsess = convert_month(z, ym, force=args.force)
            if out is None:
                failed.append(ym)
                print(f"  [{i}/{len(months)}] {ym}: no rows", flush=True)
                continue
            n = pq.ParquetFile(out).metadata.num_rows
            print(f"  [{i}/{len(months)}] {ym}: {out.stat().st_size/1e6:6.1f} MB  "
                  f"rows={n:>10,}  sessions={nsess}", flush=True)
            done.append(ym)
        except Exception as exc:  # noqa: BLE001
            failed.append(ym)
            print(f"  [{i}/{len(months)}] {ym}: ERROR {exc}", flush=True)

    zb = sum(p.stat().st_size for p in ZIPS.glob("*.zip")) / 1e9
    pb = sum(p.stat().st_size for p in PARQUET.glob("*.parquet")) / 1e9
    print(f"\ndone={len(done)}  failed={len(failed)}")
    print(f"  zips {zb:.2f} GB   parquet {pb:.2f} GB")
    if failed:
        print(f"  failed: {failed}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
