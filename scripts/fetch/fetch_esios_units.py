#!/usr/bin/env python3
"""Fetch the ESIOS registry of programming units (unidades de programación).

    .venv/bin/python scripts/fetch/fetch_esios_units.py

Writes data/esios/esios_programming_units.parquet (~3,900 rows).

**No token.** Unlike the ESIOS indicator API, archive 82 is public. The web
page at https://www.esios.ree.es/es/unidades-de-programacion is JS-rendered
and has no export button; the JSON behind it is:

    https://api.esios.ree.es/archives/82/download_json?locale=es

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

URL = "https://api.esios.ree.es/archives/82/download_json?locale=es"
OUT = DATA / "esios" / "esios_programming_units.parquet"

COLUMNS = {
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


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sess = session()
    r = sess.get(URL, timeout=180, headers={"Accept": "application/json"})
    r.raise_for_status()
    payload = json.loads(r.content.decode("utf-8-sig"))
    records = payload.get("UnidadesProgramacion")
    if not records:
        print(f"unexpected payload keys: {list(payload)[:6]}", file=sys.stderr)
        return 1

    df = pd.DataFrame(records)
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        print(f"schema drift -- missing columns: {sorted(missing)}", file=sys.stderr)
        return 1
    df = df[list(COLUMNS)].rename(columns=COLUMNS)
    df["max_power_mw"] = parse_mw(df.max_power_mw)
    for c in ("unit", "agent", "tech", "eic", "up_type", "business"):
        df[c] = df[c].astype(str).str.strip()
    df["fetched"] = date.today()

    df.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(DATA.parent)}  {len(df):,} units")
    print(f"  agents      : {df.agent.nunique()}")
    print(f"  technologies: {df.tech.nunique()}")
    print(f"  EIC present : {(df.eic.str.len() > 0).mean():.0%}")
    print(f"  up_type     : {df.up_type.value_counts().head(5).to_dict()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
