#!/usr/bin/env python3
"""Checks on the reactor outage table (`build/build_reactor_outages.py`).

    .venv/bin/python scripts/qa/check_reactor_outages.py

- Lost output re-derived for one month straight from PDBF and `cab`, without the
  builder's code, matches the stored hours.
- The dose adds up to the lost output, and a co-owned reactor's dose splits by the
  listed shares (Almaraz 1 on 2024-01-15: Iberdrola 0.527, Endesa 0.360, Naturgy 0.113).
- Known events land in the right class: Almaraz 1's refuelling of 2018-10-29, Vandellos
  II's long stop of 2018-04/07, Cofrentes' and Almaraz 1's flexible operation of
  2025-04, Almaraz 1's generator trip of 2020-06-22.
- No hour carries more lost output than capacity; parts add up.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_common import day_periods_utc  # noqa: E402

T = ROOT / "outputs/tables"


def main() -> int:
    fails = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    h = pd.read_parquet(T / "reactor_outage_hours.parquet")
    dz = pd.read_parquet(T / "reactor_outage_dose.parquet")
    s = pd.read_csv(T / "reactor_outage_spells.csv", parse_dates=["start", "end"])

    # 1. Re-derive October 2018 for Almaraz 1 from PDBF and cab.
    p = pq.read_table(ROOT / "data/omie/pdbf/parquet/pdbf_201810.parquet",
                      columns=["date", "period", "unit", "schedule_mw"], filters=[("unit", "==", "ALZ1")]).to_pandas()
    p = p.groupby(["date", "period"], as_index=False).schedule_mw.sum()
    rows = []
    for d, g in p.groupby("date"):
        ts = day_periods_utc(pd.Timestamp(d).date(), int(g.period.max()))
        rows += [(pd.Timestamp(ts[k - 1]).floor("h"), v) for k, v in zip(g.period, g.schedule_mw)]
    re = pd.DataFrame(rows, columns=["utc", "sched"]).groupby("utc").sched.mean()
    c = pq.read_table(ROOT / "data/omie/cab/parquet/cab_201810.parquet", columns=["unit", "max_power_mw"],
                      filters=[("unit", "==", "ALZ1")]).to_pandas()
    cap = float(c[c.max_power_mw > 0].max_power_mw.median())
    st = h[(h.unit == "ALZ1") & h.utc.isin(re.index)].set_index("utc")
    gap = float((st.sched_mw - re.reindex(st.index).fillna(0)).abs().max())
    check(gap < 1e-6 and abs(st.cap_mw.iloc[0] - cap) < 1e-6,
          f"ALZ1 October 2018 schedule and capacity re-derived from PDBF and cab (max gap {gap:.2e} MW, cap {cap})")

    # 2. Dose = lost output; shares.
    tot = h.lost_mw.sum()
    check(abs(dz.lost_mw.sum() - tot) / tot < 1e-6, f"dose sums to the lost output ({dz.lost_mw.sum():,.0f} vs {tot:,.0f} MWh)")
    check(bool((h.lost_mw <= h.cap_mw + 1e-6).all() and (h.lost_mw >= 0).all()), "0 <= lost <= capacity in every hour")
    check(bool((abs(h.lost_decl_mw + h.lost_undecl_mw - h.lost_mw) < 1e-6).all()), "declared + undeclared = lost")

    # 3. Known events.
    def cls_at(unit: str, t: str) -> str | None:
        r = h[(h.unit == unit) & (h.utc == pd.Timestamp(t, tz="UTC"))]
        return r.cls.iloc[0] if len(r) and r.lost_decl_mw.iloc[0] > 0 else None

    for unit, t, want, what in (("ALZ1", "2018-11-10 12:00", "planned", "Almaraz 1 refuelling, 2018-10-29 -> 12-02"),
                                ("VAN2", "2018-06-01 12:00", "unplanned", "Vandellos II long stop, 2018"),
                                ("COF1", "2025-04-25 12:00", "economic", "Cofrentes flexible operation, 2025-04"),
                                ("ALZ1", "2025-04-25 12:00", "economic", "Almaraz 1 flexible operation, 2025-04"),
                                ("ALZ1", "2020-06-24 12:00", "unplanned", "Almaraz 1 generator trip, 2020-06-22")):
        got = cls_at(unit, t)
        check(got == want, f"{what}: {got}")

    # 4. Almaraz 1's dose splits by its listed shares.
    down = h[h.lost_mw > 0].groupby("utc").unit.agg(set)
    alone = down[down.map(lambda u: u == {"ALZ1"})].index
    alone = alone[(alone.year >= 2023)]
    check(len(alone) > 0, f"hours with only Almaraz 1 down since 2023: {len(alone):,}")
    if len(alone):
        t0 = alone[len(alone) // 2]
        share = dz[dz.utc == t0].groupby("firm").lost_mw.sum()
        sh = (share / share.sum()).round(3).to_dict()
        check(abs(sh.get("IBERDROLA", 0) - 0.527) < 0.002 and abs(sh.get("ENDESA", 0) - 0.360) < 0.002
              and abs(sh.get("NATURGY", 0) - 0.113) < 0.002, f"Almaraz 1 dose by share at {t0}: {sh}")
    check(s.cls.notna().all() and (s.hours > 0).all(), f"spells: {len(s)} with a class and positive length")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
