#!/usr/bin/env python3
"""The running variable of the minimum-income near-miss design.

    .venv/bin/python scripts/qa/check_mic_running.py

Checks `build/build_mic_running.py`:
  - shift_price on a toy hour: prices 0/10/20/30 with cumulative effective MW
    100/200/300/400 and 300 MW of demand clear at 20; adding 50 MW at 5 leaves 20;
    adding 100 MW at 5 clears at 10;
  - 2019-01-03 (spec §0's example): Sagunto 1 withdrawn, r = −0.058 ± 0.01, r_A ≤ r;
    San Roque 1 accepted, 20 hours cleared, r_A = r = 0.226 ± 0.01;
  - the price shift is ≤ 0 for every withdrawn row (adding supply cannot raise the price),
    and r_A ≤ r + 0.001 on all but 0.01% (a lower price can drop a unit's cheapest hours);
    r_A = r for every accepted row;
  - no date after 2025-03-18 (the condition ends there); `flag` is the same for every unit
    on a day (a day with more than four hours that cannot be re-cleared);
  - accepted rows (≥ 4 hours cleared) have r ≥ −0.5 in at least 98% of Spanish and of
    Portuguese unit-days separately (a Portuguese unit priced at the Spanish price in
    split hours would fail).
  - mw_below_v within [0, mw_offered]; a day with F = 0 and nothing offered below v has
    r ≥ −0.01 (the condition cannot bind: whatever sells earns at least v); can_bind is
    F > 0 or some MW below v; re-cleared rows carry add_mw ≥ 0 and slope_local > 0.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "build"))
from build_mic_running import OUT, shift_price  # noqa: E402


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    pr, a = np.array([0.0, 10, 20, 30]), np.array([100.0, 200, 300, 400])
    none = shift_price(pr, a, 300.0, np.array([]), np.array([]))
    small = shift_price(pr, a, 300.0, np.array([5.0]), np.array([50.0]))
    big = shift_price(pr, a, 300.0, np.array([5.0]), np.array([100.0]))
    check((none, small, big) == (20.0, 20.0, 10.0), f"shift_price: {none}, {small}, {big} (want 20, 20, 10)")

    d = pd.read_parquet(OUT)
    d["date"] = pd.to_datetime(d.date)
    ex = d[d.date == "2019-01-03"].set_index("unit")
    s = ex.loc["SAGU1"]
    check((not s.accepted) and abs(s.r + 0.058) < 0.01 and s.r_A <= s.r + 1e-9,
          f"SAGU1 2019-01-03: accepted {s.accepted}, r {s.r:.3f}, r_A {s.r_A:.3f}")
    q = ex.loc["SROQ1"]
    check(q.accepted and q.hours_cleared == 20 and abs(q.r - 0.226) < 0.01 and q.r_A == q.r,
          f"SROQ1 2019-01-03: accepted {q.accepted}, {q.hours_cleared} h, r {q.r:.3f}, r_A {q.r_A:.3f}")

    w = d[~d.accepted & d.r.notna()]
    check((w.dp_mean <= 1e-12).all(), f"withdrawn: price shift ≤ 0 on {(w.dp_mean <= 1e-12).mean():.4%} of {len(w):,}")
    # r_A can exceed r when the lower price drops the unit's cheapest hours and raises its
    # average price (Castejón 3, 2022-02-13: −4.15 → −1.86); allow that on 0.01% of rows
    up = (w.r_A > w.r + 1e-3).mean()
    check(up <= 1e-4, f"withdrawn: r_A ≤ r + 0.001 except on {up:.4%} (≤ 0.01%)")
    acc = d[d.accepted]
    check((acc.r_A == acc.r).all(), f"accepted: r_A = r on {(acc.r_A == acc.r).mean():.4%} of {len(acc):,}")
    check(d.date.max() <= pd.Timestamp("2025-03-18"), f"last date {d.date.max().date()}")
    # the flag is a property of the day (its hours that cannot be re-cleared), the same for
    # accepted and withdrawn units; flagging only withdrawn units drops them asymmetrically
    k = d.groupby("date").flag.nunique().max()
    check(k == 1, f"flag is constant within a day (max distinct values per day {k})")

    # Task 6: whether the condition can bind on the day
    check({"mw_offered", "mw_below_v", "can_bind", "add_mw", "slope_local"} <= set(d.columns),
          "columns mw_offered, mw_below_v, can_bind, add_mw, slope_local present")
    if "mw_below_v" in d.columns:
        check(((d.mw_below_v >= 0) & (d.mw_below_v <= d.mw_offered + 1e-6)).all(), "0 ≤ mw_below_v ≤ mw_offered")
        nb = d[(d.F == 0) & (d.mw_below_v == 0) & (d.q_mwh > 0)]
        check((nb.r >= -0.01).all(), f"F = 0 and nothing offered below v: r ≥ −0.01 on {(nb.r >= -0.01).mean():.4%} "
                                     f"of {len(nb):,} (min {nb.r.min():.3f})")
        check((d.can_bind == ((d.F > 0) | (d.mw_below_v > 0))).all(), "can_bind = F > 0 or MW offered below v")
        rc = d[d.add_mw.notna()]
        check((rc.add_mw >= 0).all() and (rc.slope_local > 0).all(),
              f"re-cleared rows: add_mw ≥ 0, slope_local > 0 ({len(rc):,} rows)")
    for c in ("ES", "PT"):
        x = acc[acc.country == c]
        sh = (x.r >= -0.5).mean()
        check(len(x) > 0 and sh >= 0.98, f"accepted {c}: r ≥ −0.5 on {sh:.2%} of {len(x):,}")

    print("PASS" if not fails else f"FAIL: {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
