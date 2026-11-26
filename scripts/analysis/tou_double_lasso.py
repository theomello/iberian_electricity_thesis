"""Double LASSO for the E0 reform effect, six-summer test (spec docs/specs/2026-11-26-double-lasso-design.md, step 1).

Pooled over hours: y = log E0 load, d = dose (reform-induced change in log hourly price). Year dummies are partialled out
exactly; the other controls (calendar cells, temperature terms, Portugal's log load) are partialled out by LASSO (10-fold
cross-validation by blocks of ISO weeks, one-standard-error rule). beta = OLS of the y residual on the d residual,
week-clustered. Run for the treated summer 2021 and the six placebo summers 2014-2019 with the same pipeline.
Usage: tou_double_lasso.py [--p0]   (--p0 drops Portugal's terms)
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Lasso, LassoCV
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_industry_six_summer as S  # noqa: E402

P0 = "--p0" in sys.argv
OUT = S.OUT
BASE = dict(eta=-0.1157, mean=-0.0049, sd=0.0369)


def prep():
    x = S.build()
    covid = x.date.between(*EV.COVID)
    pre = x.date.dt.year.isin(S.YEARS) & ~covid
    dates = sorted(set(x.date[pre]) | set(pd.date_range(S.R0, S.R1)))
    tabs = CT.old_new_tables(dates)
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= S.R0) & (eh.index.get_level_values(0) <= S.R1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    x["dpx"] = np.nan_to_num(CT.series_dose("E0", tabs, ebar).reindex(idx).to_numpy())
    x["tmin"] = x.groupby("date").temp_es.transform("min")
    x["tmax"] = x.groupby("date").temp_es.transform("max")
    x["ly"] = np.log(x.load_E0)
    x["lpt"] = np.log(x.load_pt)
    return x, pre


def controls(d):
    cell = d.hour.astype(str) + "_" + (d.dow >= 5).astype(int).astype(str) + "_" + d.month.astype(str)
    blocks = [pd.get_dummies(cell, dtype=float)]
    hm = pd.get_dummies(d.hour, dtype=float)
    for v in ("temp_es", "tmin", "tmax"):
        z = (d[v] - d[v].mean()).to_numpy()[:, None]
        blocks += [hm.mul(z[:, 0], axis=0).add_prefix(f"{v}_"), hm.mul(z[:, 0] ** 2, axis=0).add_prefix(f"{v}2_")]
    blocks.append(d[["hol_es"]].astype(float))
    if not P0:
        z = (d.lpt - d.lpt.mean()).to_numpy()
        blocks += [hm.mul(z, axis=0).add_prefix("pt_"), pd.Series(z, index=d.index, name="pt")]
    W = pd.concat([b.to_frame() if isinstance(b, pd.Series) else b for b in blocks], axis=1)
    return W.loc[:, W.std() > 0]


def fit_1se(Z, y, groups):
    cv = list(GroupKFold(10).split(Z, y, groups))
    m = LassoCV(cv=cv, alphas=40, max_iter=3000, tol=1e-3, n_jobs=4, random_state=0).fit(Z, y)
    mm = m.mse_path_.mean(1)
    se = m.mse_path_.std(1, ddof=1) / np.sqrt(m.mse_path_.shape[1])
    a = m.alphas_[np.where(mm <= mm[np.argmin(mm)] + se[np.argmin(mm)])[0]].max()
    return Lasso(alpha=a, max_iter=3000, tol=1e-3).fit(Z, y), a


def one(x, pre, year):
    a, b = (S.R0, S.R1) if year == 2021 else S.aligned(year)
    win = (x.date >= a) & (x.date <= b)
    if year == 2021:
        keep = pre | win
    else:
        keep = (pre & (x.date.dt.year != year)) | win
    d = x[keep & x.ly.notna() & x.lpt.notna() & x.temp_es.notna()].copy()
    w = ((d.date >= a) & (d.date <= b)).to_numpy()
    d["dose"] = np.where(w, d.dpx, 0.0)
    W = controls(d)
    yr = d.date.dt.year.to_numpy()
    # partial out year dummies exactly (group demeaning)
    dm = lambda M: M - pd.DataFrame(M).groupby(yr).transform("mean").to_numpy()
    Wd = dm(W.to_numpy(float))
    yd, dd = dm(d[["ly"]].to_numpy())[:, 0], dm(d[["dose"]].to_numpy())[:, 0]
    sd = Wd.std(0)
    Z = Wd[:, sd > 1e-9] / sd[sd > 1e-9]
    grp = d.date.dt.strftime("%G-%V").factorize()[0]
    my, ay = fit_1se(Z, yd, grp)
    md, ad = fit_1se(Z, dd, grp)
    ry, rd = yd - my.predict(Z), dd - md.predict(Z)
    beta = float(rd @ ry / (rd @ rd))
    e = ry - beta * rd
    g = pd.Series(rd * e).groupby(grp).sum()
    se = float(np.sqrt((g ** 2).sum()) / (rd @ rd))
    r = dict(summer=year, beta=beta, se=se, resid_dose_sd_ratio=float(rd.std() / dd.std()), rows=len(d), win_rows=int(w.sum()),
             nsel_y=int((my.coef_ != 0).sum()), nsel_d=int((md.coef_ != 0).sum()), alpha_y=ay, alpha_d=ad)
    print(r, flush=True)
    return r


def main():
    x, pre = prep()
    tag = "p0" if P0 else "main"
    f = OUT / f"tou_double_lasso_{tag}.csv"
    rows = []
    for yr in [2021] + S.SUMMERS:
        rows.append(one(x, pre, yr))
        pd.DataFrame(rows).to_csv(f, index=False)
    R = pd.DataFrame(rows).set_index("summer")
    real, pl = float(R.beta.loc[2021]), R.beta.drop(2021)
    S_, m, s = len(pl), float(pl.mean()), float(pl.std(ddof=1))
    se = s * np.sqrt(1 + 1 / S_)
    t = (real - m) / se
    p = float(stats.t.cdf(t, S_ - 1))
    q = stats.t.ppf(0.975, S_ - 1)
    print(f"\n[{tag}] beta_2021 {real:+.4f}  placebo mean {m:+.4f} sd {s:.4f}  t {t:.2f}  p_t {p:.4f}  "
          f"rank {(1 + int((pl <= real).sum())) / (1 + S_):.3f}  effect interval [{real - (m + q * se):+.4f}, {real - (m - q * se):+.4f}]")
    print("RULES")
    print(f"D1 resid dose sd >= 20% in every summer: min ratio {R.resid_dose_sd_ratio.min():.3f} -> {bool(R.resid_dose_sd_ratio.min() >= 0.2)}")
    print(f"D2 |placebo mean| {abs(m):.4f} <= |beta|/3 {abs(real) / 3:.4f} -> {bool(abs(m) <= abs(real) / 3)}")
    print(f"D3 placebo sd {s:.4f} <= {0.8 * BASE['sd']:.4f} -> {bool(s <= 0.8 * BASE['sd'])}")
    print(f"D4 beta<0 and p_t<=0.05: {bool(real < 0 and p <= 0.05)}")
    print(f"D5 |beta - baseline| {abs(real - BASE['eta']):.4f} <= {BASE['sd']:.4f} -> {bool(abs(real - BASE['eta']) <= BASE['sd'])}")
    pd.DataFrame([dict(variant=tag, beta_2021=real, placebo_mean=m, placebo_sd=s, t=t, p_t=p)]).to_csv(OUT / f"tou_double_lasso_{tag}_summary.csv", index=False)


if __name__ == "__main__":
    main()
