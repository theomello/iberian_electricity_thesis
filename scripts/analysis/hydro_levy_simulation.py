"""Reform, hydro-offer (levy) and tariff-ratio scenarios in one re-clear (docs/specs/2026-11-14-hydro-levy-simulation-design.md).

Four states on each valid weekday hour's effective offer curve (outputs/cache/step): actual (AA), reform removed (AR), hydro offered as before the 1 June 2021 announcement (HA), both (HR).
Reform removed = the period-type load effects of tou_price_effect (neutral level) put back as extra demand. Pre-announcement hydro = each storage unit's movable steps (price > 1) re-priced at
k_{u,hod} x cost, k the MW-weighted ratio of its offer prices to its water value over 2021-01-01 -> 2021-05-31, same MW. Scenarios: nested-CES shares (sigma_U, sigma_L) with the policy
log price scaled by a multiplier m (rho_m = rho - (1 - m) z), energy-neutral by day, re-cleared. Writes outputs/tables/hydro_levy_simulation_*.csv and prints H1-H7.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_ces as C  # noqa: E402
import tou_ces_nested as NS  # noqa: E402
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_price_effect as PE  # noqa: E402

STEP, OUT = PE.STEP, PE.OUT
POST0, POST1 = PE.POST0, PE.POST1
ANN = pd.Timestamp("2021-06-01")
TOL, ZERO, KMIN, KMAX = 1e-6, 1.0, 0.2, 5.0
NDRAW, NBOOT, NSIG = 2000, 2000, 300
MULT = [0.0, 0.5, 1.0, 1.5, 2.0]
SEED = 20261116
EV_H, NI_H = PE.EVENING, PE.NIGHT


# ------------------------------------------------------------------ curves
class CurveSet:
    """Effective offer curves by hour after optional moves (hid, price, mw, new): cumulative MW offered at or below each price."""

    def __init__(self, mk, mv=None):
        inc = mk[["hid", "price", "da"]]
        if mv is not None and len(mv):
            inc = pd.concat([inc, pd.DataFrame({"hid": mv.hid.to_numpy(), "price": mv.price.to_numpy(), "da": -mv.mw.to_numpy()}),
                             pd.DataFrame({"hid": mv.hid.to_numpy(), "price": mv.new.to_numpy(), "da": mv.mw.to_numpy()})], ignore_index=True)
        g = inc.groupby(["hid", "price"], sort=True).da.sum().reset_index()
        g["cum"] = g.groupby("hid").da.cumsum()
        self.price, self.cum = g.price.to_numpy(float), g.cum.to_numpy(float)
        uh, st = np.unique(g.hid.to_numpy(), return_index=True)
        self.start = dict(zip(uh, st))
        self.end = dict(zip(uh, list(st[1:]) + [len(g)]))

    def clear(self, hid, target):
        s, e = self.start[hid], self.end[hid]
        idx = np.minimum(np.searchsorted(self.cum[s:e], np.asarray(target) - TOL, side="left"), e - s - 1)
        return self.price[s:e][idx]


def market_for(months, hids):
    mk = pd.concat([pd.read_parquet(STEP / f"market_{ym}.parquet") for ym in months], ignore_index=True)
    mk = mk[mk.hid.isin(hids)].sort_values(["hid", "price"], kind="stable", ignore_index=True)
    mk["da"] = mk.groupby("hid").a.diff().fillna(mk.a)
    return mk


# ------------------------------------------------------------------ hydro
def cost_table():
    c = pd.read_parquet(T.ROOT / "outputs/tables/hydro_cost_daily.parquet", columns=["unit", "date", "cost_eur_mwh"]).rename(columns={"cost_eur_mwh": "cost"})
    c["date"] = pd.to_datetime(c.date)
    return c


def storage_steps(months, cost):
    hy = pd.concat([pd.read_parquet(STEP / f"hydro_{ym}.parquet", columns=["hid", "date", "unit", "cls", "price", "mw", "withdrawn"]) for ym in months], ignore_index=True)
    hy = hy[(hy.cls == "hydro") & ~hy.withdrawn & (hy.mw > 0) & (hy.price > ZERO)].copy()
    hy["date"] = pd.to_datetime(hy.date)
    hy = hy.merge(cost, on=["unit", "date"], how="left")
    return hy[hy.cost.notna() & (hy.cost > 0)]


def ratios(hy, d0, d1, min_hours=20):
    """k_{u,hod}: MW-weighted price over MW-weighted cost of the unit's movable steps in the pre-announcement days."""
    s = hy[(hy.date >= d0) & (hy.date <= d1)].copy()
    s["hod"] = s.hid % 24
    g = s.assign(num=s.mw * s.price, den=s.mw * s.cost).groupby(["unit", "hod"]).agg(num=("num", "sum"), den=("den", "sum"), n=("hid", "nunique")).reset_index()
    g = g[g.n >= min_hours]
    g["k"] = (g.num / g.den).clip(KMIN, KMAX)
    return g.set_index(["unit", "hod"]).k, int(s.date.nunique())


