"""Part B1 of docs/specs/2026-11-17-goiener-household-design.md: the pooled 2.0TD household response by period type replaces the aggregate DiD period effects as the extra demand of the reform-removed state.

    .venv/bin/python scripts/analysis/goiener_part_b1.py

Household response by period type t in (peak, mid, off) = mean household-day LASSO error of the window (g2_household_window.parquet peak/off, g2_window_mid.parquet mid) minus Portugal's mean error of the same period
(same pipeline, trained on pre-lockdown days), over the G5 households (g5_real.parquet). Placebo windows: the 26 season-matched windows (g_placebo_errors_pre.parquet, households present in that window in g5_placebo.parquet), same construction.
Point effect b = real - mean of the placebo vectors; 2,000 draws = real - placebo vector of a window drawn uniformly (placebo-calibrated distribution, preserving the correlation across period types). These (peak, mid, off) log-point effects
take the place of (b, V) in tou_price_effect.py and levy_reform_calibrated.py: energy-neutral by day, national E0 load as the base, the same curves and four states. Outputs: evening-minus-night price contrast (re-clear, as tou_price_effect.py,
neutral level) and the reform effect R on the cost per MWh (four-state model, as levy_reform_calibrated.py), with percentile intervals. Writes outputs/tables/goiener_part_b1.csv. B1 rules in the spec.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goiener_household as GH  # noqa: E402
import goiener_noise as G  # noqa: E402
import hydro_levy_simulation as HL  # noqa: E402
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_price_effect as PE  # noqa: E402
import tou_randomization_inference as RI  # noqa: E402

ROOT = T.ROOT
NDRAW, SEED = 2000, 20261117
PER = ("kwh_peak", "kwh_mid", "kwh_off")


def cost(L, p):
    return (L * p).sum(-1) / L.sum(-1)


def pt_period_errors(temps, hpt):
    x = RI.D.prep(T.build("e0", end="2021-09-15"))
    d = x[~x.date.isin(hpt) & (x.date.dt.dayofweek < 5)].copy()
    d["per"] = np.where(d.hour.isin(GH.PEAK), "kwh_peak", np.where(d.hour < 8, "kwh_off", "kwh_mid"))
    d = d[(d.date < "2020-03-01") | ((d.date >= GH.W0) & (d.date <= GH.W1))]
    cnt = d.groupby("date").size()
    pv = d.pivot_table(index="date", columns="per", values="load_pt", aggfunc="sum")[list(PER)]
    pv = pv[cnt.reindex(pv.index) == 24]
    win, pl = {}, {}
    for per in PER:
        y = np.log(pv[per].where(pv[per] > 0)).dropna()
        win[per] = GH.errors_window(y, temps["pt"])
        pl[per] = G.errors_leave_year(y[y.index < "2020-03-01"], temps["pt"])
    return win, pl


def household_effects():
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hpt = set(pd.to_datetime(hol[hol.area == "PT"].date))
    temps = G.daily_temps()
    pw, pp = pt_period_errors(temps, hpt)
    real_users = set(pd.read_parquet(ROOT / "data/goiener/daily/g5_real.parquet").user)
    E = pd.read_parquet(ROOT / "data/goiener/daily/g2_household_window.parquet")
    M = pd.read_parquet(ROOT / "data/goiener/daily/g2_window_mid.parquet")
    E = E[E.user.isin(real_users)]
    M = M[M.user.isin(real_users)]
    real = np.array([E.peak.mean() - pw["kwh_peak"].mean(), M.mid.mean() - pw["kwh_mid"].mean(), E.off.mean() - pw["kwh_off"].mean()])
    P = pd.read_parquet(ROOT / "data/goiener/daily/g_placebo_errors_pre.parquet")
    P["date"] = pd.to_datetime(P.date)
    g5p = pd.read_parquet(ROOT / "data/goiener/daily/g5_placebo.parquet")[["user", "window"]]
    wins = [(k, a, b) for k, a, b in RI.windows() if a.year in (2018, 2019) and abs((a - pd.Timestamp(year=a.year, month=6, day=1)).days) <= 45]
    vec = []
    for k, a, b in wins:
        us = set(g5p[g5p.window == k].user)
        w = P[P.user.isin(us) & (P.date >= a) & (P.date <= b)]
        vec.append([w.peak.mean() - pp["kwh_peak"][(pp["kwh_peak"].index >= a) & (pp["kwh_peak"].index <= b)].mean(),
                    w.mid.mean() - pp["kwh_mid"][(pp["kwh_mid"].index >= a) & (pp["kwh_mid"].index <= b)].mean(),
                    w.off.mean() - pp["kwh_off"][(pp["kwh_off"].index >= a) & (pp["kwh_off"].index <= b)].mean()])
    pl = np.array(vec)
    return real, pl


def main():
    real, pl = household_effects()
    b = real - pl.mean(0)
    rng = np.random.default_rng(SEED)
    B = real[None, :] - pl[rng.integers(0, len(pl), size=NDRAW)]
    print("household period effects (log points x 100) real", np.round(100 * real, 2), "placebo mean", np.round(100 * pl.mean(0), 2), "centred b", np.round(100 * b, 2), flush=True)
    x = D.prep(T.build("e0", end="2021-09-14"))
    ct = HL.cost_table()
    m_real = PE.month_list(PE.POST0, PE.POST1)
    cv = PE.Curves(PE.month_list("2019-01-01", "2019-12-31") + m_real)
    h, LT = PE.window_hours(x, cv, PE.POST0, PE.POST1)
    # evening-minus-night price contrast, as tou_price_effect.py (neutral level)
    dp = PE.price_effect(cv, h, LT, B, "neutral")
    d1 = PE.price_effect(cv, h, LT, b[None, :], "neutral")
    e, n, c = PE.stats(dp, h)
    e1, n1, c1 = PE.stats(d1, h)
    print(f"household-based contrast {c1[0]:+.2f} [{np.percentile(c, 2.5):+.2f}, {np.percentile(c, 97.5):+.2f}] EUR/MWh (evening {e1[0]:+.2f}, night {n1[0]:+.2f}); aggregate E0: -2.39 [-2.60, -2.19]", flush=True)
    # reform effect on the cost per MWh, as levy_reform_calibrated.py
    hids = set(h.hid)
    mk = HL.market_for(m_real, hids)
    cur_a = HL.CurveSet(mk)
    L = h.load_es.to_numpy()

    def states(Bm):
        X, _, _ = HL.extra_demand(h, LT, Bm)
        p_AA, p_AR = HL.state_prices(cur_a, h, X)
        return X, p_AA, p_AR

    X, p_AA, p_AR = states(B)
    R = cost(L, p_AA) - cost(L + X, p_AR)
    Xp, pAA, pAR = states(b[None, :])
    R1 = float(cost(L, pAA) - cost(L + Xp, pAR)[0])
    Rlo, Rhi = np.percentile(R, [2.5, 97.5])
    print(f"household-based reform effect on cost per MWh (actual hydro state): {R1:+.3f} [{Rlo:+.3f}, {Rhi:+.3f}]; aggregate levy_reform_calibrated K2 (with hydro as offered): -0.016 [-0.018, -0.011]", flush=True)
    ok_c = bool(-4.8 <= c1[0] <= -1.2 and c1[0] < 0)
    ok_r = bool(R1 < 0)
    print(f"B1: contrast sign and within a factor of two [-4.8, -1.2]: {ok_c}; cost effect negative: {ok_r}", flush=True)
    pd.DataFrame([dict(item="b_peak_mid_off_centred", v1=b[0], v2=b[1], v3=b[2]), dict(item="contrast_point_lo_hi", v1=c1[0], v2=np.percentile(c, 2.5), v3=np.percentile(c, 97.5)),
                  dict(item="cost_effect_R_point_lo_hi", v1=R1, v2=Rlo, v3=Rhi), dict(item="B1_pass_contrast_cost", v1=float(ok_c), v2=float(ok_r), v3=np.nan)]).round(5).to_csv(T.OUT / "goiener_part_b1.csv", index=False)


if __name__ == "__main__":
    main()
