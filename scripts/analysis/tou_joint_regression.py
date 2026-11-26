"""docs/specs/2026-11-26-joint-regression-design.md: real dose plus counterfactual-calendar controls in one regression.

    tou_joint_regression.py 6.4        # one tariff per process; outputs/tables/tou_joint_regression_<tariff>.csv

Per summer (2021 and the six aligned placebo summers): stack and fixed effects as the baseline; regressors the real dose and J controls
built from the screened shifted-calendar doses (principal components covering 90% of their variance after the fixed effects, J <= 5).
Variants: base (no controls, = baseline), main (J), mainJm1, mainJp1, S1 (mean of the shifted doses), S2 (all shifted doses).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_industry_regulated_price as RP  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402

OUT = S6.OUT
SHIFTS = [k for k in range(-9, 10) if abs(k) >= 3]
COMMITTED = {"6.2": (-0.06369, 0.01955, 0.01684), "6.3": (-0.23291, 0.19751, 0.1808), "6.4": (-0.33676, 0.32562, 0.0830)}


def ols_first(y, X):
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(b[0])


def main():
    tar = sys.argv[1]
    x = S6.build()
    clean = S6.gates(x)
    covid = x.date.between(*EV.COVID)
    pre = x.date.dt.year.isin(S6.YEARS) & ~covid
    dates = sorted(set(x.date[pre]) | set(pd.date_range(S6.R0, S6.R1)))
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= S6.R0) & (eh.index.get_level_values(0) <= S6.R1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    ren = pd.read_parquet(RP.T_ROOT / "data/ren/ren_market_prices.parquet")
    ren = ren[ren.series == "ES"]
    loc = ren.utc_timestamp.dt.tz_convert("Europe/Madrid")
    wp = ren.assign(date=pd.to_datetime(loc.dt.date.to_numpy()), hour=loc.dt.hour.to_numpy()).groupby(["date", "hour"]).value.mean()
    pt = RP.power_table()
    orig = RP.TS.new_period_6

    def dose(k):
        if k:
            RP.TS.new_period_6 = lambda d, h, hol: orig(d, (h + k) % 24, hol)
        try:
            tab = RP.tables(dates, pt, "full", wp=wp)
        finally:
            RP.TS.new_period_6 = orig
        return np.nan_to_num(CT.series_dose(tar, tab, ebar).reindex(idx).to_numpy())

    errs = S6.errors(x, clean)
    win21 = ((x.date >= S6.R0) & (x.date <= S6.R1)).to_numpy()
    work = (x.dow < 5).to_numpy() & (x.hol_es == 0).to_numpy()
    real = dose(0)
    cfs = {}
    for k in SHIFTS:
        dk = dose(k)
        if abs(float(np.corrcoef(real[win21 & work], dk[win21 & work])[0, 1])) <= 0.5:
            cfs[k] = dk
    print(f"{tar}: {len(cfs)} screened calendars {sorted(cfs)}", flush=True)
    rows = []
    for yr in [2021] + S6.SUMMERS:
        if yr == 2021:
            w, key, mask = win21, "()", pre | pd.Series(win21, index=x.index)
        else:
            a, b = S6.aligned(yr)
            w = ((x.date >= a) & (x.date <= b)).to_numpy()
            key, mask = f"({yr},)", pre
        s = CT.make_stack(x, errs[(tar, key)], errs[("PT", key)], "PT", mask)
        F = CT.fe3(s)
        y = CT.EL.resid(F, s.e)
        spain = s.area.to_numpy() == 0
        src = s.src.to_numpy()
        col = lambda dp: np.where(spain, np.where(w, dp, 0.0)[src], 0.0)
        p0 = CT.EL.resid(F, col(real))
        C = np.column_stack([CT.EL.resid(F, col(cfs[k])) for k in cfs])
        ev, V = np.linalg.eigh(C.T @ C)
        order = np.argsort(ev)[::-1]
        ev, V = ev[order], V[:, order]
        cum = np.cumsum(ev) / ev.sum()
        J = int(min(5, np.searchsorted(cum, 0.90) + 1))
        PC = C @ V
        def fit(Z):
            X = np.column_stack([p0] + ([Z] if Z is not None and Z.shape[1] else []))
            beta = ols_first(y, X)
            res_p0 = p0 - (Z @ np.linalg.lstsq(Z, p0, rcond=None)[0] if Z is not None and Z.shape[1] else 0.0)
            return beta, float(np.var(res_p0) / np.var(p0))
        variants = {"base": (None, 0), "main": (PC[:, :J], J), "S1": (C.mean(axis=1, keepdims=True), 1), "S2": (C, C.shape[1])}
        if J >= 2:
            variants["mainJm1"] = (PC[:, :J - 1], J - 1)
        if J + 1 <= C.shape[1]:
            variants["mainJp1"] = (PC[:, :J + 1], J + 1)
        for name, (Z, nj) in variants.items():
            beta, ratio = fit(Z)
            rows.append(dict(tariff=tar, summer=yr, variant=name, beta=beta, dose_var_left=ratio, n_controls=nj, J_main=J, var_expl_J=float(cum[J - 1])))
        print(f"{tar} {yr}: J {J} ({cum[J - 1]:.2f} of variance); " + " ".join(f"{r['variant']} {r['beta']:+.3f}" for r in rows if r["summer"] == yr), flush=True)
        pd.DataFrame(rows).to_csv(OUT / f"tou_joint_regression_{tar}.csv", index=False)
        if yr == 2021:
            pass
    R = pd.DataFrame(rows)
    b = R[R.variant == "base"].set_index("summer").beta
    e, mu, sd = COMMITTED[tar]
    ok = abs(b[2021] - e) < 0.0015 and abs(b.drop(2021).mean() - mu) < 0.0015 and abs(b.drop(2021).std(ddof=1) - sd) < 0.0015
    print(f"J0 {tar}: baseline eta {b[2021]:+.5f} mean {b.drop(2021).mean():+.5f} sd {b.drop(2021).std(ddof=1):.5f} -> {'pass' if ok else 'FAIL'}", flush=True)


if __name__ == "__main__":
    main()
