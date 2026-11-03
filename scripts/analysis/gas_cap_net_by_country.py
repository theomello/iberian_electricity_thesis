#!/usr/bin/env python3
"""The cap's net with Spain and Portugal separated (notes/rq-crisis-quantity.md, section F, fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_net_by_country.py [--units panel|ccgt_coal]

Saving to Spanish and to Portuguese buyers from the no-pass-through re-clear (`gas_cap_consumer_saving.py`
output for the same --units), the Spanish bill from ESIOS (1908 x 351 + 1909 x 352 + 1907 x 353), and the
Portuguese bill bounded above by the subsidy attached to the Portuguese plants (S x their cleared MWh).
Writes outputs/tables/gas_cap_net_by_country{,_ccgt_coal}.csv.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_consumer_saving import subsidy_and_units, wider  # noqa: E402
from gas_cap_group_net import MONTHS, esios, group_buys, unit_groups  # noqa: E402
from step_curves import BIDS, KEY  # noqa: E402

T = ROOT / "outputs" / "tables"
RHOS = [0.55, 0.73, 0.75, 1.00]
SPAIN = ["reference", "free", "generic", "other_es", "pumping"]


def plant_mwh(units: set, country: pd.Series, valid_days: set) -> pd.DataFrame:
    out = []
    for ym in MONTHS:
        b = pq.read_table(BIDS / f"bids_{ym}.parquet", columns=["date", "period", "unit", "side", "status", "power_mw"]).to_pandas()
        b["date"] = pd.to_datetime(b.date)
        b = b[(b.status.astype(str) == "C") & (b.side.astype(str) == "V") & b.unit.astype(str).isin(units) & b.date.isin(valid_days)]
        b["c"] = b.unit.astype(str).map(country).fillna("ES")
        out.append(b.groupby(["date", "period", "c"]).power_mw.sum().unstack(fill_value=0.0).reset_index())
    p = pd.concat(out, ignore_index=True)
    for c in ("ES", "PT"):
        if c not in p.columns:
            p[c] = 0.0
    return p.rename(columns={"ES": "plant_es", "PT": "plant_pt"})[KEY + ["plant_es", "plant_pt"]]


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--units", choices=["panel", "ccgt_coal"], default="panel")
    a = ap.parse_args()
    sfx = "" if a.units == "panel" else f"_{a.units}"
    H = pd.read_parquet(T / f"gas_cap_consumer_saving_hourly{sfx}.parquet")
    H["date"] = pd.to_datetime(H.date)
    V = H[H.valid].copy()
    _, panel_units = subsidy_and_units()
    units = wider(panel_units, a.units)
    reg = pd.read_parquet(ROOT / "data/omie/registry/unit_registry.parquet", columns=["unit", "country"]).drop_duplicates("unit")
    country = reg.set_index("unit").country
    days = set(V.date.unique())
    gb = group_buys(unit_groups(), days).rename(columns={"free": "da_free", "reference": "da_ref"})
    pm = plant_mwh(units, country, days)
    D = pd.concat([esios(i) for i in (351, 352, 353, 1907, 1908, 1909)], axis=1).reset_index()
    M = V.merge(gb, on=KEY, how="left").merge(pm, on=KEY, how="left").merge(D, on=KEY, how="left").fillna(0.0)
    sp = {"reference": "da_ref", "free": "da_free", "generic": "generic", "other_es": "other_es", "pumping": "pumping"}
    bill_es = float((M["1908"] * M["351"] + M["1909"] * M["352"] + M["1907"] * M["353"]).sum() / 1e6)
    b_es = float((M.S * M.plant_es).sum() / 1e6)
    b_pt = float((M.S * M.plant_pt).sum() / 1e6)
    print(f"{a.units}: {len(units)} units; valid hours {len(M):,}")
    print(f"Spanish bill (ESIOS, three groups) EUR {bill_es:,.0f} m; subsidy on Spanish plants B_ES {b_es:,.0f} m "
          f"(bill / B_ES {bill_es / b_es:.2f}); on Portuguese plants B_PT {b_pt:,.0f} m "
          f"({int(M.plant_pt.sum() / 1e3):,} GWh); Spanish plants {int(M.plant_es.sum() / 1e3):,} GWh")
    rows = []
    for r in RHOS:
        d = M[f"p0_{r:.2f}"] - M.p_clear
        g_es = float(sum((d * M[c]).sum() for c in sp.values()) / 1e6)
        g_pt = float((d * M.portugal).sum() / 1e6)
        g_x = float((d * M.unknown).sum() / 1e6)
        rows.append({"units": a.units, "rho": r, "saving_spain": g_es, "saving_portugal": g_pt, "saving_exports_unregistered": g_x,
                     "saving_total": g_es + g_pt + g_x, "bill_spain": bill_es, "net_spain": g_es - bill_es,
                     "b_portugal": b_pt, "net_portugal_lower_bound": g_pt - b_pt, "b_spanish_plants": b_es})
    R = pd.DataFrame(rows)
    R.to_csv(T / f"gas_cap_net_by_country{sfx}.csv", index=False)
    print(R.drop(columns=["units"]).round({c: 0 for c in R.columns if c != "rho"}).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
