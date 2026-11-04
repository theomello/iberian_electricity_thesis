#!/usr/bin/env python3
"""Fetch DGEG's daily balance of the Iberian gas-cap mechanism ("mecanismo ibérico").

    .venv/bin/python scripts/fetch/fetch_dgeg_mecanismo_iberico.py
    .venv/bin/python scripts/fetch/fetch_dgeg_mecanismo_iberico.py --verify

Writes data/dgeg/dgeg_mecanismo_iberico_daily.parquet from the workbook the
DGEG (Direcao-Geral de Energia e Geologia) links as "Ficheiro com historico
diario (xls)" on
https://www.dgeg.gov.pt/pt/estatistica/energia/precos-de-energia/mecanismo-iberico/
(that URL redirects to the DGEG home page as of 2026-11-04; the file link was read from
the Internet Archive capture of 2026-06-10 and the file itself is still served, openly,
at the address below). The raw workbook is kept unmodified in data/dgeg/raw/.

WHAT THE COLUMNS ARE (all EUR/MWh, per day, no volumes anywhere in the file)

    spot_eur_mwh        "Preco Spot" -- OMIE day-ahead daily average
    adjust_cost_eur_mwh "Custo do Ajuste" -- OMIE's daily average adjustment charge per MWh
                        bought by the buyers who pay it (the average of the hourly
                        "ajuste" over consumers, not a total and not the subsidy per MWh
                        of generation)
    final_price         spot + adjust_cost: what a buyer exposed to the mechanism pays
    gas_eur_mwh         "Valor do Gas Natural" -- MIBGAS gas price
    price_no_mech       DGEG's counterfactual "Preco sem Mecanismo": if gas is above the
                        cap path and final_price > 0: spot + (gas - cap)/0.55, else
                        final_price (cap 40 in the first formula; 56.1 in the formula used
                        from 2023-04-01; thresholds as in the workbook). A formula
                        applied to the day's SPOT price, not a re-clearing of the market.
    differential        price_no_mech - final_price (EUR/MWh): DGEG's "daily gain"
    differential_pct    100 - 100 * final_price / price_no_mech

The workbook stores the last four as Excel formulas; this script keeps the cached
values and --verify checks the identities.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, session  # noqa: E402

OUT_DIR = DATA / "dgeg"
RAW = OUT_DIR / "raw"
XLSX_NAME = "dgeg-mie-20240103.xlsx"
XLSX_URL = "https://www.dgeg.gov.pt/media/o5uf0cbw/" + XLSX_NAME
OUT = OUT_DIR / "dgeg_mecanismo_iberico_daily.parquet"


def download() -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / XLSX_NAME
    if path.exists():
        return path
    r = session().get(XLSX_URL, timeout=120)
    r.raise_for_status()
    if not r.content.startswith(b"PK"):
        raise RuntimeError("DGEG did not return an xlsx (got HTML?): the link has moved")
    path.write_bytes(r.content)
    print(f"  downloaded {path} ({len(r.content):,} bytes)")
    return path


def parse(path: Path) -> pd.DataFrame:
    import openpyxl
    ws = openpyxl.load_workbook(path, data_only=True)["Histórico"]
    stamp = ws["I4"].value
    rows = []
    for r in ws.iter_rows(min_row=7, values_only=True):
        if r[1] is None:
            continue
        rows.append(dict(date=pd.Timestamp(r[1]), spot_eur_mwh=r[2], adjust_cost_eur_mwh=r[3],
                         final_price=r[4], gas_eur_mwh=r[5], price_no_mech=r[6],
                         differential=r[7], differential_pct=r[8],
                         provisional=(r[9] == "Provisório")))
    df = pd.DataFrame(rows)
    for c in df.columns.drop(["date", "provisional"]):
        df[c] = pd.to_numeric(df[c].replace("", None))
    df["workbook_updated"] = stamp
    return df.sort_values("date").reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="re-parse even if the parquet exists")
    args = ap.parse_args()
    if OUT.exists() and not args.refresh and not args.verify:
        print(f"  {OUT} already exists; pass --refresh to re-parse")
        return 0
    df = parse(download())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    print(f"  wrote {OUT}: {len(df)} days, {df.date.min().date()} -> {df.date.max().date()}")

    if args.verify:
        assert not df.date.duplicated().any()
        assert df.date.diff().dropna().eq(pd.Timedelta("1D")).all(), "days missing"
        assert ((df.spot_eur_mwh + df.adjust_cost_eur_mwh - df.final_price).abs() < 1e-6).all()
        d = (df.price_no_mech - df.final_price - df.differential).abs().max()
        assert d < 1e-6, "differential != price_no_mech - final_price"
        # the counterfactual formula's gas threshold and divisor move with the cap path
        # (two formulas in the workbook, the second from 2023-04-01); it is not re-derived here
        print("  --verify done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
