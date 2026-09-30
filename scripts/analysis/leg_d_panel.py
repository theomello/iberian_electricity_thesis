#!/usr/bin/env python3
"""Leg D panel: dispatchable units' offer shape by hour, with the firm's X and instruments.

    .venv/bin/python scripts/analysis/firm_x.py                  # input: X, net position, clean
    .venv/bin/python scripts/build/build_rival_solar.py          # input: the instrument
    .venv/bin/python scripts/build/build_solar_instrument.py     # input: period timestamps
    .venv/bin/python scripts/analysis/leg_d_panel.py [--months 202406 ...]

Writes outputs/tables/leg_d_panel.parquet, one row per unit x date x hour.
Framework spec §4, leg D.

UNITS. Storage hydro, pumped-storage turbines, combined cycle and coal
(`hydro`, `pumped storage`, `gas CCGT`, `coal` under OMIE's technology label),
supply roles, sell offers only. `firm` is the unit's exposed group
(`omie_owner.exposed_group`) when it is one of the five; any other owner is
`FRINGE`, kept only at FRINGE_MIN_MW or more, for the placebo.

OWNERS. A unit-day is kept only when the OMIE listing in force that day (nearest
preceding snapshot) puts the unit in the firm X is built for: `firm_x` uses one
static owner per unit, and Castejon (EDP's until sold) and PVENT1 (Alpiq's to
2018) would otherwise carry another firm's X. A co-owned unit follows its majority
owner. REPSOL rows
before its purchase of Viesgo (REPSOL_VIESGO) are dropped: the roll-up maps Viesgo
to Repsol on every date, so REPSOL's X adds two firms together before it.

OUTCOME. The §3.14 measure from `edp_quantity_at_price.month_outcomes`: MW
offered at or below the unit-DAY's volume-weighted 25/50/75% offer price, and
the offer density within +/-5 EUR/MWh of it, divided here by the unit-day's
capacity (`cab` max power that day; the registry's when `cab` has none). In a
unit-day the unit is present in, a period with no offer scores 0.

FIRM TERMS. X, the exposed net position and `clean` from `firm_x.parquet`.
Periods kept: clean (no market split, clearing identity holds) and, for the
five firms, X defined (rivals' slope >= 5 MW per EUR/MWh).

HOURS. Periods are averaged to hours, so a day weighs the same before and after
the 15-minute switch of 2025-10-01. Xp and Xm are hourly means of max(X, 0) and
min(X, 0), so Xp + Xm = X.

SIGN YESTERDAY. s_prev = 1 if the firm's mean exposed net position in the same
hour of the previous day was positive, else 0. It is known when the offer is
made. NaN when either day is not 24 hours long (the DST days and the days after
them), so hour numbers always refer to the same clock hour.

INSTRUMENTS. z = rivals' offered solar for the firm, `z_rival_<FIRM>`, in GW
(`z_all` for FRINGE); zs = z * s_prev. For robustness, s_prev7 and zs7 use the
sign in the same hour SEVEN days before: s_prev is a lagged outcome, and with
errors persistent across days a one-day lag over-rejects (reviewer, 2026-10-01). CONTROL: fcst, REE's day-ahead demand
forecast in GW.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from edp_quantity_at_price import month_outcomes  # noqa: E402
from omie_owner import exposed_group  # noqa: E402

DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
FIRM_X = ROOT / "outputs/tables/firm_x.parquet"
RIVAL = ROOT / "outputs/tables/rival_solar.parquet"
SOLAR = ROOT / "outputs/tables/solar_instrument.parquet"
OUT = ROOT / "outputs/tables/leg_d_panel.parquet"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")
CLASSES = {"hydro": "hydro", "pumped storage": "pumped", "gas CCGT": "ccgt", "coal": "coal"}
SUPPLY_ROLES = ["generation", "generation_large", "storage_mixed", "pumping"]
FRINGE_MIN_MW = 50.0
LISTS = DATA / "omie/registry/omie_unit_lists.parquet"
# Repsol completed its purchase of Viesgo's generation on this date (public record, to
# verify). The owner roll-up maps Viesgo to Repsol on every date, so before it REPSOL's
# X adds two firms together and its rows are dropped.
REPSOL_VIESGO = pd.Timestamp("2018-11-02")
OVER_CAP = 1.02
KEY = ["date", "period"]
OUTC = ["s25", "s50", "s75", "d25", "d50", "d75"]


def span(months: list[str]) -> list[str]:
    """The months plus each one's previous month, so s_prev reaches back across month ends."""
    prev = {str(pd.Period(m, "M") - 1).replace("-", "") for m in months}
    return sorted(set(months) | prev)


