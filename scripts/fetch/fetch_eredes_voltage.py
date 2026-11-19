#!/usr/bin/env python3
"""E-REDES (Portuguese distribution operator) consumption by voltage level, open data (CC BY 4.0).

    .venv/bin/python scripts/fetch/fetch_eredes_voltage.py [--force]

Two datasets from the Opendatasoft portal e-redes.opendatasoft.com (API explore v2.1, CSV export):
  consumo-total-nacional                              15-minute national consumption, kWh, by voltage
                                                      (bt, mt, at, mat, total), 2023-01-01 onward; `datahora` is UTC
  3-consumos-faturados-por-municipio-ultimos-10-anos  monthly billed active energy, kWh, by parish and voltage
                                                      ("Baixa Tensão" vs "Muito Alta, Alta e Média Tensões"), 2020-11 onward
Raw CSV to data/eredes/raw/, parquet to data/eredes/. Resumable: skips a dataset whose raw CSV exists unless --force.
Both datasets grow at the frontier (sliding window of recent months), so re-run with --force to refresh.
"""
import argparse
import io
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "eredes" / "raw"
OUT = ROOT / "data" / "eredes"
BASE = "https://e-redes.opendatasoft.com/api/explore/v2.1/catalog/datasets/{d}/exports/csv"
DATASETS = {
    "consumo-total-nacional": "national_15min_by_voltage",
    "3-consumos-faturados-por-municipio-ultimos-10-anos": "monthly_parish_by_voltage",
}

ap = argparse.ArgumentParser()
ap.add_argument("--force", action="store_true")
a = ap.parse_args()
RAW.mkdir(parents=True, exist_ok=True)
for ds, name in DATASETS.items():
    raw = RAW / f"{ds}.csv"
    if raw.exists() and not a.force:
        print("have", raw.name)
    else:
        r = requests.get(BASE.format(d=ds), params={"delimiter": ";", "timezone": "UTC"},
                         headers={"User-Agent": "research-data-fetch"}, timeout=600)
        r.raise_for_status()
        raw.write_bytes(r.content)
        print(ds, f"{len(r.content) / 1e6:.1f} MB")
    df = pd.read_csv(raw, sep=";", dtype=str)
    if name == "national_15min_by_voltage":
        df["datahora"] = pd.to_datetime(df["datahora"], utc=True)
        for c in ["bt", "mt", "at", "mat", "total"]:
            df[c] = pd.to_numeric(df[c])
        df = df[["datahora", "bt", "mt", "at", "mat", "total"]].sort_values("datahora")
    else:
        df["energia_ativa_kwh"] = pd.to_numeric(df["energia_ativa_kwh"])
        df["month"] = pd.PeriodIndex(df["data"], freq="M").to_timestamp()
    df.to_parquet(OUT / f"{name}.parquet", index=False)
    print(name, len(df), "rows")
