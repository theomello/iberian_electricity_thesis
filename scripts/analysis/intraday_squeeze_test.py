#!/usr/bin/env python3
"""Step 2 of the intraday-squeeze design: the premium, rivals' offers, and the slide.

    .venv/bin/python scripts/build/build_intraday_squeeze_events.py     # input: trips and cells
    .venv/bin/python scripts/analysis/intraday_squeeze_test.py
    .venv/bin/python scripts/analysis/intraday_squeeze_test.py --gross    # on the stored cells

Design: docs/specs/2026-10-19-intraday-squeeze-design.md §3-4; step 1 in
notes/rq-intraday-squeeze.md.

CELLS (from step 1): trip x day class (pre, window, post) x intraday session x UTC hour.
Every outcome is read as its CHANGE against the trip's own pre days in the same session
and local hour, then averaged over a trip's window (or post) cells, then over trips.
Inference is by trip: the standard error of the mean across trips.

OUTCOMES
  premium   p_ID - p_DA, Spanish prices. The day-ahead price of a window hour was set
            with the reactor in, so the window premium holds two things: the scarcity
            the day-ahead price missed, and any squeeze.
  slide     the mechanical part: the owners' net take from rivals in the cell (its change
            against the pre days, MW) over the local slope of the curve they buy along,
            rivals' sell offers plus other buyers' bids within ±H of the session price,
            per €/MWh. Price-taking rivals: premium change = slide.
  squeeze   premium change minus slide.
  rivals' offers  rivals' sell MW offered at or below an absolute price, anchor + k, where
            the anchor is the trip's mean day-ahead price for that local hour on its pre
            days (fixed, so that a day-ahead price set with or without the reactor does
            not move the yardstick). A squeeze is less supply at the same price.
RIVALS: every unit, weighted by the share NOT owned by the trip's owner groups
(lib/unit_ownership.py); other buyers likewise.

WINDOW SESSIONS. A window hour is also traded in sessions that closed before the trip.
A (delivery day, session) is REACTING from the first session of that delivery day in
which the reactor buys (> 1 MW); earlier sessions of that day CLOSED before it; delivery
days with no buy are UNKNOWN. Main: reacting cells; closed cells are a placebo.
PLACEBO 2: the last pre day against the six before it.

GROSS SLIDE (--gross). The slide above counts rivals only. The owners' replacement units
bid too, at their own (higher) cost, so a price-taking market moves along everyone's
curve: gross slide = the reactor's buy-back change over the whole market's slope near
the price (every unit but the reactor). Price-taking: premium change = gross slide, and
across trips the premium change on the gross slide has slope 1 and intercept 0.

OUTPUTS: outputs/tables/intraday_squeeze_cells_offers.parquet (gitignored),
         intraday_squeeze_trip_effects.csv, intraday_squeeze_results.csv, intraday_squeeze_gross.csv
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
from unit_ownership import attach_owners, spells  # noqa: E402
from build_intraday_squeeze_events import utc_hour, TZ, MAIN_END  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
CELLS = TABLES / "intraday_squeeze_cells.parquet"
TRIPS = TABLES / "intraday_squeeze_trips.csv"
OUT_CELLS = TABLES / "intraday_squeeze_cells_offers.parquet"
OUT_TRIPS = TABLES / "intraday_squeeze_trip_effects.csv"
OUT = TABLES / "intraday_squeeze_results.csv"
OUT_GROSS = TABLES / "intraday_squeeze_gross.csv"
KS = (-10, -5, 0, 5, 10, 20)        # €/MWh above the anchor
H, H_CHECK = 5.0, 10.0              # half-width of the band for the local slope


def offers_for(cells: pd.DataFrame, trips: pd.DataFrame) -> pd.DataFrame:
    """Per cell: rivals' sell MW at <= anchor + k, and the band volumes for the slope."""
    sp = spells()
    owners = {r.trip_id: set(str(r.owners).split()) for r in trips.itertuples()}
    cells = cells.copy()
    cells["month"] = cells.utc.dt.tz_convert(TZ).dt.strftime("%Y%m")
    out = []
    for m, cm in cells.groupby("month"):
        nxt = (pd.Timestamp(m + "01") + pd.offsets.MonthBegin(1)).strftime("%Y%m")
        fs = [DATA / f"omie/intraday/parquet/intraday_{x}.parquet" for x in (m, nxt)]
        fs = [f for f in fs if os.path.exists(f)]
        b = pd.concat([pq.read_table(f, columns=["session", "date", "period", "resolution_min", "unit", "side",
                                                 "power_mw", "price_eur_mwh", "status"],
                                     filters=[("status", "=", "O")]).to_pandas() for f in fs], ignore_index=True)
        b["utc"] = utc_hour(b.date, b.period, b.resolution_min)
        b = b[b.utc.isin(set(cm.utc))].copy()
        b["unit"] = b.unit.astype(str)
        b["side"] = b.side.astype(str)
        b["w"] = b.power_mw * b.resolution_min.astype(float) / 60.0       # MW, hourly mean
        b["date"] = b.utc.dt.tz_convert(TZ).dt.tz_localize(None).dt.normalize()
        keys = b[["unit", "date"]].drop_duplicates()
        a = attach_owners(keys, sp, value_cols=())
        for tid, ct in cm.groupby("trip_id"):
            own = a[a.group.isin(owners[tid])].groupby(["unit", "date"]).share.sum().rename("own_share")
            x = b[b.utc.isin(set(ct.utc))].merge(own.reset_index(), on=["unit", "date"], how="left")
            x["rw"] = x.w * (1.0 - x.own_share.fillna(0.0).clip(upper=1.0))     # rivals' part
            x = x.merge(ct[["session", "utc", "anchor", "p_id_es"]], on=["session", "utc"], how="inner")
            s, d = x[x.side == "V"], x[x.side == "C"]
            res = ct[["trip_id", "cls", "session", "utc"]].copy().set_index(["session", "utc"])
            for k in KS:
                v = s[s.price_eur_mwh <= s.anchor + k].groupby(["session", "utc"]).rw.sum()
                res[f"sell_le_{k:+d}"] = v.reindex(res.index).fillna(0.0)
            for h, tag in ((H, ""), (H_CHECK, "_h10")):
                inb = lambda z: (z.price_eur_mwh >= z.p_id_es - h) & (z.price_eur_mwh <= z.p_id_es + h)  # noqa: E731
                res[f"band_sell{tag}"] = s[inb(s)].groupby(["session", "utc"]).rw.sum().reindex(res.index).fillna(0.0)
                res[f"band_buy{tag}"] = d[inb(d)].groupby(["session", "utc"]).rw.sum().reindex(res.index).fillna(0.0)
            res["sell_total"] = s.groupby(["session", "utc"]).rw.sum().reindex(res.index).fillna(0.0)
            out.append(res.reset_index())
        print(f"  {m}: {len(cm):,} cells, {len(b):,} offer rows", flush=True)
    return pd.concat(out, ignore_index=True)