def leg_d_units() -> pd.DataFrame:
    """unit, firm (one of the five or FRINGE), cls, reg_mw: leg D's population."""
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                        columns=["unit", "role", "tech", "tech_omie", "tech_omie_early",
                                 "agent_owner", "max_power_mw"])
    label = u.tech_omie.fillna(u.tech_omie_early).fillna(u.tech)
    u = u[label.isin(CLASSES) & u.role.isin(SUPPLY_ROLES)].copy()
    u["cls"] = label[u.index].map(CLASSES)
    g = u.agent_owner.map(exposed_group)
    u["firm"] = g.where(g.isin(FIRMS), "FRINGE")
    u = u[(u.firm != "FRINGE") | (u.max_power_mw >= FRINGE_MIN_MW)]
    return u.rename(columns={"max_power_mw": "reg_mw"})[["unit", "firm", "cls", "reg_mw"]]


def offered_total(f: Path, units: list[str]) -> pd.DataFrame:
    """unit, date, period, off_mw: all sell MW a unit offers in the period."""
    b = pq.read_table(f, columns=["date", "period", "unit", "side", "status", "power_mw"],
                      filters=[("unit", "in", units), ("side", "==", "V"),
                               ("status", "==", "O")]).to_pandas()
    b["unit"] = b.unit.astype(str)
    t = b.groupby(["unit", "date", "period"]).power_mw.sum().rename("off_mw").reset_index()
    t["date"] = pd.to_datetime(t.date)
    return t


def unit_day_capacity(units: list[str], months: list[str]) -> pd.DataFrame:
    parts = []
    for ym in months:
        f = DATA / f"omie/cab/parquet/cab_{ym}.parquet"
        if f.exists():
            c = pq.read_table(f, columns=["date", "unit", "max_power_mw"],
                              filters=[("unit", "in", units)]).to_pandas()
            parts.append(c.groupby(["unit", "date"]).max_power_mw.max().reset_index())
    c = pd.concat(parts, ignore_index=True)
    c["date"] = pd.to_datetime(c.date)
    return c.rename(columns={"max_power_mw": "cap_mw"})


def period_frame(months: list[str]) -> pd.DataFrame:
    """date, period, hour, day_hours, fcst (GW) for every priced period in the months."""
    s = pd.read_parquet(SOLAR, columns=["date", "period", "resolution_min", "utc_timestamp"])
    s["date"] = pd.to_datetime(s.date)
    s = s[s.date.dt.strftime("%Y%m").isin(months)].copy()
    s["hour"] = (s.period - 1) // (60 // s.resolution_min)
    s["day_hours"] = s.groupby("date").period.transform("size") * s.resolution_min / 60
    fc = pd.read_parquet(DATA / "ree/ree_demand_forecast_5min.parquet",
                         columns=["utc_timestamp", "demand_forecast_mw"])
    fc = fc.set_index(pd.to_datetime(fc.utc_timestamp, utc=True)).demand_forecast_mw
    start = pd.to_datetime(s.utc_timestamp, utc=True)
    s["fcst"] = np.nan
    for res, g in s.groupby("resolution_min"):
        m = fc.resample(f"{res}min").mean()
        s.loc[g.index, "fcst"] = m.reindex(pd.DatetimeIndex(start[g.index])).to_numpy() / 1000
    return s[KEY + ["hour", "day_hours", "fcst"]]


def firm_terms(months: list[str]) -> pd.DataFrame:
    x = pd.read_parquet(FIRM_X, columns=KEY + ["firm", "clean", "X", "net_mw", "zero_price"])
    x["date"] = pd.to_datetime(x.date)
    x = x[x.date.dt.strftime("%Y%m").isin(months)].copy()
    x["Xp"], x["Xm"] = x.X.clip(lower=0), x.X.clip(upper=0)
    return x


def seller_lagged(x: pd.DataFrame, per: pd.DataFrame, days: int, name: str) -> pd.DataFrame:
    """firm, date, hour -> name: 1 if the firm was a net seller in that hour `days` days before."""
    h = x.merge(per[KEY + ["hour", "day_hours"]], on=KEY)
    h = h.groupby(["firm", "date", "hour"]).agg(net=("net_mw", "mean"),
                                                day_hours=("day_hours", "first")).reset_index()
    prev = h.assign(date=h.date + pd.Timedelta(days=days))
    m = h[["firm", "date", "hour", "day_hours"]].merge(
        prev[["firm", "date", "hour", "net", "day_hours"]], on=["firm", "date", "hour"],
        how="left", suffixes=("", "_prev"))
    ok = (m.day_hours == 24) & (m.day_hours_prev == 24)
    m[name] = np.where(ok & m.net.notna(), (m.net > 0).astype(float), np.nan)
    return m[["firm", "date", "hour", name]]


