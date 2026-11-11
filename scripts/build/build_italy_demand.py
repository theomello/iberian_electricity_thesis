"""Italian hourly demand and national price from GME's day-ahead (MGP) bids.

Reads `data/gme/offers/parquet/offers_YYYYMMDD.parquet` (760 days, 2021-06-01 -> 2023-06-30) and keeps accepted purchase
rows (side BID, status ACC) in the seven national zones (NORD, CNOR, CSUD, SUD, CALA, SICI, SARD). Foreign and
neighbouring zones (SVIZ, MONT, COAC, CORS, MALT, ...) are explicit export or border rows and are left out. Italian
demand clears in the PUN (*Prezzo Unico Nazionale*): every purchase unit in a national zone pays one price, so `pun` is
the volume-weighted mean awarded price of those rows. Pumping units bid here too (they are in `demand_mwh`).

Output `data/gme/italy_demand_hourly.parquet`: date, period (1..24, 23 or 25 on DST days), utc_timestamp, demand_mwh,
pun, bid_rows. Check printed: mean daily GWh by year against Italian consumption (about 300-320 TWh a year).
"""
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_common import day_periods_utc  # noqa: E402

NATIONAL = ["NORD", "CNOR", "CSUD", "SUD", "CALA", "SICI", "SARD"]


def main():
    out = []
    for f in sorted((ROOT / "data/gme/offers/parquet").glob("offers_*.parquet")):
        d = pd.read_parquet(f, columns=["side", "status", "zone", "period", "date", "awarded_mwh", "awarded_price_eur_mwh"])
        b = d[(d.side == "BID") & (d.status == "ACC") & (d.zone.astype(str).isin(NATIONAL))].copy()
        if b.empty:
            continue
        b["pw"] = b.awarded_mwh * b.awarded_price_eur_mwh
        g = b.groupby("period").agg(demand_mwh=("awarded_mwh", "sum"), pw=("pw", "sum"), bid_rows=("awarded_mwh", "size"))
        g["pun"] = g.pw / g.demand_mwh
        day = pd.Timestamp(b.date.iloc[0]).date()
        n = int(g.index.max())
        utc = day_periods_utc(day, n)
        g["date"] = day
        g["utc_timestamp"] = [utc[p - 1] for p in g.index]
        out.append(g.reset_index().drop(columns="pw"))
    r = pd.concat(out, ignore_index=True)
    r["date"] = pd.to_datetime(r.date)
    r.to_parquet(ROOT / "data/gme/italy_demand_hourly.parquet", index=False)
    y = r.assign(y=r.date.dt.year).groupby("y").agg(days=("date", "nunique"), gwh_day=("demand_mwh", lambda s: s.sum() / 1000), hours=("period", "size"))
    y["gwh_per_day"] = y.gwh_day / y.days
    print(f"{len(r)} rows, {r.date.nunique()} days, {r.date.min().date()} -> {r.date.max().date()}")
    print(y[["days", "hours", "gwh_per_day"]].round(0).to_string())
    print("periods per day:", r.groupby("date").period.max().value_counts().to_dict())
    print("pun: mean", round(r.pun.mean(), 1), "min", round(r.pun.min(), 1), "max", round(r.pun.max(), 1))


if __name__ == "__main__":
    main()
