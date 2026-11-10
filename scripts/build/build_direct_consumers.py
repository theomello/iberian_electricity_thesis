#!/usr/bin/env python3
"""Registry of direct market consumers: every unit that buys in the day-ahead market for its own consumption
rather than through a retailer.

    .venv/bin/python scripts/build/build_direct_consumers.py

Universe: units OMIE's *Listado de Unidades* types CONSUMIDOR DIRECTO in any snapshot, plus units ESIOS archive 82
types "Consum. directos a mercado". Writes data/omie/registry/direct_consumers.parquet, one row per unit:

- descr, agent_owner, omie_kind: OMIE's label from the latest listing naming the unit (its `technology` column).
- kind: what the unit's bids describe.
    own          a consumer bidding its own load (owner = consumer)
    represented  a representative bidding for one named consumer (the description names the consumer)
    portfolio    a representative or aggregator bidding for several consumers, or an unnamed code; not one load
    balance      demand-response / balance units ("Compras Cons. Directo Balance", SRAD)
    auxiliary    generators' own consumption (auxiliary services); belongs with the supply side
- consumer: the consumer's name (owner for `own`, description for `represented`, blank otherwise).
- group: the owner's evidence-based group, else the legal entity; consumer_generates: that firm owns >= 50 MW of\n  supply units (own and balance kinds).
- own_gen_group: consumers whose own legal entity also sells generation in OMIE (on-site cogeneration, biomass, solar),
  matched by name, owner and ESIOS physical unit and checked pair by pair (2026-11-09); OWN_GEN lists the sell units.
  Net purchases of a group = its consumer units' purchases minus its own-generation units' sales.
- sector: keyword rule on the consumer's name; blank when no rule fires.
- sample: process, weather_exposed, refinery, unclassified (own + represented only), else out.
- first_seen, last_seen, days_cab: from OMIE `cab` (days with an offer header); mwh_YYYY: PDBF scheduled energy.
"""
from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_owner import _norm  # noqa: E402

OUT = ROOT / "data" / "omie" / "registry" / "direct_consumers.parquet"
SUPPLY_ROLES = {"generation", "generation_large", "storage_mixed", "pumping"}

AUX_KINDS = {"Compras Consumos Auxiliares", "Consumo de productores", "Rep. Consumos Auxiliares"}
AUX_WORDS = re.compile(r"\b(SSAA|SS AA|CCAA|AUX|AUXILIAR|AUXILIARES|SERV AUX|SERVICIOS AUXILIARES)\b")
BALANCE_WORDS = re.compile(r"\b(SRAD|BALANCE|GESTION DEMANDA)\b")
# owner names that mark an energy company bidding on behalf of others
ENERGY_OWNER = re.compile(r"ENERG|POWER|ELECTRIC|AXPO|WIND TO MARKET|COMERCIALIZ|TRADING|MARKET|GAS Y ELECTRICIDAD|"
                          r"EFICIENCIA|RENOVABLE|UTILITIES|NEXUS|GESTERNOVA|IGNIS|CLIENTES")
CODE_DESCR = re.compile(r"^[A-Z]{2,7}\s?\d{1,3}[A-Z]?\d*$|^UNIDAD\s?\d+$|UOF|PORTAFOLIO|PORFOLIO|COMPRA ?ENERGIA|"
                        r"REPRES|\bREP\b|AGENTE|BAJA TENSION|CONSUMIDOR DIRECTO|CONSDIRECTO|COMPRA CD|UO COMPRA|"
                        r"UNIDAD (DE )?(COMPRA|PROGRAMACION)|EXENCION|DIRECTA$|^CD\d|^UP\b")