def instrument(months: list[str]) -> pd.DataFrame:
    r = pd.read_parquet(RIVAL)
    r["date"] = pd.to_datetime(r.date)
    r = r[r.date.dt.strftime("%Y%m").isin(months)]
    long = [r[KEY].assign(firm=f, z=r[f"z_rival_{f}"] / 1000) for f in FIRMS]
    long.append(r[KEY].assign(firm="FRINGE", z=r.z_all / 1000))
    return pd.concat(long, ignore_index=True)


def listed_firm(units: list[str]) -> pd.DataFrame:
    """unit, snapshot, dfirm: each unit's group (one of the five, or FRINGE) in every OMIE listing.

    A co-owned unit is listed once per owner; it follows its majority owner (ALL1,
    Anllares: Naturgy 2/3, Endesa 1/3 -> Naturgy).
    """
    lst = pd.read_parquet(LISTS, columns=["snapshot", "unit", "agent_owner", "ownership_pct"])
    lst = lst[lst.unit.isin(units)].sort_values("ownership_pct", ascending=False)
    lst = lst.drop_duplicates(["snapshot", "unit"]).copy()
    lst["snapshot"] = pd.to_datetime(lst.snapshot)
    g = lst.agent_owner.map(exposed_group)
    lst["dfirm"] = g.where(g.isin(FIRMS), "FRINGE")
    return lst[["unit", "snapshot", "dfirm"]].sort_values("snapshot")


def owned_as_assigned(ud: pd.DataFrame, lists: pd.DataFrame) -> pd.DataFrame:
    """unit, date -> keep: the listing in force that day (nearest preceding snapshot) agrees
    with the static firm X is built for. Units never listed keep their firm."""
    left = ud.assign(date=ud.date.astype("datetime64[us]")).sort_values("date")
    right = lists.rename(columns={"snapshot": "date"})
    right = right.assign(date=right.date.astype("datetime64[us]"))
    a = pd.merge_asof(left, right, on="date", by="unit", direction="backward")
    keep = (a.dfirm.isna() | (a.dfirm == a.firm)) & ~((a.firm == "REPSOL") & (a.date < REPSOL_VIESGO))
    return a[["unit", "date"]].assign(keep=keep.to_numpy())


