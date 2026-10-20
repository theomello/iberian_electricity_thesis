#!/usr/bin/env python3
"""The France-link step 2 tools, on synthetic data with a planted answer.

    .venv/bin/python scripts/qa/check_france_link_first_stage.py

  (a) `calibrate`: price = α_day + 3·RDf·(1 − p) + 1·RDf·p + noise, with day and month × hour
      effects → the ratio a/b within 3 se of 3;
  (b) `iv_ctrl`: x = 1·z + 2·w + e with z correlated with the control w → the first stage
      within 3 se of 1; y = w + u (β = 0) → se(β) under the null within 20% of the
      empirical sd of the IV estimate over 150 draws.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from france_link_first_stage import calibrate, iv_ctrl  # noqa: E402


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    rng = np.random.default_rng(11)
    days = pd.date_range("2020-01-01", periods=400, freq="D")
    d = pd.DataFrame({"date": np.repeat(days, 24), "hour": np.tile(np.arange(24), len(days))})
    d["month"] = d.date.dt.month
    d["RDf"] = rng.normal(20, 4, len(d))
    d["p"] = rng.uniform(0, 1, len(d))
    alpha = pd.Series(rng.normal(60, 15, len(days)), index=days)
    d["price"] = alpha.loc[d.date].to_numpy() + 3 * d.RDf * (1 - d.p) + 1 * d.RDf * d.p + rng.normal(0, 3, len(d))
    c = calibrate(d.rename(columns={"price": "price_es"}), rdf="RDf", p="p")
    check(abs(c["ratio"] - 3) < 3 * c["se_ratio"], f"(a) a {c['a']:.3f}, b {c['b']:.3f}, ratio {c['ratio']:.3f} "
                                                   f"(se {c['se_ratio']:.3f}), planted 3")

    # (b) iv_ctrl: a control correlated with the instrument is partialled out of x, z and y
    n, G = 4000, 200
    est, ses, pis, se_pis = [], [], [], []
    for k in range(150):
        r = np.random.default_rng(1000 + k)
        g = r.integers(0, G, n)
        w = r.normal(0, 1, n)
        z = 0.7 * w + r.normal(0, 1, n)
        x = 1.0 * z + 2.0 * w + r.normal(0, 1, n)
        y = 0.0 * x + w + r.normal(0, 1, n)
        df = pd.DataFrame({"x": x, "z": z, "w": w, "y": y, "fe": r.integers(0, 10, n)})
        res = iv_ctrl(df, ["x"], ["z"], ["w"], [df.fe.to_numpy()], {"g": g}, y="y")[0]
        pis.append(res["pi"])
        se_pis.append(res["se_pi_g"])
        ses.append(res["se_beta_g"])
        M = df[["x", "z", "w", "y"]].to_numpy() - df.groupby("fe")[["x", "z", "w", "y"]].transform("mean").to_numpy()
        W = M[:, [2]]
        R = M - W @ np.linalg.lstsq(W, M, rcond=None)[0]
        est.append((R[:, 1] @ R[:, 3]) / (R[:, 1] @ R[:, 0]))
    check(abs(np.mean(pis) - 1) < 3 * np.mean(se_pis), f"(b) first stage {np.mean(pis):.3f} (se {np.mean(se_pis):.3f}), planted 1")
    ratio = np.mean(ses) / np.std(est)
    check(abs(ratio - 1) < 0.2, f"(b) se(β) under the null {np.mean(ses):.4f} against the sd of the estimate "
                                f"{np.std(est):.4f} (ratio {ratio:.2f})")

    print("PASS" if not fails else f"FAIL: {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
