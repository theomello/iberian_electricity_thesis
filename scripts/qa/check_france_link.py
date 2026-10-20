#!/usr/bin/env python3
"""The France line's state by hour, and its prediction leaving each year out.

    .venv/bin/python scripts/qa/check_france_link.py

  (a') `fit_loyo_mn`, a multinomial logit, recovers a middle category's probability (> 0.95)
      and never uses a year's own labels (relabelling year 2 leaves year 2's predictions
      unchanged);
  (a'') with `hold`, the same leave-one-year-out fits predict with columns replaced: hold =
      the data gives the same predictions; a predictor held at its mean no longer moves them;
      a year's own labels never enter;
  (b) `outputs/tables/france_link_hours.parquet` (`build/build_france_link.py`): one state
      per row; the Spanish and French prices are equal (≤ €0.01) in ≥ 90% of open hours and
      differ in ≥ 90% of full hours; the nuclear proxy for 2022-07-15 is the mean of RTE's
      daily nuclear output on 2022-07-07 … 2022-07-13; predictions lie in [0, 1];
      z_open = p_open_full − p_open_ib (the split, from 2019).
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "build"))
from build_france_link import OUT, fit_loyo_mn  # noqa: E402


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    rng = np.random.default_rng(7)
    n = 6000
    # (a') the multinomial version: a middle category likely when |x| is small
    m = pd.DataFrame({"year": np.repeat([1, 2], n // 2), "month": rng.integers(1, 13, n),
                      "hour": rng.integers(0, 24, n), "x": rng.normal(0, 1, n)})
    eta = np.column_stack([np.zeros(n), -1 + 2.5 * m.x, -1 - 2.5 * m.x])   # mid, up, down
    pr = np.exp(eta) / np.exp(eta).sum(axis=1, keepdims=True)
    u = rng.uniform(size=n)
    m["cat"] = np.where(u < pr[:, 0], "mid", np.where(u < pr[:, 0] + pr[:, 1], "up", "down"))
    P = fit_loyo_mn(m, "cat", ["x"], base="mid")
    cm = min(np.corrcoef(P.loc[m.year == k, "mid"], pr[m.year == k, 0])[0, 1] for k in (1, 2))
    check(cm > 0.95, f"(a') multinomial: corr(P(mid), truth) {cm:.3f} (a middle state a linear logit misses)")
    g = m.copy()
    g.loc[g.year == 2, "cat"] = g.loc[g.year == 2, "cat"].map({"mid": "up", "up": "down", "down": "mid"})
    Q = fit_loyo_mn(g, "cat", ["x"], base="mid")
    dd = float((Q.loc[m.year == 2] - P.loc[m.year == 2]).abs().max().max())
    check(dd < 1e-9, f"(a') relabelling year 2 moves year 2's predictions by {dd:.2g}")

    # (a'') holding predictors: the same fits, some columns replaced
    m["x2"] = rng.normal(0, 1, n)
    same = m[["x", "x2"]].copy()
    P2, H2 = fit_loyo_mn(m, "cat", ["x", "x2"], base="mid", hold=same)
    check(float((P2 - H2).abs().max().max()) < 1e-12, "(a'') hold = the data: P_hold = P")
    held = m[["x", "x2"]].copy()
    held["x"] = m.x.mean()
    _, H3 = fit_loyo_mn(m, "cat", ["x", "x2"], base="mid", hold=held)
    cx = abs(np.corrcoef(H3["mid"], m.x)[0, 1])
    check(cx < 0.05, f"(a'') x held at its mean: |corr(P_hold, x)| {cx:.3f}")
    g2 = g.copy()
    g2["x2"] = m.x2
    _, H4 = fit_loyo_mn(g2, "cat", ["x", "x2"], base="mid", hold=held)
    d4 = float((H4.loc[m.year == 2] - H3.loc[m.year == 2]).abs().max().max())
    check(d4 < 1e-9, f"(a'') relabelling year 2 moves year 2's P_hold by {d4:.2g}")

    if not OUT.exists():
        print(f"  FAIL {OUT.relative_to(ROOT)} missing\nFAIL: {len(fails) + 1}")
        return 1
    h = pd.read_parquet(OUT)
    check(h.state.isin(["open", "import_full", "export_full"]).all(), "one state per row")
    op = h[h.state == "open"]
    fu = h[h.state != "open"]
    a, b = (op.gap.abs() <= 0.01).mean(), (fu.gap.abs() > 0.01).mean()
    check(a >= 0.90, f"open hours: ES = FR price on {a:.1%} of {len(op):,}")
    check(b >= 0.90, f"full hours: ES ≠ FR price on {b:.1%} of {len(fu):,}")
    r = pd.read_parquet(ROOT / "data/rte/eco2mix_national.parquet", columns=["utc", "nucleaire"])
    daily = r.groupby(r.utc.dt.tz_convert(None).dt.normalize()).nucleaire.mean()
    want = daily.loc["2022-07-07":"2022-07-13"].mean()
    got = h.loc[h.date == pd.Timestamp("2022-07-15"), "fr_nuc_lag"].iloc[0]
    check(abs(got - want) <= 1, f"fr_nuc_lag 2022-07-15 {got:,.0f} against {want:,.0f}")
    pc = ["p_open", "p_import_full", "p_export_full"]
    ok = h[pc].notna().all(axis=1)
    check(h.loc[ok, pc].stack().between(0, 1).all() and ok.mean() > 0.999,
          f"predictions in [0, 1] ({int((~ok).sum())} hours without predictors)")
    tot = h.loc[ok, pc].sum(axis=1)
    check(((tot - 1).abs() < 1e-9).all(), "the three predictions sum to 1 (one multinomial model)")
    sp = h.dropna(subset=["z_open"]) if "z_open" in h else h.iloc[:0]
    check(len(sp) > 50_000 and float((sp.z_open - (sp.p_open_full - sp.p_open_ib)).abs().max()) < 1e-12,
          f"split: z_open = p_open_full − p_open_ib on {len(sp):,} hours")
    print("PASS" if not fails else f"FAIL: {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
