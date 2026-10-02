#!/usr/bin/env python3
"""Link every hydro plant with coordinates (JRC) to the OMIE unit that offers it, by date.

    .venv/bin/python scripts/build/build_hydro_plant_units.py

The own-basin rainfall design needs each firm's hydro by catchment: rain over a
plant's catchment (build_catchment_rain.py) counts for the firm that owns the
plant that day. A plant reaches its owner through the OMIE unit offering it -- a
cascade such as Iberdrola's DUER, dozens of dams in one offer -- and the unit
reaches its owners through lib/unit_ownership.py (by date and by share).

SPAIN: REE's register of physical units (ESIOS archive 81,
`esios_physical_units.parquet`, a 2026-08-12 snapshot) lists every generator group
with the unit that offers it (`up`): DUER's 57 groups, EBRFEN's 104. Groups are
gathered into plants by name (reservoir, run-of-river and pumped-storage
generation); a JRC plant is linked to the REE plant whose name
words all appear in JRC's name and whose capacity is within a factor of 3 of JRC's
(without it, pumped Bolarque II and Portas matched small namesakes) (JRC repeats and decorates names: "Saucelle SAUCE II
1 - Saucelle Hydroelectric Power Plant Spain" holds SAUCELLE). Several candidates:
the most specific name, then the closest capacity. The snapshot is today's
composition, applied to the whole window.

PORTUGAL: REE's register stops at the border. The hand-checked map of
build_storage_hours.py (river plus a capacity sum matching `cab`), dated: the five
Douro dams sold to Movhera are ADOURO's (EDP) to 2021-12-31 and DOUSUP's (Movhera)
from 2022-01-01, when OMIE moved them; Iberdrola's Tamega scheme is TAMEGA's from
its first `cab` declaration. The ~1 GW moved between EDP's ACAVADO and ALIMA in
2024 stays with the plants' original units: both are EDP's.

OUTPUTS (data/omie/registry/):
  hydro_plant_units.parquet   plant_id, unit, start, end (exclusive), method
                              (esios_words / pt_hand), jrc_mw, esios_mw, words
  hydro_unit_coverage.parquet unit, esios_mw, matched_mw, matched_share, n_plants,
                              n_matched: how much of each Spanish unit's REE capacity
                              has a JRC plant (coordinates, hence catchment rain)
"""
from __future__ import annotations

import glob
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from build_storage_hours import AMBIGUOUS, CAVADO, DOURO, LIMA, MONDEGO, MOVHERA_SIX, TEJO  # noqa: E402
from unit_ownership import EARLY, LATE, attach_owners, spells  # noqa: E402

DATA = ROOT / "data"
REG = DATA / "omie/registry"
OUT = REG / "hydro_plant_units.parquet"
COVER = REG / "hydro_unit_coverage.parquet"
JRC = DATA / "jrc_hydro/jrc_hydro_plants.parquet"
UF = DATA / "esios/esios_physical_units.parquet"
HYDRO_TECH = ("Embalse", "Fluyente", "Turbinación bombeo", "Hidráulica - No UGH")
MW_RATIO = 3.0   # a link needs REE capacity within a factor of 3 of JRC's
MOVHERA_MOVE = pd.Timestamp("2022-01-01")
TAMEGA = ["H3677", "H3678", "H3679"]   # Alto Tamega, Gouvaes, Daivoes

STOP = {"HYDROELECTRIC", "HYDRO", "POWER", "PLANT", "SPAIN", "PORTUGAL", "CENTRAL", "HIDROELECTRICA",
        "HIDRAULICA", "GENERACION", "GENERAC", "GEN", "TURBINACION", "TURB", "BOMBEO", "GRUPO", "NTRA", "SRA",
        "DEL", "LAS", "LOS", "EMBASSAMENT", "EMBALSE", "SALTO", "PRESA", "III", "CENTRALE"}


def key(name: str) -> set[str]:
    """The significant words of a plant name: accents, punctuation, group numbers,
    roman numerals, connectives and plant boilerplate removed."""
    s = "".join(c for c in unicodedata.normalize("NFKD", str(name)) if not unicodedata.combining(c)).upper()
    s = re.sub(r"\(.*?\)", " ", s)
    words = re.sub(r"[^A-Z0-9 ]", " ", s).split()
    return {w for w in words if len(w) >= 3 and w.isalpha() and w not in STOP}


def match_words(jrc: set[str], ree: set[str]) -> bool:
    """True when every word of REE's plant name appears in JRC's, allowing one-letter
    spelling differences in long words (ratio >= 0.9)."""
    if not ree:
        return False
    return all(any(w == v or (len(w) >= 6 and SequenceMatcher(None, w, v).ratio() >= 0.9) for v in jrc) for w in ree)


def ree_plants() -> tuple[pd.DataFrame, pd.DataFrame]:
    """REE's hydro groups gathered into plants: up, words (frozenset), esios_mw; and per-unit totals."""
    f = pd.read_parquet(UF)
    f = f[f.tech.isin(HYDRO_TECH) & f.up.notna()].copy()
    f["words"] = f.descr_long.map(lambda s: frozenset(key(s)))
    pl = f.groupby(["up", "words"]).max_power_mw.sum().rename("esios_mw").reset_index()
    tot = f.groupby("up").max_power_mw.sum().rename("esios_mw")
    return pl[pl.words.map(len) > 0], tot


