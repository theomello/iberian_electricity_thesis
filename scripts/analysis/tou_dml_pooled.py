"""Part A of docs/specs/2026-11-26-orthogonal-and-sensitivity-design.md: the orthogonal-score (double machine learning) version.

    tou_dml_pooled.py [--series E0 6.2 6.3 6.4]

Partially linear model Y = theta*D + g(W) + e, D = dose x 1{date in the target summer's window}, folds = calendar years. Nuisances
l(W) = E[Y|W] and m(W) = E[D|W] fitted per hour on the other folds (paper's LASSO: calendar x temperature interactions, 10-fold one-SE, no trend),
residuals Y~ = Y - l^, D~ = D - m^, theta^ = sum(D~ Y~) / sum(D~^2). Targets: 2021 and the placebo summers 2014-2019 (2021 rows are in the sample
only for the 2021 target). Outcome A: log load of the series (Spain) with Portugal's log load among the features; outcome B: Spain minus
Portugal log load with calendar features only. Ridge replaces LASSO for the 2021 target (outcome A) as the second learner (O4).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy import stats
from sklearn.linear_model import Lasso, LassoCV, RidgeCV
from sklearn.model_selection import KFold
from sklearn.preprocessing import PolynomialFeatures

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_drift_location as DL  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_industry_regulated_price as RP  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402
import tou_tariff_drift as TD  # noqa: E402

OUT = S6.OUT
BASE = {"E0": (-0.11572, 0.03686), "6.2": (-0.06369, 0.01684), "6.3": (-0.23291, 0.1808), "6.4": (-0.33676, 0.0830)}  # eta_2021, placebo sd
PLAC = S6.SUMMERS


def one_se(Z, y):
    cv = LassoCV(cv=KFold(10, shuffle=True, random_state=0), alphas=50, max_iter=5000).fit(Z, y)
    m = cv.mse_path_.mean(1)
    se = cv.mse_path_.std(1, ddof=1) / np.sqrt(cv.mse_path_.shape[1])
    i = m.argmin()
    return Lasso(alpha=cv.alphas_[np.where(m <= m[i] + se[i])[0]].max(), max_iter=5000).fit(Z, y)


def hour_features(x, use_pt):
    tmin = x.groupby("date").temp_es.transform("min")
    tmax = x.groupby("date").temp_es.transform("max")
    out = {}
    for h in range(24):
        s = x[x.hour == h]
        cols = [pd.get_dummies(s.month.astype(str), prefix="m", dtype=float), (s.dow >= 5).astype(float).rename("wk"), s.hol_es.rename("hol"),
                s.temp_es.rename("t"), tmin[s.index].rename("tmin"), tmax[s.index].rename("tmax")]
        if use_pt:
            cols.append(np.log(s.load_pt).rename("lpt"))
        B = pd.concat(cols, axis=1)
        P = pd.DataFrame(PolynomialFeatures(2, include_bias=False).fit_transform(B.to_numpy()), index=B.index)
        P = P.loc[:, ~P.T.duplicated().to_numpy()]
        out[h] = (s.index.to_numpy(), P.to_numpy())
    return out


def predict(F, y, train, pred, learner):
    """Per-hour fit on rows `train`, predictions for rows `pred` (boolean arrays over x); NaN elsewhere."""
    out = np.full(len(y), np.nan)
    for h, (idx, P) in F.items():
        tr, pr = train[idx] & np.isfinite(y[idx]), pred[idx]
        if not pr.any():
            continue
        yt = y[idx][tr]
        if np.allclose(yt, 0.0):
            out[idx[pr]] = 0.0
            continue
        mu, sd = P[tr].mean(0), P[tr].std(0)
        keep = sd > 1e-9
        Z = (P[:, keep] - mu[keep]) / sd[keep]
        if learner == "ridge":
            m = RidgeCV(alphas=np.logspace(-1, 4, 20)).fit(Z[tr], yt)
        else:
            m = one_se(Z[tr], yt)
        out[idx[pr]] = m.predict(Z[pr])
    return out


def crossfit(F, y, sample, year, learner):
    out = np.full(len(y), np.nan)
    for f in sorted(set(year[sample])):
        pred = sample & (year == f)
        out += 0  # keep dtype
        r = predict(F, y, sample & (year != f), pred, learner)
        out[pred] = r[pred]
    return out


def main():
    series = ["E0", "6.2", "6.3", "6.4"]
    if "--series" in sys.argv:
        series = sys.argv[sys.argv.index("--series") + 1:]
    x = S6.build()
    clean = S6.gates(x)
    covid = x.date.between(*EV.COVID)
    pre = (x.date.dt.year.isin(S6.YEARS) & ~covid).to_numpy()
    win21 = ((x.date >= S6.R0) & (x.date <= S6.R1)).to_numpy()
    year = x.date.dt.year.to_numpy()
    dates = sorted(set(x.date[pre]) | set(pd.date_range(S6.R0, S6.R1)))
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= S6.R0) & (eh.index.get_level_values(0) <= S6.R1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    to_x = lambda ser: np.nan_to_num(ser.reindex(idx).to_numpy())
    ren = pd.read_parquet(RP.T_ROOT / "data/ren/ren_market_prices.parquet")
    ren = ren[ren.series == "ES"]
    loc = ren.utc_timestamp.dt.tz_convert("Europe/Madrid")
    wp = ren.assign(date=pd.to_datetime(loc.dt.date.to_numpy()), hour=loc.dt.hour.to_numpy()).groupby(["date", "hour"]).value.mean()
    tab_t = RP.tables(dates, RP.power_table(), "full", wp=wp)
    tab_e = CT.old_new_tables(dates)
    FA, FB = hour_features(x, True), hour_features(x, False)
    S_pre = pre.copy()
    S_21 = pre | win21
    rows = []
    for n in series:
        dose = to_x(CT.series_dose(n, tab_e if n == "E0" else tab_t, ebar))
        yA = np.log(x[f"load_{n}"].to_numpy())
        yB = yA - np.log(x.load_pt.to_numpy())
        # dose nuisance m(W) once per target (it does not depend on the outcome)
        Dm = {}
        for T in PLAC + [2021]:
            a, b = (S6.R0, S6.R1) if T == 2021 else S6.aligned(T)
            sample = S_21 if T == 2021 else S_pre
            w = ((x.date >= a) & (x.date <= b)).to_numpy()
            D = np.where(w, dose, 0.0)
            sm = sample & np.isfinite(yA)
            m = np.full(len(yA), np.nan)
            for f in sorted(set(year[sm])):
                pred = sm & (year == f)
                m[pred] = predict(FA, D, sm & (year != f), pred, "lasso")[pred] if (D[sm & (year != f)] != 0).any() else 0.0
            Dm[T] = (D, m, sm)
            print(f"{n}: dose nuisance for target {T} done", flush=True)
        D, _, sm = Dm[2021]
        m_r = np.full(len(yA), np.nan)
        for f in sorted(set(year[sm])):
            pred = sm & (year == f)
            m_r[pred] = predict(FA, D, sm & (year != f), pred, "ridge")[pred] if (D[sm & (year != f)] != 0).any() else 0.0
        res = {}
        for oc, (F, y) in {"A": (FA, yA), "B": (FB, yB)}.items():
            print(f"{n} outcome {oc}: outcome nuisance l(W) cross-fits ...", flush=True)
            l_pre = crossfit(F, y, S_pre & np.isfinite(y), year, "lasso")
            l_21 = crossfit(F, y, S_21 & np.isfinite(y), year, "lasso")
            targets = {}
            for T in PLAC + [2021]:
                D, m, sm = Dm[T]
                l = l_21 if T == 2021 else l_pre
                Dt, Yt = (D - m)[sm], (y - l)[sm]
                ok = np.isfinite(Dt) & np.isfinite(Yt)
                targets[T] = float((Dt[ok] * Yt[ok]).sum() / (Dt[ok] ** 2).sum())
                print(f"   {n} {oc} target {T}: theta {targets[T]:+.4f}", flush=True)
            res[oc] = targets
            if oc == "A":
                l_r = crossfit(FA, yA, S_21 & np.isfinite(yA), year, "ridge")
                D, _, sm = Dm[2021]
                Dt, Yt = (D - m_r)[sm], (yA - l_r)[sm]
                ok = np.isfinite(Dt) & np.isfinite(Yt)
                theta_ridge = float((Dt[ok] * Yt[ok]).sum() / (Dt[ok] ** 2).sum())
        for oc in ("A", "B"):
            pl = np.array([res[oc][t] for t in PLAC])
            th = res[oc][2021]
            mean, trend, slope, sse, mm, sd = TD.nulls(th, dict(zip(PLAC, pl)))
            rows.append(dict(series=n, outcome=oc, target="summary", theta=th, placebo_mean=mm, placebo_sd=sd, p_mean=mean["p"], effect_mean=mean["eff"],
                             effect_trend=trend["eff"], p_trend=trend["p"], theta_ridge=theta_ridge if oc == "A" else np.nan))
        e, bsd = BASE[n]
        print(f"\n=== {n} ===")
        for oc in ("A", "B"):
            r = [q for q in rows if q["series"] == n and q["outcome"] == oc and q["target"] == "summary"][0]
            o1 = abs(r["theta"] - e) <= bsd
            o3 = r["placebo_sd"] <= 1.5 * bsd
            print(f"outcome {oc}: theta_2021 {r['theta']:+.4f} (baseline {e:+.4f}) placebo mean {r['placebo_mean']:+.4f} sd {r['placebo_sd']:.4f} (baseline sd {bsd:.4f}); "
                  f"mean-null effect {r['effect_mean']:+.3f} p {r['p_mean']:.3f}; trend effect {r['effect_trend']:+.3f} p {r['p_trend']:.3f}")
            print(f"   O1 agreement |diff| {abs(r['theta'] - e):.4f} <= {bsd:.4f}: {o1} | O3 spread ratio {r['placebo_sd'] / bsd:.2f} <= 1.5: {o3}")
        rA = [q for q in rows if q["series"] == n and q["outcome"] == "A" and q["target"] == "summary"][0]
        print(f"O4 ridge theta_2021 {theta_ridge:+.4f} vs LASSO {rA['theta']:+.4f}: |diff| {abs(theta_ridge - rA['theta']):.4f} <= 0.02: {abs(theta_ridge - rA['theta']) <= 0.02}")
        pd.DataFrame([dict(series=n, outcome=o, target=t, theta=v) for o, d in res.items() for t, v in d.items()] + rows).to_csv(OUT / f"tou_dml_pooled_{n}.csv", index=False)
    print("\nO0 (gate) is the cached baseline, reproduced in tou_drift_location.py and tou_tariff_drift.py (committed).")


if __name__ == "__main__":
    main()
