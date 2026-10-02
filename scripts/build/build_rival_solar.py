#!/usr/bin/env python3
"""Rivals' offered solar (or wind), per firm and period: the leg D instruments.

    .venv/bin/python scripts/build/build_rival_solar.py [--tech wind] [--months 202406 ...]

Writes outputs/tables/rival_solar.parquet (rival_wind.parquet with --tech wind), one
row per day-ahead period that has a price and a bid file. The columns keep the same
names for both technologies:

    z_all            MW of solar offered day-ahead by every solar-labelled supply unit
    own_<FIRM>       the part offered by units whose owner group is FIRM
    z_rival_<FIRM>   z_all - own_<FIRM>, the instrument for FIRM (framework spec §4, leg D)

Built exactly as `build_solar_instrument.py` builds `z_offered` (sell offers,
status O, solar-labelled units outside the purchase roles), once for each of the
five firms instead of for EDP alone. A firm's own solar is every unit whose
owner rolls up to it under `owner_group` -- pass-through entities included, so
no volume the firm's group bids enters its own instrument -- by date and by share
since 2026-10-02 (lib/unit_ownership.py): the owners in force that day, each times
its listed share. For EDP this
reproduces `z_offered`; `scripts/qa/check_rival_solar.py` checks it. Wind is built
the same way from wind-labelled units. Neither total holds EDPSVD1 ("VENTA RE"),
SU Eletricidade's sale of Portugal's feed-in renewables, which carries no technology
label and is pass-through, not EDP's own. Only days
the bid files cover are kept, so a partial frontier month cannot read as zero
solar; within a covered day a period with no solar row carries 0.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_owner import exposed_group  # noqa: E402
from unit_ownership import attach_owners, spells  # noqa: E402

DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
TABLES = ROOT / "outputs/tables"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")
KEY = ["date", "period"]
MATCH = DATA / "jrc_ppdb/jrc_cab_match.parquet"
# Ownership is by date and by share since 2026-10-02 (lib/unit_ownership.py). That
# retired OWNER_FIX: NATVD11-15, EDP's wind parks sold through EDP Comercializadora
# from 2018-01-01 to 2020-08-31, have one listing (2022-02-08) naming EDP
# Comercializadora, which the static owner rolled up to TotalEnergies for the whole
# window. The dated rule for that entity (EDP's until 2020-11-30) now gives EDP for
# their whole bidding life; scripts/qa/check_rival_solar.py pins it.
LISTS = DATA / "omie/registry/omie_unit_lists.parquet"


def thermal_groups() -> tuple[str, ...]:
    """The five firms, then every other group owning a JRC-matched thermal unit in any
    OMIE listing: leg C needs each such owner's rivals' renewables."""
    m = pd.read_parquet(MATCH, columns=["unit"])
    lst = pd.read_parquet(LISTS, columns=["unit", "agent_owner"])
    g = lst[lst.unit.isin(m.unit)].agent_owner.map(exposed_group).dropna()
    return FIRMS + tuple(sorted(set(g) - set(FIRMS)))


def tech_units(tech: str = "solar") -> pd.Index:
    """The supply units labelled `tech` (solar: those z_offered uses)."""
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                        columns=["unit", "role", "tech", "tech_omie", "tech_omie_early"])
    label = u.tech_omie.fillna(u.tech_omie_early).fillna(u.tech)
    return pd.Index(u.loc[(label == tech) & ~u.role.str.startswith("purchase"), "unit"].astype(str))


def month(f: Path, units: pd.Index, sp: pd.DataFrame, groups: tuple[str, ...] = FIRMS) -> pd.DataFrame:
    b = pq.read_table(f, columns=["date", "period", "unit", "side", "status", "power_mw"],
                      filters=[("unit", "in", list(units)), ("side", "==", "V"),
                               ("status", "==", "O")]).to_pandas()
    b["unit"] = b.unit.astype(str)
    parts = [b.power_mw.groupby([b.date, b.period]).sum().rename("z_all")]
    # One row per owner in force that day, power x share: a co-owned park counts
    # for each owner pro rata, a sold one for its owner at the time.
    o = attach_owners(b, sp)
    k = [o.date, o.period]
    for g in groups:
        parts.append(o.power_mw.where(o.group == g, 0.0).groupby(k).sum().rename(f"own_{g}"))
    return pd.concat(parts, axis=1).fillna(0.0).reset_index()


def align(d: pd.DataFrame, px: pd.DataFrame, groups: tuple[str, ...] = FIRMS) -> pd.DataFrame:
    """Solar sums onto the priced periods of the days the bid files cover.

    Only days with bid rows are kept: a frontier month's zip can be partial
    (CLAUDE.md), and a priced day with no bids must be missing, not zero solar.
    Within a covered day, a period with no solar row carries 0.
    """
    d = px[px.date.isin(set(d.date))].merge(d, on=KEY, how="left")
    num = [c for c in d.columns if c not in KEY]
    d[num] = d[num].fillna(0.0)
    for g in groups:
        d[f"z_rival_{g}"] = d.z_all - d[f"own_{g}"]
    return d


def build(months: list[str] | None, tech: str = "solar") -> pd.DataFrame:
    groups = thermal_groups()
    units = tech_units(tech)
    sp = spells()
    sp = sp[sp.unit.isin(set(units))]
    out = TABLES / f"rival_{tech}.parquet"
    print(f"{len(units)} {tech}-labelled supply units; the five firms own some at some date: "
          + ", ".join(f"{f} {sp.loc[sp.group == f, 'unit'].nunique()}" for f in FIRMS))
    files = sorted(BIDS.glob("bids_*.parquet"))
    if months:
        files = [f for f in files if f.stem.split("_")[1] in months]
    parts = []
    for f in files:
        parts.append(month(f, units, sp, groups))
        print(f"  {f.stem}", file=sys.stderr, flush=True)
    d = pd.concat(parts, ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet", columns=KEY)
    px["date"] = pd.to_datetime(px.date)
    d = align(d, px, groups)
    out.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(out, index=False)
    print(f"wrote {out.relative_to(ROOT)}  ({len(d):,} periods)")
    return d


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*", help="YYYYMM months only (for checks)")
    ap.add_argument("--tech", choices=("solar", "wind"), default="solar")
    a = ap.parse_args()
    build(a.months, a.tech)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
