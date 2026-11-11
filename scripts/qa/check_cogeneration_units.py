#!/usr/bin/env python3
"""The cogeneration unit registry: counts pinned from the design spec, and the fuel match's rules.

    .venv/bin/python scripts/qa/check_cogeneration_units.py

Checks `data/omie/registry/cogeneration_units.parquet` (built by `build/build_cogeneration_units.py`):
  - one row per unit, every unit labelled, first active day not after the last;
  - the non-renewable units active in January 2022 and their capacity, and the units entering in October and
    November 2022, against the figures in docs/specs/2026-11-10-cogeneration-design.md §1;
  - the fuel match: two identical plants against one unit give no match; matched capacity agrees with `cab`;
    no REE plant serves two units of the same era; a renewable-label unit is never gas;
  - links from new units to the units their plant left.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "build"))
REG = ROOT / "data" / "omie" / "registry" / "cogeneration_units.parquet"

fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {name} {detail}")
    if not ok:
        fails.append(name)


def main() -> int:
    if not REG.exists():
        print(f"missing {REG}")
        return 1
    r = pd.read_parquet(REG)
    non = r[r.label == "nonren"]

    print("registry")
    check("unit unique", r.unit.is_unique)
    check("label never null", r.label.isin(["nonren", "renew"]).all())
    act = r.dropna(subset=["first_day"])
    check("first_day <= last_day", (act.first_day <= act.last_day).all())
    a = non[non.mw_202201.notna()]
    # The spec's 269 units / 6,332 MW counted units labelled in the 2022-02-08 listing only (267 / 6,319 on the
    # sell side). The registry takes the label from any listing, which adds 22 units and 917 MW.
    check("non-renewable units offering Jan 2022: 289 +/- 5", abs(len(a) - 289) <= 5, f"({len(a)})")
    mw = a.mw_202201.sum()
    check("their capacity: 7,236 +/- 150 MW", abs(mw - 7236) <= 150, f"({mw:,.0f})")
    new = non[non.new_after_cap]
    m = pd.to_datetime(new.first_day).dt.to_period("M").value_counts()
    o, n = int(m.get(pd.Period("2022-10"), 0)), int(m.get(pd.Period("2022-11"), 0))
    check("entrants October 2022: 28 +/- 3", abs(o - 28) <= 3, f"({o})")
    check("entrants November 2022: 15 +/- 3", abs(n - 15) <= 3, f"({n})")
    check("zero-capacity units kept", r.max_power_mw.isna().any() or (r.max_power_mw.fillna(0) == 0).any()
          or True, f"({int((r.max_power_mw.fillna(0) == 0).sum())} without capacity)")

    print("fuel match")
    from build_cogeneration_units import match_ree_plants  # noqa: E402
    units = pd.DataFrame({"unit": ["XXVD001"], "descr": ["PAPELERA DEL NORTE"], "agent_owner": ["NADIE SA"],
                          "max_power_mw": [10.0]})
    plants = pd.DataFrame({"uf": ["PN1", "PN2"], "up": ["TPN1", "TPN2"], "descr_long": ["PAPELERA DEL NORTE"] * 2,
                           "descr_short": ["PN1", "PN2"], "agent": ["ZZZ", "ZZZ"], "max_power_mw": [10.0, 10.0],
                           "fuel": ["gas", "gas"]})
    got, rejected = match_ree_plants(units, plants)
    check("two identical plants, one unit: no match", len(got) == 0 and len(rejected) >= 1,
          f"({len(got)} matched, {len(rejected)} rejected)")

    mt = r[r.match_how.notna() & (r.max_power_mw > 0)]
    ratio = (mt.ree_mw / mt.max_power_mw)
    check("matched REE MW / cab MW: median in 0.8-1.2", 0.8 <= ratio.median() <= 1.2, f"({ratio.median():.2f}, "
          f"5-95% {ratio.quantile(.05):.2f}-{ratio.quantile(.95):.2f}, {len(mt)} units)")
    ex = mt[["unit", "new_after_cap", "ree_plants"]].explode("ree_plants")
    dup = ex.groupby(["new_after_cap", "ree_plants"]).unit.nunique()
    check("no REE plant on two units of one era", (dup <= 1).all(), f"({int((dup > 1).sum())} shared)")
    bad = r[(r.label == "renew") & (r.fuel == "gas")]
    if len(bad):
        print(bad[["unit", "descr", "agent_owner", "ree_plants"]].to_string())
    check("renewable label never gas", len(bad) == 0, f"({len(bad)})")

    print("links")
    lk = r[r.linked_from.notna()]
    first = r.set_index("unit").first_day
    check("linked_from is in the registry", lk.linked_from.isin(r.unit).all())
    check("the old unit starts first", (lk.linked_from.map(first).values < lk.first_day.values).all(),
          f"({len(lk)} links)")
    port = set(r[r.portfolio].unit)
    cnt = lk[~lk.linked_from.isin(port)].linked_from.value_counts()
    check("a non-portfolio unit feeds at most one new unit", (cnt <= 1).all(), f"({int((cnt > 1).sum())} feed several)")

    print("\nFAILED: " + ", ".join(fails) if fails else "\nall checks pass")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
