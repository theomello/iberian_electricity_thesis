"""LASSO prediction errors as in Enrich, Li, Mizrahi and Reguant (first step; after Burlig et al. 2020).

One model per area and hour of the day, fitted on pre-treatment days only (2018-01-01 -> 2020-12-31 without March-June 2020). Predictors: month dummies, weekend, national
holiday, the hour's temperature, the day's minimum and maximum temperature, and all their pairwise interactions (and squares). LASSO, penalty chosen by 10-fold cross-validation
with the one-standard-error rule. No trend. Errors = log load minus the log prediction, in and out of sample. Second step: mean error by cell (evening peak / night, working day /
weekend-holiday) over a window, contrasts as in tou_ddd, standard errors clustered by week. Areas: Spain (E0 or industry) and Portugal.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Lasso, LassoCV
from sklearn.model_selection import KFold
from sklearn.preprocessing import PolynomialFeatures

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as E  # noqa: E402

TRAIN_END = pd.Timestamp("2020-12-31")


def fit_one_se(X, y):
    cv = LassoCV(cv=KFold(10, shuffle=True, random_state=0), alphas=50, max_iter=5000).fit(X, y)
    m = cv.mse_path_.mean(1)
    se = cv.mse_path_.std(1, ddof=1) / np.sqrt(cv.mse_path_.shape[1])
    i = m.argmin()
    alpha = cv.alphas_[np.where(m <= m[i] + se[i])[0]].max()
    return Lasso(alpha=alpha, max_iter=5000).fit(X, y)


def area_errors(x, load, temp, hol, exclude_years=()):
    """Log-load prediction errors for every row of x, one LASSO per hour."""
    tmin = x.groupby("date")[temp].transform("min")
    tmax = x.groupby("date")[temp].transform("max")
    err = pd.Series(np.nan, index=x.index)
    for h in range(24):
        s = x[x.hour == h]
        B = pd.concat([pd.get_dummies(s.month.astype(str), prefix="m", dtype=float), (s.dow >= 5).astype(float).rename("wk"), s[hol].rename("hol"),
                       s[temp].rename("t"), tmin[s.index].rename("tmin"), tmax[s.index].rename("tmax")], axis=1)
        P = pd.DataFrame(PolynomialFeatures(2, include_bias=False).fit_transform(B.to_numpy()), index=B.index)
        tr = (s.date <= TRAIN_END) & ~s.date.between(*E.COVID) & ~s.date.dt.year.isin(exclude_years)  # exclude_years: leave-year-out for cross-fitting
        P = P.loc[:, ~P.T.duplicated().to_numpy()]
        mu, sd = P[tr].mean(), P[tr].std()
        keep = sd > 0
        Z = ((P.loc[:, keep] - mu[keep]) / sd[keep]).to_numpy()
        y = np.log(s[load]).to_numpy()
        m = fit_one_se(Z[tr.to_numpy()], y[tr.to_numpy()])
        err[s.index] = y - m.predict(Z)
    return err


def errors(x_es, exclude_years=()):
    """Spain-minus-Portugal error for rows of x_es (needs load_es, load_pt, temp_es, temp_pt, hol_es, hol_pt)."""
    e_es = area_errors(x_es, "load_es", "temp_es", "hol_es", exclude_years)
    e_pt = area_errors(x_es, "load_pt", "temp_pt", "hol_pt", exclude_years)
    return e_es, e_pt


def cell_ddd(x, err, s, e):
    """DDD of mean errors, evening peak vs night, working vs weekend-holiday, over [s, e]; returns (b, se)."""
    sub = x[(x.date >= s) & (x.date <= e) & ~x.date.between(*E.COVID)].copy()
    sub["err"] = err[sub.index]
    y = E.classed(sub, E.HOURS if hasattr(E, "HOURS") else [18, 19, 20, 21]).dropna(subset=["err"])
    Dm = pd.get_dummies(y.cell, dtype=float)
    Xv = Dm.to_numpy()
    b = np.linalg.pinv(Xv) @ y.err.to_numpy()
    r = y.err.to_numpy() - Xv @ b
    V = T.hac_cluster(Xv, r, y.date.dt.to_period("W").astype(str).factorize()[0])
    return D.contrasts(b, V, [f"post_{c}" for c in Dm.columns])["DDD peak"]
