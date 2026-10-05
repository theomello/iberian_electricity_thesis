#!/usr/bin/env python3
"""Event study: the owners' plants against rivals' plants, day by day around an unplanned reactor trip.

    .venv/bin/python scripts/analysis/outage_offer_panel.py      # input: offers and X by unit-hour
    .venv/bin/python scripts/analysis/outage_event_study.py

`notes/rq-reactor-outages.md` §6: with unit x week effects, a firm's own unplanned
outage raised its combined cycles' offers (+16 EUR/MWh per GW, t 1.7), the wrong
sign for market power. Week effects keep only the starts and ends of spells and hide
the timing. This shows the timing directly.

EVENTS. Unplanned spells (`reactor_outage_spells.csv`) of at least MIN_HOURS, with
no unplanned spell of the same reactor in the GAP_DAYS before, and the reactor
running normally in the PRE days before (mean lost output under PRE_CLEAN of
capacity, any cause): six "trips" continue a refuelling or another stop, so their
owners were already short in the pre-period. Day 0 is the Madrid
date the spell starts in the PDBF schedule: the first delivery day whose day-ahead
offers were made after the trip. Day -1's offers were made before it.

DESIGN. Stacked (one copy of the panel per event, days -PRE..+POST), unit-day means
of the outage panel's clean hours:

    y_ude = a_(unit x event) + d_(technology x date x event)
            + sum_(k != -1) b_k x 1[day - day0 = k] x T_ge + controls + e

T_ge is the group's share of the tripped reactor that day times its capacity (GW),
0 for every other group, so rivals' plants of the same technology on the same day
are the comparison. Controls: the group's unplanned dose from OTHER reactors and its
planned dose (GW, daily means), so overlapping outages do not load on b_k.
Clusters: events. With about 30 events, read the pattern, not single days.

Also binned: days -PRE..-2 (pre), 0..+3 (first days), +4..+POST (later), against -1.

Writes outputs/tables/outage_event_study.csv and outputs/figures/outage_event_study.png.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from midday_hydro_iv import ols  # noqa: E402
from outage_offer_test import demean  # noqa: E402
from unit_ownership import spells  # noqa: E402

TABLES = ROOT / "outputs/tables"
OUT = TABLES / "outage_event_study.csv"
FIG = ROOT / "outputs/figures/outage_event_study.png"
MIN_HOURS = 24
GAP_DAYS = 14
PRE_CLEAN = 0.10
PRE, POST = 7, 14
TZ = "Europe/Madrid"


def events() -> pd.DataFrame:
    s = pd.read_csv(TABLES / "reactor_outage_spells.csv", parse_dates=["start", "end"])
    u = s[s.cls == "unplanned"].sort_values(["unit", "start"]).copy()
    prev_end = u.groupby("unit").end.shift()
    fresh = prev_end.isna() | ((u.start - prev_end) > pd.Timedelta(days=GAP_DAYS))
    e = u[fresh & (u.hours >= MIN_HOURS)].copy()
    e["day0"] = e.start.dt.tz_convert(TZ).dt.tz_localize(None).dt.normalize()
    e["event"] = e.unit + "_" + e.day0.dt.strftime("%Y%m%d")
    h = pd.read_parquet(TABLES / "reactor_outage_hours.parquet", columns=["unit", "utc", "cap_mw", "lost_mw"])
    cap = h.groupby("unit").cap_mw.median()
    h["date"] = h.utc.dt.tz_convert(TZ).dt.tz_localize(None).dt.normalize()
    lost = h.groupby(["unit", "date"]).apply(lambda g: g.lost_mw.sum() / g.cap_mw.sum(), include_groups=False)

    def pre_lost(r) -> float:
        days = pd.date_range(r.day0 - pd.Timedelta(days=PRE), r.day0 - pd.Timedelta(days=1))
        return float(lost.reindex([(r.unit, x) for x in days]).fillna(1.0).mean())

    e["pre_lost"] = e.apply(pre_lost, axis=1)
    print("dropped, reactor not running normally in the week before:",
          ", ".join(f"{x} ({v:.0%})" for x, v in zip(e.event[e.pre_lost >= PRE_CLEAN], e.pre_lost[e.pre_lost >= PRE_CLEAN])))
    e = e[e.pre_lost < PRE_CLEAN]
    sp = spells()
    rows = []
    for r in e.itertuples():
        o = sp[(sp.unit == r.unit) & (sp.start <= r.day0) & (sp.end > r.day0)]
        for g, sh in o.groupby("group").share.sum().items():
            rows.append({"event": r.event, "reactor": r.unit, "day0": r.day0, "days": r.hours / 24,
                         "group": g, "share": sh, "T": sh * cap[r.unit] / 1000})
    return pd.DataFrame(rows)


def daily_doses() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(group x date planned and unplanned dose, GW, 24-hour means; reactor x date unplanned lost GW)."""
    dz = pd.read_parquet(TABLES / "reactor_outage_dose.parquet")
    dz = dz[dz.cls.isin(["unplanned", "planned"])].copy()
    dz["date"] = dz.utc.dt.tz_convert(TZ).dt.tz_localize(None).dt.normalize()
    g = dz.pivot_table(index=["firm", "date"], columns="cls", values="lost_mw", aggfunc="sum").fillna(0) / 24 / 1000
    g = g.rename(columns={"unplanned": "unpl_all", "planned": "plan"}).reset_index().rename(columns={"firm": "group"})
    h = pd.read_parquet(TABLES / "reactor_outage_hours.parquet", columns=["unit", "utc", "cls", "lost_decl_mw"])
    h = h[h.cls.eq("unplanned") & (h.lost_decl_mw > 0)].copy()
    h["date"] = h.utc.dt.tz_convert(TZ).dt.tz_localize(None).dt.normalize()
    r = (h.groupby(["unit", "date"]).lost_decl_mw.sum() / 24 / 1000).rename("lost").reset_index()
    return g, r.rename(columns={"unit": "reactor"})