def spain(jrc: pd.DataFrame, pl: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for p in jrc[jrc.country_code == "ES"].itertuples():
        jw = key(p.name)
        cand = pl[pl.words.map(lambda w: match_words(jw, w))]
        r = cand.esios_mw / p.installed_capacity_MW
        cand = cand[(r <= MW_RATIO) & (r >= 1 / MW_RATIO)]
        if cand.empty:
            continue
        cand = cand.assign(n=cand.words.map(len), gap=(cand.esios_mw - p.installed_capacity_MW).abs())
        best = cand.sort_values(["n", "gap"], ascending=[False, True]).iloc[0]
        rows.append({"plant_id": p.id, "unit": best.up, "start": EARLY, "end": LATE, "method": "esios_words",
                     "jrc_mw": p.installed_capacity_MW, "esios_mw": best.esios_mw,
                     "words": " ".join(sorted(best.words)), "gap": best.gap})
    # JRC lists some plants twice (Silvon 81.5 and 80 MW, Doiras 61.9 and 43): one JRC
    # plant per REE plant, the closest in capacity, so no catchment counts twice.
    d = pd.DataFrame(rows).sort_values("gap").drop_duplicates(["unit", "words"])
    return d.drop(columns="gap").sort_values("plant_id").reset_index(drop=True)


def first_cab(unit: str) -> pd.Timestamp:
    for f in sorted(glob.glob(str(DATA / "omie/cab/parquet/cab_*.parquet"))):
        c = pd.read_parquet(f, columns=["date", "unit", "max_power_mw"], filters=[("unit", "==", unit)])
        if (c.max_power_mw > 0).any():
            return pd.Timestamp(c.loc[c.max_power_mw > 0, "date"].min())
    return LATE


def portugal(jrc: pd.DataFrame) -> pd.DataFrame:
    mw = jrc.set_index("id").installed_capacity_MW
    spans = ([(p, "ADOURO", EARLY, LATE) for p in DOURO]
             + [(p, "ADOURO", EARLY, MOVHERA_MOVE) for p in MOVHERA_SIX]
             + [(p, "DOUSUP", MOVHERA_MOVE, LATE) for p in MOVHERA_SIX]
             + [(p, "ALIMA", EARLY, LATE) for p in LIMA] + [(p, "ACAVADO", EARLY, LATE) for p in CAVADO]
             + [(p, "TEMON", EARLY, LATE) for p in TEJO]
             + [(p, "MONDEGO", EARLY, LATE) for p in MONDEGO + AMBIGUOUS]   # Alva and upper Mondego
             + [(p, "GUADIA", EARLY, LATE) for p in ["H52"]])
    t0 = first_cab("TAMEGA")
    spans += [(p, "TAMEGA", t0, LATE) for p in TAMEGA]
    return pd.DataFrame([{"plant_id": p, "unit": u, "start": s, "end": e, "method": "pt_hand",
                          "jrc_mw": mw.get(p), "esios_mw": None, "words": ""} for p, u, s, e in spans])


def owners_of_plants(df: pd.DataFrame, links: pd.DataFrame | None = None, sp: pd.DataFrame | None = None) -> pd.DataFrame:
    """For each (plant_id, date): the plant's unit that day and that unit's owners, with shares."""
    links = pd.read_parquet(OUT) if links is None else links
    m = df.merge(links[["plant_id", "unit", "start", "end"]], on="plant_id")
    m = m[(m.date >= m.start) & (m.date < m.end)].drop(columns=["start", "end"])
    return attach_owners(m, sp if sp is not None else spells(), value_cols=())


def main() -> int:
    jrc = pd.read_parquet(JRC)
    pl, tot = ree_plants()
    es, pt = spain(jrc, pl), portugal(jrc)
    d = pd.concat([es, pt], ignore_index=True)
    REG.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    matched = es.drop_duplicates(["unit", "words"]).groupby("unit").esios_mw.sum()
    n_pl = pl.groupby("up").size()
    n_m = es.drop_duplicates(["unit", "words"]).groupby("unit").size()
    cov = pd.DataFrame({"esios_mw": tot, "matched_mw": matched, "n_plants": n_pl, "n_matched": n_m}).fillna(0.0)
    cov["matched_share"] = (cov.matched_mw / cov.esios_mw).clip(upper=1.0)
    cov = cov.rename_axis("unit").reset_index()
    cov.to_parquet(COVER, index=False)
    es_j = jrc[jrc.country_code == "ES"]
    print(f"Spain: {es.plant_id.nunique()} of {len(es_j)} JRC plants linked "
          f"({es.jrc_mw.sum():,.0f} of {es_j.installed_capacity_MW.sum():,.0f} MW) to {es.unit.nunique()} units")
    print(f"Portugal: {pt.plant_id.nunique()} plants, hand map, {pt.unit.nunique()} units")
    top = cov.sort_values("esios_mw", ascending=False).head(15)
    print("largest Spanish units, REE capacity matched to a JRC plant:\n" + top.round(2).to_string(index=False))
    rev = es.merge(jrc.set_index("id").name, left_on="plant_id", right_index=True)
    rev = rev.sort_values("jrc_mw", ascending=False).head(40)
    print("\nlinks to review (largest 40):\n" + rev[["name", "jrc_mw", "unit", "words", "esios_mw"]].to_string(index=False))
    print(f"\nwrote {OUT.relative_to(ROOT)} ({len(d)} spells), {COVER.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
