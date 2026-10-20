#!/usr/bin/env python3
"""RTE's eco2mix national data, hourly in UTC.

    .venv/bin/python scripts/qa/check_rte_eco2mix.py

Checks `data/rte/eco2mix_national.parquet` (`fetch/fetch_rte_eco2mix.py`):
  - at least 99.9% of UTC hours 2018-01-01 → 2025-09-30 present;
  - French nuclear output within 10–65 GW in every hour;
  - RTE's D-1 demand forecast correlates above 0.95 with realised demand;
  - the commercial exchange with Spain correlates above 0.8 in absolute value with OMIE's
    scheduled net flow on the France border (export_occupied + import_occupied, imports
    negative as published); the sign is printed, not assumed.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
FILE = ROOT / "data" / "rte" / "eco2mix_national.parquet"


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    if not FILE.exists():
        print(f"  FAIL {FILE.relative_to(ROOT)} missing\nFAIL: 1")
        return 1
    r = pd.read_parquet(FILE)
    w = r[(r.utc >= pd.Timestamp("2018-01-01", tz="UTC")) & (r.utc < pd.Timestamp("2025-10-01", tz="UTC"))]
    want = pd.date_range("2018-01-01", "2025-09-30 23:00", freq="h", tz="UTC")
    have = want.isin(w.utc).mean()
    check(have >= 0.999, f"UTC hours present: {have:.4%} of {len(want):,}")
    check(w.nucleaire.between(10_000, 65_000).all(),
          f"nuclear within 10–65 GW (min {w.nucleaire.min():,.0f}, max {w.nucleaire.max():,.0f})")
    c = w.prevision_j1.corr(w.consommation)
    check(c > 0.95, f"corr(D-1 forecast, demand) {c:.3f}")

    ic = pd.read_parquet(ROOT / "data/omie/interconnection/omie_interconnection_capacity.parquet")
    ic = ic[(ic.border == "FR") & (ic.resolution_min == 60)]
    px = pd.read_parquet(ROOT / "data/omie/prices/omie_day_ahead_prices.parquet", columns=["date", "period", "utc_timestamp"])
    ic = ic.merge(px, on=["date", "period"])
    ic["utc"] = pd.to_datetime(ic.utc_timestamp, utc=True)
    ic["net"] = ic.export_occupied_mw + ic.import_occupied_mw
    j = ic.merge(w[["utc", "ech_comm_espagne"]], on="utc")
    c = j.net.corr(j.ech_comm_espagne)
    check(abs(c) > 0.8, f"corr(RTE exchange with Spain, OMIE net flow Spain→France) {c:+.3f} on {len(j):,} hours "
                        f"({'RTE positive = France exports to Spain' if c < 0 else 'same sign as OMIE'})")
    print("PASS" if not fails else f"FAIL: {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
