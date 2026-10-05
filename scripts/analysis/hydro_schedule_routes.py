#!/usr/bin/env python3
"""Through which market does storage hydro actually sell its energy?

    .venv/bin/python scripts/analysis/hydro_schedule_routes.py

Threat 9 of `notes/rq-midday-hydro.md`: a unit that prices itself out of the
day-ahead auction in an hour may still run in that hour through another route.
The midday-hydro design reads the water-allocation decision off auction offers,
which is only valid if the auction is where the energy is allocated.

THREE ROUTES, ALL PUBLISHED PER UNIT PER PERIOD

* bilateral -- PDBF `role_code == "4"`, the physical bilateral contract
  schedule. Nominated outside the auction, so a unit can run at full output in
  an hour where its auction offer is priced out.
* auction   -- day-ahead cleared sell volume, from the bid files (`status C`,
  `side V`). Cross-checked against PDBF `role_code == "1"`.
* intraday  -- net cleared volume summed over the intraday sessions, sell minus
  buy. Negative when a unit buys back part of its schedule.

Their sum is the unit's scheduled position after the intraday market. What is
NOT visible is balancing reserve and redispatch after that (ESIOS, token
required), so this is the schedule, not metered output.

Each row carries the unit's owner group in force on its date
(`hydro_within_day_probe.dated_group`, 2026-10-05).

ENERGY, NOT MW

Every file here switched to 15-minute periods on its own date (PDBF and intraday
2025-03-19, day-ahead 2025-10-01), so each is converted to MWh with
`resolution_min / 60` and summed to the local hour before anything is combined.
PDBF has several rows per unit-period (one per role code), so it is summed per
role and never joined raw -- see CLAUDE.md on the spurious "36% -> 5%" collapse.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hydro_within_day_probe import BIDS, dated_group, storage_hydro  # noqa: E402

DATA = ROOT / "data"
PDBF = DATA / "omie/pdbf/parquet"
INTRADAY = DATA / "omie/intraday/parquet"
OUT = ROOT / "outputs/tables/hydro_schedule_routes.parquet"

BREAK = pd.Timestamp("2024-06-29")   # Iberdrola's flat-bidding break, hydro_flat_break.py
PRICE_OUT = 300.0   # EUR/MWh; Iberdrola's price-out blocks sit at 384-498 (hydro_flat_break.py)
HOUR_BINS = {"night 1-7": range(1, 8), "morning 8-10": range(8, 11),
             "midday 11-17": range(11, 18), "evening 18-23": range(18, 24),
             "late 24": range(24, 26)}


def to_hour(period: pd.Series, res: pd.Series) -> pd.Series:
    return ((period - 1) * res // 60 + 1).astype(int)


def month_routes(ym: str, units: list[str]) -> pd.DataFrame:
    keys = ["unit", "date", "hour"]
    parts = []

    f = PDBF / f"pdbf_{ym}.parquet"
    if f.exists():
        p = pq.read_table(f, columns=["date", "period", "resolution_min", "unit",
                                      "schedule_mw", "role_code"],
                          filters=[("unit", "in", units)]).to_pandas()
        p["hour"] = to_hour(p.period, p.resolution_min)
        p["mwh"] = p.schedule_mw * p.resolution_min / 60
        piv = (p[p.role_code.isin(["1", "4"])]
               .pivot_table(index=keys, columns="role_code", values="mwh", aggfunc="sum")
               .rename(columns={"1": "pdbf_auction", "4": "bilateral"}))
        parts.append(piv)

    b = pq.read_table(BIDS / f"bids_{ym}.parquet",
                      columns=["date", "hour", "resolution_min", "unit", "side", "status", "power_mw"],
                      filters=[("unit", "in", units), ("status", "==", "C"), ("side", "==", "V")]
                      ).to_pandas()
    b["mwh"] = b.power_mw * b.resolution_min / 60
    parts.append(b.groupby(keys).mwh.sum().rename("auction").to_frame())

    f = INTRADAY / f"intraday_{ym}.parquet"
    if f.exists():
        i = pq.read_table(f, columns=["date", "hour", "resolution_min", "unit", "side",
                                      "status", "power_mw"],
                          filters=[("unit", "in", units), ("status", "==", "C")]).to_pandas()
        sign = i.side.astype(str).map({"V": 1.0, "C": -1.0}).astype(float)
        i["mwh"] = i.power_mw * i.resolution_min / 60 * sign
        parts.append(i.groupby(keys).mwh.sum().rename("intraday").to_frame())

    d = pd.concat(parts, axis=1).fillna(0.0).reset_index()
    d["date"] = pd.to_datetime(d["date"])
    return d


def main() -> int:
    cap = storage_hydro()
    units = list(cap.unit)
    months = sorted(f.stem.split("_")[1] for f in BIDS.glob("bids_*.parquet"))
    d = pd.concat([month_routes(m, units) for m in months], ignore_index=True)
    for c in ("bilateral", "auction", "intraday", "pdbf_auction"):
        if c not in d:
            d[c] = 0.0
    # A month-end hour can come from two month files (an intraday row carries its own
    # delivery date, which may fall in the previous month), so sum each unit-hour once.
    # Until 2026-10-05 1,046 unit-hours appeared twice, auction and intraday split.
    d = d.groupby(["unit", "date", "hour"], as_index=False)[
        ["pdbf_auction", "bilateral", "auction", "intraday"]].sum()
    d = d.merge(cap[["unit", "group"]], on="unit")
    d["group"] = dated_group(d)          # the owner group in force on the row's date
    d["total"] = d.bilateral + d.auction + d.intraday
    d["year"] = d.date.dt.year
    d["bin"] = d.hour.map({h: k for k, r in HOUR_BINS.items() for h in r})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)

    # Cross-check: PDBF's own auction row against the bid files' cleared volume.
    both = d[d.date < "2026-06-01"]
    gap = (both.pdbf_auction.sum() - both.auction.sum()) / both.auction.sum()
    print(f"PDBF role 1 vs bid-file cleared sell, storage hydro, to 2026-05: {gap:+.2%}\n")

    def shares(g: pd.DataFrame) -> pd.Series:
        pos = g[["bilateral", "auction", "intraday"]].sum()
        return (pos / g.total.sum()).round(2)

    print("ROUTE SHARES of scheduled energy, by group and year "
          "(bilateral / auction / intraday net)")
    t = d.groupby(["group", "year"]).apply(shares, include_groups=False)
    t["TWh"] = (d.groupby(["group", "year"]).total.sum() / 1e6).round(2)
    for grp, g in t.groupby(level=0):
        print(f"{grp}")
        print(g.droplevel(0).T.to_string(), "\n")

    ib = d[d.group == "IBERDROLA"]
    print("IBERDROLA, monthly bilateral share of scheduled energy, around the break")
    m = ib.assign(month=ib.date.dt.to_period("M"))
    win = m[(m.date >= BREAK - pd.DateOffset(months=9)) & (m.date < BREAK + pd.DateOffset(months=9))]
    tab = (win.groupby(["month", "unit"]).bilateral.sum()
           / win.groupby(["month", "unit"]).total.sum()).unstack()
    tab["all"] = win.groupby("month").bilateral.sum() / win.groupby("month").total.sum()
    tab["GWh"] = win.groupby("month").total.sum() / 1e3
    print(tab.round(2).to_string(), "\n")

    print("IBERDROLA, mean MWh per unit-hour by route and time of day, a year either side")
    yr = pd.DateOffset(years=1)
    for label, s in (("before", ib[(ib.date >= BREAK - yr) & (ib.date < BREAK)]),
                     ("after", ib[(ib.date >= BREAK) & (ib.date < BREAK + yr)])):
        prof = s.groupby("bin")[["bilateral", "auction", "intraday", "total"]].mean()
        print(f"  {label}")
        print(prof.reindex(list(HOUR_BINS)).round(0).to_string(), "\n")

    print("ALL GROUPS, share of each time-of-day bin's scheduled energy that is bilateral, "
          "2018-2023 vs 2024-2026")
    d["late"] = d.year >= 2024
    t = (d.groupby(["group", "late", "bin"]).bilateral.sum()
         / d.groupby(["group", "late", "bin"]).total.sum()).unstack("bin")[list(HOUR_BINS)]
    print(t.round(2).to_string())

    # The direct threat-9 test: within a unit-day, is the bilateral schedule
    # higher in the hours where the auction offer is priced out? If so, a
    # price-out marks capacity already running on contract, not withholding.
    probe = ROOT / "outputs/tables/hydro_within_day_probe_full.parquet"
    if probe.exists():
        p = pd.read_parquet(probe, columns=["unit", "date", "hh", "p50", "price_es"])
        p = (p.rename(columns={"hh": "hour"})
             .groupby(["unit", "date", "hour"]).agg(p50=("p50", "max"), p=("price_es", "max"))
             .reset_index())
        x = d.merge(p, on=["unit", "date", "hour"], how="inner")
        x = x[x.p50.notna()]
        x["priced_out"] = (x.p50 >= PRICE_OUT) & (x.p50 > x.p + 100)
        # keep unit-days with both kinds of hour, so the comparison is within day
        mix = x.groupby(["unit", "date"]).priced_out.transform("nunique") == 2
        x = x[mix]
        for c in ("bilateral", "auction", "intraday", "total"):
            x[c + "_w"] = x[c] - x.groupby(["unit", "date"])[c].transform("mean")
        print(f"\nTHREAT 9: p50 priced out (>= {PRICE_OUT:.0f} EUR/MWh and > p* + 100) "
              "vs not, within unit-days that have both.\nMean deviation from the unit-day "
              "mean, MWh per unit-hour")
        cols = ["bilateral_w", "auction_w", "intraday_w", "total_w"]
        for grp in ("IBERDROLA", "ENDESA", "EDP", "NATURGY"):
            g = x[x.group == grp]
            if g.empty:
                continue
            t = g.groupby("priced_out")[cols].mean().round(0)
            t["unit_hours"] = g.groupby("priced_out").size()
            t["unit_days"] = g.groupby("priced_out")[["unit", "date"]].apply(
                lambda y: len(y.drop_duplicates()))
            print(f"  {grp}")
            print(t.to_string(), "\n")

    print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(d):,} unit-hours)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
