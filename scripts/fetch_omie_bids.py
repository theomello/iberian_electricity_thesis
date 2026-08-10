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
import re
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
        ("period", pa.int8()),        # 1..25 hourly era, 1..100 quarter-hourly
        ("hour", pa.int8()),          # 1..25
        ("quarter", pa.int8()),       # 1..4; 0 in the hourly era
        ("resolution_min", pa.int8()),
        ("country", pa.dictionary(pa.int8(), pa.string())),
        ("unit", pa.dictionary(pa.int32(), pa.string())),
        ("side", pa.dictionary(pa.int8(), pa.string())),      # V=sell, C=buy
        ("power_mw", pa.float32()),
        ("price_eur_mwh", pa.float32()),
        ("status", pa.dictionary(pa.int8(), pa.string())),    # O=offered, C=matched
        ("offer_type", pa.dictionary(pa.int8(), pa.string())),  # null before 2025-10
    ]
)

# Units that represent cross-border interconnection rather than a physical
# Spanish or Portuguese generator/consumer. Their net position is why matched
# buy need not equal matched sell -- see verify_month().
INTERCONNECTION_UNITS = {"MIEU", "FRANC01", "INTRE01", "INTVD01", "EINTC01"}

PERIOD_RE = re.compile(r"^H(\d+)Q(\d+)$", re.IGNORECASE)


