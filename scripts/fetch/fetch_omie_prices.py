"""Fetch OMIE day-ahead marginal prices for the MIBEL market (PT + ES).

Source
------
OMIE public file set `marginalpdbc`, one file per delivery day, no token.

Format (semicolon-delimited, latin-1)::

    MARGINALPDBC;
    2024;01;15;1;77.7;77.7;
    ...
    *

Fields: ``year;month;day;hour;price_pt;price_es``

Column order was VERIFIED empirically on 2026-08-07 rather than assumed.
On 2024-01-01 hour 12 the market split, giving ``29.8`` and ``3.9``. Cross
referencing the matched sell bids in `curva_pbc_uof` for that hour: Spanish
units cleared at a maximum of 3.90 and Portuguese units at 29.80. Therefore
field 5 is **Portugal** and field 6 is **Spain**.

Usage
-----
    .venv/bin/python scripts/fetch_omie_prices.py            # full window
    .venv/bin/python scripts/fetch_omie_prices.py --start 2024-01-01
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import (  # noqa: E402
    DATA,
    END,
    OMIE_LIST,
    START,
    date_range,
    day_periods_utc,
    omie_url,
    parse_price_number,
    resolution_minutes,
    session,
)

RAW = DATA / "omie" / "prices" / "raw"
OUT = DATA / "omie" / "prices" / "omie_day_ahead_prices.parquet"


def available_files(sess) -> tuple[dict[date, str], set[int]]:
    """Discover what OMIE actually publishes, rather than guessing names.

    OMIE splits this dataset two ways: older years (2018-2022 as of
    2026-08-07) are only available as **yearly zips**, while recent years are
    served as individual daily files. Assuming the daily pattern everywhere
    silently loses every pre-2023 day.

    Daily files also carry a revision suffix -- usually `.1`, but a handful
    of days have `.2` or `.3` corrections. We keep the highest revision.
    """
    r = sess.get(
        OMIE_LIST,
        params={"parents[0]": "marginalpdbc", "realdir": "marginalpdbc"},
        timeout=90,
    )
    r.raise_for_status()

    year_zips = {int(y) for y in re.findall(r"marginalpdbc_(\d{4})\.zip", r.text)}
    daily: dict[date, str] = {}
    for stamp, rev in re.findall(r"marginalpdbc_(\d{8})\.(\d+)", r.text):
        d = datetime.strptime(stamp, "%Y%m%d").date()
        name = f"marginalpdbc_{stamp}.{rev}"
        prev = daily.get(d)
        if prev is None or int(rev) > int(prev.rsplit(".", 1)[1]):
            daily[d] = name
    return daily, year_zips


def fetch_year_zip(sess, year: int) -> int:
    """Download a yearly archive and extract its daily files into RAW."""
    fname = f"marginalpdbc_{year}.zip"
    zpath = RAW.parent / fname
    if not (zpath.exists() and zipfile.is_zipfile(zpath)):
        r = sess.get(omie_url("marginalpdbc", fname), timeout=300, allow_redirects=True)
        if r.status_code != 200:
            return 0
        zpath.write_bytes(r.content)
        if not zipfile.is_zipfile(zpath):
            zpath.unlink(missing_ok=True)
            return 0
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


def fetch_day(sess, d: date, fname: str) -> Path | None:
    """Download one daily price file, skipping if already present."""
    dest = RAW / fname
    if dest.exists() and dest.stat().st_size > 100:
        return dest
    r = sess.get(omie_url("marginalpdbc", fname), timeout=60, allow_redirects=True)
    # OMIE serves a 404 HTML page for missing days rather than a bare 404.
    if r.status_code != 200 or b"MARGINALPDBC" not in r.content[:64]:
        return None
    dest.write_bytes(r.content)
    return dest


def parse_day(path: Path) -> list[dict]:
    """Parse one daily file into hourly rows."""
    rows: list[dict] = []
    text = path.read_text(encoding="latin-1")
    for line in text.splitlines():
        parts = line.split(";")
        if len(parts) < 6 or not parts[0].strip().isdigit():
            continue
        try:
            y, m, dd, period = (int(parts[i]) for i in range(4))
            price_pt = parse_price_number(parts[4])
            price_es = parse_price_number(parts[5])
        except (ValueError, IndexError):
            continue
        rows.append(
            {
                "date": date(y, m, dd),
                "period": period,
                "price_pt": price_pt,
                "price_es": price_es,
            }
        )
    return rows


def attach_utc(df: pd.DataFrame) -> pd.DataFrame:
    """Map each (date, period) to a true UTC instant.

    Handles both the hourly era and the 15-minute era that begins
    2025-10-01, plus the 23/25-hour DST days in each, by deriving the step
    from the observed number of periods on that day.
    """
    counts = df.groupby("date")["period"].max().to_dict()
    stamps: dict[date, list[datetime]] = {}
    out, res = [], []
    for d, period in zip(df["date"], df["period"]):
        grid = stamps.get(d)
        if grid is None:
            grid = stamps[d] = day_periods_utc(d, counts[d])
        # OMIE period index is 1-based within the local day.
        out.append(grid[period - 1] if 1 <= period <= len(grid) else pd.NaT)
        res.append(resolution_minutes(counts[d]))
    df = df.copy()
    df["utc_timestamp"] = out
    df["resolution_min"] = res
    return df


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", type=date.fromisoformat, default=START)
    ap.add_argument("--end", type=date.fromisoformat, default=END)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    days = list(date_range(args.start, min(args.end, date.today())))
    print(f"OMIE prices: {len(days)} days, {args.start} -> {args.end}", flush=True)

    sess = session()
    daily_map, year_zips = available_files(sess)

    # Yearly archives first -- they cover the years with no daily files.
    years = sorted({d.year for d in days} & year_zips)
    for y in years:
        n = fetch_year_zip(sess, y)
        print(f"  yearly zip {y}: {n} daily files extracted", flush=True)

    todo = [d for d in days if not any(RAW.glob(f"marginalpdbc_{d:%Y%m%d}.*"))]
    print(f"  {len(days) - len(todo)} days already on disk, {len(todo)} to fetch", flush=True)

    missing = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(fetch_day, sess, d, daily_map.get(d, f"marginalpdbc_{d:%Y%m%d}.1")): d
            for d in todo
        }
        for i, fut in enumerate(as_completed(futs), 1):
            d = futs[fut]
            try:
                if fut.result() is None:
                    missing.append(d)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {d}: {exc}", flush=True)
                missing.append(d)
            if i % 500 == 0:
                print(f"  {i}/{len(todo)} fetched", flush=True)

    on_disk = len({p.name.split("_")[1].split(".")[0] for p in RAW.glob("marginalpdbc_*")})
    print(f"days on disk={on_disk}  still missing={len(missing)}", flush=True)

    # Parse every file on disk, not just this run's downloads, so that a
    # partial or resumed run extends the parquet instead of truncating it.
    rows: list[dict] = []
    for p in sorted(RAW.glob("marginalpdbc_*")):
        rows.extend(parse_day(p))
    if not rows:
        print("no rows parsed", flush=True)
        return 1

    df = (pd.DataFrame(rows)
            .drop_duplicates(["date", "period"])
            .sort_values(["date", "period"]))
    df = attach_utc(df)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)

    per = df.groupby("date")["period"].max()
    print(f"\nwrote {OUT}  rows={len(df):,}")
    print(f"  span      : {df['date'].min()} -> {df['date'].max()}")
    print(f"  price_es  : mean {df['price_es'].mean():.2f}  "
          f"min {df['price_es'].min():.2f}  max {df['price_es'].max():.2f} EUR/MWh")
    print(f"  split hrs : {(df['price_es'] != df['price_pt']).mean():.1%} of hours ES != PT")
    print(f"  DST days  : {(per == 23).sum()} x 23p, {(per == 25).sum()} x 25p (hourly era); "
          f"{(per == 92).sum()} x 92p, {(per == 100).sum()} x 100p (15-min era)")
    print(f"  resolution: {(df['resolution_min'] == 60).sum():,} hourly rows, "
          f"{(df['resolution_min'] == 15).sum():,} quarter-hourly rows")
    print(f"  bad stamps: {df['utc_timestamp'].isna().sum()}")
    if missing:
        print(f"  missing   : {len(missing)} days (first few: {missing[:5]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
