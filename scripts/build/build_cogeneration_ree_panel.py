#!/usr/bin/env python3
"""Daily output of every REE programming unit, from the I90DIA workbooks, with cogeneration's fuel attached.

    .venv/bin/python scripts/build/build_cogeneration_ree_panel.py [--force]

Design: docs/specs/2026-11-10-cogeneration-design.md; why REE's units and not OMIE's: notes/rq-cogeneration.md.
For cogeneration REE's programming unit (UP) is the plant, and REE's registers give its fuel; OMIE's offer units are
mostly representatives' numbered units. Reads every workbook on disk (data/esios/raw/archives/34/, fetched by
fetch/fetch_esios_i90.py: the 15th of each month 2019-01 -> 2025-09, and every day 2022-04-01 -> 2023-03-31) from
2021-01 to 2023-12 and writes

  outputs/tables/cogeneration_ree/days/ree_YYYYMMDD.parquet   one row per programming unit with a schedule that day:
      p48_mwh       final schedule (sheet I90DIA02, the workbook's own Total column)
      p48_peak_mw   the largest period of the day, as MW
      pdbf_mwh      day-ahead base schedule (I90DIA26), all transaction types; pdbf_bilateral_mwh of which bilateral
  outputs/tables/cogeneration_ree/ree_units.parquet           one row per programming unit seen:
      tech, fuel (gas / other_fossil / biomass_waste / null), agent, max_power_mw, in_register,
      first_day, last_day, days, peak_mw (largest p48_peak_mw seen)

`tech` comes from REE's programming-unit register (ESIOS archive 82), else from its physical units (archive 81), both
2026-08-12 snapshots: a unit that existed in 2022 and not in 2026 has in_register False and no fuel.
All units are kept, not only cogeneration, so that a plant's earlier unit can be looked for among them.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "esios" / "raw" / "archives" / "34"
OUT = ROOT / "outputs" / "tables" / "cogeneration_ree"
FIRST, LAST = "20210101", "20231231"
FUEL = {"Gas natural cogeneración": "gas",
        "Derivados del petróleo o carbón": "other_fossil", "Fuel": "other_fossil",
        "Turbina vapor - Fuel gas": "other_fossil", "Energía residual": "other_fossil",
        "Biomasa": "biomass_waste", "Biogás": "biomass_waste", "Residuos varios": "biomass_waste",
        "Residuos domésticos y similares": "biomass_waste"}


def _sheet(wb, name: str) -> pd.DataFrame:
    sh = wb.sheet_by_name(name)
    rows = [sh.row_values(r) for r in range(sh.nrows)]
    wb.unload_sheet(name)
    h = next(r for r in range(12) if rows[r] and str(rows[r][0]).strip() == "Unidad de Programación")
    head = [str(c).strip() for c in rows[h]]
    d = pd.DataFrame(rows[h + 1:], columns=head)
    d = d[d["Unidad de Programación"].astype(str).str.strip() != ""]
    d["unit"] = d["Unidad de Programación"].astype(str).str.strip()
    return d


def _periods(d: pd.DataFrame) -> list[str]:
    return [c for c in d.columns if (len(c) == 5 and c[2] == "-") or c.replace(".0", "").isdigit()]


def day(f: Path) -> pd.DataFrame:
    import xlrd
    z = zipfile.ZipFile(f)
    wb = xlrd.open_workbook(file_contents=z.read(z.namelist()[0]), on_demand=True)
    p = _sheet(wb, "I90DIA02")
    per = _periods(p)
    v = p[per].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    p48 = pd.DataFrame({"unit": p.unit.values, "p48_mwh": v.sum(axis=1).values,
                        "p48_peak_mw": v.max(axis=1).values * (len(per) / 24)})
    p48 = p48.groupby("unit", as_index=False).agg(p48_mwh=("p48_mwh", "sum"), p48_peak_mw=("p48_peak_mw", "sum"))
    b = _sheet(wb, "I90DIA26")
    v = b[_periods(b)].apply(pd.to_numeric, errors="coerce").fillna(0.0).sum(axis=1)
    bil = b["Tipo Transacción"].astype(str).str.strip().str.lower().str.startswith("bilateral")
    pdbf = pd.DataFrame({"unit": b.unit.values, "pdbf_mwh": v.values, "pdbf_bilateral_mwh": v.where(bil, 0.0).values})
    pdbf = pdbf.groupby("unit", as_index=False).sum()
    out = p48.merge(pdbf, on="unit", how="outer").fillna(0.0)
    out.insert(0, "date", f.stem[7:11] + "-" + f.stem[11:13] + "-" + f.stem[13:15])
    return out


def units_table(days: pd.DataFrame) -> pd.DataFrame:
    a = pd.read_parquet(ROOT / "data" / "esios" / "esios_programming_units.parquet")[
        ["unit", "tech", "agent", "max_power_mw"]]
    ph = pd.read_parquet(ROOT / "data" / "esios" / "esios_physical_units.parquet")
    ph = ph.groupby("up").agg(tech_uf=("tech", "first"), mw_uf=("max_power_mw", "sum"), agent_uf=("agent", "first"))
    act = days[days.p48_mwh > 0].groupby("unit").agg(first_day=("date", "min"), last_day=("date", "max"),
                                                     days=("date", "nunique"), peak_mw=("p48_peak_mw", "max"))
    u = act.reset_index().merge(a, on="unit", how="left").merge(ph, left_on="unit", right_index=True, how="left")
    u["in_register"] = u.tech.notna() | u.tech_uf.notna()
    u["tech"] = u.tech_uf.fillna(u.tech)  # the physical units name the fuel; the programming register is coarser
    u["agent"] = u.agent.fillna(u.agent_uf)
    u["max_power_mw"] = u.mw_uf.fillna(u.max_power_mw)
    u["fuel"] = u.tech.map(FUEL)
    return u.drop(columns=["tech_uf", "mw_uf", "agent_uf"])


def main() -> int:
    force = "--force" in sys.argv
    (OUT / "days").mkdir(parents=True, exist_ok=True)
    files = [f for f in sorted(RAW.glob("I90DIA_*.zip")) if FIRST <= f.stem[7:15] <= LAST]
    for i, f in enumerate(files):
        o = OUT / "days" / f"ree_{f.stem[7:15]}.parquet"
        if o.exists() and not force:
            continue
        day(f).to_parquet(o, index=False)
        if i % 25 == 0:
            print(f"{f.stem[7:15]} ({i + 1}/{len(files)})", flush=True)
    d = pd.concat(pd.read_parquet(f) for f in sorted((OUT / "days").glob("ree_*.parquet")))
    u = units_table(d)
    u.to_parquet(OUT / "ree_units.parquet", index=False)
    print(f"{d.date.nunique()} days, {len(u):,} programming units with output; in the register: {u.in_register.sum():,}")
    print(u.groupby(u.fuel.fillna("(not cogeneration or unknown)")).agg(units=("unit", "size"),
                                                                       mw=("max_power_mw", "sum")).round(0).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
