#!/usr/bin/env python3
"""The own-wind quantity panel and step 1's tools.

    .venv/bin/python scripts/qa/check_own_wind_quantity.py

Design `docs/specs/2026-10-21-own-wind-quantity-test-design.md`; script
`analysis/own_wind_quantity_test.py`. Checks:
  - if the panel exists: on every row, other generation + own wind + generic units equals the
    holiday quantity panel's generation, in total and by leg, within 0.01 MW; Wdev is finite;
  - the two-stage fit recovers planted book balancing (b_W −0.5, b_P 0) and Nash (b_P −40) on a
    synthetic panel where own wind is endogenous, through the same effects and controls as the
    real run, while OLS on the same data is off;
  - the standard error of b_P under b_P = 0 (from the restricted model's residual) is within 10%
    of the two-stage se when b_P is in fact 0;
  - slope groups (design §8): thirds of each firm's own hours by 1/slope, ordered and balanced;
    the three instruments Wdev × D_k sum to Wdev; and when the wind's response to Wdev falls in
    steep hours (1.2, 1.0, 0.4 by group, as in the data), they recover book balancing and Nash.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
for s in ("lib", "analysis"):
    sys.path.insert(0, str(ROOT / "scripts" / s))
from own_wind_quantity_test import PANEL  # noqa: E402

QPANEL = ROOT / "outputs/tables/holiday_quantity_panel.parquet"


def synthetic(seed: int = 3) -> pd.DataFrame:
    """5 groups × 260 weekdays × 24 hours: Wdev drives own wind W_s, whose error u also enters
    the outcome's error (so OLS is biased); slope, s, retail and three forecasts vary."""
    rng = np.random.default_rng(seed)
    idx = pd.MultiIndex.from_product([list("ABCDE"), pd.bdate_range("2021-01-04", periods=260), range(24)],
                                     names=["group", "date", "hour"])
    d = pd.DataFrame(index=idx).reset_index()
    n = len(d)
    gi = pd.factorize(d.group)[0]
    d["F_wind"], d["F_solar"], d["F_demand"] = rng.normal(8, 3, n), rng.normal(5, 2, n), rng.normal(28, 4, n)
    d["slope"] = rng.uniform(20, 200, n)
    d["inv_slope"] = 1 / d.slope
    d["s"] = rng.uniform(0, 80, n)
    d["retail"] = -rng.normal(3000, 300, n)
    d["Wdev"] = rng.normal(0, 300, n)
    u = rng.normal(0, 150, n)
    d["W_s"] = 1000 + 300 * gi + 0.9 * d.Wdev + 60 * d.F_wind + u
    d["P_W"] = d.W_s * d.inv_slope
    d["Wdev_inv"] = d.Wdev * d.inv_slope
    day = pd.Series(rng.normal(0, 400, d.date.nunique()), index=d.date.unique())
    d["e"] = rng.normal(0, 200, n) + d.date.map(day).to_numpy() + 2.0 * u + 30 * d.F_demand
    return d


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    # the two-stage fit and the se under the null
    try:
        from own_wind_quantity_test import fit_iv, se_null_iv, prep, controls_for
    except ImportError as e:
        check(False, f"step 1 tools missing ({e})")
    else:
        d = synthetic()
        ctrl = controls_for(d)
        sbar = 40.0
        d["y_bb"] = -0.5 * d.W_s + d.e
        d["y_nash"] = -sbar * d.P_W + d.e
        d["y_0"] = d.e
        for y, want_w, want_p in (("y_bb", -0.5, 0.0), ("y_nash", 0.0, -sbar)):
            r = fit_iv(d, y, ["W_s", "P_W"], ["Wdev", "Wdev_inv"], ctrl)
            ok = all(abs(r[k][0] - w) < 3 * r[k][1] for k, w in (("W_s", want_w), ("P_W", want_p)))
            check(ok, f"{y}: b_W {r['W_s'][0]:+.3f} ({r['W_s'][1]:.3f}) want {want_w:+.1f}, "
                      f"b_P {r['P_W'][0]:+.2f} ({r['P_W'][1]:.2f}) want {want_p:+.0f}")
        M = prep(d, ["y_bb", "W_s", "P_W"] + ctrl)
        b_ols = np.linalg.lstsq(M[:, 1:], M[:, 0], rcond=None)[0]
        check(abs(b_ols[0] + 0.5) > 0.3, f"OLS on the same data is biased: b_W {b_ols[0]:+.3f} (truth −0.5)")
        r0 = fit_iv(d, "y_0", ["W_s", "P_W"], ["Wdev", "Wdev_inv"], ctrl)
        M = prep(d, ["y_0", "W_s", "P_W", "Wdev", "Wdev_inv"] + ctrl)
        cl = d.date.dt.strftime("%Y%m%d").to_numpy()
        sn = se_null_iv(M[:, 0], M[:, 1:3], M[:, 3:5], M[:, 5:], cl, 1)
        check(abs(sn / r0["P_W"][1] - 1) < 0.10,
              f"se(b_P) under the null {sn:.3f} against the fitted se {r0['P_W'][1]:.3f} at b_P = 0 (within 10%)")

    # slope groups: thirds of each firm's hours by 1/slope, instruments that let the response vary
    try:
        from own_wind_quantity_test import group_instruments, controls_for
    except ImportError as e:
        check(False, f"slope-group tools missing ({e})")
    else:
        d = synthetic(seed=5)
        inst, dums = group_instruments(d)
        ordered = all((x.groupby("slope_group").inv_slope.max().to_numpy()[:-1]
                       <= x.groupby("slope_group").inv_slope.min().to_numpy()[1:]).all() for _, x in d.groupby("group"))
        sizes = d.groupby(["group", "slope_group"]).size()
        check(inst == ["Wdev_g1", "Wdev_g2", "Wdev_g3"] and dums == ["D_2", "D_3"] and ordered
              and sizes.max() - sizes.min() <= 1 and np.allclose(d[inst].sum(axis=1), d.Wdev),
              f"slope groups: thirds within each firm, ordered by 1/slope, sizes {sizes.min()}–{sizes.max()}, "
              "instruments sum to Wdev")
        resp = np.array([0.0, 1.2, 1.0, 0.4])[d.slope_group.to_numpy()]
        d["W_s"] = d.W_s + (resp - 0.9) * d.Wdev
        d["P_W"] = d.W_s * d.inv_slope
        d["y_bb"], d["y_nash"] = -0.5 * d.W_s + d.e, -40.0 * d.P_W + d.e
        ctrl = controls_for(d) + dums
        for y, want_w, want_p in (("y_bb", -0.5, 0.0), ("y_nash", 0.0, -40.0)):
            r = fit_iv(d, y, ["W_s", "P_W"], inst, ctrl)
            ok = all(abs(r[k][0] - w) < 3 * r[k][1] for k, w in (("W_s", want_w), ("P_W", want_p)))
            check(ok, f"slope-group instruments, response 1.2/1.0/0.4, {y}: b_W {r['W_s'][0]:+.3f} ({r['W_s'][1]:.3f}), "
                      f"b_P {r['P_W'][0]:+.2f} ({r['P_W'][1]:.2f}); want {want_w:+.1f}, {want_p:+.0f}")

    # the panel adds up
    if PANEL.exists():
        p = pd.read_parquet(PANEL)
        q = pd.read_parquet(QPANEL, columns=["group", "date", "hour", "gen", "gen_auction", "gen_bilateral"])
        m = p.drop(columns=["gen", "gen_auction", "gen_bilateral"], errors="ignore").merge(
            q, on=["group", "date", "hour"], how="left", validate="1:1")
        gaps = {"total": (m.G_other + m.W_s + m.generic - m.gen).abs().max(),
                "auction": (m.G_other_auction + m.W_s_auction + m.generic_auction - m.gen_auction).abs().max(),
                "bilateral": (m.G_other_bilateral + m.W_s_bilateral + m.generic_bilateral - m.gen_bilateral).abs().max()}
        check(max(gaps.values()) < 0.01, "other generation + own wind + generic = holiday gen, "
              + ", ".join(f"{k} max gap {v:.4f} MW" for k, v in gaps.items()) + f" ({len(m):,} rows)")
        check(bool(np.isfinite(p.Wdev).all() and np.isfinite(p.Wdev_inv).all()),
              f"Wdev finite on every row ({int((~np.isfinite(p.Wdev)).sum())} not)")
    else:
        print(f"  (panel {PANEL.relative_to(ROOT)} not built: panel checks skipped)")

    print("FAIL: " + str(len(fails)) if fails else "all checks pass")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
