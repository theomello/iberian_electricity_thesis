"""Industry response to the 2021 reform against six pre-reform summers (docs/specs/2026-11-18-industry-six-summer-ri-design.md).

    .venv/bin/python scripts/analysis/tou_industry_six_summer.py --check   # X0 data gates only
    .venv/bin/python scripts/analysis/tou_industry_six_summer.py           # gates, errors, rules R0-R5

Statistic: tou_cross_tariff.Fit.eta (eta_am), Spanish series minus Portugal (REN), central dose (E = post-window mean OMIE).
Prediction step: the paper's per-hour LASSO (tou_lasso_paper.area_errors), fitted leave-one-year-out on the series' clean
years of 2014-2020 (COVID out). Errors for summer Y come from the model that leaves Y out; for 2021 from the model on all
clean years. Each fit uses its own model's errors for every row of the stack, so treated and placebo summers follow one
procedure. One aligned 107-day window per summer (weekday-aligned with 2021-06-01, start nearest 1 June); shifts of
-4..+4 weeks are descriptive. Inference by summer: prediction t-test (S-1 df) and rank. Deterministic.
IND dose weights use 2018-2020 component shares, as in the earlier industry runs, so the 2021 dose is unchanged.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402

TSP = pd.Timestamp
R0, R1 = CT.POST0, CT.POST1
LEN = (R1 - R0).days
YEARS = range(2014, 2021)
SUMMERS = [2014, 2015, 2016, 2017, 2018, 2019]
SERIES = ["E0", "IND", "E1+E2", "6.2", "6.3", "6.4"]
IDS = {"E0": [1201], "E1+E2": [1202, 1203], "6.2": [1216], "6.3": [1217], "6.4": [1218], "IND": [1202, 1203, 1204, 1205, 1206, 1207]}
COMP = {"E1+E2": [1202, 1203], "E3": [1204], "E4": [1205], "E56": [1206, 1207]}
COMP_TARIFF = {"E1+E2": "E1+E2", "E3": "6.2", "E4": "6.3", "E56": "6.4"}
NEEDS_E12 = {"IND", "E1+E2"}
CACHE = CT.CACHE / "six_summer_errors.parquet"
OUT = T.OUT


def gates(x):
    """X0: per-year data gates. Returns {series: set of clean years}."""
    m = lambda ids: CT.esios_load(ids).assign(ym=lambda d: d.date.dt.strftime("%Y-%m"))
    tot = m([1193]).groupby("ym").v.sum()
    # sum with absent hours as zero: E5 (1206) has gaps (650 days from spring 2014), and an aligned sum would make them NaN
    e = sum(m([i]).groupby("ym").v.sum() for i in (1202, 1203, 1204, 1205, 1207)).add(
        m([1206]).groupby("ym").v.sum(), fill_value=0).add(m([1201]).groupby("ym").v.sum(), fill_value=0)
    ratio = (e / tot).dropna()
    clean = {n: set(YEARS) for n in SERIES}
    print("X0 data gates")
    for y in (2014, 2017):
        r = ratio[ratio.index.str.startswith(str(y))]
        ok = bool(len(r) == 12 and (r.sub(1).abs() <= 0.01).all())
        print(f"  E0-E6 / 1193 in {y}: min {r.min():.4f} max {r.max():.4f} months {len(r)} -> {'pass' if ok else 'FAIL'}")
        if not ok:
            for n in NEEDS_E12:
                clean[n].discard(y)
    for n in NEEDS_E12:
        clean[n] -= {2015, 2016}  # registered: E1, E2 incomplete at source
    hours = x.groupby(x.date.dt.strftime("%Y-%m")).size()
    for n in ["E0", "6.2", "6.3", "6.4"]:
        have = x.dropna(subset=[f"load_{n}"]).groupby(x.date.dt.strftime("%Y-%m")).size()
        miss = (hours - have.reindex(hours.index).fillna(0))
        miss = miss[(miss.index >= "2014-01") & (miss.index <= "2017-12") & (miss > 0)]
        print(f"  {n} complete 2014-2017: {'pass' if miss.empty else 'FAIL ' + str(miss.to_dict())}")
        for ym in miss.index:
            clean[n].discard(int(ym[:4]))
    pt = pd.read_parquet(T.ROOT / "data/ren/ren_production_15min.parquet")
    pts = pt[(pt.series == "Consumption")].groupby("local_date").size()
    print(f"  REN points per day: {sorted(pts.value_counts().to_dict().items())}")
    return clean


def build():
    x = D.prep(T.build("e0", end="2021-09-15", start="2013-12-31"))
    for n, ids in {**IDS, **{f"c_{k}": v for k, v in COMP.items()}}.items():
        x = x.merge(CT.esios_load(ids).rename(columns={"v": f"load_{n}"}), on=["date", "hour"], how="left")
    return x


def aligned(y, shift=0):
    k = round((R0 - TSP(y, 6, 1)).days / 7)
    a = R0 - pd.Timedelta(days=7 * k) + pd.Timedelta(days=7 * shift)
    return a, a + pd.Timedelta(days=LEN)


def errors(x, clean):
    if CACHE.exists() and "--refit" not in sys.argv:
        c = pd.read_parquet(CACHE)
        return {tuple(k.split("|", 1)): c[k] for k in c.columns}
    tasks = []
    for n in SERIES:
        xx = x.copy()
        xx.loc[~xx.date.dt.year.isin(clean[n] | {2021}), f"load_{n}"] = np.nan
        for ex in [()] + [(y,) for y in SUMMERS if y in clean[n]]:
            tasks.append((n, xx, f"load_{n}", "temp_es", "hol_es", ex))
    for ex in [()] + [(y,) for y in SUMMERS]:
        tasks.append(("PT", x, "load_pt", "temp_pt", "hol_pt", ex))
    print(f"fitting {len(tasks)} LASSO models", flush=True)
    res = Parallel(n_jobs=min(4, os.cpu_count() or 1), verbose=5)(delayed(CT.one_task)(*t) for t in tasks)
    errs = {(n, str(ex)): e for n, ex, e in res}
    pd.DataFrame({f"{k[0]}|{k[1]}": v for k, v in errs.items()}).to_parquet(CACHE)
    return errs


def main():
    x = build()
    clean = gates(x)
    print("clean years:", {n: sorted(v) for n, v in clean.items()}, flush=True)
    if "--check" in sys.argv:
        for y in SUMMERS:
            a, b = aligned(y)
            w = x[(x.date >= a) & (x.date <= b)]
            gaps = {n: int(w[f"load_{n}"].isna().sum()) for n in SERIES if y in clean[n]}
            print(f"  aligned {y}: {a.date()} -> {b.date()}, missing hours {gaps}, temp/PT missing {int(w[['temp_es', 'temp_pt', 'load_pt']].isna().sum().sum())}")
        return
    errs = errors(x, clean)
    print("errors ready", flush=True)

    covid = x.date.between(*EV.COVID)
    pre = (x.date.dt.year.isin(YEARS)) & ~covid
    shares = {k: float(x.loc[pre & (x.date >= "2018-01-01"), f"load_c_{k}"].mean()) for k in COMP}
    wts = {k: v / sum(shares.values()) for k, v in shares.items()}
    dates = sorted(set(x.date[pre]) | set(pd.date_range(R0, R1)))
    tabs = CT.old_new_tables(dates)
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= R0) & (eh.index.get_level_values(0) <= R1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    to_x = lambda ser: np.nan_to_num(ser.reindex(idx).to_numpy())

    def dose(n):
        if n == "IND":
            return sum(wts[k] * to_x(CT.series_dose(COMP_TARIFF[k], tabs, ebar)) for k in COMP)
        return to_x(CT.series_dose(n, tabs, ebar))

    def dose_ddd(dpx, w):
        y = x[w].assign(dp=dpx[w])
        ev, ni = y.hour.isin([18, 19, 20, 21]), y.hour < 8
        m = lambda h, k: y[h & (y.kind == k)].dp.mean()
        return (m(ev, "work") - m(ni, "work")) - (m(ev, "wknd") - m(ni, "wknd"))

    rows = []
    for n in SERIES:
        dpx = dose(n)
        summers = [y for y in SUMMERS if y in clean[n]]
        # treated: model on all clean years, stack = clean pre years + 2021 window
        win = ((x.date >= R0) & (x.date <= R1)).to_numpy()
        f = CT.Fit(CT.make_stack(x, errs[(n, "()")], errs[("PT", "()")], "PT", pre | pd.Series(win, index=x.index)))
        r = f.eta(np.where(win, dpx, 0.0))
        rows.append(dict(series=n, summer=2021, shift=0, start=R0.date(), eta=r["eta_am"], se=r["se_am"], d=dose_ddd(dpx, win)))
        for y in summers:
            fy = CT.Fit(CT.make_stack(x, errs[(n, f"({y},)")], errs[("PT", f"({y},)")], "PT", pre))
            for sh in range(-4, 5):
                a, b = aligned(y, sh)
                w = ((x.date >= a) & (x.date <= b)).to_numpy()
                r = fy.eta(np.where(w, dpx, 0.0))
                rows.append(dict(series=n, summer=y, shift=sh, start=a.date(), eta=r["eta_am"], se=r["se_am"], d=dose_ddd(dpx, w)))
        print(n, "done", flush=True)
    R = pd.DataFrame(rows)
    R.round(6).to_csv(OUT / "tou_industry_six_summer.csv", index=False)

    al = R[R["shift"] == 0].set_index(["series", "summer"])
    # 6.4 common-shift correction, per summer (aligned windows), same formula everywhere
    corr = {}
    for yv in [2021] + SUMMERS:
        if ("IND", yv) in al.index and ("6.4", yv) in al.index:
            i, s = al.loc[("IND", yv)], al.loc[("6.4", yv)]
            corr[yv] = (i.eta * i.d - s.eta * s.d) / (i.d - s.d)
    for yv, v in corr.items():
        al.loc[("IND_corr", yv), ["eta", "d"]] = [v, np.nan]

    def test(n, drop=None):
        e = al.loc[n].eta
        real = float(e.loc[2021])
        pl = e.drop(2021)
        if drop is not None:
            pl = pl.drop(drop)
        S, m, s = len(pl), float(pl.mean()), float(pl.std(ddof=1))
        se = s * np.sqrt(1 + 1 / S)
        t = (real - m) / se
        q = stats.t.ppf(0.975, S - 1)
        return dict(series=n, S=S, eta_2021=real, placebo_mean=m, placebo_sd=s, t=t, p_t=float(stats.t.cdf(t, S - 1)),
                    p_rank=(1 + int((pl <= real).sum())) / (1 + S), lo=real - (m + q * se), hi=real - (m - q * se),
                    placebos=" ".join(f"{k}:{v:+.3f}" for k, v in pl.items()))

    S_ = pd.DataFrame([test(n) for n in SERIES + ["IND_corr"]])
    S_.round(5).to_csv(OUT / "tou_industry_six_summer_summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(S_.round(3).to_string(index=False))
    print("\nshifted windows (descriptive): placebo sd by series:",
          R[R.summer != 2021].groupby("series").eta.std().round(3).to_dict())
    old = pd.read_csv(OUT / "tou_industry_adjusted.csv")
    old = old[(old.control == "PT") & (old.variant == "central")].set_index("series").eta_real
    print("2021 estimate, 2018-20 fit vs leave-one-year-out 2014-20 fit:",
          {n: (round(float(old.get(n, np.nan)), 3), round(float(al.loc[(n, 2021)].eta), 3)) for n in SERIES})

    t = S_.set_index("series")
    ind = t.loc["IND"]
    loso = [test("IND", drop=y)["p_t"] for y in al.loc["IND"].index if y != 2021]
    print("\nRULES")
    print(f"R0 E0 machinery: p_t {t.loc['E0', 'p_t']:.4f} <= 0.05: {bool(t.loc['E0', 'p_t'] <= 0.05)}")
    print(f"R1 IND detection: p_t {ind.p_t:.4f} <= 0.05: {bool(ind.p_t <= 0.05)}")
    print(f"R2 IND rank: p_rank {ind.p_rank:.3f} == 1/(S+1) {1 / (ind.S + 1):.3f}: {bool(np.isclose(ind.p_rank, 1 / (ind.S + 1)))}")
    print(f"R3 IND null centred: |m| {abs(ind.placebo_mean):.4f} <= |eta|/3 {abs(ind.eta_2021) / 3:.4f}: {bool(abs(ind.placebo_mean) <= abs(ind.eta_2021) / 3)}")
    print(f"R4 IND leave-one-summer-out p_t {[round(p, 4) for p in loso]} all <= 0.10: {bool(max(loso) <= 0.10)}")
    c = t.loc["IND_corr"]
    print(f"R5 corrected: eta_corr {c.eta_2021:+.4f} < 0, p_t {c.p_t:.4f} <= 0.10: {bool(c.eta_2021 < 0 and c.p_t <= 0.10)}")


if __name__ == "__main__":
    main()
