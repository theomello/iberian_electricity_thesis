"""Part C of docs/specs/2026-11-26-orthogonal-and-sensitivity-design.md: the 2020 summer as a seventh placebo (flagged, not an equal draw).

LASSO refits that leave 2020 out (keys "(2020,)") for E0, 6.2, 6.3, 6.4 and Portugal, then the baseline estimate (E0, 6.2-6.4) and the
joint-regression estimate (6.2-6.4) on the aligned 2020 window with the dose laid on it. 1 March - 30 June 2020 is excluded (COVID), so the
window is effectively 1 July - 15 September. Not added to any registered placebo set; used as the observed 2020 anchor in Part B.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_drift_location as DL  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_industry_regulated_price as RP  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402

OUT = S6.OUT
SHIFTS = [k for k in range(-9, 10) if abs(k) >= 3]
CACHE = CT.CACHE / "placebo2020_errors.parquet"


def refit(x, clean):
    if CACHE.exists() and "--refit" not in sys.argv:
        c = pd.read_parquet(CACHE)
        return {tuple(k.split("|", 1)): c[k] for k in c.columns}
    tasks = []
    for n in ["E0", "6.2", "6.3", "6.4"]:
        xx = x.copy()
        xx.loc[~xx.date.dt.year.isin(clean[n] | {2021}), f"load_{n}"] = np.nan
        tasks.append((n, xx, f"load_{n}", "temp_es", "hol_es", (2020,)))
    tasks.append(("PT", x, "load_pt", "temp_pt", "hol_pt", (2020,)))
    print(f"fitting {len(tasks)} LASSO sets leaving 2020 out", flush=True)
    res = Parallel(n_jobs=4, verbose=5)(delayed(CT.one_task)(*t) for t in tasks)
    errs = {(n, str(ex)): e for n, ex, e in res}
    pd.DataFrame({f"{k[0]}|{k[1]}": v for k, v in errs.items()}).to_parquet(CACHE)
    return errs


def main():
    x = S6.build()
    clean = S6.gates(x)
    covid = x.date.between(*EV.COVID)
    pre = x.date.dt.year.isin(S6.YEARS) & ~covid
    errs = S6.errors(x, clean)
    errs.update(refit(x, clean))
    a, b = S6.aligned(2020)
    w = ((x.date >= a) & (x.date <= b)).to_numpy()
    win_pre = w & pre.to_numpy()
    n_exp = int(win_pre.sum())
    print(f"2020 window {a.date()} -> {b.date()}: {n_exp} hours inside the data after the COVID exclusion ({n_exp / 24:.0f} days of {S6.LEN})", flush=True)
    for n in ["E0", "6.2", "6.3", "6.4"]:
        have = int((win_pre & x[f"load_{n}"].notna().to_numpy()).sum())
        e_have = int((win_pre & errs[(n, "(2020,)")].reindex(x.index).notna().to_numpy()).sum())
        print(f"C1 {n}: load present {have / n_exp:.3f}, error present {e_have / n_exp:.3f} -> {'pass' if have / n_exp >= 0.99 and e_have / n_exp >= 0.99 else 'FAIL'}")
    dates = sorted(set(x.date[pre]) | set(pd.date_range(S6.R0, S6.R1)))
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= S6.R0) & (eh.index.get_level_values(0) <= S6.R1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    to_x = lambda ser: np.nan_to_num(ser.reindex(idx).to_numpy())
    ren = pd.read_parquet(RP.T_ROOT / "data/ren/ren_market_prices.parquet")
    ren = ren[ren.series == "ES"]
    loc = ren.utc_timestamp.dt.tz_convert("Europe/Madrid")
    wp = ren.assign(date=pd.to_datetime(loc.dt.date.to_numpy()), hour=loc.dt.hour.to_numpy()).groupby(["date", "hour"]).value.mean()
    pt = RP.power_table()
    tab_e0 = CT.old_new_tables(dates)
    orig = RP.TS.new_period_6

    def dose(tar, k=0):
        if k:
            RP.TS.new_period_6 = lambda d, h, hol: orig(d, (h + k) % 24, hol)
        try:
            tab = RP.tables(dates, pt, "full", wp=wp)
        finally:
            RP.TS.new_period_6 = orig
        return to_x(CT.series_dose(tar, tab, ebar))

    rows = []
    # baseline estimates
    d_e0 = to_x(CT.series_dose("E0", tab_e0, ebar))
    b, _ = DL.eta_variant(x, errs, "(2020,)", {"E0": np.where(w, d_e0, 0.0)}, pre, ["E0"], (a, b_ := S6.aligned(2020)[1]), "baseline")
    rows.append(dict(series="E0", spec="baseline", beta=b))
    print(f"E0 baseline 2020: {b:+.4f}", flush=True)
    for tar in ("6.2", "6.3", "6.4"):
        real = dose(tar)
        b, _ = DL.eta_variant(x, errs, "(2020,)", {tar: np.where(w, real, 0.0)}, pre, [tar], (a, b_), "baseline")
        rows.append(dict(series=tar, spec="baseline", beta=b))
        # joint regression (main spec): screened shifted calendars, PCs covering 90% of variance, at most 5
        win21 = ((x.date >= S6.R0) & (x.date <= S6.R1)).to_numpy()
        work = (x.dow < 5).to_numpy() & (x.hol_es == 0).to_numpy()
        cfs = []
        for k in SHIFTS:
            dk = dose(tar, k)
            if abs(float(np.corrcoef(real[win21 & work], dk[win21 & work])[0, 1])) <= 0.5:
                cfs.append(dk)
        s = CT.make_stack(x, errs[(tar, "(2020,)")], errs[("PT", "(2020,)")], "PT", pre)
        F = CT.fe3(s)
        y = CT.EL.resid(F, s.e)
        spain, src = s.area.to_numpy() == 0, s.src.to_numpy()
        col = lambda dp: np.where(spain, np.where(w, dp, 0.0)[src], 0.0)
        p0 = CT.EL.resid(F, col(real))
        C = np.column_stack([CT.EL.resid(F, col(d)) for d in cfs])
        ev, V = np.linalg.eigh(C.T @ C)
        o = np.argsort(ev)[::-1]
        ev, V = ev[o], V[:, o]
        J = int(min(5, np.searchsorted(np.cumsum(ev) / ev.sum(), 0.90) + 1))
        X = np.column_stack([p0, (C @ V)[:, :J]])
        bj = float(np.linalg.lstsq(X, y, rcond=None)[0][0])
        rows.append(dict(series=tar, spec="joint", beta=bj))
        print(f"{tar}: baseline {b:+.4f}  joint {bj:+.4f}  ({len(cfs)} calendars, J {J})", flush=True)
    R = pd.DataFrame(rows)
    # C2: against the line through 2014-2019 and the largest year-to-year change
    s3 = pd.read_csv(OUT / "tou_tariff_drift_step3.csv").set_index("series")
    s6 = pd.read_csv(OUT / "tou_industry_six_summer.csv")
    e0 = s6[(s6.series == "E0") & (s6["shift"] == 0)].set_index("summer").eta
    paths = {("E0", "baseline"): e0.loc[S6.SUMMERS].to_numpy()}
    for t in ("6.2", "6.3", "6.4"):
        pl = dict(p.split(":") for p in s3.loc[t, "placebos"].split())
        paths[(t, "baseline")] = np.array([float(pl[str(y)]) for y in S6.SUMMERS])
        J_ = pd.read_csv(OUT / f"tou_joint_regression_{t}.csv")
        paths[(t, "joint")] = J_[J_.variant == "main"].set_index("summer").beta.loc[S6.SUMMERS].to_numpy()
    ex, fl = [], []
    for r in R.itertuples():
        pl = paths[(r.series, r.spec)]
        sl, ic = np.polyfit(S6.SUMMERS, pl, 1)
        extrap = ic + sl * 2020
        mx = float(np.abs(np.diff(pl)).max())
        ex.append(extrap); fl.append(abs(r.beta - extrap) > mx)
    R["extrapolated_2020"], R["covid_flag"] = ex, fl
    R.round(5).to_csv(OUT / "tou_placebo_2020.csv", index=False)
    print(R.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
