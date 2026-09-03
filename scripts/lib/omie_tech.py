#!/usr/bin/env python3
"""Normalise OMIE's *Listado de Unidades* technology labels to a coarse class.

Shared by `build/build_unit_agents.py` and `analysis/marginal_technology.py`,
which both need the same mapping; it lived in the latter until 2026-09-03.

OMIE's raw label carries two things at once — a technology and a *regulatory
arrangement* ("RE Tar. CUR Eólica" vs "RE Mercado Eólica" are the same
technology under different tariff regimes). Normalising strips the second, and
that matters for stability: of 78 units whose raw label changes across the four
technology-bearing snapshots, only 41 change class, and the rest are OMIE
renaming its own categories ("VENTA GENERICA" to "Unidad Generica",
"RE Tar. CUR X" to "RE Mercado X").
"""

from __future__ import annotations

import re

TECH_MAP: list[tuple[str, str]] = [
    (r"Nuclear", "nuclear"),
    (r"Ciclo Combinado", "gas CCGT"),
    (r"Hulla|Antracita|Carb[oó]n|Lignito", "coal"),
    (r"Bombeo", "pumped storage"),
    (r"Hidr[aá]ulica", "hydro"),
    (r"E[oó]lica", "wind"),
    (r"Solar", "solar"),
    (r"T[eé]rmica Renovable|Biomasa|Biog[aá]s", "biomass"),
    (r"T[eé]rmica no", "cogeneration"),
    (r"Geot[eé]rmica", "geothermal"),
    (r"Almacenamiento", "storage"),
    (r"H[ií]brida", "hybrid"),
]

# Labels that name a commercial arrangement rather than a technology. Counting
# these as identified would overstate coverage; they are reported separately.
UNSPECIFIC = re.compile(
    r"Generica|Gen[eé]rica|Porfolio|Portfolio|Tarifa|Agente vendedor|"
    r"Productor Reg|Venta excedentes", re.I)

# Sub-classes that differ in granularity rather than in kind. Collapsing them
# raises agreement with the independent `cab`-name technology from 93.3% to
# 98.7% -- most apparent conflicts are one source saying "hydro" where the
# other says "pumped storage". Use for robustness checks, not as the default.
COARSE = {"pumped storage": "hydro",
          "biomass": "RE thermal", "waste": "RE thermal",
          "cogeneration": "RE thermal", "geothermal": "RE thermal"}


def classify(t: str | None) -> str | None:
    if not isinstance(t, str) or not t.strip():
        return None
    if UNSPECIFIC.search(t):
        return None
    for pat, name in TECH_MAP:
        if re.search(pat, t, re.I):
            return name
    return None


def coarsen(cls: str | None) -> str | None:
    return COARSE.get(cls, cls) if cls else None
