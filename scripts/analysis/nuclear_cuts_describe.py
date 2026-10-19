#!/usr/bin/env python3
"""T1 of the nuclear-cuts design: describe when, how and at what prices reactors cut.

    .venv/bin/python scripts/analysis/nuclear_cuts_describe.py

Design: docs/specs/2026-10-19-nuclear-cuts-design.md §4 T1. No estimation.

CUT. A reactor-hour's cut = lost output no declaration covers (`lost_undecl_mw` in
reactor_outage_hours.parquet) plus output declared as flexible operation (class
`economic`). Hours of a reactor-day carrying any other declared loss (refuelling,
faults, weather, ramps, ...) are left out: the reactor was not free to choose. A day
is a *whole stop* if the reactor is scheduled at 0 all day, else a *partial* cut.
Whole stops on days `indisp` has no snapshot for may be outages the register missed.

LEGS. PDBF role 4 is the bilateral contract with the co-owners' retailers; the other
role codes are the auction and self-scheduling.

FORM. From the offers (`curva_pbc_uof`, status O, sell side): MW offered at ≤ 0,
at a reservation price (0 < p < PROHIBITIVE), and at a prohibitive price (≥ PROHIBITIVE,
a cut-off checked against the distribution printed below).

PRICES. Expected price for day D = the OMIP Spanish base-load price for D from the
finest contract, on the latest trade date ≤ D − 2 (before offers close at noon on
D − 1; `build_water_value_forward.forward_days`). Realised price for comparison only.

COST, PROVISIONAL (every rate is *to verify*; design §3):
  c_lo   = (Enresa fee + spent-fuel tax + regional tax) / (1 − IVPEE): fuel worth 0
  c_acct = c_lo + FUEL_ACCT / (1 − IVPEE): fuel at a rough accounting cost
  c_hi   = max(c_acct, expected price in the 30 days before the next refuelling):
           fuel saved now runs at the end of the cycle
OUTPUTS: outputs/tables/nuclear_cuts_daily.parquet, nuclear_cuts_summary.csv
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
from omie_common import day_periods_utc  # noqa: E402
from build_water_value_forward import forward_days  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
OUT_DAILY = TABLES / "nuclear_cuts_daily.parquet"
OUT_SUMMARY = TABLES / "nuclear_cuts_summary.csv"
REACTORS = ["ALZ1", "ALZ2", "ASC1", "ASC2", "COF1", "TRL1", "VAN2"]
OPERATOR = {"ALZ1": "CNAT", "ALZ2": "CNAT", "TRL1": "CNAT", "ASC1": "ANAV", "ASC2": "ANAV",
            "VAN2": "ANAV", "COF1": "Iberdrola"}
PROHIBITIVE = 200.0
FREE = {"economic"}                       # declared classes that are chosen cuts

# Provisional cost inputs, EUR/MWh, all to verify against the official texts.
ENRESA = [("1900-01-01", 6.69), ("2020-01-01", 7.98), ("2024-07-01", 10.36)]   # RD 750/2019, RD 589/2024
SPENT_FUEL = 5.4          # Ley 15/2012, 2,190 EUR/kg HM; ~297 MEUR a year over ~55 TWh
REGIONAL = {"ALZ1": 5.0, "ALZ2": 5.0, "ASC1": 6.0, "ASC2": 6.0, "VAN2": 6.0, "COF1": 1.8, "TRL1": 0.0}
FUEL_ACCT = 6.0
IVPEE = [("1900-01-01", 0.07), ("2018-10-07", 0.0), ("2019-04-01", 0.07), ("2021-07-01", 0.0),
         ("2024-01-01", 0.035), ("2024-04-01", 0.0525), ("2024-07-01", 0.07)]


def step_rate(table, days: pd.Series) -> np.ndarray:
    t = pd.DataFrame(table, columns=["d", "v"]).assign(d=lambda x: pd.to_datetime(x.d))
    q = pd.DataFrame({"d": pd.to_datetime(days).astype("datetime64[ns]")}).reset_index()
    r = pd.merge_asof(q.sort_values("d"), t.astype({"d": "datetime64[ns]"}), on="d").sort_values("index")
    return r.v.to_numpy()


def local_date(utc: pd.Series) -> pd.Series:
    return utc.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize()


def period_utc(dates) -> pd.DataFrame:
    """date, period, utc hour for the day-ahead market's periods (prices file)."""
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet", columns=["date", "period", "utc_timestamp"])
    px["date"] = pd.to_datetime(px.date)
    px["utc"] = pd.to_datetime(px.utc_timestamp, utc=True).dt.floor("h")
    return px[px.date.isin(dates)][["date", "period", "utc"]]


