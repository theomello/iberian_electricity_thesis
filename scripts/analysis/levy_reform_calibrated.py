"""Calibrated reform and levy decomposition in euros per MWh (docs/specs/2026-11-16-levy-reform-calibrated-design.md, rules K1-K7).

    .venv/bin/python scripts/analysis/levy_reform_calibrated.py

Four states as in hydro_levy_simulation; consumer cost per MWh C_s = sum(L_s p_s)/sum(L_s) over the valid weekday hours of the window; R = C_AA - C_AR (reform), H = C_AA - C_HA (levy),
I = R - (C_HA - C_HR). Dose scenarios: L_m = L x exp(-(1-m) B_k - c_day(m)), energy neutral by day (extra_demand with (1-m) B). Writes outputs/tables/levy_reform_calibrated_*.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hydro_levy_simulation as HL  # noqa: E402
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_price_effect as PE  # noqa: E402

POST0, POST1, OUT = PE.POST0, PE.POST1, PE.OUT
NDRAW, NBOOT, NDOSE, SEED = 2000, 2000, 1000, 20261117
MULT = [0.0, 0.5, 1.0, 1.5, 2.0]
ci = HL.ci


def cost(L, p):
    return (L * p).sum(-1) / L.sum(-1)


def main():
    x = D.prep(T.build("e0", end="2021-09-14"))
    errs = PE.get_errors(x)
    covid = x.date.between(*EV.COVID)
    pre = (x.date >= "2018-01-01") & (x.date <= "2020-12-31") & ~covid
    real_mask = pre | ((x.date >= POST0) & (x.date <= POST1))
    b, V = PE.effects(x, errs[("ES", "()")], errs[("PT", "()")], real_mask, POST0, POST1)
    rng = np.random.default_rng(SEED)
    B = rng.multivariate_normal(b, V, size=NDRAW)

    ct = HL.cost_table()
    m_real = PE.month_list(POST0, POST1)
    cv = PE.Curves(PE.month_list("2019-01-01", "2019-12-31") + m_real)
    h, LT = PE.window_hours(x, cv, POST0, POST1)
    hids = set(h.hid)
    mk = HL.market_for(m_real, hids)
    cur_a = HL.CurveSet(mk)
    hy_win = HL.storage_steps(m_real, ct)
    kr, _ = HL.ratios(HL.storage_steps(PE.month_list("2021-01-01", "2021-05-31"), ct), pd.Timestamp("2021-01-01"), pd.Timestamp("2021-05-31"))
    cur_h = HL.CurveSet(mk, HL.moves(hy_win, hids, kr))
    L = h.load_es.to_numpy()
    jul = (h.date.dt.month != 7).to_numpy()

    def states(Bm):
        X, _, _ = HL.extra_demand(h, LT, Bm)
        p_AA, p_AR = HL.state_prices(cur_a, h, X)
        p_HA, p_HR = HL.state_prices(cur_h, h, X)
        return X, p_AA, p_AR, p_HA, p_HR

    def effects_from(X, p_AA, p_AR, p_HA, p_HR, keep=None):
        k = np.ones(len(L), bool) if keep is None else keep
        Lk, Xk = L[k], X[:, k]
        C_AA, C_HA = cost(Lk, p_AA[k]), cost(Lk, p_HA[k])
        C_AR, C_HR = cost(Lk + Xk, p_AR[:, k]), cost(Lk + Xk, p_HR[:, k])
        return C_AA, C_HA, C_AR, C_HR

    # ---------- main: draws
    X, p_AA, p_AR, p_HA, p_HR = states(B)
    C_AA, C_HA, C_AR, C_HR = effects_from(X, p_AA, p_AR, p_HA, p_HR)
    R, I = C_AA - C_AR, (C_AA - C_AR) - (C_HA - C_HR)
    # point
    Xp, pAA, pAR, pHA, pHR = states(b[None, :])
    c = effects_from(Xp, pAA, pAR, pHA, pHR)
    R1, H1pt = float((c[0] - c[2])[0]), float(c[0] - c[1])
    I1 = float((c[0] - c[2])[0] - (c[1] - c[3])[0])
    # levy effect: week-block bootstrap of the load-weighted hydro difference
    dH = p_AA - p_HA
    wk = h.date.dt.to_period("W").astype(str).to_numpy()
    uw, inv = np.unique(wk, return_inverse=True)
    sl = np.array([(L * dH)[inv == i].sum() for i in range(len(uw))])
    sw = np.array([L[inv == i].sum() for i in range(len(uw))])
    bi = rng.integers(0, len(uw), size=(NBOOT, len(uw)))
    Hb = sl[bi].sum(1) / sw[bi].sum(1)
    H = float(cost(L, p_AA) - cost(L, p_HA))
    Hlo, Hhi = ci(Hb)
    Rlo, Rhi = ci(R)
    print(f"cost per MWh: actual {cost(L, p_AA):.2f}; reform effect R {R1:+.3f} (draw median {np.median(R):+.3f}) [{Rlo:+.3f}, {Rhi:+.3f}]; levy effect H {H:+.3f} [{Hlo:+.3f}, {Hhi:+.3f}]; "
          f"interaction I {I1:+.3f} ({100 * abs(I1) / abs(R1):.0f}% of |R|), draws {np.median(I):+.3f} [{ci(I)[0]:+.3f}, {ci(I)[1]:+.3f}]", flush=True)
    Rh = C_HA - C_HR  # reform effect under hydro back
    print(f"reform effect under pre-announcement hydro {float((c[1] - c[3])[0]):+.3f}", flush=True)

    # ---------- K1 anchors
    Xm0, _, _ = HL.extra_demand(h, LT, B[:5] * 1.0)
    Xm0b, _, _ = HL.extra_demand(h, LT, (1 - 0.0) * B[:5])
    Xm1, _, _ = HL.extra_demand(h, LT, (1 - 1.0) * B[:5])
    k1 = bool(np.abs(Xm0 - Xm0b).max() < 1e-6 and np.abs(Xm1).max() < 1e-6)

    # ---------- dose scenarios (reform effect at dose m = C_m - C_0), both hydro regimes
    rows = []
    Bd = B[:NDOSE]
    res = {}
    for m in MULT:
        Xm, _, _ = HL.extra_demand(h, LT, (1 - m) * Bd)
        for rg, cur in (("actual hydro", cur_a), ("pre-announcement hydro", cur_h)):
            hid, dt = h.hid.to_numpy(), h.d_tot.to_numpy()
            pm = np.empty_like(Xm)
            for j in range(len(h)):
                pm[:, j] = cur.clear(hid[j], dt[j] + Xm[:, j])
            res[(rg, m)] = cost(L + Xm, pm)
    for rg in ("actual hydro", "pre-announcement hydro"):
        for m in MULT:
            e = res[(rg, m)] - res[(rg, 0.0)]
            rows.append(dict(regime=rg, multiplier=m, cost_per_mwh=float(np.median(res[(rg, m)])), effect_vs_no_reform=float(np.median(e)), lo=ci(e)[0], hi=ci(e)[1]))
    Dd = pd.DataFrame(rows)
    print(Dd.round(3).to_string(index=False), flush=True)
    k5 = True
    for rg in ("actual hydro", "pre-announcement hydro"):
        e = Dd[Dd.regime == rg].effect_vs_no_reform.to_numpy()
        k5 &= bool(np.all(np.diff(e) < 1e-9) and np.all(e[1:] < 0))

    # ---------- placebo windows
    def cf(n):
        a, bb = errs[(n, "(2018,)")], errs[(n, "(2019,)")]
        return pd.concat([a[x.date.reindex(a.index).dt.year == 2018], bb[x.date.reindex(bb.index).dt.year == 2019]])
    eEc, ePc = cf("ES"), cf("PT")
    pmask = (x.date >= "2018-01-01") & (x.date <= "2019-12-31")
    hy_19 = HL.storage_steps(PE.month_list("2019-01-01", "2019-12-31"), ct)
    pl = []
    for s0 in PE.PLACEBO_STARTS:
        s1 = s0 + pd.Timedelta(days=105)
        if s1 > pd.Timestamp("2019-12-31"):
            continue
        bp, _ = PE.effects(x, eEc, ePc, pmask, s0, s1)
        hp, LTp = HL.window_hours_safe(x, cv, s0, s1)
        mkp = HL.market_for(PE.month_list(s0, s1), set(hp.hid))
        ca = HL.CurveSet(mkp)
        Xp_, _, _ = HL.extra_demand(hp, LTp, bp[None, :])
        pa0, paR = HL.state_prices(ca, hp, Xp_)
        Lp = hp.load_es.to_numpy()
        row = dict(start=s0.date(), reform_effect=float(cost(Lp, pa0) - cost(Lp + Xp_[0], paR[0])), hours=len(hp), levy_effect=np.nan, pre_days=0)
        d0 = max(pd.Timestamp("2019-01-01"), s0 - pd.Timedelta(days=105))
        krp, npd = HL.ratios(hy_19, d0, s0 - pd.Timedelta(days=1))
        row["pre_days"] = npd
        if npd >= 56:
            ch = HL.CurveSet(mkp, HL.moves(hy_19, set(hp.hid), krp))
            ph0, _ = HL.state_prices(ch, hp, np.zeros((1, len(hp))))
            row["levy_effect"] = float(cost(Lp, pa0) - cost(Lp, ph0))
        pl.append(row)
    PL = pd.DataFrame(pl)
    print(PL.round(3).to_string(index=False), flush=True)
    rank = int((PL.reform_effect.abs() >= abs(R1)).sum()) + 1
    plh = PL.levy_effect.dropna()

    # ---------- K7 robustness at the point estimates
    kj = jul
    cj = effects_from(Xp, pAA, pAR, pHA, pHR, keep=kj)
    Rj, Hj = float((cj[0] - cj[2])[0]), float(cj[0] - cj[1])
    kr2, _ = HL.ratios(HL.storage_steps(PE.month_list("2021-03-01", "2021-05-31"), ct), pd.Timestamp("2021-03-01"), pd.Timestamp("2021-05-31"))
    cur_h2 = HL.CurveSet(mk, HL.moves(hy_win, hids, kr2))
    p_H2, _ = HL.state_prices(cur_h2, h, np.zeros((1, len(h))))
    H2 = float(cost(L, pAA) - cost(L, p_H2))
    rob = pd.DataFrame([dict(variant="base", R=R1, H=H), dict(variant="July dropped", R=Rj, H=Hj), dict(variant="ratios 2021-03-01 to 05-31", R=R1, H=H2)])
    print(rob.round(3).to_string(index=False), flush=True)

    # ---------- rules
    k2 = bool(R1 < 0 and Rhi < 0)
    k3 = bool(H < 0 and Hhi < 0 and -10 <= H <= -0.10)
    k4 = bool(abs(I1) <= 0.25 * abs(R1))
    k6 = bool(rank <= 2 and len(plh) > 0 and plh.abs().mean() <= abs(H) / 3)
    k7 = bool(Rj < 0 and Hj < 0 and H2 < 0 and 0.5 <= Hj / H <= 2 and 0.5 <= H2 / H <= 2)
    print(f"\nK1 anchors: {k1}")
    print(f"K2 reform effect R {R1:+.3f} [{Rlo:+.3f}, {Rhi:+.3f}] negative, excludes zero: {k2}")
    print(f"K3 levy effect H {H:+.3f} [{Hlo:+.3f}, {Hhi:+.3f}] negative, excludes zero, in [-10, -0.10]: {k3}")
    print(f"K4 additivity |I| {abs(I1):.3f} vs 25% of |R| = {0.25 * abs(R1):.3f}: {k4}")
    print(f"K5 monotone and negative in dose, both regimes: {k5}")
    print(f"K6 placebo: reform rank {rank} of {len(PL) + 1}; placebo mean |levy| {plh.abs().mean() if len(plh) else np.nan:.3f} vs a third of real {abs(H) / 3:.3f}: {k6}")
    print(f"K7 robustness: {k7}")

    pd.DataFrame([dict(item="cost per MWh actual", value=float(cost(L, p_AA))), dict(item="R reform effect (point)", value=R1, lo=Rlo, hi=Rhi),
                  dict(item="H levy effect", value=H, lo=Hlo, hi=Hhi), dict(item="I interaction (point)", value=I1, lo=ci(I)[0], hi=ci(I)[1]),
                  dict(item="reform effect under pre-announcement hydro (point)", value=float((c[1] - c[3])[0]))]).round(4).to_csv(OUT / "levy_reform_calibrated_summary.csv", index=False)
    Dd.round(4).to_csv(OUT / "levy_reform_calibrated_dose.csv", index=False)
    PL.round(4).to_csv(OUT / "levy_reform_calibrated_placebo.csv", index=False)
    rob.round(4).to_csv(OUT / "levy_reform_calibrated_robustness.csv", index=False)


if __name__ == "__main__":
    main()
