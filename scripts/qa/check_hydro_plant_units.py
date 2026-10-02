#!/usr/bin/env python3
"""Hydro plants -> OMIE units -> owners at the time: the link and its coverage.

    .venv/bin/python scripts/qa/check_hydro_plant_units.py

Checks `build/build_hydro_plant_units.py`:
  - name keys and word matching on known pairs (JRC's spellings against REE's);
  - no plant is in two units on the same date;
  - Portugal reproduces the hand-checked map of build_storage_hours.py (capacity
    sums per unit, and the five Douro dams moving from ADOURO to DOUSUP in 2022);
  - geography: each Spanish cascade's matched plants lie in one river basin
    (>= 90% of matched capacity in the main HydroBASINS basin, for the one-river
    cascades; GDLQ, UFGC, VIES and SBEU span rivers) and no JRC plant counted twice;
  - coverage: the share of each large cascade's REE capacity matched to a JRC plant;
  - owners at the time, through lib/unit_ownership: Aldeadavila is Iberdrola's,
    Mequinenza Endesa's, Belesar Naturgy's, Alto Lindoso EDP's, and Miranda EDP's in
    2021 and Movhera's in 2023.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "build"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from build_hydro_plant_units import OUT, key, match_words, owners_of_plants  # noqa: E402

BIG = ("DUER", "TAJO", "SIL", "EBRFEN", "UFMI", "JUCA", "SBEU", "GDLQ", "UFTA", "UFGC", "HCHI", "VIES")
# Units offering one river's cascade. The others span rivers, as REE registers them:
# GDLQ (Guadalquivir plus Guadalfeo and Guadalhorce), UFGC (Esla, Limia, Mino, Ulla),
# VIES (Navia plus Esla), SBEU (Sil plus Eume).
ONE_RIVER = ("DUER", "TAJO", "SIL", "EBRFEN", "UFMI", "JUCA", "UFTA", "HCHI")


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    check(key("Saucelle SAUCE II 1 - Saucelle Hydroelectric Power Plant Spain") == {"SAUCELLE", "SAUCE"},
          f"key drops plant boilerplate and group numbers ({key('Saucelle SAUCE II 1 - Saucelle Hydroelectric Power Plant Spain')})")
    check(match_words({"JM", "ORIOL", "JOSE", "MARIA"}, {"JOSE", "MARIA", "ORIOL"})
          and not match_words({"MUELA"}, {"MEROLA"}), "word matching: contained, not merely similar")

    if not OUT.exists():
        check(False, f"{OUT.relative_to(ROOT)} missing -- run scripts/build/build_hydro_plant_units.py")
        print(f"{len(fails)} failure(s)")
        return 1
    d = pd.read_parquet(OUT)
    jrc = pd.read_parquet(ROOT / "data/jrc_hydro/jrc_hydro_plants.parquet").set_index("id")
    print(f"{len(d)} plant-unit spells, {d.plant_id.nunique()} plants, {d.unit.nunique()} units; "
          f"by method: {d.method.value_counts().to_dict()}")

    # one unit per plant per date
    dup = 0
    for pid, g in d.groupby("plant_id"):
        g = g.sort_values("start")
        dup += int((g.start.iloc[1:].to_numpy() < g.end.iloc[:-1].to_numpy()).sum())
    check(dup == 0, f"no plant in two units on the same date ({dup} overlaps)")

    # Portugal against build_storage_hours
    pt = d[d.method == "pt_hand"]
    def mw(unit, when):
        g = pt[(pt.unit == unit) & (pt.start <= when) & (pt.end > when)]
        return jrc.loc[g.plant_id, "installed_capacity_MW"].sum()
    w21, w23 = pd.Timestamp("2021-06-01"), pd.Timestamp("2023-06-01")
    check(abs(mw("ADOURO", w21) - 2831) < 2 and abs(mw("ADOURO", w23) - 1147) < 2 and abs(mw("DOUSUP", w23) - 1684) < 2,
          f"Portugal: ADOURO 2,831 MW in 2021 and 1,147 in 2023, DOUSUP 1,684 in 2023 "
          f"(got {mw('ADOURO', w21):.0f}, {mw('ADOURO', w23):.0f}, {mw('DOUSUP', w23):.0f})")
    check(abs(mw("GUADIA", w23) - 514) < 2, f"Portugal: GUADIA is Alqueva, 514 MW (got {mw('GUADIA', w23):.0f})")

    # Spain: geography and coverage
    es = d[d.method.isin(["esios_words"])].copy()
    b = pd.read_parquet(ROOT / "data/eobs/plant_catchments.parquet")[["plant_id", "hybas_id"]]
    basins = pd.read_parquet(ROOT / "data/hydrosheds/hybas_iberia_lev12.parquet", columns=["HYBAS_ID", "MAIN_BAS"])
    es = es.merge(b, on="plant_id").merge(basins, left_on="hybas_id", right_on="HYBAS_ID")
    es["mw"] = es.plant_id.map(jrc.installed_capacity_MW)
    share = es.groupby(["unit", "MAIN_BAS"]).mw.sum().groupby("unit").apply(lambda s: s.max() / s.sum())
    big = share.reindex([u for u in BIG if u in share.index])
    print(f"      share of matched capacity in the unit's main basin: {big.round(2).to_dict()}")
    one = share.reindex(list(ONE_RIVER))
    check(one.notna().all() and (one >= 0.90).all(), "each one-river cascade's matched plants lie in that river's basin")
    dup = es.groupby(["unit", "words"]).plant_id.nunique().max()
    check(dup == 1, f"one JRC plant per REE plant (max {dup})")
    cov = pd.read_parquet(OUT.with_name("hydro_unit_coverage.parquet")).set_index("unit")
    cb = cov.reindex([u for u in BIG if u in cov.index]).matched_share
    print(f"      share of REE capacity matched to a JRC plant: {cb.round(2).to_dict()}")
    check(len(cb) >= 10 and cb.median() >= 0.6, "large cascades: median >= 60% of REE capacity matched to JRC plants")

    # owners at the time
    def owner(name_part, when):
        pid = jrc.index[jrc.name.str.upper().str.contains(name_part)][0]
        o = owners_of_plants(pd.DataFrame({"plant_id": [pid], "date": [pd.Timestamp(when)]}))
        return o.sort_values("share", ascending=False).group.iloc[0] if len(o) else None
    got = {n: owner(n, w) for n, w in [("ALDEADAVILA", "2023-06-01"), ("MEQUINENZA", "2023-06-01"),
                                        ("BELESAR", "2023-06-01"), ("ALTO LINDOSO", "2023-06-01"),
                                        ("MIRANDA", "2021-06-01")]}
    got["MIRANDA 2023"] = owner("MIRANDA", "2023-06-01")
    want = {"ALDEADAVILA": "IBERDROLA", "MEQUINENZA": "ENDESA", "BELESAR": "NATURGY", "ALTO LINDOSO": "EDP",
            "MIRANDA": "EDP", "MIRANDA 2023": "MOVHERA"}
    check(got == want, f"owners at the time: {got}")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