def legs() -> pd.DataFrame:
    """unit, utc, bilat_mw, auction_mw from PDBF (mean MW over the UTC hour)."""
    frames = []
    for f in sorted(glob.glob(str(DATA / "omie/pdbf/parquet/pdbf_*.parquet"))):
        p = pq.read_table(f, columns=["date", "period", "unit", "schedule_mw", "role_code"],
                          filters=[("unit", "in", REACTORS)]).to_pandas()
        if p.empty:
            continue
        p["leg"] = np.where(p.role_code.astype(str) == "4", "bilat_mw", "auction_mw")
        p = p.groupby(["date", "unit", "period", "leg"]).schedule_mw.sum().unstack(fill_value=0.0).reset_index()
        nper = pq.read_table(f, columns=["date", "period"]).to_pandas().groupby("date").period.max()
        u = pd.concat([pd.DataFrame({"date": d, "period": range(1, int(n) + 1),
                                     "utc": day_periods_utc(pd.Timestamp(d).date(), int(n))}) for d, n in nper.items()])
        u["utc"] = pd.to_datetime(u.utc, utc=True).dt.floor("h")
        npr = u.groupby("utc").size().rename("np")
        p = p.merge(u, on=["date", "period"])
        for c in ("bilat_mw", "auction_mw"):
            if c not in p:
                p[c] = 0.0
        s = p.groupby(["unit", "utc"])[["bilat_mw", "auction_mw"]].sum().reset_index().merge(npr, on="utc")
        s[["bilat_mw", "auction_mw"]] = s[["bilat_mw", "auction_mw"]].div(s.np, axis=0)
        frames.append(s.drop(columns=["np"]))
    return pd.concat(frames)


def offers() -> pd.DataFrame:
    """unit, utc, MW offered (status O, sell) at <= 0, reservation, prohibitive; the
    MW-weighted reservation price; MW accepted. Mean MW over the UTC hour."""
    frames = []
    for f in sorted(glob.glob(str(DATA / "omie/bids/parquet/bids_*.parquet"))):
        b = pq.read_table(f, columns=["date", "period", "unit", "side", "power_mw", "price_eur_mwh", "status"],
                          filters=[("unit", "in", REACTORS)]).to_pandas()
        if b.empty:
            continue
        b = b[b.side.astype(str) == "V"]
        b["date"] = pd.to_datetime(b.date)
        o = b[b.status.astype(str) == "O"].copy()
        o["band"] = np.where(o.price_eur_mwh <= 0, "zero_mw",
                             np.where(o.price_eur_mwh < PROHIBITIVE, "resv_mw", "prohib_mw"))
        o["pq"] = o.price_eur_mwh * o.power_mw * (o.band == "resv_mw")
        g = o.pivot_table(index=["date", "period", "unit"], columns="band", values="power_mw",
                          aggfunc="sum", fill_value=0.0)
        g["resv_pq"] = o.groupby(["date", "period", "unit"]).pq.sum()
        g["accepted_mw"] = b[b.status.astype(str) == "C"].groupby(["date", "period", "unit"]).power_mw.sum()
        g = g.fillna(0.0).reset_index()
        g = g.merge(period_utc(g.date.unique()), on=["date", "period"])
        cols = [c for c in ("zero_mw", "resv_mw", "prohib_mw", "resv_pq", "accepted_mw") if c in g]
        frames.append(g.groupby(["unit", "utc"])[cols].mean().reset_index())
    out = pd.concat(frames).fillna(0.0)
    return out


