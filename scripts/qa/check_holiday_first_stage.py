#!/usr/bin/env python3
"""The just-identified IV pieces behind the holiday first stage and power (`iv_null`).

    .venv/bin/python scripts/qa/check_holiday_first_stage.py

On synthetic panels with two-way fixed effects, a sparse event instrument (non-zero on
5% of the dates, like a holiday dose), date-level shocks and a planted first stage π = 1:
  - the first-stage coefficient is within 3 standard errors of 1;
  - with β = 0, the mean se(β) under the null is within 20% of the standard deviation
    of the 2SLS estimate over the draws (so the power calculation is calibrated);
  - mde = 2.80 x se(β);
  - with two instruments (an Endesa split), each first stage recovers its own π.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from holiday_first_stage import codes_of, endesa_split, iv_null  # noqa: E402
from step_estimator import wdemean  # noqa: E402


def panel(rng: np.random.Generator, beta: float, n_dates: int = 300, n_units: int = 12) -> pd.DataFrame:
    dates = np.repeat(np.arange(n_dates), n_units)
    units = np.tile(np.arange(n_units), n_dates)
    group = np.where(units < 3, "ENDESA", "OTHER")
    event = rng.random(n_dates) < 0.05
    z = np.where(event[dates], rng.uniform(0.5, 1.5, len(dates)) * (units % 3 + 1), 0.0)
    fe = rng.normal(0, 3, n_units)[units] + rng.normal(0, 3, n_dates)[dates]
    x = 1.0 * z + fe + rng.normal(0, 1, len(dates)) + rng.normal(0, 1, n_dates)[dates]
    y = beta * x + fe + rng.normal(0, 2, len(dates)) + rng.normal(0, 2, n_dates)[dates]
    return pd.DataFrame({"unit": units.astype(str), "date": dates, "group": group, "x": x, "z": z, "y": y,
                         "t": (dates // 1).astype(str)})


def tsls(d: pd.DataFrame, codes: list) -> float:
    M = wdemean(d[["x", "z", "y"]].to_numpy(float), codes, np.ones(len(d)))
    return float((M[:, 1] @ M[:, 2]) / (M[:, 1] @ M[:, 0]))


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    rng = np.random.default_rng(7)
    d = panel(rng, beta=0.5)
    fe = codes_of(d.unit, d.t.astype(str) + "|" + (d.unit.astype(int) % 2).astype(str))
    r = iv_null(d, ["x"], ["z"], fe, {"date": d.date.to_numpy()}, "y")[0]
    check(abs(r["pi"] - 1) < 3 * r["se_pi_date"], f"first stage {r['pi']:.3f} (se {r['se_pi_date']:.3f}) near 1")
    check(abs(r["mde_date"] - 2.80 * r["se_beta_date"]) < 1e-12, "mde = 2.80 x se(beta)")

    est, ses = [], []
    for _ in range(150):
        d = panel(rng, beta=0.0)
        fe = codes_of(d.unit, d.t.astype(str) + "|" + (d.unit.astype(int) % 2).astype(str))
        est.append(tsls(d, fe))
        ses.append(iv_null(d, ["x"], ["z"], fe, {"date": d.date.to_numpy()}, "y")[0]["se_beta_date"])
    sd, mse = float(np.std(est)), float(np.mean(ses))
    check(abs(mse / sd - 1) < 0.2, f"se(beta) under the null {mse:.4f} vs sd over draws {sd:.4f}")

    d = panel(rng, beta=0.0)
    fe = codes_of(d.unit, d.t.astype(str) + "|" + (d.unit.astype(int) % 2).astype(str))
    xs, zs = endesa_split(d, "x", "z")
    rr = iv_null(d, xs, zs, fe, {"date": d.date.to_numpy()}, "y")
    for r in rr:
        check(abs(r["pi"] - 1) < 3 * r["se_pi_date"], f"{r['x']} on {r['z']}: pi {r['pi']:.3f} near 1")

    print(f"\n{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