def moves(hy, hids, kr):
    s = hy[hy.hid.isin(hids)].copy()
    s["hod"] = s.hid % 24
    s["k"] = kr.reindex(pd.MultiIndex.from_arrays([s.unit, s.hod])).to_numpy()
    s = s[s.k.notna()]
    s["new"] = s.k * s.cost
    return s[["hid", "price", "mw", "new"]]


# ------------------------------------------------------------------ reform effect and scenarios
def extra_demand(h, LT, B):
    """Extra demand (draws x hours) of the reform-removed state, energy neutral by day: load x (exp(-tau) - 1), tau = B_k + c_day."""
    Cd = np.log(np.exp(-B) @ LT.to_numpy().T / LT.to_numpy().sum(1))
    tau = B[:, h.k.to_numpy()] + Cd[:, h.day.to_numpy()]
    return h.load_es.to_numpy()[None, :] * (np.exp(-tau) - 1.0), B[:, :, None] * 0 + 0, Cd


def state_prices(cur, h, X):
    """Prices (draws x hours) for each of the extra-demand rows X, plus the actual-demand price (hours)."""
    hid, dt = h.hid.to_numpy(), h.d_tot.to_numpy()
    p0 = np.array([cur.clear(hid[j], dt[j]) for j in range(len(h))])
    pX = np.empty_like(X)
    for j in range(len(h)):
        pX[:, j] = cur.clear(hid[j], dt[j] + X[:, j])
    return p0, pX


def contrast(v, h):
    """Evening minus night mean of v (draws x hours or hours)."""
    v = np.atleast_2d(v)
    return v[:, h.hour.isin(EV_H).to_numpy()].mean(1) - v[:, h.hour.isin(NI_H).to_numpy()].mean(1)


def ci(a):
    return float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))


def design_post(d, ctrl):
    rows = (d.pre | d.post) & d.both
    A = NS.add_eps(C.design(d, rows, ctrl), d)
    post = pd.to_datetime(A["dates"]) >= POST0
    return {"dates": pd.to_datetime(A["dates"])[post], "Y0": A["Y0"][post], "rho": A["rho"][post], "z": A["z"][post], "eps": A["eps"]}


def shift_ratio(P, sig, m):
    w1 = NS.shares_nested(sig, P["Y0"], P["rho"], P["eps"])
    wm = NS.shares_nested(sig, P["Y0"], P["rho"] - (1 - m) * P["z"], P["eps"])
    return wm / w1


def scenario_X(h, LT, P, sig, m):
    """Extra demand (hours) of the tariff-ratio-m state relative to the actual one, energy neutral by day, for hours on days in the design."""
    r = shift_ratio(P, sig, m)
    di = {dt: i for i, dt in enumerate(P["dates"])}
    ok = h.date.map(lambda x: x in di).to_numpy()
    X = np.zeros(len(h))
    LTn = LT.to_numpy()
    for j in np.where(ok)[0]:
        i = di[h.date.iat[j]]
        k = int(h.k.iat[j])
        day = int(h.day.iat[j])
        s = LTn[day].sum() / (LTn[day] * r[i]).sum()
        X[j] = h.load_es.iat[j] * (r[i, k] * s - 1.0)
    return X, ok


