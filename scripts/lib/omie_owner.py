#!/usr/bin/env python3
"""Roll OMIE's published `agent_owner` up to something firm-like.

Shared by `build/build_contract_position.py`, `analysis/residual_demand_firm.py`
and `analysis/firm_shares_hourly.py`; it lived in the last of those until
2026-09-04.

WHY THIS IS NEEDED AND WHY IT IS WEAK

`agent_owner` (OMIE's *Listado de Unidades*) covers far more units than the
inference chain in `build_unit_agents.py` -- 100% of contracted sell MW against
74-93% -- but it names **legal entities and does no roll-up**, where the chain's
`firm` column rolls agents up through ESIOS legal names. Without this, one firm
appears as several competitors.

The first-token heuristic is crude by design and is **presentation-level, not
evidence**: it will merge unrelated firms sharing a first word and split a group
whose entities are named differently. Use it for coverage and trend diagnostics.
Before publishing share *levels* from it, build a real group mapping.
"""

from __future__ import annotations

import re

# Legal-entity suffixes and divisional words to strip when rolling OMIE's
# published owner up to something firm-like. "REPSOL SERVICIOS RENOVABLES,
# S.A.", "REPSOL GENERACION ELECTRICA, S.L.U." and "REPSOL GENERACION
# ELECTRICA, S.A" are three registrations of one firm; without this they are
# three competitors. Deliberately crude -- it collapses 84 owners of plant
# >=50 MW to 67 groups -- and it is presentation-level, not evidence.
_OWNER_NOISE = re.compile(
    r"\b(S\.?A\.?U?|S\.?L\.?U?|SLU|SAU|SA|SL|ESPANA|ESPAÑA|IBERIA|"
    r"GENERACION|GENERACIÓN|RENOVABLES|SERVICIOS|ELECTRICA|ELÉCTRICA|"
    r"ENERGIA|ENERGÍA|POWER|GROUP|COMERCIALIZADORA|PRODUCCION|PRODUCCIÓN)\b",
    re.I)


# Entities whose first token does not name their group. Each is corroborated
# TWICE and independently -- by the unit codes themselves and by the ESIOS-based
# inference chain in unit_agents.parquet -- not by outside knowledge:
#
#   SU ELETRICIDADE  4 units, all PT, coded EDPSVD1-3; chain says EDP  4/4
#   GAS NATURAL     49 units, coded ACE4/BES4/ALZ1;    chain says NATURGY 44/49
#   ENERGIA XXI     14 units, coded E21VD*;            chain says ENDESA/EEXXI
#   CURENERGIA      11 units, coded IBCUC01/ICUVD*;    chain says IBERDROLA 11/11
#
# They matter: on 2023 cleared sell volume SU is 7.96%, GAS 2.83%. Left
# unaliased they appear as separate firms and understate EDP and Naturgy.
# This list is NOT exhaustive -- see the docstring on grouping.
OWNER_ALIASES = {
    "SU": "EDP",
    "GAS": "NATURGY",
    "XXI": "ENDESA",
    "CURENERG": "IBERDROLA",
}


def owner_group(name: str | None) -> str | None:
    """First surviving token of OMIE's published owner name.

    Not a corporate-structure mapping: it will merge unrelated firms sharing a
    first word and will split a group whose entities are named differently.
    Use it for coverage and trend diagnostics, not for a published share table.
    """
    if not isinstance(name, str) or not name.strip():
        return None
    t = _OWNER_NOISE.sub(" ", name.upper())
    t = re.sub(r"[^A-Z ]", " ", t)
    t = " ".join(t.split())
    if not t:
        return None
    g = t.split(" ")[0][:12]
    return OWNER_ALIASES.get(g, g)


