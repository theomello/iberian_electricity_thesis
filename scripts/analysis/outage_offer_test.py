#!/usr/bin/env python3
"""Offer = cost + beta x X, with X instrumented by each firm's own reactor outages.

    .venv/bin/python scripts/analysis/outage_offer_panel.py   # input
    .venv/bin/python scripts/analysis/outage_offer_test.py

Framework spec §9.2 and §9.3 (rank 1); the instrument is built and its first stage
on n checked in `notes/rq-reactor-outages.md`.

    y_ut = a_(unit x week) + d_(technology x date x hour) + beta * X_ft + e_ut

- y: the unit's offer price at 25% or 50% of its offered volume (EUR/MWh); for
  thermal units also that price minus the cost known at bidding (c_bid).
- d_(technology x date x hour) absorbs the market price, the merit order and every
  common shock, so beta is identified only by differences in X across firms within
  the hour, moved by each firm's own outage dose.
- a_(unit x week): outages last days to weeks, so a unit-day effect would absorb
  them. Within the week, the dose moves the level of a firm's X across days: this is
  the across-day margin.
- Instruments: the firm's unplanned and planned reactor outage doses (GW of its
  share of the lost output). Undeclared and economic cuts are not used (price
  responses).
- beta is in EUR/MWh of offer per EUR/MWh of X: 1 is supply-function Nash, 0 price
  taking. Errors clustered by ISO week; month clusters as a check.

Diagnostics: the first stage and reduced form; offered volume on the dose (a firm
covering a lost reactor's contracts with its own plant offers less in the auction,
which is not conduct); beta+ and beta- with instruments split by the firm's sign in
the previous week (predetermined).

Writes outputs/tables/outage_offer_results.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from iv_two_endog import ar_set_k1, ar_set_one, ar_test, fmt_intervals, sw_f, tsls_k  # noqa: E402
from midday_hydro_iv import ols  # noqa: E402

PANEL = ROOT / "outputs/tables/outage_offer_panel.parquet"
OUT = ROOT / "outputs/tables/outage_offer_results.csv"
WEAK_F = 10.0


def demean(M: np.ndarray, codes: list[np.ndarray], tol: float = 1e-8, maxit: int = 1000) -> np.ndarray:
    """Alternating projections with bincount group means (fast for millions of rows)."""
    M = M.astype(float).copy()
    counts = [np.bincount(c) for c in codes]
    for it in range(maxit):
        delta = 0.0
        for c, n in zip(codes, counts):
            for j in range(M.shape[1]):
                m = np.bincount(c, weights=M[:, j], minlength=len(n)) / n
                M[:, j] -= m[c]
                delta = max(delta, float(np.abs(m).max()))
        if delta < tol * (1 + float(np.abs(M).max())):
            break
    return M


VARS = ["o25", "o50", "oc50", "off_share", "X", "Xp", "Xm", "dose_unpl", "dose_plan",
        "dose_unpl_s", "dose_unpl_b", "dose_plan_s", "dose_plan_b"]
_CACHE: dict = {}


def prepare(d: pd.DataFrame, y: str, xs: list[str], zs: list[str]) -> tuple:
    """Rows complete in y, xs, zs and the demeaned columns. A sample that is a union of
    whole fixed-effect components of a larger one (a technology: no unit and no
    technology-hour spans two) reuses its demeaned values; other samples are demeaned
    once each and cached."""
    cols = [y, *xs, *zs]
    key = (len(d), int(d.index[0]), int(d.index[-1]), y)
    if key not in _CACHE:
        # Every sample drops rows missing any variable a specification can use (the
        # sign-split instruments are missing in each firm's first week), so nothing is
        # zero-filled before demeaning; oc50 exists for thermal units only and is used
        # only with a thermal sample, whose y it is.
        need = [y, "X", "Xp", "Xm", "dose_unpl", "dose_plan", "dose_unpl_s", "dose_unpl_b",
                "dose_plan_s", "dose_plan_b", "off_share"]
        base = d.dropna(subset=need)
        base = base[np.isfinite(base[need].to_numpy(float)).all(axis=1)]
        have = [c for c in VARS if c in base.columns and base[c].notna().all()]
        filled = base[have].to_numpy(float)
        codes = [pd.factorize(base.uw)[0], pd.factorize(base.cdh)[0]]
        _CACHE[key] = (base, pd.DataFrame(demean(filled, codes), index=base.index, columns=have),
                       base[have].notna())
    base, dm, ok = _CACHE[key]
    keep = ok[cols].all(axis=1).to_numpy()
    s = base[keep]
    return s, dm.loc[s.index, cols].to_numpy()


def iv(d: pd.DataFrame, y: str, label: str, zs=("dose_unpl", "dose_plan"), xs=("X",),
       cl: str = "wk", only: pd.Series | None = None) -> dict:
    """2SLS; `only` restricts to rows of d that form whole fixed-effect components, so the
    demeaning of d (cached) is valid for them."""
    xs, zs = list(xs), list(zs)
    s, M = prepare(d, y, xs, zs)
    if only is not None:
        m = only.loc[s.index].to_numpy()
        s, M = s[m], M[m]
    Y, X, Z = M[:, 0], M[:, 1:1 + len(xs)], M[:, 1 + len(xs):]
    W = np.zeros((len(s), 0))
    c = s[cl].to_numpy()
    row = {"sample": label, "y": y, "x": "+".join(xs), "instruments": "+".join(zs), "cluster": cl,
           "n": len(s), "units": s.unit.nunique(), "weeks": s.wk.nunique()}
    if (np.abs(Z).sum(axis=0) == 0).any():
        print(f"  {label:44s} {y:8s} instrument has no variation")
        return row | {"status": "no variation"}
    fs = [ols(X[:, j], Z, c) for j in range(len(xs))]
    b, V = tsls_k(Y, X, Z, W, c)
    F = [sw_f(X, Z, W, c, j) for j in range(len(xs))]
    row |= {"status": "weak" if min(F) < WEAK_F else "ok"}
    for j, x in enumerate(xs):
        row |= {f"b_{x}": b[j], f"se_{x}": np.sqrt(V[j, j]), f"F_{x}": F[j]}
        for k, z in enumerate(zs):
            row |= {f"fs_{x}_{z}": fs[j][0][k], f"fs_se_{x}_{z}": fs[j][1][k]}
    rf = ols(Y, Z, c)
    for k, z in enumerate(zs):
        row |= {f"rf_{z}": rf[0][k], f"rf_se_{z}": rf[1][k]}
    txt = "  ".join(f"{x} {b[j]:+.3f} ({np.sqrt(V[j, j]):.3f}, F {F[j]:.1f})" for j, x in enumerate(xs))
    if len(xs) == 1:
        _, p0 = ar_test(Y, X, Z, W, c, [0.0])
        _, p1 = ar_test(Y, X, Z, W, c, [1.0])
        st = ar_set_k1(Y, X[:, 0], Z, W, c) if len(zs) == 2 else (
            {"intervals": ar_set_one(Y, X[:, 0], Z, W, c)} if len(zs) == 1 else None)
        ar = fmt_intervals(st["intervals"]) if st else ""
        row |= {"ar_p_beta0": p0, "ar_p_beta1": p1, "ar_set": ar}
        txt += f"  AR p(0) {p0:.3g} p(1) {p1:.3g}  set {ar}"
    fs_txt = " ".join(f"{z}:{fs[0][0][k]:+.2f}" for k, z in enumerate(zs))
    print(f"  {label:44s} {y:8s} n={len(s):>9,}  FS X per GW [{fs_txt}]  {txt}"
          f"{'  WEAK' if row['status'] == 'weak' else ''}")
    return row


def reduced(d: pd.DataFrame, y: str, label: str, zs=("dose_unpl", "dose_plan")) -> dict:
    zs = list(zs)
    s, M = prepare(d, y, [], zs)
    b, se = ols(M[:, 0], M[:, 1:], s.wk.to_numpy())
    print(f"  {label:44s} {y:9s} " + "  ".join(f"{z} {b[k]:+.4f} ({se[k]:.4f})" for k, z in enumerate(zs)))
    return {"sample": label, "y": y, "x": "reduced form", "n": len(s),
            **{f"rf_{z}": b[k] for k, z in enumerate(zs)}, **{f"rf_se_{z}": se[k] for k, z in enumerate(zs)}}


def main() -> int:
    d = pd.read_parquet(PANEL)
    d["uw"] = d.unit + "_" + d.wk.astype(str)
    d["cdh"] = d.cls + "_" + d.date.dt.strftime("%Y%m%d") + "_" + d.hour.astype(str)
    d["mo"] = d.date.dt.strftime("%Y%m")
    d["oc50"] = d.o50 - d.c_bid
    # Sign of the firm's X over the previous ISO week: predetermined when the week's offers are made.
    fw = d.groupby(["group", "wk"]).X.mean().rename("xw").reset_index().sort_values(["group", "wk"])
    fw["s_prevwk"] = (fw.groupby("group").xw.shift() > 0).astype(float).where(fw.groupby("group").xw.shift().notna())
    d = d.merge(fw[["group", "wk", "s_prevwk"]], on=["group", "wk"], how="left")
    for z in ("dose_unpl", "dose_plan"):
        d[f"{z}_s"] = d[z] * d.s_prevwk
        d[f"{z}_b"] = d[z] * (1 - d.s_prevwk)
    d["Xp"], d["Xm"] = d.X.clip(lower=0), d.X.clip(upper=0)
    five = d.firm5 != "FRINGE"
    print(f"{len(d):,} unit-hours, {d.unit.nunique()} units; dose > 0 in {(d.dose_unpl > 0).mean():.3%} (unplanned), "
          f"{(d.dose_plan > 0).mean():.3%} (planned) of unit-hours\n")

    rows = []
    print("BETA: offer price on X, unit x week and technology x hour effects, week clusters")
    for y in ("o25", "o50"):
        rows.append(iv(d, y, "all units, both doses"))
        rows.append(iv(d, y, "all units, unplanned only", zs=("dose_unpl",)))
        rows.append(iv(d, y, "all units, planned only", zs=("dose_plan",)))
        rows.append(iv(d[five], y, "five firms only, both doses"))
        rows.append(iv(d, y, "all units, both doses, month clusters", cl="mo"))
        rows.append(iv(d[~d.zero_price], y, "all units, no zero-price hours"))
        for c in ("hydro", "ccgt", "coal", "pumped"):
            rows.append(iv(d, y, f"{c}, both doses", only=d.cls == c))
    print("\nTHERMAL, offer minus cost known at bidding")
    th = d[d.cls.isin(["ccgt", "coal"]) & d.c_bid.notna()]
    rows.append(iv(th, "oc50", "thermal with c_bid, both doses"))
    rows.append(iv(th, "o50", "thermal with c_bid, offer level, both doses"))
    print("\nSELLERS AND BUYERS: X+ and X-, doses split by the firm's sign in the previous week")
    for y in ("o25", "o50"):
        rows.append(iv(d, y, "all units, two slopes", xs=("Xp", "Xm"),
                       zs=("dose_unpl_s", "dose_unpl_b", "dose_plan_s", "dose_plan_b")))
    print("\nREDUCED FORMS and the volume check")
    for y in ("o25", "o50", "off_share", "X"):
        rows.append(reduced(d, y, "all units"))
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\n-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