def available_months(sess) -> list[str]:
    """Scrape OMIE's own listing for the months that actually exist."""
    r = sess.get(
        OMIE_LIST,
        params={"parents[0]": "curva_pbc_uof", "realdir": "curva_pbc_uof"},
        timeout=90,
    )
    r.raise_for_status()
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
    """Parse one daily bid file, handling both market-resolution eras.

    **The file format changed with the 15-minute MTU switch on 2025-10-01.**

    Hourly era (to 2025-09-30), 8 columns::

        Hora;Fecha;Pais;Unidad;Tipo Oferta;Energía C/V;Precio C/V;Ofertada/Casada;
        1;01/01/2024;MI;TOTRM01;C;380,7;1.500,00;O;

    Quarter-hourly era (from 2025-10-01), 9 columns::

        Periodo;Fecha;Pais;Unidad;Tipo Oferta;Potencia C/V;Precio C/V;Ofertada/Casada;Tipología;
        H1Q1;11/10/2025;MI;TOTRM01;C;396,2;1.500,00;O;S;

    Three things change, and all three break a naive parser:

    1. The period key becomes ``H<hour>Q<quarter>`` instead of a bare integer,
       so an ``isdigit()`` guard silently drops every row.
    2. The quantity column is relabelled ``Potencia`` (MW) rather than
       ``Energía`` (MWh). Numerically the hourly figure is MWh over one hour,
       which equals average MW, so both are stored as ``power_mw``; derive
       energy as ``power_mw * resolution_min / 60``.
    3. A ninth column ``Tipología de Oferta`` appears: ``S`` simple, ``C01``/
       ``C02``/``C04`` complex conditions, and ``Imp FR``/``Exp FR`` for
       French interconnection.
    """
    rows: list[tuple] = []
    text = io.StringIO(raw.decode("latin-1"))
    for rec in csv.reader(text, delimiter=";"):
        if len(rec) < 8:
            continue
        key = rec[0].strip()
        if key.isdigit():
            hour, quarter, period, res = int(key), 0, int(key), 60
        else:
            m = PERIOD_RE.match(key)
            if not m:
                continue
            hour, quarter = int(m.group(1)), int(m.group(2))
            period, res = (hour - 1) * 4 + quarter, 15
        try:
            d = datetime.strptime(rec[1].strip(), "%d/%m/%Y").date()
            rows.append(
                (
                    d,
                    period,
                    hour,
                    quarter,
                    res,
                    rec[2].strip(),
                    rec[3].strip(),
                    rec[4].strip(),
                    parse_bid_number(rec[5]),
                    parse_bid_number(rec[6]),
                    rec[7].strip(),
                    rec[8].strip() if len(rec) > 8 and rec[8].strip() else None,
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
            "period": pa.array(cols[1], pa.int8()),
            "hour": pa.array(cols[2], pa.int8()),
            "quarter": pa.array(cols[3], pa.int8()),
            "resolution_min": pa.array(cols[4], pa.int8()),
            "country": pa.array(cols[5], pa.string()).dictionary_encode(),
            "unit": pa.array(cols[6], pa.string()).dictionary_encode(),
            "side": pa.array(cols[7], pa.string()).dictionary_encode(),
            "power_mw": pa.array(cols[8], pa.float32()),
            "price_eur_mwh": pa.array(cols[9], pa.float32()),
            "status": pa.array(cols[10], pa.string()).dictionary_encode(),
            # explicit string type: offer_type is entirely null before
            # 2025-10, and an inferred null dictionary cannot be written.
            "offer_type": pa.array(cols[11], pa.string()).dictionary_encode(),
        }
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(tbl, out, compression="zstd", compression_level=3)
    return out


OLD_SCHEMA_MARKER = "energy_mwh"


def migrate_month(path: Path) -> tuple[bool, int, int]:
    """Upgrade an hourly-era parquet to the two-era schema, losslessly.

    Re-parsing the zip is unnecessary for hourly months: every new column is
    derivable from what is already stored.

    ``period`` = ``hour`` · ``quarter`` = 0 · ``resolution_min`` = 60 ·
    ``offer_type`` = null · ``power_mw`` = ``energy_mwh``

    That last mapping is exact, not an approximation: the hourly files publish
    energy in MWh delivered over one hour, which is numerically identical to
    average MW. Measured at ~23x faster than re-parsing (1.5 s vs 33.8 s per
    month).

    Returns (migrated?, rows_before, rows_after) so the caller can prove the
    row count survived.
    """
    tbl = pq.read_table(path)
    if OLD_SCHEMA_MARKER not in tbl.schema.names:
        return False, tbl.num_rows, tbl.num_rows
    n = tbl.num_rows
    hour = tbl.column("hour")
    out = pa.table(
        {
            "date": tbl.column("date"),
            "period": hour,
            "hour": hour,
            "quarter": pa.array([0] * n, pa.int8()),
            "resolution_min": pa.array([60] * n, pa.int8()),
            "country": tbl.column("country"),
            "unit": tbl.column("unit"),
            "side": tbl.column("side"),
            "power_mw": tbl.column("energy_mwh"),
            "price_eur_mwh": tbl.column("price_eur_mwh"),
            "status": tbl.column("status"),
            "offer_type": pa.array([None] * n, pa.string()).dictionary_encode(),
        }
    )
    tmp = path.with_suffix(".parquet.tmp")
    pq.write_table(out, tmp, compression="zstd", compression_level=3)
    after = pq.ParquetFile(tmp).metadata.num_rows
    if after != n:  # never replace a good file with a short one
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"{path.name}: row count {n} -> {after}")
    tmp.replace(path)
    return True, n, after


