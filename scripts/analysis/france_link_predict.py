#!/usr/bin/env python3
"""Step 1 of the France-link design: does the line's state follow from French conditions and
published capacity?

    .venv/bin/python scripts/analysis/france_link_predict.py [--split]

Spec `docs/specs/2026-10-20-france-link-design.md` §4 step 1. Reads
`outputs/tables/france_link_hours.parquet` (`build/build_france_link.py`).

For each state (open, import-full, export-full):
  F_excluded  a linear probability model of the state on the excluded predictors (cap_imp,
              cap_exp, fr_load_fc, fr_nuc_lag, GW), demeaned within month × hour cells,
              errors clustered by date; F = Wald / 4
  F_pred      the same with the out-of-sample prediction p_state as the one regressor (t²)
  corr_oos    corr(p_state, state), each year predicted from a fit on the others
  auc_oos     the area under the ROC curve of p_state
Samples: all (2018-01 → 2025-09) and the estimation window (2019-01 → 2025-09); also by year.

STOP RULE (spec §4 step 1): for the open state, F_excluded below 20 or corr_oos below 0.3.
Writes outputs/tables/france_link_predict.csv.

--split (plan Task 6, note §1.5): the prediction with Iberian forecasts added, split into the
part Iberian conditions give (p_open_ib, a control) and what France and capacity add (z_open,
the instrument). Reports corr(p_open_full, open), the F of open on z_open with p_open_ib as a
control (month × hour cells, date clusters) and the partial correlation; stop if the first is
below 0.3 or the F below 20 (fixed before the run). Writes france_link_predict_split.csv.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
T = ROOT / "outputs/tables"
PRED = ["cap_imp", "cap_exp", "fr_load_fc", "fr_nuc_lag"]
STATES = ["open", "import_full", "export_full"]


def demean(M: np.ndarray, cells: np.ndarray) -> np.ndarray:
    _, g = np.unique(cells, return_inverse=True)
    s = np.zeros((g.max() + 1, M.shape[1]))
    np.add.at(s, g, M)
    return M - (s / np.bincount(g)[:, None])[g]


def wald_f(y: np.ndarray, X: np.ndarray, cells: np.ndarray, cl: np.ndarray, test: list[int] | None = None) -> float:
    """Wald F on the coefficients `test` (all by default) of a regression within cells, CR1 by cl."""
    Z = demean(np.column_stack([y, X]), cells)
    yd, Xd = Z[:, 0], Z[:, 1:]
    A = np.linalg.inv(Xd.T @ Xd)
    b = A @ (Xd.T @ yd)
    e = yd - Xd @ b
    _, g = np.unique(cl, return_inverse=True)
    s = np.zeros((g.max() + 1, Xd.shape[1]))
    np.add.at(s, g, Xd * e[:, None])
    G, n, k = g.max() + 1, len(yd), Xd.shape[1]
    V = G / (G - 1) * (n - 1) / (n - k) * A @ (s.T @ s) @ A
    t = list(range(k)) if test is None else test
    bt = b[t]
    return float(bt @ np.linalg.solve(V[np.ix_(t, t)], bt) / len(t))


def auc(p: np.ndarray, y: np.ndarray) -> float:
    r = pd.Series(p).rank().to_numpy()
    n1, n0 = y.sum(), (1 - y).sum()
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def stats(h: pd.DataFrame, label: str) -> list[dict]:
    h = h.dropna(subset=PRED + ["p_open"])
    cells = (h.month * 100 + h.hour).to_numpy()
    cl = h.date.dt.strftime("%Y%m%d").to_numpy()
    rows = []
    for s in STATES:
        y = (h.state == s).to_numpy(float)
        p = h[f"p_{s}"].to_numpy()
        rows.append({"sample": label, "state": s, "n": len(h), "share": y.mean(),
                     "F_excluded": wald_f(y, h[PRED].to_numpy() / 1000.0, cells, cl),
                     "F_pred": wald_f(y, p[:, None], cells, cl),
                     "corr_oos": float(np.corrcoef(p, y)[0, 1]), "auc_oos": auc(p, y)})
    return rows


def split_stats(h: pd.DataFrame, label: str) -> dict:
    h = h.dropna(subset=["z_open", "p_open_ib"])
    y = (h.state == "open").to_numpy(float)
    cells = (h.month * 100 + h.hour).to_numpy()
    cl = h.date.dt.strftime("%Y%m%d").to_numpy()
    X = h[["z_open", "p_open_ib"]].to_numpy()
    Z = demean(np.column_stack([y, X]), cells)
    ry = Z[:, 0] - Z[:, 2] * (Z[:, 2] @ Z[:, 0]) / (Z[:, 2] @ Z[:, 2])
    rz = Z[:, 1] - Z[:, 2] * (Z[:, 2] @ Z[:, 1]) / (Z[:, 2] @ Z[:, 2])
    return {"sample": label, "n": len(h), "share_open": y.mean(),
            "corr_full": float(np.corrcoef(h.p_open_full, y)[0, 1]),
            "corr_french_only": float(np.corrcoef(h.p_open, y)[0, 1]),
            "F_z_given_ib": wald_f(y, X, cells, cl, test=[0]),
            "partial_corr_z": float(np.corrcoef(ry, rz)[0, 1]),
            "sd_z": float(h.z_open.std()), "sd_ib": float(h.p_open_ib.std())}


def run_split(h: pd.DataFrame) -> int:
    rows = [split_stats(h, "2019-01 → 2025-09")] + [split_stats(g, str(y)) for y, g in h.groupby("year") if y >= 2019]
    rows.append(split_stats(h[h.year != 2022], "without 2022"))
    out = pd.DataFrame(rows)
    out.to_csv(T / "france_link_predict_split.csv", index=False)
    with pd.option_context("display.width", 160, "display.float_format", "{:.3f}".format):
        print(out.to_string(index=False))
    m = out.iloc[0]
    stops = {f"corr(p_open_full, open) {m.corr_full:.3f} < 0.3": m.corr_full < 0.3,
             f"F of open on z_open given p_open_ib {m.F_z_given_ib:.1f} < 20": m.F_z_given_ib < 20}
    for k, v in stops.items():
        print(f"  {'STOP' if v else 'ok  '} {k}")
    print(f"stop rule (split): {'STOP' if any(stops.values()) else 'CONTINUE'}")
    return 0


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--split", action="store_true")
    args = ap.parse_args()
    h = pd.read_parquet(T / "france_link_hours.parquet")
    h["date"] = pd.to_datetime(h.date)
    if args.split:
        return run_split(h)
    rows = stats(h, "2018-01 → 2025-09") + stats(h[h.date >= "2019-01-01"], "2019-01 → 2025-09")
    for y, g in h.groupby("year"):
        rows += stats(g, str(y))
    out = pd.DataFrame(rows)
    out.to_csv(T / "france_link_predict.csv", index=False)
    with pd.option_context("display.width", 140, "display.float_format", "{:.3f}".format):
        print(out.to_string(index=False))
    main_ = out[(out["sample"] == "2019-01 → 2025-09") & (out.state == "open")].iloc[0]
    stops = {f"open: F on the excluded predictors {main_.F_excluded:.1f} < 20": main_.F_excluded < 20,
             f"open: out-of-sample corr {main_.corr_oos:.3f} < 0.3": main_.corr_oos < 0.3}
    for k, v in stops.items():
        print(f"  {'STOP' if v else 'ok  '} {k}")
    print(f"stop rule (step 1): {'STOP' if any(stops.values()) else 'CONTINUE'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
