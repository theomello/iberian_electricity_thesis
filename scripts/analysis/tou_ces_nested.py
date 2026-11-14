"""Nested CES: peak against the rest (sigma_U), then mid against valley (sigma_L) (docs/specs/2026-11-13-nested-ces-design.md).

Same data, tastes, instruments, sample, controls and estimator as tou_ces.py (nonlinear 2SLS on the share residuals of P and M); only the share function changes:
  pi_M = w0_{M|N} e^{-sL rho_M} / (w0_{M|N} e^{-sL rho_M} + w0_{V|N} e^{-sL rho_V})
  ln P_N/Pbar_N = ln(eps_M e^{(1-sL) rho_M} + eps_V e^{(1-sL) rho_V}) / (1 - sL)
  w_P/(1-w_P) = w0_P/(1-w0_P) * exp(-sU (rho_P - ln P_N/Pbar_N));  w_M = (1-w_P) pi_M, w_V = (1-w_P)(1-pi_M)
Writes outputs/tables/tou_nested_ces_*.csv and prints N1-N5.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_ces as C  # noqa: E402

OUT = C.OUT
K = C.K


def shares_nested(theta, Y0, rho, eps):
    sU, sL = theta
    w0 = C.shares(0.0, Y0, rho)                       # softmax(Y0, 0): the taste-path shares at the reference prices
    wMN = w0[:, 1] / (w0[:, 1] + w0[:, 2])
    lM, lV = np.exp(-sL * rho[:, 1]) * wMN, np.exp(-sL * rho[:, 2]) * (1 - wMN)
    piM = lM / (lM + lV)
    if abs(1 - sL) < 1e-6:
        lnPN = eps[0] * rho[:, 1] + eps[1] * rho[:, 2]
    else:
        lnPN = np.log(eps[0] * np.exp((1 - sL) * rho[:, 1]) + eps[1] * np.exp((1 - sL) * rho[:, 2])) / (1 - sL)
    odds = w0[:, 0] / (1 - w0[:, 0]) * np.exp(-sU * (rho[:, 0] - lnPN))
    wP = odds / (1 + odds)
    return np.column_stack([wP, (1 - wP) * piM, (1 - wP) * (1 - piM)])


def moments_n(theta, a):
    w = shares_nested(theta, a["Y0"], a["rho"], a["eps"])
    R = a["W"][:, :2] - w[:, :2]
    return np.column_stack([R[:, 0:1] * a["Z"], R[:, 1:2] * a["Z"]])


def fit_n(a, starts=((0.07, 0.1), (0.07, 0.3), (0.05, 0.0), (0.1, 0.2))):
    Wt = C.weight(a)
    Q = lambda t: (lambda g: float(g @ Wt @ g))(moments_n(t, a).mean(0))
    best = None
    for s0 in starts:
        r = optimize.minimize(Q, np.array(s0), method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-15, "maxiter": 5000})
        if best is None or r.fun < best.fun:
            best = r
    th = best.x
    h = 1e-5
    G = np.column_stack([(moments_n(th + h * e, a).mean(0) - moments_n(th - h * e, a).mean(0)) / (2 * h) for e in np.eye(2)])
    S = C.cluster_cov(moments_n(th, a), a["cl"])
    Bm = np.linalg.inv(G.T @ Wt @ G)
    V = Bm @ G.T @ Wt @ S @ Wt @ G @ Bm
    sv = np.linalg.svd(G, compute_uv=False)
    return th, V, float(sv[-1] / sv[0]), float(best.fun)


def add_eps(a, d):
    pre = d.pre & d.both
    e = d.loc[pre, [f"p_{k}" for k in K]].to_numpy() * d.loc[pre, [f"q_es_{k}" for k in K]].to_numpy()
    e = (e / e.sum(1, keepdims=True)).mean(0)
    a["eps"] = np.array([e[1] / (e[1] + e[2]), e[2] / (e[1] + e[2])])
    a["eP"] = float(e[0])
    return a


def main():
    d, ebar = C.daily_frame()
    d = C.add_tastes(d)
    both = d.both
    rows = (d.pre | d.post) & both
    A = add_eps(C.design(d, rows, "ren"), d)
    th, V, cond, Q = fit_n(A)
    se = np.sqrt(np.diag(V))
    fs = C.first_stage(A)
    wald = float((th[0] - th[1]) ** 2 / (V[0, 0] + V[1, 1] - 2 * V[0, 1]))
    p3 = float(1 - stats.chi2.cdf(wald, 1))
    print(f"nest weights within N (pre-reform mean expenditure shares): M {A['eps'][0]:.3f}, V {A['eps'][1]:.3f}; peak share of expenditure {A['eP']:.3f}", flush=True)
    print(f"sigma_U (peak vs rest) {th[0]:.4f} (se {se[0]:.4f}, 95% [{th[0] - 1.96 * se[0]:.3f}, {th[0] + 1.96 * se[0]:.3f}]); sigma_L (mid vs valley) {th[1]:.4f} (se {se[1]:.4f}, 95% [{th[1] - 1.96 * se[1]:.3f}, {th[1] + 1.96 * se[1]:.3f}])", flush=True)
    print(f"N1 first-stage F {fs}; Jacobian smallest/largest singular value {cond:.4f}; objective {Q:.3e}", flush=True)
    print(f"N3 Wald sigma_U = sigma_L: {wald:.2f}, p {p3:.4f}", flush=True)
    print(f"implied own-hour elasticity of the peak with eta = 0: {-th[0] * (1 - A['eP']):.4f}", flush=True)

    var = {"REN control (main)": (th, se)}
    for lab, ctrl, rr in (("no control", "none", rows), ("regulated-unit control", "ptu", rows), ("excl. July", "ren", (rows & ~(d.date.dt.month == 7)) | (rows & ~d.post))):
        a = add_eps(C.design(d, rr, ctrl), d)
        t_, V_, _, _ = fit_n(a, starts=(tuple(th), (0.07, 0.1), (0.07, 0.3)))
        var[lab] = (t_, np.sqrt(np.diag(V_)))
        print(f"   N5 {lab}: sigma_U {t_[0]:.4f} (se {np.sqrt(V_[0, 0]):.4f}), sigma_L {t_[1]:.4f} (se {np.sqrt(V_[1, 1]):.4f}), n {len(a['W'])}", flush=True)

    # N4 placebo, the single-CES spec's fake policy path by weekday position
    real_post = d[d.post & both].reset_index(drop=True)
    zreal = np.log(real_post[[f"pol_{k}" for k in K]].to_numpy() / (C.EL.OLD + ebar))
    pl = []
    for s0 in C.PLACEBO_STARTS:
        s1 = s0 + pd.Timedelta(days=105)
        if s1 > pd.Timestamp("2019-12-31"):
            continue
        rr = d.date.between("2018-01-01", "2019-12-31") & d.pre & both
        sub = d[rr]
        fake = np.zeros((len(sub), 3))
        inw = sub.date.between(s0, s1).to_numpy()
        fake[inw] = zreal[np.arange(int(inw.sum())) % len(zreal)]
        a = add_eps(C.design(d, rr, "ren", ex=True, fake=fake), d)
        t_, V_, _, _ = fit_n(a, starts=((0.0, 0.0), (0.05, 0.05), (-0.05, 0.1)))
        pl.append(dict(start=s0.date(), sigma_U=t_[0], se_U=float(np.sqrt(V_[0, 0])), sigma_L=t_[1], se_L=float(np.sqrt(V_[1, 1]))))
    PL = pd.DataFrame(pl)
    print(PL.round(4).to_string(index=False), flush=True)

    pd.DataFrame([dict(sample=k, sigma_U=v[0][0], se_U=v[1][0], sigma_L=v[0][1], se_L=v[1][1]) for k, v in var.items()] +
                 [dict(sample="N3 Wald", sigma_U=wald, se_U=p3), dict(sample="N1", sigma_U=cond, se_U=fs["P/V"], sigma_L=fs["M/V"])]).round(5).to_csv(OUT / "tou_nested_ces_summary.csv", index=False)
    PL.round(5).to_csv(OUT / "tou_nested_ces_placebo.csv", index=False)

    # rules
    ok1 = bool(min(fs.values()) >= 10 and cond >= 0.05)
    ok2 = bool(all(th[i] > 0 and th[i] - 1.96 * se[i] > 0 and 0.02 <= th[i] <= 3 for i in (0, 1)))
    rejected = p3 < 0.05
    rU = int((PL.sigma_U.abs() >= abs(th[0])).sum()) + 1
    rL = int((PL.sigma_L.abs() >= abs(th[1])).sum()) + 1
    ok4 = bool(rU <= 2 and rL <= 2)
    order = lambda t: bool(t[0] > t[1])
    ok5 = bool(all(v[0][0] > 0 and v[0][1] > 0 for v in var.values()) and len({order(v[0]) for v in var.values()}) == 1)
    print(f"\nN1 identification (F >= 10 for both, Jacobian ratio >= 0.05): {ok1}")
    print(f"N2 sign and size (each sigma positive, interval excludes zero, in [0.02, 3]): {ok2}")
    print(f"N3 nesting: {'rejected, nested model is the result' if rejected else 'not rejected, single CES stands'} (p {p3:.4f}); sigma_L {'>' if th[1] > th[0] else '<'} sigma_U")
    print(f"N4 placebo ranks: sigma_U {rU} of {len(PL) + 1}, sigma_L {rL} of {len(PL) + 1} (top 2 for each needed): {ok4}")
    print(f"N5 robustness (both positive, same ordering in every variant): {ok5}")


if __name__ == "__main__":
    main()
