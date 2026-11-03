#!/usr/bin/env python3
"""Recovery simulation for B3 (notes/rq-crisis-quantity.md, H2, rules fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_quantity_recovery.py [--reps 100] [--workers 4]

Synthetic panels built on the real in-money weekly run20 matrix (missing cells, g_w, units kept): Italian block and Iberian
counterfactual from a rank-k factor model (k = 0 or 2), scenario S1 (Iberia follows Italy's week path) or S2 (plus its own
weekly path eta, resampled in blocks after the cap), a planted effect (rho0 - 1) * g_w and a drift of +0.13 after the cap.
For each draw: rho-hat = 1 + b of B3 at Xu's cross-validated r and at fixed r = 0..5.
Writes outputs/tables/gas_cap_quantity_recovery{,_summary}.csv.
"""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_ife import em_factor, gsc, xu_cv  # noqa: E402
from gas_cap_quantity_b1 import CAP0, matrix, panel  # noqa: E402
from gas_cap_quantity_b3_curve import slope  # noqa: E402

T = ROOT / "outputs" / "tables"
DRIFT = 0.13
BLOCK = 4
CELLS = list(product((0, 2), ("S1", "S2"), (0.5, 1.0)))


def real():
    h = panel()
    W, _ = matrix(h, "run20")
    ib = h.drop_duplicates("unit").set_index("unit").iberia.reindex(W.index).to_numpy()
    cols = W.columns
    e = pd.read_csv(T / "gas_cap_quantity_b1_ends.csv", parse_dates=["w"]).set_index("w")
    g = (e.full_run20 - e.none_run20).reindex(cols).to_numpy()
    return W.to_numpy(), ib, cols < CAP0, g


def base(M, ib, pre, k):
    IT = M[~ib]
    a, b, LF = em_factor(IT, k)
    fit_it = a + b + LF
    sd_it = np.sqrt(np.nanmean((IT - fit_it) ** 2, axis=1))
    F = (np.linalg.svd(LF, full_matrices=False)[2][:k].T * np.sqrt(M.shape[1])) if k else np.zeros((M.shape[1], 0))
    xi = b.ravel()
    Zall = np.column_stack([np.ones(len(xi)), F])
    y0, sd_ib = [], []
    for y in M[ib]:
        o = ~np.isnan(y) & pre
        c = np.linalg.lstsq(Zall[o], y[o] - xi[o], rcond=None)[0]
        y0.append(xi + Zall @ c)
        sd_ib.append(np.std(y[o] - xi[o] - Zall[o] @ c))
    y0 = np.array(y0)
    eta_pre = np.nanmean(M[ib], axis=0) - y0.mean(axis=0)
    return fit_it, sd_it, y0, np.array(sd_ib), eta_pre


def simulate(M, ib, pre, g, B, scen, rho0, rng):
    fit_it, sd_it, y0, sd_ib, eta_pre = B
    T_ = M.shape[1]
    Y = np.empty_like(M)
    Y[~ib] = fit_it + rng.normal(size=fit_it.shape) * sd_it[:, None]
    eta = np.zeros(T_)
    if scen == "S2":
        e0 = eta_pre[pre] - np.nanmean(eta_pre[pre])
        eta[pre] = e0
        n_post = int((~pre).sum())
        starts = rng.integers(0, len(e0) - BLOCK + 1, size=int(np.ceil(n_post / BLOCK)))
        eta[~pre] = np.concatenate([e0[s:s + BLOCK] for s in starts])[:n_post]
    eff = np.where(~pre & ~np.isnan(g), (rho0 - 1) * np.nan_to_num(g), 0.0) + np.where(~pre, DRIFT, 0.0)
    Y[ib] = y0 + eta + eff + rng.normal(size=y0.shape) * sd_ib[:, None]
    Y[np.isnan(M)] = np.nan
    return Y


def run_cell(args):
    ci, reps = args
    k, scen, rho0 = CELLS[ci]
    M, ib, pre, g = real()
    B = base(M, ib, pre, k)
    rng = np.random.default_rng(20261103 + ci)
    rows = []
    for rep in range(reps):
        Y = simulate(M, ib, pre, g, B, scen, rho0, rng)
        rh = int(np.argmin(xu_cv(Y, ib, pre)))
        rho = [1 + slope(gsc(Y, ib, pre, r), g, ~pre, None, False) for r in range(6)]
        rows.append({"true_r": k, "scenario": scen, "rho0": rho0, "rep": rep, "r_hat": rh, "rho_cv": rho[rh],
                     **{f"rho_r{r}": rho[r] for r in range(6)}})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=100)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cells", type=int, default=len(CELLS), help="run the first n cells (timing)")
    a = ap.parse_args()
    idx = list(range(a.cells))
    with ProcessPoolExecutor(a.workers) as ex:
        out = [r for rows in ex.map(run_cell, [(i, a.reps) for i in idx]) for r in rows]
    D = pd.DataFrame(out)
    D.to_csv(T / "gas_cap_quantity_recovery.csv", index=False)
    S = []
    for (k, sc, r0), d in D.groupby(["true_r", "scenario", "rho0"]):
        row = {"true_r": k, "scenario": sc, "rho0": r0, "reps": len(d), "share_r_hat_true": float((d.r_hat == k).mean()),
               "bias_cv": float((d.rho_cv - r0).mean()), "sd_cv": float(d.rho_cv.std()),
               "rmse_cv": float(np.sqrt(((d.rho_cv - r0) ** 2).mean()))}
        for r in range(6):
            row[f"bias_r{r}"] = float((d[f"rho_r{r}"] - r0).mean())
        row["slope_in_r"] = float(np.polyfit(range(6), [d[f"rho_r{r}"].mean() for r in range(6)], 1)[0])
        S.append(row)
    S = pd.DataFrame(S)
    S.to_csv(T / "gas_cap_quantity_recovery_summary.csv", index=False)
    with pd.option_context("display.width", 220):
        print(S.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
