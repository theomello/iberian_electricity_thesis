#!/usr/bin/env python3
"""Rivals' offered solar, per firm and period: the leg D instrument.

    .venv/bin/python scripts/build/build_rival_solar.py [--months 202406 ...]

Writes outputs/tables/rival_solar.parquet, one row per day-ahead period that has
a price and a bid file:

    z_all            MW of solar offered day-ahead by every solar-labelled supply unit
    own_<FIRM>       the part offered by units whose owner group is FIRM
    z_rival_<FIRM>   z_all - own_<FIRM>, the instrument for FIRM (framework spec §4, leg D)

Built exactly as `build_solar_instrument.py` builds `z_offered` (sell offers,
status O, solar-labelled units outside the purchase roles), once for each of the
five firms instead of for EDP alone. A firm's own solar is every unit whose
owner rolls up to it under `owner_group` -- pass-through entities included, so
no volume the firm's group bids enters its own instrument. For EDP this
reproduces `z_offered`; `scripts/qa/check_rival_solar.py` checks it. Periods
with no solar offer (night) carry 0, not a gap.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_owner import owner_group  # noqa: E402

DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
OUT = ROOT / "outputs/tables/rival_solar.parquet"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")
KEY = ["date", "period"]


def solar_units() -> pd.Series:
    """unit -> owner group, for the solar-labelled supply units z_offered uses."""
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                        columns=["unit", "role", "tech", "tech_omie", "tech_omie_early", "agent_owner"])
    label = u.tech_omie.fillna(u.tech_omie_early).fillna(u.tech)
    s = u[(label == "solar") & ~u.role.str.startswith("purchase")]
    return pd.Series(s.agent_owner.map(owner_group).to_numpy(), index=s.unit.astype(str).to_numpy())


def month(f: Path, grp: pd.Series) -> pd.DataFrame:
    b = pq.read_table(f, columns=["date", "period", "unit", "side", "status", "power_mw"],
                      filters=[("unit", "in", list(grp.index)), ("side", "==", "V"),
                               ("status", "==", "O")]).to_pandas()
    b["grp"] = b.unit.astype(str).map(grp)
    k = [b.date, b.period]
    parts = [b.power_mw.groupby(k).sum().rename("z_all")]
    for firm in FIRMS:
        parts.append(b.power_mw.where(b.grp == firm, 0.0).groupby(k).sum().rename(f"own_{firm}"))
    return pd.concat(parts, axis=1).reset_index()


def build(months: list[str] | None) -> pd.DataFrame:
    grp = solar_units()
    print(f"{len(grp)} solar-labelled supply units; the five firms own "
          + ", ".join(f"{f} {(grp == f).sum()}" for f in FIRMS))
    files = sorted(BIDS.glob("bids_*.parquet"))
    if months:
        files = [f for f in files if f.stem.split("_")[1] in months]
    parts = []
    for f in files:
        parts.append(month(f, grp))
        print(f"  {f.stem}", file=sys.stderr, flush=True)
    d = pd.concat(parts, ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet", columns=KEY)
    px["date"] = pd.to_datetime(px.date)
    ym = {f.stem.split("_")[1] for f in files}
    px = px[px.date.dt.strftime("%Y%m").isin(ym)]
    d = px.merge(d, on=KEY, how="left")
    num = [c for c in d.columns if c not in KEY]
    d[num] = d[num].fillna(0.0)
    for firm in FIRMS:
        d[f"z_rival_{firm}"] = d.z_all - d[f"own_{firm}"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(d):,} periods)")
    return d


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*", help="YYYYMM months only (for checks)")
    build(ap.parse_args().months)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
