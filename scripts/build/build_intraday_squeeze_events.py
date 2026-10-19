#!/usr/bin/env python3
"""Step 1 of the intraday-squeeze design: reactor trips, their windows, and who buys what.

    .venv/bin/python scripts/build/build_intraday_squeeze_events.py
    .venv/bin/python scripts/build/build_intraday_squeeze_events.py --summarise   # from the stored files

Design: docs/specs/2026-10-19-intraday-squeeze-design.md §2, §7 step 1. Descriptive only:
no premium, no offers, no estimate.

TRIPS. Unplanned `indisp` declarations of the seven reactors (classified by
build_reactor_outages.py) that take a reactor below MAX_AVAIL MW. A breakdown declared
several times (same reactor, starts within GROUP_DAYS) is one trip, starting at its
earliest declared start.

KNOWN = the earlier of the declared start and the declaration time: from then on the
owner knows it is short. THE WINDOW = delivery hours from the start to the end of the
last delivery day whose day-ahead schedule was fixed before KNOWN (day-ahead offers
close at 12:00 on D-1), so the reactor is still in the day-ahead schedule there. Kept:
trips whose reactor is scheduled at least MIN_SCHED MW on average in the window.

CONTROL DAYS. PRE: the PRE_DAYS calendar days before the trip's local day. POST: full
days after the window on which the reactor is still out (at least 90% of hours more than
half lost in reactor_outage_hours), up to POST_DAYS, consecutive. Same scarcity as the
window, nobody forced to buy it back.

CELLS, per trip x day class x session x delivery hour (UTC), from the cleared intraday
rows (`curva_pibc_uof`, status C; mean MW over the hour's periods):
  rx_net_buy_mw          the tripped reactor's unit: cleared buys minus sells
  own_other_net_sell_mw  the owner groups' other units: cleared sells minus buys, each
                         unit weighted by the owner groups' combined share of it
  b_mw                   rx_net_buy_mw - own_other_net_sell_mw: what the owners take
                         from rivals
  mkt_sell_mw            all cleared sells in the session-hour
  da_sched_mw            the reactor's PDBF schedule that hour (the day-ahead position)
  p_id_es, p_id_pt       the session's price (marginalpibc price_b, price_a), hourly mean
  p_da_es                the day-ahead Spanish price, hourly mean
REGIME: `mibel6` to 2024-06-13 (six MIBEL sessions), `ida` from 2024-06-14 (three IDA
auctions). The 28 April 2025 blackout's trip is kept in the files and flagged `dropped`.

OUTPUTS: outputs/tables/intraday_squeeze_trips.csv (one row per trip),
         outputs/tables/intraday_squeeze_cells.parquet (gitignored)
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
from omie_common import day_periods_utc  # noqa: E402
from unit_ownership import attach_owners, spells  # noqa: E402
import build_reactor_outages as bro  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
OUT_TRIPS = TABLES / "intraday_squeeze_trips.csv"
OUT_CELLS = TABLES / "intraday_squeeze_cells.parquet"
MAX_AVAIL = 300.0
GROUP_DAYS = 3
MIN_SCHED = 200.0
PRE_DAYS, POST_DAYS = 7, 7
IDA_START = pd.Timestamp("2024-06-14")
BLACKOUT = pd.Timestamp("2025-04-28")
MAIN_END = pd.Timestamp("2024-06-13")
TZ = "Europe/Madrid"


def local(ts: pd.Series) -> pd.Series:
    return pd.to_datetime(ts).dt.tz_localize(TZ, ambiguous=True, nonexistent="shift_forward")


def trips() -> pd.DataFrame:
    dec, _ = bro.declarations()
    dec = dec[(dec.cls == "unplanned") & (dec.available_mw < MAX_AVAIL)].copy()
    raw = pd.concat([pd.read_parquet(f, columns=["outage_id", "declared"])
                     for f in sorted(glob.glob(str(DATA / "omie/indisp/parquet/*.parquet")))])
    decl = raw.groupby("outage_id").declared.min()
    dec["declared"] = local(dec.outage_id.map(decl))
    dec["start"] = dec.start.dt.tz_convert(TZ)
    dec["end"] = dec.end.dt.tz_convert(TZ)
    dec = dec.sort_values(["unit", "start"])
    new = dec.groupby("unit").start.diff().isna() | (dec.groupby("unit").start.diff() > pd.Timedelta(days=GROUP_DAYS))
    dec["trip"] = new.cumsum()
    t = dec.groupby("trip").agg(unit=("unit", "first"), start=("start", "min"), end=("end", "max"),
                                declared=("declared", "min"), n_decl=("outage_id", "size"),
                                outage_ids=("outage_id", lambda x: " ".join(x)),
                                reason=("reason", "first"), cause=("cause", "first")).reset_index(drop=True)
    t["known"] = t[["start", "declared"]].min(axis=1)
    kd = t.known.dt.tz_localize(None).dt.normalize()
    fixed_to = kd + pd.to_timedelta(np.where(t.known.dt.hour >= 12, 1, 0), unit="D")
    t["window_end"] = (fixed_to + pd.Timedelta(days=1)).dt.tz_localize(TZ, ambiguous=True, nonexistent="shift_forward")
    t["window_start"] = t.start
    t["window_h"] = ((t.window_end - t.window_start).dt.total_seconds() / 3600).clip(lower=0)
    t = t[t.window_h > 0].reset_index(drop=True)
    t["trip_id"] = [f"{u}_{s:%Y%m%d%H%M}" for u, s in zip(t.unit, t.start)]
    t["regime"] = np.where(t.start.dt.tz_localize(None) < IDA_START, "mibel6", "ida")
    t["dropped"] = t.start.dt.tz_localize(None).dt.normalize().eq(BLACKOUT)
    return t


def reactor_days(t: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Hourly day-ahead schedule of the reactors, and each reactor-day's 'out' share."""
    h = pd.read_parquet(TABLES / "reactor_outage_hours.parquet", columns=["unit", "utc", "sched_mw", "cap_mw", "lost_mw"])
    h["date"] = h.utc.dt.tz_convert(TZ).dt.tz_localize(None).dt.normalize()
    out = h.assign(o=h.lost_mw > 0.5 * h.cap_mw).groupby(["unit", "date"]).o.mean().rename("out").reset_index()
    return h[["unit", "utc", "sched_mw"]], out


