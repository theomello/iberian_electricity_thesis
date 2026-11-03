#!/usr/bin/env python3
"""Recovery simulation with a dose-correlated confound (notes/rq-crisis-quantity.md, H4, rules fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_quantity_recovery_confound.py [--reps 60] [--workers 4]

H2's data-generating process, scenario S1, plus an Iberian-only response kappa * z_w to the weekly MIBGAS price (z standardised on the
pre-cap weeks), kappa = sign * sqrt(share * var(eta_pre)). Writes outputs/tables/gas_cap_quantity_recovery_confound{,_summary}.csv.
"""
from __future__ import annotations

import os

for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[v] = "1"

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_ife import gsc, xu_cv  # noqa: E402
from gas_cap_quantity_b1 import matrix, panel  # noqa: E402
from gas_cap_quantity_b3_checks import weekly_gas  # noqa: E402
from gas_cap_quantity_b3_curve import slope  # noqa: E402
from gas_cap_quantity_recovery import DRIFT, base, real  # noqa: E402

T = ROOT / "outputs" / "tables"
CELLS = list(product((0, 2), (+1, -1), (0.5, 0.05), (0.5, 1.0)))  # true r, sign, share of eta_pre variance, rho0


def zseries(cols, pre):
    m = pd.Series(weekly_gas(cols)[:, 0], index=cols).interpolate(limit_direction="both")
    return ((m - m[pre].mean()) / m[pre].std()).to_numpy()


def run_cell(args):
    ci, reps = args
    k, sign, share, rho0 = CELLS[ci]
    M, ib, pre, g = real()
    cols = panel_cols()
    B = base(M, ib, pre, k)
    fit_it, sd_it, y0, sd_ib, eta_pre = B
    z = zseries(cols, pre)
    kappa = sign * np.sqrt(share * np.nanvar(eta_pre[pre]))
    post_obs = ~pre & ~np.isnan(g)
    corr = float(np.corrcoef(z[post_obs], g[post_obs])[0, 1])
    rng = np.random.default_rng(20261104 + ci)
    rows = []
    t0 = time.time()
    for rep in range(reps):
        Y = np.empty_like(M)
        Y[~ib] = fit_it + rng.normal(size=fit_it.shape) * sd_it[:, None]
        eff = np.where(~pre & ~np.isnan(g), (rho0 - 1) * np.nan_to_num(g), 0.0) + np.where(~pre, DRIFT, 0.0)
        Y[ib] = y0 + kappa * z + eff + rng.normal(size=y0.shape) * sd_ib[:, None]
        Y[np.isnan(M)] = np.nan
        rh = int(np.argmin(xu_cv(Y, ib, pre)))
        rho = [1 + slope(gsc(Y, ib, pre, r), g, ~pre, None, False) for r in range(6)]
        rows.append({"true_r": k, "sign": sign, "share": share, "rho0": rho0, "rep": rep, "r_hat": rh, "rho_cv": rho[rh], "corr_z_dose": corr,
                     **{f"rho_r{r}": rho[r] for r in range(6)}})
        if (rep + 1) % 10 == 0 or rep == 0:
            print(f"cell {ci} (k={k}, sign={sign:+d}, share={share}, rho0={rho0}): {rep + 1}/{reps} draws, {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    return rows


def panel_cols():
    W, _ = matrix(panel(), "run20")
    return W.columns


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=60)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cells", type=int, default=len(CELLS))
    a = ap.parse_args()
    with ProcessPoolExecutor(a.workers) as ex:
        out = [r for rows in ex.map(run_cell, [(i, a.reps) for i in range(a.cells)]) for r in rows]
    D = pd.DataFrame(out)
    D.to_csv(T / "gas_cap_quantity_recovery_confound.csv", index=False)
    S = []
    for (k, sg, sh, r0), d in D.groupby(["true_r", "sign", "share", "rho0"]):
        row = {"true_r": k, "sign": sg, "share": sh, "rho0": r0, "reps": len(d), "corr_z_dose": float(d.corr_z_dose.iloc[0]),
               "share_r_hat_true": float((d.r_hat == k).mean()), "bias_cv": float((d.rho_cv - r0).mean()),
               "sd_cv": float(d.rho_cv.std())}
        for r in range(6):
            row[f"bias_r{r}"] = float((d[f"rho_r{r}"] - r0).mean())
        row["fall_r0_to_r5"] = row["bias_r0"] - row["bias_r5"]
        S.append(row)
    S = pd.DataFrame(S)
    S.to_csv(T / "gas_cap_quantity_recovery_confound_summary.csv", index=False)
    with pd.option_context("display.width", 240):
        print(S.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