SECTORS = [  # first match wins; on the normalised consumer name
    ("refining_petrochem", r"PETROLEO|REFIN|REPSOL|CEPSA|PETRONOR|BP OIL|LNG|ENAGAS"),
    ("steel", r"ACER|SIDER|CELSA|ARCELOR|MEGASA|LAMINACION|GERDAU|TUBACEX|FERRALL|FORJA|SIDENOR"),
    ("aluminium_metals", r"ALUMIN|ALCOA|ZINC|ASTURIANA DE ZINC|ATLANTIC COPPER|COBRE|METAL|FUNDIC|FERROATL|FERROGLOBE"),
    ("chemicals", r"QUIMIC|ERCROS|CLORO|SOLVAY|GASES|AIR LIQUIDE|PRAXAIR|MESSER|CARBUROS|HIDROGEN|FERTIBERIA|"
                  r"ABONOS|PLASTIFICANT|POLIM"),
    ("cement_minerals", r"DOLOMIT|CALER|CALCIN|\bCAL\b|CEMENT|CALES|YESO|CERAMIC|ARCILL|ARIDOS|CANTERA|LADRILL|MINER|MARMOL|GRANIT|TEJAS"),
    ("glass", r"VIDRI|GLASS|CRISTAL"),
    ("paper_wood", r"\bENCE\b|GOMA CAMPS|PAPEL|PAPER|CARTON|CELULOS|MADER|TABLER|SERRER"),
    ("plastics_rubber", r"PLAST|CAUCHO|POLIET|EMBALAJ|ENVASE|FILM"),
    ("textiles", r"\bTEX\b|HISPANO TEX|UNITEX|TEXTIL|FIBRA|HILATUR|TINTOR"),
    ("food_agri", r"ALIMENT|GUISSONA|MATADERO|ESCORXADOR|CARNIC|LACTE|LECHE|QUESO|PESCA|CONSERV|FRUT|HORTIC|"
                  r"BODEGA|VINO|ACEIT|HARIN|PIENSO|AZUCAR|CERVEZ|ZUMO|JIJONENC|ALMENDRA|MIEL|AVICOL|PORCIN|FRIGORIF|"
                  r"CONGELAD|GRANJA|COOPERATIVA|SAT\b|AGRARI|AGRICOL"),
    ("water_irrigation", r"REGANTE|RIEGO|AGUA|CANAL|DESALA|DEPURA|HIDRAUL|ACUIFER"),
    ("public_transport", r"AYUNTAMIENTO|AYTO|SALUD|ALUMBRADO|ADIF|RENFE|METRO|PUERTO|AEROPUERT|AENA|HOSPITAL|UNIVERSI|"
                         r"DIPUTACION|GENERALITAT|JUNTA|CONSELL|MINISTERIO"),
    ("retail_services", r"TELECOR|CORTE INGLES|DATA|TELEFON|TELECOM|CENTRO DE DATOS|HOTEL|COMERCIAL|DISTRIBUC|LOGIST|SUPERMERC|MERCADONA"),
    ("automotive_machinery", r"AUTOMO|SEAT|RENAULT|FORD|VOLKSWAGEN|MOTOR|LINAMAR|MANDRILAD|MECANIZ|MAQUIN|"
                             r"COMPONENT|INDUSTRIAS"),
]