def classify_days(t: pd.DataFrame, sched: pd.DataFrame, out: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per trip: DA schedule in the window, post days; and the list of (trip, class, UTC hour)."""
    rows, cells = [], []
    for r in t.itertuples(index=False):
        s = sched[(sched.unit == r.unit) & (sched.utc >= r.window_start.tz_convert("UTC")) &
                  (sched.utc < r.window_end.tz_convert("UTC"))]
        da = s.sched_mw.mean() if len(s) else np.nan
        wend = r.window_end.tz_localize(None).normalize()
        o = out[(out.unit == r.unit) & (out.date >= wend)].set_index("date").out
        post = []
        for k in range(POST_DAYS):
            dte = wend + pd.Timedelta(days=k)
            if o.get(dte, 0.0) >= 0.9:
                post.append(dte)
            else:
                break
        d0 = r.start.tz_localize(None).normalize()
        pre = [d0 - pd.Timedelta(days=k) for k in range(PRE_DAYS, 0, -1)]
        rows.append({"trip_id": r.trip_id, "da_sched_mw": da, "post_days": len(post)})
        hrs = pd.date_range(r.window_start.floor("h").tz_convert("UTC"), r.window_end.tz_convert("UTC"),
                            freq="h", inclusive="left")
        cells.append(pd.DataFrame({"trip_id": r.trip_id, "cls": "window", "utc": hrs}))
        for cls, days in (("pre", pre), ("post", post)):
            for dte in days:
                a = pd.Timestamp(dte).tz_localize(TZ).tz_convert("UTC")
                b = (pd.Timestamp(dte) + pd.Timedelta(days=1)).tz_localize(TZ).tz_convert("UTC")
                cells.append(pd.DataFrame({"trip_id": r.trip_id, "cls": cls,
                                           "utc": pd.date_range(a, b, freq="h", inclusive="left")}))
    return pd.DataFrame(rows), pd.concat(cells, ignore_index=True)


_UTC: dict = {}


def utc_hour(date, period, res) -> pd.Series:
    """UTC hour of each (local date, period, resolution) row."""
    key = pd.DataFrame({"d": pd.to_datetime(pd.Series(date)).to_numpy(), "p": np.asarray(period, int),
                        "r": np.asarray(res, int)})
    out = np.empty(len(key), dtype="datetime64[ns]")
    for (d, r), pos in key.groupby(["d", "r"]).indices.items():
        if (d, r) not in _UTC:
            d0 = pd.Timestamp(d)
            hours = round(((d0 + pd.Timedelta(days=1)).tz_localize(TZ) - d0.tz_localize(TZ)).total_seconds() / 3600)
            n = hours * 60 // int(r)
            _UTC[(d, r)] = np.array([np.datetime64(x.replace(tzinfo=None), "ns") for x in day_periods_utc(d0.date(), n)])
        u = _UTC[(d, r)]
        out[pos] = u[np.clip(key.p.to_numpy()[pos] - 1, 0, len(u) - 1)]
    idx = date.index if hasattr(date, "index") else None
    return pd.Series(pd.DatetimeIndex(out).tz_localize("UTC").floor("h"), index=idx)


def intraday(units_by_trip: dict, cells: pd.DataFrame) -> pd.DataFrame:
    """Cleared intraday volumes per trip, class, session and UTC hour."""
    cells = cells.copy()
    cells["month"] = cells.utc.dt.tz_convert(TZ).dt.strftime("%Y%m")
    sp = spells()
    out = []
    for m, cm in cells.groupby("month"):
        f = DATA / f"omie/intraday/parquet/intraday_{m}.parquet"
        nxt = (pd.Timestamp(m + "01") + pd.offsets.MonthBegin(1)).strftime("%Y%m")
        fs = [p for p in (f, DATA / f"omie/intraday/parquet/intraday_{nxt}.parquet") if os.path.exists(p)]
        if not fs:
            continue
        b = pd.concat([pq.read_table(p, columns=["session", "date", "period", "resolution_min", "unit", "side",
                                                  "power_mw", "status"], filters=[("status", "=", "C")]).to_pandas()
                       for p in fs], ignore_index=True)
        b["utc"] = utc_hour(b.date, b.period, b.resolution_min)
        b = b[b.utc.isin(set(cm.utc))]
        b["unit"] = b.unit.astype(str)
        b["sgn"] = np.where(b.side.astype(str) == "V", 1.0, -1.0)
        # mean MW over the hour's periods: power_mw is average MW per period
        b["w"] = b.power_mw * b.resolution_min.astype(float) / 60.0
        g = b.groupby(["session", "utc", "unit", "sgn"]).w.sum().unstack("sgn", fill_value=0.0)
        g.columns = ["buy" if c < 0 else "sell" for c in g.columns]
        g = g.reset_index()
        mkt = g.groupby(["session", "utc"]).sell.sum().rename("mkt_sell_mw")
        g["date"] = g.utc.dt.tz_convert(TZ).dt.tz_localize(None).dt.normalize()
        for tid, ct in cm.groupby("trip_id"):
            rx, owners = units_by_trip[tid]
            x = g[g.utc.isin(set(ct.utc))]
            r = x[x.unit == rx].set_index(["session", "utc"])
            o = x[x.unit != rx]
            o = attach_owners(o, sp, value_cols=("buy", "sell"))
            o = o[o.group.isin(owners) & ~o.pt]          # regulated pass-through supply is not exposed
            on = (o.sell - o.buy).groupby([o.session, o.utc]).sum().rename("own_other_net_sell_mw")
            k = ct.merge(mkt.reset_index(), on="utc", how="left")
            k = k.set_index(["session", "utc"])
            k["rx_net_buy_mw"] = (r.buy - r.sell).reindex(k.index).fillna(0.0)
            k["own_other_net_sell_mw"] = on.reindex(k.index).fillna(0.0)
            out.append(k.reset_index())
    c = pd.concat(out, ignore_index=True)
    c["b_mw"] = c.rx_net_buy_mw - c.own_other_net_sell_mw
    return c


def prices(c: pd.DataFrame) -> pd.DataFrame:
    ip = pd.read_parquet(DATA / "omie/intraday_prices/omie_intraday_prices.parquet")
    res = np.where(ip.groupby(["date", "session"]).period.transform("max") > 25, 15, 60)
    ip["utc"] = utc_hour(ip.date, ip.period, pd.Series(res, index=ip.index))
    ip = ip.groupby(["session", "utc"]).agg(p_id_pt=("price_a", "mean"), p_id_es=("price_b", "mean")).reset_index()
    da = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet", columns=["utc_timestamp", "price_es"])
    da["utc"] = pd.to_datetime(da.utc_timestamp, utc=True).dt.floor("h")
    da = da.groupby("utc").price_es.mean().rename("p_da_es").reset_index()
    return c.merge(ip, on=["session", "utc"], how="left").merge(da, on="utc", how="left")


def summarise(t: pd.DataFrame, c: pd.DataFrame) -> pd.DataFrame:
    """Per trip, from the cells. Owners and reactors trade intraday every day, so every
    measure is also given as its CHANGE against the trip's pre days in the same session
    and local hour: what the trip added."""
    derived = ("rx_buy_mw", "rx_buy_mwh", "b_mwh", "b_share", "b_share_of_mkt", "own_other_change_mw",
               "sessions_buying", "first_buy_session", "buyback_share", "rx_change_mw", "own_change_mw",
               "take_change_mw", "take_share", "take_share_of_mkt")
    t = t.drop(columns=[x for x in derived if x in t.columns])
    w = c[c.cls == "window"]
    pre = (c[c.cls == "pre"].groupby(["trip_id", "session", "local_hour"])
           [["rx_net_buy_mw", "own_other_net_sell_mw"]].mean().add_suffix("_pre").reset_index())
    w = w.merge(pre, on=["trip_id", "session", "local_hour"], how="left").fillna(
        {"rx_net_buy_mw_pre": 0.0, "own_other_net_sell_mw_pre": 0.0})
    w["rx_d"] = w.rx_net_buy_mw - w.rx_net_buy_mw_pre
    w["own_d"] = w.own_other_net_sell_mw - w.own_other_net_sell_mw_pre
    hourly = w.groupby(["trip_id", "utc"]).agg(rx=("rx_net_buy_mw", "sum"), rx_d=("rx_d", "sum"),
                                               own_d=("own_d", "sum"), mkt=("mkt_sell_mw", "sum")).reset_index()
    hourly["take_d"] = hourly.rx_d - hourly.own_d
    g = hourly.groupby("trip_id").agg(rx_buy_mw=("rx", "mean"), rx_change_mw=("rx_d", "mean"),
                                      own_change_mw=("own_d", "mean"), take_change_mw=("take_d", "mean"),
                                      take_sum=("take_d", "sum"), mkt_sum=("mkt", "sum")).reset_index()
    g["take_share_of_mkt"] = g.take_sum / g.mkt_sum
    sess = (w[w.rx_net_buy_mw > 1].groupby("trip_id").agg(sessions_buying=("session", "nunique"))
            .join(w[w.rx_net_buy_mw > 1].sort_values("utc").groupby("trip_id").session.first()
                  .rename("first_buy_session")).reset_index())
    t = t.merge(g.drop(columns=["take_sum", "mkt_sum"]), on="trip_id", how="left").merge(sess, on="trip_id", how="left")
    t["sessions_buying"] = t.sessions_buying.fillna(0).astype(int)
    t["buyback_share"] = t.rx_buy_mw / t.da_sched_mw
    t["take_share"] = t.take_change_mw / t.da_sched_mw
    return t


def report(t: pd.DataFrame, c: pd.DataFrame) -> None:
    keep = t[~t.dropped.astype(bool)]
    st = pd.to_datetime(keep.start, utc=True).dt.tz_convert(TZ)
    main = keep[st.dt.tz_localize(None) <= MAIN_END]
    pd.set_option("display.width", 240)
    print("\nTRIPS (MW: means over the window's hours, summed over sessions; 'change' is against the pre days)")
    print(keep[["trip_id", "owners", "regime", "window_h", "da_sched_mw", "post_days", "first_buy_session",
                "sessions_buying", "rx_buy_mw", "rx_change_mw", "own_change_mw", "take_change_mw", "take_share",
                "take_share_of_mkt"]].round(2).to_string(index=False))
    print(f"\nby year: {st.dt.year.value_counts().sort_index().to_dict()}; with post-window days: "
          f"{int((keep.post_days > 0).sum())}")
    q = lambda x: f"{x.median():.2f} (middle half {x.quantile(.25):.2f} to {x.quantile(.75):.2f})"  # noqa: E731
    for lab, g in (("main sample (to 2024-06-13)", main), ("IDA era", keep[keep.regime == "ida"])):
        print(f"{lab}: {len(g)} trips")
        print(f"  reactor's net intraday buy / DA schedule:                         {q(g.buyback_share)}")
        print(f"  owners' net take from rivals (change against pre days) / DA sched: {q(g.take_share)}")
        print(f"  owners' other units sold more intraday by (MW, median):            {g.own_change_mw.median():.0f}")
        print(f"  the take as a share of the window's cleared intraday sales:        {q(g.take_share_of_mkt)}")
    print(f"first session with a buy-back (main sample): "
          f"{main.first_buy_session.value_counts().sort_index().to_dict()}")
    print(f"cells: {len(c):,} (trip x class x session x hour); by class {c.cls.value_counts().to_dict()}")
    share30 = (main.buyback_share >= 0.30).mean()
    print(f"\nSTOP RULE (design §7): main-sample trips whose reactor buys back at least 30% of its day-ahead "
          f"schedule in the auctions: {share30:.0%} -> "
          f"{'continue to step 2' if share30 > 0.5 else 'propose step 4 or stop'}")


COLS = ["trip_id", "unit", "owners", "regime", "dropped", "start", "declared", "known", "window_start", "window_end",
        "window_h", "da_sched_mw", "post_days", "n_decl", "first_buy_session", "sessions_buying", "rx_buy_mw",
        "buyback_share", "rx_change_mw", "own_change_mw", "take_change_mw", "take_share", "take_share_of_mkt",
        "reason", "cause", "outage_ids"]


def main() -> int:
    t = trips()
    sched, out = reactor_days(t)
    info, cells = classify_days(t, sched, out)
    t = t.merge(info, on="trip_id")
    t = t[t.da_sched_mw >= MIN_SCHED].reset_index(drop=True)
    cells = cells[cells.trip_id.isin(t.trip_id)]
    print(f"{len(t)} trips (reactor below {MAX_AVAIL:.0f} MW, scheduled >= {MIN_SCHED:.0f} MW in the window); "
          f"{int(t.dropped.sum())} dropped (blackout)")
    sp = spells()
    day = t.start.dt.tz_localize(None).dt.normalize()
    own = attach_owners(t[["unit"]].assign(date=day), sp, value_cols=())
    owners = own.groupby(["unit", "date"]).group.apply(lambda g: sorted(set(g.dropna()))).to_dict()
    t["owners"] = [" ".join(owners[(u, d)]) for u, d in zip(t.unit, day)]
    units_by_trip = {tid: (u, set(o.split())) for tid, u, o in zip(t.trip_id, t.unit, t.owners)}
    c = intraday(units_by_trip, cells)
    c = c.merge(sched.rename(columns={"sched_mw": "da_sched_mw"}).merge(t[["trip_id", "unit"]], on="unit"),
                on=["trip_id", "utc"], how="left")
    c = prices(c)
    c = c.merge(t[["trip_id", "regime", "dropped"]], on="trip_id")
    c["local_date"] = c.utc.dt.tz_convert(TZ).dt.tz_localize(None).dt.normalize()
    c["local_hour"] = c.utc.dt.tz_convert(TZ).dt.hour
    t = summarise(t, c)
    TABLES.mkdir(parents=True, exist_ok=True)
    t[COLS].to_csv(OUT_TRIPS, index=False)
    c.to_parquet(OUT_CELLS, index=False)
    report(t, c)
    print(f"\nwrote {OUT_TRIPS.relative_to(ROOT)}, {OUT_CELLS.relative_to(ROOT)}")
    return 0


def summarise_only() -> int:
    """Recompute the per-trip measures and the report from the stored files."""
    t = summarise(pd.read_csv(OUT_TRIPS), pd.read_parquet(OUT_CELLS))
    c = pd.read_parquet(OUT_CELLS)
    t[[x for x in COLS if x in t.columns]].to_csv(OUT_TRIPS, index=False)
    report(t, c)
    return 0


if __name__ == "__main__":
    if "--summarise" in sys.argv:
        raise SystemExit(summarise_only())
    raise SystemExit(main())