def main() -> int:
    ev = events()
    one = ev.drop_duplicates("event")
    print(f"{len(one)} events (unplanned, >= {MIN_HOURS} h, none of the same reactor in the {GAP_DAYS} days before, "
          f"running normally the {PRE} days before); "
          f"median length {one.days.median():.1f} days")
    print(one.groupby("reactor").size().to_string())
    p = pd.read_parquet(TABLES / "outage_offer_panel.parquet",
                        columns=["unit", "group", "cls", "date", "o25", "o50", "X", "off_share"])
    p = p.groupby(["unit", "group", "cls", "date"], as_index=False)[["o25", "o50", "X", "off_share"]].mean()
    gd, rl = daily_doses()
    parts = []
    for e in one.itertuples():
        w = p[(p.date >= e.day0 - pd.Timedelta(days=PRE)) & (p.date <= e.day0 + pd.Timedelta(days=POST))].copy()
        w["event"] = e.event
        w["k"] = (w.date - e.day0).dt.days
        w = w.merge(ev[ev.event == e.event][["group", "share", "T"]], on="group", how="left").fillna(
            {"share": 0.0, "T": 0.0})
        w = w.merge(gd, on=["group", "date"], how="left").fillna({"unpl_all": 0.0, "plan": 0.0})
        own = rl[rl.reactor == e.reactor][["date", "lost"]]
        w = w.merge(own, on="date", how="left").fillna({"lost": 0.0})
        # the group's unplanned dose from other reactors: all of it minus its share of this one
        w["unpl_other"] = (w.unpl_all - w.lost * w.share).clip(lower=0)
        parts.append(w)
    d = pd.concat(parts, ignore_index=True)
    d["ue"] = d.unit + "|" + d.event
    d["cde"] = d.cls + "|" + d.date.dt.strftime("%Y%m%d") + "|" + d.event
    ks = [k for k in range(-PRE, POST + 1) if k != -1]
    for k in ks:
        d[f"t{k}"] = d["T"] * (d.k == k)
    d["b_pre"] = d["T"] * d.k.between(-PRE, -2)
    d["b_early"] = d["T"] * d.k.between(0, 3)
    d["b_late"] = d["T"] * d.k.between(4, POST)
    print(f"{len(d):,} unit-day-event rows, {d.unit.nunique()} units")

    rows = []
    days = [f"t{k}" for k in ks]
    ctrl = ["unpl_other", "plan"]
    samples = {"thermal": d.cls.isin(["ccgt", "coal"]), "ccgt": d.cls.eq("ccgt"), "coal": d.cls.eq("coal"),
               "hydro": d.cls.eq("hydro"), "all": d.cls.notna()}
    for name, m in samples.items():
        s = d[m.to_numpy()]
        for y in ("o50", "o25", "X", "off_share"):
            if y in ("X", "off_share") and name not in ("all", "thermal"):
                continue
            ss = s.dropna(subset=[y])
            cols = [y, *days, "b_pre", "b_early", "b_late", *ctrl]
            M = demean(ss[cols].to_numpy(float), [pd.factorize(ss.ue)[0], pd.factorize(ss.cde)[0]])
            D = pd.DataFrame(M, columns=cols)
            cl = ss.event.to_numpy()
            b, se = ols(D[y].to_numpy(), D[days + ctrl].to_numpy(), cl)
            for j, k in enumerate(ks):
                rows.append({"sample": name, "y": y, "spec": "by day", "k": k, "b": b[j], "se": se[j],
                             "n": len(ss), "events": ss.event.nunique()})
            bb, sb = ols(D[y].to_numpy(), D[["b_pre", "b_early", "b_late", *ctrl]].to_numpy(), cl)
            for j, lab in enumerate(["pre (-7..-2)", "days 0..3", "days 4..14"]):
                rows.append({"sample": name, "y": y, "spec": "binned", "k": lab, "b": bb[j], "se": sb[j],
                             "n": len(ss), "events": ss.event.nunique()})
            print(f"  {name:8s} {y:9s} pre {bb[0]:+7.2f} ({sb[0]:5.2f})   days 0-3 {bb[1]:+7.2f} ({sb[1]:5.2f})   "
                  f"days 4-14 {bb[2]:+7.2f} ({sb[2]:5.2f})   per GW of the owner's share, n={len(ss):,}")
    r = pd.DataFrame(rows)
    r.to_csv(OUT, index=False)
    plot(r)
    print(f"\n-> {OUT.relative_to(ROOT)}, {FIG.relative_to(ROOT)}")
    return 0