def verify_month(path: Path) -> dict:
    """Check matched buy against matched sell, per period.

    **This is an anomaly detector, not a strict invariant.** Matched buy
    equals matched sell only when net cross-border flow is zero. Spain is
    coupled to France, so energy can enter or leave the ES+PT market without
    a matching local unit bid, and the raw gap is then non-zero by normal
    market operation -- concentrated in solar hours, when export volumes peak.
    Measured over 2025-05, the raw gap correlates 0.99 with the net position
    of the interconnection pseudo-units.

    Reported instead is the raw gap plus a **dropout detector**: an affected
    day is missing a block of units from *every* period, so its imbalance is
    both pervasive and near-constant within the day. Interconnection-driven
    gaps vary period to period and cluster in daylight hours, so they fail the
    constancy test and are correctly ignored.
    """
    df = pd.read_parquet(
        path, columns=["date", "period", "unit", "side", "power_mw", "status"]
    )
    m = df[df["status"] == "C"]
    if m.empty:
        return {"rows": len(df), "checked": 0,
                "max_gap_pct": float("nan"), "max_adj_gap_pct": float("nan")}

    g = m.groupby(["date", "period", "side"])["power_mw"].sum().unstack(fill_value=0.0)
    if "V" not in g or "C" not in g:
        return {"rows": len(df), "checked": 0,
                "max_gap_pct": float("nan"), "max_adj_gap_pct": float("nan")}

    denom = g["V"].replace(0, pd.NA)
    g["gap"] = g["V"] - g["C"]
    gap_pct = (g["gap"].abs() / denom).dropna()

    # Dropout signature: on an affected day a block of units is missing from
    # *every* period, so the imbalance is both pervasive and near-constant
    # within the day. Interconnection-driven gaps instead vary period to
    # period and concentrate in daylight hours, so they fail the second test.
    # Thresholds calibrated against the two known dropouts (2018-06-14,
    # 2022-10-12) and the interconnection-driven days of 2025-05:
    #
    #                   %periods   sign-consistency   std/mean
    #   dropout            100%          100%          0.08-0.25
    #   interconnection    <=92%         <=92%         0.52-1.34
    #
    # A missing block of units affects every period and always on the same
    # side, so all three statistics are extreme. Interconnection flow reverses
    # through the day and concentrates in daylight hours, so it fails all
    # three. std/mean separates most widely, hence the 0.40 cut.
    dropouts = []
    frame = g.reset_index()
    for day, sub in frame.groupby("date"):
        rel = (sub["gap"].abs() / sub["V"].replace(0, pd.NA)).dropna()
        if len(rel) == 0 or (rel > 0.005).mean() < 0.99:
            continue
        sign = max((sub["gap"] > 0).mean(), (sub["gap"] < 0).mean())
        nz = sub["gap"].abs()
        if sign >= 0.99 and nz.mean() > 0 and nz.std() / nz.mean() < 0.40:
            dropouts.append((str(day), float(sub["gap"].mean())))

    return {
        "rows": len(df),
        "checked": len(gap_pct),
        "max_gap_pct": float(gap_pct.max() * 100) if len(gap_pct) else float("nan"),
        "dropouts": dropouts,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*", help="explicit YYYYMM list")
    ap.add_argument("--list", action="store_true", help="list available months and exit")
    ap.add_argument("--force", action="store_true", help="re-parse existing parquet")
    ap.add_argument("--verify", action="store_true", help="run the clearing-identity check")
    ap.add_argument("--rebuild", action="store_true",
                    help="migrate old-schema parquet in place and parse anything missing")
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
    migrated = 0
    for i, ym in enumerate(months, 1):
        try:
            # Rebuild: upgrade an existing hourly-era file in place rather
            # than re-parsing its zip (~23x cheaper, and provably lossless).
            existing = PARQUET / f"bids_{ym}.parquet"
            if args.rebuild and existing.exists():
                did, before, after = migrate_month(existing)
                if did:
                    migrated += 1
                    msg = f"  [{i}/{len(months)}] {ym}: migrated {before:,} rows"
                    if args.verify:
                        v = verify_month(existing)
                        msg += f"  gap={v['max_gap_pct']:6.2f}%"
                        if v["dropouts"]:
                            msg += f"  DROPOUT: {[d for d, _ in v['dropouts']]}"
                    print(msg, flush=True)
                    done.append(ym)
                    continue

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
                msg += f"  rows={v['rows']:>10,}  gap={v['max_gap_pct']:6.2f}%"
                if v["dropouts"]:
                    msg += f"  DROPOUT DAYS: {[d for d, _ in v['dropouts']]}"
            print(msg, flush=True)
            done.append(ym)
        except Exception as exc:  # noqa: BLE001
            failed.append(ym)
            print(f"  [{i}/{len(months)}] {ym}: ERROR {exc}", flush=True)

    zb = sum(p.stat().st_size for p in ZIPS.glob("*.zip")) / 1e9
    pb = sum(p.stat().st_size for p in PARQUET.glob("*.parquet")) / 1e9
    print(f"\ndone={len(done)}  failed={len(failed)}  migrated={migrated}")
    print(f"  zips    : {zb:.2f} GB")
    print(f"  parquet : {pb:.2f} GB")
    if failed:
        print(f"  failed  : {failed}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
