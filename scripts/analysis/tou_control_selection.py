"""Choice of the Portuguese control for the nested CES (docs/specs/2026-11-13-control-selection-design.md).

    .venv/bin/python scripts/analysis/tou_control_selection.py

Loadings of Spain's pre-reform taste residual on Portugal's (leave-year-out LASSO residuals, 2018-2020 without the lockdown), then six candidate controls through the nested CES of tou_ces_nested.py,
each with its nine 2019 placebo windows. Selection: smallest root-mean-square of the placebo sigma_L. Writes outputs/tables/tou_control_selection_*.csv and prints C1-C5.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_ces as C  # noqa: E402
import tou_ces_nested as N  # noqa: E402

K2 = ("P", "M")


def loo_residuals(d):
    res = {}
    for name, ctry in (("es", "es"), ("pt", "pt"), ("ptu", "pt")):
        for k in K2:
            y = d[f"y_{name}_{k}"]
            r = pd.Series(np.nan, index=d.index)
            for yr in (2018, 2019, 2020):
                pred = C.taste_pred(d, y, ctry, (yr,))
                sel = d.year == yr
                r[sel] = (y - pred)[sel]
            res[(name, k)] = r
    return res


def loadings(res, d):
    elig = d.pre & d.both
    for key in res:
        elig &= res[key].notna()
    out, cl = {}, pd.factorize(d.week[elig])[0]
    for k in K2:
        y = res[("es", k)][elig].to_numpy()
        for lab, names in (("REN", ["pt"]), ("regulated unit", ["ptu"]), ("both", ["pt", "ptu"])):
            X = np.column_stack([res[(n, k)][elig].to_numpy() for n in names])
            XtX = np.linalg.inv(X.T @ X)
            b = XtX @ X.T @ y
            u = y - X @ b
            S = pd.DataFrame(X * u[:, None]).groupby(cl).sum().to_numpy()
            V = XtX @ (S.T @ S) @ XtX
            out[(lab, k)] = (b, np.sqrt(np.diag(V)))
    return out, int(elig.sum())


def run_candidate(d, ebar, control, zreal):
    both = d.both
    base = (d.pre | d.post) & both
    need_ptu = control == "ptu" or (isinstance(control, dict) and "ptu" in control)
    if need_ptu:
        base &= d[[f"q_ptu_{k}" for k in C.K]].notna().all(axis=1)
    A = N.add_eps(C.design(d, base, control), d)
    th, V, cond, _ = N.fit_n(A)
    wald = float((th[0] - th[1]) ** 2 / (V[0, 0] + V[1, 1] - 2 * V[0, 1]))
    pl = []
    for s0 in C.PLACEBO_STARTS:
        s1 = s0 + pd.Timedelta(days=105)
        if s1 > pd.Timestamp("2019-12-31"):
            continue
        rr = d.date.between("2018-01-01", "2019-12-31") & d.pre & both
        if need_ptu:
            rr &= d[[f"q_ptu_{k}" for k in C.K]].notna().all(axis=1)
        sub = d[rr]
        fake = np.zeros((len(sub), 3))
        inw = sub.date.between(s0, s1).to_numpy()
        fake[inw] = zreal[np.arange(int(inw.sum())) % len(zreal)]
        a = N.add_eps(C.design(d, rr, control, ex=True, fake=fake), d)
        t_, V_, _, _ = N.fit_n(a, starts=((0.0, 0.0), (0.05, 0.05), (-0.05, 0.1)))
        pl.append((t_[0], t_[1]))
    pl = np.array(pl)
    return dict(sigma_U=th[0], sigma_L=th[1], se_U=float(np.sqrt(V[0, 0])), se_L=float(np.sqrt(V[1, 1])), p_equal=float(1 - stats.chi2.cdf(wald, 1)), cond=cond,
                rms_U=float(np.sqrt((pl[:, 0] ** 2).mean())), rms_L=float(np.sqrt((pl[:, 1] ** 2).mean())),
                rank_U=int(1 + (np.abs(pl[:, 0]) >= abs(th[0])).sum()), rank_L=int(1 + (np.abs(pl[:, 1]) >= abs(th[1])).sum())), pl


def main():
    d, ebar = C.daily_frame()
    d = C.add_tastes(d)
    res = loo_residuals(d)
    L_, n = loadings(res, d)
    print(f"loadings of Spain's residual on the control residual(s), {n} pre-reform weekdays (leave-year-out):", flush=True)
    rows = []
    for (lab, k), (b, se) in L_.items():
        print(f"   {lab:15s} {k}: " + ", ".join(f"{x:.3f} (se {s:.3f}, t {x / s:.1f})" for x, s in zip(b, se)), flush=True)
        rows.append(dict(control=lab, ratio=k, loading=";".join(f"{x:.4f}" for x in b), se=";".join(f"{s:.4f}" for s in se)))
    pd.DataFrame(rows).to_csv(C.OUT / "tou_control_selection_loadings.csv", index=False)
    kP = {lab: (L_[(lab, "P")][0], L_[(lab, "M")][0]) for lab in ("REN", "regulated unit", "both")}
    real_post = d[d.post & d.both].reset_index(drop=True)
    zreal = np.log(real_post[[f"pol_{k}" for k in C.K]].to_numpy() / (C.EL.OLD + ebar))
    cands = {"none": "none", "REN (loading 1)": "ren", "regulated unit (loading 1)": "ptu",
             "REN (estimated)": {"pt": tuple(kP["REN"][i][0] for i in (0, 1))},
             "regulated unit (estimated)": {"ptu": tuple(kP["regulated unit"][i][0] for i in (0, 1))},
             "both (estimated)": {"pt": (kP["both"][0][0], kP["both"][1][0]), "ptu": (kP["both"][0][1], kP["both"][1][1])}}
    # kP[...][i] is the loading vector of ratio i; for REN/regulated unit it has one entry, for both two
    cands["REN (estimated)"] = {"pt": (L_[("REN", "P")][0][0], L_[("REN", "M")][0][0])}
    cands["regulated unit (estimated)"] = {"ptu": (L_[("regulated unit", "P")][0][0], L_[("regulated unit", "M")][0][0])}
    cands["both (estimated)"] = {"pt": (L_[("both", "P")][0][0], L_[("both", "M")][0][0]), "ptu": (L_[("both", "P")][0][1], L_[("both", "M")][0][1])}
    out, plc = {}, []
    for lab, ctl in cands.items():
        o, pl = run_candidate(d, ebar, ctl, zreal)
        out[lab] = o
        for i, (u, l) in enumerate(pl):
            plc.append(dict(control=lab, window=i, sigma_U=u, sigma_L=l))
        print(f"   {lab:28s} sigma_U {o['sigma_U']:.4f} (se {o['se_U']:.4f}) sigma_L {o['sigma_L']:.4f} (se {o['se_L']:.4f}) equality p {o['p_equal']:.4f} | placebo rms U {o['rms_U']:.4f} L {o['rms_L']:.4f} | ranks {o['rank_U']}, {o['rank_L']} of 10", flush=True)
    R = pd.DataFrame(out).T
    R.round(5).to_csv(C.OUT / "tou_control_selection_candidates.csv")
    pd.DataFrame(plc).round(5).to_csv(C.OUT / "tou_control_selection_placebo.csv", index=False)

    # rules
    c1 = {lab: all(abs(L_[(lab, k)][0][0] / L_[(lab, k)][1][0]) >= 2 for k in K2) for lab in ("REN", "regulated unit")}
    best = R.rms_L.astype(float).min()
    near = R[R.rms_L.astype(float) <= best * 1.05]
    sel = near.rms_U.astype(float).idxmin() if len(near) > 1 else near.index[0]
    s = out[sel]
    c3 = bool(s["sigma_U"] > 0 and s["sigma_L"] > 0 and s["p_equal"] < 0.05 and s["sigma_L"] > s["sigma_U"] and s["rank_U"] <= 2 and s["rank_L"] <= 2)
    est = [out[k]["sigma_L"] for k in ("REN (estimated)", "regulated unit (estimated)", "both (estimated)")]
    rng_est = max(est) - min(est)
    old = [out[k]["sigma_L"] for k in ("REN (loading 1)", "regulated unit (loading 1)", "none")]
    print(f"\nC1 loadings carry information (|t| >= 2 in both ratios): {c1}")
    print(f"C2 selected control (smallest placebo rms of sigma_L, ties within 5% to sigma_U): {sel} (rms_L {out[sel]['rms_L']:.4f}; candidates within 5%: {list(near.index)})")
    print(f"C3 nested result under the selected control (both positive, equality rejected, sigma_L > sigma_U, both rank <= 2 of 10): {c3}")
    print(f"C4 range of sigma_L across the three estimated-loading candidates {rng_est:.3f} (<= 0.08 needed): {bool(rng_est <= 0.08)}; across the earlier three {max(old) - min(old):.3f}")
    print("C5 sigma_U and sigma_L under all six controls are in outputs/tables/tou_control_selection_candidates.csv; the selected one is", sel)


if __name__ == "__main__":
    main()