def plot(r: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    panels = [("ccgt", "o50", "Combined cycles: offer at 50% of volume"),
              ("coal", "o50", "Coal: offer at 50% of volume"),
              ("hydro", "o50", "Hydro: offer at 50% of volume"),
              ("all", "X", "Firm's X (first stage)")]
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.5), sharex=True)
    for ax, (s, y, title) in zip(axes.flat, panels):
        q = r[(r["sample"] == s) & (r.y == y) & (r.spec == "by day")].copy()
        q["k"] = q.k.astype(int)
        q = pd.concat([q, pd.DataFrame({"k": [-1], "b": [0.0], "se": [0.0]})]).sort_values("k")
        ax.axhline(0, color="#888", lw=0.8)
        ax.axvline(-0.5, color="#888", lw=0.8, ls=":")
        ax.fill_between(q.k, q.b - 1.96 * q.se, q.b + 1.96 * q.se, color="#4a7ab5", alpha=0.2, lw=0)
        ax.plot(q.k, q.b, "o-", color="#2b5d9b", ms=3, lw=1.2)
        ax.set_title(title, fontsize=10)
        ax.set_ylabel("EUR/MWh per GW")
    for ax in axes[1]:
        ax.set_xlabel("days from the trip (0 = first delivery day after it)")
    fig.suptitle("Owners' plants against rivals' plants around unplanned reactor trips (95% bands, event clusters)",
                 fontsize=10)
    fig.tight_layout()
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=150)


if __name__ == "__main__":
    raise SystemExit(main())
