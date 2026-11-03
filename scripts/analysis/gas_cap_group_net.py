#!/usr/bin/env python3
"""Net of the cap's pass-through by buyer group (notes/rq-crisis-quantity.md, "net by buyer group", fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_group_net.py

Reference suppliers and free-market retailers, valid hours of 2022-06-15 -> 2023-02-25, 54 modelled gas units:
  bill_g   = sum_h charge_g,h x PBF demand_g,h   (ESIOS 1909 x 352; 1908 x 351)
  saving_g = sum_h (p0_h - p_h) x cleared day-ahead buy MWh of g's units in h   (p0: the no-pass-through re-clear)
  net_g    = saving_g - bill_g, in EUR m and per MWh of the group's PBF demand.
Groups of units: Spanish units whose OMIE listing owner is a regulated pass-through supplier (reference suppliers);
Spanish registry role `purchase_retail` outside that set (free-market retailers).

Reads gas_cap_consumer_saving_hourly.parquet (run gas_cap_consumer_saving.py first). Writes
outputs/tables/gas_cap_group_net.csv and gas_cap_group_share_monthly.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from omie_owner import is_pass_through  # noqa: E402
from step_curves import BIDS, KEY, hid  # noqa: E402

T = ROOT / "outputs" / "tables"
MONTHS = ["202206", "202207", "202208", "202209", "202210", "202211", "202212", "202301", "202302"]
RHOS = [0.55, 0.73, 0.75, 1.00]


def esios(i: int) -> pd.Series:
    x = pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet")
    x["date"] = pd.to_datetime(x.datetime.str[:10])
    x["period"] = x.datetime.str[11:13].astype(int) + 1
    return x.groupby(KEY).value.mean().rename(str(i))


def unit_groups() -> pd.Series:
    """reference / free / generic / pumping / other_es (Spanish), portugal, and unknown (not in the registry:
    mostly the interconnection pseudo-units, i.e. exports)."""
    reg = pd.read_parquet(ROOT / "data/omie/registry/unit_registry.parquet", columns=["unit", "country", "role"])
    ag = pd.read_parquet(ROOT / "data/omie/registry/unit_agents.parquet", columns=["unit", "agent_owner"])
    u = reg.merge(ag, on="unit", how="left").drop_duplicates("unit")
    ref = u.agent_owner.map(is_pass_through).fillna(False)
    g = pd.Series("other_es", index=u.unit.to_numpy())
    g[(u.role == "purchase_retail").to_numpy()] = "free"
    g[(u.role == "storage_mixed").to_numpy()] = "generic"
    g[(u.role == "pumping").to_numpy()] = "pumping"
    g[(u.country == "PT").to_numpy()] = "portugal"
    g[((u.country != "ES") & (u.country != "PT")).to_numpy()] = "unknown"
    g[(ref & (u.country == "ES")).to_numpy()] = "reference"
    return g


def group_buys(groups: pd.Series, valid_days: set) -> pd.DataFrame:
    out = []
    for ym in MONTHS:
        b = pq.read_table(BIDS / f"bids_{ym}.parquet",
                          columns=["date", "period", "unit", "side", "status", "power_mw"]).to_pandas()
        b["date"] = pd.to_datetime(b.date)
        b = b[(b.status.astype(str) == "C") & (b.side.astype(str) == "C") & b.date.isin(valid_days)]
        b["g"] = b.unit.astype(str).map(groups).fillna("unknown")
        out.append(b.groupby(["date", "period", "g"]).power_mw.sum().unstack(fill_value=0.0).reset_index())
    return pd.concat(out, ignore_index=True)


def main() -> int:
    H = pd.read_parquet(T / "gas_cap_consumer_saving_hourly.parquet")
    H["date"] = pd.to_datetime(H.date)
    V = H[H.valid].copy()
    gb = group_buys(unit_groups(), set(V.date.unique())).rename(columns={"free": "da_free", "reference": "da_ref"})
    CATS = ["reference", "free", "generic", "pumping", "other_es", "portugal", "unknown"]
    for c_ in CATS:
        if c_ not in ("reference", "free") and c_ not in gb.columns:
            gb[c_] = 0.0
    D = pd.concat([esios(i) for i in (351, 352, 1908, 1909)], axis=1).reset_index()
    M = V.merge(gb, on=KEY, how="left").merge(D, on=KEY, how="left")
    M["mo"] = M.date.dt.strftime("%Y-%m")

    share = M.groupby("mo").apply(lambda d: pd.Series({
        "da_free_gwh": d.da_free.sum() / 1e3, "pbf_free_gwh": d["351"].sum() / 1e3,
        "da_ref_gwh": d.da_ref.sum() / 1e3, "pbf_ref_gwh": d["352"].sum() / 1e3,
        "da_generic_gwh": d.generic.sum() / 1e3}))
    share["share_free_plus_generic"] = (share.da_free_gwh + share.da_generic_gwh) / share.pbf_free_gwh
    share["share_free"] = share.da_free_gwh / share.pbf_free_gwh
    share["share_ref"] = share.da_ref_gwh / share.pbf_ref_gwh
    share["ratio"] = share.share_free / share.share_ref
    c = M.groupby("mo").apply(lambda d: d["1908"].mean() / d["1909"].mean())
    share["charge_ratio"] = c
    print("day-ahead purchases over scheduled (PBF) demand, by month:")
    print(share.round(2).to_string())
    share.reset_index().to_csv(T / "gas_cap_group_share_monthly.csv", index=False)

    rows = []
    for g, da, pbf, ch in (("reference suppliers", "da_ref", "352", "1909"), ("free-market retailers", "da_free", "351", "1908")):
        bill = float((M[ch] * M[pbf]).sum() / 1e6)
        mwh = float(M[pbf].sum())
        for r in RHOS:
            sav = float(((M[f"p0_{r:.2f}"] - M.p_clear) * M[da]).sum() / 1e6)
            rows.append({"group": g, "rho": r, "saving_eur_m": sav, "bill_eur_m": bill, "net_eur_m": sav - bill,
                         "net_per_mwh": (sav - bill) * 1e6 / mwh, "pbf_gwh": mwh / 1e3,
                         "da_gwh": float(M[da].sum() / 1e3)})
    cols = {"reference": "da_ref", "free": "da_free", **{c_: c_ for c_ in CATS if c_ not in ("reference", "free")}}
    who = []
    for c_, col in cols.items():
        for r in RHOS:
            who.append({"category": c_, "rho": r, "da_gwh": float(M[col].sum() / 1e3),
                        "saving_eur_m": float(((M[f"p0_{r:.2f}"] - M.p_clear) * M[col]).sum() / 1e6)})
    W_ = pd.DataFrame(who)
    W_["share_of_saving"] = W_.saving_eur_m / W_.groupby("rho").saving_eur_m.transform("sum")
    W_.to_csv(T / "gas_cap_saving_by_category.csv", index=False)
    print("\nwho receives the wholesale saving (day-ahead buys by category):")
    print(W_[W_.rho.isin([0.55, 0.73, 0.75])].pivot(index="category", columns="rho", values="saving_eur_m").round(0).assign(
        da_gwh=W_[W_.rho == 0.73].set_index("category").da_gwh.round(0), share_073=W_[W_.rho == 0.73].set_index("category").share_of_saving.round(3)).to_string())
    assert abs(sum(M[col].sum() for col in cols.values()) - M.buy_mw.sum()) / M.buy_mw.sum() < 1e-3, "categories must cover all cleared buys"
    R = pd.DataFrame(rows)
    R.to_csv(T / "gas_cap_group_net.csv", index=False)
    print("\nnet by group (54 units, valid hours):")
    print(R.round(1).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
