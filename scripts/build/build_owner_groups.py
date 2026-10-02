#!/usr/bin/env python3
"""Roll OMIE's published `agent_owner` up to corporate groups.

    .venv/bin/python scripts/build/build_owner_groups.py
    .venv/bin/python scripts/build/build_owner_groups.py --save
    .venv/bin/python scripts/build/build_owner_groups.py --show-unmapped

Writes data/omie/registry/owner_groups.parquet -- one row per distinct
`agent_owner` string, with the group it belongs to and the evidence for it.

WHY THIS EXISTS

`agent_owner` (from OMIE's *Listado de Unidades*) covers far more units than the
inference chain in `build_unit_agents.py` -- 100% of contracted sell MW against
74-94% -- but it names **legal entities and does no roll-up**. Without a group
mapping, one firm appears as several competitors: "REPSOL SERVICIOS RENOVABLES,
S.A.", "REPSOL GENERACION ELECTRICA, S.L.U." and "REPSOL PETROLEO" are three
rows, and `SU ELETRICIDADE, S.A.` -- 7.3% of supply volume -- reads as a firm in
its own right rather than as EDP's Portuguese regulated supplier.

That is the one thing blocking a published cross-firm share table off the owner
tier. This file supplies it. It replaces the first-token heuristic in
`lib/omie_owner.py`, which was explicitly diagnostic-only.

THREE LAYERS, IN DESCENDING ORDER OF EVIDENCE, AND NOTHING IS GUESSED

1. `esios`  -- the modal firm the INDEPENDENT ESIOS-based chain assigns to this
   entity's own units. Accepted only on real support: at least MIN_SUPPORT units
   carrying a firm and at least AGREE_FRAC of them agreeing. This is the
   strongest evidence available, because ESIOS and the OMIE listing share no
   field: agreement between them is corroboration, not circularity.
2. `stem`   -- the entity's distinctive leading token matches a group already
   established by layer 1 ("REPSOL PETROLEO" against a REPSOL established from
   "REPSOL SERVICIOS RENOVABLES"). Never invents a group on its own.
3. `manual` -- hand-verified cases neither rule reaches, each carrying its
   reason in the table below and each checked against unit codes.

Everything else is left **unmapped on purpose** and grouped as itself. A wrong
grouping silently merges two competitors and corrupts every share, Herfindahl
and residual-demand figure downstream; an unmapped entity only understates a
group, visibly. `--show-unmapped` lists what is left, largest first.

WHY THE SUPPORT THRESHOLDS ARE NOT OPTIONAL

Taking the modal ESIOS firm without a support test looks fine and is wrong:
"GALP ENERGIA ESPANA, S.A.U." has 41 units of which exactly **one** carries an
ESIOS firm, and that one says IGNIS. Accepting it would fold Galp into Ignis.
"REPSOL COMERCIALIZADORA" has 51 units, 4 with a firm, reading WIND_TO_MARKET.
Both are rejected by MIN_SUPPORT/AGREE_FRAC and fall through to layer 2 or 3.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
UNIT_LISTS = DATA / "omie" / "registry" / "omie_unit_lists.parquet"
AGENTS = DATA / "omie" / "registry" / "unit_agents.parquet"
OUT = DATA / "omie" / "registry" / "owner_groups.parquet"

# Layer 1 acceptance. Both must hold -- see the docstring on Galp.
MIN_SUPPORT = 3       # units of this entity that carry an ESIOS firm
AGREE_FRAC = 0.60     # share of THOSE agreeing on the modal firm
MIN_UNIT_FRAC = 0.10  # supporting units as a share of the entity's OWN units

# Layer 2 propagates a layer-1 answer across every entity sharing a stem, so it
# AMPLIFIES whatever evidence layer 1 accepted. Establishing a stem therefore
# needs more than clearing layer 1. "ENERGYA VM GESTION DE ENERGIA" reads CENTE
# on 3 of its 25 units, which passes layer 1; propagating that relabels
# "ENERGYA VM GENERACION (ACT. COMER. RE)" and its 392 units -- 2.3% of supply
# volume -- on the strength of three observations about a different entity.
STEM_MIN_SUPPORT = 5
STEM_AGREE_FRAC = 0.75

# MIN_UNIT_FRAC is the one that stops thin evidence about a large entity.
# AGREE_FRAC is computed only over units that carry a firm, so an entity with
# 245 units of which 4 are labelled scores 1.00 on it. "ENERGYA VM GENERACION"
# is exactly that -- 4/245 reading PRADO -- and without this gate it folds a
# 2.3%-of-supply firm into an unrelated one.

# Legal form, activity qualifiers and parentheticals. Stripped before the stem
# is taken, so "ENDESA GENERACION, S.A." and "ENDESA ENERGIA" share a stem.
NOISE = re.compile(
    r"\b(SAU|SLU|SA|SL|SAS|SCA|SGPS|LIMITED|LTD|GMBH|BV|PLC|INC|"
    r"ESPANA|IBERIA|PORTUGAL|ESPANOLA|"
    r"GENERACION|COMERCIALIZADORA|COMERCIALIZADOR|COMERCIALIZACION|"
    r"RENOVABLES|RENOVABLE|SERVICIOS|ELECTRICA|ELECTRICIDAD|ELETRICIDADE|"
    r"ENERGIA|ENERGIAS|ENERGY|ENERGIE|POWER|GROUP|GRUPO|TRADING|MARKETS|"
    r"PRODUCCION|GESTION|DESARROLLO|DESARROLLOS|IBERICA|GLOBAL|"
    r"ULTIMO|RECURSO|REFERENCIA|CLIENTES|SUMINISTRO)\b", re.I)

# Connectives, stripped after NOISE so a stem is never "DE" or "Y". Without
# this "GESTION DE ENERGIA Y MERCADOS" loses its content words to NOISE and
# stems as "DE Y".
CONNECTIVES = re.compile(r"\b(DE|DEL|DA|DO|DOS|DAS|LA|EL|LOS|LAS|Y|E|AND)\b", re.I)

# Layer 3. Each is an entity whose group cannot be read off its own name and
# which layer 1 could not carry. Reason recorded; all checked against the unit
# codes the entity actually holds, not against outside knowledge.
MANUAL_GROUPS: dict[str, tuple[str, str]] = {
    "SU ELETRICIDADE": ("EDP",
        "EDP's Portuguese last-resort supplier; its units are coded EDPSVD1-3 "
        "and the ESIOS chain assigns all three to EDP"),
    "CURENERGIA": ("IBERDROLA",
        "Iberdrola's last-resort supplier; units coded IBCUC01/ICUVD*, ESIOS "
        "assigns 11/11 to IBERDROLA"),
    "ENERGIA XXI": ("ENDESA",
        "Endesa's last-resort supplier; units coded E21VD*, ESIOS names "
        "ENDESA/EEXXI on the units that carry a firm"),
    "GAS NATURAL": ("NATURGY",
        "Gas Natural Fenosa renamed Naturgy in 2018; ESIOS assigns 44/44 of "
        "its units to NATURGY, which is layer-1 evidence in its own right"),
    "PETROGAL": ("GALP",
        "ESIOS names GALP on its units; shares the Galp group with "
        "GALP ENERGIA ESPANA, which layer 1 cannot reach (1 unit of 41)"),
    "ABONO GENERACIONES ELECTRICAS": ("EDP",
        "the Abono coal plant, ESIOS assigns 2/2 to EDP"),
    "MAGNON GREEN": ("ENCE",
        "ENCE's biomass arm; ESIOS assigns 12/12 to ENCE"),
}

# Group-level merges: two group LABELS that are one corporate group. Needed when
# layer 1 established a group from a legal NAME rather than from ownership --
# the manual layer above only fills entities layer 1 left open, so it cannot
# correct a layer-1 label. Applied after all three layers; each carries both
# in-data evidence and the ownership fact.
GROUP_MERGES: dict[str, tuple[str, str]] = {
    "ENEL": ("ENDESA",
        "Enel Green Power Espana is 100% owned by Endesa Generacion, which bought "
        "the remaining 60% from Enel Green Power International in 2016 (Enel and "
        "Endesa filings, July 2016) -- the whole window. In the data, two of the "
        "entity's own units (ECY*) carry the ESIOS agent ENDESA COGENER Y "
        "RENOVABLES, which the ESIOS chain assigns to ENDESA; ESIOS labels the "
        "rest ENEL after the legal name. Standing apart, it made Endesa's "
        "residual-demand slope count Endesa's own renewables as a rival's "
        "(merged 2026-09-29)"),
    "EDP COMERCIAL": ("EDP",
        "EDP Comercial - Comercializacao de Energia, S.A. is EDP's Portuguese "
        "liberalised retailer, a full subsidiary of EDP - Energias de Portugal "
        "(EDP Integrated Annual Report 2024, Part IV, Annex I: 100% of capital and "
        "voting rights; a direct equity investment of EDP S.A., note on "
        "investments in subsidiaries). It stood alone for want of merge evidence "
        "in the ESIOS chain. The midday-hydro panels already counted it in EDP's "
        "net position; the firm panel did not, so EDP's retail load was missing "
        "from the chapter's net-buyer shares (merged 2026-09-30)"),
    # Renamings the layers left apart, found by notes/report-ownership-mapping.md
    # (merged 2026-10-02). Each pair is one legal entity under an old and a new name,
    # or two entities of one company; the ESIOS chain agrees in every case.
    "TOTAL": ("TOTALENERGIES",
        "TOTAL GAS & POWER LIMITED is TOTALENERGIES GAS & POWER LIMITED before Total "
        "renamed itself TotalEnergies (May 2021); ESIOS gives its units TOTALENERGIES"),
    "CLIDOM": ("HOLALUZ",
        "CLIDOM ENERGY SL is Holaluz's earlier entity; Holaluz's legal name is "
        "HOLALUZ-CLIDOM SA, and ESIOS gives both the agent CLIDM"),
    "GAS": ("BP",
        "BP GAS AND POWER IBERIA, S.A.U.: the stem took the word GAS; ESIOS gives BP"),
    "GAS EUROPE": ("BP",
        "BP GAS EUROPE, S.A.U.: the stem took GAS EUROPE; ESIOS gives BP"),
    "LDA": ("PH ENERGIA",
        "PH ENERGIA, LDA: the stem took the Portuguese legal form LDA"),
    "UNIPESSOAL": ("PH ENERGIA",
        "PH ENERGIA UNIPESSOAL LDA: the stem took the legal form UNIPESSOAL; the same "
        "company as PH ENERGIA, LDA"),
    "ALDRO": ("ENI PLENITUDE",
        "Aldro Energia y Soluciones became ENI PLENITUDE IBERIA after Eni Plenitude "
        "bought it (2022); ESIOS gives both the agent ALDRO. One continuing retailer: "
        "the change of parent outside the five firms is not dated here"),
    "IBERENERGIA": ("EDP",
        "IBERENERGIA,S.A. holds Trillo's 15.5%: a 100% subsidiary of Hidroelectrica del "
        "Cantabrico (EDP Espana), to which HC transferred the stake (El Periodico de la "
        "Energia, 'EDP Espana pide a Industria traspasar la titularidad de su "
        "participacion en Trillo a su filial Iberenergia'; CNMC INF/DE/0178/14). ESIOS "
        "links it to Iberdrola only through Trillo's operator (merged 2026-10-02)"),
}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def normalise(name: str) -> str:
    s = strip_accents(str(name)).upper()
    s = re.sub(r"\(.*?\)", " ", s)          # activity qualifiers
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = NOISE.sub(" ", s)
    s = CONNECTIVES.sub(" ", s)
    return " ".join(s.split())


def stem(name: str) -> str | None:
    """Leading distinctive token, or the first two where the first is short."""
    n = normalise(name)
    if not n:
        return None
    parts = [p for p in n.split(" ") if len(p) >= 3 and not p.isdigit()]
    if not parts:
        return None
    if len(parts[0]) <= 4 and len(parts) > 1:
        return f"{parts[0]} {parts[1]}"
    return parts[0]


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    ul = pq.read_table(UNIT_LISTS, columns=["unit", "agent_owner"]).to_pandas()
    ul = ul[ul.agent_owner.notna()].drop_duplicates(["unit", "agent_owner"])
    ua = pq.read_table(AGENTS, columns=["unit", "firm", "role",
                                        "net_cleared_mwh"]).to_pandas()
    return ul, ua


def build(verbose: bool = True) -> pd.DataFrame:
    ul, ua = load()
    d = ul.merge(ua[["unit", "firm"]], on="unit", how="left")

    # Layer 1: modal ESIOS firm per entity, on real support.
    def modal(s: pd.Series) -> tuple[str | None, int, float]:
        v = s.dropna()
        if v.empty:
            return None, 0, 0.0
        top = v.value_counts()
        return top.index[0], int(top.iloc[0]), float(top.iloc[0] / len(v))

    rows = []
    for owner, g in d.groupby("agent_owner"):
        firm, n, frac = modal(g.firm)
        rows.append({"agent_owner": owner, "n_units": g.unit.nunique(),
                     "esios_firm": firm, "esios_n": n, "esios_frac": frac})
    e = pd.DataFrame(rows)
    ok = ((e.esios_n >= MIN_SUPPORT) & (e.esios_frac >= AGREE_FRAC)
          & (e.esios_n / e.n_units >= MIN_UNIT_FRAC))
    e["group"] = e.esios_firm.where(ok)
    e["source"] = pd.Series(["esios"] * len(e)).where(ok)
    e["stem"] = e.agent_owner.map(stem)

    # Layer 3 first, so a hand-verified case is never overridden by a stem.
    for key, (grp, why) in MANUAL_GROUPS.items():
        hit = e.agent_owner.map(lambda x: normalise(x).startswith(key))
        e.loc[hit & e.group.isna(), ["group", "source"]] = [grp, "manual"]

    # Layer 2: a stem already established by layer 1 carries its siblings.
    strong = e[(e.source == "esios") & (e.esios_n >= STEM_MIN_SUPPORT)
               & (e.esios_frac >= STEM_AGREE_FRAC)]
    established = (strong.groupby("stem").group
                    .agg(lambda s: s.mode().iloc[0] if len(s.mode()) == 1 else None)
                    .dropna().to_dict())
    take = e.group.isna() & e.stem.map(lambda s: s in established)
    e.loc[take, "group"] = e.loc[take, "stem"].map(established)
    e.loc[take, "source"] = "stem"

    # Everything else groups as itself, visibly.
    e["group"] = e.group.fillna(e.stem).fillna(e.agent_owner)
    # "self" is a decision, not a gap: the entity stands as its own group
    # because no rule found evidence to merge it into another. For a genuinely
    # standalone firm -- Shell, Statkraft, Movhera -- that is the right answer.
    e["source"] = e.source.fillna("self")

    # Group-level merges, last, so they can join a label layer 1 established.
    for src, (dst, _why) in GROUP_MERGES.items():
        hit = e.group == src
        e.loc[hit, "group"] = dst
        e.loc[hit, "source"] = e.loc[hit, "source"] + "+merge"
        if verbose:
            print(f"  group merge {src} -> {dst}: {int(hit.sum())} entities, "
                  f"{int(e.loc[hit, 'n_units'].sum())} units")

    if verbose:
        print(f"{len(e):,} distinct agent_owner strings -> "
              f"{e.group.nunique():,} groups")
        print("  by source: " + ", ".join(
            f"{k}:{v}" for k, v in e.source.value_counts().items()))
        rej = e[(e.esios_firm.notna()) & (e.source != "esios")]
        print(f"\n  {len(rej)} entities had an ESIOS firm REFUSED for weak support "
              f"(< {MIN_SUPPORT} units, < {AGREE_FRAC:.0%} agreement, "
              f"or < {MIN_UNIT_FRAC:.0%} of the entity's own units):")
        for r in rej.nlargest(6, "n_units").itertuples():
            print(f"    {r.agent_owner[:44]:46s} {r.esios_firm} on "
                  f"{r.esios_n}/{r.n_units} -> grouped as {r.group}")
    return e


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--show-unmapped", action="store_true")
    args = ap.parse_args()

    e = build()
    _, ua = load()
    SUP = {"generation", "generation_large", "storage_mixed", "pumping"}
    g = ua[ua.role.isin(SUP)].copy()
    g["v"] = g.net_cleared_mwh.abs().fillna(0)
    own = pq.read_table(AGENTS, columns=["unit", "agent_owner"]).to_pandas()
    g = g.merge(own, on="unit", how="left").merge(
        e[["agent_owner", "group", "source"]], on="agent_owner", how="left")
    tot = g.v.sum()
    print(f"\n  supply volume by mapping source: " + ", ".join(
        f"{k}:{v/tot:.1%}" for k, v in g.groupby('source').v.sum().items()))
    print("\n  top groups by supply volume:")
    for grp, v in g.groupby("group").v.sum().nlargest(12).items():
        n = e.loc[e.group == grp, "agent_owner"].nunique()
        print(f"    {str(grp)[:26]:28s}{v/tot:7.2%}   ({n} entities)")

    if args.show_unmapped:
        u = g[g.source == "self"].groupby("group").v.sum().nlargest(15)
        print("\n  largest SELF groups (stand alone; no merge evidence found):")
        for grp, v in u.items():
            print(f"    {str(grp)[:34]:36s}{v/tot:7.3%}")

    if args.save:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        e.to_parquet(OUT, index=False)
        print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(e):,} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