def expected_prices(days: pd.DatetimeIndex, refuel: pd.DataFrame) -> pd.DataFrame:
    """date, unit, p_exp (OMIP price for the day, trade date <= D-2) and p_late (mean
    expected price over the 30 days before the reactor's next refuelling)."""
    fw = forward_days("ES", 620)
    fw["trade_date"] = pd.to_datetime(fw.trade_date)
    # p_exp: latest trade date <= D - 2
    q = pd.DataFrame({"date": days.astype("datetime64[ns]")})
    q["cut"] = q.date - pd.Timedelta(days=2)
    f1 = fw.rename(columns={"day": "date"}).astype({"date": "datetime64[ns]"}).sort_values("trade_date")
    pe = pd.merge_asof(q.sort_values("cut"), f1.rename(columns={"trade_date": "cut"}).astype({"cut": "datetime64[ns]"}),
                       on="cut", by="date", direction="backward", tolerance=pd.Timedelta(days=10))
    pe = pe[["date", "fwd"]].rename(columns={"fwd": "p_exp"})
    # trade date used for each day, then the forward over the end-of-cycle window
    tds = np.sort(fw.trade_date.unique())
    idx = np.searchsorted(tds, (days - pd.Timedelta(days=2)).to_numpy(), side="right") - 1
    td = pd.Series(np.where(idx >= 0, tds[np.clip(idx, 0, None)], np.datetime64("NaT")), index=days)
    fwi = fw.set_index(["trade_date", "day"]).fwd.sort_index()
    rows = []
    for u, g in refuel.groupby("unit"):
        starts = np.sort(g.start.to_numpy())
        gap = np.median(np.diff(starts)) if len(starts) > 1 else np.timedelta64(540, "D")
        for d in days:
            nxt = starts[starts > np.datetime64(d)]
            nx = pd.Timestamp(nxt[0]) if len(nxt) else pd.Timestamp(starts[-1] + gap)
            while nx <= d:
                nx = nx + pd.Timedelta(gap)
            t = td.get(d)
            if pd.isna(t):
                rows.append((d, u, np.nan, nx))
                continue
            try:
                v = fwi.loc[t].loc[nx - pd.Timedelta(days=30): nx - pd.Timedelta(days=1)]
            except KeyError:
                v = pd.Series(dtype=float)
            rows.append((d, u, v.mean() if len(v) else np.nan, nx))
    pl = pd.DataFrame(rows, columns=["date", "unit", "p_late", "next_refuel"])
    return pl.merge(pe, on="date", how="left")


