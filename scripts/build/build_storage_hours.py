#!/usr/bin/env python3
"""Storage-hours per hydro market unit: stored energy over declared capacity.

    .venv/bin/python scripts/fetch/fetch_jrc_hydro_database.py   # input
    .venv/bin/python scripts/build/build_storage_hours.py

Item 4 of `notes/rq-midday-hydro.md` §7. How many hours of full output a unit's
reservoirs hold decides whether its water value can be constant within the day
(assumption A1 of `docs/specs/2026-09-29-water-value-design.md`) and how large
the competitive confounder in the day-level conduct test is (§7, item 10).

SCOPE: the auction-route storage units in Portugal -- EDP's six Portuguese
cascades and Movhera's Douro Internacional. Spain's are not built: the JRC
database gives a storage figure for only 30% of Spanish reservoir plants and a
volume or height for fewer, and MITECO's volumes carry no head.

PLANTS TO UNITS, hand-checked. An OMIE unit is a cascade, not a plant, and no
source publishes its plant list. Each assignment below rests on the plant lying
on the unit's named river AND the plants' summed capacity matching the unit's
declared `cab` max power. Plants that fit neither test are left out, and
AMBIGUOUS plants are carried both ways.

  ALIMA  to 2024-02: Alto Lindoso + Touvedo, 652 MW = cab 652.
  ACAVADO to 2024-02: nine Cavado/Rabagao/Homem plants, 1,648 MW vs cab 1,632.
  From 2024-03 about 1,000 MW of offered volume moves from ACAVADO to ALIMA
  (cab: 1,632 -> 632 and 652 -> 1,652), and which plants moved is not
  published, so from then the two are reported as ONE pair.
  ADOURO from 2022: eight national-Douro plants, 1,147 MW = cab 1,147 (2022).
  ADOURO to 2021, plus the five later sold to Movhera: 2,831 vs cab 2,849.
  DOUSUP (Movhera) from 2022: Miranda, Picote, Bemposta, Baixo Sabor, Foz Tua,
  1,684 MW vs cab 1,709.
  GUADIA: Alqueva, 514 MW vs cab 508.
  TEMON: the seven Tejo/Zezere plants, 591 MW vs cab 703-708.
  MONDEGO: Aguieira + Raiva, 360 MW vs cab 435-462.
  AMBIGUOUS between TEMON and MONDEGO: Caldeirao (upper Mondego) and the four
  Serra da Estrela plants (Alva, a Mondego tributary), 110 MW. Either way the two
  units come out ~80-110 MW short of cab, so plants are missing from the JRC list.

STORED ENERGY PER PLANT, a LOWER BOUND:

  E = max(JRC storage_capacity_MWh, 2.316 * dam_height_m * volume_Mm3)

2.316 = 1000 kg/m3 * 9.81 * 0.85 efficiency / 3.6e9 J/MWh * 1e6 m3/Mm3. The
formula uses the dam height as the head, which understates high-head diversion
plants (Alto Lindoso: formula 88,700 MWh, JRC 224,600), and it ignores the
downstream heads the same water passes through in a cascade. JRC's figure is
taken where it is larger; for pumped storage it is often only the pumping cycle
(Alqueva 5,800 MWh on a 4,150 hm3 reservoir), which the max() guards against.
Run-of-river plants (HROR) with no figure count as zero. Reservoir or pumped
plants with neither figure are MISSING, and their capacity share is reported.
Plants sharing one reservoir (Venda Nova with Frades I and II; Salamonde I and
II) count it once, at the largest figure.

KNOWN UNDERSTATEMENT: Alto Rabagao, the Cavado cascade's largest reservoir, has
no volume or height in the JRC file, only a storage of 8,160 MWh that looks like
a pumping cycle. So Cavado's figure, and the pair's after 2024-02, is a floor.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
JRC = DATA / "jrc_hydro/jrc_hydro_plants.parquet"
CAB = DATA / "omie/cab/parquet"
OUT = DATA / "jrc_hydro/storage_hours.parquet"
K = 2.316   # MWh per (m of head x Mm3), at 85% efficiency

MOVHERA_SIX = ["H104", "H76", "H79", "H286", "H3329"]   # Miranda, Picote, Bemposta, Baixo Sabor, Foz Tua
DOURO = ["H185", "H271", "H263", "H358", "H240", "H437", "H1272", "H756"]
CAVADO = ["H800", "H410", "H675", "H250", "H32", "H219", "H714", "H936", "H558"]
LIMA = ["H42", "H1332"]
TEJO = ["H475", "H916", "H955", "H310", "H386", "H611", "H1234"]
MONDEGO = ["H122", "H1299"]
AMBIGUOUS = ["H968", "H1613", "H1612", "H1373", "H1309"]   # Caldeirao, Serra da Estrela

# (unit label, cab units whose capacity is the denominator, plants, first, last)
SPELLS: list[tuple[str, list[str], list[str], str, str]] = [
    ("ALIMA", ["ALIMA"], LIMA, "2018-01", "2024-02"),
    ("ACAVADO", ["ACAVADO"], CAVADO, "2018-01", "2024-02"),
    ("ACAVADO+ALIMA", ["ACAVADO", "ALIMA"], CAVADO + LIMA, "2024-03", "2026-06"),
    ("ADOURO", ["ADOURO"], DOURO + MOVHERA_SIX, "2018-01", "2021-12"),
    ("ADOURO", ["ADOURO"], DOURO, "2022-01", "2026-06"),
    ("DOUSUP", ["DOUSUP"], MOVHERA_SIX, "2022-01", "2026-06"),
    ("GUADIA", ["GUADIA"], ["H52"], "2018-01", "2026-06"),
    ("TEMON", ["TEMON"], TEJO, "2018-01", "2026-06"),
    ("TEMON (+ambiguous)", ["TEMON"], TEJO + AMBIGUOUS, "2018-01", "2026-06"),
    ("MONDEGO", ["MONDEGO"], MONDEGO, "2018-01", "2026-06"),
    ("MONDEGO (+ambiguous)", ["MONDEGO"], MONDEGO + AMBIGUOUS, "2018-01", "2026-06"),
]
# Reservoirs shared by several plants: counted once, at the largest figure.
SHARED = {"H558": "venda_nova", "H250": "venda_nova", "H32": "venda_nova",
          "H936": "salamonde", "H219": "salamonde"}


def plant_energy() -> pd.DataFrame:
    j = pd.read_parquet(JRC).set_index("id")
    f = K * j.dam_height_m * j.volume_Mm3
    e = pd.concat([j.storage_capacity_MWh, f], axis=1).max(axis=1, skipna=True)
    e = e.where(e.notna(), np.where(j.type == "HROR", 0.0, np.nan))
    return pd.DataFrame({"name": j.name.str.slice(0, 30), "type": j.type,
                         "mw": j.installed_capacity_MW, "e_jrc": j.storage_capacity_MWh,
                         "e_formula": f, "e_mwh": e})


def cab_capacity() -> pd.DataFrame:
    parts = []
    for p in sorted(CAB.glob("cab_*.parquet")):
        c = pd.read_parquet(p, columns=["unit", "max_power_mw"])
        c = c[c.unit.isin(["ALIMA", "ACAVADO", "ADOURO", "DOUSUP", "GUADIA", "TEMON", "MONDEGO"])]
        if not c.empty:
            parts.append(c.groupby("unit").max_power_mw.median().rename(p.stem[4:]))
    t = pd.concat(parts, axis=1).T
    t.index = pd.PeriodIndex(t.index, freq="M")
    return t


def build() -> pd.DataFrame:
    pe = plant_energy()
    cap = cab_capacity()
    rows = []
    for label, cab_units, plants, first, last in SPELLS:
        p = pe.loc[plants].copy()
        p["res"] = [SHARED.get(i, i) for i in p.index]
        e = p.groupby("res").e_mwh.max(min_count=1)
        # Missing only if the plant's reservoir has no figure from any plant sharing it.
        missing_mw = p.loc[p.res.map(e).isna(), "mw"].sum()
        months = pd.period_range(first, last, freq="M")
        c = cap.reindex(months)[cab_units].sum(axis=1, min_count=1)
        rows.append({"unit": label, "first": first, "last": last,
                     "plants": len(p), "jrc_mw": p.mw.sum(), "cab_mw": c.median(),
                     "storage_mwh": e.sum(), "missing_mw_share": missing_mw / p.mw.sum(),
                     "hours": e.sum() / c.median()})
    t = pd.DataFrame(rows)
    t["days"] = t.hours / 24
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t.to_parquet(OUT, index=False)
    return t


def main() -> int:
    t = build()
    pe = plant_energy()
    print("PLANTS USED, stored energy MWh (lower bound)")
    used = sorted({i for _, _, ps, _, _ in SPELLS for i in ps})
    print(pe.loc[used, ["name", "type", "mw", "e_jrc", "e_formula", "e_mwh"]].round(0).to_string())
    print("\nSTORAGE-HOURS PER UNIT (lower bound: own dam height as head, missing plants as zero)")
    print(t.round({"jrc_mw": 0, "cab_mw": 0, "storage_mwh": 0, "missing_mw_share": 2,
                   "hours": 0, "days": 1}).to_string(index=False))
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
