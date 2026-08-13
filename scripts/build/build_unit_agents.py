#!/usr/bin/env python3
"""Map OMIE bidding units to the market agent that controls their offers.

    .venv/bin/python scripts/build/build_unit_agents.py
    .venv/bin/python scripts/build/build_unit_agents.py --month 202401

Writes data/omie/registry/unit_agents.parquet.

WHY THIS EXISTS

Residual demand facing firm i is D(p) - sum of *everyone else's* supply. To
exclude "i's own units" you must know which units are i's. Without that,
only the market-wide residual demand is computable -- the elasticity facing an
infinitesimal participant, which bounds every real firm's price impact from
below but is not a Lerner index for anyone. This file supplies the grouping.

THREE LAYERS, IN DESCENDING ORDER OF EVIDENCE

1. `esios`  -- exact match of the unit code to REE's programming-unit registry,
   which publishes the Sujeto del Mercado directly. Authoritative.
2. `name`   -- the `cab` plant name literally contains an ESIOS agent code, e.g.
   `GREPSC1` is named "REPSB GENERICA VENTA" and REPSB is an agent. Strong, and
   it rescues units REE never registers because it never dispatches them.
3. `prefix` -- a hand-checked mnemonic dictionary for the large commercial
   vehicles that appear in neither. **Only entries justified by evidence in the
   data are encoded here** (the plant name names the firm, or the code is
   unambiguous). Prefixes whose owner could not be established from the data
   are deliberately left out: an unmapped unit is honest, a guessed one
   silently corrupts every market-share and markup figure downstream.

MEASURE COVERAGE ON THE NEAR-MARGINAL BAND, NOT ON TOTAL VOLUME

Price is set at the margin. A unit offering 5 GW at 0 EUR/MWh is inframarginal
in almost every hour and contributes nothing to the slope of residual demand
around the clearing price, while a 200 MW CCGT bidding within a euro of it
contributes a great deal. Total-volume coverage therefore flatters the mapping
for exactly the units that matter least. This script reports both, and the
near-marginal figure is the one that governs whether eta can become a Lerner
index -- it uses the same +/-5 EUR band as
scripts/analysis/residual_demand_slope.py.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = DATA / "omie" / "registry" / "unit_agents.parquet"
OUT_CONF = DATA / "omie" / "registry" / "unit_agents_confirmed.parquet"
BAND = 5.0

# Agent codes that are also ordinary words. Matching these inside a plant name
# produces false positives, so the name layer skips them.
GENERIC_TOKENS = {
    "HYDRO", "ENERG", "SERV", "POWER", "COMER", "SOLAR", "EOLIC", "GAS",
    "CENTRAL", "PLANTA", "UNIDAD", "VENTA", "COMPRA", "GENER", "ELECT",
    "TOTAL", "GRUPO", "IBER", "NORTE", "SUR", "ESTE", "OESTE", "COGEN",
    "DUERO", "EBRO", "TAJO", "JUCAR", "SEGURA", "MINO", "COMPA", "ALUZ",
    "CUENCA", "FABRICA", "FABRICAS", "PENINSULAR",
}

# Layer 3. Each entry records the evidence that justifies it; anything that
# would have been a guess is absent by design and shows up as unmapped.
PREFIX_AGENTS: dict[str, tuple[str, str, str]] = {
    # ---- confirmed: the evidence is inside the data itself ------------------
    "EGV": ("AXPO", "confirmed", 'cab name "AXPO VENTA R. ESPECIAL nnn"'),
    "EGE": ("ACCIONA", "confirmed", 'cab name "AC. GREEN EN. DEV. VENTA RE n"'),
    "EDR": ("ACCIONA", "confirmed", 'cab name "ACCIONA VENTA nnn"'),
    "ACC": ("ACCIONA", "confirmed", 'cab name "AC.GREEN EN. DEV. VENTA RO n"'),
    "WMV": ("WMARK", "confirmed", 'cab name "VENTA EXCED AUTOPROD WMARK nnn"'),

    "GNV": ("GNERA", "confirmed", 'cab name "UOF GNERA MAYOR DE 1MW"'),
    "ECY": ("ECYR", "confirmed", 'cab name "ECYR VENTA REG. ESP. 1"'),
    "GRE": ("REPSB", "confirmed", 'cab name "REPSB GENERICA VENTA"; REPSB is an ESIOS agent'),
    "EBL": ("EBLCO", "confirmed", 'cab name "GENÉRICA VENTA EBLCO" on sibling GEBLCC1'),
    "ENR": ("ENCE", "confirmed", 'cab name "ENCE ENERGIA HUELVA"'),
    "EGP": ("ENEL_GREEN_POWER", "confirmed", 'cab name "EOLICA EEGPEM"'),

    "HCG": ("EDP", "confirmed", 'ESIOS agent "HC G" resolves to "EDP ESPAÑA, S.A."'),

    # ---- inferred: mnemonic plus independent corroboration ------------------
    # None of these is established by the data alone. Each is the mnemonic
    # agreeing with at least one other signal -- the CNMC share gap, or the
    # registration-id clustering. Reported separately so every result can be
    # run with and without them; see --tier in this script.
    "EDP": ("EDP", "inferred", "mnemonic; CNMC shows EDP 13pp short with 0% attributed"),
    "IBE": ("IBERDROLA", "inferred", "mnemonic; CNMC 15.9pp gap; id-neighbours 56% Iberdrola"),
    # "IGN" was assigned to Iberdrola on the mnemonic "Iberdrola Generación"
    # and WITHDRAWN on inspection: across its 55 units the cab names are
    # "UOF XALLAS I", "SOLAR MULA", "GALICIA VENTO", "PE CABEZA MESÁ" and
    # similar -- a mixed wind and small-hydro portfolio. "IBERDROLA" appears
    # nowhere in them and "IGNIS" appears twice, so the prefix is far more
    # likely Ignis Energía. Worth 2.5% of cleared sell volume; left unmapped.
    "GGN": ("NATURGY", "inferred", "mnemonic (Gas Natural); CNMC 4.9pp gap"),
    "NXV": ("NEXUS", "inferred", "CNMC lists Nexus at 4% with 0% attributed; NXV is 3.3%"),
    # The Portuguese river-basin block. In `cab` these carry consecutive
    # registration ids 8600221-8600226 -- ADOURO, ACAVADO, ALIMA, TEMON,
    # GUADIA, MONDEGO -- all first seen 2018-01-01/02 and all named as river
    # systems. One registration batch, so they share a registrant.
    # (the Portuguese river-basin block moved to UNIT_AGENTS -- see below:
    #  a 3-letter prefix caught unrelated units such as ACAPC01 and ALIOC01)
    # TAM (Tâmega) and DOU (Douro Internacional) were assigned to EDP with the
    # rest of the Portuguese hydro and are now WITHDRAWN. Both sit outside the
    # 8600221-226 batch and appear years later: TAMEGA is cab id 8600323 at
    # 1,158.1 MW first seen 2022-01-26, and DOUSUP is id 8601821 first seen
    # 2021-09-09. Those capacities and dates point to ownership changes rather
    # than to the original EDP block, and identifying the new owner needs a
    # source outside this repo. See notes/unmapped-prefixes-to-confirm.md.
    "GED": ("ENDESA", "inferred", "WEAKEST: only the CNMC 11.8pp gap, no name evidence"),

    # ---- Portuguese thermal and hydro, named in cab and documented publicly --
    # cab supplies the plant name; ownership is documented in the trade press
    # and company filings. Each is checked against capacity as well as name.
    "RIB": ("EDP", "inferred", "C.C. Ribatejo; EDP-owned CCGT"),
    "LAR": ("EDP", "inferred", "C.C. Lares; EDP-owned CCGT"),
    "SIN": ("EDP", "inferred", "C.T. Sines coal; EDP. 4 x 295 MW = 1,180 MW vs 1,256 published"),
    "RPG": ("TEJO_ENERGIA", "inferred",
            "C.T. Pego; Tejo Energia = TrustEnergy 56.25% + Endesa Generacion 43.75%. "
            "2 x 292 MW = 584 MW vs 628 published. NOT folded into Endesa: the "
            "bidding entity is the joint venture, and Endesa holds a minority"),
    "RTG": ("TURBOGAS", "inferred", "C.C. Turbogas, Tapada do Outeiro; Turbogas"),
    "DOU": ("MOVHERA", "inferred",
            "Douro Internacional. EDP sold six Douro dams to an Engie-led "
            "consortium (Engie 40 / Credit Agricole 35 / Mirova 25), completed "
            "Dec-2020, vehicle Movhera. Dams total 1.2 GW run-of-river + 0.5 GW "
            "pumped = 1.7 GW; DOUSUP reads 1,709.4 MW and is first seen "
            "2021-09-09, after completion. Capacity and date both match"),
    "TAM": ("IBERDROLA", "inferred",
            "Tamega complex; 1,158.1 MW first seen 2022-01-26 matches "
            "Iberdrola's Tamega gigabattery, commissioned 2022"),
}

# Exact unit codes. Evidence that identifies ONE unit belongs here, not in the
# prefix table: validating the prefix layer against units where ESIOS knows the
# answer showed 3-letter rules catching unrelated codes -- "ACA" was justified
# by ACAVADO but also matched ACAPC01, "ALI" by ALIMA but also ALIOC01.
# Regex rules for evidence that justifies a family of units but not a whole
# 3-letter prefix. "HIS" -> RWE came from a unit named "PE RWE", but the prefix
# also catches HISPE units belonging to a different agent; "GAL" -> GALP
# likewise catches GALAC01. Narrowing to the family the evidence covers took
# the prefix layer from 50% to 79% against ESIOS-known units.
UNIT_PATTERNS: list[tuple[str, str, str, str]] = [
    (r"^HISVD", "RWE", "confirmed", 'cab name "PE RWE" on HISVD units'),
    (r"^GALPW", "GALP", "confirmed", 'GALPWV2 "UNIDADE DE VENDA", PT'),
]

UNIT_AGENTS: dict[str, tuple[str, str, str]] = {
    "ADOURO":  ("EDP", "inferred", "PT river-basin block, cab id 8600221"),
    "ACAVADO": ("EDP", "inferred", "PT river-basin block, cab id 8600222"),
    "ALIMA":   ("EDP", "inferred", "PT river-basin block, cab id 8600223"),
    "TEMON":   ("EDP", "inferred", "PT river-basin block, cab id 8600224"),
    "GUADIA":  ("EDP", "inferred", "PT river-basin block, cab id 8600225"),
    "MONDEGO": ("EDP", "inferred", "PT river-basin block, cab id 8600226"),
}

# Deliberately NOT mapped. Each hypothesis, the evidence for it, and the thing
# that would settle it are written up in notes/unmapped-prefixes-to-confirm.md.
# Do not promote one to an entry here without a source outside this repo.
#
# CNMC's published generation shares (data/cnmc/cnmc_generation_shares.parquet)
# corroborate the dictionary -- AXPO lands at 7.1% against CNMC's 7.0% -- and
# they show which firms the unmapped prefixes must belong to. Resist the
# temptation to assign prefixes so the volumes match: that is curve-fitting,
# and the result could not then be used as evidence about concentration.


# Agent -> parent firm. ESIOS publishes the agent, not the group above it:
# IBEG "IBERDROLA GENERACION", IGNU "IBERDROLA GENERACION NUCLEAR" and IBGT are
# three agents and one firm. Market power is a property of the firm, so the
# agents have to be rolled up. Matched on the **legal name** in archive 83, not
# on the code, so each assignment is evidenced by the name itself.
FIRM_TOKENS: list[tuple[str, str]] = [
    ("IBERDROLA", "IBERDROLA"), ("CURENERG", "IBERDROLA"),
    ("ENDESA", "ENDESA"),
    ("NATURGY", "NATURGY"), ("GAS NATURAL", "NATURGY"),
    ("EDP", "EDP"), ("HIDROCANTABRICO", "EDP"), ("HIDROELECTRICA DEL CANT", "EDP"),
    ("REPSOL", "REPSOL"),
    ("ACCIONA", "ACCIONA"), ("EHN GREEN", "ACCIONA"),
    ("AXPO", "AXPO"),
    ("ENGIE", "ENGIE"),
    ("RWE", "RWE"),
    ("ENEL", "ENEL"),
    ("GALP", "GALP"),
    ("VIESGO", "VIESGO"),
    ("TOTAL", "TOTALENERGIES"), ("TOTALENERGIES", "TOTALENERGIES"),
    ("SHELL", "SHELL"),
    ("BP ", "BP"),
    ("ENCE", "ENCE"),
    ("WIND TO MARKET", "WIND_TO_MARKET"),
    ("NEXUS", "NEXUS"),
    ("CEPSA", "CEPSA"), ("MOEVE", "CEPSA"),
]


# OMIE's own corporate tag in pdbce. Sparse (121 units) but *dated* and
# independent of ESIOS, and 38 of those units are covered by nothing else.
# Each mapping below is corroborated rather than guessed:
GROUP_TAG_FIRMS: dict[str, tuple[str, str]] = {
    "IB":  ("IBERDROLA", "mnemonic"),
    "GN":  ("NATURGY", "mnemonic (Gas Natural)"),
    "REP": ("REPSOL", "mnemonic"),
    "GE":  ("ENDESA", "carried by Ascó/Vandellós, which are Endesa units"),
    "HC":  ("EDP", 'ESIOS archive 83: agent "HC G" = "EDP ESPAÑA, S.A."'),
    "EHN": ("ACCIONA", 'archive 83 lists "EHN GREEN ENERGY DEVELOPMENT"'),
    # EV, EGL and DET are left out: no corroboration in any source here.
}


def firm_of(name: str) -> str | None:
    if not isinstance(name, str):
        return None
    u = name.upper()
    for token, firm in FIRM_TOKENS:
        if token in u:
            return firm
    return None


# Technology from the cab plant name, for the ~86% of units ESIOS never
# registers. Ordered: the first pattern that matches wins, so the specific
# prefixes come before the loose keyword fallbacks.
TECH_PATTERNS: list[tuple[str, str]] = [
    (r"^C\.?N\.?\b|CENTRAL NUCLEAR", "nuclear"),
    (r"^C\.?C\.?\b|CICLO COMBINADO", "combined_cycle"),
    (r"^C\.?T\.?\b|T[EÉ]RMICA|CARB[OÓ]N|HULLA", "thermal"),
    (r"\bC\.?H\.?B\.?\b|BOMBEO", "pumped_storage"),
    # Hydro is named after rivers and basins as often as by technology, and
    # missing those understated hydro badly in the marginal-technology counts:
    # ALIMA "LIMA", ACAVADO "CAVADO", TEMON "SISTEMA TEJO-MONDEGO",
    # GUADIA "BACIA HID. DO GUADIANA", DOUSUP "DOURO INTERNACIONAL" all read as
    # unknown before these patterns were added.
    (r"UOF HIDRO|\bC\.?H\.?\b|HIDRO|HIDR[AÁ]ULIC|\bHIDRA\b|BACIA\s+HID|"
     r"\bMINI\s*HID|SALTO|EMBALSE|AZUD|\bPRESA\b", "hydro"),
    (r"\bDOURO\b|\bTAMEGA\b|\bT[AÂ]MEGA\b|\bCAVADO\b|\bC[AÁ]VADO\b|\bLIMA\b|"
     r"\bMONDEGO\b|\bGUADIANA\b|\bTEJO\b|\bZEZERE\b|\bZ[EÊ]ZERE\b|"
     r"\bSABOR\b|\bTUA\b|\bALQUEVA\b", "hydro"),
    (r"\bP\.?S\.?\b|\bFV\b|FOTOVOLT|SOLAR", "solar"),
    (r"\bP\.?E\.?\b|E[OÓ]LIC", "wind"),
    (r"BIOMASA|BIOG[AÁ]S", "biomass"),
    (r"COGENERA|\bCOG\b", "cogeneration"),
    (r"RESIDUOS|\bR\.?S\.?U\.?\b|VALORIZA", "waste"),
    (r"BATER[IÍ]A|ALMACENAM", "storage"),
]

# The regime is a coarser partition than technology, and a far better covered
# one. Regimen Especial is the Spanish special regime -- renewables,
# cogeneration and waste; Regimen Ordinario is conventional thermal, hydro and
# nuclear. Hundreds of aggregation vehicles name their regime without naming a
# technology ("AXPO VENTA R. ESPECIAL 042"), and for the marginal-technology
# question that still rules out half the stack. Kept in its own column rather
# than folded into tech_cab: it is a different, weaker claim.
REGIME_PATTERNS: list[tuple[str, str]] = [
    (r"R[EÉ]G(IMEN|\.)?\s*ESP|R\.\s*ESPECIAL|\bREG\.?\s*ESP|"
     r"VENTA\s+R\.?E\b|VENDA\s+R\.?E\b|\bR\.?E\.?\s*\d|VGERE|"
     r"EXCED.*AUTOPROD|AUTOPROD", "special"),
    (r"R[EÉ]G(IMEN|\.)?\s*ORD|\bREG\.?\s*ORD|VENTA\s+R\.?O\b|\bR\.?O\.?\s*\d",
     "ordinary"),
]

# Technologies that sit inside the special regime, used to derive the regime
# from a known technology without re-reading the name.
SPECIAL_REGIME_TECH = {"solar", "solar_thermal", "wind", "biomass",
                       "cogeneration", "waste"}
ORDINARY_REGIME_TECH = {"nuclear", "combined_cycle", "thermal", "hydro",
                        "hydro_ugh", "hydro_ror", "pumped_storage"}

# ESIOS publishes its own Spanish technology vocabulary, which is NOT the one
# tech_from_name produces. Mixing the two silently counted 350 retailer units
# as having a "technology" and left 41 UGH hydro units without a regime, so
# normalise ESIOS onto the cab vocabulary before combining them.
ESIOS_TECH_MAP = {
    "Solar fotovoltaica": "solar",
    "Solar térmica": "solar_thermal",
    "Eólica terrestre": "wind",
    "Eólica marina": "wind",
    # ESIOS distinguishes the three hydro classes that matter for a water-value
    # design: UGH is a managed storage group, Fluyente is run-of-river.
    "Hidráulica UGH": "hydro_ugh",
    "Embalse": "hydro_ugh",
    "Fluyente": "hydro_ror",
    "Hidráulica - No UGH": "hydro_ror",
    "Turbinación bombeo": "pumped_storage",
    "Consumo bombeo": "pumped_storage",
    "Ciclo combinado": "combined_cycle",
    "Nuclear": "nuclear",
    "Carbón": "thermal",
    "Derivados del petróleo ó carbón": "thermal",
    "Derivados del petróleo o carbón": "thermal",
    "Gas Natural": "thermal",
    "Gas natural cogeneración": "cogeneration",
    "Gas Natural Cogeneración": "cogeneration",
    "Cogeneración": "cogeneration",
    "Biogás": "biomass",
    "Biomasa": "biomass",
    "Residuos": "waste",
    "Batería electroquímica": "storage",
    "Almacenamiento": "storage",
}

# ESIOS categories that are not a generation technology at all. Counting these
# as covered inflates technology coverage with demand and interconnection.
ESIOS_NON_GENERATION = {
    "Comercializadores mercado libre", "Comercializadores último recurso",
    "Consumos directos en mercado", "Consumo de Servicios Auxiliares",
    # Generic and portfolio labels are ESIOS declining to state a technology.
    "Genéricas", "Porfolio", "Portfolio",
}


def normalise_esios_tech(t: str | None) -> str | None:
    """Map an ESIOS technology onto the cab vocabulary, or None if it is not a
    generation technology (demand, interconnection, or an explicit non-answer)."""
    if not isinstance(t, str) or not t.strip():
        return None
    t = t.strip()
    if t in ESIOS_NON_GENERATION:
        return None
    if t.startswith(("Importación", "Exportación", "Enlace")):
        return None
    return ESIOS_TECH_MAP.get(t)


def tech_from_name(descr: str) -> str | None:
    if not isinstance(descr, str) or not descr.strip():
        return None
    u = descr.upper()
    for pat, tech in TECH_PATTERNS:
        if re.search(pat, u):
            return tech
    return None


def regime_from_name(descr: str) -> str | None:
    if not isinstance(descr, str) or not descr.strip():
        return None
    u = descr.upper()
    for pat, regime in REGIME_PATTERNS:
        if re.search(pat, u):
            return regime
    return None


def alpha_prefix(unit: str, n: int = 3) -> str:
    return re.sub(r"[0-9]", "", str(unit))[:n]


def build(month: str, tier: str = "all") -> pd.DataFrame:
    esios = pq.read_table(DATA / "esios" / "esios_programming_units.parquet").to_pandas()
    agents = {a.upper() for a in esios.agent.dropna().unique() if len(a.strip()) >= 3}
    by_code = dict(zip(esios.unit, esios.agent))
    tech_by_code = dict(zip(esios.unit, esios.tech))

    # Read EVERY cab month, not one. A single month names only the units active
    # in it: January 2024 covers 2,241 units, the full archive 7,357. Units that
    # entered or left outside the sample month were invisible to the name layer,
    # which is why coverage was weakest in 2025-2026 -- those units simply had no
    # name to match against. Names like "ENDG GENERICA COMPRA" and "IBERDROLA
    # CLIENTES COMPRA" sit in other months and resolve immediately.
    cab_files = sorted((DATA / "omie" / "cab" / "parquet").glob("cab_*.parquet"))
    parts = [pq.read_table(f, columns=["unit", "descr", "max_power_mw"]).to_pandas()
             for f in cab_files]
    cab_all = pd.concat(parts, ignore_index=True)
    cab_all = cab_all[cab_all.descr.astype(str).str.strip().ne("")]
    cab = cab_all.groupby("unit").agg(descr=("descr", "last"),
                                      max_power_mw=("max_power_mw", "max"))

    reg = pq.read_table(DATA / "omie" / "registry" / "unit_registry.parquet").to_pandas()
    df = reg[["unit", "country", "role", "net_cleared_mwh"]].copy()
    df["descr"] = df.unit.map(cab.descr).fillna("")
    df["max_power_mw"] = df.unit.map(cab.max_power_mw)
    df["prefix"] = df.unit.map(alpha_prefix)

    def from_name(d: str) -> str | None:
        """An ESIOS agent code appearing inside the cab plant name.

        Some agent codes are ordinary Spanish words and match plant
        descriptions rather than owners: HYDRO is a real agent code, so
        "HYDRO CUENCA EBRO" resolved to HYDRO when the unit belongs to ASIE.
        Validation against ESIOS-known units put this layer at 74% before the
        blocklist. Tokens below are excluded outright.
        """
        for tok in re.findall(r"[A-Z0-9]{3,}", d.upper()):
            if tok in agents and tok not in GENERIC_TOKENS:
                return tok
        return None

    def firm_from_name(d: str) -> str | None:
        """A firm's own name written into the plant name.

        `BRR1R` is called "AXPO VENTA R. ORD. (LOS BARRIOS)" -- the firm is
        stated outright, but the agent-code matcher missed it because AXPO is
        not itself an ESIOS agent code (AXPOP is). Only multi-word or
        distinctive company names are used; generic words like HIDRO or SOLAR
        would match plant descriptions rather than owners.
        """
        if not isinstance(d, str):
            return None
        u = d.upper()
        for token, firm in FIRM_TOKENS:
            if len(token) >= 4 and token in u:
                return firm
        return None

    df["agent_esios"] = df.unit.map(by_code)
    df["_agent_name_src"] = df.descr.map(from_name)
    def by_pattern(unit: str, idx: int):
        for pat, firm, tier, _ in UNIT_PATTERNS:
            if re.match(pat, str(unit)):
                return (firm, tier)[idx]
        return None

    df["agent_unit"] = df.unit.map(lambda u: UNIT_AGENTS.get(u, (None, None, None))[0])
    df["agent_prefix"] = (df.unit.map(lambda u: UNIT_AGENTS.get(u, (None, None, None))[0])
        .fillna(df.unit.map(lambda u: by_pattern(u, 0)))
        .fillna(df.prefix.map(lambda p: PREFIX_AGENTS.get(p, (None, None, None))[0])))
    df["prefix_tier"] = (df.unit.map(lambda u: UNIT_AGENTS.get(u, (None, None, None))[1])
        .fillna(df.unit.map(lambda u: by_pattern(u, 1)))
        .fillna(df.prefix.map(lambda p: PREFIX_AGENTS.get(p, (None, None, None))[1])))
    if tier == "confirmed":
        drop = df.prefix_tier.eq("inferred")
        df.loc[drop, "agent_prefix"] = None

    df["firm_tag"] = df.unit.map(
        dict(zip(reg.unit, reg.group_tag))).map(
        lambda t: GROUP_TAG_FIRMS.get(t, (None, None))[0] if pd.notna(t) else None)

    df["agent"] = df.agent_esios.fillna(df._agent_name_src).fillna(df.agent_prefix)
    df["source"] = (
        df.agent_esios.notna().map({True: "esios", False: None})
        .fillna(df._agent_name_src.notna().map({True: "name", False: None}))
        .fillna(df.agent_prefix.notna().map({True: "prefix", False: None})))
    df["confidence"] = (df.source.map({"esios": "authoritative", "name": "confirmed"})
                        .fillna(df.prefix_tier)
                        .fillna(df.firm_tag.notna().map({True: "group_tag", False: None})))
    df["tech_esios"] = df.unit.map(tech_by_code)
    df["tech_cab"] = df.descr.map(tech_from_name)
    # ESIOS raw label kept in tech_esios for traceability; tech is the single
    # normalised vocabulary and is the column analysis should use.
    df["tech"] = df.tech_cab.fillna(df.tech_esios.map(normalise_esios_tech))
    # A known technology implies its regime; otherwise read the regime off the
    # name. Technology first, so the stronger evidence wins.
    df["regime"] = (
        df.tech.map(lambda t: "special" if t in SPECIAL_REGIME_TECH
                    else ("ordinary" if t in ORDINARY_REGIME_TECH else None))
        .fillna(df.descr.map(regime_from_name)))

    # Roll agents up to the firm, using archive 83's legal names as evidence.
    sm_path = DATA / "esios" / "esios_market_subjects.parquet"
    if sm_path.exists():
        sm = pq.read_table(sm_path).to_pandas()
        name_by_agent = dict(zip(sm.agent, sm.name))
        type_by_agent = dict(zip(sm.agent, sm.type))
        df["agent_name"] = df.agent.map(name_by_agent)
        df["agent_type"] = df.agent.map(type_by_agent)
        # Layer-3 labels are already firm names, so fall back to the label.
        # An agent that belongs to no major group is not unmapped -- it is a
        # small independent firm, and for residual demand that is exactly what
        # it is. Requiring membership of one of the 17 majors would discard the
        # decision-maker we actually need. So: roll up to the group where one
        # exists, otherwise the agent stands as its own firm.
        df["firm_group"] = (df.agent_name.map(firm_of)
                              .fillna(df.agent.map(firm_of))
                              .fillna(df.firm_tag))
        # Firm stated in the plant name; used only where nothing stronger applies.
        df["firm_named"] = df.descr.map(firm_from_name)
        df["firm"] = df.firm_group.fillna(df.firm_named).fillna(df.agent)
        df["is_major"] = df.firm_group.notna() | df.firm_named.notna()
    return df.drop(columns=["agent_esios", "agent_prefix", "_agent_name_src"], errors="ignore")


def near_marginal_coverage(month: str, mapped: set[str]) -> None:
    """Coverage weighted by offers sitting within BAND of the clearing price."""
    b = pq.read_table(DATA / "omie" / "bids" / "parquet" / f"bids_{month}.parquet",
                      columns=["date", "period", "unit", "side", "status",
                               "power_mw", "price_eur_mwh"]).to_pandas()
    px = pq.read_table(DATA / "omie" / "prices" / "omie_day_ahead_prices.parquet",
                       columns=["date", "period", "price_es", "price_pt"]).to_pandas()
    px = px[px.price_es == px.price_pt]          # no single curve when the market splits
    o = b[(b.status == "O") & (b.side == "V")].merge(px, on=["date", "period"])
    o["known"] = o.unit.isin(mapped)
    near = o[(o.price_eur_mwh - o.price_es).abs() <= BAND]
    priced = o[o.price_eur_mwh > 0]
    taker = o[o.price_eur_mwh <= 0]
    print(f"\n  coverage of OFFERED sell volume, {month}")
    for lab, s in (("all offered", o), (f"near-marginal (+/-{BAND:g} EUR)", near),
                   ("priced above 0", priced), ("price takers (<=0)", taker)):
        w = s.power_mw
        print(f"    {lab:28s}: {w[s.known].sum() / w.sum():6.1%}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", default="202401", help="YYYYMM used for cab names and coverage")
    ap.add_argument("--tier", choices=["all", "confirmed"], default="all",
                    help="'confirmed' drops the inferred prefix assignments")
    args = ap.parse_args()

    df = build(args.month, args.tier)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT if args.tier == 'all' else OUT_CONF, index=False)

    gen = df[df.role.isin(["generation", "generation_large", "storage_mixed", "pumping"])]
    vol = gen.net_cleared_mwh.abs().fillna(0)
    tot = vol.sum()
    print(f"wrote {OUT.relative_to(DATA.parent)}  {len(df):,} units")
    print(f"\n  mapped {df.agent.notna().sum():,} of {len(df):,} units")
    print(f"  by source: {df.source.value_counts(dropna=False).to_dict()}")
    print(f"\n  generation-side volume covered: "
          f"{vol[gen.agent.notna()].sum() / tot:.1%}")
    print(f"  distinct agents on the generation side: {gen.agent.nunique()}")

    if "firm" in df.columns:
        g2 = df[df.role.isin(["generation", "generation_large", "storage_mixed", "pumping"])]
        v2 = g2.net_cleared_mwh.abs().fillna(0)
        print(f"\n  rolled up to {g2.firm.nunique()} parent firms; "
              f"{v2[g2.firm.notna()].sum() / tot:.1%} of generation volume has one")
        top = (g2.assign(v=v2).groupby("firm").v.sum() / tot).sort_values(ascending=False).head(8)
        for f, s_ in top.items():
            print(f"    {f:16s} {s_:6.2%}")

    gg = df[df.role.isin(["generation", "generation_large", "storage_mixed", "pumping"])]
    vv = gg.net_cleared_mwh.abs().fillna(0)
    print(f"\n  technology from cab names: {gg.tech_cab.notna().sum():,} of {len(gg):,} "
          f"generation units ({vv[gg.tech_cab.notna()].sum() / tot:.1%} of volume)")
    print(f"  technology, cab + esios:   {gg.tech.notna().sum():,} of {len(gg):,} "
          f"({vv[gg.tech.notna()].sum() / tot:.1%} of volume)")
    print(f"  regime (special/ordinary): {gg.regime.notna().sum():,} of {len(gg):,} "
          f"({vv[gg.regime.notna()].sum() / tot:.1%} of volume)   "
          + "  ".join(f"{k}:{v}" for k, v in gg.regime.value_counts().items()))
    print("   " + "  ".join(f"{k}:{v}" for k, v in
                            gg.tech_cab.value_counts().head(8).items()))

    near_marginal_coverage(args.month, set(df.loc[df.agent.notna(), "unit"]))

    unmapped = gen[gen.agent.isna()].assign(v=vol[gen.agent.isna()])
    top = (unmapped.groupby("prefix").v.sum().sort_values(ascending=False).head(8) / tot)
    print(f"\n  largest unmapped prefixes (share of generation volume):")
    for p, s in top.items():
        print(f"    {p:5s} {s:6.2%}")
    print("\n  These are unmapped on purpose -- see PREFIX_AGENTS in this file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
