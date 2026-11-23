"""Prediction-model selection for the six-summer industry test (docs/specs/2026-11-23-industry-prediction-model-registration-design.md).

    .venv/bin/python scripts/analysis/tou_prediction_models.py --select   # step 1: placebo summers only, 2021 sealed

Candidates (one model per area and hour, Spain series and Portugal alike):
  M0 the paper's LASSO (tou_lasso_paper.area_errors), M1 + calendar, M2 + weather memory, M3 = M1 + M2 (LASSO),
  M4 random forest on M3's raw features (training-row errors out-of-bag), M5 = M3 errors with Portugal scaled by b_k.
Statistic as registered: pooled 6.2+6.3+6.4, full dose (tou_industry_regulated_price), aligned windows, Portugal
control; E0 with its toll dose (tou_industry_six_summer). Only the six leave-one-year-out models are fitted; every row
dated 2021-01-01 or later is dropped before any feature is built. Error caches: data/cache_tou/predmodel/.
Deterministic (CV folds and forests seeded).
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.easter import easter
from joblib import Parallel, delayed
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import PolynomialFeatures

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_industry_regulated_price as RP  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402
import tou_lasso_paper as L  # noqa: E402

SEAL = pd.Timestamp("2021-01-01")
CACHE = CT.CACHE / "predmodel"
OUT = S6.OUT
POOL = ["6.2", "6.3", "6.4"]
AREAS = {"E0": ("load_E0", "temp_es", "hol_es"), "6.2": ("load_6.2", "temp_es", "hol_es"), "6.3": ("load_6.3", "temp_es", "hol_es"),
         "6.4": ("load_6.4", "temp_es", "hol_es"), "PT": ("load_pt", "temp_pt", "hol_pt")}
CAL = ["bridge", "pre_hol", "post_hol", "holy_week", "xmas"] + [f"aug_w{k}" for k in range(1, 6)]
WEA = ["t_lag", "tmax3", "cdh24", "hdh15"]
EXTRA = {"M0": [], "M1": CAL, "M2": WEA, "M3": CAL + WEA}


def day_features(x, temp, hol):
    """Calendar and weather-memory features by date for one area (continuous daily index, so shifts are by day)."""
    days = pd.date_range(x.date.min(), x.date.max())
    g = x.groupby("date")
    t = x.set_index(["date", "hour"])[temp]
    ish = g[hol].max().reindex(days).fillna(0).astype(bool)
    off = ish | pd.Series(days.dayofweek >= 5, index=days)
    f = pd.DataFrame(index=days)
    f["bridge"] = (~off & off.shift(1, fill_value=False) & off.shift(-1, fill_value=False)).astype(float)
    f["pre_hol"] = (~off & ish.shift(-1, fill_value=False)).astype(float)
    f["post_hol"] = (~off & ish.shift(1, fill_value=False)).astype(float)
    hw = set()
    for y in range(days.year.min(), days.year.max() + 1):
        e = pd.Timestamp(easter(y))
        hw |= {e - pd.Timedelta(days=k) for k in (6, 5, 4)}  # Monday-Wednesday of Holy Week
    f["holy_week"] = days.isin(list(hw)).astype(float)
    f["xmas"] = (((days.month == 12) & (days.day >= 24)) | ((days.month == 1) & (days.day <= 6))).astype(float)
    for k in range(1, 6):
        f[f"aug_w{k}"] = ((days.month == 8) & ((days.day - 1) // 7 == k - 1)).astype(float)
    dmean = t.groupby(level=0).mean().reindex(days)
    dmax = t.groupby(level=0).max().reindex(days)
    f["t_lag"] = dmean.shift(1).fillna(dmean)
    f["tmax3"] = dmax.rolling(3, min_periods=1).mean()
    f["cdh24"] = np.maximum(t - 24, 0).groupby(level=0).sum().reindex(days)
    f["hdh15"] = np.maximum(15 - t, 0).groupby(level=0).sum().reindex(days)
    return f


def base_matrix(s, temp, hol, tmin, tmax, feats, extra, dummies=True):
    cols = [pd.get_dummies(s.month.astype(str), prefix="m", dtype=float), (s.dow >= 5).astype(float).rename("wk"), s[hol].rename("hol"),
            s[temp].rename("t"), tmin[s.index].rename("tmin"), tmax[s.index].rename("tmax")]
    if extra:
        cols.append(feats.reindex(s.date.to_numpy())[extra].set_axis(s.index))
    return pd.concat(cols, axis=1)


def train_mask(s, excl):
    return (s.date <= L.TRAIN_END) & ~s.date.between(*EV.COVID) & ~s.date.dt.year.isin(excl)


def lasso_errors(x, load, temp, hol, extra, excl):
    """tou_lasso_paper.area_errors with extra base columns (extra = [] is the same computation)."""
    feats = day_features(x, temp, hol) if extra else None
    tmin = x.groupby("date")[temp].transform("min")
    tmax = x.groupby("date")[temp].transform("max")
    err = pd.Series(np.nan, index=x.index)
    for h in range(24):
        s = x[x.hour == h]
        B = base_matrix(s, temp, hol, tmin, tmax, feats, extra)
        P = pd.DataFrame(PolynomialFeatures(2, include_bias=False).fit_transform(B.to_numpy()), index=B.index)
        tr = train_mask(s, excl)
        P = P.loc[:, ~P.T.duplicated().to_numpy()]
        mu, sd = P[tr].mean(), P[tr].std()
        keep = sd > 0
        Z = ((P.loc[:, keep] - mu[keep]) / sd[keep]).to_numpy()
        y = np.log(s[load]).to_numpy()
        m = L.fit_one_se(Z[tr.to_numpy()], y[tr.to_numpy()])
        err[s.index] = y - m.predict(Z)
    return err


def forest_errors(x, load, temp, hol, excl):
    feats = day_features(x, temp, hol)
    tmin = x.groupby("date")[temp].transform("min")
    tmax = x.groupby("date")[temp].transform("max")
    err = pd.Series(np.nan, index=x.index)
    for h in range(24):
        s = x[x.hour == h]
        Z = base_matrix(s, temp, hol, tmin, tmax, feats, EXTRA["M3"]).to_numpy()
        y = np.log(s[load]).to_numpy()
        tr = train_mask(s, excl).to_numpy()
        rf = RandomForestRegressor(n_estimators=500, min_samples_leaf=5, oob_score=True, random_state=0, n_jobs=1).fit(Z[tr], y[tr])
        pred = rf.predict(Z)
        pred[tr] = rf.oob_prediction_
        err[s.index] = y - pred
    return err


def task(model, area, x, excl):
    path = CACHE / f"{model}_{area}_{excl[0]}.parquet"
    if path.exists():
        return model, area, excl, pd.read_parquet(path).err
    load, temp, hol = AREAS[area]
    xx = x.dropna(subset=[load])
    e = forest_errors(xx, load, temp, hol, excl) if model == "M4" else lasso_errors(xx, load, temp, hol, EXTRA[model], excl)
    e.rename("err").to_frame().to_parquet(path)
    return model, area, excl, e


def pooled(x, ek, ec, dpxs, mask, names):
    """tou_industry_regulated_price.pooled_eta with a control error series per Spanish series."""
    parts, pv = [], []
    for j, n in enumerate(names):
        st = CT.make_stack(x, ek[n], ec[n], "PT", mask)
        st["area"] = st.area + 2 * j
        st["ym"] = f"{j}_" + st.date.dt.strftime("%Y-%m")
        pv.append(np.where(st.area.to_numpy() == 2 * j, dpxs[n][st.src.to_numpy()], 0.0))
        parts.append(st)
    s = pd.concat(parts, ignore_index=True)
    F = CT.fe3(s)
    y = CT.EL.resid(F, s.e)
    p = CT.EL.resid(F, np.concatenate(pv))
    g = pd.factorize(s.area.astype(str) + "_" + s.ym)[0]
    b, V, G = CT.ols_cl(y, p, g)
    return float(b[0])


def spread(vals):
    """(mean, sd, slope per year, s_e) of placebo values {year: eta}; s_e with S - 2 df."""
    yr = np.array(sorted(vals), float)
    v = np.array([vals[int(k)] for k in yr])
    X = np.c_[np.ones_like(yr), yr - yr.mean()]
    b, *_ = np.linalg.lstsq(X, v, rcond=None)
    r = v - X @ b
    return float(v.mean()), float(v.std(ddof=1)), float(b[1]), float(np.sqrt(r @ r / (len(v) - 2)))


def main():
    if "--select" not in sys.argv:
        sys.exit("only --select (step 1) is implemented; step 2 waits for the user")
    x = S6.build()
    x = x[x.date < SEAL].copy()
    assert x.date.max() < SEAL and x.index.equals(pd.RangeIndex(len(x))) and x.date.is_monotonic_increasing
    print(f"sealed: rows {x.date.min().date()} -> {x.date.max().date()}", flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    jobs = [(m, a, (y,)) for m in ["M0", "M1", "M2", "M3", "M4"] for a in AREAS for y in S6.SUMMERS]
    print(f"{len(jobs)} leave-one-year-out fits (cached ones are read)", flush=True)
    res = Parallel(n_jobs=min(4, os.cpu_count() or 1), verbose=5)(delayed(task)(m, a, x, ex) for m, a, ex in jobs)
    E = {(m, a, ex[0]): e.reindex(x.index) for m, a, ex, e in res}

    # G0a: the new harness's M0 errors equal the registered cache (same LASSO code path)
    old = pd.read_parquet(S6.CACHE)
    dif = max(float((E[("M0", a, y)] - old[f"{a}|({y},)"].reindex(x.index)).abs().max()) for a in AREAS for y in S6.SUMMERS)
    print(f"G0a M0 errors vs registered cache: max abs diff {dif:.2e}", flush=True)

    # M5: Portugal scaled by b, the OLS slope of the series' M3 errors on Portugal's M3 errors in the training rows
    pre = x.date.dt.year.isin(S6.YEARS) & ~x.date.between(*EV.COVID)
    for a in ["E0"] + POOL:
        for y in S6.SUMMERS:
            tr = pre & (x.date.dt.year != y)
            es, ep = E[("M3", a, y)][tr], E[("M3", "PT", y)][tr]
            ok = es.notna() & ep.notna()
            b = float(np.polyfit(ep[ok], es[ok], 1)[0])
            E[("M5", a, y)] = E[("M3", a, y)]
            E[("M5", f"PT_{a}", y)] = b * E[("M3", "PT", y)]
            print(f"  M5 b[{a}, leave {y}] = {b:+.3f}")

    # doses as registered (2021 post-window mean OMIE price as E; placebo windows only)
    dates = sorted(set(x.date[pre]))
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= S6.R0) & (eh.index.get_level_values(0) <= S6.R1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    to_x = lambda ser: np.nan_to_num(ser.reindex(idx).to_numpy())
    tab_full = RP.tables(dates, RP.power_table(), "full")
    tab_toll = CT.old_new_tables(dates)
    dose = {n: to_x(CT.series_dose(n, tab_full, ebar)) for n in POOL}
    dose["E0"] = to_x(CT.series_dose("E0", tab_toll, ebar))

    rows = []
    for m in ["M0", "M1", "M2", "M3", "M4", "M5"]:
        for target, names in (("pool", POOL), ("E0", ["E0"])):
            vals = {}
            for y in S6.SUMMERS:
                a_, b_ = S6.aligned(y)
                w = ((x.date >= a_) & (x.date <= b_)).to_numpy()
                ek = {n: E[(m, n, y)] for n in names}
                ec = {n: E[(m, f"PT_{n}" if m == "M5" else "PT", y)] for n in names}
                vals[y] = pooled(x, ek, ec, {n: np.where(w, dose[n], 0.0) for n in names}, pre, names)
            mean, sd, slope, se = spread(vals)
            loo = [spread({k: v for k, v in vals.items() if k != d})[3] for d in S6.SUMMERS]
            rows.append(dict(model=m, target=target, mean=mean, s=sd, slope=slope, s_e=se,
                             **{f"eta_{y}": v for y, v in vals.items()}, **{f"s_e_drop_{d}": v for d, v in zip(S6.SUMMERS, loo)}))
        print(m, "done", flush=True)
    R = pd.DataFrame(rows)
    R.round(6).to_csv(OUT / "tou_prediction_model_selection.csv", index=False)
    pd.set_option("display.width", 250)
    print(R[["model", "target", "mean", "s", "slope", "s_e"] + [f"eta_{y}" for y in S6.SUMMERS]].round(4).to_string(index=False))

    # G0b: M0 reproduces the registered pooled placebo values (full dose) and E0's six-summer placebo values
    # the csv keeps each placebo value to 3 decimals and the mean and sd to 5: values within rounding, mean and sd to 1e-4
    reg = pd.read_csv(OUT / "tou_industry_regulated_price_summary.csv")
    reg = reg[(reg.dose == "full") & reg.series.str.startswith("pool")].iloc[0]
    e0 = pd.read_csv(OUT / "tou_industry_six_summer_summary.csv").set_index("series").loc["E0"]
    P = R.set_index(["model", "target"])
    g0 = True
    for tgt, r in (("pool", reg), ("E0", e0)):
        v = {int(k): float(s) for k, s in (p.split(":") for p in r.placebos.split())}
        got = P.loc[("M0", tgt)]
        dv = max(abs(got[f"eta_{y}"] - v[y]) for y in S6.SUMMERS)
        dm, ds = abs(got["mean"] - r.placebo_mean), abs(got.s - r.placebo_sd)
        ok = dv <= 5.01e-4 and dm <= 1e-4 and ds <= 1e-4
        g0 &= ok
        print(f"G0b M0 {tgt}: max value diff {dv:.1e}, mean diff {dm:.1e}, sd diff {ds:.1e} -> {'pass' if ok else 'FAIL'}")
    if not g0 or dif > 1e-6:
        print("G0 FAILS: harness bug; nothing below is read")
        return

    pool = P.xs("pool", level="target")
    base = pool.loc["M0"]

    def rules(m):
        r = pool.loc[m]
        a = r.s_e <= 0.8 * base.s_e
        b = r.s <= 1.1 * base.s
        c = all(r[f"s_e_drop_{d}"] < base[f"s_e_drop_{d}"] for d in S6.SUMMERS)
        return a, b, c

    cands = pool.drop("M0")
    best = cands.s_e.min()
    near = cands[cands.s_e <= 1.05 * best]
    ch = near.s.idxmin()
    print(f"\nM0 pooled: s {base.s:.4f}, s_e {base.s_e:.4f}, slope {base.slope:+.4f}")
    for m in cands.index:
        a, b, c = rules(m)
        print(f"  {m}: s_e {cands.loc[m, 's_e']:.4f} ({cands.loc[m, 's_e'] / base.s_e - 1:+.0%}), s {cands.loc[m, 's']:.4f} "
              f"({cands.loc[m, 's'] / base.s - 1:+.0%}); (a) {a} (b) {b} (c) {c}")
    a, b, c = rules(ch)
    print(f"\nSTEP 1 challenger: {ch} (within 5% of the smallest s_e: {list(near.index)}); adopted: {bool(a and b and c)}")
    a3, b3, c3 = rules("M3")
    print(f"STEP 3 (amendment B) M3 on its own: (a) {a3} (b) {b3} (c) {c3} -> adopted on its own: {bool(a3 and b3 and c3)}")


if __name__ == "__main__":
    main()
