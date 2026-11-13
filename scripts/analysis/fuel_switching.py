"""Fuel switching between coal and gas in Iberian dispatch (docs/specs/2026-11-13-fuel-switching-scope.md).

    .venv/bin/python scripts/analysis/fuel_switching.py

Fleet: daily utilisation of the plant-specific coal and gas units of the step cache (cleared MW-hours over available MW-hours), bid-time cost ratio r = ln(c_coal / c_gas) (capacity weighted).
Main estimator: Poisson pseudo-ML of coal utilisation u_c (zeros kept) with offset ln u_g, E[u_c] = u_g exp(f(r) + gamma R + months), f a cubic spline with interior knots at the terciles of r
(truncated-power form), standard errors clustered by week. sigma = -f'(median r). VES: f quadratic, sigma(r) = sigma0 + sigma1 r. Unit level: logit of dispatch on ln p* - ln c by fuel.
Writes outputs/tables/fuel_switching_*.csv and prints F1-F6.

Reusable: the window, the fuels and the cost columns are arguments of the functions; nothing assumes Spain except the cache's schema.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent.parent
STEP = ROOT / "outputs" / "cache" / "step"
OUT = ROOT / "outputs" / "tables"
SEED = 20261113
NSHIFT = 200


def months(a, b):
    return [d.strftime("%Y%m") for d in pd.date_range(pd.Timestamp(a).replace(day=1), b, freq="MS")]


def load_unit_hours(yms):
    parts = []
    for ym in yms:
        u = pd.read_parquet(STEP / f"units_{ym}.parquet", columns=["hid", "unit", "fuel", "cap_mw", "cost", "cleared_mw", "withdrawn"])
        g = u.groupby(["hid", "unit", "fuel"]).agg(cap=("cap_mw", "max"), cost=("cost", "first"), cl=("cleared_mw", "first"), wd=("withdrawn", "max")).reset_index()
        h = pd.read_parquet(STEP / f"hours_{ym}.parquet", columns=["hid", "date", "p_star", "valid", "F_demand", "F_wind", "F_solar"])
        h = h[h.valid.astype(bool)]
        parts.append(g.merge(h, on="hid"))
    uh = pd.concat(parts, ignore_index=True)
    uh["date"] = pd.to_datetime(uh.date)
    uh["fuel"] = uh.fuel.astype(str)
    return uh[uh.cap.notna() & (uh.cap > 0)]


def daily(uh):
    cols = []
    for fu in ("coal", "gas"):
        g = uh[uh.fuel == fu]
        d = g.assign(cc=g.cost * g.cap).groupby("date").agg(cl=("cl", "sum"), cap=("cap", "sum"), cc=("cc", "sum"))
        d["u"], d["cost"] = d.cl / d.cap, d.cc / d.cap
        cols.append(d[["cl", "cap", "u", "cost"]].add_suffix(f"_{fu[0]}"))
    D = pd.concat(cols, axis=1).dropna()
    hrs = uh.drop_duplicates("hid")
    D["R"] = hrs.assign(R=hrs.F_demand - hrs.F_wind - hrs.F_solar).groupby("date").R.mean().reindex(D.index)
    D["capt"] = (uh.groupby("date").cap.sum() / hrs.groupby("date").size()).reindex(D.index)
    D["Rcap"] = D.R / D.capt
    D["r"] = np.log(D.cost_c / D.cost_g)
    D["week"] = pd.factorize(D.index.to_period("W").astype(str))[0]
    D["month"] = D.index.month
    return D


def basis(z, k):
    return np.column_stack([z, z ** 2, z ** 3, np.clip(z - k[0], 0, None) ** 3, np.clip(z - k[1], 0, None) ** 3])


def dbasis(z, k):
    return np.column_stack([np.ones_like(z), 2 * z, 3 * z ** 2, 3 * np.clip(z - k[0], 0, None) ** 2, 3 * np.clip(z - k[1], 0, None) ** 2])


def design(D, r, kind="spline", control=True, extra=None):
    mu, sd = r.mean(), r.std()
    z = (r - mu) / sd
    k = np.quantile(z, [1 / 3, 2 / 3])
    B = basis(z, k) if kind == "spline" else np.column_stack([z, z ** 2])
    cols = [B]
    if control:
        cols.append(D.Rcap.to_numpy()[:, None])
    if extra is not None:
        cols.append(np.asarray(extra)[:, None])
    cols.append(pd.get_dummies(D.month, drop_first=True, dtype=float).to_numpy())
    X = sm.add_constant(np.column_stack(cols), has_constant="add")
    return X, z, k, mu, sd, B.shape[1]


def fit(D, r=None, y="u_c", off="u_g", kind="spline", control=True, extra=None, ols=False):
    r = D.r.to_numpy() if r is None else r
    X, z, k, mu, sd, nb = design(D, r, kind, control, extra)
    if ols:
        m = sm.OLS(np.log(D[y] / D[off]).to_numpy(), X).fit(cov_type="cluster", cov_kwds={"groups": D.week.to_numpy()})
    else:
        m = sm.GLM(D[y].to_numpy(), X, family=sm.families.Poisson(), offset=np.log(D[off].to_numpy())).fit(cov_type="cluster", cov_kwds={"groups": D.week.to_numpy()})
    b, V = m.params, m.cov_params()
    z0 = float(np.median(z))
    if kind == "spline":
        g = -dbasis(np.array([z0]), k)[0] / sd
        idx = slice(1, 6)
    else:
        g = -np.array([1.0, 2 * z0]) / sd
        idx = slice(1, 3)
    sig = float(g @ b[idx])
    se = float(np.sqrt(g @ V[idx, idx] @ g))
    out = dict(sigma=sig, se=se, t=sig / se, median_r=float(np.median(r)), n=len(D))
    if kind == "spline":
        Vn = V[2:6, 2:6]
        W = float(b[2:6] @ np.linalg.solve(Vn, b[2:6]))
        out.update(wald_linear=W, p_linear=float(1 - stats.chi2.cdf(W, 4)))
    else:
        c, sec = b[2], np.sqrt(V[2, 2])
        out.update(sigma1=float(-2 * c / sd ** 2), sigma1_se=float(2 * sec / sd ** 2), t_c=float(c / sec))
        # sigma at parity r = 0
        z_par = (0 - mu) / sd
        out["sigma_at_zero"] = float(-(b[1] + 2 * c * z_par) / sd)
    return out, m


def unit_logit(uh):
    s = uh[(uh.p_star > 0) & (uh.cost > 0) & (~uh.wd.astype(bool))].copy()
    s["x"] = np.log(s.p_star) - np.log(s.cost)
    near = s[s.x.abs() <= 0.5].copy()
    near["y"] = (near.cl > 0).astype(float)
    near["coal"] = (near.fuel == "coal").astype(float)
    near["xc"] = near.x * near.coal
    X = sm.add_constant(near[["x", "coal", "xc"]])
    m = sm.Logit(near.y, X).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(near.unit)[0]})
    wald = float(m.params["xc"] ** 2 / m.cov_params().loc["xc", "xc"])
    below = s[(s.cost + 5) < s.p_star]
    share = below.groupby("fuel").apply(lambda g: (g.cl > 0).mean())
    return dict(slope_gas=float(m.params["x"]), slope_coal=float(m.params["x"] + m.params["xc"]), diff=float(m.params["xc"]), diff_t=float(m.params["xc"] / np.sqrt(m.cov_params().loc["xc", "xc"])),
                p_equal=float(1 - stats.chi2.cdf(wald, 1)), n=len(near), share_dispatched_gas=float(share.get("gas", np.nan)), share_dispatched_coal=float(share.get("coal", np.nan)),
                n_below_gas=int((below.fuel == "gas").sum()), n_below_coal=int((below.fuel == "coal").sum()))


def main():
    A0, A1 = "2019-01-01", "2020-02-29"
    uh_all = load_unit_hours(months(A0, "2020-03-31") + months("2020-07-01", "2020-12-31"))   # March 2020 only for the 30-day lead of the cost ratio; 2020 H2 for F5
    D_all = daily(uh_all)
    D = D_all.loc[A0:A1].copy()
    uhA = uh_all[(uh_all.date >= A0) & (uh_all.date <= A1)]
    res = []

    # F1 feasibility
    ncoal = uhA[uhA.fuel == "coal"].unit.nunique()
    capc = float(D.cap_c.sum() / uhA.drop_duplicates("hid").shape[0])
    f1 = bool(ncoal >= 15 and capc >= 5000 and D.r.std() >= 0.10)
    print(f"F1 window A: {len(D)} days, coal units {ncoal}, mean available coal capacity {capc:.0f} MW, sd of the daily ln cost ratio {D.r.std():.3f}; days with zero coal output {int((D.u_c == 0).sum())}: {f1}", flush=True)

    # main: spline PPML
    main_, m = fit(D)
    ves, _ = fit(D, kind="ves")
    print(f"F2 sigma at the median ratio ({main_['median_r']:.3f}): {main_['sigma']:.3f} (se {main_['se']:.3f}, t {main_['t']:.2f})", flush=True)
    print(f"F4 spline against linear: Wald {main_['wald_linear']:.2f}, p {main_['p_linear']:.4f}; VES: sigma0 (median) {ves['sigma']:.3f}, sigma1 {ves['sigma1']:.3f} (se {ves['sigma1_se']:.3f}, t on the quadratic term {ves['t_c']:.2f}), sigma at parity {ves['sigma_at_zero']:.3f}", flush=True)
    # sigma along the curve
    zg = np.linspace(D.r.quantile(0.1), D.r.quantile(0.9), 5)
    X, z, k, mu, sd, nb = design(D, D.r.to_numpy())
    curve = [float(-(dbasis(np.array([(rv - mu) / sd]), k)[0] @ m.params[1:6]) / sd) for rv in zg]
    print("   spline sigma(r) at the 10/30/50/70/90th percentile of r:", np.round(curve, 3), "r =", np.round(zg, 2), flush=True)
    res.append(dict(row="F2/F4 spline", **main_))
    res.append(dict(row="F4 VES (quadratic)", **ves))

    # F3a lead
    r_ser = D_all.r
    lead = pd.Series({d: r_ser.loc[d + pd.Timedelta(days=1): d + pd.Timedelta(days=30)].mean() if r_ser.loc[d + pd.Timedelta(days=1): d + pd.Timedelta(days=30)].count() == 30 else np.nan for d in D.index})
    ok = lead.notna().to_numpy()
    Dl = D[ok]
    f3a, _ = fit(Dl, extra=lead[ok].to_numpy())
    Xl, *_ = design(Dl, Dl.r.to_numpy(), extra=lead[ok].to_numpy())
    ml = sm.GLM(Dl.u_c.to_numpy(), Xl, family=sm.families.Poisson(), offset=np.log(Dl.u_g.to_numpy())).fit(cov_type="cluster", cov_kwds={"groups": Dl.week.to_numpy()})
    t_lead = float(ml.params[6] / np.sqrt(ml.cov_params()[6, 6]))
    print(f"F3a lead of the next-30-day cost ratio: coefficient {ml.params[6]:.3f}, t {t_lead:.2f} (|t| < 2 needed); n {len(Dl)}", flush=True)

    # F3b circular shifts
    rng = np.random.default_rng(SEED)
    n = len(D)
    t_real = abs(main_["t"])
    ts = []
    for _ in range(NSHIFT):
        s = int(rng.integers(30, n - 29))
        o, _m = fit(D, r=np.roll(D.r.to_numpy(), s))
        ts.append(abs(o["t"]))
    rank = int(1 + sum(t >= t_real for t in ts))
    print(f"F3b circular shifts: real |t| {t_real:.2f}; shifted |t| median {np.median(ts):.2f}, 95th pct {np.percentile(ts, 95):.2f}, max {max(ts):.2f}; real ranks {rank} of {NSHIFT + 1} (top 10 needed)", flush=True)
    pd.DataFrame({"abs_t_shift": ts}).to_csv(OUT / "fuel_switching_placebo.csv", index=False)

    # F5 robustness
    var = {}
    var["MW instead of utilisation"], _ = fit(D, y="cl_c", off="cl_g")
    var["no residual-demand control"], _ = fit(D, control=False)
    low = D.cap_c + D.cap_g
    var["excl. 10% lowest offered capacity"], _ = fit(D[low > low.quantile(0.10)])
    pos = D[D.u_c > 0]
    var["positive-coal days only (log-linear OLS)"], _ = fit(pos, ols=True)
    B0, B1 = "2020-07-01", "2020-12-31"
    DB = D_all.loc[B0:B1].copy()
    var["window 2020-07 to 2020-12"], _ = fit(DB)
    for k_, v in var.items():
        print(f"   F5 {k_}: sigma {v['sigma']:.3f} (se {v['se']:.3f}, t {v['t']:.2f}), n {v['n']}", flush=True)
        res.append(dict(row="F5 " + k_, **v))

    # F6 unit-level logit
    f6d = unit_logit(uhA)
    print(f"F6 unit-hour logit on ln p* - ln c (|x| <= 0.5, n {f6d['n']}): slope gas {f6d['slope_gas']:.2f}, coal {f6d['slope_coal']:.2f}; equality p {f6d['p_equal']:.4f}; dispatched when cost + 5 < p*: gas {f6d['share_dispatched_gas']:.3f} (n {f6d['n_below_gas']}), coal {f6d['share_dispatched_coal']:.3f} (n {f6d['n_below_coal']})", flush=True)
    pd.DataFrame([f6d]).round(5).to_csv(OUT / "fuel_switching_unit_logit.csv", index=False)
    pd.DataFrame(res).round(5).to_csv(OUT / "fuel_switching_summary.csv", index=False)

    # rules
    f2 = bool(main_["sigma"] > 0 and main_["t"] <= -2 or (main_["sigma"] > 0 and abs(main_["t"]) >= 2))
    f2 = bool(main_["sigma"] > 0 and abs(main_["t"]) >= 2 and 0.2 <= main_["sigma"] <= 10)
    f3 = bool(abs(t_lead) < 2 and rank <= 10)
    rej = bool(main_["p_linear"] < 0.05 or abs(ves["t_c"]) >= 2)
    f5 = all(v["sigma"] > 0 and abs(v["t"]) >= 2 for k_, v in var.items() if "2020-07" not in k_) and var["window 2020-07 to 2020-12"]["sigma"] > 0
    f6 = bool(f6d["share_dispatched_gas"] >= 0.9 and f6d["share_dispatched_coal"] >= 0.9 and f6d["p_equal"] > 0.05)
    print(f"\nF1 feasibility: {f1}")
    print(f"F2 sign and size (sigma {main_['sigma']:.3f} in [0.2, 10], |t| >= 2, f' < 0): {f2}")
    print(f"F3 placebo (lead |t| < 2 and rank <= 10): {f3}")
    print(f"F4 constant sigma {'REJECTED: the flexible curve is the result' if rej else 'not rejected'} (spline p {main_['p_linear']:.4f}; VES quadratic t {ves['t_c']:.2f})")
    print(f"F5 robustness (sign and |t| >= 2 in each; sign only in 2020 H2): {f5}")
    print(f"F6 merit-order consistency (>= 90% dispatched for each fuel, equal slopes at 5%): {f6}")


if __name__ == "__main__":
    main()
