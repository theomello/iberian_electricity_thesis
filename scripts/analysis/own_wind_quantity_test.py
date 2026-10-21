#!/usr/bin/env python3
"""Own wind as the shock: when a firm's own wind blows, does it cut its other plants in
proportion to the wind (book balancing) or to the wind's effect on the price (market power)?

    .venv/bin/python scripts/analysis/own_wind_quantity_test.py --panel
    .venv/bin/python scripts/analysis/own_wind_quantity_test.py --test --step 1
    .venv/bin/python scripts/analysis/own_wind_quantity_test.py --test --step 1 --slope-groups

Spec `docs/specs/2026-10-21-own-wind-quantity-test-design.md`; plan
`docs/plans/2026-10-21-own-wind-quantity-test-step1.md`.

PANEL (`--panel` → outputs/tables/own_wind_quantity_panel.parquet, gitignored). The holiday
quantity panel's rows (five firms, weekdays, 2019-01 → 2025-09, slope ≥ FLOOR and s defined)
joined to:
  generation  from the self-supply panel (PDBF, MW, unit to its largest owner that day), by leg:
              W_s (the `wind` class: own scheduled wind), generic (OMIE's generic units: bought
              energy resold), G_other (every other class); and, both legs, g_hydro_storage,
              g_nuclear, g_thermal (gas, coal, thermal without a cost), g_rest
  own wind    W_real = Σ_r K_gr cf_rt and Wdev = Σ_r K_gr (cf_rt − cf_t), MW: located onshore
              capacity by region times its measured capacity factor, and its deviation from the
              peninsula's (`self_supply_cost.own_wind_hourly`); Wdev_fc the same with REE's D-1
              national forecast split across regions by the measured shares
  forecasts   F_wind, F_solar, F_demand: REE's D-1 peninsular forecasts (ESIOS 1777, 1779, 1775), GW
  ratios      P_W = W_s / slope (€/MWh: own wind as a move along the firm's residual demand),
              Wdev_inv = Wdev / slope, Wdev_fc_inv
Hours without own wind (fewer than 30 provinces reporting) drop out.

STEP 1 (`--test --step 1` → outputs/tables/own_wind_quantity_step1.csv). Date × hour and firm ×
month effects; controls 1/slope, own retail purchases, and a slope per firm on each D-1 forecast;
errors clustered by date. Endogenous W_s and P_W, instruments Wdev and Wdev_inv.
  first stage  W_s and P_W on both instruments; Sanderson–Windmeijer F for each
  placebo      own retail purchases on both instruments (the other controls): should be about 0
  power        se(b_P) under b_P = 0, from the residual of the model without P_W, so that b_P is
               never formed; s̄ = own offer slope weighted by |Wdev|; smallest detectable β =
               2.8 se / s̄, for other generation in total and by leg
Stop if either F < 10, or the smallest detectable β (other generation, total) exceeds 1.

SLOPE GROUPS (`--slope-groups` → outputs/tables/own_wind_quantity_step1_groups.csv; design §8,
added after step 1 stopped). Step 1 with instruments Wdev × D_k, D_k the k-th third of the firm's
own hours by 1/slope (1 flat, 3 steep), and D_2, D_3 as controls: the wind's response to Wdev may
differ by group. Also reports each group's mean 1/slope.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
for sub in ("lib", "analysis"):
    sys.path.insert(0, str(ROOT / "scripts" / sub))

T = ROOT / "outputs" / "tables"
QPANEL = T / "holiday_quantity_panel.parquet"
SPANEL = T / "self_supply_panel.parquet"
PANEL = T / "own_wind_quantity_panel.parquet"
FIRMS = ["ENDESA", "IBERDROLA", "NATURGY", "EDP", "REPSOL"]
KEY = ["group", "date", "hour"]
STEP1 = T / "own_wind_quantity_step1.csv"
STEP1_GROUPS = T / "own_wind_quantity_step1_groups.csv"
FORECASTS = ["F_wind", "F_solar", "F_demand"]
Z80 = 1.96 + 0.84
CLASSES = {"hydro_storage": "g_hydro_storage", "nuclear": "g_nuclear", "gas": "g_thermal", "coal": "g_thermal",
           "thermal_nocost": "g_thermal"}


def generation() -> pd.DataFrame:
    """KEY, W_s / generic / G_other by leg and in total, and the other classes both legs, MW."""
    g = pd.read_parquet(SPANEL, columns=KEY + ["cls", "leg", "mwh"])
    g = g[g.date.dt.dayofweek < 5]
    g["k"] = np.where(g.cls == "wind", "W_s", np.where(g.cls == "generic", "generic", "G_other"))
    legs = g.pivot_table(index=KEY, columns=["k", "leg"], values="mwh", aggfunc="sum", fill_value=0.0)
    legs.columns = [f"{k}_{leg}" for k, leg in legs.columns]
    o = g[g.k == "G_other"].assign(c=lambda x: x.cls.map(CLASSES).fillna("g_rest"))
    cls = o.pivot_table(index=KEY, columns="c", values="mwh", aggfunc="sum", fill_value=0.0)
    out = legs.join(cls, how="outer").fillna(0.0).reset_index()
    for k in ("W_s", "generic", "G_other"):
        for leg in ("auction", "bilateral"):
            if f"{k}_{leg}" not in out:
                out[f"{k}_{leg}"] = 0.0
        out[k] = out[f"{k}_auction"] + out[f"{k}_bilateral"]
    return out


def own_wind() -> pd.DataFrame:
    """KEY, utc, W_real, Wdev, Wdev_fc, F_wind, F_solar, F_demand; hours repeated on a DST day out."""
    from regional_wind_offer_test import forecasts, own_capacity, regional_cf
    from self_supply_cost import own_wind_hourly
    fc = forecasts()
    cf = regional_cf(fc)
    k = own_capacity(FIRMS)
    missing = sorted(set(FIRMS) - set(k.group))
    if missing:
        raise SystemExit(f"no located wind for {missing}: Wdev would be 0, not missing; decide before running")
    r = own_wind_hourly(k, cf).rename(columns={"Wdev_real": "Wdev"})
    f = own_wind_hourly(k, cf.assign(cf_real=cf.cf_fc, dev_real=cf.dev_fc))[["group", "utc", "Wdev_real"]]
    w = r.merge(f.rename(columns={"Wdev_real": "Wdev_fc"}), on=["group", "utc"], validate="1:1")
    w = w[~w.duplicated(KEY, keep=False)]
    return w.merge(fc, on="utc", how="inner")


def build_panel() -> int:
    q = pd.read_parquet(QPANEL)
    n0 = len(q)
    q = q[q.slope.notna() & q.s.notna()]
    n1 = len(q)
    q = q.merge(generation(), on=KEY, how="left", validate="1:1")
    gcols = [c for c in q.columns if c.startswith(("W_s", "generic", "G_other", "g_"))]
    q[gcols] = q[gcols].fillna(0.0)
    q = q.merge(own_wind(), on=KEY, how="inner", validate="1:1")
    q = q.dropna(subset=["F_wind", "F_solar", "F_demand", "Wdev_fc"])
    q["P_W"] = q.W_s * q.inv_slope
    q["Wdev_inv"] = q.Wdev * q.inv_slope
    q["Wdev_fc_inv"] = q.Wdev_fc * q.inv_slope
    q.to_parquet(PANEL, index=False)
    print(f"\nwrote {PANEL.relative_to(ROOT)}: {len(q):,} firm-hours of {n1:,} with slope and s ({n0:,} in the "
          f"holiday panel); {q.date.nunique():,} days")
    by = q.groupby("group")
    tab = pd.DataFrame({"hours": by.size(), "W_s MW": by.W_s.mean(), "bilateral share": by.W_s_bilateral.sum() / by.W_s.sum(),
                        "W_real MW": by.W_real.mean(), "Wdev sd": by.Wdev.std(), "G_other MW": by.G_other.mean(),
                        "corr(W_s, W_real)": by.apply(lambda x: x.W_s.corr(x.W_real), include_groups=False)})
    print(tab.round(3).to_string())
    return 0


def prep(d: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """The columns net of date × hour and firm × month effects."""
    from holiday_quantity_test import resid
    return resid(d, cols)


def controls_for(d: pd.DataFrame) -> list[str]:
    """Adds one column per forecast and firm (the first firm, alphabetically, left out: with date ×
    hour effects the five sum to the forecast itself) and returns the control list."""
    out = ["inv_slope", "retail"]
    for g in sorted(d.group.unique())[1:]:
        on = (d.group == g).to_numpy(float)
        for f in FORECASTS:
            d[f"{f}_{g}"] = on * d[f].to_numpy(float)
            out.append(f"{f}_{g}")
    return out


def group_instruments(d: pd.DataFrame, col: str = "Wdev") -> tuple[list[str], list[str]]:
    """Adds slope_group (1 flat … 3 steep: thirds of each firm's own hours by 1/slope), col × D_k
    for k = 1, 2, 3, and dummies D_2, D_3; returns (instruments, dummies)."""
    r = d.groupby("group").inv_slope.rank(method="first")
    n = d.groupby("group").inv_slope.transform("size")
    d["slope_group"] = (np.ceil(3 * r / n)).astype(int).clip(1, 3)
    inst = []
    for k in (1, 2, 3):
        d[f"{col}_g{k}"] = d[col].where(d.slope_group == k, 0.0)
        inst.append(f"{col}_g{k}")
    for k in (2, 3):
        d[f"D_{k}"] = (d.slope_group == k).astype(float)
    return inst, ["D_2", "D_3"]


def _clusters(d: pd.DataFrame, cluster: str = "date") -> np.ndarray:
    return (d.date.dt.strftime("%G%V") if cluster == "week" else d.date.dt.strftime("%Y%m%d")).to_numpy()


def fit_iv(d: pd.DataFrame, y: str, endog: list[str], inst: list[str], controls: list[str],
           cluster: str = "date") -> dict:
    """Two-stage least squares of y on endog, instruments inst, after the effects and with the
    controls; {endog: (b, se)}, se clustered."""
    from iv_two_endog import tsls_k
    k, L = len(endog), len(inst)
    M = prep(d, [y] + endog + inst + controls)
    b, V = tsls_k(M[:, 0], M[:, 1:1 + k], M[:, 1 + k:1 + k + L], M[:, 1 + k + L:], _clusters(d, cluster))
    return {e: (float(b[i]), float(np.sqrt(V[i, i]))) for i, e in enumerate(endog)}


def se_null_iv(y: np.ndarray, X: np.ndarray, Z: np.ndarray, W: np.ndarray, cl: np.ndarray, j: int) -> float:
    """se of X[:, j]'s two-stage coefficient under the null that it is 0: the covariance of the
    full model, with the residual of the model without X[:, j]. The coefficient is never formed."""
    from midday_hydro_iv import cluster_meat
    Zf = np.column_stack([Z, W])
    Xr = np.column_stack([np.delete(X, j, axis=1), W])
    Hr = Zf @ np.linalg.lstsq(Zf, Xr, rcond=None)[0]
    u0 = y - Xr @ np.linalg.solve(Hr.T @ Xr, Hr.T @ y)
    Xf = np.column_stack([X, W])
    H = Zf @ np.linalg.lstsq(Zf, Xf, rcond=None)[0]
    inv = np.linalg.inv(H.T @ Xf)
    V = inv @ cluster_meat(H, u0, cl) @ inv.T
    return float(np.sqrt(V[j, j]))


def step1(groups: bool = False) -> int:
    from holiday_quantity_test import ols
    from iv_two_endog import sw_f
    d = pd.read_parquet(PANEL)
    ctrl = controls_for(d)
    ys, X_, Z_ = ["G_other", "G_other_auction", "G_other_bilateral"], ["W_s", "P_W"], ["Wdev", "Wdev_inv"]
    rows = []
    if groups:
        Z_, dums = group_instruments(d)
        ctrl = ctrl + dums
        for k, x in d.groupby("slope_group"):
            rows.append({"part": "slope group", "y": "mean 1/slope", "x": f"group {k}", "b": x.inv_slope.mean(),
                         "median_slope": x.slope.median(), "hours": len(x)})
    L = len(Z_)
    M = prep(d, ys + X_ + Z_ + ctrl)
    Y, X, Z, W = M[:, :3], M[:, 3:5], M[:, 5:5 + L], M[:, 5 + L:]
    cl = _clusters(d)
    for j, x in enumerate(X_):
        b, se = ols(X[:, j], np.column_stack([Z, W]), cl)
        F = sw_f(X, Z, W, cl, j)
        for i, z in enumerate(Z_):
            rows.append({"part": "first stage", "y": x, "x": z, "b": b[i], "se": se[i], "t": b[i] / se[i], "F_sw": F})
    ir = ctrl.index("retail")
    Wp = np.delete(W, ir, axis=1)
    b, se = ols(W[:, ir], np.column_stack([Z, Wp]), cl)
    for i, z in enumerate(Z_):
        rows.append({"part": "placebo", "y": "retail", "x": z, "b": b[i], "se": se[i], "t": b[i] / se[i]})
    a = d.Wdev.abs().to_numpy()
    s_bar = float(np.average(d.s.to_numpy(float), weights=a))
    for i, y in enumerate(ys):
        sn = se_null_iv(Y[:, i], X, Z, W, cl, 1)
        rows.append({"part": "power", "y": y, "x": "P_W", "se": sn, "s_bar": s_bar, "mde_beta": Z80 * sn / s_bar})
    out = pd.DataFrame(rows)
    out["n"] = len(d)
    out.to_csv(STEP1_GROUPS if groups else STEP1, index=False)
    with pd.option_context("display.width", 160, "display.float_format", "{:.4g}".format):
        print(out.drop(columns="n").to_string(index=False))
    print(f"\n{len(d):,} firm-hours, {d.date.nunique():,} days; s̄ (own offer slope, |Wdev|-weighted) {s_bar:.1f} MW "
          f"per €/MWh; P_W median {d.P_W.median():.2f}, Wdev_inv sd {d.Wdev_inv.std():.3f} €/MWh")
    fs = out[out.part == "first stage"].groupby("y").F_sw.first()
    pw = out[(out.part == "power") & (out.y == "G_other")].iloc[0]
    pl = out[out.part == "placebo"]
    stops = {f"first-stage F for {x} {fs[x]:.1f} < 10": fs[x] < 10 for x in X_}
    stops[f"smallest detectable β {pw.mde_beta:.2f} > 1 (se(b_P) {pw.se:.2f} under b_P = 0, Nash −{s_bar:.1f})"] = pw.mde_beta > 1
    for k, v in stops.items():
        print(f"  {'STOP' if v else 'ok  '} {k}")
    print("  placebo (no stop rule): " + ", ".join(f"retail on {r.x} t {r.t:+.2f}" for r in pl.itertuples()))
    if groups:
        print("  slope groups: 'b' is the group's mean 1/slope")
    print(f"stop rule (step 1): {'STOP' if any(stops.values()) else 'CONTINUE'}")
    return 0


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--panel", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--slope-groups", action="store_true")
    args = ap.parse_args()
    if args.panel:
        return build_panel()
    if args.test and args.step == 1:
        return step1(groups=args.slope_groups)
    raise SystemExit("--panel, or --test --step 1")


if __name__ == "__main__":
    sys.exit(main())
