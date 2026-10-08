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

NET OF CONTRACTS (§5.5). Iberdrola, Endesa and, from 2022, Naturgy deliver most of their
hydro under bilateral contracts (PDBF role 4), outside the auction. The auction curve then
covers what is left, so ocf_net reads it at the share the water left after the contracts
would fill (pooled over the month; `offered`). Example: a unit expecting 100 MWh of water
on a day sells 70 bilaterally and offers 150 MWh in the auction; ocf_net reads the curve
at 30 / 150 = 20%. `net of contracts` compares ocf and ocf_net on the same days.
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
AT = ("o50", "ocf", "ocf_net", "ocf_day")
SIX = ["EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL", "MOVHERA"]
ZERO = 1.0           # €/MWh


def bilateral(ym: str, units: list[str]) -> pd.DataFrame:
    """unit, date, bil: MWh the unit delivers that day under bilateral contracts (PDBF role 4,
    outside the auction)."""
    p = pd.read_parquet(ROOT / f"data/omie/pdbf/parquet/pdbf_{ym}.parquet",
                        columns=["date", "unit", "role_code", "schedule_mw", "resolution_min"],
                        filters=[("unit", "in", units), ("role_code", "==", "4")])
    p["bil"] = p.schedule_mw * p.resolution_min / 60
    p["date"] = pd.to_datetime(p.date)
    return p.groupby(["unit", "date"], as_index=False).bil.sum()


def day_hours(dates: pd.Series) -> pd.Series:
    """Hours in each Madrid calendar day: 23 or 25 on the DST days."""
    d = pd.DatetimeIndex(dates)
    return pd.Series(((d + pd.Timedelta(days=1)).tz_localize("Europe/Madrid") - d.tz_localize("Europe/Madrid"))
                     / pd.Timedelta(hours=1), index=dates.index)


def read_at(h: pd.DataFrame, r: str) -> pd.Series:
    """(unit, date) -> price of the first step at which the cumulative offered share reaches
    column r (capped at 1); none where r ≤ 0."""
    return h[(h[r] > 0) & (h.cum >= h[r].clip(upper=1) - 1e-9)].groupby(["unit", "date"]).price.first()


def offered(w: pd.DataFrame, net: bool = False) -> pd.DataFrame:
    """unit, date, o50, ocf: the price at half of the unit's offered hydro volume that day,
    and at its expected running share cf_s.

    net=True adds the read point net of bilateral contracts. The unit's expected water is
    cf_s × max power × hours; what its bilateral contracts (PDBF role 4) deliver is gone
    before the auction, so the auction offer is read at the share the rest would fill:
      r_net   (expected water − bilateral MWh) / offered MWh, pooled over the month (the
              cost is a 30-day value, and contracts move volume between days)
      r_day   the same for the day alone
    ocf_net and ocf_day read the curve there, capped at the top step; none when the
    contracts take all the expected water (r ≤ 0). Also bil, the day's bilateral MWh, and
    contracted, the month's bilateral MWh over its expected water."""
    w = w.assign(ym=w.date.dt.strftime("%Y%m"))
    parts = []
    for f in sorted(CACHE.glob("hydro_2*.parquet")):
        h = pd.read_parquet(f, columns=["date", "unit", "price", "mw", "cap_mw", "withdrawn"])
        h = h[~h.withdrawn & (h.mw > 0)]
        h["date"] = pd.to_datetime(h.date)
        h = h.merge(w[["unit", "date", "cf_s"]], on=["unit", "date"]).sort_values(["unit", "date", "price"])
        g = h.groupby(["unit", "date"])
        h["cum"] = g.mw.cumsum() / g.mw.transform("sum")
        out = [h[h.cum >= 0.5].groupby(["unit", "date"]).price.first().rename("o50"),
               h[h.cum >= h.cf_s].groupby(["unit", "date"]).price.first().rename("ocf")]
        if net:
            ym = f.stem.split("_")[1]
            u = g.agg(o=("mw", "sum"), cap=("cap_mw", "max"), cf_s=("cf_s", "first")).reset_index()
            b = bilateral(ym, u.unit.unique().tolist())
            u = u.merge(b, on=["unit", "date"], how="left").fillna({"bil": 0.0})
            u["r_day"] = (u.cf_s * u.cap * day_hours(u.date) - u.bil) / u.o
            # the month: expected water and contracts over every day, offers over the days offered
            cap = u.groupby("unit").cap.max()
            m = w[(w.ym == ym) & w.unit.isin(cap.index)]
            water = (m.cf_s * m.unit.map(cap) * day_hours(m.date)).groupby(m.unit).sum()
            bil = b.groupby("unit").bil.sum().reindex(water.index).fillna(0.0)
            u["r_net"] = u.unit.map((water - bil) / u.groupby("unit").o.sum())
            u["contracted"] = u.unit.map(bil / water)
            h = h.merge(u[["unit", "date", "r_net", "r_day"]], on=["unit", "date"])
            out += [read_at(h, "r_net").rename("ocf_net"), read_at(h, "r_day").rename("ocf_day"),
                    u.set_index(["unit", "date"])[["r_net", "r_day", "bil", "contracted"]]]
        parts.append(pd.concat(out, axis=1))
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

    d = w[w.cls == "hydro"].merge(offered(w, net=True), on=["unit", "date"]).dropna(subset=["o50", "ocf", *LAMS])
    print(f"offered: {len(d):,} unit-days, {d.unit.nunique()} units")
    for at in AT:
        for (grp, sto), x in d.groupby(["group", d.storage.ne("none").map({True: "storage", False: "none"})]):
            if len(x) < 500:
                continue
            row = {"test": f"offered at {at}", "key": grp, "storage": sto, "n": x[at].notna().sum(),
                   "units": x.unit.nunique(), "offer": x[at].median()}
            if at in ("ocf_net", "ocf_day"):
                r = "r_net" if at == "ocf_net" else "r_day"
                row |= {"cf_s": x.cf_s.median(), "r": x[r].median(), "r_le0": (x[r] <= 0).mean(),
                        "contracted": x.contracted.median()}
            x = x.dropna(subset=[at])
            for lam in LAMS:
                row |= {f"{lam}": x[lam].median(), f"slope_{lam}": within_slope(x, at, lam),
                        f"ratio_{lam}": (x[at] / x[lam]).median()}
            row["ratio_lam30s_above1"] = (x[at] / x.lam30s)[x[at] > ZERO].median()
            rows.append(row)

    # storage units of the six groups: offer over λ*30s at cf_s and net of contracts, on the
    # same days (both read points defined and above €1), and the days the contracts take it all
    y = d[(d.storage != "none") & d.group.isin(SIX) & (d.lam30s > 0)]
    for grp, x in y.groupby("group"):
        for yr, z in [("all", x), *x.groupby(x.date.dt.year)]:
            b = z[(z.ocf > ZERO) & (z.ocf_net > ZERO)]
            if len(b) < 100:
                continue
            rows.append({"test": "net of contracts", "key": grp, "year": yr, "n": len(b),
                         "ratio_ocf": (b.ocf / b.lam30s).median(), "ratio_ocf_net": (b.ocf_net / b.lam30s).median(),
                         "cf_s": z.cf_s.median(), "r": z.r_net.median(), "contracted": z.contracted.median(),
                         "r_le0": (z.r_net <= 0).mean(), "r_gt1": (z.r_net > 1).mean(),
                         "ratio_ocf_contracted": (z.ocf / z.lam30s)[z.r_net <= 0].median()})

    s = d[(d.storage != "none") & d.fill_anom.notna()]
    for at in AT:
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
