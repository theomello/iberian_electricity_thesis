"""Scratch check: swap the per-hour learner in the six-summer E0 test; compare placebo spread. Not registered; exploratory."""
import os, sys, shutil, traceback
os.environ["OMP_NUM_THREADS"] = "1"
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed
AN = "/Users/theodor/projects/vre_spain_thesis/scripts/analysis"
sys.path.insert(0, AN)
SCR = Path(__file__).resolve().parent
import tou_lasso_paper as L
import tou_industry_six_summer as S
from sklearn.linear_model import Lasso, LassoCV, RidgeCV, ElasticNetCV, LinearRegression
from sklearn.model_selection import KFold
from sklearn.ensemble import HistGradientBoostingRegressor

def fit_1se(X, y):
    cv = LassoCV(cv=KFold(10, shuffle=True, random_state=0), alphas=50, max_iter=5000).fit(X, y)
    mm = cv.mse_path_.mean(1); se = cv.mse_path_.std(1, ddof=1) / np.sqrt(cv.mse_path_.shape[1]); i = mm.argmin()
    return Lasso(alpha=cv.alphas_[np.where(mm <= mm[i] + se[i])[0]].max(), max_iter=5000).fit(X, y)

class Post:
    def __init__(s, X, y):
        m = fit_1se(X, y)
        s.k = np.abs(m.coef_) > 0
        s.m = LinearRegression().fit(X[:, s.k], y) if s.k.any() else None
        s.c = y.mean()
    def predict(s, X): return s.m.predict(X[:, s.k]) if s.m is not None else np.full(len(X), s.c)

ORIG = L.fit_one_se
def lasso_min(X, y): return LassoCV(cv=KFold(10, shuffle=True, random_state=0), alphas=50, max_iter=5000).fit(X, y)
def ridge(X, y): return RidgeCV(alphas=np.logspace(-1, 4, 30)).fit(X, y)
def enet(X, y): return ElasticNetCV(l1_ratio=0.5, cv=KFold(10, shuffle=True, random_state=0), alphas=30, max_iter=5000).fit(X, y)
def post(X, y): return Post(X, y)
def boost(X, y): return HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200, random_state=0).fit(X, y)
LEARNERS = {"lasso_1se": ORIG, "lasso_min": lasso_min, "ridge": ridge, "enet": enet, "post_lasso": post, "boost": boost}

def task(learner, name, xx, load, temp, hol, ex):
    L.fit_one_se = LEARNERS[learner]
    xx = xx.dropna(subset=[load])
    return learner, name, ex, L.area_errors(xx, load, temp, hol, ex)

def main():
    which = sys.argv[1:] or list(LEARNERS)
    x = S.build(); clean = S.gates(x)
    out = []
    S.SERIES = ["E0"]; S.NEEDS_E12 = set(); S.OUT = SCR
    shutil.copy(S.T.OUT / "tou_industry_adjusted.csv", SCR / "tou_industry_adjusted.csv")
    for lr in which:
        tasks = []
        xx = x.copy(); xx.loc[~xx.date.dt.year.isin(clean["E0"] | {2021}), "load_E0"] = np.nan
        for ex in [()] + [(y,) for y in S.SUMMERS if y in clean["E0"]]:
            tasks.append((lr, "E0", xx, "load_E0", "temp_es", "hol_es", ex))
        for ex in [()] + [(y,) for y in S.SUMMERS]:
            tasks.append((lr, "PT", x, "load_pt", "temp_pt", "hol_pt", ex))
        res = Parallel(n_jobs=4, verbose=5)(delayed(task)(*t) for t in tasks)
        errs = {(n, str(ex)): e for l, n, ex, e in res if l == lr}
        pd.DataFrame({f'{k[0]}|{k[1]}': v for k, v in errs.items()}).to_parquet(SCR / f'errs_{lr}.parquet')
        S.errors = lambda x_, c_, errs=errs: errs
        try: S.main()
        except Exception as e: print("main ended:", type(e).__name__, e)
        R = pd.read_csv(SCR / "tou_industry_six_summer.csv"); R = R[(R.series == "E0") & (R["shift"] == 0)].set_index("summer").eta
        pl = R.drop(2021); real = R.loc[2021]
        sd = pl.std(ddof=1); t = (real - pl.mean()) / (sd * np.sqrt(1 + 1 / len(pl)))
        shifted = pd.read_csv(SCR / "tou_industry_six_summer.csv"); shifted = shifted[(shifted.series == "E0") & (shifted.summer != 2021)].eta.std()
        out.append(dict(learner=lr, eta_2021=real, placebo_mean=pl.mean(), placebo_sd=sd, t=t, shifted_sd=shifted, placebos=" ".join(f"{k}:{v:+.3f}" for k, v in pl.items())))
        pd.DataFrame(out).to_csv(SCR / "learner_swap_summary.csv", index=False)
    print(pd.DataFrame(out).round(4).to_string(index=False))

if __name__ == "__main__": main()