def reacting(c: pd.DataFrame) -> pd.Series:
    """reacting / closed / unknown for window cells, from the reactor's own first buy."""
    w = c[c.cls == "window"]
    first = (w[w.rx_net_buy_mw > 1].groupby(["trip_id", "local_date"]).session.min().rename("first_s"))
    k = c[["trip_id", "local_date", "session", "cls"]].merge(first.reset_index(), on=["trip_id", "local_date"], how="left")
    lab = np.where(k.cls != "window", k.cls,
                   np.where(k.first_s.isna(), "unknown", np.where(k.session >= k.first_s, "reacting", "closed")))
    return pd.Series(lab, index=c.index)


def changes(c: pd.DataFrame, ys: list[str]) -> pd.DataFrame:
    """Each outcome minus its pre-day mean in the same trip, session and local hour."""
    base = c[c.cls == "pre"].groupby(["trip_id", "session", "local_hour"])[ys].mean().add_suffix("_pre")
    c = c.merge(base.reset_index(), on=["trip_id", "session", "local_hour"], how="left")
    for y in ys:
        c[f"d_{y}"] = c[y] - c[f"{y}_pre"]
    return c


def across(t: pd.DataFrame, label: str, cols: list[str]) -> list[dict]:
    rows = []
    for col in cols:
        v = t[col].dropna()
        rows.append({"comparison": label, "outcome": col, "mean": v.mean(), "se": v.std(ddof=1) / np.sqrt(len(v)),
                     "median": v.median(), "trips": len(v)})
    return rows


