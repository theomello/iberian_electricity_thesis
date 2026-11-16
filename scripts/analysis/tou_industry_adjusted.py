"""Placebo-adjusted industry elasticity (docs/specs/2026-11-16-industry-adjusted-design.md).

Equation 4 against Portugal (primary) and France (check) for E0, E1+E2, IND (E1-E6) and the tariff series 6.2-6.4, on the real window 2021-06-01 -> 2021-09-15 and on the same dose laid on
2018-06-01 -> 2018-09-15 and 2019-06-01 -> 2019-09-15 (cross-fitted errors). eta_adj = eta_real - mean(eta_p18, eta_p19);
sd_adj = sqrt(se_real^2 + (se_p18^2 + se_p19^2)/4 + ((eta_p18 - eta_p19)/2)^2). Reuses data/cache_tou/cross_tariff_errors.parquet; new fits (IND, France cross-fits) go to cross_tariff_ind_errors.parquet.
Writes outputs/tables/tou_industry_adjusted.csv and prints the seven registered rules.
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
import tou_lasso_paper as L  # noqa: E402

TSP = pd.Timestamp
POST0, POST1 = CT.POST0, CT.POST1
P18 = (TSP("2018-06-01"), TSP("2018-09-15"))
P19 = (CT.PL0, CT.PL1)
SERIES = ["E0", "E1+E2", "IND", "6.2", "6.3", "6.4"]
COMP = {"E1+E2": [1202, 1203], "E3": [1204], "E4": [1205], "E56": [1206, 1207]}
COMP_TARIFF = {"E1+E2": "E1+E2", "E3": "6.2", "E4": "6.3", "E56": "6.4"}
CACHE_NEW = CT.CACHE / "cross_tariff_ind_errors.parquet"


def new_errors(x):
    if CACHE_NEW.exists() and "--refit" not in sys.argv:
        c = pd.read_parquet(CACHE_NEW)
        return {tuple(k.split("|", 1)): c[k] for k in c.columns}
    tasks = [("IND", x, "load_IND", "temp_es", "hol_es", ex) for ex in ((), (2018,), (2019,))]
    tasks += [("FR", x, "load_fr", "temp_es", "hol_es", ex) for ex in ((2018,), (2019,))]
    res = Parallel(n_jobs=min(4, os.cpu_count() or 1), verbose=5)(delayed(CT.one_task)(*t) for t in tasks)
    errs = {(n, str(ex)): e for n, ex, e in res}
    pd.DataFrame({f"{k[0]}|{k[1]}": v for k, v in errs.items()}).to_parquet(CACHE_NEW)
    return errs


def main():
    x = D.prep(T.build("e0", end="2021-09-15"))
    for name, ids in {**CT.LOADS, "IND": [1202, 1203, 1204, 1205, 1206, 1207], **{f"c_{k}": v for k, v in COMP.items()}}.items():
        x = x.merge(CT.esios_load(ids).rename(columns={"v": f"load_{name}"}), on=["date", "hour"], how="left")
    x = x.merge(CT.france_load(), on=["date", "hour"], how="left")
    errs = CT.get_errors(x)
    errs.update(new_errors(x))
    print("errors ready", flush=True)

    covid = x.date.between(*EV.COVID)
    pre = (x.date >= "2018-01-01") & (x.date <= "2020-12-31") & ~covid
    shares = {k: float(x.loc[pre, f"load_c_{k}"].mean()) for k in COMP}
    tot = sum(shares.values())
    wts = {k: v / tot for k, v in shares.items()}
    print("IND dose weights:", {k: round(v, 3) for k, v in wts.items()}, flush=True)

    dates = list(pd.date_range(POST0, POST1)) + list(pd.date_range(*P19)) + list(pd.date_range(*P18))
    tabs = CT.old_new_tables(dates)
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= POST0) & (eh.index.get_level_values(0) <= POST1)].mean())
    ehx = eh.clip(lower=0)
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    to_x = lambda ser: np.nan_to_num(ser.reindex(idx).to_numpy())

    def dose(n, e, **kw):
        if n == "IND":
            return sum(wts[k] * to_x(CT.series_dose(COMP_TARIFF[k], tabs, e)) for k in COMP)
        return to_x(CT.series_dose(n, tabs, e, **kw))

    win = {w: ((x.date >= a) & (x.date <= b)).to_numpy() for w, (a, b) in {"real": (POST0, POST1), "p18": P18, "p19": P19}.items()}
    real_mask = (((x.date >= "2018-01-01") & (x.date <= "2020-12-31")) | pd.Series(win["real"], index=x.index)) & ~covid
    plc_mask = (x.date >= "2018-01-01") & (x.date <= P19[1])
    year = x.date.dt.year

    def cf(n):
        a, b = errs[(n, "(2018,)")], errs[(n, "(2019,)")]
        return pd.concat([a[year.reindex(a.index) == 2018], b[year.reindex(b.index) == 2019]])
    ctrl = {"PT": (errs[("PT", "()")], cf("PT")), "FR": (errs[("FR", "()")], cf("FR"))}

    def dose_summary(dpx):
        y = x[win["real"]].assign(dp=dpx[win["real"]])
        ev, ni = y.hour.isin([18, 19, 20, 21]), y.hour < 8
        m = lambda h, k: y[h & (y.kind == k)].dp.mean()
        return (m(ev, "work") - m(ni, "work")) - (m(ev, "wknd") - m(ni, "wknd"))

    # dose variants per series
    variants = {}
    for n in SERIES:
        v = {"central": dose(n, ebar), "E=60": dose(n, 60.0), "hourly": dose(n, ehx)}
        if n in ("E0", "E1+E2"):
            w0 = CT.MIX[n][0][1]
            v["w-10"], v["w+10"] = dose(n, ebar, w1=w0 - 0.1), dose(n, ebar, w1=w0 + 0.1)
        variants[n] = v

    rows = []
    for n in SERIES:
        ek_real, ek_cf = errs[(n, "()")], cf(n)
        sd_within = x[win["real"]].assign(dp=variants[n]["central"][win["real"]]).groupby("date").dp.std().mean()
        for c, (ec_real, ec_cf) in ctrl.items():
            fr = CT.Fit(CT.make_stack(x, ek_real, ec_real, c, real_mask & (x.load_fr.notna() if c == "FR" else True)))
            fp = CT.Fit(CT.make_stack(x, ek_cf, ec_cf, c, plc_mask & (x.load_fr.notna() if c == "FR" else True)))
            for vname, dpx in variants[n].items():
                r = fr.eta(np.where(win["real"], dpx, 0.0))
                a = fp.eta(np.where(win["p18"], dpx, 0.0))
                b = fp.eta(np.where(win["p19"], dpx, 0.0))
                adj = r["eta_am"] - (a["eta_am"] + b["eta_am"]) / 2
                sd = np.sqrt(r["se_am"] ** 2 + (a["se_am"] ** 2 + b["se_am"] ** 2) / 4 + ((a["eta_am"] - b["eta_am"]) / 2) ** 2)
                row = dict(series=n, control=c, variant=vname, eta_real=r["eta_am"], se_real=r["se_am"], eta_p18=a["eta_am"], se_p18=a["se_am"], eta_p19=b["eta_am"], se_p19=b["se_am"],
                           eta_adj=adj, sd_adj=sd, lo=adj - 1.96 * sd, hi=adj + 1.96 * sd, within_day_sd=sd_within, dose_ddd=dose_summary(dpx))
                if vname == "central":
                    rf = {}
                    for lab, (s0, e0) in (("real", (POST0, POST1)), ("p18", P18), ("p19", P19)):
                        err = ((ek_real - ec_real) if lab == "real" else (ek_cf - ec_cf)).reindex(x.index)
                        rf[lab] = L.cell_ddd(x, err, s0, e0)[0]
                    row.update(rf_real=rf["real"], rf_p18=rf["p18"], rf_p19=rf["p19"])
                rows.append(row)
                print(n, c, vname, {k: round(float(row[k]), 3) for k in ("eta_real", "eta_p18", "eta_p19", "eta_adj", "sd_adj")}, flush=True)
    R = pd.DataFrame(rows)
    R.round(5).to_csv(T.OUT / "tou_industry_adjusted.csv", index=False)

    pd.set_option("display.width", 220)
    cen = R[(R.control == "PT") & (R.variant == "central")].set_index("series")
    fr_ = R[(R.control == "FR") & (R.variant == "central")].set_index("series")
    print("\ncentral, Portugal:\n", cen[["eta_real", "eta_p18", "eta_p19", "eta_adj", "sd_adj", "lo", "hi", "within_day_sd", "dose_ddd"]].round(3).to_string())
    print("France:\n", fr_[["eta_real", "eta_p18", "eta_p19", "eta_adj", "sd_adj", "lo", "hi"]].round(3).to_string())
    print("\nRULE 1 readable:", {n: bool(cen.loc[n, "within_day_sd"] >= 0.02) for n in SERIES})
    e0 = cen.loc["E0"]
    print("RULE 2 E0 eta_adj in [-0.15,-0.03]:", bool(-0.15 <= e0.eta_adj <= -0.03), round(float(e0.eta_adj), 3))
    for n in SERIES:
        c = cen.loc[n]
        rd = bool(c.within_day_sd >= 0.02)
        r3 = bool(np.sign(c.eta_p18) == np.sign(c.eta_p19) and abs(c.eta_p18 - c.eta_p19) < 0.5 * abs(c.eta_real))
        r4 = bool(c.eta_adj < 0 and c.hi < 0)
        r5 = bool(c.rf_real - (c.rf_p18 + c.rf_p19) / 2 < 0 and abs(c.rf_real) > abs(c.rf_p18) and abs(c.rf_real) > abs(c.rf_p19))
        f = fr_.loc[n]
        r6 = bool(np.sign(f.eta_adj) == np.sign(c.eta_adj) and f.lo <= c.hi and c.lo <= f.hi)
        sens = R[(R.series == n) & (R.control == "PT") & (R.variant.isin(["E=60", "hourly"]))]
        r7 = bool(((sens.eta_adj - c.eta_adj).abs() <= 0.3 * abs(c.eta_adj)).all())
        print(f"{n}: readable {rd} | R3 placebo years agree {r3} | R4 detected {r4} | R5 reduced form {r5} | R6 France {r6} | R7 sensitivity {r7} | eta_adj {c.eta_adj:.3f} [{c.lo:.3f}, {c.hi:.3f}]")


if __name__ == "__main__":
    main()