# Checked by hand against the unit name, owner and public information; the largest units by volume. (kind, consumer,
# sector); None keeps the rule's value.
HAND = {
    "TLCRC01": ("own", "TELECOR (EL CORTE INGLES)", "retail_services"),
    "CELRC01": ("represented", "CELSA", "steel"),
    "CELSR01": ("balance", "CELSA", "steel"),
    "EENRC02": ("represented", "ENCE PONTEVEDRA + NAVIA", "paper_wood"),
    "ENERC03": ("represented", "ENCE PONTEVEDRA + NAVIA", "paper_wood"),
    "RECRC19": ("represented", "SERVICIO EXTREMENO DE SALUD", "public_transport"),
    "SCRUR01": ("balance", "ALUMINA ESPANOLA", "aluminium_metals"),
    "SCRUC01": ("own", "ALUMINA ESPANOLA", "aluminium_metals"),
    "DOLRC01": ("own", "DOLOMITAS DEL NORTE", "cement_minerals"),
    "URBRC04": ("represented", "AYUNTAMIENTO DE ZARAGOZA", "public_transport"),
    "COGRC01": ("represented", "CORPORACION ALIMENTARIA GUISSONA", "food_agri"),
    "GUISR01": ("balance", "CORPORACION ALIMENTARIA GUISSONA", "food_agri"),
    "CUPRC01": ("own", "CUPIRE PADESA", None),
    "MELUC01": ("own", "HISPANO TEX", "textiles"),
    "SEDAC01": ("own", "UNITEX", "textiles"),
    "GOCAC01": ("own", "GOMA CAMPS", "paper_wood"),
    "RECRC11": ("represented", "ALUMASA", "aluminium_metals"),
    "RECRC21": ("represented", "MAFRESA", None),
    "TRARC01": ("own", "TRADEBE", "waste"),
    "CALEC01": ("own", "CALERA DE ALZO", "cement_minerals"),
    "CACRC01": ("own", "CALCINOR", "cement_minerals"),
    "SPBBC01": ("own", "THE SPB GLOBAL CORPORATION", "chemicals"),
    "REPQC01": ("own", "REPSOL QUIMICA", "refining_petrochem"),
    "LLARC01": ("own", "CASTELLAR VIDRIO", "glass"),
}

# own generation: group -> (consumer units, OMIE sell units). Same legal owner in OMIE's listings, and the ESIOS
# physical unit or the name ties the plant to the consumer's site. Repsol Química's cogenerations stay apart from
# Repsol Petróleo (different legal entity). Matched but with no OMIE volume, so left out: GUISGN (Guissona, an
# ESIOS-only programming unit), SNICRE1, REPRE01, EYPPV6 (Mafriges), EMBUPAL (Palacios, another legal entity).
OWN_GEN = {
    "ENCE": (["ENERC03", "EENRC02", "PONXC01"],
             ["ENEVD02", "ENEVD04", "ENEVD07", "ENRVD02", "ENRVD04", "ENRVD07"]),  # Navia biomass + cogen, Pontevedra
    "REPSOL PETROLEO": (["REPEC01", "REPRC01"],
                        ["CILCOR", "RPTRTAR", "REPPLL", "REPVD01", "REPVD02", "REPVD03", "REPVD04"]),
    "REPSOL QUIMICA": (["REPQC01"], ["COG75RQ", "EMORELL", "EMORPER"]),
    "SNIACE": (["SNIAC01"], ["SNICOG"]),
    "GUISSONA": (["GUISC02", "GUISR01", "COGRC01"], ["GUIRE01"]),
    "TRADEBE": (["TRARC01"], ["TRARE01"]),
    "RIVAS": (["RIVAC01"], ["RIVRE01"]),
    "SLY MURCIA": (["SLYRC01"], ["SLYRE01"]),
}


def firm_of(owner: str | None, groups: pd.DataFrame) -> str | None:
    """Evidence-based group (ESIOS, stem, manual) when there is one, else the legal entity itself: the 'self' groups in
    owner_groups take a name from the first word and merge unrelated owners (five COMPANIA..., every AYUNTAMIENTO)."""
    if not isinstance(owner, str):
        return None
    r = groups.get(owner)
    if r is not None and not str(r[1]).startswith("self"):
        return r[0]
    return _norm(owner)


def listings() -> pd.DataFrame:
    l = pd.read_parquet(ROOT / "data/omie/registry/omie_unit_lists.parquet")
    cd = l[l.unit_type == "CONSUMIDOR DIRECTO"].sort_values("snapshot")
    last = cd.groupby("unit").tail(1).set_index("unit")
    out = last[["descr", "agent_owner", "technology", "snapshot", "zone"]].rename(
        columns={"technology": "omie_kind", "snapshot": "listed_last"})
    out["listed_first"] = cd.groupby("unit").snapshot.min()
    out["n_owners"] = cd.groupby("unit").agent_owner.nunique()
    return out


