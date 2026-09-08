#!/usr/bin/env python3
"""Roll OMIE's published `agent_owner` up to corporate groups.

Shared by `build/build_contract_position.py`, `analysis/residual_demand_firm.py`
and `analysis/firm_shares_hourly.py`.

`agent_owner` (OMIE's *Listado de Unidades*) covers far more units than the
inference chain in `build_unit_agents.py` -- 100% of contracted sell MW against
74-94% -- but it names **legal entities and does no roll-up**, so one firm
appears as several competitors. This module supplies the roll-up.

THE MAPPING IS BUILT, NOT GUESSED. `build/build_owner_groups.py` derives it from
three layers of evidence -- the independent ESIOS chain's verdict on an entity's
own units, a stem match onto a group that layer established, and a short
hand-verified table -- and leaves anything unproven standing as its own group.
Read that file before trusting a grouping; it prints its refusals.

Until 2026-09-04 this module instead took the first surviving token of the
owner name. That was explicitly diagnostic-only and it was wrong in ways that
mattered: it read `SU ELETRICIDADE` (7.3% of supply volume) as a firm rather
than as EDP, and split Repsol across three entities. The built mapping is used
when present; the heuristic remains only as a fallback so a missing artefact
degrades visibly rather than crashing a downstream run.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
GROUPS = ROOT / "data" / "omie" / "registry" / "owner_groups.parquet"

_MAP: dict[str, str] | None = None
_WARNED = False

_NOISE = re.compile(
    r"\b(SAU|SLU|SA|SL|SAS|SCA|SGPS|LIMITED|LTD|GMBH|BV|PLC|INC|"
    r"ESPANA|IBERIA|PORTUGAL|ESPANOLA|GENERACION|COMERCIALIZADORA|"
    r"COMERCIALIZADOR|COMERCIALIZACION|RENOVABLES|RENOVABLE|SERVICIOS|"
    r"ELECTRICA|ELECTRICIDAD|ELETRICIDADE|ENERGIA|ENERGIAS|ENERGY|ENERGIE|"
    r"POWER|GROUP|GRUPO|TRADING|MARKETS|PRODUCCION|GESTION|DESARROLLO|"
    r"DESARROLLOS|IBERICA|GLOBAL|ULTIMO|RECURSO|REFERENCIA|CLIENTES|"
    r"SUMINISTRO)\b", re.I)
_CONNECTIVES = re.compile(r"\b(DE|DEL|DA|DO|DOS|DAS|LA|EL|LOS|LAS|Y|E|AND)\b", re.I)


def _fallback(name: str) -> str | None:
    s = "".join(c for c in unicodedata.normalize("NFKD", str(name))
                if not unicodedata.combining(c)).upper()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = _CONNECTIVES.sub(" ", _NOISE.sub(" ", s))
    parts = [p for p in s.split() if len(p) >= 3 and not p.isdigit()]
    if not parts:
        return None
    return f"{parts[0]} {parts[1]}" if len(parts[0]) <= 4 and len(parts) > 1 else parts[0]


def _load() -> dict[str, str]:
    global _MAP, _WARNED
    if _MAP is None:
        if GROUPS.exists():
            g = pd.read_parquet(GROUPS, columns=["agent_owner", "group"])
            _MAP = dict(zip(g.agent_owner, g["group"]))
        else:
            _MAP = {}
            if not _WARNED:
                print(f"  NOTE: {GROUPS.name} missing -- falling back to the "
                      "first-token heuristic; run build_owner_groups.py --save")
                _WARNED = True
    return _MAP


def owner_group(name: str | None) -> str | None:
    """Corporate group for one OMIE `agent_owner` string, or None."""
    if not isinstance(name, str) or not name.strip():
        return None
    m = _load()
    if name in m:
        return m[name]
    return _fallback(name)
