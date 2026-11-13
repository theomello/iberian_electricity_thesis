"""Elasticity of substitution across tariff periods (docs/specs/2026-11-13-ces-substitution-design.md).

Daily weekday shares of E0 load in three period types (peak, mid, valley). Tastes: a LASSO of ln(q_k/q_V) on weather and month before the reform (the paper's first step, daily), plus
Portugal's residual of the same ratio as the common-shape control. Share system (CES, quantity form): w_k = w0_k (p_k/pbar_k)^(-sigma) / sum_j w0_j (p_j/pbar_j)^(-sigma), w0 the
taste-path shares at the reference prices pbar (pre-reform means). Estimated by nonlinear IV (GMM, 2SLS weight) with the policy price ratios, weather and month as instruments, standard
errors clustered by week. Writes outputs/tables/tou_ces_*.csv and prints S1-S6.

Reusable: the period hours, the control series, the window and the instruments are arguments; nothing is specific to Spain except the data frames.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats
from sklearn.preprocessing import PolynomialFeatures

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_area_panel as AP  # noqa: E402
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_elasticity_paper as EL  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_lasso_paper as L  # noqa: E402

OUT = T.OUT
POST0, POST1 = pd.Timestamp("2021-06-01"), pd.Timestamp("2021-09-14")
PRE0, PRE1 = pd.Timestamp("2018-01-01"), pd.Timestamp("2020-12-31")
K = ["P", "M", "V"]
HOURS = {"P": [10, 11, 12, 13, 18, 19, 20, 21], "M": [8, 9, 14, 15, 16, 17, 22, 23], "V": list(range(8))}
HK = {h: k for k, hs in HOURS.items() for h in hs}
PLACEBO_STARTS = list(pd.date_range("2019-01-01", "2019-09-01", freq="MS"))
PANEL = T.ROOT / "outputs" / "tables" / "regulated_area_panel"


# ------------------------------------------------------------------ data
def daily_frame():
    x = D.prep(T.build("e0", end="2021-09-14"))
    p, ebar = EL.prices()
    x = x.merge(p, on=["date", "hour"], how="left")
    q = pd.read_parquet(PANEL / "regulated_area_hourly.parquet")
    q = q[q.area == "PORTUGAL"]
    loc = q.utc_timestamp.dt.tz_convert("Europe/Lisbon")
    ptu = pd.DataFrame({"date": pd.to_datetime(loc.dt.date.to_numpy()), "hour": loc.dt.hour.to_numpy(), "load_ptu": q.load_mw.to_numpy()}).drop_duplicates(["date", "hour"])
    x = x.merge(ptu, on=["date", "hour"], how="left")
    x["k"] = x.hour.map(HK)
    g = x.groupby("date")
    ok = (g.hour.count() == 24) & g.load_es.apply(lambda s: s.notna().all()) & g.load_pt.apply(lambda s: s.notna().all()) & g.price.apply(lambda s: s.notna().all())
    x = x[x.date.isin(ok[ok].index)]
    d = pd.DataFrame(index=sorted(x.date.unique()))
    d.index.name = "date"
    for name, col in (("es", "load_es"), ("pt", "load_pt"), ("ptu", "load_ptu")):
        s = x.pivot_table(index="date", columns="k", values=col, aggfunc="sum")
        for k in K:
            d[f"q_{name}_{k}"] = s[k]
    pr = x.pivot_table(index="date", columns="k", values="price", aggfunc="mean")
    ch = x.pivot_table(index="date", columns="k", values="charge", aggfunc="mean")
    for k in K:
        d[f"p_{k}"] = pr[k]
        d[f"pol_{k}"] = ch[k] + ebar
    for nm, c in (("es", "temp_es"), ("pt", "temp_pt")):
        d[f"tmean_{nm}"], d[f"tmin_{nm}"], d[f"tmax_{nm}"] = g[c].mean(), g[c].min(), g[c].max()
    first = x.groupby("date").first()
    d["es_work"] = (first.kind == "work")
    d["pt_work"] = (first.dow < 5) & (first.hol_pt == 0)
    d = d.reset_index()
    d["month"] = d.date.dt.month
    d["year"] = d.date.dt.year
    d["week"] = d.date.dt.to_period("W").astype(str)
    covid = d.date.between(*EV.COVID)
    d["pre"] = d.date.between(PRE0, PRE1) & ~covid
    d["post"] = d.date.between(POST0, POST1)
    d["both"] = d.es_work & d.pt_work
    return d, ebar


# ------------------------------------------------------------------ tastes (LASSO on the daily log ratio)
def taste_pred(d, y, ctry, excl=()):
    tm, tn, tx = d[f"tmean_{ctry}"], d[f"tmin_{ctry}"], d[f"tmax_{ctry}"]
    B = pd.concat([pd.get_dummies(d.month.astype(str), prefix="m", dtype=float), tm.rename("t"), tn.rename("tmin"), tx.rename("tmax")], axis=1)
    P = pd.DataFrame(PolynomialFeatures(2, include_bias=False).fit_transform(B.to_numpy()), index=d.index)
    P = P.loc[:, ~P.T.duplicated().to_numpy()]
    tr = d.pre & d.both & ~d.year.isin(excl) & y.notna()
    mu, sd = P[tr].mean(), P[tr].std()
    keep = sd > 0
    Z = ((P.loc[:, keep] - mu[keep]) / sd[keep]).to_numpy()
    m = L.fit_one_se(Z[tr.to_numpy()], y[tr].to_numpy())
    return pd.Series(m.predict(Z), index=d.index)


def add_tastes(d, excl_sets=((), (2018,), (2019,))):
    for name, ctry in (("es", "es"), ("pt", "pt"), ("ptu", "pt")):
        for k in ("P", "M"):
            y = np.log(d[f"q_{name}_{k}"] / d[f"q_{name}_V"])
            d[f"y_{name}_{k}"] = y
            for ex in excl_sets:
                d[f"yhat_{name}_{k}_{''.join(map(str, ex)) or 'full'}"] = taste_pred(d, y, ctry, ex)
    return d


def crossfit(d, name, k):
    full = d[f"yhat_{name}_{k}_2018"].where(d.year == 2018, d[f"yhat_{name}_{k}_2019"])
    return full


# ------------------------------------------------------------------ the CES system
def design(d, rows, control="ren", ex=None, fake=None):
    """Arrays for the rows: shares, taste-path log ratios incl. the control residual, log relative prices rho, policy log prices z, instrument matrix, clusters."""
    s = d[rows]
    if control == "ptu":
        s = s[s[[f"q_ptu_{k}" for k in K]].notna().all(axis=1)]
    idx = s.index
    yh = {k: (s[f"yhat_es_{k}_full"] if ex is None else crossfit(d, "es", k).loc[idx]) for k in ("P", "M")}
    ctl = {}
    for k in ("P", "M"):
        if control == "none":
            ctl[k] = np.zeros(len(s))
        else:
            nm = "pt" if control == "ren" else "ptu"
            yhp = s[f"yhat_{nm}_{k}_full"] if ex is None else crossfit(d, nm, k).loc[idx]
            ctl[k] = (s[f"y_{nm}_{k}"] - yhp).to_numpy()
    Y0 = np.column_stack([yh["P"].to_numpy() + ctl["P"], yh["M"].to_numpy() + ctl["M"]])
    q = s[[f"q_es_{k}" for k in K]].to_numpy()
    W = q / q.sum(1, keepdims=True)
    pref = d.loc[d.pre & d.both, [f"p_{k}" for k in K]].mean().to_numpy()
    rho = np.log(s[[f"p_{k}" for k in K]].to_numpy() / pref)
    oldpol = EL.OLD
    z = np.log(s[[f"pol_{k}" for k in K]].to_numpy() / (oldpol + ebar_global()))
    if fake is not None:   # placebo: the price is the fake policy path, no endogenous part
        z = fake
        rho = fake
    tm = (s.tmean_es - d.tmean_es.mean()) / d.tmean_es.std()
    Z = np.column_stack([np.ones(len(s)), z[:, 0] - z[:, 2], z[:, 1] - z[:, 2], tm, tm ** 2, pd.get_dummies(s.month, drop_first=True, dtype=float).to_numpy()])
    Z, kept = drop_dependent(Z)
    return dict(W=W, Y0=Y0, rho=rho, z=z, Z=Z, cl=pd.factorize(s.week)[0], dates=s.date.to_numpy(), q=q, p=s[[f"p_{k}" for k in K]].to_numpy())


_EBAR = {}


def ebar_global():
    if "v" not in _EBAR:
        _EBAR["v"] = EL.prices()[1]
    return _EBAR["v"]


def drop_dependent(Z, tol=1e-9):
    """Keep the columns of Z, in order, that add rank: the policy price of each period is constant within the reform window, so the ratios are collinear with a post indicator."""
    keep = []
    for j in range(Z.shape[1]):
        cand = keep + [j]
        sv = np.linalg.svd(Z[:, cand], compute_uv=False)
        if sv[-1] > tol * sv[0]:
            keep = cand
    return Z[:, keep], keep


def shares(sig, Y0, rho):
    sig = np.atleast_1d(sig)
    sg = np.full(3, sig[0]) if len(sig) == 1 else sig
    lg = np.column_stack([Y0[:, 0] - sg[0] * rho[:, 0], Y0[:, 1] - sg[1] * rho[:, 1], -sg[2] * rho[:, 2]])
    lg -= lg.max(1, keepdims=True)
    e = np.exp(lg)
    return e / e.sum(1, keepdims=True)


def moments(sig, a):
    w = shares(sig, a["Y0"], a["rho"])
    R = a["W"][:, :2] - w[:, :2]
    return np.column_stack([R[:, 0:1] * a["Z"], R[:, 1:2] * a["Z"]])


def weight(a):
    Z = a["Z"]
    A = np.linalg.inv(Z.T @ Z / len(Z))
    L_ = Z.shape[1]
    Wt = np.zeros((2 * L_, 2 * L_))
    Wt[:L_, :L_], Wt[L_:, L_:] = A, A
    return Wt


def cluster_cov(u, cl):
    S = pd.DataFrame(u).groupby(cl).sum().to_numpy()
    return S.T @ S / len(u) ** 2


def fit(a, start=None, npar=1):
    Wt = weight(a)
    Q = lambda s: (lambda g: float(g @ Wt @ g))(moments(s, a).mean(0))
    if npar == 1:
        grid = np.linspace(-3, 8, 56)
        s0 = grid[np.argmin([Q(g) for g in grid])]
        r = optimize.minimize_scalar(lambda s: Q(s), bounds=(s0 - 0.25, s0 + 0.25), method="bounded", options={"xatol": 1e-8})
        sig = np.array([r.x])
    else:
        r = optimize.minimize(Q, start, method="Nelder-Mead", options={"xatol": 1e-7, "fatol": 1e-14, "maxiter": 4000})
        sig = r.x
    h = 1e-5
    G = np.column_stack([(moments(sig + h * e, a).mean(0) - moments(sig - h * e, a).mean(0)) / (2 * h) for e in np.eye(len(sig))])
    S = cluster_cov(moments(sig, a), a["cl"])
    Bm = np.linalg.inv(G.T @ Wt @ G)
    V = Bm @ G.T @ Wt @ S @ Wt @ G @ Bm
    gbar = moments(sig, a).mean(0)
    # J: efficient weight on the cluster covariance, ridge for the many instruments
    try:
        J = float(len(a["Z"]) * gbar @ np.linalg.pinv(S * len(a["Z"])) @ gbar)
    except Exception:
        J = np.nan
    return sig, V, J


def first_stage(a):
    out = {}
    Z, cl = a["Z"], a["cl"]
    for nm, y in (("P/V", a["rho"][:, 0] - a["rho"][:, 2]), ("M/V", a["rho"][:, 1] - a["rho"][:, 2])):
        b = np.linalg.lstsq(Z, y, rcond=None)[0]
        u = y - Z @ b
        Ai = np.linalg.inv(Z.T @ Z)
        Sg = pd.DataFrame(Z * u[:, None]).groupby(cl).sum().to_numpy()
        V = Ai @ (Sg.T @ Sg) @ Ai
        idx = [1]
        out[nm] = float(b[1] ** 2 / V[1, 1])
    return out


def main():
    d, ebar = daily_frame()
    d = add_tastes(d)
    both = d.both
    rows_real = (d.pre | d.post) & both
    A = design(d, rows_real, "ren")
    print(f"days in the estimation sample {len(A['W'])} (post window {int((d.post & both).sum())}); policy ratios (post mean) P/V {A['z'][d.loc[rows_real, 'post'].to_numpy()].mean(0).round(3)}", flush=True)
    sig, V, J = fit(A)
    se = float(np.sqrt(V[0, 0]))
    fs = first_stage(A)
    print(f"S1 first-stage F: {fs}", flush=True)
    print(f"sigma (REN control) {sig[0]:.4f} (se {se:.4f}, 95% [{sig[0] - 1.96 * se:.3f}, {sig[0] + 1.96 * se:.3f}]), J {J:.1f}", flush=True)

    # S3: implied own-hour elasticity with eta = 0
    pre = d.pre & both
    exp_sh = (d.loc[pre, [f"p_{k}" for k in K]].to_numpy() * d.loc[pre, [f"q_es_{k}" for k in K]].to_numpy())
    eP = float((exp_sh[:, 0] / exp_sh.sum(1)).mean())
    eps, se_eps = -sig[0] * (1 - eP), (1 - eP) * se
    c4 = pd.read_csv(OUT / "tou_elasticity_paper.csv")
    c4 = c4[c4.col == 4].iloc[0]
    print(f"S3 e_P (pre mean expenditure share of the peak block) {eP:.3f}; implied own-hour elasticity with eta=0: {eps:.4f} (se {se_eps:.4f}); E0 column 4 {c4.eta:.4f} (se {c4.se:.4f}); the spec text says -0.086", flush=True)

    # S6 variants
    var = {}
    for lab, ctrl, rows in (("REN control (main)", "ren", rows_real), ("no control", "none", rows_real), ("regulated-unit control", "ptu", rows_real),
                            ("excl. July", "ren", rows_real & ~(d.date.dt.month == 7) | (rows_real & ~d.post))):
        a = design(d, rows, ctrl)
        s_, V_, _ = fit(a)
        var[lab] = (s_[0], float(np.sqrt(V_[0, 0])))
        print(f"   S6 {lab}: sigma {s_[0]:.4f} (se {np.sqrt(V_[0, 0]):.4f}, n {len(a['W'])})", flush=True)

    # S4 placebo windows: fake policy path by weekday position
    real_post = d[d.post & both].reset_index(drop=True)
    zreal = np.log(real_post[[f"pol_{k}" for k in K]].to_numpy() / (EL.OLD + ebar))
    pl = []
    for s0 in PLACEBO_STARTS:
        s1 = s0 + pd.Timedelta(days=105)
        if s1 > pd.Timestamp("2019-12-31"):
            continue
        rows = d.date.between("2018-01-01", "2019-12-31") & d.pre & both
        sub = d[rows]
        fake = np.zeros((len(sub), 3))
        inw = sub.date.between(s0, s1).to_numpy()
        n_in = int(inw.sum())
        fake[inw] = zreal[np.arange(n_in) % len(zreal)]
        a = design(d, rows, "ren", ex=True, fake=fake)
        s_, V_, _ = fit(a)
        pl.append(dict(start=s0.date(), sigma=s_[0], se=float(np.sqrt(V_[0, 0])), days_in_window=n_in))
    PL = pd.DataFrame(pl)
    print(PL.round(4).to_string(index=False), flush=True)

    # S5: unrestricted period-specific price responses (the CES restriction is equality)
    a3 = design(d, rows_real, "ren")
    L_ = a3["Z"].shape[1]
    Z3 = np.column_stack([a3["Z"], a3["z"][:, 1], a3["z"][:, 2]])   # extra policy prices; dependent ones are dropped
    Z3, _ = drop_dependent(Z3)
    a3b = dict(a3, Z=Z3)
    s3, V3, _ = fit(a3b, start=np.full(3, sig[0]), npar=3)
    Rm = np.array([[1, -1, 0], [0, 1, -1]], float)
    wd = float((Rm @ s3) @ np.linalg.pinv(Rm @ V3 @ Rm.T) @ (Rm @ s3))
    Gs = np.column_stack([(moments(s3 + 1e-5 * e, a3b).mean(0) - moments(s3 - 1e-5 * e, a3b).mean(0)) / 2e-5 for e in np.eye(3)])
    sv = np.linalg.svd(Gs, compute_uv=False)
    cond = float(sv[-1] / sv[0])
    print(f"S5 Jacobian singular values {np.round(sv, 5)}, smallest/largest {cond:.4f}; excluded-instrument rank (policy prices after dropping dependent ones): {Z3.shape[1] - 1 - 2 - 11}", flush=True)
    p5 = float(1 - stats.chi2.cdf(wd, 2))
    print(f"S5 period-specific sigmas P/M/V {np.round(s3, 3)} (se {np.round(np.sqrt(np.diag(V3)), 3)}); Wald equality {wd:.2f}, p {p5:.3f}", flush=True)

    pd.DataFrame([dict(sample="post window REN control", sigma=sig[0], se=se, J=J, e_P=eP, eps_own=eps, eps_se=se_eps, col4=c4.eta, col4_se=c4.se, F_PV=fs["P/V"], F_MV=fs["M/V"])] +
                 [dict(sample=k, sigma=v[0], se=v[1]) for k, v in var.items()] +
                 [dict(sample="S5 sigma_P/M/V", sigma=s3[0], se=np.sqrt(V3[0, 0])), dict(sample="S5 sigma_M", sigma=s3[1], se=np.sqrt(V3[1, 1])), dict(sample="S5 sigma_V", sigma=s3[2], se=np.sqrt(V3[2, 2])), dict(sample="S5 Wald p", sigma=p5)]).round(5).to_csv(OUT / "tou_ces_summary.csv", index=False)
    PL.round(5).to_csv(OUT / "tou_ces_placebo.csv", index=False)

    # rules
    ok1 = bool(min(fs.values()) >= 10)
    ok2 = bool(sig[0] > 0 and sig[0] - 1.96 * se > 0 and 0.02 <= sig[0] <= 3)
    ok3 = bool(abs(eps - c4.eta) <= se_eps)
    rank = int((PL.sigma.abs() >= abs(sig[0])).sum()) + 1
    ok4 = bool(rank <= 2)
    ok5 = bool(p5 > 0.05)
    ok6 = bool(all(v[0] > 0 for v in var.values()))
    print(f"\nS1 identification (both first-stage F >= 10): {ok1}")
    print(f"S2 sign and size: {ok2}")
    print(f"S3 consistency with E0 column 4 (|{eps:.4f} - {c4.eta:.4f}| <= {se_eps:.4f}): {ok3}; against the spec's -0.086: {bool(abs(eps + 0.086) <= se_eps)}")
    print(f"S4 placebo rank {rank} of {len(PL) + 1} (top 2 needed): {ok4}")
    print(f"S5 CES restriction not rejected at 5% (p {p5:.3f}): {ok5}")
    print(f"S6 sign of sigma positive in every variant: {ok6}")


if __name__ == "__main__":
    main()
