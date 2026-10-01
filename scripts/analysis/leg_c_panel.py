#!/usr/bin/env python3
"""Leg C panel: matched thermal units at their own margin, with cost, the owner's X and instruments.

    .venv/bin/python scripts/build/build_rival_solar.py [--tech wind]   # inputs (Task 1)
    .venv/bin/python scripts/analysis/leg_c_panel.py [--months 202201 ...]

Writes outputs/tables/leg_c_panel.parquet, one row per unit x date x period, 2018-2023,
for the JRC-matched gas and coal units (`jrc_cab_match.parquet`). Framework spec §4, leg C.

SAMPLE. A unit-period is kept when the unit is PARTLY DISPATCHED -- some of its offered
volume cleared and some did not, so the price lies on its own curve and its cost is the
firm's marginal cost -- and it CLEARED in the periods just before and after, so any
start-up is sunk. Neighbours are UTC instants (`at_margin`), so midnight, month ends and
DST days need no special case; the bid months are concatenated before neighbours are found.
Clean periods only (`firm_x.clean`: no market split, clearing identity holds), so the
Spanish price is the price.

OWNER. The majority owner in the OMIE listing in force that day (nearest preceding
snapshot), as its exposed group (`omie_owner.exposed_group`). REPSOL rows before its
Viesgo purchase (2018-11-02) are dropped, as in leg D. A row whose owner has no X (Bizkaia
Energia, Amorebieta's owner until 2022-02-08) is dropped and counted.

COLUMNS
  p            clearing price, EUR/MWh
  c            implied marginal cost, gas-capped from 2022-06-15 (marginal_cost_capped_eur_mwh)
  c_uncapped   the cost at the market gas price
  fuel_index   c * eff: fuel price plus emission factor x CO2, per MWh of heat (spec 2)
  eff, eff_is_generic, fuel
  var_term     the declared minimum-income variable term (cab), NaN when not declared (route 3)
  X            owner's exposed n / rivals' slope within +-5 EUR/MWh (firm_incentive_net), EUR/MWh
  zw, zs       owner's rivals' offered wind and solar, GW (instruments)
  wk           ISO year x 100 + week (clusters)
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
sys.path.insert(0, str(ROOT / "scripts" / "build"))
from build_rival_solar import thermal_groups  # noqa: E402
from leg_d_panel import REPSOL_VIESGO  # noqa: E402
from omie_owner import exposed_group  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
BIDS = DATA / "omie/bids/parquet"
CAB = DATA / "omie/cab/parquet"
OUT = TABLES / "leg_c_panel.parquet"
YEARS = (2018, 2023)
TOL = 0.1  # MW: "some cleared, some not" needs more than rounding on each side


def unit_periods(f: Path, units: list[str]) -> pd.DataFrame:
    """One bid month -> unit, date, period, offered_mw (status O) and cleared_mw (status C), sell side."""
    b = pq.read_table(f, columns=["date", "period", "unit", "side", "status", "power_mw"],
                      filters=[("unit", "in", units), ("side", "==", "V")]).to_pandas()
    b["unit"] = b.unit.astype(str)
    g = b.groupby(["unit", "date", "period", "status"]).power_mw.sum().unstack("status", fill_value=0.0)
    g = g.reindex(columns=["O", "C"], fill_value=0.0)
    return g.rename(columns={"O": "offered_mw", "C": "cleared_mw"}).reset_index()


def at_margin(up: pd.DataFrame) -> pd.Series:
    """Partly dispatched now, and cleared at the UTC instants just before and after.

    `up` has unit, utc, resolution_min, offered_mw, cleared_mw for every period the unit
    offered; a neighbour the unit did not offer in counts as not cleared."""
    on = up.loc[up.cleared_mw > TOL, ["unit", "utc"]].assign(on=True)
    step = pd.to_timedelta(up.resolution_min, unit="min")

    def cleared_at(shift: pd.Series) -> pd.Series:
        # Keep utc a time-zone-aware Series: .to_numpy() would turn it into objects.
        q = pd.DataFrame({"unit": up.unit, "utc": up.utc + shift}).reset_index(drop=True)
        return q.merge(on, on=["unit", "utc"], how="left").on.notna()

    partly = ((up.cleared_mw > TOL) & (up.offered_mw - up.cleared_mw > TOL)).reset_index(drop=True)
    ok = partly & cleared_at(-step) & cleared_at(step)
    return pd.Series(ok.to_numpy(), index=up.index)


def owner_listings(units: list[str]) -> pd.DataFrame:
    """unit, date (snapshot), firm: the majority owner's exposed group in every OMIE listing."""
    lst = pd.read_parquet(DATA / "omie/registry/omie_unit_lists.parquet",
                          columns=["snapshot", "unit", "agent_owner", "ownership_pct"])
    lst = lst[lst.unit.isin(units)].sort_values("ownership_pct", ascending=False)
    lst = lst.drop_duplicates(["snapshot", "unit"]).copy()
    lst["date"] = pd.to_datetime(lst.snapshot).astype("datetime64[us]")
    lst["firm"] = lst.agent_owner.map(exposed_group)
    return lst[["unit", "date", "firm"]].sort_values("date")


