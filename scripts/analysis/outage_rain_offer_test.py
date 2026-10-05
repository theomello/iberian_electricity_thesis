#!/usr/bin/env python3
"""Thermal offers on X with two instruments: reactor outages and own-catchment rain.

    .venv/bin/python scripts/analysis/outage_offer_panel.py              # input: offers, X, doses
    .venv/bin/python scripts/build/build_catchment_rain.py               # input: rain per catchment
    .venv/bin/python scripts/analysis/outage_rain_offer_test.py

Framework spec §9.3: rain in a firm's own catchments is the second instrument for
its n (`notes/rq-hydro-rain-first-stage.md`). Its index is the one of
`hydro_rain_catchment_first_stage.py`, computed for every day and every group that
owns linked hydro:

    H_ft = sum over plants j of  GW_j x share_fjt x z_jt

z_jt is the rain over plant j's catchment in the k days BEFORE day t (k = 30, 90),
standardised against the plant's 1991-2020 k-day sums in the same calendar month.
A group with no linked hydro has H = 0.

THERMAL UNITS ONLY. Rain changes a hydro unit's own cost (the value of its water),
so it is not excluded from hydro offers. A combined cycle's or a coal plant's cost
does not depend on rain; rain reaches its offer only through the firm's position.

EFFECTS. Rain moves slowly: a 30-day sum changes little within a week, so unit x
week effects (outage_offer_test.py) would leave it almost nothing. The main
specification uses unit x month effects with technology x date x hour effects, and
clusters by month. The outage doses are run both ways for comparison.

AR SETS. With three instruments the exact AR set is found on a grid (0.01 steps over
[-20, 20]) from the Z-coefficients of y and X and their cluster covariance, so the
grid costs no extra regressions.

Writes outputs/tables/outage_rain_offer_results.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from build_hydro_plant_units import owners_of_plants  # noqa: E402
from hydro_rain_catchment_first_stage import plant_z  # noqa: E402
from iv_two_endog import _ar_parts, sw_f, tsls_k  # noqa: E402
from midday_hydro_iv import ols  # noqa: E402
from outage_offer_test import demean  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
PANEL = TABLES / "outage_offer_panel.parquet"
OUT = TABLES / "outage_rain_offer_results.csv"
WINDOWS = (30, 90)
GRID = np.round(np.arange(-20, 20.0001, 0.01), 2)
WEAK_F = 10.0


def daily_rain(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """group, date, H30, H90 for every group owning linked hydro, on the given dates."""
    pc = pd.read_parquet(DATA / "eobs/plant_catchments.parquet", columns=["plant_id", "capacity_mw"])
    o = owners_of_plants(pc.merge(pd.DataFrame({"date": dates}), how="cross"))
    o["gw"] = o.capacity_mw / 1000 * o.share
    out = None
    for k in WINDOWS:
        z = plant_z(k).reindex(dates).rename_axis(index="date", columns="plant_id").stack().rename("z").reset_index()
        m = o.merge(z, on=["plant_id", "date"]).dropna(subset=["z"])
        h = (m.gw * m.z).groupby([m.group, m.date]).sum().rename(f"H{k}").reset_index()
        out = h if out is None else out.merge(h, on=["group", "date"], how="outer")
    return out


def ar_grid(y, x, Z, W, cl, level=0.95) -> tuple[str, float, float]:
    """AR set on GRID, and the AR p-values at 0 and 1, for one regressor and any L."""
    C, V = _ar_parts(y, x[:, None], Z, W, cl)
    L = Z.shape[1]
    crit = chi2.ppf(level, L)

    def stat(g):
        w = np.array([1.0, -g])
        b = C @ w
        S = sum(w[a] * w[c] * V[a][c] for a in range(2) for c in range(2))
        return float(b @ np.linalg.solve(S, b))

    keep = np.array([stat(g) <= crit for g in GRID])
    iv, start = [], None
    for g, k in zip(GRID, keep):
        if k and start is None:
            start = g
        if not k and start is not None:
            iv.append((start, prev))
            start = None
        prev = g
    if start is not None:
        iv.append((start, GRID[-1]))
    txt = " U ".join(f"[{'-inf' if lo == GRID[0] else f'{lo:.2f}'}, {'+inf' if hi == GRID[-1] else f'{hi:.2f}'}]"
                     for lo, hi in iv) or "empty"
    return txt, float(chi2.sf(stat(0.0), L)), float(chi2.sf(stat(1.0), L))


def iv(s: pd.DataFrame, D: pd.DataFrame, y: str, zs: list[str], label: str, fe: str, cl: str) -> dict:
    keep = D[[y, "X", *zs]].notna().all(axis=1).to_numpy()
    Y, X, Z = D.loc[keep, y].to_numpy(), D.loc[keep, ["X"]].to_numpy(), D.loc[keep, zs].to_numpy()
    c = s.loc[keep, cl].to_numpy()
    W = np.zeros((len(Y), 0))
    row = {"sample": label, "y": y, "effects": fe, "instruments": "+".join(zs), "cluster": cl, "n": int(keep.sum())}
    if (np.abs(Z).sum(axis=0) == 0).any():
        print(f"  {label:40s} {y:5s} an instrument has no variation")
        return row | {"status": "no variation"}
    fs = ols(X[:, 0], Z, c)
    b, V = tsls_k(Y, X, Z, W, c)
    F = sw_f(X, Z, W, c, 0)
    ar, p0, p1 = ar_grid(Y, X[:, 0], Z, W, c)
    rf = ols(Y, Z, c)
    row |= {"b": b[0], "se": np.sqrt(V[0, 0]), "F": F, "status": "weak" if F < WEAK_F else "ok",
            "ar_p_beta0": p0, "ar_p_beta1": p1, "ar_set": ar,
            **{f"fs_{z}": fs[0][k] for k, z in enumerate(zs)}, **{f"fs_se_{z}": fs[1][k] for k, z in enumerate(zs)},
            **{f"rf_{z}": rf[0][k] for k, z in enumerate(zs)}, **{f"rf_se_{z}": rf[1][k] for k, z in enumerate(zs)}}
    fs_txt = " ".join(f"{z}:{fs[0][k]:+.2f}({fs[1][k]:.2f})" for k, z in enumerate(zs))
    print(f"  {label:40s} {y:5s} FS [{fs_txt}]  b {b[0]:+.3f} ({np.sqrt(V[0, 0]):.3f}, F {F:.1f})  "
          f"AR p(0) {p0:.3g} p(1) {p1:.3g}  set {ar}{'  WEAK' if F < WEAK_F else ''}")
    return row


def main() -> int:
    d = pd.read_parquet(PANEL, columns=["unit", "group", "cls", "date", "hour", "o25", "o50", "c_bid", "X",
                                        "dose_unpl", "dose_plan", "wk"])
    d = d[d.cls.isin(["ccgt", "coal"]) & d.c_bid.notna()].copy()
    r = daily_rain(pd.DatetimeIndex(sorted(d.date.unique())))
    print("mean daily rain index by group (GW-weighted z), groups with thermal units in the panel:")
    print(r[r.group.isin(d.group.unique())].groupby("group")[["H30", "H90"]].agg(["mean", "std"]).round(2).to_string())
    d = d.merge(r, on=["group", "date"], how="left")
    first = r.dropna(subset=["H90"]).date.min()
    d = d[(d.date >= first) & (d.date <= r.date.max())]
    d[["H30", "H90"]] = d[["H30", "H90"]].fillna(0.0)        # no linked hydro: no own rain
    d["oc50"] = d.o50 - d.c_bid
    d["mo"] = d.date.dt.strftime("%Y%m")
    d["um"] = d.unit + "_" + d.mo
    d["uw"] = d.unit + "_" + d.wk.astype(str)
    d["cdh"] = d.cls + "_" + d.date.dt.strftime("%Y%m%d") + "_" + d.hour.astype(str)
    cols = ["o25", "o50", "oc50", "X", "dose_unpl", "dose_plan", "H30", "H90"]
    d = d.dropna(subset=cols).reset_index(drop=True)
    print(f"\n{len(d):,} thermal unit-hours, {d.unit.nunique()} units, {d.date.min().date()} -> {d.date.max().date()}; "
          f"H30 non-zero on {(d.H30 != 0).mean():.1%}")

    rows = []
    for fe in ("uw", "um"):
        D = pd.DataFrame(demean(d[cols].to_numpy(float), [pd.factorize(d[fe])[0], pd.factorize(d.cdh)[0]]),
                         columns=cols)
        cl = "wk" if fe == "uw" else "mo"
        name = {"uw": "unit x week", "um": "unit x month"}[fe]
        print(f"\n{name.upper()} and technology x date x hour effects, {cl} clusters")
        print(f"  within sd: X {D.X.std():.2f}, dose_unpl {D.dose_unpl.std():.4f}, dose_plan {D.dose_plan.std():.4f}, "
              f"H30 {D.H30.std():.3f}, H90 {D.H90.std():.3f}")
        specs = [("outages", ["dose_unpl", "dose_plan"])]
        if fe == "um":
            specs += [("rain 30 days", ["H30"]), ("rain 90 days", ["H90"]),
                      ("outages + rain 30", ["dose_unpl", "dose_plan", "H30"]),
                      ("outages + rain 90", ["dose_unpl", "dose_plan", "H90"])]
        for y in ("o50", "o25", "oc50"):
            for lab, zs in specs:
                rows.append(iv(d, D, y, zs, lab, name, cl))
        if fe == "um":
            for z in ("H30", "H90"):
                b, se = ols(D.X.to_numpy(), D[[z]].to_numpy(), d[cl].to_numpy())
                print(f"  first stage X on {z} alone: {b[0]:+.3f} ({se[0]:.3f}), F {(b[0] / se[0]) ** 2:.1f}")
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\n-> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