def main() -> int:
    h = pd.read_parquet(TABLES / "reactor_outage_hours.parquet")
    h["date"] = local_date(h.utc)
    other_decl = (h.lost_decl_mw > 0) & ~h.cls.isin(FREE)
    h["econ_mw"] = np.where(h.cls.isin(FREE), h.lost_decl_mw, 0.0)
    h["cut_mw"] = h.lost_undecl_mw.fillna(0) + h.econ_mw
    h["gap"] = h.undecl_cause.eq("undeclared_gap")
    blocked = h.assign(o=other_decl).groupby(["unit", "date"]).o.transform("any")
    print("reactor-hours:", len(h), "; on days with another declared loss (left out):", int(blocked.sum()))
    h = h[~blocked].copy()

    lg = legs()
    of = offers()
    h = h.merge(lg, on=["unit", "utc"], how="left").merge(of, on=["unit", "utc"], how="left")
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet", columns=["utc_timestamp", "price_es"])
    px["utc"] = pd.to_datetime(px.utc_timestamp, utc=True).dt.floor("h")
    h = h.merge(px.groupby("utc").price_es.mean().rename("p_real").reset_index(), on="utc", how="left")

    # reactor-day
    agg = dict(cap_mw=("cap_mw", "mean"), sched_mw=("sched_mw", "mean"), sched_min=("sched_mw", "min"),
               sched_max=("sched_mw", "max"), cut_mw=("cut_mw", "mean"), econ_mw=("econ_mw", "mean"),
               gap=("gap", "max"), bilat_mw=("bilat_mw", "mean"), auction_mw=("auction_mw", "mean"),
               zero_mw=("zero_mw", "mean"), resv_mw=("resv_mw", "mean"), prohib_mw=("prohib_mw", "mean"),
               resv_pq=("resv_pq", "sum"), resv_sum=("resv_mw", "sum"), accepted_mw=("accepted_mw", "mean"),
               p_real=("p_real", "mean"), hours=("utc", "size"))
    d = h.groupby(["unit", "date"]).agg(**agg).reset_index()
    d["resv_price"] = d.resv_pq / d.resv_sum.where(d.resv_sum > 0)
    d["form"] = np.where(d.cut_mw <= 0, "none", np.where(d.sched_max <= 0, "whole_stop", "partial"))
    d["year"] = d.date.dt.year
    d["operator"] = d.unit.map(OPERATOR)

    # forecasts: (wind + solar) / demand, D-1, peninsular, daily totals (from 2019)
    fc = {}
    for i, n in ((1775, "dem"), (1777, "wind"), (1779, "pv")):
        e = pd.read_parquet(DATA / f"esios/esios_{i}.parquet", columns=["datetime", "value"])
        e["date"] = pd.to_datetime(e.datetime.astype(str).str[:10])
        fc[n] = e.groupby("date").value.sum()
    fc = pd.DataFrame(fc)
    fc["vre_share_fc"] = (fc.wind + fc.pv) / fc.dem
    fc["pv_share_fc"] = fc.pv / fc.dem
    d = d.merge(fc[["vre_share_fc", "pv_share_fc"]].reset_index(), on="date", how="left")

    # expected prices and provisional cost
    sp = pd.read_csv(TABLES / "reactor_outage_spells.csv", parse_dates=["start", "end"])
    refuel = sp[(sp.cls == "planned") & (sp.cause == "refuelling")][["unit", "start"]].copy()
    refuel["start"] = refuel.start.dt.tz_localize(None) if refuel.start.dt.tz is not None else refuel.start
    days = pd.DatetimeIndex(sorted(d.date.unique()))
    ep = expected_prices(days, refuel)
    d = d.merge(ep, on=["date", "unit"], how="left")
    t = step_rate(IVPEE, d.date)
    d["c_lo"] = (step_rate(ENRESA, d.date) + SPENT_FUEL + d.unit.map(REGIONAL)) / (1 - t)
    d["c_acct"] = d.c_lo + FUEL_ACCT / (1 - t)
    d["c_hi"] = np.fmax(d.c_acct, d.p_late)
    TABLES.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT_DAILY, index=False)

    rows = []

    def show(title, df):
        print(f"\n{title}\n{df.to_string()}")
        rows.append(df.assign(table=title).reset_index())

    twh = lambda x: x.sum() * 24 / 1e6  # noqa: E731  (mean MW per day -> TWh)
    show("CUT, TWh by year and form (partial = scheduled above 0 somewhere in the day)",
         d.pivot_table(index="year", columns="form", values="cut_mw", aggfunc=twh).drop(columns="none", errors="ignore").round(2))
    show("whole stops on days the register has no snapshot for, TWh",
         d[(d.form == "whole_stop")].pivot_table(index="year", columns="gap", values="cut_mw", aggfunc=twh).round(2))
    show("declared flexible operation inside the cut, TWh", d.groupby("year").econ_mw.apply(twh).round(2).to_frame())
    show("PARTIAL cut as a share of capacity, by reactor and year",
         d.pivot_table(index="year", columns="unit", values="cut_mw", aggfunc="sum").div(
             d.pivot_table(index="year", columns="unit", values="cap_mw", aggfunc="sum")).round(3))
    p = d[d.form.isin(["partial", "none"]) & d.year.ge(2024)]
    show("2024-2026, partial cuts: share of capacity cut, by month of year",
         (p.groupby(p.date.dt.month).cut_mw.sum() / p.groupby(p.date.dt.month).cap_mw.sum()).round(3).to_frame("cut_share"))
    show("2024-2026, partial cuts: share of capacity cut, by day of week (0 = Monday)",
         (p.groupby(p.date.dt.dayofweek).cut_mw.sum() / p.groupby(p.date.dt.dayofweek).cap_mw.sum()).round(3).to_frame("cut_share"))

    # legs and form on cut days vs full days
    q = d[d.form.isin(["partial", "none"])].copy()
    q["state"] = np.where(q.form == "partial", "cut day", "full day")
    show("legs, mean MW per reactor (2024-2026): bilateral and auction, cut days vs full days",
         q[q.year >= 2024].groupby(["unit", "state"])[["cap_mw", "sched_mw", "bilat_mw", "auction_mw"]].mean().round(0))
    show("form of the partial cut (2024-2026), mean MW offered: at <= 0, reservation, prohibitive; accepted",
         q[q.year >= 2024].groupby(["unit", "state"])[["zero_mw", "resv_mw", "prohib_mw", "accepted_mw", "cut_mw"]].mean().round(0))
    print("\ncheck the prohibitive cut-off: MW offered above 0 by price band, 2018-2026 (all reactor-hours)")
    b = []
    for f in sorted(glob.glob(str(DATA / "omie/bids/parquet/bids_202[3-6]*.parquet"))):
        x = pq.read_table(f, columns=["unit", "side", "power_mw", "price_eur_mwh", "status"],
                          filters=[("unit", "in", REACTORS)]).to_pandas()
        b.append(x[(x.side.astype(str) == "V") & (x.status.astype(str) == "O") & (x.price_eur_mwh > 0)])
    b = pd.concat(b)
    cuts = pd.cut(b.price_eur_mwh, [0, 20, 40, 60, 100, 150, 200, 250, 300, 500, 5000])
    print((b.groupby(cuts, observed=False).power_mw.sum() / b.power_mw.sum()).round(3).to_string())
    show("reservation price (MW-weighted) on days offering one, by reactor and year: median",
         d[d.resv_price.notna()].pivot_table(index="year", columns="unit", values="resv_price", aggfunc="median").round(1))
    show("days offering a reservation price, by reactor and year",
         d[d.resv_price.notna()].pivot_table(index="year", columns="unit", values="resv_price", aggfunc="size").fillna(0).astype(int))

    # against the D-1 renewable forecast
    q2 = q[q.vre_share_fc.notna()].copy()
    q2["era"] = np.where(q2.year >= 2024, "2024-2026", "2019-2023")
    q2["vre_bin"] = pd.qcut(q2.vre_share_fc, 10, labels=False) + 1
    show("partial cut share of capacity by decile of D-1 (wind + solar) / demand forecast",
         (q2.groupby(["vre_bin", "era"]).cut_mw.sum() / q2.groupby(["vre_bin", "era"]).cap_mw.sum()).unstack().round(3))

    # against the expected price
    bins = [-1e9, 10, 20, 30, 40, 50, 70, 1e9]
    lab = ["<10", "10-20", "20-30", "30-40", "40-50", "50-70", ">=70"]
    for col, name in (("p_exp", "expected (OMIP, D-2)"), ("p_real", "realised day-ahead")):
        r = q.dropna(subset=[col]).copy()
        r["era"] = np.where(r.year >= 2024, "2024-2026", "2018-2023")
        r["bin"] = pd.cut(r[col], bins, labels=lab)
        show(f"partial cut share of capacity by {name} daily price, EUR/MWh",
             (r.groupby(["bin", "era"], observed=False).cut_mw.sum() /
              r.groupby(["bin", "era"], observed=False).cap_mw.sum()).unstack().round(3))
        show(f"partial cut volume, TWh, by {name} daily price",
             r.groupby(["bin", "era"], observed=False).cut_mw.apply(twh).unstack().round(2))

    r = q[(q.form == "partial") & q.p_exp.notna()].copy()
    r["vs_cost"] = np.select([r.p_exp < r.c_lo, r.p_exp < r.c_acct, r.p_exp < r.c_hi],
                             ["below c_lo", "c_lo to c_acct", "c_acct to c_hi"], "above c_hi")
    show("partial cut volume (TWh) by expected price against the PROVISIONAL cost bounds",
         r.pivot_table(index="year", columns="vs_cost", values="cut_mw", aggfunc=twh).fillna(0).round(2))
    show("provisional cost bounds, EUR/MWh, mean by year", d.groupby("year")[["c_lo", "c_acct", "p_late", "c_hi", "p_exp", "p_real"]].mean().round(1))

    pd.concat(rows, ignore_index=True).to_csv(OUT_SUMMARY, index=False)
    print(f"\nwrote {OUT_DAILY.relative_to(ROOT)}, {OUT_SUMMARY.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
