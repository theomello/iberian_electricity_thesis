#!/usr/bin/env python3
"""β from the conditions of a step bidder: each gas or coal step's price and length.

    .venv/bin/python scripts/analysis/step_curves.py                 # curves
    .venv/bin/python scripts/analysis/step_engine.py --months ...    # resampled clearing
    .venv/bin/python scripts/analysis/step_estimator.py

Framework spec §9.7 step 6; step-offer design `docs/specs/2026-10-01-step-offer-design.md`
§3. A firm offers steps before it knows its residual demand. For step k of unit u, at
price b_k, with the firm's X = n / |RD′|:

  PRICE of step k, over the draws in which k sets the price (`step_engine.py`):
      E[1{k sets p} · ((b_k − c_u)·|RD′| − β·n)] = 0
      ⇒  b_k − c_u = β · X̃_k,   X̃_k = Σ n / Σ |RD′| over those draws
  LENGTH of step k, over the draws in which p falls in the firm's gap above k:
      E[1{gap above k} · (p − c_u − β·X)] = 0
      ⇒  p̄_k − c_u = β · X̄_k   (means over those draws)
      holds only where the length is chosen: not for a unit's last step (capacity) or
      a block priced at 5 €/MWh or less (minimum load); there it is an inequality.

c_u: implied cost on prices known when offers close, gas cap applied
(`marginal_cost_capped_bid_eur_mwh`; plant-specific efficiency only).

THE NON-STRATEGIC LADDER (framework §9.1). Offer ladders slope up without market power
(part-load efficiency, start-ups, operation and maintenance), so b_k − c_u is not zero
for a price-taker. Fixed effects take it out, identified by firms whose X̃ is near 0:
  unit × month           constant cost errors
  fuel × date × hour     everything common to the hour, including which part of the
                         merit order the draws select
  fuel × position        the ladder: decile of the step's midpoint in the unit's capacity
β then comes from differences in X̃ across firms' steps within the hour.

X̃ IS ENDOGENOUS. It depends on b_k (a higher step is marginal in tighter draws), so an
unmeasured cost raises both. Instruments known when offers close and shifting the
firm's n, not the unit's cost: the firm's planned and unplanned reactor outages (GW,
`reactor_outage_dose.parquet`) and its regional wind deviation (`Wdev_fc`, as in
`regional_wind_offer_test.py`). The least-squares fit is reported as a description.

SLOPE FLOOR. X̃ is undefined when rivals' mean slope over the active draws is below FLOOR
(20 MW per €/MWh; 5 and 50 as checks). The ±5 €/MWh band is thin at the 150–300 €/MWh
prices of 2021–2023 (median slope over marginal draws 76–190, against 450–485 in
2019–2020), and 1/slope sends X̃ to ±1,000 there.

Rows: steps whose firm-level price point is ≥ 90% gas or coal of that unit's group.
Weights: number of draws in which the moment is active. Week clusters. Anderson–Rubin
sets on GRID. 2019-01 → 2023-12, hourly.

Writes outputs/tables/step_estimator_results.csv and step_estimator_rows.parquet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from iv_two_endog import _ar_parts, sw_f, tsls_k  # noqa: E402
from midday_hydro_iv import cluster_meat  # noqa: E402
from regional_wind_offer_test import forecasts, own_capacity, regional_cf  # noqa: E402

CACHE = ROOT / "outputs/cache/step"
TABLES = ROOT / "outputs/tables"
OUT = TABLES / "step_estimator_results.csv"
ROWS = TABLES / "step_estimator_rows.parquet"
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")
FIRST, LAST = "201901", "202312"
GRID = np.round(np.arange(-20.0, 20.0 + 1e-9, 0.01), 2)
THERMAL_SHARE = 0.9
MINLOAD = 5.0
TOP = 0.98
FLOOR = 20             # MW per €/MWh: rivals' mean slope over the active draws (X undefined below)
FLOORS = (5, 20, 50)
WEAK_F = 10.0


def months() -> list[str]:
    return [m for m in sorted(p.stem.split("_")[1] for p in CACHE.glob("moments_2*.parquet")) if FIRST <= m <= LAST]


def rows() -> pd.DataFrame:
    parts = []
    for ym in months():
        m = pd.read_parquet(CACHE / f"moments_{ym}.parquet")
        u = pd.read_parquet(CACHE / f"units_{ym}.parquet")
        u = u[~u.withdrawn & u.group.notna()]
        tot = u.groupby(["hid", "group", "price"]).mw.sum().rename("th_mw").reset_index()
        m = m.merge(tot, on=["hid", "group", "price"], how="inner")
        m = m[m.th_mw >= THERMAL_SHARE * m.v_sell]
        d = u.merge(m, on=["hid", "group", "price"], how="inner")
        h = pd.read_parquet(CACHE / f"hours_{ym}.parquet", columns=["hid", "date", "period", "utc", "p_star"])
        parts.append(d.merge(h, on="hid"))
    d = pd.concat(parts, ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    return d


def derive(d: pd.DataFrame) -> pd.DataFrame:
    d["mk"] = d.price - d.cost
    sbar = d.m_s / d.m_n.where(d.m_n > 0)
    gbar = d.g_s / d.g_n.where(d.g_n > 0)
    for f in FLOORS:
        d[f"Xt{f}"] = np.where(sbar >= f, d.m_sn / d.m_s.where(d.m_s > 0), np.nan)
        d[f"Xg{f}"] = np.where((gbar >= f) & (d.g_xn > 0), d.g_x / d.g_xn.where(d.g_xn > 0), np.nan)
    d["Xt"], d["Xg"] = d[f"Xt{FLOOR}"], d[f"Xg{FLOOR}"]
    d["mk_gap"] = np.where(d.g_n > 0, d.g_p / d.g_n.where(d.g_n > 0) - d.cost, np.nan)
    d["pos"] = np.minimum(9, ((d.mw_below + d.mw / 2) / d.cap_mw * 10).fillna(0).astype(int).clip(0, 9))
    d["top"] = d.mw_below + d.mw >= TOP * d.cap_mw
    d["minload"] = d.price <= MINLOAD
    d["five"] = d.group.isin(FIRMS)
    d["r_X"] = np.where(d.r_s >= 5.0, d.r_n / d.r_s.where(d.r_s > 0), np.nan)
    return d


def instruments(d: pd.DataFrame) -> pd.DataFrame:
    dz = pd.read_parquet(TABLES / "reactor_outage_dose.parquet")
    dz = dz[dz.cls.isin(["unplanned", "planned"])].pivot_table(
        index=["firm", "utc"], columns="cls", values="lost_mw", aggfunc="sum").fillna(0.0) / 1000
    dz = dz.rename(columns={"unplanned": "dose_unpl", "planned": "dose_plan"}).reset_index().rename(
        columns={"firm": "group"})
    dz["utc"] = pd.to_datetime(dz.utc, utc=True)
    d["utc"] = pd.to_datetime(d.utc, utc=True)
    d = d.merge(dz, on=["group", "utc"], how="left")
    d[["dose_unpl", "dose_plan"]] = d[["dose_unpl", "dose_plan"]].fillna(0.0)
    fc = forecasts()
    cf = regional_cf(fc)
    k = own_capacity(d.group.unique())
    w = k.merge(cf, on="nuts_id")
    w["Wdev_fc"] = w.K_gw * w.dev_fc
    w = w.groupby(["group", "utc"]).Wdev_fc.sum(min_count=1).reset_index()
    w["utc"] = pd.to_datetime(w.utc, utc=True)
    d = d.merge(w, on=["group", "utc"], how="left")
    d.loc[~d.group.isin(k.group), "Wdev_fc"] = 0.0
    return d


def wdemean(M: np.ndarray, codes: list[np.ndarray], w: np.ndarray, tol: float = 1e-8, maxit: int = 500) -> np.ndarray:
    """Weighted alternating projections."""
    M = M.astype(float).copy()
    sw = [np.bincount(c, weights=w) for c in codes]
    for _ in range(maxit):
        delta = 0.0
        for c, s in zip(codes, sw):
            for j in range(M.shape[1]):
                m = np.bincount(c, weights=w * M[:, j], minlength=len(s)) / np.where(s > 0, s, 1)
                M[:, j] -= m[c]
                delta = max(delta, float(np.abs(m).max()))
        if delta < tol * (1 + float(np.abs(M).max())):
            break
    return M


def ar_grid(y, x, Z, W, cl, level=0.95) -> tuple[str, float, float]:
    C, V = _ar_parts(y, x[:, None], Z, W, cl)
    L = Z.shape[1]
    crit = chi2.ppf(level, L)

    def stat(g):
        wv = np.array([1.0, -g])
        b = C @ wv
        S = sum(wv[a] * wv[c] * V[a][c] for a in range(2) for c in range(2))
        return float(b @ np.linalg.solve(S, b))

    keep = np.array([stat(g) <= crit for g in GRID])
    iv, start, prev = [], None, None
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


def fe_codes(s: pd.DataFrame, fe: str) -> list[np.ndarray]:
    um = s.unit + "_" + s.date.dt.strftime("%Y%m")
    fdh = s.fuel + "_" + s.hid.astype(str)
    fd = s.fuel + "_" + s.date.dt.strftime("%Y%m%d")
    fp = s.fuel + "_" + s.pos.astype(str)
    hr = s.period.astype(str)
    sets = {"main": [um, fdh, fp], "date": [um, fd, fp, hr], "noladder": [um, fdh]}
    return [pd.factorize(c)[0] for c in sets[fe]]


def est(d: pd.DataFrame, y: str, x: str, w: str, label: str, zs=("dose_unpl", "dose_plan"), fe: str = "main") -> dict:
    zs = list(zs)
    s = d.dropna(subset=[y, x, w, *zs])
    s = s[(s[w] > 0) & np.isfinite(s[[y, x, *zs]].to_numpy(float)).all(axis=1)]
    if len(s) < 1000:
        print(f"  {label:52s} too few rows ({len(s)})")
        return {"sample": label, "y": y, "x": x, "n": len(s), "status": "too few rows"}
    row = {"sample": label, "y": y, "x": x, "weight": w, "fe": fe, "instruments": "+".join(zs) or "none",
           "n": len(s), "units": s.unit.nunique(), "groups": s.group.nunique(),
           "mean_y": np.average(s[y], weights=s[w]), "mean_x": np.average(s[x], weights=s[w]),
           "sd_x": float(np.sqrt(np.cov(s[x], aweights=s[w])))}
    wt = s[w].to_numpy(float)
    M = wdemean(s[[y, x, *zs]].to_numpy(float), fe_codes(s, fe), wt)
    r = np.sqrt(wt)
    Y, X, Z = M[:, 0] * r, M[:, [1]] * r[:, None], M[:, 2:] * r[:, None]
    W0 = np.zeros((len(s), 0))
    cl = s.date.dt.strftime("%G%V").to_numpy()
    inv = 1.0 / (X[:, 0] @ X[:, 0])
    b_ols = inv * (X[:, 0] @ Y)
    V_ols = inv * cluster_meat(X, Y - X[:, 0] * b_ols, cl)[0, 0] * inv
    row |= {"b_ols": b_ols, "se_ols": np.sqrt(V_ols)}
    txt = f"LS {b_ols:+.3f} ({np.sqrt(V_ols):.3f})"
    if zs:
        if (np.abs(Z).sum(axis=0) == 0).any():
            print(f"  {label:52s} an instrument has no variation")
            return row | {"status": "no variation"}
        b, V = tsls_k(Y, X, Z, W0, cl)
        F = sw_f(X, Z, W0, cl, 0)
        ar, p0, p1 = ar_grid(Y, X[:, 0], Z, W0, cl)
        row |= {"b_iv": b[0], "se_iv": np.sqrt(V[0, 0]), "F": F, "ar_set": ar, "ar_p0": p0, "ar_p1": p1,
                "status": "weak" if F < WEAK_F else "ok"}
        txt += f"  IV {b[0]:+.3f} ({np.sqrt(V[0, 0]):.3f}) F {F:.1f}  AR p(0) {p0:.3g} p(1) {p1:.3g}  set {ar}"
    print(f"  {label:52s} n={len(s):>9,}  mean y {row['mean_y']:6.2f}  mean X {row['mean_x']:+6.2f}  {txt}", flush=True)
    return row


def describe(d: pd.DataFrame) -> None:
    p = d[d.m_n > 0]
    print(f"\nPRICE MOMENTS: {len(p):,} unit-steps marginal in at least one draw ({p.unit.nunique()} units); "
          f"of {len(d):,} thermal steps with draws")
    g = p.groupby("group").apply(lambda x: pd.Series({
        "steps": len(x), "draws_marginal": x.m_n.sum(),
        "markup": np.average(x.mk, weights=x.m_n), "X_tilde": np.average(x.Xt.fillna(0), weights=x.m_n)}),
        include_groups=False)
    print(g.round(2).to_string())
    p = p.assign(xb=pd.cut(p.Xt, [-np.inf, -4, -2, -1, -0.5, 0, 0.5, 1, 2, 4, np.inf]))
    t = p.groupby(["xb", "five"], observed=True).apply(lambda x: pd.Series({
        "steps": len(x), "markup": np.average(x.mk, weights=x.m_n)}), include_groups=False).unstack("five")
    print("\nmarkup (b − c, €/MWh, weighted by marginal draws) by X̃ bin, other owners (False) and the five (True):")
    print(t.round(2).to_string())


def main() -> int:
    if "--reuse" in sys.argv and ROWS.exists():
        d = derive(pd.read_parquet(ROWS))
    else:
        d = instruments(rows())
        d.to_parquet(ROWS, index=False)
        d = derive(d)
    describe(d)
    res = []
    p = d[d.m_n > 0]
    print("\nPRICE MOMENTS: b − c = β·X̃ (weights: marginal draws)")
    res.append(est(p, "mk", "Xt", "m_n", "all, least squares", zs=()))
    res.append(est(p, "mk", "Xt", "m_n", "all, doses"))
    res.append(est(p, "mk", "Xt", "m_n", "all, doses + regional wind", zs=("dose_unpl", "dose_plan", "Wdev_fc")))
    res.append(est(p, "mk", "Xt", "m_n", "all, regional wind alone", zs=("Wdev_fc",)))
    res.append(est(p, "mk", "Xt", "m_n", "all, doses, fuel×date + hour effects", fe="date"))
    res.append(est(p, "mk", "Xt", "m_n", "all, doses, no ladder effects", fe="noladder"))
    res.append(est(p, "mk", "Xt5", "m_n", "all, doses, slope floor 5"))
    res.append(est(p, "mk", "Xt50", "m_n", "all, doses, slope floor 50"))
    res.append(est(p[p.Xt.abs() <= 30], "mk", "Xt", "m_n", "all, doses, |X̃| ≤ 30"))
    res.append(est(p[p.fuel == "gas"], "mk", "Xt", "m_n", "gas, doses"))
    res.append(est(p[p.date < "2021-07-01"], "mk", "Xt", "m_n", "2019 – 2021 H1, doses"))
    res.append(est(p[p.date >= "2021-07-01"], "mk", "Xt", "m_n", "2021 H2 – 2023, doses"))
    res.append(est(p[p.five], "mk", "Xt", "m_n", "five firms, doses"))
    res.append(est(p[~p.five], "mk", "Xt", "m_n", "other owners (LS only)", zs=()))

    gp = d[(d.g_n > 0) & ~d.top & ~d.minload]
    print("\nLENGTH MOMENTS: p̄ − c = β·X̄ over gap draws, chosen boundaries only (weights: gap draws)")
    res.append(est(gp, "mk_gap", "Xg", "g_n", "gap, all, doses"))
    res.append(est(gp, "mk_gap", "Xg", "g_n", "gap, all, doses + regional wind", zs=("dose_unpl", "dose_plan", "Wdev_fc")))
    res.append(est(gp[gp.fuel == "gas"], "mk_gap", "Xg", "g_n", "gap, gas, doses"))

    print("\nONE DRAW (the realised residual demand): the ex-post version")
    one = d.assign(w1=1.0)
    res.append(est(one[one.r_event == 1], "mk", "r_X", "w1", "realised, own step sets p, doses"))
    gap1 = one[(one.r_event == 2) & ~one.top & ~one.minload].assign(mk_r=lambda x: x.r_p - x.cost)
    res.append(est(gap1, "mk_r", "r_X", "w1", "realised, gap above own step, doses"))

    pd.DataFrame(res).to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
