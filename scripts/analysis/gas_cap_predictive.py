#!/usr/bin/env python3
"""Model code for the within-Iberia counterfactual (notes/rq-crisis-quantity.md, H8): sample, predictors, ridge with unit intercepts, baselines.

Imported by gas_cap_quantity_predictive_stage1.py and gas_cap_quantity_predictive_stage2.py; running it prints the sample.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_ife import em_factor  # noqa: E402
from gas_cap_quantity_b1 import CAP0, matrix, panel  # noqa: E402

T = ROOT / "outputs" / "tables"
FIT0, FIT1 = pd.Timestamp("2021-10-04"), pd.Timestamp("2022-06-06")
POST0 = pd.Timestamp("2022-06-20")
ORIGINS = (20, 24, 28, 32)
HORIZON = 4
LAMBDAS = (0.1, 1.0, 10.0)
VARIANTS = {
    "ES": {"gas_in": ["psv_bid", "eua_bid", "netload_fc", "temp_es"], "gas_out": ["eua_bid", "netload_fc", "temp_es"]},
    "IT": {"gas_in": ["psv_bid", "eua_bid", "temp_it"], "gas_out": ["eua_bid", "temp_it"]},
}


def load() -> dict:
    h = panel()
    W, thr = matrix(h, "run20")
    meta = h.drop_duplicates("unit").set_index("unit")
    ib = meta.iberia.reindex(W.index).to_numpy()
    firm = pd.Series(meta.firm.reindex(W.index).to_numpy())
    cols = W.columns
    e = pd.read_csv(T / "gas_cap_quantity_b1_ends.csv", parse_dates=["w"]).set_index("w")
    g = (e.full_run20 - e.none_run20).reindex(cols).to_numpy()
    cond = pd.read_parquet(T / "gas_cap_weekly_conditions.parquet").reindex(cols)
    assert not cond.isna().any().any(), "conditions must cover every matrix week"
    fit = np.flatnonzero((cols >= FIT0) & (cols <= FIT1))
    post = np.flatnonzero(cols >= POST0)
    return {"M": W.to_numpy(), "units": W.index.to_numpy(), "ib": ib, "firm": firm, "cols": cols, "g": g, "cond": cond, "fit": fit, "post": post}


def ridge_fit(Y: np.ndarray, X: np.ndarray, train: np.ndarray, lam: float) -> dict:
    """Unit intercepts free (within transformation over each unit's observed training weeks), common slopes, ridge on standardised X."""
    mu, sd = X[train].mean(axis=0), X[train].std(axis=0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    rows, ys, ybar, zbar = [], [], np.full(Y.shape[0], np.nan), np.zeros((Y.shape[0], X.shape[1]))
    for i in range(Y.shape[0]):
        o = train[~np.isnan(Y[i, train])]
        if len(o) < 3:
            continue
        ybar[i], zbar[i] = Y[i, o].mean(), Z[o].mean(axis=0)
        rows.append(Z[o] - zbar[i])
        ys.append(Y[i, o] - ybar[i])
    A, b = np.vstack(rows), np.concatenate(ys)
    beta = np.linalg.solve(A.T @ A + lam * len(b) * np.eye(A.shape[1]), A.T @ b)
    return {"beta": beta, "ybar": ybar, "zbar": zbar, "Z": Z}


def ridge_predict(fit: dict, test: np.ndarray) -> np.ndarray:
    """Predicted Y (units x len(test)); NaN for units without a fit."""
    return fit["ybar"][:, None] + (fit["Z"][test][None, :, :] - fit["zbar"][:, None, :]) @ fit["beta"]


def mean_only(Y: np.ndarray, train: np.ndarray, n_test: int) -> np.ndarray:
    yb = np.nanmean(Y[:, train], axis=1)
    return np.repeat(yb[:, None], n_test, axis=1)


def gsc_r0(Y: np.ndarray, ib: np.ndarray, train: np.ndarray, test: np.ndarray) -> np.ndarray:
    """Italy-based baseline (Xu 2017 at r = 0): the Italian two-way week effect plus each Iberian unit's own level fitted on the training weeks."""
    _, b, _ = em_factor(Y[~ib], 0)
    xi = b.ravel()
    c = np.nanmean(Y[:, train] - xi[train][None, :], axis=1)
    return c[:, None] + xi[test][None, :]


def clip01(p: np.ndarray) -> np.ndarray:
    return np.clip(p, 0.0, 1.0)


if __name__ == "__main__":
    s = load()
    print(f"{s['ib'].sum()} Iberian, {(~s['ib']).sum()} Italian units x {len(s['cols'])} weeks; {len(s['fit'])} fit weeks, {len(s['post'])} post weeks; "
          f"post weeks with g > 0: {int((s['g'][s['post']] > 0).sum())}")