def esios() -> pd.DataFrame:
    e = pd.read_parquet(ROOT / "data/esios/esios_programming_units.parquet")
    e = e[e.up_type == "Consum. directos a mercado"].set_index("unit")
    return e[["descr_long", "agent"]].rename(columns={"descr_long": "esios_descr", "agent": "esios_agent"})


def activity(units: set) -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(str(ROOT / "data/omie/cab/parquet/cab_*.parquet"))):
        c = pd.read_parquet(f, columns=["date", "unit", "descr"])
        c = c[c.unit.isin(units)]
        if len(c):
            rows.append(c)
    c = pd.concat(rows)
    c["date"] = pd.to_datetime(c.date)
    g = c.groupby("unit")
    return pd.DataFrame({"first_seen": g.date.min(), "last_seen": g.date.max(), "days_cab": g.date.nunique(),
                         "cab_descr": g.descr.last()})


def volume(units: set) -> pd.DataFrame:
    parts = []
    for f in sorted(glob.glob(str(ROOT / "data/omie/pdbf/parquet/pdbf_*.parquet"))):
        p = pd.read_parquet(f, columns=["date", "unit", "schedule_mw", "resolution_min"])
        p = p[p.unit.isin(units)]
        if not len(p):
            continue
        p["year"] = pd.to_datetime(p.date).dt.year
        p["mwh"] = p.schedule_mw.abs() * p.resolution_min / 60
        parts.append(p.groupby(["unit", "year"]).mwh.sum())
    v = pd.concat(parts).groupby(level=[0, 1]).sum().unstack(fill_value=0.0)
    v.columns = [f"mwh_{y}" for y in v.columns]
    return v


def generating_groups(groups: dict) -> set:
    """Firms owning at least 50 MW of supply units (so a council's rooftop panels do not count)."""
    ua = pd.read_parquet(ROOT / "data/omie/registry/unit_agents.parquet", columns=["role", "agent_owner", "max_power_mw"])
    ua = ua[ua.role.isin(SUPPLY_ROLES) & ua.agent_owner.notna()]
    mw = ua.groupby(ua.agent_owner.map(lambda o: firm_of(o, groups))).max_power_mw.sum()
    return set(mw[mw >= 50].index)


def classify(r: pd.Series, owner_counts: pd.Series) -> str:
    d, o = _norm(str(r.descr or r.esios_descr or "")), _norm(str(r.agent_owner or ""))
    k = r.omie_kind if isinstance(r.omie_kind, str) else ""
    if k in AUX_KINDS or AUX_WORDS.search(d) or (r.name.endswith(("X", "XR", "XR1")) and "C0" not in r.name):
        return "auxiliary"
    if k == "Compras Cons. Directo Balance" or BALANCE_WORDS.search(d):
        return "balance"
    energy_owner = bool(ENERGY_OWNER.search(o))
    many = owner_counts.get(r.agent_owner, 0) >= 3
    if not energy_owner and d and (d.split()[0] in o.split() or o[:6] in d):
        return "own"  # the description names the owner itself
    if CODE_DESCR.search(d) or d == _norm(r.name):
        return "portfolio" if (energy_owner or many or not o) else "own"
    if energy_owner or many:
        # a representative: one named consumer if the description is a name not shared with the owner
        return "represented" if (d and d[:8] not in o) else "portfolio"
    return "own"


def sector(name: str) -> str:
    n = _norm(name or "")
    for s, pat in SECTORS:
        if re.search(pat, n):
            return s
    return ""


PROCESS = {"steel", "aluminium_metals", "chemicals", "cement_minerals", "glass", "paper_wood", "plastics_rubber",
           "textiles", "food_agri", "automotive_machinery", "waste"}
