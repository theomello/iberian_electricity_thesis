#!/usr/bin/env python3
"""The regression-discontinuity tools in `lib/rd.py`, on synthetic data with a planted answer.

    .venv/bin/python scripts/qa/check_rd.py

  (a) y = 1 + 0.5 r + 2·1[r ≥ 0] + N(0, 1), 20,000 draws in 2,000 clusters:
      rd_jump recovers 2 within 3 se, p < 0.001;
  (b) y = 1[r ≥ 0] exactly: tau = 1, se ≈ 0;
  (c) r uniform on [−3, 3] with 1.5× the density right of 0, n = 20,000:
      mccrary's theta within 3 se of ln 1.5, p < 0.01;
  (d) r uniform on [−3, 3], no break: p > 0.01.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from rd import mccrary, rd_jump  # noqa: E402


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    rng = np.random.default_rng(20261020)
    n = 20_000
    r = rng.uniform(-3, 3, n)
    cl = rng.integers(0, 2_000, n)
    d = (r >= 0).astype(float)
    y = 1 + 0.5 * r + 2 * d + rng.normal(0, 1, n)
    a = rd_jump(y, r, cl, h=2.0)
    check(abs(a["tau"] - 2) < 3 * a["se"] and a["p"] < 1e-3,
          f"(a) tau {a['tau']:.3f} se {a['se']:.3f} p {a['p']:.2g} n {a['n_left']}/{a['n_right']}")
    b = rd_jump(d, r, cl, h=2.0)
    check(abs(b["tau"] - 1) < 1e-9 and b["se"] < 1e-6, f"(b) tau {b['tau']:.6f} se {b['se']:.2g}")

    # (c): left half at density 1, right half at 1.5 (draw 1.5x as many on the right)
    left = rng.uniform(-3, 0, 8_000)
    right = rng.uniform(0, 3, 12_000)
    c = mccrary(np.concatenate([left, right]), h=2.0, b=0.05)
    check(abs(c["theta"] - np.log(1.5)) < 3 * c["se"] and c["p"] < 0.01,
          f"(c) theta {c['theta']:.3f} (ln 1.5 = {np.log(1.5):.3f}) se {c['se']:.3f} p {c['p']:.2g}")
    e = mccrary(rng.uniform(-3, 3, n), h=2.0, b=0.05)
    check(e["p"] > 0.01, f"(d) theta {e['theta']:.3f} se {e['se']:.3f} p {e['p']:.2f}")

    print("PASS" if not fails else f"FAIL: {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
