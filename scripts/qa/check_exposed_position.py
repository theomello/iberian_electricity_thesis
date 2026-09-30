#!/usr/bin/env python3
"""The pass-through rule matches exactly the regulated suppliers.

    .venv/bin/python scripts/qa/check_exposed_position.py

Framework spec §2.4. Pins the set of OMIE owner strings the rule matches, so a
registry snapshot that adds or renames a regulated supplier fails here instead
of silently changing a firm's net position. Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_owner import exposed_group, is_pass_through, owner_group  # noqa: E402

GROUPS = ROOT / "data/omie/registry/owner_groups.parquet"

# Every owner string in owner_groups.parquet the rule must match (2026-09-30).
EXPECTED = {
    "BASER COMERCIALIZADORA DE REFERENCIA SA",
    "CHC COMERCIALIZADOR DE REFERENCIA, A.L.U.",
    "COMERCIALIZADOR DE REFERENCIA ENERGÉTICO, S.L.U",
    "COMERCIALIZADORA REGULADA GAS POWER, S.A",
    "CURENERGÍA COMERCIALIZADOR DE ÚLTIMO RECURSO, SAU",
    "E.ON COMERC. DE ULTIMO RECURSO, S.L. (REP. RE)",
    "E.ON COMERCIALIZADORA DE ULTIMO RECURSO, S.L.",
    "EDP COMERCIALIZADORA DE ULTIMO RECURSO SA",
    "EDP SERVIÇO UNIVERSAL",
    "ENDESA ENERGIA XXI, S.L.",
    "ENDESA ENERGIA XXI, S.L. (REP. RE)",
    "ENERGÍA XXI COMERCIALIZADORA DE REFERENCIA, S.L.",
    "IBERDROLA COMERC. DE ÚLTIMO RECURSO, SA (REP.RE)",
    "IBERDROLA COMERCIALIZACIÓN DE ÚLTIMO RECURSO, SA",
    "REGSITI COMERCIALIZADORA REGULADA, S.L.U.",
    "SU ELETRICIDADE, S.A.",
    "VIESGO COMERCIALIZADORA DE REFERENCIA, S.L.",
}

# Exposed entities of the five firms, and names that only look regulated.
MUST_NOT = [
    "EDP COMERCIAL COMERCIALIZACAO DE ENERGIA SA", "EDP GEM PORTUGAL S.A.",
    "EDP ESPAÑA, S.A.U. (COMERCIAL)", "IBERDROLA CLIENTES ESPAÑA S.A.U",
    "IBERDROLA ENERGÍA ESPAÑA S..A.", "ENDESA ENERGÍA", "GAS NATURAL COMERCIALIZADORA",
    "REPSOL COMERCIALIZADORA DE ELECTRICIDAD Y GAS SLU", "NEXT ENERGIA XXI SL",
    "MYEN XXI SL", "SERVIGAS S.XXI S.A.", "TRADE UNIVERSAL ENERGY, S.A.",
    "GRUPO ENERGÉTICO ASECOR S.L",
]


def main() -> int:
    fails: list[str] = []
    for s in sorted(EXPECTED):
        if not is_pass_through(s):
            fails.append(f"should match: {s!r}")
        if exposed_group(s) is not None:
            fails.append(f"exposed_group should be None: {s!r}")
    for s in MUST_NOT:
        if is_pass_through(s):
            fails.append(f"should NOT match: {s!r}")
        if exposed_group(s) != owner_group(s):
            fails.append(f"exposed_group should equal owner_group: {s!r}")
    if is_pass_through(None) or is_pass_through("  ") or exposed_group(None) is not None:
        fails.append("null or blank names must give False / None")

    g = pd.read_parquet(GROUPS, columns=["agent_owner"])
    got = set(g.agent_owner[g.agent_owner.map(is_pass_through)])
    for s in sorted(got - EXPECTED):
        fails.append(f"unexpected match in owner_groups: {s!r}")
    for s in sorted(EXPECTED - got):
        fails.append(f"expected string absent from owner_groups: {s!r}")

    print(f"pass-through strings matched in owner_groups: {len(got)} (expected {len(EXPECTED)})")
    for f in fails:
        print(f"  FAIL {f}")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