def instruments(groups: tuple[str, ...]) -> pd.DataFrame:
    """date, period, firm, zw, zs: each group's rivals' offered wind and solar, GW."""
    parts = []
    for tech, col in (("wind", "zw"), ("solar", "zs")):
        r = pd.read_parquet(TABLES / f"rival_{tech}.parquet")
        r["date"] = pd.to_datetime(r.date)
        long = pd.concat([r[["date", "period"]].assign(firm=g, **{col: r[f"z_rival_{g}"] / 1000})
                          for g in groups if f"z_rival_{g}" in r])
        parts.append(long.set_index(["date", "period", "firm"]))
    return pd.concat(parts, axis=1).reset_index()


def declared_var(units: list[str], months: list[str]) -> pd.DataFrame:
    """unit, date, var_term: the last declared minimum-income variable term of the day (sell side)."""
    parts = []
    for ym in months:
        f = CAB / f"cab_{ym}.parquet"
        if f.exists():
            c = pd.read_parquet(f, columns=["date", "unit", "side", "version", "min_income_var_eur_mwh"])
            c = c[c.unit.isin(units) & (c.side == "V")].sort_values("version")
            parts.append(c.drop_duplicates(["unit", "date"], keep="last"))
    v = pd.concat(parts, ignore_index=True)
    v["date"] = pd.to_datetime(v.date)
    return v[["unit", "date"]].assign(var_term=v.min_income_var_eur_mwh.where(v.min_income_var_eur_mwh > 0))


def build(months: list[str] | None) -> pd.DataFrame:
    units = sorted(pd.read_parquet(DATA / "jrc_ppdb/jrc_cab_match.parquet", columns=["unit"]).unit.astype(str))
    files = [f for f in sorted(BIDS.glob("bids_*.parquet"))
             if YEARS[0] <= int(f.stem.split("_")[1][:4]) <= YEARS[1]]
    if months:
        files = [f for f in files if f.stem.split("_")[1] in months]
    up = pd.concat([unit_periods(f, units) for f in files], ignore_index=True)
    up["date"] = pd.to_datetime(up.date)
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "price_es", "utc_timestamp", "resolution_min"])
    px["date"] = pd.to_datetime(px.date)
    up = up.merge(px.rename(columns={"utc_timestamp": "utc"}), on=["date", "period"])
    up["utc"] = pd.to_datetime(up.utc, utc=True)
    d = up[at_margin(up).to_numpy()].copy()
    print(f"{len(up):,} unit-periods offered; {len(d):,} at the unit's own margin")
    clean = pd.read_parquet(TABLES / "firm_x.parquet", columns=["date", "period", "clean"])
    clean = clean.drop_duplicates(["date", "period"])
    clean["date"] = pd.to_datetime(clean.date)
    d = d.merge(clean, on=["date", "period"])
    d = d[d.clean].drop(columns="clean")
    print(f"  {len(d):,} in clean periods")
    left = d.assign(date=d.date.astype("datetime64[us]")).sort_values("date")
    d = pd.merge_asof(left, owner_listings(units), on="date", by="unit", direction="backward")
    d = d[~((d.firm == "REPSOL") & (d.date < REPSOL_VIESGO))]
    groups = thermal_groups()
    x = pd.read_parquet(TABLES / "firm_incentive_net.parquet",
                        columns=["date", "period", "firm", "net_exp_mw", "slope_exp_h5"],
                        filters=[("firm", "in", list(groups))])
    x["date"] = pd.to_datetime(x.date).astype("datetime64[us]")
    x["X"] = x.net_exp_mw / x.slope_exp_h5
    d = d.merge(x[["date", "period", "firm", "X"]], on=["date", "period", "firm"], how="left")
    z = instruments(groups)
    z["date"] = z.date.astype("datetime64[us]")
    d = d.merge(z, on=["date", "period", "firm"], how="left")
    cost = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet",
                           columns=["unit", "date", "fuel", "eff", "eff_is_generic",
                                    "marginal_cost_eur_mwh", "marginal_cost_capped_eur_mwh"])
    cost["date"] = pd.to_datetime(cost.date).astype("datetime64[us]")
    d = d.merge(cost.rename(columns={"marginal_cost_capped_eur_mwh": "c",
                                     "marginal_cost_eur_mwh": "c_uncapped"}), on=["unit", "date"], how="left")
    ym = sorted({f.stem.split("_")[1] for f in files})
    v = declared_var(units, ym)
    v["date"] = v.date.astype("datetime64[us]")
    d = d.merge(v, on=["unit", "date"], how="left")
    miss = d[["X", "zw", "zs", "c"]].isna()
    print("dropped for a missing column:", miss.sum().to_dict(),
          "| owners without X:", d.loc[miss.X, "firm"].value_counts().to_dict())
    d = d[~miss.any(axis=1)].copy()
    d["p"] = d.price_es
    d["fuel_index"] = d.c * d.eff
    iso = d.date.dt.isocalendar()
    d["wk"] = (iso.year.astype(int) * 100 + iso.week.astype(int)).astype("int32")
    cols = ["unit", "firm", "fuel", "date", "period", "utc", "wk", "p", "c", "c_uncapped", "fuel_index",
            "eff", "eff_is_generic", "var_term", "X", "zw", "zs", "offered_mw", "cleared_mw"]
    d = d[cols].sort_values(["unit", "date", "period"]).reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(d):,} unit-periods, {d.unit.nunique()} units)")
    return d


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*", help="YYYYMM months only (for checks)")
    build(ap.parse_args().months)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
