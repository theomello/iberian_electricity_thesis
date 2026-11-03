#!/usr/bin/env python3
"""Does a gas-price control repair the confounded recovery worlds? (notes/rq-crisis-quantity.md, H5, rules fixed before running)

    .venv/bin/python scripts/analysis/gas_cap_quantity_recovery_control.py [--reps 60] [--workers 4]

H4's data-generating process (S1 plus an Iberian-only response kappa * z_w to the standardised weekly MIBGAS price, share 0 = none).
Per draw: rho-hat without and with z_w as a regressor, at Xu's cross-validated r and at fixed r = 0..5.
Writes outputs/tables/gas_cap_quantity_recovery_control{,_summary}.csv.
"""
from __future__ import annotations

import os

for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[v] = "1"

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_ife import gsc, xu_cv  # noqa: E402
from gas_cap_quantity_b3_curve import slope  # noqa: E402
from gas_cap_quantity_recovery import DRIFT, base, real  # noqa: E402
from gas_cap_quantity_recovery_confound import panel_cols, zseries  # noqa: E402

T = ROOT / "outputs" / "tables"
CELLS = [(k, sg, sh, r0) for k in (0, 2) for (sg, sh) in ((+1, 0.5), (-1, 0.5), (+1, 0.05), (-1, 0.05), (+1, 0.0)) for r0 in (0.5, 1.0)]


def run_cell(args):
    ci, reps = args
    k, sign, share, rho0 = CELLS[ci]
    M, ib, pre, g = real()
    cols = panel_cols()
    fit_it, sd_it, y0, sd_ib, eta_pre = base(M, ib, pre, k)
    z = zseries(cols, pre)
    kappa = sign * np.sqrt(share * np.nanvar(eta_pre[pre]))
    rng = np.random.default_rng(20261105 + ci)
    Z = z[:, None]
    rows = []
    t0 = time.time()
    for rep in range(reps):
        Y = np.empty_like(M)
        Y[~ib] = fit_it + rng.normal(size=fit_it.shape) * sd_it[:, None]
        eff = np.where(~pre & ~np.isnan(g), (rho0 - 1) * np.nan_to_num(g), 0.0) + np.where(~pre, DRIFT, 0.0)
        Y[ib] = y0 + kappa * z + eff + rng.normal(size=y0.shape) * sd_ib[:, None]
        Y[np.isnan(M)] = np.nan
        rh = int(np.argmin(xu_cv(Y, ib, pre)))
        atts = [gsc(Y, ib, pre, r) for r in range(6)]
        u = [1 + slope(a, g, ~pre, None, False) for a in atts]
        c = [1 + slope(a, g, ~pre, Z, False) for a in atts]
        rows.append({"true_r": k, "sign": sign, "share": share, "rho0": rho0, "rep": rep, "r_hat": rh, "rho_u": u[rh], "rho_c": c[rh],
                     **{f"u_r{r}": u[r] for r in range(6)}, **{f"c_r{r}": c[r] for r in range(6)}})
        if (rep + 1) % 20 == 0 or rep == 0:
            print(f"cell {ci} (k={k}, sign={sign:+d}, share={share}, rho0={rho0}): {rep + 1}/{reps}, {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=60)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    with ProcessPoolExecutor(a.workers) as ex:
        out = [r for rows in ex.map(run_cell, [(i, a.reps) for i in range(len(CELLS))]) for r in rows]
    D = pd.DataFrame(out)
    D.to_csv(T / "gas_cap_quantity_recovery_control.csv", index=False)
    S = []
    for (k, sg, sh, r0), d in D.groupby(["true_r", "sign", "share", "rho0"]):
        bu, bc = (d.rho_u - r0), (d.rho_c - r0)
        S.append({"true_r": k, "sign": sg, "share": sh, "rho0": r0, "reps": len(d), "bias_u": bu.mean(), "bias_c": bc.mean(),
                  "sd_u": d.rho_u.std(), "sd_c": d.rho_c.std(), "sd_ratio": d.rho_c.std() / d.rho_u.std(),
                  "rmse_u": float(np.sqrt((bu ** 2).mean())), "rmse_c": float(np.sqrt((bc ** 2).mean())),
                  "bias_c_r0": float((d.c_r0 - r0).mean()), "bias_c_r5": float((d.c_r5 - r0).mean())})
    S = pd.DataFrame(S)
    S.to_csv(T / "gas_cap_quantity_recovery_control_summary.csv", index=False)
    with pd.option_context("display.width", 240):
        print(S.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