def gross_bands(cells: pd.DataFrame, trips: pd.DataFrame) -> pd.DataFrame:
    """Per cell: the whole market's offered volume within ±H (and ±H_CHECK) of the session
    price, sells and buys, every unit but the tripped reactor itself (owners' units in)."""
    rx = dict(zip(trips.trip_id, trips.unit))
    cells = cells.copy()
    cells["month"] = cells.utc.dt.tz_convert(TZ).dt.strftime("%Y%m")
    out = []
    for m, cm in cells.groupby("month"):
        nxt = (pd.Timestamp(m + "01") + pd.offsets.MonthBegin(1)).strftime("%Y%m")
        fs = [DATA / f"omie/intraday/parquet/intraday_{x}.parquet" for x in (m, nxt)]
        fs = [f for f in fs if os.path.exists(f)]
        b = pd.concat([pq.read_table(f, columns=["session", "date", "period", "resolution_min", "unit", "side",
                                                 "power_mw", "price_eur_mwh", "status"],
                                     filters=[("status", "=", "O")]).to_pandas() for f in fs], ignore_index=True)
        b["utc"] = utc_hour(b.date, b.period, b.resolution_min)
        b = b[b.utc.isin(set(cm.utc))].copy()
        b["unit"] = b.unit.astype(str)
        b["side"] = b.side.astype(str)
        b["w"] = b.power_mw * b.resolution_min.astype(float) / 60.0
        for tid, ct in cm.groupby("trip_id"):
            x = b[b.utc.isin(set(ct.utc)) & (b.unit != rx[tid])]
            x = x.merge(ct[["session", "utc", "p_id_es"]], on=["session", "utc"], how="inner")
            res = ct[["trip_id", "cls", "session", "utc"]].copy().set_index(["session", "utc"])
            for h, tag in ((H, ""), (H_CHECK, "_h10")):
                inb = (x.price_eur_mwh >= x.p_id_es - h) & (x.price_eur_mwh <= x.p_id_es + h)
                for side, name in (("V", "sell"), ("C", "buy")):
                    v = x[inb & (x.side == side)].groupby(["session", "utc"]).w.sum()
                    res[f"all_band_{name}{tag}"] = v.reindex(res.index).fillna(0.0)
            out.append(res.reset_index())
        print(f"  {m}: {len(cm):,} cells", flush=True)
    return pd.concat(out, ignore_index=True)