WEATHER = {"retail_services", "public_transport", "water_irrigation"}


def sample_of(kind: str, sector: str) -> str:
    """The design's samples (notes/rq-direct-consumers.md, step 0): process industry is the main sample; loads that
    move with the weather (shops, councils, hospitals, irrigation, transport) are the comparison group."""
    if kind not in ("own", "represented"):
        return "out"
    if sector == "refining_petrochem":
        return "refinery"
    if sector in PROCESS:
        return "process"
    if sector in WEATHER:
        return "weather_exposed"
    return "unclassified"


def main() -> int:
    L, E = listings(), esios()
    reg = L.join(E, how="outer")
    reg["descr"] = reg.descr.fillna(reg.esios_descr)
    units = set(reg.index)
    A, V = activity(units), volume(units)
    reg = reg.join(A).join(V)
    reg["descr"] = reg.descr.fillna(reg.cab_descr)
    oc = reg.agent_owner.value_counts()
    reg["kind"] = [classify(r, oc) for _, r in reg.iterrows()]
    reg["consumer"] = ""
    reg.loc[reg.kind == "own", "consumer"] = reg.agent_owner.fillna(reg.descr)
    reg.loc[reg.kind == "represented", "consumer"] = reg.descr
    og = pd.read_parquet(ROOT / "data/omie/registry/owner_groups.parquet")
    groups = {o: (g, src) for o, g, src in zip(og.agent_owner, og.group, og.source)}
    reg["group"] = reg.agent_owner.map(lambda o: firm_of(o, groups))
    for u, (k, c, sec) in HAND.items():
        if u in reg.index:
            reg.loc[u, ["kind", "consumer"]] = [k, c]
            if sec:
                reg.loc[u, "hand_sector"] = sec
    gen = generating_groups(groups)
    reg["consumer_generates"] = reg.kind.isin(["own", "balance"]) & reg.group.isin(gen)
    reg["own_gen_group"] = None
    for g, (cons, _) in OWN_GEN.items():
        reg.loc[reg.index.intersection(cons), "own_gen_group"] = g
    reg["sector"] = [sector(f"{c} {d}") if k in ("own", "represented", "balance") else ""
                     for c, d, k in zip(reg.consumer, reg.descr, reg.kind)]
    if "hand_sector" in reg:
        reg["sector"] = reg.hand_sector.fillna(reg.sector)
        reg = reg.drop(columns="hand_sector")
    reg["sample"] = [sample_of(k, sec) for k, sec in zip(reg.kind, reg.sector)]
    mcols = [c for c in reg.columns if c.startswith("mwh_")]
    reg[mcols] = reg[mcols].fillna(0.0)
    reg["mwh_total"] = reg[mcols].sum(axis=1)
    reg.index.name = "unit"
    reg = reg.reset_index().sort_values("mwh_total", ascending=False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    reg.to_parquet(OUT, index=False)

    act = reg[reg.days_cab.fillna(0) > 0]
    print(f"{len(reg)} units in the universe, {len(act)} with an offer header in cab -> {OUT.relative_to(ROOT)}")
    t = act.groupby("kind").agg(units=("unit", "size"), twh=("mwh_total", lambda x: x.sum() / 1e6))
    print(t.round(2).to_string())
    own = act[act.kind.isin(["own", "represented"])]
    print("\nown + represented by sector (units, TWh 2018-2026):")
    s = own.assign(sector=own.sector.replace("", "(none)")).groupby("sector").agg(
        units=("unit", "size"), twh=("mwh_total", lambda x: x.sum() / 1e6))
    print(s.sort_values("twh", ascending=False).round(2).to_string())
    print(f"\nconsumers whose group also generates: {own.consumer_generates.sum()} units, "
          f"groups {sorted(own.loc[own.consumer_generates, 'group'].dropna().unique())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
