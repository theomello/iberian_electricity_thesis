#!/usr/bin/env python3
"""Leg D panel: keys, hours, the lagged-sign rules, X, the instrument and the outcome range.

    .venv/bin/python scripts/qa/check_leg_d_panel.py

Checks outputs/tables/leg_d_panel.parquet against its inputs (framework spec §4,
leg D). Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "outputs/tables/leg_d_panel.parquet"
FIRM_X = ROOT / "outputs/tables/firm_x.parquet"
RIVAL = ROOT / "outputs/tables/rival_solar.parquet"
PRICES = ROOT / "data/omie/prices/omie_day_ahead_prices.parquet"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")
OVER_CAP = 1.02
HOURLY_DAY, QUARTER_DAY = pd.Timestamp("2024-06-12"), pd.Timestamp("2025-12-10")


def firm_hour(x: pd.DataFrame, firm: str, day: pd.Timestamp, col: str) -> pd.Series:
    """Hourly mean of a firm_x column over the clean periods with X defined."""
    g = x[(x.firm == firm) & (x.date == day) & x.clean & x.X.notna()].copy()
    g["hour"] = (g.period - 1) // (60 // g.resolution_min)
    return g.groupby("hour")[col].mean()


def main() -> int:
    if not PANEL.exists():
        print(f"  FAIL {PANEL.relative_to(ROOT)} missing -- run scripts/analysis/leg_d_panel.py")
        return 1
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    h = pd.read_parquet(PANEL)
    five = h[h.firm != "FRINGE"]
    print(f"{len(h):,} unit-hours, {h.unit.nunique()} units, {h.date.min().date()} .. {h.date.max().date()}")
    check(not h.duplicated(["unit", "date", "hour"]).any(), "one row per unit x date x hour")
    check(set(h.firm) <= set(FIRMS) | {"FRINGE"}, "firm is one of the five or FRINGE")
    check(h.loc[h.firm == "FRINGE", "X"].isna().all(), "FRINGE rows carry no X")
    check(five.X.notna().all(), "every five-firm row has X")
    check(bool((five.Xp + five.Xm - five.X).abs().max() < 1e-4), "Xp + Xm = X")
    check(bool(h.hour.between(0, 24).all() and h.n_per.between(1, 4).all()), "hours 0..24, 1..4 periods each")
    check(bool(h.s75.max() <= OVER_CAP + 1e-6 and h.s25.min() >= 0), "capacity shares within [0, 1.02]")
    check(bool(h.cap_mw.notna().all() and (h.cap_mw > 0).all()), "capacity known and positive")
    check(five.z.notna().all() and five.fcst.notna().mean() > 0.99, "instrument everywhere, forecast on >99%")
    ok = five.s_prev.notna()
    check(bool(np.allclose(five.zs[ok], five.z[ok] * five.s_prev[ok], atol=1e-5)), "zs = z * s_prev")

    px = pd.read_parquet(PRICES, columns=["date", "period", "resolution_min"])
    px["date"] = pd.to_datetime(px.date)
    hours = px.groupby("date").apply(lambda g: len(g) * g.resolution_min.iloc[0] / 60, include_groups=False)
    odd = set(hours[hours != 24].index)
    odd |= {d + pd.Timedelta(days=1) for d in odd}
    check(five[five.date.isin(odd)].s_prev.isna().all(), "s_prev undefined on DST days and the days after")
    odd7 = set(hours[hours != 24].index) | {d + pd.Timedelta(days=7) for d in hours[hours != 24].index}
    check(five[five.date.isin(odd7)].s_prev7.isna().all(), "s_prev7 undefined on DST days and 7 days after")
    ok7 = five.s_prev7.notna()
    check(bool(np.allclose(five.zs7[ok7], five.z[ok7] * five.s_prev7[ok7], atol=1e-5)), "zs7 = z * s_prev7")
    first = five[five.date == pd.Timestamp("2024-06-01")]
    check(len(first) > 0 and first.s_prev.notna().mean() > 0.99, "2024-06-01: s_prev reaches back into May")

    x = pd.read_parquet(FIRM_X, columns=["date", "period", "resolution_min", "firm", "clean", "X", "net_mw"])
    x["date"] = pd.to_datetime(x.date)
    for firm, day in (("EDP", HOURLY_DAY), ("IBERDROLA", QUARTER_DAY)):
        p = five[(five.firm == firm) & (five.date == day)].drop_duplicates("hour").set_index("hour")
        check(len(p) > 0 and float((p.X - firm_hour(x, firm, day, "X").reindex(p.index)).abs().max()) < 1e-4,
              f"{firm} {day.date()}: X is the hourly mean of firm_x")
        prev = x[(x.firm == firm) & (x.date == day - pd.Timedelta(days=1))].copy()
        prev["hour"] = (prev.period - 1) // (60 // prev.resolution_min)
        want = (prev.groupby("hour").net_mw.mean() > 0).astype(float).reindex(p.index)
        check(bool((p.s_prev == want).all()), f"{firm} {day.date()}: s_prev is yesterday's sign, same hour")
        wk_ago = x[(x.firm == firm) & (x.date == day - pd.Timedelta(days=7))].copy()
        wk_ago["hour"] = (wk_ago.period - 1) // (60 // wk_ago.resolution_min)
        want7 = (wk_ago.groupby("hour").net_mw.mean() > 0).astype(float).reindex(p.index)
        check(bool((p.s_prev7 == want7).all()), f"{firm} {day.date()}: s_prev7 is the sign 7 days before")

    # A period without an offer inside a present unit-day scores 0; it is not dropped.
    fh = x[x.clean & x.X.notna()].copy()
    fh["hour"] = (fh.period - 1) // (60 // fh.resolution_min)
    firm_hours = fh.groupby(["firm", "date"]).hour.nunique().rename("firm_hours").reset_index()
    uh = five.groupby(["unit", "firm", "date"]).size().rename("unit_hours").reset_index()
    uh = uh.merge(firm_hours, on=["firm", "date"], how="left")
    gap = float((uh.unit_hours != uh.firm_hours).mean())
    check(gap < 0.001, f"every unit-day covers all its firm's clean hours ({gap:.4f} do not)")

    # Ownership on the date, by the unit's largest owner (lib/unit_ownership.py, 2026-10-02).
    sys.path.insert(0, str(ROOT / "scripts" / "lib"))
    from unit_ownership import majority_group
    ud = h[["unit", "date"]].drop_duplicates()
    g = majority_group(ud)
    want = pd.Series(g.where(g.isin(FIRMS), "FRINGE").to_numpy(), index=pd.MultiIndex.from_frame(ud))
    got = h.drop_duplicates(["unit", "date"]).set_index(["unit", "date"]).firm
    off = (got != want.reindex(got.index)).sum()
    check(off == 0, f"every unit-day counts for its largest owner that day, or FRINGE ({off:,} do not)")
    check(not ((five.firm == "REPSOL") & (five.date < pd.Timestamp("2018-11-02"))).any(),
          "no REPSOL rows before Repsol bought Viesgo (2018-11-02)")
    ct = h[h.unit.isin(["CTJON1", "CTJON3"])]
    check(ct.empty or ((ct.firm == "EDP") == (ct.date < pd.Timestamp("2020-12-01"))).all(),
          "Castejon is EDP's before its sale on 2020-12-01 and FRINGE after")
    al = h[h.unit == "ALL1"]
    check(al.empty or (al.firm == "NATURGY").all(), "a co-owned unit follows its majority owner (ALL1: Naturgy 2/3)")

    r = pd.read_parquet(RIVAL)
    r["date"] = pd.to_datetime(r.date)
    r = r[r.date == HOURLY_DAY].set_index("period").z_rival_EDP / 1000
    p = five[(five.firm == "EDP") & (five.date == HOURLY_DAY)].drop_duplicates("hour").set_index("hour")
    check(float((p.z - r.reindex(p.index + 1).to_numpy()).abs().max()) < 1e-4,
          f"EDP {HOURLY_DAY.date()}: z is rivals' offered solar in GW")

    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
