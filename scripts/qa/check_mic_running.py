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
  - no date after 2025-03-18 (the condition ends there);
  - accepted rows (≥ 4 hours cleared) have r ≥ −0.5 in at least 98% of Spanish and of
    Portuguese unit-days separately (a Portuguese unit priced at the Spanish price in
    split hours would fail).
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
    for c in ("ES", "PT"):
        x = acc[acc.country == c]
        sh = (x.r >= -0.5).mean()
        check(len(x) > 0 and sh >= 0.98, f"accepted {c}: r ≥ −0.5 on {sh:.2%} of {len(x):,}")

    print("PASS" if not fails else f"FAIL: {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