def gross() -> int:
    """The price-taking benchmark with the owners' replacement units in: the reactor's
    gross buy-back change over the whole market's slope near the price."""
    trips = pd.read_csv(TRIPS)
    trips = trips[~trips.dropped.astype(bool)]
    c = pd.read_parquet(OUT_CELLS)
    print(f"{len(trips)} trips, {len(c):,} cells; reading offered curves (all units)")
    g = gross_bands(c, trips)
    c = c.drop(columns=[x for x in g.columns if x.startswith("all_band")], errors="ignore")
    c = c.merge(g, on=["trip_id", "cls", "session", "utc"], how="left")
    for tag, h in (("", H), ("_h10", H_CHECK)):
        sl = (c[f"all_band_sell{tag}"] + c[f"all_band_buy{tag}"]) / (2 * h)
        c[f"slope_all{tag}"] = sl
        c[f"gslide{tag}"] = np.where(sl > 0, c.d_rx_net_buy_mw / sl.where(sl > 0), np.nan)
        c[f"gresid{tag}"] = c.d_premium - c[f"gslide{tag}"]
    c.to_parquet(OUT_CELLS, index=False)
    trips["main"] = pd.to_datetime(trips.start, utc=True).dt.tz_convert(TZ).dt.tz_localize(None) <= MAIN_END
    cols = ["d_premium", "gslide", "gresid", "gslide_h10", "gresid_h10", "d_rx_net_buy_mw", "slide", "squeeze"]
    rows = []
    from scipy.stats import wilcoxon
    for sample, ids in (("main sample", set(trips[trips.main].trip_id)), ("all trips", set(trips.trip_id))):
        cs = c[c.trip_id.isin(ids)]
        print(f"\n{sample.upper()} (mean over trips, se over trips)")
        for grp, vals in (("sess_class", ["reacting", "closed", "post"]), ("placebo", ["last pre day"])):
            t = cs.groupby(["trip_id", grp])[cols].mean().reset_index()
            for v in vals:
                gv = t[t[grp] == v]
                txt = "  ".join(f"{k} {gv[k].mean():+6.2f} ({gv[k].std(ddof=1) / np.sqrt(gv[k].notna().sum()):5.2f})"
                                for k in ("d_premium", "gslide", "gresid", "gresid_h10"))
                wp = wilcoxon(gv.gresid.dropna()).pvalue if gv.gresid.notna().sum() > 5 else np.nan
                print(f"  {v:14s} n={len(gv):2d}  {txt}  median gresid {gv.gresid.median():+.2f} (Wilcoxon p {wp:.3f})")
                for k in cols:
                    rows.append({"sample": sample, "cells": v, "outcome": k, "mean": gv[k].mean(),
                                 "se": gv[k].std(ddof=1) / np.sqrt(gv[k].notna().sum()), "median": gv[k].median(),
                                 "trips": int(gv[k].notna().sum())})
            if grp == "sess_class":
                tw = t[t.sess_class == "reacting"].dropna(subset=["d_premium", "gslide"])
                X = np.column_stack([np.ones(len(tw)), tw.gslide])
                b = np.linalg.lstsq(X, tw.d_premium, rcond=None)[0]
                e = tw.d_premium - X @ b
                V = np.linalg.inv(X.T @ X) * (e @ e) / (len(tw) - 2)
                print(f"  across {len(tw)} trips (reacting): premium change = {b[0]:+.2f} ({np.sqrt(V[0, 0]):.2f}) + "
                      f"{b[1]:+.2f} ({np.sqrt(V[1, 1]):.2f}) x gross slide;  price-taking: 0 + 1 x slide")
                rows.append({"sample": sample, "cells": "reacting", "outcome": "premium on gross slide",
                             "mean": b[1], "se": np.sqrt(V[1, 1]), "median": b[0], "trips": len(tw)})
    m = c[(c.sess_class == "reacting") & c.trip_id.isin(set(trips[trips.main].trip_id))]
    print(f"\nreacting cells, main sample: median whole-market slope {m.slope_all.median():.0f} MW per €/MWh "
          f"(rivals only: {m.slope.median():.0f}); median reactor buy-back change {m.d_rx_net_buy_mw.median():.0f} MW")
    pd.DataFrame(rows).to_csv(OUT_GROSS, index=False)
    print(f"wrote {OUT_CELLS.relative_to(ROOT)}, {OUT_GROSS.relative_to(ROOT)}")
    return 0


