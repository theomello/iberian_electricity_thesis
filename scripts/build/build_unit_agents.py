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
BAND = 5.0

# Layer 3. Each entry records the evidence that justifies it; anything that
# would have been a guess is absent by design and shows up as unmapped.
PREFIX_AGENTS: dict[str, tuple[str, str]] = {
    "EGV": ("AXPO", 'cab name "AXPO VENTA R. ESPECIAL nnn"'),
    "EGE": ("ACCIONA", 'cab name "AC. GREEN EN. DEV. VENTA RE n"'),
    "WMV": ("WMARK", 'cab name "VENTA EXCED AUTOPROD WMARK nnn"'),
    "EGP": ("ENEL_GREEN_POWER", 'cab name "EOLICA EEGPEM"; EGP mnemonic'),
    "HIS": ("RWE", 'cab name "PE RWE"'),
    "GNV": ("GNERA", 'cab name "UOF GNERA MAYOR DE 1MW"'),
    "GAL": ("GALP", 'cab name "UNIDADE DE VENDA"; GALPWV2 code, PT'),
    "ECY": ("ECYR", 'cab name "ECYR VENTA REG. ESP. 1"'),
    "GRE": ("REPSB", 'cab name "REPSB GENERICA VENTA" -- REPSB is an ESIOS agent'),
    "EBL": ("EBLCO", 'cab name "GENÉRICA VENTA EBLCO" on sibling unit GEBLCC1'),
    "EDR": ("ACCIONA", 'cab name "ACCIONA VENTA nnn"'),
    "ACC": ("ACCIONA", 'cab name "AC.GREEN EN. DEV. VENTA RO n"'),
    "ENR": ("ENCE", 'cab name "ENCE ENERGIA HUELVA"'),
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
    (r"UOF HIDRO|\bC\.?H\.?\b|HIDRO|HIDR[AÁ]ULIC", "hydro"),
    (r"\bP\.?S\.?\b|\bFV\b|FOTOVOLT|SOLAR", "solar"),
    (r"\bP\.?E\.?\b|E[OÓ]LIC", "wind"),
    (r"BIOMASA|BIOG[AÁ]S", "biomass"),
    (r"COGENERA", "cogeneration"),
    (r"BATER[IÍ]A|ALMACENAM", "storage"),
]


def tech_from_name(descr: str) -> str | None:
    if not isinstance(descr, str) or not descr.strip():
        return None
    u = descr.upper()
    for pat, tech in TECH_PATTERNS:
        if re.search(pat, u):
            return tech
    return None


def alpha_prefix(unit: str, n: int = 3) -> str:
    return re.sub(r"[0-9]", "", str(unit))[:n]


def build(month: str) -> pd.DataFrame:
    esios = pq.read_table(DATA / "esios" / "esios_programming_units.parquet").to_pandas()
    agents = {a.upper() for a in esios.agent.dropna().unique() if len(a.strip()) >= 3}
    by_code = dict(zip(esios.unit, esios.agent))
    tech_by_code = dict(zip(esios.unit, esios.tech))

    cab = pq.read_table(DATA / "omie" / "cab" / "parquet" / f"cab_{month}.parquet",
                        columns=["unit", "descr", "max_power_mw"]).to_pandas()
    cab = cab.groupby("unit").last()

    reg = pq.read_table(DATA / "omie" / "registry" / "unit_registry.parquet").to_pandas()
    df = reg[["unit", "country", "role", "net_cleared_mwh"]].copy()
    df["descr"] = df.unit.map(cab.descr).fillna("")
    df["max_power_mw"] = df.unit.map(cab.max_power_mw)
    df["prefix"] = df.unit.map(alpha_prefix)

    def from_name(d: str) -> str | None:
        for tok in re.findall(r"[A-Z0-9]{3,}", d.upper()):
            if tok in agents:
                return tok
        return None

    df["agent_esios"] = df.unit.map(by_code)
    df["_agent_name_src"] = df.descr.map(from_name)
    df["agent_prefix"] = df.prefix.map(lambda p: PREFIX_AGENTS.get(p, (None, None))[0])

    df["agent"] = df.agent_esios.fillna(df._agent_name_src).fillna(df.agent_prefix)
    df["source"] = (
        df.agent_esios.notna().map({True: "esios", False: None})
        .fillna(df._agent_name_src.notna().map({True: "name", False: None}))
        .fillna(df.agent_prefix.notna().map({True: "prefix", False: None})))
    df["tech_esios"] = df.unit.map(tech_by_code)
    df["tech_cab"] = df.descr.map(tech_from_name)

    # Roll agents up to the firm, using archive 83's legal names as evidence.
    sm_path = DATA / "esios" / "esios_market_subjects.parquet"
    if sm_path.exists():
        sm = pq.read_table(sm_path).to_pandas()
        name_by_agent = dict(zip(sm.agent, sm.name))
        type_by_agent = dict(zip(sm.agent, sm.type))
        df["agent_name"] = df.agent.map(name_by_agent)
        df["agent_type"] = df.agent.map(type_by_agent)
        # Layer-3 labels are already firm names, so fall back to the label.
        df["firm"] = df.agent_name.map(firm_of).fillna(df.agent.map(firm_of))
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
    args = ap.parse_args()

    df = build(args.month)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)

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
