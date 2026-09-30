#!/usr/bin/env python3
"""Rivals' offered solar: one row per period, the identity, and EDP's z_offered reproduced.

    .venv/bin/python scripts/qa/check_rival_solar.py

Framework spec §4, leg D. Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "build"))
OUT = ROOT / "outputs/tables/rival_solar.parquet"
SOLAR = ROOT / "outputs/tables/solar_instrument.parquet"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")
KEY = ["date", "period"]


def partial_month_kept_out() -> list[str]:
    """A priced day with no bid rows (a partial frontier zip) must be absent, not zero."""
    from build_rival_solar import align
    px = pd.DataFrame({"date": pd.to_datetime(["2026-05-01"] * 2 + ["2026-05-02"] * 2),
                       "period": [1, 2, 1, 2]})
    d = pd.DataFrame({"date": pd.to_datetime(["2026-05-01"]), "period": [2], "z_all": [5.0]}
                     | {f"own_{f}": [1.0] for f in FIRMS})
    a = align(d, px)
    fails = []
    if set(a.date) != {pd.Timestamp("2026-05-01")}:
        fails.append("a priced day with no bids was kept (would read as zero solar)")
    if len(a) != 2 or a.loc[a.period == 1, "z_all"].iloc[0] != 0.0:
        fails.append("a period without solar rows inside a bid day must carry 0")
    if (a.z_rival_EDP != a.z_all - a.own_EDP).any():
        fails.append("align: z_rival_EDP != z_all - own_EDP")
    return fails


def main() -> int:
    unit = partial_month_kept_out()
    print("align on a synthetic partial month:", "ok" if not unit else "; ".join(unit))
    if unit:
        for f_ in unit:
            print(f"  FAIL {f_}")
        return 1
    if not OUT.exists():
        print(f"  FAIL {OUT.relative_to(ROOT)} missing -- run scripts/build/build_rival_solar.py")
        return 1
    fails: list[str] = []
    d = pd.read_parquet(OUT)
    d["date"] = pd.to_datetime(d.date)
    if d.duplicated(KEY).any():
        fails.append("duplicate (date, period) rows")
    num = [c for c in d.columns if c not in KEY]
    if d[num].isna().any().any():
        fails.append("missing values: a period with no solar offer must carry 0")
    for f in FIRMS:
        if (d[f"own_{f}"] < 0).any():
            fails.append(f"own_{f} negative")
        if ((d.z_all - d[f"own_{f}"] - d[f"z_rival_{f}"]).abs() > 1e-6).any():
            fails.append(f"z_rival_{f} != z_all - own_{f}")
    px = pd.read_parquet(ROOT / "data/omie/prices/omie_day_ahead_prices.parquet", columns=KEY)
    px["date"] = pd.to_datetime(px.date)
    px = px[px.date.dt.strftime("%Y%m").isin(set(d.date.dt.strftime("%Y%m")))]
    missing = len(px.merge(d[KEY], on=KEY, how="left", indicator=True).query("_merge == 'left_only'"))
    print(f"priced periods in the covered months: {len(px):,}; missing here: {missing}")
    if missing:
        fails.append(f"{missing} priced periods missing (night periods must carry z, not be dropped)")
    s = pd.read_parquet(SOLAR, columns=KEY + ["z_offered"])
    s["date"] = pd.to_datetime(s.date)
    m = d.merge(s, on=KEY).dropna(subset=["z_offered"])
    corr = m.z_rival_EDP.corr(m.z_offered)
    med = (m.z_rival_EDP - m.z_offered).abs().median()
    print(f"EDP's rival solar vs z_offered: {len(m):,} periods, corr {corr:.6f}, median |diff| {med:.3f} MW")
    if not (corr > 0.999 and med < 1.0):
        fails.append("z_rival_EDP does not reproduce z_offered")
    print("mean own offered solar, MW:", {f: round(d[f"own_{f}"].mean()) for f in FIRMS},
          f"of z_all {d.z_all.mean():.0f}")
    for f_ in fails:
        print(f"  FAIL {f_}")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
