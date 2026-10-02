#!/usr/bin/env python3
"""Leg D rerun: REE's day-ahead wind and solar forecasts as the instruments for X+ and X-.

    .venv/bin/python scripts/analysis/leg_d_panel.py            # input
    .venv/bin/python scripts/analysis/leg_d_forecast_test.py

Same model as `leg_d_sign_test.py` (framework spec §4, leg D), same panel, same
fixed effects, same inference; only the instruments and the demand control change:

    y_uh = a_ud + a_hym + g+ * Xp_fh + g- * Xm_fh + c * D_h + e

Instruments: W and S, REE's wind and solar forecasts for D+1, published before
11:00 on D-1 (ESIOS 1777, 1779), GW. Control: D, REE's demand forecast of the same
vintage (ESIOS 1775), GW; it replaces `fcst`, whose publication time is not stated.

Why. The first run instrumented with rivals' offered solar z and z * s_prev. Offered
volume is partly a choice, and z * s_prev made yesterday's sign (a lagged outcome)
an instrument; with s_prev controlled the first stage all but vanished
(`notes/rq-leg-d-sign-of-n.md` §3.2). The forecasts are fixed before any offer is
made and move every firm's n (`notes/rq-forecast-first-stage.md`), so they need no
lagged sign. The model stays just identified: two instruments, two regressors.

Sample: unit-hours from 2019-01-01 (the forecasts start then) on the days where
the five firms' s_prev is defined (24-hour days whose previous day is 24 hours
too), so that hour numbers are clock hours; the five firms' rows also need s_prev
itself, as in the first run. The FRINGE has no X and so no s_prev of its own: it is
kept on the same days.

Rows: pooled (s50, s25, s75); by technology; by firm; by era; no zero-price hours;
s_prev controlled (the forecasts should not need it); D as a third instrument (one
overidentifying restriction); the forecasts x firm as instruments (the firms' n
responds differently, and a pooled first stage forces one response); one common
slope c on X = X+ + X- instrumented by W and S (exact AR set with two instruments:
empty means Nash's single slope does not fit both forecasts); the placebo reduced
forms of the fringe on W and S; and the rows net of the fringe's forecast response,
pooled, by firm and with the forecasts x firm.

Writes outputs/tables/leg_d_forecast_results.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from iv_two_endog import (ar_common_exact, ar_projection, ar_set_k1, ar_test,  # noqa: E402
                          fmt_intervals, fmt_set, projection_grid, projection_sign, sw_f, tsls_k)
from leg_d_sign_test import load  # noqa: E402
from midday_hydro_iv import ols  # noqa: E402
from solar_first_stage import demean  # noqa: E402

ESIOS = ROOT / "data/esios"
OUT = ROOT / "outputs/tables/leg_d_forecast_results.csv"
FORECASTS = {"W": 1777, "S": 1779, "D": 1775}   # wind, solar, demand: GW
START = "2019-01-01"
MIN_ROWS = 2000
WEAK_F = 10.0
ERAS = [("2019-2021", 2019, 2021), ("2022-2023", 2022, 2023), ("2024-2026", 2024, 2026)]


def forecasts() -> pd.DataFrame:
    """date (local), hour (local clock hour) -> W, S, D in GW. On DST days a clock hour
    is missing or repeated; those days have no s_prev and leave the sample anyway."""
    out = None
    for name, ind in FORECASTS.items():
        f = pd.read_parquet(ESIOS / f"esios_{ind}.parquet", columns=["utc_timestamp", "value"])
        local = f.utc_timestamp.dt.tz_convert("Europe/Madrid")
        f = pd.DataFrame({"date": pd.to_datetime(local.dt.date), "hour": local.dt.hour,
                          name: f.value / 1000.0}).drop_duplicates(["date", "hour"])
        out = f if out is None else out.merge(f, on=["date", "hour"], how="outer")
    return out


def estimate(d: pd.DataFrame, label: str, y: str = "y50", dens: str = "dd50",
             z: tuple = ("W", "S"), controls: tuple = ("D",)) -> dict:
    z, controls = list(z), list(controls)
    cols = [y, "Xp", "Xm", *z, *controls]
    d = d.dropna(subset=cols)
    row = {"sample": label, "outcome": y, "instrument": ", ".join(z), "controls": ", ".join(controls),
           "n": len(d), "units": d.unit.nunique(), "weeks": d.wk.nunique(),
           "weeks_seller": d.loc[d.Xp > 0, "wk"].nunique(), "weeks_buyer": d.loc[d.Xm < 0, "wk"].nunique()}
    if len(d) < MIN_ROWS:
        print(f"  {label:44s} too few ({len(d)})")
        return row | {"status": "too few"}
    w = demean(d, cols, ["ud", "hym"])
    Y, X, Z = w[y].to_numpy(), w[["Xp", "Xm"]].to_numpy(), w[z].to_numpy()
    W, cl = w[controls].to_numpy(), d.wk.to_numpy()
    b, V = tsls_k(Y, X, Z, W, cl)
    if np.isnan(b).any():
        print(f"  {label:44s} n={len(d):>9,}  not identified")
        return row | {"status": "not identified"}
    se = np.sqrt(np.diag(V))
    p_eq = float(2 * stats.norm.sf(abs(b[0] - b[1]) / np.sqrt(V[0, 0] + V[1, 1] - 2 * V[0, 1])))
    f_p, f_m = sw_f(X, Z, W, cl, 0), sw_f(X, Z, W, cl, 1)
    _, p00 = ar_test(Y, X, Z, W, cl, [0.0, 0.0])
    # The AR projections and the exact common-slope set need exactly two instruments.
    two = len(z) == 2
    gp, gm = projection_grid(b[0], se[0]), projection_grid(b[1], se[1])
    pp = ar_projection(Y, X, Z, W, cl, 0, gp) if two else None
    pm = ar_projection(Y, X, Z, W, cl, 1, gm) if two else None
    m_p, m_m = d.loc[d.Xp > 0, dens].mean(), d.loc[d.Xm < 0, dens].mean()
    bp, bm = -b[0] / m_p, -b[1] / m_m
    ex = ar_common_exact(Y, X, Z, W, cl) if two else None
    exb = ar_common_exact(Y, X * np.array([m_p, m_m]), Z, W, cl) if two else None
    common = fmt_intervals(ex["intervals"]) if ex else "n/a"
    common_beta = fmt_intervals([[-hi, -lo] for lo, hi in reversed(exb["intervals"])]) if exb else "n/a"
    weak = bool(min(f_p, f_m) < WEAK_F)
    min_p = f" (min p {ex['p_min']:.3f})" if ex else ""
    row |= {"status": "weak" if weak else "ok", "g_plus": b[0], "se_plus": se[0], "g_minus": b[1],
            "se_minus": se[1], "p_equal": p_eq, "sw_f_plus": f_p, "sw_f_minus": f_m, "ar_p_zero": p00,
            "ar_common": common, "ar_common_p_min": ex["p_min"] if ex else np.nan,
            "proj_plus": fmt_set(pp, gp) if two else "n/a", "proj_minus": fmt_set(pm, gm) if two else "n/a",
            "sign_plus": projection_sign(pp) if two else "n/a", "sign_minus": projection_sign(pm) if two else "n/a",
            "density_plus": m_p, "density_minus": m_m, "beta_plus": bp, "beta_minus": bm,
            "beta_common": common_beta}
    print(f"  {label:44s} n={len(d):>9,}  g+ {b[0]:+.3f} ({se[0]:.3f})  g- {b[1]:+.3f} ({se[1]:.3f})  "
          f"p(eq) {p_eq:.3f}  SW F {f_p:.1f}/{f_m:.1f}  AR p(0,0) {p00:.1e}  common g {common}{min_p}  "
          f"sign {row['sign_plus']}/{row['sign_minus']}  beta {bp:+.2f}/{bm:+.2f}  "
          f"common beta {common_beta}{'  WEAK' if weak else ''}")
    return row


def common_slope(d: pd.DataFrame, label: str, y: str = "y50", controls: tuple = ("D",)) -> dict:
    """One slope c on X = X+ + X-, instrumented by W and S: Nash's equality imposed.
    Two instruments for one regressor, so the exact AR set also tests the restriction:
    empty means no single slope fits both forecasts."""
    controls = list(controls)
    cols = [y, "X", "W", "S", *controls]
    d = d.dropna(subset=cols)
    w = demean(d, cols, ["ud", "hym"])
    Y, x, Z = w[y].to_numpy(), w.X.to_numpy(), w[["W", "S"]].to_numpy()
    W, cl = w[controls].to_numpy(), d.wk.to_numpy()
    b, V = tsls_k(Y, x[:, None], Z, W, cl)
    f1 = sw_f(x[:, None], Z, W, cl, 0)
    _, p0 = ar_test(Y, x[:, None], Z, W, cl, [0.0])
    s = ar_set_k1(Y, x, Z, W, cl)
    ar = fmt_intervals(s["intervals"]) if s else "not identified"
    dens = d.dd50.mean()
    print(f"  {label:44s} n={len(d):>9,}  c {b[0]:+.3f} ({np.sqrt(V[0, 0]):.3f})  F {f1:.1f}  "
          f"AR p(c=0) {p0:.1e}  AR set {ar} (min p {s['p_min'] if s else np.nan:.3f})  "
          f"beta {-b[0] / dens:+.2f}")
    return {"sample": label, "outcome": y, "instrument": "W, S (one slope)", "controls": ", ".join(controls),
            "status": "weak" if f1 < WEAK_F else "ok", "n": len(d), "units": d.unit.nunique(),
            "weeks": d.wk.nunique(), "c": b[0], "c_se": float(np.sqrt(V[0, 0])), "c_f": f1,
            "ar_p_zero": p0, "ar_common": ar, "ar_common_p_min": s["p_min"] if s else np.nan,
            "beta_c": -b[0] / dens}


def reduced_form(d: pd.DataFrame, label: str) -> dict:
    cols = ["y50", "W", "S", "D"]
    d = d.dropna(subset=cols)
    w = demean(d, cols, ["ud", "hym"])
    b, se = ols(w.y50.to_numpy(), w[["W", "S", "D"]].to_numpy(), d.wk.to_numpy())
    print(f"  {label:44s} n={len(d):>9,}  s50 on W {b[0]:+.3f} (t {b[0]/se[0]:+.1f}), "
          f"on S {b[1]:+.3f} (t {b[1]/se[1]:+.1f}) pp per GW")
    return {"sample": label, "outcome": "y50 reduced form", "status": "ok", "n": len(d),
            "rf_W": b[0], "rf_W_se": se[0], "rf_S": b[1], "rf_S_se": se[1]}


def main() -> int:
    h = load()
    h = h[h.date >= START]
    days = h.loc[(h.firm != "FRINGE") & h.s_prev.notna(), "date"].unique()
    h = h[h.date.isin(days) & ((h.firm == "FRINGE") | h.s_prev.notna())]
    h = h.merge(forecasts(), on=["date", "hour"], how="left")
    miss = h[["W", "S", "D"]].isna().any(axis=1)
    print(f"{len(h):,} unit-hours from {START}; {miss.sum():,} without a forecast")
    h = h[~miss].copy()
    five = h[h.firm != "FRINGE"].copy()
    rows = []
    print("\nLEG D WITH FORECAST INSTRUMENTS -- g in pp of capacity per EUR/MWh of X; beta = -g / density.\n")
    print("POOLED, all five firms")
    rows.append(estimate(five, "pooled"))
    for q in ("25", "75"):
        rows.append(estimate(five, f"pooled, s{q}", f"y{q}", f"dd{q}"))
    print("\nBY TECHNOLOGY")
    rows.append(estimate(five[five.cls.isin(["hydro", "pumped"])], "hydro + pumped"))
    rows.append(estimate(five[five.cls.isin(["ccgt", "coal"])], "ccgt + coal"))
    print("\nBY FIRM")
    for f, g in five.groupby("firm"):
        rows.append(estimate(g, f))
    print("\nBY ERA")
    for lab, a, b in ERAS:
        rows.append(estimate(five[five.date.dt.year.between(a, b)], lab))
    print("\nROBUSTNESS")
    rows.append(estimate(five[five.zero_price == 0], "no zero-price hours"))
    rows.append(estimate(five, "pooled, s_prev controlled", controls=("D", "s_prev")))
    rows.append(estimate(five, "pooled, D as a third instrument", z=("W", "S", "D"), controls=()))
    rows.append(estimate(five[five.firm != "ENDESA"], "pooled, without Endesa"))
    # A pooled first stage forces one forecast response on all five firms, whose n
    # responds differently (notes/rq-forecast-first-stage.md): let it differ by firm.
    fz = []
    for f in sorted(five.firm.unique()):
        for v in ("W", "S"):
            five[f"{v}_{f}"] = five[v].where(five.firm == f, 0.0)
            fz.append(f"{v}_{f}")
    rows.append(estimate(five, "pooled, forecasts x firm as instruments", z=tuple(fz)))
    print("\nONE COMMON SLOPE -- Nash's equality imposed; an empty AR set means it fits neither way")
    rows.append(common_slope(five, "pooled, one slope"))
    rows.append(common_slope(five[five.firm != "ENDESA"], "pooled, one slope, without Endesa"))
    rows.append(common_slope(five, "pooled, one slope, s_prev controlled", controls=("D", "s_prev")))
    print("\nPLACEBO -- reduced forms, s50 on the forecasts")
    fringe = h[h.firm == "FRINGE"]
    tech = h.cls.isin(["ccgt", "coal"]).map({True: "thermal", False: "hydro"}).astype(str)
    rf = {}
    for who, d in (("FRINGE", fringe), ("five firms", five)):
        for c, g in d.groupby(tech.loc[d.index]):
            r = reduced_form(g, f"{who}, {c}")
            rows.append(r)
            if who == "FRINGE":
                rf[c] = (r["rf_W"], r["rf_S"])
    print("\nNET OF THE FRINGE'S FORECAST RESPONSE -- forecasts allowed to move offers through cost")
    h["y50_net"] = (h.y50 - tech.map({c: v[0] for c, v in rf.items()}) * h.W
                    - tech.map({c: v[1] for c, v in rf.items()}) * h.S)
    five = h[h.firm != "FRINGE"]
    five = five.copy()
    for f in sorted(five.firm.unique()):
        for v in ("W", "S"):
            five[f"{v}_{f}"] = five[v].where(five.firm == f, 0.0)
    rows.append(estimate(five, "pooled, net of the fringe's response", y="y50_net"))
    rows.append(estimate(five, "pooled, forecasts x firm, net of the fringe's response", y="y50_net",
                         z=tuple(f"{v}_{f}" for f in sorted(five.firm.unique()) for v in ("W", "S"))))
    rows.append(common_slope(five, "pooled, one slope, net of the fringe's response", y="y50_net"))
    for f, g in five.groupby("firm"):
        rows.append(common_slope(g, f"{f}, one slope, net of the fringe's response", y="y50_net"))
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0 if rows[0].get("status") in ("ok", "weak") else 1


if __name__ == "__main__":
    raise SystemExit(main())
