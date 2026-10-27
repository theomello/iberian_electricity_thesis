#!/usr/bin/env python3
"""β from the price of hydro offer steps, with the water value differenced out by unit-day effects.

    .venv/bin/python scripts/analysis/step_curves.py                               # curves
    .venv/bin/python scripts/analysis/step_engine.py --kind hydro --months ...     # resampled clearing
    .venv/bin/python scripts/analysis/step_estimator_hydro.py [--reuse]

The thermal step estimator (`step_estimator.py`) with storage hydro and pumped-storage
turbines (leg D's units). A reservoir's marginal cost is its water value λ, which is
not observed; within a day it is one number (framework spec §4, leg A, assumption A1),
so unit × day effects take it out:

    b_k = λ_ud + β · X̃_k + hydro class × hour + class × ladder position

b_k is the step's price, X̃_k = Σ n / Σ |RD′| over the resampled draws in which the
firm's price point k sets the price (`step_engine.py`). β comes from how a unit's step
prices move across the hours of one day against the firm's X̃ in those hours, compared
with other owners' hydro in the same hour.

INSTRUMENTS vary within the day and are known when offers close: each firm's own
response to REE's D-1 wind and solar forecasts (group × F_wind, group × F_solar, GW;
leg D §7's firm-specific first stage). The common response is absorbed by the
class × hour effects, so only differences between firms identify. Alternatives:
reactor outages (vary little within a day) and regional wind deviation (`Wdev_fc`).

FLAT UNIT-DAYS. A unit offering the identical curve in all 24 hours made one choice for
the day, so the within-day condition does not apply (EDP's four flat cascades, leg A).
They are left out of the main rows and added back as a check.

Rows: hydro price points above 1 €/MWh that set the price in at least one draw, ≥ 90%
of the firm's sell MW at that price from its storage or pumped hydro. X̃ undefined below
a mean rivals' slope of FLOOR (20 MW per €/MWh; 5 and 50 as checks). `Xt_rel` uses a band
of ±5% of the price (at least ±2.5 €/MWh) instead of ±5 €/MWh, so the window keeps its
width relative to the price level (thin at the 150–300 €/MWh prices of 2021–2023). Weights: marginal
draws. Week clusters. 2019-01 → 2025-09.

Writes outputs/tables/step_estimator_hydro_results.csv and step_estimator_hydro_rows.parquet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from iv_two_endog import sw_f, tsls_k  # noqa: E402
from midday_hydro_iv import cluster_meat  # noqa: E402
from regional_wind_offer_test import FORECASTS, forecasts, tagged  # noqa: E402
from step_estimator import CACHE, FIRMS, FLOORS, INSTRUMENTS, ar_grid, instruments, wdemean, with_slopes  # noqa: E402

TABLES = ROOT / "outputs/tables"
OUT = tagged(TABLES / "step_estimator_hydro_results.csv")
ROWS = TABLES / "step_estimator_hydro_rows.parquet"
FIRST, LAST = "201901", "202509"
HYDRO_SHARE = 0.9
FLOOR = 20
MIN_ROWS = 20_000
WEAK_F = 10.0
# Movhera's Douro dams, offered inside ADOURO after their sale (lib/unit_ownership.UNIT_SHARES): whose
# stake those offers answer to is not known, so ADOURO is left out over the window (2026-10-21)
AMBIGUOUS = [("ADOURO", "2020-12-17", "2021-09-09")]


def months() -> list[str]:
    return [m for m in sorted(p.stem.split("_")[1] for p in CACHE.glob("hmoments_2*.parquet")) if FIRST <= m <= LAST]


def flat_days(h: pd.DataFrame) -> pd.DataFrame:
    """unit, date, flat: the unit offered the identical curve (every price and quantity)
    in all 24 hours of the day."""
    # an hour's curve as the (wrapping) sum of its steps' hashes: equal curves, equal sums
    k = pd.util.hash_pandas_object(pd.DataFrame({"p": np.round(h.price, 2), "m": np.round(h.mw, 1)}), index=False)
    sig = h.assign(k=k.astype("uint64").to_numpy()).groupby(["unit", "date", "hid"]).k.sum().rename("sig")
    s = sig.reset_index().groupby(["unit", "date"]).agg(hours=("hid", "nunique"), curves=("sig", "nunique"))
    return s.assign(flat=(s.hours == 24) & (s.curves == 1)).reset_index()[["unit", "date", "flat"]]


def rows(sim: int | None = None) -> pd.DataFrame:
    """Hydro unit-steps with their moments; with `sim`, the simulated price-takers of
    `step_engine.py --sim` (steps at their simulated prices, flat days as offered)."""
    parts = []
    ms = [ym for ym in months() if sim is None or (CACHE / f"hsim{sim}_moments_{ym}.parquet").exists()]
    if len(ms) < len(months()):
        print(f"  simulated seed {sim}: {len(ms)} of {len(months())} months on disk ({ms[0]}–{ms[-1]})", flush=True)
    for ym in ms:
        m = pd.read_parquet(CACHE / (f"hsim{sim}_moments_{ym}.parquet" if sim is not None else f"hmoments_{ym}.parquet"))
        h = pd.read_parquet(CACHE / f"hydro_{ym}.parquet")
        h["date"] = pd.to_datetime(h.date)
        fl = flat_days(h)
        if sim is not None:
            h = pd.read_parquet(CACHE / f"hsim{sim}_units_{ym}.parquet")
            h["date"] = pd.to_datetime(h.date)
        u = h[~h.withdrawn & h.group.notna() & (h.price > 1.0)]
        tot = u.groupby(["hid", "group", "price"]).mw.sum().rename("hy_mw").reset_index()
        m = m.merge(tot, on=["hid", "group", "price"], how="inner")
        m = m[m.hy_mw >= HYDRO_SHARE * m.v_sell]
        d = u.merge(m, on=["hid", "group", "price"], how="inner").merge(fl, on=["unit", "date"], how="left")
        hr = pd.read_parquet(CACHE / f"hours_{ym}.parquet", columns=["hid", "period", "utc", "p_star"])
        parts.append(d.merge(hr, on="hid"))
        print(f"  {ym}: {len(parts[-1]):,} hydro unit-steps with draws", flush=True)
    d = pd.concat(parts, ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    for u, a, b in AMBIGUOUS:
        d = d[~((d.unit == u) & (d.date >= a) & (d.date < b))]
    return d


def add_instruments(d: pd.DataFrame) -> pd.DataFrame:
    d = instruments(d)                       # dose_unpl, dose_plan, Wdev_fc (step_estimator)
    fc = forecasts()
    fc["utc"] = pd.to_datetime(fc.utc, utc=True)
    return d.merge(fc, on="utc", how="left")


def derive(d: pd.DataFrame) -> pd.DataFrame:
    sbar = d.m_s / d.m_n.where(d.m_n > 0)
    for f in FLOORS:
        d[f"Xt{f}"] = np.where(sbar >= f, d.m_sn / d.m_s.where(d.m_s > 0), np.nan)
    d["Xt"] = d[f"Xt{FLOOR}"]
    sbar_rel = d.m_s_rel / d.m_n.where(d.m_n > 0)
    d["Xt_rel"] = np.where(sbar_rel >= FLOOR, d.m_sn / d.m_s_rel.where(d.m_s_rel > 0), np.nan)
    d["Xp"], d["Xm"] = d.Xt.clip(lower=0), d.Xt.clip(upper=0)
    d["pos"] = np.minimum(9, ((d.mw_below + d.mw / 2) / d.cap_mw * 10).fillna(0).astype(int).clip(0, 9))
    d["five"] = d.group.isin(FIRMS)
    d["flat"] = d.flat.fillna(False).astype(bool)
    return d


def zf(d: pd.DataFrame) -> list[str]:
    """group × F_wind and group × F_solar for groups with MIN_ROWS rows or more."""
    n = d.group.value_counts()
    cols = []
    for g in sorted(n[n >= MIN_ROWS].index):
        on = (d.group == g).to_numpy(float)
        for k, c in (("Fw", "F_wind"), ("Fs", "F_solar")):
            d[f"{k}_{g}"] = on * d[c].to_numpy()
            cols.append(f"{k}_{g}")
    return cols


def fe_codes(s: pd.DataFrame) -> list[np.ndarray]:
    ud = s.unit + "_" + s.date.dt.strftime("%Y%m%d")
    ch = s.cls + "_" + s.hid.astype(str)
    cp = s.cls + "_" + s.pos.astype(str)
    return [pd.factorize(c)[0] for c in (ud, ch, cp)]


def est(d: pd.DataFrame, label: str, zs: list[str] | str, x: str = "Xt", xs2: tuple | None = None,
        y: str = "price", fe=fe_codes, ws: tuple = (), slopes: tuple = (), slopes_by: str | None = None) -> dict:
    """Weighted 2SLS of the step price (or `y`) on X̃ (or on X̃⁺ and X̃⁻ when xs2 is given),
    with the fixed effects `fe(rows)` (unit × day, class × hour, class × position by default),
    the exogenous controls `ws`, and a slope for every unit on the columns `slopes` (absorbed
    with the first fixed effect)."""
    s = d.dropna(subset=[x, "m_n", y]).copy()
    if isinstance(zs, str) and zs == "firm forecasts":
        zs = zf(s)
    zs, ws, slopes = list(zs), list(ws), list(slopes)
    xs = list(xs2) if xs2 else [x]
    s = s[(s.m_n > 0) & np.isfinite(s[[y, *xs, *zs, *ws, *slopes]].to_numpy(float)).all(axis=1)]
    row = {"sample": label, "x": "+".join(xs), "instruments": ", ".join(zs) if len(zs) <= 3 else f"{len(zs)} firm × forecast",
           "controls": ", ".join(ws), "unit_slopes": ", ".join(slopes), "n": len(s), "units": s.unit.nunique(),
           "groups": s.group.nunique(), "mean_x": np.average(s[xs[0]], weights=s.m_n)}
    if len(s) < 5000:
        print(f"  {label:58s} too few rows ({len(s):,})")
        return row | {"status": "too few rows"}
    wt = s.m_n.to_numpy(float)
    M = wdemean(s[[y, *xs, *zs, *ws]].to_numpy(float), with_slopes(fe(s), s, slopes, wt, slopes_by), wt)
    r = np.sqrt(wt)
    k, L = len(xs), len(zs)
    Y, X, Z = M[:, 0] * r, M[:, 1:1 + k] * r[:, None], M[:, 1 + k:1 + k + L] * r[:, None]
    W0 = M[:, 1 + k + L:] * r[:, None]
    keep = np.abs(Z).sum(axis=0) > 0
    Z = Z[:, keep]
    if W0.shape[1]:                         # controls partialled out of the least-squares fit too
        Pw = W0 @ np.linalg.lstsq(W0, np.column_stack([Y, X]), rcond=None)[0]
        Yl, Xl = Y - Pw[:, 0], X - Pw[:, 1:]
    else:
        Yl, Xl = Y, X
    cl = s.date.dt.strftime("%G%V").to_numpy()
    inv = np.linalg.inv(Xl.T @ Xl)
    b_ls = inv @ Xl.T @ Yl
    V_ls = inv @ cluster_meat(Xl, Yl - Xl @ b_ls, cl) @ inv
    for j, xn in enumerate(xs):
        row |= {f"b_ls_{xn}": b_ls[j], f"se_ls_{xn}": np.sqrt(V_ls[j, j])}
    txt = "LS " + " ".join(f"{b_ls[j]:+.3f} ({np.sqrt(V_ls[j, j]):.3f})" for j in range(k))
    if Z.shape[1] >= k:
        b, V = tsls_k(Y, X, Z, W0, cl)
        F = [sw_f(X, Z, W0, cl, j) for j in range(k)]
        for j, xn in enumerate(xs):
            row |= {f"b_iv_{xn}": b[j], f"se_iv_{xn}": np.sqrt(V[j, j]), f"F_{xn}": F[j]}
        row["status"] = "weak" if min(F) < WEAK_F else "ok"
        txt += "  IV " + " ".join(f"{xn} {b[j]:+.3f} ({np.sqrt(V[j, j]):.3f}, F {F[j]:.1f})" for j, xn in enumerate(xs))
        if k == 1:
            ar, p0, p1 = ar_grid(Y, X[:, 0], Z, W0, cl)
            row |= {"ar_set": ar, "ar_p0": p0, "ar_p1": p1}
            txt += f"  AR p(0) {p0:.3g} p(1) {p1:.3g}  set {ar}"
        else:
            dlt = np.array([1.0, -1.0])
            row["p_equal"] = float(2 * (1 - __import__("scipy.stats").stats.norm.cdf(
                abs(dlt @ b) / np.sqrt(dlt @ V @ dlt))))
            txt += f"  p(β⁺ = β⁻) {row['p_equal']:.3g}"
    print(f"  {label:58s} n={len(s):>9,}  {txt}{'  WEAK' if row.get('status') == 'weak' else ''}", flush=True)
    return row


def describe(d: pd.DataFrame) -> None:
    p = d[d.m_n > 0]
    print(f"\n{len(p):,} hydro unit-steps set the price in at least one draw ({p.unit.nunique()} units); "
          f"flat unit-days {p.flat.mean():.3f} of them")
    g = p.groupby("group").apply(lambda x: pd.Series({
        "steps": len(x), "units": x.unit.nunique(), "flat": x.flat.mean(),
        "X_tilde": np.average(x.Xt.fillna(0), weights=x.m_n), "price": np.average(x.price, weights=x.m_n)}),
        include_groups=False)
    print(g.sort_values("steps", ascending=False).round(2).to_string())


def main() -> int:
    if "--reuse" in sys.argv and ROWS.exists():        # instruments recomputed: they depend on --locations
        d = add_instruments(pd.read_parquet(ROWS).drop(columns=INSTRUMENTS + list(FORECASTS)))
    else:
        d = add_instruments(rows())
        d.to_parquet(ROWS, index=False)
    d = derive(d)
    describe(d)
    p = d[(d.m_n > 0) & ~d.flat]
    a = d[d.m_n > 0]
    res = []
    print("\nPRICE OF A HYDRO STEP: b = λ_ud + β·X̃ (unit × day, class × hour, class × position effects)")
    res.append(est(p, "all, firm × forecast instruments", "firm forecasts"))
    res.append(est(a, "flat unit-days included", "firm forecasts"))
    res.append(est(p, "reactor outages", ["dose_unpl", "dose_plan"]))
    res.append(est(p, "regional wind deviation", ["Wdev_fc"]))
    res.append(est(p, "slope floor 5", "firm forecasts", x="Xt5"))
    res.append(est(p, "slope floor 50", "firm forecasts", x="Xt50"))
    res.append(est(p[p.Xt.abs() <= 30], "|X̃| ≤ 30", "firm forecasts"))
    res.append(est(p, "price-scaled band (±5% of p)", "firm forecasts", x="Xt_rel"))
    res.append(est(p[p.date < "2024-01-01"], "2019–2023", "firm forecasts"))
    res.append(est(p[p.date >= "2024-01-01"], "2024 – 2025-09", "firm forecasts"))
    res.append(est(p[p.five], "five firms only", "firm forecasts"))
    res.append(est(p[p.cls == "hydro"], "storage hydro only (no pumped)", "firm forecasts"))
    print("\nBY SIGN OF X̃ (β⁺ for net sellers, β⁻ for net buyers; leg D §7)")
    res.append(est(p, "two slopes, firm × forecast instruments", "firm forecasts", xs2=("Xp", "Xm")))
    res.append(est(p[p.date >= "2024-01-01"], "two slopes, 2024 – 2025-09", "firm forecasts", xs2=("Xp", "Xm")))
    pd.DataFrame(res).to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
