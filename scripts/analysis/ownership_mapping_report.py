#!/usr/bin/env python3
"""How good is the unit -> firm mapping, and what does using today's owner cost?

    .venv/bin/python scripts/analysis/ownership_mapping_report.py

The firm panels (`firm_x.py`, `firm_incentive_rebuild.py`) give each unit its most
recent listed owner (`unit_agents.agent_owner`, OMIE's latest *Listado de
Unidades* naming the unit) for the whole window. OMIE's listings are snapshots
(12, 2014-09-24 -> 2025-01-31, none for 2021), so the owner in force on a date is
the nearest PRECEDING snapshot that lists the unit (a co-owned unit follows its
largest share), else the nearest following one. This script measures:

  1. coverage: cleared volume (sell and buy) whose unit has an owner group, by year;
  2. how groups were built: `owner_groups.source`, by cleared volume;
  3. static vs dated: cleared volume whose static group differs from the dated one,
     by year and, for every group with sizeable volume, by firm;
  4. representation: each sizeable group's sell volume from units whose name says
     they are third parties' plant (REPRESENTAD*, R. ESPECIAL), where the group's
     X is not its own exposure;
  5. the (static, dated) group pairs behind the differences, which separate real
     ownership changes from renamings the grouping has not merged;
  6. co-owned units: the static owner is ONE of the co-owners, not always the
     largest; the average MW each group gains or loses against a pro-rata split.

Writes outputs/tables/ownership_mapping_report_{year,firm,pairs,coowned}.csv.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_owner import is_pass_through, owner_group  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
REG = DATA / "omie/registry"


CACHE = TABLES / "cleared_unit_month.parquet"   # gitignored, like every outputs/tables parquet


def cleared_by_unit_month() -> pd.DataFrame:
    """unit, month, side (V sell / C buy) -> cleared energy, GWh. Cached: reading the
    102 bid months takes minutes; delete the cache after a bid refresh."""
    if CACHE.exists():
        c = pd.read_parquet(CACHE)
        c["month"] = pd.PeriodIndex(c.month, freq="M")
        return c
    out = []
    for f in sorted(glob.glob(str(DATA / "omie/bids/parquet/bids_*.parquet"))):
        b = pq.read_table(f, columns=["date", "unit", "side", "status", "power_mw", "resolution_min"],
                          filters=[("status", "==", "C")]).to_pandas()
        b["gwh"] = b.power_mw * b.resolution_min / 60 / 1000
        b["month"] = pd.to_datetime(b.date).dt.to_period("M")
        out.append(b.groupby(["unit", "month", "side"], observed=True).gwh.sum().reset_index())
        print(f"  {Path(f).name}", end="\r", flush=True)
    print()
    c = pd.concat(out)
    c["unit"], c["side"] = c.unit.astype(str), c.side.astype(str)
    c.assign(month=c.month.astype(str)).to_parquet(CACHE, index=False)
    return c


def dated_owner(units_months: pd.DataFrame) -> pd.Series:
    """The owner group in force for each (unit, month): nearest preceding snapshot, else following."""
    lst = pd.read_parquet(REG / "omie_unit_lists.parquet", columns=["snapshot", "unit", "agent_owner", "ownership_pct"])
    lst = lst.sort_values("ownership_pct", ascending=False).drop_duplicates(["snapshot", "unit"])
    lst["snapshot"] = pd.to_datetime(lst.snapshot).astype("datetime64[ns]")
    lst["group"] = lst.agent_owner.map(owner_group)
    um = units_months.copy()
    um["t"] = um.month.dt.to_timestamp(how="end").dt.normalize().astype("datetime64[ns]")
    um = um.sort_values("t")
    lst = lst.sort_values("snapshot")
    pre = pd.merge_asof(um, lst[["snapshot", "unit", "group"]], left_on="t", right_on="snapshot",
                        by="unit", direction="backward")
    post = pd.merge_asof(um, lst[["snapshot", "unit", "group"]], left_on="t", right_on="snapshot",
                         by="unit", direction="forward")
    g = pre.group.fillna(post.group)
    return pd.Series(g.to_numpy(), index=pd.MultiIndex.from_frame(pre[["unit", "month"]]))


def main() -> int:
    c = cleared_by_unit_month()
    ua = pd.read_parquet(REG / "unit_agents.parquet", columns=["unit", "descr", "agent_owner"])
    ua["static"] = ua.agent_owner.map(owner_group)
    ua["pass_through"] = ua.agent_owner.map(is_pass_through).astype(bool)
    c = c.merge(ua[["unit", "descr", "static", "pass_through"]], on="unit", how="left")
    um = c[["unit", "month"]].drop_duplicates()
    dated = dated_owner(um)
    c["dated"] = dated.reindex(pd.MultiIndex.from_frame(c[["unit", "month"]])).to_numpy()
    c["year"] = c.month.dt.year
    c["has_group"] = c.static.notna()
    c["differs"] = c.static.notna() & c.dated.notna() & (c.static != c.dated)
    c["repr"] = c.descr.fillna("").str.upper().str.contains("REPRESENTAD|R\\. ESPECIAL|R ESPECIAL")

    # 1 + 3: by year and side
    y = c.groupby(["year", "side"]).apply(lambda g: pd.Series({
        "cleared_TWh": g.gwh.sum() / 1000,
        "with_owner_group": g.loc[g.has_group, "gwh"].sum() / g.gwh.sum(),
        "static_differs_from_dated": g.loc[g.differs, "gwh"].sum() / g.gwh.sum(),
    }), include_groups=False).reset_index()
    y["side"] = y.side.map({"V": "sell", "C": "buy"})
    print("\nBY YEAR: share of cleared volume")
    print(y.round(3).to_string(index=False))

    # 2: how groups were built, by cleared volume
    og = pd.read_parquet(REG / "owner_groups.parquet", columns=["agent_owner", "source"])
    c = c.merge(ua[["unit", "agent_owner"]], on="unit", how="left").merge(og, on="agent_owner", how="left")
    s = c.groupby("source", dropna=False).gwh.sum()
    print("\nGROUP SOURCE, share of cleared volume (both sides)")
    print((s / s.sum()).round(3).sort_values(ascending=False).to_string())

    # 3 + 4: by firm, for groups with sizeable volume
    f = c[c.has_group].groupby("static").apply(lambda g: pd.Series({
        "cleared_TWh": g.gwh.sum() / 1000,
        "sell_TWh": g.loc[g.side == "V", "gwh"].sum() / 1000,
        "buy_TWh": g.loc[g.side == "C", "gwh"].sum() / 1000,
        "share_dated_owner_differs": g.loc[g.differs, "gwh"].sum() / g.gwh.sum(),
        "years_affected": ", ".join(str(v) for v in sorted(g.loc[g.differs & (g.gwh > 0), "year"].unique())),
        "share_sell_represented": (g.loc[(g.side == "V") & g.repr, "gwh"].sum()
                                   / max(g.loc[g.side == "V", "gwh"].sum(), 1e-9)),
        "share_pass_through": g.loc[g.pass_through, "gwh"].sum() / g.gwh.sum(),
    }), include_groups=False).sort_values("cleared_TWh", ascending=False)
    f = f[f.cleared_TWh >= 5]
    print(f"\nBY FIRM (groups with >= 5 TWh cleared 2018-2026: {len(f)})")
    print(f.round(3).to_string())
    # 5: which (static, dated) pairs carry the differences
    x = c[c.differs]
    pairs = x.groupby(["static", "dated"]).agg(
        TWh=("gwh", lambda v: v.sum() / 1000), units=("unit", "nunique"),
        first_year=("year", "min"), last_year=("year", "max")).sort_values("TWh", ascending=False)
    print("\nSTATIC vs DATED GROUP PAIRS, largest 15")
    print(pairs.head(15).round(2).to_string())

    # 6: co-owned units, static single owner against a pro-rata split (latest listing's shares)
    lst = pd.read_parquet(REG / "omie_unit_lists.parquet", columns=["snapshot", "unit", "agent_owner", "ownership_pct"])
    last = lst[lst.snapshot == lst.snapshot.max()]
    co = last.groupby("unit").agent_owner.nunique()
    co = list(co[co > 1].index)
    hours = (c.month.max().to_timestamp(how="end") - c.month.min().to_timestamp()).total_seconds() / 3600
    sell = c[(c.side == "V") & c.unit.isin(co)].groupby("unit").gwh.sum()
    static = ua.set_index("unit").static
    diff: dict[str, float] = {}
    for u, gwh in sell.items():
        mw = gwh * 1000 / hours
        diff[static[u]] = diff.get(static[u], 0.0) + mw
        for _, r in last[last.unit == u].iterrows():
            g = owner_group(r.agent_owner)
            diff[g] = diff.get(g, 0.0) - mw * r.ownership_pct / 100
    cw = pd.Series(diff, name="static_minus_prorata_mw").round(1).sort_values()
    cw = cw[cw.abs() >= 1]
    print(f"\nCO-OWNED UNITS in the latest listing: {len(co)}, {sell.sum() / c.loc[c.side == 'V', 'gwh'].sum():.3f} "
          f"of cleared sell volume; static minus pro-rata, average MW:")
    print(cw.to_string())

    y.to_csv(TABLES / "ownership_mapping_report_year.csv", index=False)
    f.to_csv(TABLES / "ownership_mapping_report_firm.csv")
    pairs.to_csv(TABLES / "ownership_mapping_report_pairs.csv")
    cw.to_csv(TABLES / "ownership_mapping_report_coowned.csv")
    print("\n-> outputs/tables/ownership_mapping_report_{year,firm,pairs,coowned}.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
