#!/usr/bin/env python3
"""The forward-price water value against the water value firms offer.

    .venv/bin/python scripts/build/build_water_value_forward.py     # input
    .venv/bin/python scripts/analysis/water_value_forward_check.py

`notes/rq-water-value-forward.md` §3-§5. Three comparisons, each for λ* without storage
(lam30) and with it (lam30s):
  revealed   EDP's and Movhera's λ̂50 from `water_value_revealed.parquet` (the price at
             half of the offered volume, rq-midday-hydro.md §3.16): medians, correlation,
             slope of λ̂ on λ*.
  offered    every storage unit's offered hydro steps over the day (`hydro_YYYYMM`
             caches), ordered by price, read at two points: o50, the price at half of the
             offered volume, and ocf, the price at the unit's expected running share cf_s.
             By group: medians, within-unit slope, and the median ratio of offer to λ*.
  storage    for units with a storage series, the within unit × calendar month slope of
             log(offer / λ*) on the fill anomaly: if the benchmark misses scarce water,
             offers sit further above it when reservoirs are low (a negative slope).

WHY ocf. A cascade unit offers its full turbine capacity but has water for about a fifth
of the hours. A price-taker offers the water it expects to use at λ; the price of the
capacity beyond it says little about the water value. o50 mixes the two: Iberdrola's
basin units offer 2.8 × λ* at o50 and 1.2 × at ocf.
Writes outputs/tables/water_value_forward_check.csv.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
TABLES = ROOT / "outputs/tables"
CACHE = ROOT / "outputs/cache/step"
OUT = TABLES / "water_value_forward_check.csv"
LAMS = ("lam30", "lam30s")


def offered(w: pd.DataFrame) -> pd.DataFrame:
    """unit, date, o50, ocf: the price at half of the unit's offered hydro volume that day,
    and at its expected running share cf_s."""
    parts = []
    for f in sorted(CACHE.glob("hydro_2*.parquet")):
        h = pd.read_parquet(f, columns=["date", "unit", "price", "mw", "withdrawn"])
        h = h[~h.withdrawn & (h.mw > 0)]
        h["date"] = pd.to_datetime(h.date)
        h = h.merge(w[["unit", "date", "cf_s"]], on=["unit", "date"]).sort_values(["unit", "date", "price"])
        g = h.groupby(["unit", "date"])
        h["cum"] = g.mw.cumsum() / g.mw.transform("sum")
        parts.append(pd.concat([h[h.cum >= 0.5].groupby(["unit", "date"]).price.first().rename("o50"),
                                h[h.cum >= h.cf_s].groupby(["unit", "date"]).price.first().rename("ocf")], axis=1))
    return pd.concat(parts).reset_index()


def within_slope(x: pd.DataFrame, y: str, lam: str) -> float:
    a = x[y] - x.groupby("unit")[y].transform("mean")
    b = x[lam] - x.groupby("unit")[lam].transform("mean")
    return float((a @ b) / (b @ b))


def main() -> int:
    w = pd.read_parquet(TABLES / "water_value_forward.parquet")
    w["date"] = pd.to_datetime(w.date)
    rows = []

    r = pd.read_parquet(TABLES / "water_value_revealed.parquet")[["unit", "date", "lambda50"]]
    r["date"] = pd.to_datetime(r.date)
    e = r.merge(w[["unit", "date", "storage", *LAMS]], on=["unit", "date"]).dropna()
    e = e[e.date >= "2019-01-01"]
    print("revealed λ̂50 against λ*30, without storage | with storage:")
    for unit, x in e.groupby("unit"):
        row = {"test": "revealed", "key": unit, "storage": x.storage.mode().iat[0], "n": len(x),
               "offer": x.lambda50.median()}
        for lam in LAMS:
            row |= {f"{lam}": x[lam].median(), f"corr_{lam}": np.corrcoef(x.lambda50, x[lam])[0, 1],
                    f"slope_{lam}": np.polyfit(x[lam], x.lambda50, 1)[0]}
        rows.append(row)

    d = w[w.cls == "hydro"].merge(offered(w), on=["unit", "date"]).dropna(subset=["o50", "ocf", *LAMS])
    print(f"offered: {len(d):,} unit-days, {d.unit.nunique()} units")
    for at in ("o50", "ocf"):
        for (grp, sto), x in d.groupby(["group", d.storage.ne("none").map({True: "storage", False: "none"})]):
            if len(x) < 500:
                continue
            row = {"test": f"offered at {at}", "key": grp, "storage": sto, "n": len(x), "units": x.unit.nunique(),
                   "offer": x[at].median()}
            for lam in LAMS:
                row |= {f"{lam}": x[lam].median(), f"slope_{lam}": within_slope(x, at, lam),
                        f"ratio_{lam}": (x[at] / x[lam]).median()}
            rows.append(row)

    s = d[(d.storage != "none") & d.fill_anom.notna()]
    for at in ("o50", "ocf"):
        for grp, x in s[s[at] > 1].groupby("group"):
            kx = [x.unit, x.date.dt.month]
            f = x.fill_anom - x.groupby(kx).fill_anom.transform("mean")
            row = {"test": f"storage at {at}", "key": grp, "storage": x.storage.mode().iat[0], "n": len(x),
                   "units": x.unit.nunique()}
            for lam in LAMS:
                gap = np.log(x[at] / x[lam])
                gap = gap - gap.groupby(kx).transform("mean")
                row[f"slope_{lam}"] = (gap @ f) / (f @ f)
            rows.append(row)

    t = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    for test, g in t.groupby("test", sort=False):
        print(f"\n{test}:")
        print(g.dropna(axis=1, how="all").drop(columns="test").round(2).to_string(index=False))
    t.to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