def main():
    x = D.prep(T.build("e0", end="2021-09-14"))
    errs = PE.get_errors(x)
    covid = x.date.between(*EV.COVID)
    pre = (x.date >= "2018-01-01") & (x.date <= "2020-12-31") & ~covid
    real_mask = pre | ((x.date >= POST0) & (x.date <= POST1))
    b, V = PE.effects(x, errs[("ES", "()")], errs[("PT", "()")], real_mask, POST0, POST1)
    rng = np.random.default_rng(SEED)
    B = rng.multivariate_normal(b, V, size=NDRAW)

    cost = cost_table()
    m_real = PE.month_list(POST0, POST1)
    cv = PE.Curves(PE.month_list("2019-01-01", "2019-12-31") + m_real)
    h, LT = PE.window_hours(x, cv, POST0, POST1)
    allw = cv.h[(cv.h.date >= POST0) & (cv.h.date <= POST1) & (cv.h.date.dt.dayofweek < 5)]
    share_valid = float(allw.valid.astype(bool).mean())
    hids = set(h.hid)
    mk = market_for(m_real, hids)
    cur_a = CurveSet(mk)
    # H1 identity: no step moved reproduces the cached re-clear
    pc = h.set_index("hid").p_clear
    err = np.array([abs(cur_a.clear(i, d_) - pc[i]) for i, d_ in zip(h.hid, h.d_tot)])
    ident = float((err < 0.006).mean())
    mae = float(err.mean())
    print(f"H1: valid weekday share {100 * share_valid:.1f}% (>= 70%); identity: re-clear equals cached price in {100 * ident:.2f}% of {len(h)} hours (mean abs {mae:.4f})", flush=True)

    # pre-announcement hydro for the real window
    hy_pre = storage_steps(PE.month_list("2021-01-01", "2021-05-31"), cost)
    kr, npre = ratios(hy_pre, pd.Timestamp("2021-01-01"), pd.Timestamp("2021-05-31"))
    hy_win = storage_steps(m_real, cost)
    mv = moves(hy_win, hids, kr)
    cur_h = CurveSet(mk, mv)
    print(f"pre-announcement ratios for {kr.groupby(level=0).ngroups} units over {npre} days; {len(mv)} step moves in the window; mean k {kr.mean():.2f}", flush=True)

    # four states
    X, _, Cd = extra_demand(h, LT, B)
    p_AA, p_AR = state_prices(cur_a, h, X)
    p_HA, p_HR = state_prices(cur_h, h, X)
    dRA = p_AA[None, :] - p_AR           # reform effect, actual hydro (draws x hours)
    dRH = p_HA[None, :] - p_HR           # reform effect, pre-announcement hydro
    dH = p_AA - p_HA                     # hydro (levy) effect, hours
    cRA, cRH = contrast(dRA, h), contrast(dRH, h)
    cI = cRA - cRH
    eRA = dRA[:, h.hour.isin(EV_H).to_numpy()].mean(1)
    # week-block bootstrap of the hydro effect
    wk = h.date.dt.to_period("W").astype(str).to_numpy()
    uw, inv = np.unique(wk, return_inverse=True)
    sums = np.array([dH[inv == i].sum() for i in range(len(uw))])
    cnts = np.array([(inv == i).sum() for i in range(len(uw))])
    bi = rng.integers(0, len(uw), size=(NBOOT, len(uw)))
    dH_boot = sums[bi].sum(1) / cnts[bi].sum(1)
    dH_mean, dH_ci = float(dH.mean()), ci(dH_boot)
    ev, ni = h.hour.isin(EV_H).to_numpy(), h.hour.isin(NI_H).to_numpy()
    print(f"states (mean over valid weekday hours): actual price {p_AA.mean():.2f}, hydro back {p_HA.mean():.2f}; hydro effect Delta_H {dH_mean:+.2f} [{dH_ci[0]:+.2f}, {dH_ci[1]:+.2f}] (evening {dH[ev].mean():+.2f}, night {dH[ni].mean():+.2f})", flush=True)
    print(f"reform effect, actual hydro: contrast {np.median(cRA):+.2f} [{ci(cRA)[0]:+.2f}, {ci(cRA)[1]:+.2f}] (point at the estimates below); pre-announcement hydro: contrast {np.median(cRH):+.2f} [{ci(cRH)[0]:+.2f}, {ci(cRH)[1]:+.2f}]; interaction {np.median(cI):+.2f} [{ci(cI)[0]:+.2f}, {ci(cI)[1]:+.2f}]", flush=True)
    X1, _, _ = extra_demand(h, LT, b[None, :])
    _, pAR1 = state_prices(cur_a, h, X1)
    _, pHR1 = state_prices(cur_h, h, X1)
    cRA1, cRH1 = float(contrast(p_AA[None, :] - pAR1, h)[0]), float(contrast(p_HA[None, :] - pHR1, h)[0])
    I1 = cRA1 - cRH1
    print(f"at the point estimates: Delta_R^A contrast {cRA1:+.2f}, Delta_R^H contrast {cRH1:+.2f}, interaction {I1:+.2f} ({100 * abs(I1) / abs(cRA1):.0f}% of |Delta_R^A|)", flush=True)

    # placebo windows
    def cf(n):
        a, bb = errs[(n, "(2018,)")], errs[(n, "(2019,)")]
        return pd.concat([a[x.date.reindex(a.index).dt.year == 2018], bb[x.date.reindex(bb.index).dt.year == 2019]])
    eEc, ePc = cf("ES"), cf("PT")
    pmask = (x.date >= "2018-01-01") & (x.date <= "2019-12-31")
    hy_19 = storage_steps(PE.month_list("2019-01-01", "2019-12-31"), cost)
    pl = []
    for s0 in PE.PLACEBO_STARTS:
        s1 = s0 + pd.Timedelta(days=105)
        if s1 > pd.Timestamp("2019-12-31"):
            continue
        bp, _ = PE.effects(x, eEc, ePc, pmask, s0, s1)
        hp, LTp = window_hours_safe(x, cv, s0, s1)
        mkp = market_for(PE.month_list(s0, s1), set(hp.hid))
        ca = CurveSet(mkp)
        Xp, _, _ = extra_demand(hp, LTp, bp[None, :])
        pa0, paR = state_prices(ca, hp, Xp)
        row = dict(start=s0.date(), reform_contrast_actual=float(contrast(pa0[None, :] - paR, hp)[0]), hours=len(hp), dH_mean=np.nan, dH_pre_days=0)
        d0 = max(pd.Timestamp("2019-01-01"), s0 - pd.Timedelta(days=105))
        krp, npd = ratios(hy_19, d0, s0 - pd.Timedelta(days=1))
        row["dH_pre_days"] = npd
        if npd >= 56:
            mvp = moves(hy_19, set(hp.hid), krp)
            ch = CurveSet(mkp, mvp)
            ph0, _ = state_prices(ch, hp, np.zeros((1, len(hp))))
            row["dH_mean"] = float((pa0 - ph0).mean())
        pl.append(row)
    PL = pd.DataFrame(pl)
    print(PL.round(3).to_string(index=False), flush=True)

    # scenarios
    d, ebar = C.daily_frame()
    d = C.add_tastes(d)
    sel = pd.read_csv(OUT / "tou_control_selection_loadings.csv")
    lp = {r.ratio: [float(v) for v in str(r.loading).split(";")] for r in sel[sel.control == "both"].itertuples()}
    ctrls = {"none": ("none", (0.07026, 0.21399)), "REN": ("ren", (0.0738, 0.16689)),
             "selected (both, estimated)": ({"pt": (lp["P"][0], lp["M"][0]), "ptu": (lp["P"][1], lp["M"][1])}, (0.07251, 0.20125))}
    dsgn = {k: design_post(d, v[0]) for k, v in ctrls.items()}
    Psel, sig_sel = dsgn["selected (both, estimated)"], ctrls["selected (both, estimated)"][1]
    se_sel = (0.00319, 0.01159)

    def scen(P, sig, curve, hh, LTh):
        res = {}
        for m in MULT:
            Xm, ok = scenario_X(hh, LTh, P, sig, m)
            hid, dt = hh.hid.to_numpy(), hh.d_tot.to_numpy()
            res[m] = np.array([curve.clear(hid[j], dt[j] + Xm[j]) if ok[j] else np.nan for j in range(len(hh))])
        ok_ = ~np.isnan(res[1.0])
        out = {}
        for m in MULT:
            dlt = res[m] - res[0.0]
            hsub = hh[ok_].reset_index(drop=True)
            out[m] = dict(contrast=float(contrast(dlt[ok_], hsub)[0]), euros=float((dlt[ok_] * hsub.load_es.to_numpy()).sum() / hsub.load_es.sum()))
        return out
    rows = []
    for regime, curve in (("actual hydro", cur_a), ("pre-announcement hydro", cur_h)):
        sc = scen(Psel, sig_sel, curve, h, LT)
        for m, v in sc.items():
            rows.append(dict(regime=regime, control="selected", sigma_U=sig_sel[0], sigma_L=sig_sel[1], multiplier=m, **v))
    S = pd.DataFrame(rows)
    # sigma draws for the central scenario interval
    dr = rng.normal(sig_sel, se_sel, size=(NSIG, 2))
    cdraw = {(rg, m): [] for rg in ("actual hydro", "pre-announcement hydro") for m in MULT}
    for sg in dr:
        sg = np.maximum(sg, 0.005)
        for rg, curve in (("actual hydro", cur_a), ("pre-announcement hydro", cur_h)):
            for m, v in scen(Psel, tuple(sg), curve, h, LT).items():
                cdraw[(rg, m)].append(v["contrast"])
    S["contrast_lo"] = [ci(cdraw[(r.regime, r.multiplier)])[0] for r in S.itertuples()]
    S["contrast_hi"] = [ci(cdraw[(r.regime, r.multiplier)])[1] for r in S.itertuples()]
    print(S.round(2).to_string(index=False), flush=True)

    # H6 closure at the actual ratio: model-implied period shifts against the DiD effects
    r0 = shift_ratio(Psel, sig_sel, 0.0)
    di = {dt: i for i, dt in enumerate(Psel["dates"])}
    LTn = LT.to_numpy()
    tau_mod = []
    for dt, i in di.items():
        if dt in LT.index:
            day = LT.index.get_loc(dt)
            s = LTn[day].sum() / (LTn[day] * r0[i]).sum()
            tau_mod.append(-np.log(r0[i] * s))
    tau_mod = np.mean(tau_mod, axis=0)
    tau_did = (B + Cd.mean(1)[:, None]) if False else None
    tauD = np.array([[(B[g, k] + Cd[g, :].mean()) for k in range(3)] for g in range(NDRAW)])
    lo_hi = [ci(tauD[:, k]) for k in range(3)]
    in_ci = [bool(lo_hi[k][0] <= tau_mod[k] <= lo_hi[k][1]) for k in range(3)]
    mono = {rg: bool(np.all(np.diff(S[S.regime == rg].contrast.to_numpy()) <= 1e-9)) for rg in ("actual hydro", "pre-announcement hydro")}
    print(f"H6 model period shifts (peak, mid, valley) {np.round(100 * tau_mod, 2)} against DiD intervals {[(round(100 * a, 2), round(100 * c, 2)) for a, c in lo_hi]}: {in_ci}; monotone in m: {mono}", flush=True)

    # H7 robustness: sign at every multiplier
    h7 = []
    for cname, (ctl, sg0) in ctrls.items():
        for dU, dL in ((0, 0), (0.011, 0.02), (0.011, -0.02), (-0.011, 0.02), (-0.011, -0.02)):
            sg = (sg0[0] + dU, sg0[1] + dL)
            for rg, curve in (("actual hydro", cur_a), ("pre-announcement hydro", cur_h)):
                sc = scen(dsgn[cname], sg, curve, h, LT)
                h7.append(dict(control=cname, dU=dU, dL=dL, regime=rg, all_negative=all(sc[m]["contrast"] < 0 for m in MULT if m > 0), contrast_m1=sc[1.0]["contrast"]))
    H7 = pd.DataFrame(h7)
    print(H7.round(2).to_string(index=False), flush=True)

    S.round(4).to_csv(OUT / "hydro_levy_simulation_scenarios.csv", index=False)
    PL.round(4).to_csv(OUT / "hydro_levy_simulation_placebo.csv", index=False)
    H7.round(4).to_csv(OUT / "hydro_levy_simulation_robustness.csv", index=False)
    pd.DataFrame([dict(state="Delta_H hydro effect (mean, all valid hours)", value=dH_mean, lo=dH_ci[0], hi=dH_ci[1]),
                  dict(state="Delta_H evening", value=float(dH[ev].mean())), dict(state="Delta_H night", value=float(dH[ni].mean())),
                  dict(state="Delta_R^A contrast (point)", value=cRA1, lo=ci(cRA)[0], hi=ci(cRA)[1]),
                  dict(state="Delta_R^H contrast (point)", value=cRH1, lo=ci(cRH)[0], hi=ci(cRH)[1]),
                  dict(state="interaction (point)", value=I1, lo=ci(cI)[0], hi=ci(cI)[1]),
                  dict(state="valid share", value=share_valid), dict(state="identity share", value=ident)]).round(4).to_csv(OUT / "hydro_levy_simulation_summary.csv", index=False)

    # rules
    ok1 = bool(share_valid >= 0.70 and ident >= 0.999 and mae <= 0.5)
    ok2 = bool(dH_mean < 0 and dH_ci[1] < 0 and -10 <= dH_mean <= -0.10)
    ok3 = bool(cRA1 < 0 and -2.4 <= cRA1 <= -1.7 and cRH1 < 0)
    ok4 = bool(abs(I1) <= 0.25 * abs(cRA1))
    pa = PL.reform_contrast_actual.abs()
    rank = int((pa >= abs(cRA1)).sum()) + 1
    plh = PL.dH_mean.dropna()
    ok5 = bool(rank <= 2 and len(plh) > 0 and plh.abs().mean() <= abs(dH_mean) / 3)
    ok6 = bool(all(in_ci) and all(mono.values()))
    ok7 = bool(H7.all_negative.all())
    print(f"\nH1 curve valid: {ok1}")
    print(f"H2 levy channel visible (Delta_H {dH_mean:+.2f} [{dH_ci[0]:+.2f}, {dH_ci[1]:+.2f}], negative, excludes zero, in [-10, -0.10]): {ok2}")
    print(f"H3 reform effect survives (actual hydro {cRA1:+.2f} in [-2.4, -1.7]; pre-announcement hydro {cRH1:+.2f} negative): {ok3}")
    print(f"H4 additivity (|I| {abs(I1):.2f} vs 25% of {abs(cRA1):.2f} = {0.25 * abs(cRA1):.2f}): {ok4}")
    print(f"H5 placebo: reform contrast rank {rank} of {len(PL) + 1} (top 2); placebo mean |Delta_H| {plh.abs().mean() if len(plh) else np.nan:.2f} over {len(plh)} windows vs a third of real {abs(dH_mean) / 3:.2f}: {ok5}")
    print(f"H6 closure and monotone: {ok6}")
    print(f"H7 robustness (sign negative at every multiplier > 0 in every control, sigma corner, hydro regime): {ok7}")


def window_hours_safe(x, cv, s0, s1):
    return PE.window_hours(x, cv, s0, s1)


if __name__ == "__main__":
    main()
