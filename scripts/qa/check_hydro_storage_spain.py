#!/usr/bin/env python3
"""Spanish hydro storage: REE's national series (ESIOS 623) and MITECO's reservoirs by basin.

    .venv/bin/python scripts/fetch/fetch_esios_spain.py --ids 623 --geo 0 --start 2018-01-01 --end <today>
    .venv/bin/python scripts/qa/check_hydro_storage_spain.py

ESIOS 623 is described as the weekly mean stored hydro energy (MWh) "of each market
agent", but the API returns one peninsular series (`disaggregated: False`). So the
per-firm split has to come from MITECO's weekly reservoir volumes, by hydrographic
demarcation: the large Spanish hydro units (UGH, Unidad de Gestión Hidráulica) are
registered by basin ("UGH. DUERO", "UGH. UF-MIÑO", "UGH. TER").

Checks:
  1. ESIOS 623 is weekly, stamped on Mondays, and tracks MITECO's peninsular total
     (levels and weekly changes);
  2. each unit's monthly capacity factor (PDBF output over `cab` max power, as in
     `build/build_water_value_forward.py`) moves with its own basin's fill, against the
     national series and against every other basin (placebo). Anomalies are taken
     against the calendar month's mean.
Prints the table; exits non-zero if check 1 fails or own basin ranks first for fewer
than half the units.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "build"))
import build_water_value_forward as wv  # noqa: E402

DATA = ROOT / "data"

# unit -> MITECO demarcations holding its reservoirs, read off the `cab` names
BASIN = {
    "DUER": ["Duero"], "TAJO": ["Tajo"], "SIL": ["Miño - Sil"], "JUCA": ["Júcar"],
    "EBRA": ["Ebro"],                                                    # Iberdrola
    "EBRFEN": ["Ebro"], "SBEU": ["Miño - Sil", "Galicia Costa"], "GDLQ": ["Guadalquivir"],
    "GDNA": ["Guadiana"], "TERE": ["Cuencas Internas de Cataluña"], "TEES": ["Duero"],  # Endesa
    "UFMI": ["Miño - Sil"], "UFTA": ["Tajo"], "UFGC": ["Galicia Costa"],  # Naturgy
    "HCHI": ["Cantábrico Occidental"],                                   # EDP
    "VIES": ["Cantábrico Occidental", "Cantábrico Oriental"],            # Repsol (Viesgo)
}


def esios() -> pd.Series:
    e = pd.read_parquet(DATA / "esios/esios_623.parquet")
    e["date"] = pd.to_datetime(e.datetime.str[:10])
    return e.set_index("date").value.sort_index()


def miteco() -> pd.DataFrame:
    m = pd.read_parquet(DATA / "miteco/embalses_historico.parquet")
    m["date"] = pd.to_datetime(m.date)
    return m[m.date >= "2017-06-01"]


def check_national(e: pd.Series, m: pd.DataFrame) -> bool:
    ok = True
    gaps = e.index.to_series().diff().dt.days.dropna()
    print(f"ESIOS 623: {len(e)} weeks {e.index.min():%Y-%m-%d} -> {e.index.max():%Y-%m-%d}, "
          f"weekdays {sorted(set(e.index.day_name()))}, gaps over 7 days at "
          f"{[f'{d:%Y-%m-%d}' for d in gaps[gaps > 7].index]}")
    ok &= set(e.index.day_name()) == {"Monday"}
    tot = m.groupby("date").stored_hm3.sum().rename("miteco")
    j = pd.merge_asof(e.rename("esios").reset_index(), tot.reset_index().rename(columns={"date": "mdate"}),
                      left_on="date", right_on="mdate", direction="nearest", tolerance=pd.Timedelta(days=3))
    j = j.dropna()
    lev, chg = j[["esios", "miteco"]].corr().iloc[0, 1], j[["esios", "miteco"]].diff().corr().iloc[0, 1]
    print(f"  against MITECO's total ({len(j)} weeks, MITECO dated {sorted((j.mdate - j.date).dt.days.unique())} "
          f"days later): level corr {lev:.3f}, weekly change corr {chg:.3f}")
    for s in (-1, 1):
        print(f"    ESIOS shifted {s:+d} week: change corr "
              f"{j.miteco.diff().corr(j.esios.shift(s).diff()):.3f}")
    ok &= lev > 0.85 and chg > 0.8
    return ok


def basin_fill(m: pd.DataFrame, basins: list[str]) -> pd.Series:
    g = m[m.ambito.isin(basins)].groupby(m.date.dt.to_period("M"))[["stored_hm3", "capacity_hm3"]].sum()
    return g.stored_hm3 / g.capacity_hm3


def check_basins(e: pd.Series, m: pd.DataFrame) -> bool:
    cf = wv.capacity_factors(list(BASIN))
    cf.index = pd.PeriodIndex.from_fields(year=cf.year, month=cf.month, freq="M")
    nat = e.groupby(e.index.to_period("M")).mean()
    basins = sorted(m.ambito.unique())
    rows = []
    for u, own in BASIN.items():
        d = pd.concat([cf[cf.unit == u].cf.rename("cf"), basin_fill(m, own).rename("own"),
                       nat.rename("nat")], axis=1).dropna()
        mo = d.index.month
        a = d - d.groupby(mo).transform("mean")
        r_own = a.cf.corr(a.own)
        plac = []
        for b in basins:
            if b in own:
                continue
            f = basin_fill(m, [b]).reindex(d.index)
            if f.notna().sum() >= 30 and f.std() > 0:
                plac.append(a.cf.corr(f - f.groupby(mo).transform("mean")))
        rows.append(dict(unit=u, basin=" + ".join(own), months=len(d), own=r_own, national=a.cf.corr(a.nat),
                         placebo_median=np.median(plac), rank=1 + sum(p > r_own for p in plac), of=len(plac) + 1))
    r = pd.DataFrame(rows)
    print("\nmonthly capacity-factor anomaly against fill anomaly (correlation):")
    print(r.round(2).to_string(index=False))
    first = (r["rank"] == 1).mean()
    print(f"\nown basin ranks first for {(r['rank'] == 1).sum()} of {len(r)} units, top three for "
          f"{(r['rank'] <= 3).sum()}; beats the national series for {(r.own > r.national).sum()}")
    return first >= 0.5


def main() -> int:
    e, m = esios(), miteco()
    ok = check_national(e, m)
    ok &= check_basins(e, m)
    print("\nOK" if ok else "\nFAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
