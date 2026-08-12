#!/usr/bin/env python3
"""Fetch REE's three market-registry archives from ESIOS.

    .venv/bin/python scripts/fetch/fetch_esios_units.py

Writes to data/esios/:
    esios_programming_units.parquet   archive 82, ~3,900 bidding units
    esios_physical_units.parquet      archive 81, ~6,600 physical units
    esios_market_subjects.parquet     archive 83, ~740 agents with legal names

**No token.** Unlike the ESIOS indicator API these archives are public:

    https://api.esios.ree.es/archives/{82,81,83}/download_json?locale=es

Only 82 is reachable from the website. 81 and 83 were found by probing archive
ids -- `https://api.esios.ree.es/archives` itself returns 403, so there is no
index to read. Archive 81 links each physical unit to both its agent
(`Vinculación con SM`) and its bidding unit (`Vinculación con UP`); every UP's
physical units agree on the agent, which is a useful internal check. Archive 83
gives the agent's legal name and, importantly, its **type** -- `Productor`,
`Comercializador`, or `Representante`. The last of those is how you tell a
firm bidding its own plant from a trader bidding somebody else's.

Note archive 81 adds **no** unit coverage beyond 82: it links to the same UP
namespace. It is worth fetching for the physical-level technology and capacity,
and for the agent consistency check, not for reach.

This is REE's **system-operator** registry, and that scope is the whole point
of reading it carefully:

* `agent` (Sujeto del Mercado) is the registered market participant that
  submits offers for the unit -- the entity that *decides the bid*. That is
  the object market power is about, and nothing in the OMIE files publishes
  it. 738 distinct agents.
* `tech` (Tipo de producción) is an authoritative 41-level technology
  taxonomy, better than parsing `cab` plant names.
* `eic` is populated for 100% of rows, which is the bridge to ENTSO-E.

WHAT IT DOES NOT COVER, and why

REE registers what it *dispatches*. OMIE's bid files additionally contain
**commercial aggregation vehicles** -- `EDPSVD1` ("VENTA RE", 6,500 MW),
`IBEVD11` ("EÓLICA HABILITADA"), `EGVD076` ("AXPO VENTA R. ESPECIAL 076") --
which exist only to bid, because REE dispatches the underlying assets instead.
Measured on 2026-08-11: 592 of our unit codes appear here, covering 63.3% of
positively-priced offered volume but only **34.6% of near-marginal volume**
and 12.2% of price-taker (<=0 EUR) volume.

So this file is authoritative but partial, and the gap is not random -- it is
concentrated in exactly the renewable portfolio units. Do not treat an
unmatched unit as unimportant; treat it as unknown. See
scripts/build/build_unit_agents.py for how the remainder is handled.

The registry is a **snapshot**, not a time series: it reflects the fleet as of
the fetch date and carries no entry/exit dates. Re-fetching later will silently
change it, so record the fetch date with any result that depends on it.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, session  # noqa: E402

# Three public archives, none needing a token. 82 is the one the web page
# shows; 81 and 83 are not linked from it and were found by probing ids.
ARCHIVES = {
    82: ("UnidadesProgramacion", "esios_programming_units.parquet"),
    81: ("UnidadesFisicas", "esios_physical_units.parquet"),
    83: ("SujetosMercado", "esios_market_subjects.parquet"),
}
URL = "https://api.esios.ree.es/archives/{id}/download_json?locale=es"
OUT = DATA / "esios" / "esios_programming_units.parquet"

SPANISH = {
    "Código de UF": "uf",
    "Vinculación con SM": "agent",
    "Vinculación con UP": "up",
    "Código de sujeto": "agent",
    "Nombre": "name",
    "Tipo de SM": "type",

    "Código de UP": "unit",
    "Descripción corta": "descr_short",
    "Descripción larga": "descr_long",
    "Código EIC": "eic",
    "Tipo de producción": "tech",
    "Negocio": "business",
    "Ámbito de actuación": "scope",
    "Zona de Regulación": "regulation_zone",
    "Tipo de UP": "up_type",
    "Sujeto del Mercado": "agent",
    "Potencia máxima MW": "max_power_mw",
}


def parse_mw(s: pd.Series) -> pd.Series:
    """Spanish decimals: dot thousands, comma decimal -- as in curva_pbc_uof."""
    return pd.to_numeric(
        s.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
        errors="coerce")


def fetch_archive(sess, aid: int, key: str, fname: str) -> int:
    r = sess.get(URL.format(id=aid), timeout=180, headers={"Accept": "application/json"})
    r.raise_for_status()
    payload = json.loads(r.content.decode("utf-8-sig"))
    records = payload.get(key)
    if not records:
        print(f"  ! archive {aid}: expected key {key!r}, got {list(payload)[:4]}",
              file=sys.stderr)
        return 0
    df = pd.DataFrame(records)
    df.columns = [SPANISH.get(c, c) for c in df.columns]
    for c in df.columns:
        if c.endswith("_mw"):
            df[c] = parse_mw(df[c])
        elif df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()
    df["fetched"] = date.today()
    out = DATA / "esios" / fname
    df.to_parquet(out, index=False)
    print(f"  {out.name:36s} {len(df):>6,} rows  {list(df.columns)[:5]}")
    return len(df)


def main() -> int:
    (DATA / "esios").mkdir(parents=True, exist_ok=True)
    sess = session()
    for aid, (key, fname) in ARCHIVES.items():
        fetch_archive(sess, aid, key, fname)

    up = pd.read_parquet(DATA / "esios" / ARCHIVES[82][1])
    print(f"\n  programming units {len(up):,} | agents {up.agent.nunique()} "
          f"| technologies {up.tech.nunique()} | EIC {(up.eic.str.len()>0).mean():.0%}")
    sm = pd.read_parquet(DATA / "esios" / ARCHIVES[83][1])
    if "type" in sm.columns:
        print(f"  market subjects by type: {sm.type.value_counts().head(5).to_dict()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
