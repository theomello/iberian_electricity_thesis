"""Cross-tariff dose-response of the June 2021 reform (docs/specs/2026-11-12-industry-voltage-design.md, incl. the amendment of the same day).

Five Spanish demand series: E0 (ESIOS 1201), E1+E2 (1202+1203), tariff series 6.2 (1216), 6.3 (1217), 6.4 (1218). First step: the paper's per-area-hour LASSO (tou_lasso_paper), trained on
2018-01-01 -> 2020-12-31 without March-June 2020. Dose: change in ln price by hour, dp = ln[(E + T_new)/(E + T_old)], tolls+charges of the old and new regimes by tariff and period
(tou_tariff_schedule, plus the 2.0A flat 44.027 -> 2.0TD P1/P2/P3 here), E = mean OMIE price over the post window; mixed series use the measured weights of the amendment
(E0 0.69 2.0TD / 0.31 3.0TD; E1+E2 0.20 3.1A->6.1TD / 0.80 6.1). Regression (paper's Eq. 4, no instrument because dp is set by the regulator): LASSO error on eta_k * dp * 1[Spain series k] with
hour x weekend x area, hour x weekend x month-of-sample and weekend x area x month-of-sample effects; clustered by area x month-of-sample (weekly beside). Post window 2021-06-01 -> 2021-09-15.
Placebo: the same dose pattern laid on 2019-06-01 -> 2019-09-15 with errors cross-fitted (each of 2018 and 2019 left out). Pooled Wald test of equal eta across series, clustered by week.
France control: errors from the same per-hour LASSO on RTE load with Spain's temperature and holidays as stand-ins (France's are not on disk). Writes outputs/tables/tou_cross_tariff_*.csv.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
from joblib import Parallel, delayed
from scipy.stats import chi2, spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_elasticity_paper as EL  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_lasso_paper as L  # noqa: E402
import tou_tariff_schedule as TS  # noqa: E402

TSP = pd.Timestamp
POST0, POST1 = TSP("2021-06-01"), TSP("2021-09-15")
PL0, PL1 = TSP("2019-06-01"), TSP("2019-09-15")
CACHE = T.ROOT / "data" / "cache_tou"
OUT = T.OUT
P20, OLD20 = {1: 133.118, 2: 41.772, 3: 6.001}, 44.027
LOADS = {"E0": [1201], "E1+E2": [1202, 1203], "6.2": [1216], "6.3": [1217], "6.4": [1218]}
MIX = {"E0": [("2.0", 0.69), ("3.0", 0.31)], "E1+E2": [("3.1->6.1", 0.20), ("6.1", 0.80)], "6.2": [("6.2", 1.0)], "6.3": [("6.3", 1.0)], "6.4": [("6.4", 1.0)]}


def esios_load(ids):
    s = sum(pd.read_parquet(T.ROOT / f"data/esios/esios_{i}.parquet")[["utc_timestamp", "value"]].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value for i in ids)
    loc = s.index.tz_convert("Europe/Madrid")
    return pd.DataFrame({"date": pd.to_datetime(loc.date), "hour": loc.hour, "v": s.to_numpy()}).drop_duplicates(["date", "hour"])


def france_load():
    f = pd.read_parquet(T.ROOT / "data/rte/eco2mix_national.parquet", columns=["utc", "consommation"]).drop_duplicates("utc").set_index("utc").consommation
    loc = f.index.tz_convert("Europe/Paris")
    return pd.DataFrame({"date": pd.to_datetime(loc.date), "hour": loc.hour, "load_fr": f.to_numpy()}).drop_duplicates(["date", "hour"])


def omie_hourly():
    d = pd.read_parquet(T.ROOT / "data/omie/prices/omie_day_ahead_prices.parquet")
    d = d[d.resolution_min == 60]
    loc = d.utc_timestamp.dt.tz_convert("Europe/Madrid")
    s = pd.DataFrame({"date": pd.to_datetime(loc.dt.date.to_numpy()), "hour": loc.dt.hour.to_numpy(), "p": d.price_es.to_numpy()}).drop_duplicates(["date", "hour"])
    return s.set_index(["date", "hour"]).p


# ---------- dose ----------
def old_new_tables(dates):
    s = TS.schedule(dates)
    hol = TS.holidays()
    rows = []
    for d in dates:
        off = d.dayofweek >= 5 or d in hol or (d.month == 1 and d.day == 6)
        for h in range(24):
            p = 3 if (off or h < 8) else (1 if (10 <= h < 14 or 18 <= h < 22) else 2)
            rows.append(dict(date=d, hour=h, tariff="2.0", old_price=OLD20, new_price=P20[p]))
    s = pd.concat([s[["date", "hour", "tariff", "old_price", "new_price"]], pd.DataFrame(rows)])
    return {t: g.set_index(["date", "hour"])[["old_price", "new_price"]] for t, g in s.groupby("tariff")}


def dp_tariff(tab, e):
    eb = e.reindex(tab.index).to_numpy() if isinstance(e, pd.Series) else e
    return pd.Series(np.log((eb + tab.new_price.to_numpy()) / (eb + tab.old_price.to_numpy())), index=tab.index)


def series_dose(name, tabs, e, w1=None, pure=None):
    mix = MIX[name]
    if pure is not None:
        mix = [(mix[pure][0], 1.0)]
    elif w1 is not None and len(mix) == 2:
        mix = [(mix[0][0], w1), (mix[1][0], 1 - w1)]
    out = None
    for t, wt in mix:
        v = wt * dp_tariff(tabs[t], e)
        out = v if out is None else out + v
    return out


# ---------- errors ----------
def one_task(name, x, load, temp, hol, excl):
    xx = x.dropna(subset=[load])
    return name, excl, L.area_errors(xx, load, temp, hol, excl)


def get_errors(x):
    path = CACHE / "cross_tariff_errors.parquet"
    if path.exists() and "--refit" not in sys.argv:
        c = pd.read_parquet(path)
        return {tuple(k.split("|", 1)): c[k] for k in c.columns}
    CACHE.mkdir(parents=True, exist_ok=True)
    tasks = []
    for ex in ((), (2018,), (2019,)):
        for name in LOADS:
            tasks.append((name, x, f"load_{name}", "temp_es", "hol_es", ex))
        tasks.append(("PT", x, "load_pt", "temp_pt", "hol_pt", ex))
    tasks.append(("FR", x, "load_fr", "temp_es", "hol_es", ()))
    res = Parallel(n_jobs=min(4, os.cpu_count() or 1), verbose=5)(delayed(one_task)(*t) for t in tasks)
    errs = {(n, str(ex)): e for n, ex, e in res}
    pd.DataFrame({f"{k[0]}|{k[1]}": v for k, v in errs.items()}).to_parquet(path)
    return errs


# ---------- regression ----------
def onehot(*cols):
    code = pd.factorize(pd.Series(list(zip(*cols))))[0]
    return sp.csr_matrix((np.ones(len(code)), (np.arange(len(code)), code)), shape=(len(code), code.max() + 1))


def fe3(s):
    return sp.hstack([onehot(s.hour, s.wk, s.area), onehot(s.hour, s.wk, s.ym), onehot(s.wk, s.area, s.ym)]).tocsr()


def ols_cl(y, X, g):
    X = X.reshape(len(y), -1)
    Ai = np.linalg.inv(X.T @ X)
    b = Ai @ (X.T @ y)
    u = y - X @ b
    sums = pd.DataFrame(X * u[:, None]).groupby(g).sum().to_numpy()
    G = len(sums)
    return b, Ai @ (sums.T @ sums) @ Ai * G / (G - 1), G


def make_stack(x, ek, ec, ctrl, mask):
    d = x[mask].copy()
    d["ek"], d["ec"] = ek.reindex(d.index), ec.reindex(d.index)
    d = d.dropna(subset=["ek", "ec"])
    a = pd.DataFrame({"area": 0, "src": d.index, "date": d.date, "hour": d.hour, "wk": d.weekend.astype(int), "e": d.ek, "hdh": np.maximum(18 - d.temp_es, 0), "cdh": np.maximum(d.temp_es - 18, 0)})
    if ctrl == "PT":
        wk, t = ((d.dow >= 5) | (d.hol_pt == 1)).astype(int), d.temp_pt
    else:
        wk, t = d.weekend.astype(int), d.temp_es  # France: stand-ins
    b = pd.DataFrame({"area": 1, "src": d.index, "date": d.date, "hour": d.hour, "wk": wk, "e": d.ec, "hdh": np.maximum(18 - t, 0), "cdh": np.maximum(t - 18, 0)})
    s = pd.concat([a, b], ignore_index=True)
    s["ym"] = s.date.dt.strftime("%Y-%m")
    s["moy"] = s.date.dt.month
    return s


def dp_on(s, dpx):
    return np.where(s.area.to_numpy() == 0, dpx[s.src.to_numpy()], 0.0)


class Fit:
    """Residualises the outcome once for a stack and fixed-effect set; fits any dose on it."""

    def __init__(self, s, F=None):
        self.s = s
        self.F = fe3(s) if F is None else F
        self.y = EL.resid(self.F, s.e)
        self.g_am = pd.factorize(s.area.astype(str) + "_" + s.ym)[0]
        self.g_wk = pd.factorize(s.date.dt.to_period("W").astype(str))[0]

    def eta(self, dpx):
        p = EL.resid(self.F, dp_on(self.s, dpx))
        out = {}
        for tag, g in (("am", self.g_am), ("wk", self.g_wk)):
            b, V, G = ols_cl(self.y, p, g)
            out[f"eta_{tag}"], out[f"se_{tag}"] = b[0], np.sqrt(V[0, 0])
            out[f"t_{tag}"] = b[0] / np.sqrt(V[0, 0])
        out["n"], out["clusters_am"] = len(self.y), len(np.unique(self.g_am))
        return out


def main():
    x = D.prep(T.build("e0", end="2021-09-15"))
    for name, ids in LOADS.items():
        x = x.merge(esios_load(ids).rename(columns={"v": f"load_{name}"}), on=["date", "hour"], how="left")
    x = x.merge(france_load(), on=["date", "hour"], how="left")
    print(f"x: {len(x)} rows; missing loads", {n: int(x[f'load_{n}'].isna().sum()) for n in LOADS}, "France", int(x.load_fr.isna().sum()), flush=True)

    # definition check: tariff series against voltage series, by month around the reform
    chk = x.assign(ym=x.date.dt.strftime("%Y-%m")).groupby("ym")[["load_6.2", "load_6.3", "load_6.4"]].sum()
    e3, e4, e6 = (esios_load([i]).assign(ym=lambda d: d.date.dt.strftime("%Y-%m")).groupby("ym").v.sum() for i in (1204, 1205, 1207))
    print("tariff / voltage series ratio by month (6.2/E3, 6.3/E4, 6.4/E6):", flush=True)
    r = pd.DataFrame({"6.2/E3": chk["load_6.2"] / e3.reindex(chk.index), "6.3/E4": chk["load_6.3"] / e4.reindex(chk.index), "6.4/E6": chk["load_6.4"] / e6.reindex(chk.index)})
    print(r.loc["2020-09":"2021-09"].round(3).to_string(), flush=True)

    errs = get_errors(x)
    print("errors ready", flush=True)

    # doses
    dates = list(pd.date_range(POST0, POST1)) + list(pd.date_range(PL0, PL1))
    tabs = old_new_tables(dates)
    eh = omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= POST0) & (eh.index.get_level_values(0) <= POST1)].mean())
    print(f"post-window mean OMIE price {ebar:.2f}", flush=True)
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    to_x = lambda ser: np.nan_to_num(ser.reindex(idx).to_numpy())
    real = (x.date >= POST0) & (x.date <= POST1)
    plc = (x.date >= PL0) & (x.date <= PL1)
    ehx = eh.clip(lower=0)

    def dose_x(name, kind, **kw):
        e = {"mean": ebar, "60": 60.0, "hour": ehx}[kind]
        d = to_x(series_dose(name, tabs, e, **kw))
        return d
    central = {n: dose_x(n, "mean") for n in LOADS}

    def dose_summary(dpx):
        y = x[real].assign(dp=dpx[real.to_numpy()])
        ev, ni = y.hour.isin([18, 19, 20, 21]), y.hour < 8
        m = lambda h, k: y[h & (y.kind == k)].dp.mean()
        return (m(ev, "work") - m(ni, "work")) - (m(ev, "wknd") - m(ni, "wknd"))
    rows_dose = []
    for n in LOADS:
        dp = pd.Series(central[n])[real.to_numpy()]
        sd_within = x[real].assign(dp=central[n][real.to_numpy()]).groupby("date").dp.std().mean()
        rows_dose.append(dict(series=n, dose_ddd=dose_summary(central[n]), within_day_sd=sd_within, mean_dp=float(dp.mean())))
    dose = pd.DataFrame(rows_dose).set_index("series")
    dose["readable"] = dose.within_day_sd >= 0.02
    print(dose.round(3).to_string(), flush=True)

    # samples
    covid = x.date.between(*EV.COVID)
    real_mask = (((x.date >= "2018-01-01") & (x.date <= "2020-12-31")) | real) & ~covid
    plc_mask = (x.date >= "2018-01-01") & (x.date <= PL1)
    ept = errs[("PT", "()")]
    efr = errs[("FR", "()")]
    cf = lambda n: pd.concat([errs[(n, "(2018,)")][x.date.dt.year.reindex(errs[(n, "(2018,)")].index) == 2018], errs[(n, "(2019,)")][x.date.dt.year.reindex(errs[(n, "(2019,)")].index) == 2019]])
    cf_pt = cf("PT")

    res, plac, rf_rows = [], [], []
    fits = {}
    for n in LOADS:
        ek = errs[(n, "()")]
        s_pt = make_stack(x, ek, ept, "PT", real_mask)
        fp = Fit(s_pt)
        fits[n] = fp
        spec_rows = [("central", central[n]), ("E=60", dose_x(n, "60")), ("E=hourly OMIE", dose_x(n, "hour"))]
        if len(MIX[n]) == 2:
            spec_rows += [(f"weight -10 pts on {MIX[n][0][0]}", dose_x(n, "mean", w1=MIX[n][0][1] - 0.1)), (f"weight +10 pts on {MIX[n][0][0]}", dose_x(n, "mean", w1=MIX[n][0][1] + 0.1)),
                          (f"pure {MIX[n][0][0]}", dose_x(n, "mean", pure=0)), (f"pure {MIX[n][1][0]}", dose_x(n, "mean", pure=1))]
        for lab, dpx in spec_rows:
            r = fp.eta(np.where(real.to_numpy(), dpx, 0.0))
            r.update(series=n, spec=lab, control="Portugal", dose_ddd=dose_summary(dpx))
            res.append(r)
            print(n, lab, {k: round(float(v), 4) for k, v in r.items() if k in ("eta_am", "se_am", "t_am", "t_wk")}, flush=True)
        # paper column-4 set (adds month-of-year x hour x weekend x area and temperature interactions)
        f4 = Fit(s_pt, EL.fe_matrix(s_pt, 4))
        r = f4.eta(np.where(real.to_numpy(), central[n], 0.0))
        r.update(series=n, spec="FE incl. month-of-year and temperature", control="Portugal", dose_ddd=dose_summary(central[n]))
        res.append(r)
        # France control
        xs = x[x[f"load_{n}"].notna() & x.load_fr.notna()]
        s_fr = make_stack(x, ek, efr, "FR", real_mask & x.load_fr.notna())
        r = Fit(s_fr).eta(np.where(real.to_numpy(), central[n], 0.0))
        r.update(series=n, spec="central", control="France", dose_ddd=dose.loc[n, "dose_ddd"])
        res.append(r)
        print(n, "France", {k: round(float(v), 4) for k, v in r.items() if k in ("eta_am", "se_am", "t_am")}, flush=True)
        # placebo 2019 (laid dose, cross-fitted errors)
        s_pl = make_stack(x, cf(n), cf_pt, "PT", plc_mask)
        dpl = np.where(plc.to_numpy(), to_x(series_dose(n, tabs, ebar)), 0.0)
        r = Fit(s_pl).eta(dpl)
        r.update(series=n, spec="placebo 2019", control="Portugal", dose_ddd=np.nan)
        res.append(r)
        print(n, "placebo", {k: round(float(v), 4) for k, v in r.items() if k in ("eta_am", "se_am", "t_am")}, flush=True)
        # reduced form: evening vs night, working vs weekend DDD of mean errors, Portugal and France
        for ctrl, ec in (("Portugal", ept), ("France", efr)):
            b, se = L.cell_ddd(x, (ek - ec).dropna(), POST0, POST1)
            rf_rows.append(dict(series=n, control=ctrl, rf_ddd=b, rf_se=se))
    R = pd.DataFrame(res)
    RF = pd.DataFrame(rf_rows)

    # pooled Wald across readable series, Portugal control, clustered by week
    read = [n for n in LOADS if dose.loc[n, "readable"]]
    allidx = None
    for n in read:
        ix = errs[(n, "()")].dropna().index
        allidx = ix if allidx is None else allidx.intersection(ix)
    allidx = allidx.intersection(ept.dropna().index)
    d = x.loc[allidx]
    d = d[real_mask.loc[allidx]]
    parts = []
    for i, n in enumerate(read):
        parts.append(pd.DataFrame({"area": i, "src": d.index, "date": d.date, "hour": d.hour, "wk": d.weekend.astype(int), "e": errs[(n, "()")].reindex(d.index),
                                   "dp": np.where(real.to_numpy(), central[n], 0.0)[d.index]}))
    parts.append(pd.DataFrame({"area": len(read), "src": d.index, "date": d.date, "hour": d.hour, "wk": ((d.dow >= 5) | (d.hol_pt == 1)).astype(int), "e": ept.reindex(d.index), "dp": 0.0}))
    s = pd.concat(parts, ignore_index=True)
    s["ym"] = s.date.dt.strftime("%Y-%m")
    F = fe3(s)
    y = EL.resid(F, s.e)
    X = np.column_stack([EL.resid(F, (s.dp * (s.area == i)).to_numpy()) for i in range(len(read))])
    g = pd.factorize(s.date.dt.to_period("W").astype(str))[0]
    b, V, G = ols_cl(y, X, g)
    Rm = np.zeros((len(read) - 1, len(read)))
    for i in range(len(read) - 1):
        Rm[i, i], Rm[i, i + 1] = 1, -1
    W = float((Rm @ b) @ np.linalg.inv(Rm @ V @ Rm.T) @ (Rm @ b))
    pw = 1 - chi2.cdf(W, len(read) - 1)
    pooled = pd.DataFrame({"series": read, "eta": b, "se": np.sqrt(np.diag(V))})
    print("pooled eta by series (weekly clusters, Portugal):\n", pooled.round(4).to_string(), f"\nWald equal eta: chi2({len(read) - 1}) = {W:.2f}, p = {pw:.3f}", flush=True)

    # ---- outputs
    R.round(5).to_csv(OUT / "tou_cross_tariff_main.csv", index=False)
    dose.round(4).to_csv(OUT / "tou_cross_tariff_dose.csv")
    RF.round(5).to_csv(OUT / "tou_cross_tariff_reduced_form.csv", index=False)
    pooled.assign(wald_chi2=W, wald_p=pw).round(5).to_csv(OUT / "tou_cross_tariff_pooled.csv", index=False)

    # ---- rules
    pd.set_option("display.width", 220)
    cen = R[(R.spec == "central") & (R.control == "Portugal")].set_index("series")
    pl = R[R.spec == "placebo 2019"].set_index("series")
    fr = R[(R.spec == "central") & (R.control == "France")].set_index("series")
    print("\ncentral:\n", cen[["eta_am", "se_am", "t_am", "eta_wk", "t_wk", "dose_ddd"]].round(3).to_string())
    print("placebo:\n", pl[["eta_am", "se_am", "t_am"]].round(3).to_string())
    print("France:\n", fr[["eta_am", "se_am", "t_am"]].round(3).to_string())
    print("reduced form (DDD of errors, evening vs night):\n", RF.round(4).to_string(index=False))
    print("\nRULE 1 readable:", dose.readable.to_dict(), dose.within_day_sd.round(3).to_dict())
    e0 = R[(R.series == "E0") & (R.control == "Portugal") & (R.spec.isin(["central", "pure 2.0", "pure 3.0"]))]
    ok2 = bool(((e0.eta_am < 0) & (e0.t_am <= -2) & (e0.eta_am >= -0.25) & (e0.eta_am <= -0.03)).all())
    print("RULE 2 E0 eta negative, t<=-2, in [-0.25,-0.03] (central and both pure tariffs):", ok2, e0[["spec", "eta_am", "t_am"]].round(3).values.tolist())
    ok3 = {n: bool(pl.loc[n, "t_am"] > -2 and cen.loc[n, "eta_am"] < pl.loc[n, "eta_am"]) for n in read}
    print("RULE 3 placebo t>-2 and real below placebo:", ok3)
    single = [n for n in ("6.2", "6.3", "6.4") if n in read]
    ok4 = {n: bool(cen.loc[n, "eta_am"] < 0 and cen.loc[n, "t_am"] <= -2) for n in single}
    print("RULE 4 single-tariff series negative with t<=-2:", ok4, "any:", any(ok4.values()))
    print(f"RULE 5 Wald equal eta not rejected at 5%: {pw >= 0.05} (p {pw:.3f})")
    rfp = RF[RF.control == "Portugal"].set_index("series").rf_ddd
    sp_ = spearmanr((-rfp.loc[read]).to_numpy(), dose.loc[read, "dose_ddd"].to_numpy())
    print(f"RULE 6 Spearman(-reduced form, dose) = {sp_.correlation:.2f} (>= 0.7 needed, {len(read)} series):", bool(sp_.correlation >= 0.7))
    ok7 = {n: bool(np.sign(fr.loc[n, "eta_am"]) == np.sign(cen.loc[n, "eta_am"])) for n in read}
    print("RULE 7 France same sign:", ok7)


if __name__ == "__main__":
    main()