def main() -> int:
    trips = pd.read_csv(TRIPS)
    trips = trips[~trips.dropped.astype(bool)]
    c = pd.read_parquet(CELLS)
    c = c[c.trip_id.isin(trips.trip_id)].reset_index(drop=True)
    anchor = c[c.cls == "pre"].groupby(["trip_id", "local_hour"]).p_da_es.mean().rename("anchor")
    c = c.merge(anchor.reset_index(), on=["trip_id", "local_hour"], how="left")
    print(f"{len(trips)} trips, {len(c):,} cells; reading offered curves")
    o = offers_for(c, trips)
    c = c.merge(o, on=["trip_id", "cls", "session", "utc"], how="left")
    c["premium"] = c.p_id_es - c.p_da_es
    c["sess_class"] = reacting(c)
    pre_d = c.local_date.groupby(c.trip_id).transform(lambda x: x[c.loc[x.index, "cls"] == "pre"].max())
    c["placebo"] = np.where(c.cls != "pre", "", np.where(c.local_date == pre_d, "last pre day", "earlier pre"))
    ys = ["premium", "rx_net_buy_mw", "own_other_net_sell_mw"] + [f"sell_le_{k:+d}" for k in KS] + ["sell_total"]
    c = changes(c, ys)
    # placebo: the last pre day against the six before it (not against a mean that includes it)
    early = (c[c.placebo == "earlier pre"].groupby(["trip_id", "session", "local_hour"])[ys].mean()
             .add_suffix("_early").reset_index())
    c = c.merge(early, on=["trip_id", "session", "local_hour"], how="left")
    last = (c.placebo == "last pre day").to_numpy()
    for y in ys:
        c.loc[last, f"d_{y}"] = c.loc[last, y] - c.loc[last, f"{y}_early"]
    c["take_d"] = c.d_rx_net_buy_mw - c.d_own_other_net_sell_mw
    for tag in ("", "_h10"):
        h = H if tag == "" else H_CHECK
        slope = (c[f"band_sell{tag}"] + c[f"band_buy{tag}"]) / (2 * h)          # MW per €/MWh
        c[f"slope{tag}"] = slope
        c[f"slide{tag}"] = np.where(slope > 0, c.take_d / slope.where(slope > 0), np.nan)
        c[f"squeeze{tag}"] = c.d_premium - c[f"slide{tag}"]
    c.to_parquet(OUT_CELLS, index=False)

    trips["main"] = pd.to_datetime(trips.start, utc=True).dt.tz_convert(TZ).dt.tz_localize(None) <= MAIN_END
    main_ids = set(trips[trips.main].trip_id)
    ycols = ["d_premium", "slide", "squeeze", "slide_h10", "squeeze_h10", "take_d"] + \
            [f"d_sell_le_{k:+d}" for k in KS] + ["d_sell_total"]
    rows = []
    t_all = []
    for sample, ids in (("main sample", main_ids), ("all trips", set(trips.trip_id))):
        cs = c[c.trip_id.isin(ids)]
        for grp, lab in (("sess_class", "window sessions"), ("cls", "day class"), ("placebo", "placebo")):
            g = cs.groupby(["trip_id", grp])[ycols].mean().reset_index()
            for val, gv in g.groupby(grp):
                if val in ("", "pre", "earlier pre"):
                    continue
                rows += [r | {"sample": sample, "cells": f"{lab}: {val}"} for r in across(gv, f"{lab}: {val}", ycols)]
            if sample == "main sample" and grp == "sess_class":
                t_all.append(g)
    res = pd.DataFrame(rows)
    res.to_csv(OUT, index=False)
    te = t_all[0].merge(trips[["trip_id", "owners", "regime", "da_sched_mw", "take_change_mw", "post_days"]], on="trip_id")
    te.to_csv(OUT_TRIPS, index=False)

    pd.set_option("display.width", 220)
    show = ["d_premium", "slide", "squeeze", "take_d", "d_sell_le_+0", "d_sell_le_+10", "d_sell_total"]
    for sample in ("main sample", "all trips"):
        r = res[(res["sample"] == sample) & res.outcome.isin(show)]
        tab = r.pivot_table(index="cells", columns="outcome", values="mean")[show]
        se = r.pivot_table(index="cells", columns="outcome", values="se")[show]
        n = r.groupby("cells").trips.max()
        print(f"\n{sample.upper()}: mean over trips of the change against pre days (se over trips); trips")
        for cell in tab.index:
            print(f"  {cell:34s} n={n[cell]:2d}  " + "  ".join(
                f"{o} {tab.loc[cell, o]:+8.2f} ({se.loc[cell, o]:6.2f})" for o in show))
    print("\nunits: premium, slide, squeeze in €/MWh; take_d and rivals' offered MW (sell_le_k: at or below the "
          "pre-day anchor + k) in MW; slope band ±5 €/MWh (±10 in the csv)")
    w = c[(c.sess_class == "reacting") & c.trip_id.isin(main_ids)]
    print(f"\nreacting window cells, main sample: {len(w):,}; median local slope {w.slope.median():.0f} MW per €/MWh "
          f"(±5 band), median take {w.take_d.median():.0f} MW")
    # dose: across trips, the window premium change on the owners' take
    tw = te[te.sess_class == "reacting"].dropna(subset=["d_premium", "take_d"])
    if len(tw) > 5:
        X = np.column_stack([np.ones(len(tw)), tw.take_d / 100.0])
        b = np.linalg.lstsq(X, tw.d_premium, rcond=None)[0]
        e = tw.d_premium - X @ b
        V = np.linalg.inv(X.T @ X) * (e @ e) / (len(tw) - 2)
        print(f"across {len(tw)} trips: premium change = {b[0]:+.2f} + {b[1]:+.2f} per 100 MW of take "
              f"(se {np.sqrt(V[1, 1]):.2f})")
    print(f"\nwrote {OUT_CELLS.relative_to(ROOT)}, {OUT_TRIPS.relative_to(ROOT)}, {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    if "--gross" in sys.argv:
        raise SystemExit(gross())
    raise SystemExit(main())
