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
}
# Deliberately NOT mapped despite carrying volume, because the data does not
# establish the owner and the mnemonic alone is ambiguous. Listed so the gap is
# explicit rather than silent: GED, GGN, GGA, CEV, NXV, IGV, IGN, IBE, EDP,
# ADO, DOU, NEX, GAS, GSH, HCG, DET. Several are guessable by a domain expert
# (IBE almost certainly Iberdrola, EDP almost certainly EDP) -- confirm against
# an external source before encoding them.


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
    df["agent_name"] = df.descr.map(from_name)
    df["agent_prefix"] = df.prefix.map(lambda p: PREFIX_AGENTS.get(p, (None, None))[0])

    df["agent"] = df.agent_esios.fillna(df.agent_name).fillna(df.agent_prefix)
    df["source"] = (
        df.agent_esios.notna().map({True: "esios", False: None})
        .fillna(df.agent_name.notna().map({True: "name", False: None}))
        .fillna(df.agent_prefix.notna().map({True: "prefix", False: None})))
    df["tech_esios"] = df.unit.map(tech_by_code)
    return df.drop(columns=["agent_esios", "agent_name", "agent_prefix"])


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
