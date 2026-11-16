"""Daily period sums of the GoiEner households (docs/specs/2026-11-17-goiener-household-design.md).

    .venv/bin/python scripts/build/build_goiener_daily.py

Streams data/goiener/raw/imp-pre.tzst and imp-post.tzst (never extracted to disk) and, for the selected supply points (tariff 2.0TD or 3.0TD, province Gipuzkoa, Bizkaia, Araba/Alava, Navarra or Madrid,
no declared self-consumption, series spanning 2020-02-29 and 2021-09-15, at most 10% missing samples), sums the hourly kWh of each complete 24-hour day over the paper's period types (peak 10-14 and 18-22,
mid, off-peak 0-8) and counts imputed hours. Writes data/goiener/daily/daily.parquet (user, date, kwh_peak, kwh_mid, kwh_off, n_imputed). Timestamps are taken as local clock time.
"""
import io
import subprocess
import sys
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "goiener" / "raw"
OUT = ROOT / "data" / "goiener" / "daily"
PEAK = {10, 11, 12, 13, 18, 19, 20, 21}
OFF = set(range(8))
PROV = {"Gipuzkoa", "Bizkaia", "Araba/Alava", "Navarra", "Madrid"}


def select():
    m = pd.read_csv(RAW / "metadata.csv", parse_dates=["start_date", "end_date"])
    ok = (m.contracted_tariff.isin(["2.0TD", "3.0TD"]) & m.province.isin(PROV) & m.self_consumption_type.isna() & (m.start_date <= "2020-02-29") & (m.end_date >= "2021-09-15")
          & (m.missing_samples_pct <= 10))
    return m[ok].set_index("user")


def stream(path, users, d0, d1):
    p = subprocess.Popen(["zstd", "-dc", str(path)], stdout=subprocess.PIPE)
    out, n = [], 0
    with tarfile.open(fileobj=p.stdout, mode="r|") as tf:
        for mem in tf:
            if not mem.isfile() or not mem.name.endswith(".csv"):
                continue
            u = Path(mem.name).stem
            if u not in users:
                continue
            d = pd.read_csv(io.BytesIO(tf.extractfile(mem).read()), parse_dates=["timestamp"])
            d = d[(d.timestamp >= d0) & (d.timestamp < d1)]
            if d.empty:
                continue
            d["date"] = d.timestamp.dt.normalize()
            h = d.timestamp.dt.hour
            d["per"] = np.where(h.isin(PEAK), "peak", np.where(h.isin(OFF), "off", "mid"))
            cnt = d.groupby("date").size()
            g = d.pivot_table(index="date", columns="per", values="kWh", aggfunc="sum").reindex(columns=["peak", "mid", "off"])
            g["n_imputed"] = d.groupby("date").imputed.sum()
            g = g[cnt.reindex(g.index) == 24].reset_index()
            g.insert(0, "user", u)
            out.append(g.rename(columns={"peak": "kwh_peak", "mid": "kwh_mid", "off": "kwh_off"}))
            n += 1
            if n % 2000 == 0:
                print(f"  {path.name}: {n} households", flush=True)
    p.stdout.close()
    p.wait()
    return pd.concat(out, ignore_index=True)


def main():
    meta = select()
    users = set(meta.index)
    print(f"selected {len(users)} supply points of {sum(1 for _ in open(RAW / 'metadata.csv')) - 1}", flush=True)
    pre = stream(RAW / "imp-pre.tzst", users, "2018-01-01", "2020-03-01")
    post = stream(RAW / "imp-post.tzst", users, "2021-05-31", "2021-09-16")
    d = pd.concat([pre, post], ignore_index=True)
    d.to_parquet(OUT / "daily.parquet")
    meta.reset_index().to_parquet(OUT / "selected_metadata.parquet")
    print(f"daily rows {len(d)}, households {d.user.nunique()}; pre {len(pre)} rows, post {len(post)} rows", flush=True)


if __name__ == "__main__":
    main()