def hourly(o: pd.DataFrame, off: pd.DataFrame, u: pd.DataFrame, cap: pd.DataFrame,
           per: pd.DataFrame, x: pd.DataFrame, clean: pd.DataFrame, z: pd.DataFrame,
           lists: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """One month of unit-period outcomes -> unit-hours with X, the instrument and controls.

    Also returns the unit-days dropped because the unit offered more than
    OVER_CAP x its capacity in some period: from 2025-04 some combined cycles
    submit alternative complex orders (`C04`) whose volumes do not add, so the
    capacity share is undefined that day.
    """
    o["date"] = pd.to_datetime(o.date)
    # Every period of a unit-day the unit is present in: a period with no offer scores 0
    # (nothing offered at or below the reference price), not a missing row -- whether a
    # unit offers at all moves with the hour, so dropping those periods selects.
    grid = o[["unit", "date"]].drop_duplicates().merge(per[KEY], on="date")
    o = grid.merge(o, on=["unit", "date", "period"], how="left")
    o[OUTC] = o[OUTC].fillna(0.0)
    o = o.merge(u, on="unit").merge(cap, on=["unit", "date"], how="left")
    own = owned_as_assigned(o[["unit", "date", "firm"]].drop_duplicates(), lists)
    o = o.merge(own, on=["unit", "date"])
    moved = o[~o.keep].drop_duplicates(["unit", "date"])[["unit", "firm", "date"]]
    o = o[o.keep].drop(columns="keep")
    o["cap_mw"] = o.cap_mw.where(o.cap_mw > 0, o.reg_mw)
    o = o.merge(off, on=["unit", "date", "period"], how="left")
    bad = (o.off_mw > OVER_CAP * o.cap_mw).groupby([o.unit, o.date]).transform("any")
    dropped = o[bad].drop_duplicates(["unit", "date"])[["unit", "cls", "date"]]
    o = o[~bad].copy()
    o[OUTC] = o[OUTC].div(o.cap_mw, axis=0)
    o = o.merge(per, on=KEY).merge(clean, on=KEY)
    o = o[o.clean]
    o = o.merge(x[KEY + ["firm", "X", "Xp", "Xm"]], on=KEY + ["firm"], how="left")
    o = o[(o.firm == "FRINGE") | o.X.notna()]
    o = o.merge(z, on=KEY + ["firm"], how="left")
    agg = {c: "mean" for c in OUTC + ["X", "Xp", "Xm", "z", "fcst"]}
    agg.update(cap_mw="first", zero_price="max", period="size", cls="first")
    h = o.groupby(["unit", "firm", "date", "hour"]).agg(agg)
    return h.rename(columns={"period": "n_per"}).reset_index(), dropped, moved


def build(months: list[str] | None) -> pd.DataFrame:
    files = sorted(BIDS.glob("bids_*.parquet"))
    if months:
        files = [f for f in files if f.stem.split("_")[1] in months]
    months = [f.stem.split("_")[1] for f in files]
    u = leg_d_units()
    units = sorted(u.unit)
    print(f"{len(units)} units:\n{u.groupby(['firm', 'cls']).size().unstack(fill_value=0)}")
    one = pd.Series(1.0, index=units)
    per, x, z = period_frame(span(months)), firm_terms(span(months)), instrument(months)
    clean = x[x.firm == FIRMS[0]][KEY + ["clean", "zero_price"]]
    lists = listed_firm(units)
    parts, drops, moves = [], [], []
    for f, ym in zip(files, months):
        o = month_outcomes(f, units, one)
        if not o.empty:
            h_m, d_m, m_m = hourly(o, offered_total(f, units), u, unit_day_capacity(units, [ym]),
                                   per, x, clean, z, lists)
            parts.append(h_m)
            drops.append(d_m)
            moves.append(m_m)
        print(f"  {f.stem}", file=sys.stderr, flush=True)
    h = pd.concat(parts, ignore_index=True)
    dropped = pd.concat(drops, ignore_index=True)
    moved = pd.concat(moves, ignore_index=True)
    for days, name in ((1, "s_prev"), (7, "s_prev7")):
        h = h.merge(seller_lagged(x, per, days, name), on=["firm", "date", "hour"], how="left")
        h.loc[h.firm == "FRINGE", name] = np.nan
    h["zs"] = h.z * h.s_prev
    h["zs7"] = h.z * h.s_prev7
    iso = h.date.dt.isocalendar()
    h["wk"] = (iso.year * 100 + iso.week).astype("int64")
    f32 = OUTC + ["X", "Xp", "Xm", "z", "zs", "zs7", "fcst"]
    h[f32] = h[f32].astype("float32")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    h.to_parquet(OUT, index=False)
    report(h, dropped, moved)
    return h


def report(h: pd.DataFrame, dropped: pd.DataFrame, moved: pd.DataFrame) -> None:
    print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(h):,} unit-hours)")
    print("\nUNIT-DAYS DROPPED, owner that day is not the firm X is built for (listing / Viesgo):")
    print(moved.groupby(["firm", moved.date.dt.year]).size().unstack(fill_value=0).to_string()
          if len(moved) else "  none")
    print("\nUNIT-DAYS DROPPED, offered volume above capacity (alternative complex orders):")
    print(dropped.groupby(["cls", dropped.date.dt.year]).size().unstack(fill_value=0).to_string()
          if len(dropped) else "  none")
    sd = h.groupby(["unit", "firm", "cls", "date"]).s50.std()
    var = (sd > 0.005).groupby(["firm", "cls", sd.index.get_level_values("date").year]).mean()
    print("\nSHARE OF UNIT-DAYS WHOSE s50 MOVES WITHIN THE DAY (sd > 0.5 pp) -- only these identify")
    print(var.unstack().round(2).to_string())
    f = h[h.firm != "FRINGE"]
    both = f.groupby(["firm", "date"]).Xp.transform("max").gt(0) & f.groupby(["firm", "date"]).Xm.transform("min").lt(0)
    print("\nUNIT-HOURS by firm; share on firm-days with both signs of X:")
    print(f.assign(both=both).groupby("firm").agg(n=("s50", "size"), both=("both", "mean")).round(3).to_string())


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*", help="YYYYMM months only (for checks)")
    build(ap.parse_args().months)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
