#!/usr/bin/env python3
"""Fetch MIBGAS's daily gas price indexes -- the fuel-cost input a CCGT
implied marginal cost needs.

    .venv/bin/python scripts/fetch/fetch_mibgas_prices.py
    .venv/bin/python scripts/fetch/fetch_mibgas_prices.py --verify

Writes data/mibgas/mibgas_price_index_daily.parquet, one row per delivery
day. Resumable like the OMIE fetchers: skips a year whose raw file is
already on disk unless --refresh is passed.

WHY

CCGT variable cost is dominated by gas: CNMC's own supervision reports say
so directly ("el gas natural es el combustible con mayor impacto... dado que
los costes de producción de los ciclos combinados dependen de él"). Combined
with `fetch_jrc_ppdb_efficiency.py`'s per-unit thermal efficiency, this gives
`gas_price / efficiency` -- most of an implied marginal cost, missing only
the CO2 term.

SOURCE, AND HOW IT WAS FOUND

MIBGAS's own market-results pages are a JS-rendered SPA with no visible
static link -- curl on the page returns none of the download links a
browser sees. The actual files sit behind a predictable path, found by
fetching the page's AJAX fragment directly
(`https://www.mibgas.es/es/ajax/node/1184`), which does embed a real link:

    https://www.mibgas.es/es/file-access/MIBGAS_Data_{YYYY}.xlsx?path=AGNO_{YYYY}/XLS

Confirmed for 2018 through 2026 (the current year), token-free, no
registration. Each file is MIBGAS's own "Market Results" workbook for that
year, one row per trading day per product.

THREE LAYOUTS, LIKE `cab`'S -- MIBGAS RESHAPED ITS OWN WORKBOOK TWICE

The index sheet is not stable across the window. Checked year-by-year rather
than assumed:

  * **2018-2020** -- sheet `Indices`, one row per day, `Area` column present
    but constant (`ES`), price in `MIBGAS-ES Index`.
  * **2021-2022** -- still sheet `Indices`, but now **long**: two rows per
    day, `Area` in `{ES, PT}`, price in the differently-named `MIBGAS Index`.
    Filtering `Area == "ES"` recovers one row per day.
  * **2023 onward** -- sheet renamed `MIBGAS Indexes` (plural, with an "es"),
    back to one row per day, price back in `MIBGAS-ES Index`, and several
    new columns alongside it (`PVB`/`VTP` last- and average-price variants,
    `MIBGAS-PT`, `LNG-ES`, `AVB-ES`).

A parser hardcoded to any one layout silently fails or silently
mis-reads the others -- exactly the trap CLAUDE.md already documents for
`cab`'s 2025-03-19 width change and REE realtime's 2025-12-12 field swap.
This one is dispatched **on the sheet name actually present** in each
year's workbook, which is what the data itself signals, rather than on a
hardcoded year cutoff.

WHAT'S HARMONIZED VS. ERA-ONLY

Only `mibgas_es_eur_mwh` -- the plain MIBGAS-ES daily index -- exists in a
comparable form across all three eras, and is the column this repo's
implied-marginal-cost use case actually needs. The 2023+-only richer fields
(PVB/VTP split, MIBGAS-PT, LNG-ES, AVB-ES) are carried through but are
**null for 2018-2022** by construction, the same era-boundary-null pattern
CLAUDE.md documents for REE realtime's 2025-12-12 field swap -- do not
treat them as continuous series back to 2018.

`Regulated gas` / `PGN_RD_10_2022` (the RD-L 10/2022 "Iberian exception"
gas-cap price paid to generators) is a separate, smaller series -- relevant
to the gas-cap question this repo has already tried and failed to identify
a market-wide effect for (`notes/rq-gas-cap-conduct.md`) -- and is
deliberately left unparsed here rather than folded in silently.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, session  # noqa: E402

OUT_DIR = DATA / "mibgas"
RAW_DIR = OUT_DIR / "raw"
OUT = OUT_DIR / "mibgas_price_index_daily.parquet"
URL_TMPL = "https://www.mibgas.es/es/file-access/MIBGAS_Data_{year}.xlsx?path=AGNO_{year}/XLS"
FIRST_YEAR = 2018

# 2018-2020: one row/day, Area constant "ES".
LAYOUT_A_MAP = {
    "Delivery day": "date",
    "MIBGAS-ES Index\n[EUR/MWh]": "mibgas_es_eur_mwh",
}
# 2021-2022: two rows/day (Area in {ES, PT}); filter Area == "ES" first.
LAYOUT_B_MAP = {
    "Delivery day": "date",
    "MIBGAS Index\n[EUR/MWh]": "mibgas_es_eur_mwh",
}
# 2023+: one row/day, richer field set.
LAYOUT_C_MAP = {
    "Delivery day": "date",
    "MIBGAS PVB Last Price Index Day-Ahead\n[EUR/MWh]": "pvb_last_eur_mwh",
    "MIBGAS PVB Average Price Index Day-Ahead\n[EUR/MWh]": "pvb_avg_eur_mwh",
    "MIBGAS VTP Last Price Index Day-Ahead\n[EUR/MWh]": "vtp_last_eur_mwh",
    "MIBGAS VTP Average Price Index Day-Ahead\n[EUR/MWh]": "vtp_avg_eur_mwh",
    "MIBGAS-ES Index\n[EUR/MWh]": "mibgas_es_eur_mwh",
    "MIBGAS-PT Index\n[EUR/MWh]": "mibgas_pt_eur_mwh",
    "MIBGAS\nLNG-ES Index\n[EUR/MWh]": "lng_es_eur_mwh",
    "MIBGAS\nAVB-ES Index\n[EUR/MWh]": "avb_es_eur_mwh",
}
ALL_ERA_ONLY_COLS = sorted(
    set(LAYOUT_C_MAP.values()) - {"date", "mibgas_es_eur_mwh"}
)


def years() -> list[int]:
    return list(range(FIRST_YEAR, date.today().year + 1))


def download(sess, year: int) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"MIBGAS_Data_{year}.xlsx"
    if path.exists():
        return path
    url = URL_TMPL.format(year=year)
    r = sess.get(url, timeout=120)
    r.raise_for_status()
    path.write_bytes(r.content)
    print(f"  {year}: downloaded {len(r.content):,} bytes")
    return path


def parse_year(path: Path, year: int) -> pd.DataFrame:
    import openpyxl
    sheetnames = openpyxl.load_workbook(path, read_only=True).sheetnames

    if "MIBGAS Indexes" in sheetnames:
        raw = pd.read_excel(path, sheet_name="MIBGAS Indexes", engine="openpyxl")
        col_map = LAYOUT_C_MAP
    elif "Indices" in sheetnames:
        raw = pd.read_excel(path, sheet_name="Indices", engine="openpyxl")
        if "MIBGAS Index\n[EUR/MWh]" in raw.columns:
            raw = raw[raw["Area"] == "ES"]
            col_map = LAYOUT_B_MAP
        else:
            col_map = LAYOUT_A_MAP
    else:
        raise RuntimeError(f"{path.name}: no recognised index sheet in {sheetnames}")

    missing = set(col_map) - set(raw.columns)
    if missing:
        raise RuntimeError(f"{path.name}: missing expected columns {missing}")
    df = raw[list(col_map)].rename(columns=col_map)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.dropna(subset=["date"])
    for col in ALL_ERA_ONLY_COLS:
        if col not in df.columns:
            df[col] = pd.NA
    df["source_year"] = year
    return df


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true",
                     help="re-derive coverage facts from the written parquet")
    ap.add_argument("--refresh", action="store_true",
                     help="re-download every year even if already on disk")
    args = ap.parse_args()

    if OUT.exists() and not args.refresh and not args.verify:
        print(f"  {OUT} already exists; pass --refresh to re-fetch")
        df = pd.read_parquet(OUT)
    else:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        sess = session()
        frames = []
        for yr in years():
            if args.refresh:
                (RAW_DIR / f"MIBGAS_Data_{yr}.xlsx").unlink(missing_ok=True)
            path = download(sess, yr)
            frames.append(parse_year(path, yr))
        df = pd.concat(frames, ignore_index=True)
        df = df.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
        df.to_parquet(OUT, index=False)
        print(f"  wrote {OUT}")

    print(f"\n{len(df):,} days, {df.date.min()} -> {df.date.max()}")
    print(f"  mibgas_es_eur_mwh null: {df.mibgas_es_eur_mwh.isna().sum()}")
    print(f"  mibgas_es_eur_mwh mean: {df.mibgas_es_eur_mwh.mean():.2f} EUR/MWh, "
          f"range {df.mibgas_es_eur_mwh.min():.2f}-{df.mibgas_es_eur_mwh.max():.2f}")
    print(f"  2023+-only fields null before 2023: "
          f"{df.loc[df.source_year < 2023, 'pvb_last_eur_mwh'].isna().all()}")

    if args.verify:
        dupe = df.duplicated("date").sum()
        assert dupe == 0, "duplicate date rows -- parse is not a key"
        expected_days = (pd.Timestamp(df.date.max()) - pd.Timestamp(df.date.min())).days + 1
        coverage = len(df) / expected_days
        assert coverage > 0.95, f"day coverage {coverage:.1%} looks too low for a daily index"
        assert df.mibgas_es_eur_mwh.isna().mean() < 0.02, "mibgas_es_eur_mwh should be near-complete"
        print(f"  day coverage vs. calendar span: {coverage:.1%}")
        print("\n  --verify passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
