"""Randomization inference for the time-of-use estimates (docs/specs/2026-11-17-randomization-inference-design.md, rules RI0-RI6).

    .venv/bin/python scripts/analysis/tou_randomization_inference.py

Placebo windows: the real window 2021-06-01 -> 2021-09-15 shifted back by 7k days (weekday aligned), kept when inside 2018-01-01 -> 2020-12-31 and clear of the COVID block. Same Equation 4 statistic
(tou_cross_tariff.Fit.eta, eta_am), same dose structure laid on the placebo calendar, Portugal as control, errors cross-fitted by year (leave-2018/2019/2020-out). New leave-2020-out fits are cached in
data/cache_tou/cross_tariff_ri_errors.parquet. Writes outputs/tables/tou_randomization_inference.csv (one row per series and window) and ..._summary.csv.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402

TSP = pd.Timestamp
R0, R1 = CT.POST0, CT.POST1
SPAN0, SPAN1 = TSP("2018-01-01"), TSP("2020-12-31")
SERIES = ["E0", "E1+E2", "IND", "6.2", "6.3", "6.4"]
COMP = {"E1+E2": [1202, 1203], "E3": [1204], "E4": [1205], "E56": [1206, 1207]}
COMP_TARIFF = {"E1+E2": "E1+E2", "E3": "6.2", "E4": "6.3", "E56": "6.4"}
CACHE_RI = CT.CACHE / "cross_tariff_ri_errors.parquet"


def ri_errors(x):
    if CACHE_RI.exists() and "--refit" not in sys.argv:
        c = pd.read_parquet(CACHE_RI)
        return {tuple(k.split("|", 1)): c[k] for k in c.columns}
    tasks = [(n, x, f"load_{n}", "temp_es", "hol_es", (2020,)) for n in list(CT.LOADS) + ["IND"]]
    tasks.append(("PT", x, "load_pt", "temp_pt", "hol_pt", (2020,)))
    res = Parallel(n_jobs=min(4, os.cpu_count() or 1), verbose=5)(delayed(CT.one_task)(*t) for t in tasks)
    errs = {(n, str(ex)): e for n, ex, e in res}
    pd.DataFrame({f"{k[0]}|{k[1]}": v for k, v in errs.items()}).to_parquet(CACHE_RI)
    return errs


def windows():
    out = []
    for k in range(1, 400):
        a, b = R0 - pd.Timedelta(days=7 * k), R1 - pd.Timedelta(days=7 * k)
        if a < SPAN0 or b > SPAN1:
            continue
        if a <= TSP("2020-06-30") and b >= TSP("2020-03-01"):
            continue
        out.append((k, a, b))
    return out


def main():
    x = D.prep(T.build("e0", end="2021-09-15"))
    for n, ids in {**CT.LOADS, "IND": [1202, 1203, 1204, 1205, 1206, 1207], **{f"c_{k}": v for k, v in COMP.items()}}.items():
        x = x.merge(CT.esios_load(ids).rename(columns={"v": f"load_{n}"}), on=["date", "hour"], how="left")
    errs = CT.get_errors(x)
    errs.update(pd.read_parquet(CT.CACHE / "cross_tariff_ind_errors.parquet").pipe(lambda c: {tuple(k.split("|", 1)): c[k] for k in c.columns}))
    errs.update(ri_errors(x))
    print("errors ready", flush=True)

    covid = x.date.between(*EV.COVID)
    pre = (x.date >= "2018-01-01") & (x.date <= "2020-12-31") & ~covid
    real_mask = (pre | ((x.date >= R0) & (x.date <= R1))) & ~covid
    plc_mask = pre
    year = x.date.dt.year

    def cf(n):
        parts = [errs[(n, f"({y},)")][year.reindex(errs[(n, f"({y},)")].index) == y] for y in (2018, 2019, 2020)]
        return pd.concat(parts)

    shares = {k: float(x.loc[pre, f"load_c_{k}"].mean()) for k in COMP}
    tot = sum(shares.values())
    wts = {k: v / tot for k, v in shares.items()}
    W = windows()
    print(f"{len(W)} placebo windows (k {W[0][0]}..{W[-1][0]})", flush=True)

    dates = sorted(set(pd.date_range(SPAN0, SPAN1)) | set(pd.date_range(R0, R1)))
    tabs = CT.old_new_tables(dates)
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= R0) & (eh.index.get_level_values(0) <= R1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    to_x = lambda ser: np.nan_to_num(ser.reindex(idx).to_numpy())

    def dose(n):
        if n == "IND":
            return sum(wts[k] * to_x(CT.series_dose(COMP_TARIFF[k], tabs, ebar)) for k in COMP)
        return to_x(CT.series_dose(n, tabs, ebar))

    rows, summ = [], []
    real_win = ((x.date >= R0) & (x.date <= R1)).to_numpy()
    for n in SERIES:
        dpx = dose(n)
        fr = CT.Fit(CT.make_stack(x, errs[(n, "()")], errs[("PT", "()")], "PT", real_mask))
        er = fr.eta(np.where(real_win, dpx, 0.0))
        fp = CT.Fit(CT.make_stack(x, cf(n), cf("PT"), "PT", plc_mask))
        eta_s = []
        for k, a, b in W:
            w = ((x.date >= a) & (x.date <= b)).to_numpy()
            # placebo dose = the dose structure on the placebo calendar
            r = fp.eta(np.where(w, dpx, 0.0))
            eta_s.append(r["eta_am"])
            rows.append(dict(series=n, k=k, start=a.date(), end=b.date(), eta=r["eta_am"], se=r["se_am"]))
        eta_s = np.array(eta_s)
        ks = np.array([k for k, _, _ in W])
        starts = pd.to_datetime([a for _, a, _ in W])

        def stats(sel, label):
            e = eta_s[sel]
            N = len(e)
            p1 = (1 + (e <= er["eta_am"]).sum()) / (1 + N)
            p2 = (1 + (np.abs(e) >= abs(er["eta_am"])).sum()) / (1 + N)
            lo, hi = er["eta_am"] - np.quantile(e, 0.975), er["eta_am"] - np.quantile(e, 0.025)
            return dict(series=n, subset=label, N=N, eta_real=er["eta_am"], se_real=er["se_am"], placebo_mean=float(e.mean()), placebo_sd=float(e.std(ddof=1)), p_one_sided=p1, p_two_sided=p2,
                        eta_RI=er["eta_am"] - float(e.mean()), ci_lo=lo, ci_hi=hi)
        sel_all = np.ones(len(W), bool)
        keep, last = [], -999
        for i, k in enumerate(ks):
            if last == -999 or abs(k - last) >= 16:
                keep.append(i)
                last = k
        sel_no = np.zeros(len(W), bool)
        sel_no[keep] = True
        doy = starts.dayofyear
        sel_se = np.array([(s.year in (2018, 2019)) and abs((s - TSP(year=s.year, month=6, day=1)).days) <= 45 for s in starts])
        for sel, lab in ((sel_all, "all"), (sel_no, "non-overlapping"), (sel_se, "season-matched")):
            summ.append(stats(sel, lab))
        print(n, {k: round(float(v), 3) if not isinstance(v, str) else v for k, v in summ[-3].items() if k in ("eta_real", "placebo_mean", "placebo_sd", "p_one_sided", "eta_RI", "ci_lo", "ci_hi")}, flush=True)
    R, S = pd.DataFrame(rows), pd.DataFrame(summ)
    R.round(5).to_csv(T.OUT / "tou_randomization_inference.csv", index=False)
    S.round(5).to_csv(T.OUT / "tou_randomization_inference_summary.csv", index=False)
    pd.set_option("display.width", 220)
    print(S.round(3).to_string(index=False))

    e0 = S[S.series == "E0"].set_index("subset")
    prior = pd.read_csv(T.OUT / "tou_industry_adjusted.csv")
    prior = float(prior[(prior.series == "E0") & (prior.control == "PT") & (prior.variant == "central")].eta_adj.iloc[0])
    print(f"\nRI0 enough windows ({len(W)} >= 40): {len(W) >= 40}")
    print(f"RI1 headline one-sided p {e0.loc['all', 'p_one_sided']:.4f} <= 0.05: {bool(e0.loc['all', 'p_one_sided'] <= 0.05)}")
    print(f"RI2 |mean placebo| {abs(e0.loc['all', 'placebo_mean']):.4f} <= 0.03: {bool(abs(e0.loc['all', 'placebo_mean']) <= 0.03)}")
    print(f"RI3 non-overlapping p {e0.loc['non-overlapping', 'p_one_sided']:.3f} (N {int(e0.loc['non-overlapping', 'N'])}) <= 0.15: {bool(e0.loc['non-overlapping', 'p_one_sided'] <= 0.15)}")
    print(f"RI4 season-matched p {e0.loc['season-matched', 'p_one_sided']:.3f} (N {int(e0.loc['season-matched', 'N'])}) <= 0.10: {bool(e0.loc['season-matched', 'p_one_sided'] <= 0.10)}")
    print(f"RI5 eta_RI {e0.loc['all', 'eta_RI']:+.3f} vs two-year {prior:+.3f}, within 0.02: {bool(abs(e0.loc['all', 'eta_RI'] - prior) <= 0.02)}")
    print(f"RI6 interval [{e0.loc['all', 'ci_lo']:+.3f}, {e0.loc['all', 'ci_hi']:+.3f}] excludes zero: {bool(e0.loc['all', 'ci_hi'] < 0 or e0.loc['all', 'ci_lo'] > 0)}")


if __name__ == "__main__":
    main()
