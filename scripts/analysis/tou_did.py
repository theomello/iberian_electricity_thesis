"""Replication of the June 2021 time-of-use reform effect (Enrich, Li, Mizrahi, Reguant; JEEM 2024) on aggregate data.

Treated: Spain's regulated-retail schedule (ESIOS 352, hourly). Control: Portugal's hourly consumption (REN `Consumption`,
15-minute averaged to the hour). Window 2018-01-01 -> 2021-09-30, break 2021-06-01. Each country on its own local clock; the
outcome is the log of Spanish load minus the log of Portuguese load at the same local hour of the same date, so the
difference removes everything common to the date and hour. Period types follow the Spanish rule on the Spanish calendar:
off-peak = weekends, Spanish national holidays and 00-08h; peak = working days 10-14h and 18-22h; mid-peak = the rest.
Step 1 (DiD): the difference on post x period type, with period type, hour, weekday and month effects; four variants
(V1 base; V2 + linear trend; V3 + temperature and holiday differences; V4 year-month effects, which identify only the
contrast between period types). Step 2 (prediction errors, Burlig et al. 2020): LASSO per country on the pre-period
(2018-01 -> 2021-05) to predict the post-period, then the mean prediction-error difference by period type. Placebos: the
same on fake breaks at the 1st of every month 2019-01 -> 2020-12 with a 4-month post-window, and fake peaks on weekends.
Pre-set stop rules in docs/specs/2026-11-11-tou-replication-design.md section 3. Outputs outputs/tables/tou_did_*.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LassoCV
from sklearn.model_selection import TimeSeriesSplit

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables"
BREAK = pd.Timestamp("2021-06-01")
END = pd.Timestamp("2021-09-30")
TYPES = ["peak", "mid", "off"]


def hourly(s, tz):
    s = s.copy()
    s.index = s.index.tz_convert(tz)
    return s


def build() -> pd.DataFrame:
    es = pd.read_parquet(ROOT / "data/esios/esios_352.parquet")[["utc_timestamp", "value"]].drop_duplicates("utc_timestamp")
    es = es.set_index("utc_timestamp").value
    pt = pd.read_parquet(ROOT / "data/ren/ren_production_15min.parquet")
    pt = pt[pt.series == "Consumption"].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value_mw
    pt = pt.resample("1h").mean()
    t = pd.read_parquet(ROOT / "data/weather/temperature_population_hourly.parquet", columns=["city", "country", "utc_timestamp", "temperature_2m"])
    tes = t[t.country == "ES"].groupby("utc_timestamp").temperature_2m.mean()
    tpt = t[t.country == "PT"].groupby("utc_timestamp").temperature_2m.mean()
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    hpt = set(pd.to_datetime(hol[hol.area == "PT"].date))
    rows = {}
    for name, s, tz, temp in [("es", es, "Europe/Madrid", tes), ("pt", pt, "Europe/Lisbon", tpt)]:
        d = pd.DataFrame({"load": s, "temp": temp}).dropna()
        d = d[(d.index >= "2017-12-31") & (d.index < "2021-10-01")]
        loc = d.index.tz_convert(tz)
        d["date"] = pd.to_datetime(loc.date)
        d["hour"] = loc.hour
        d = d.drop_duplicates(["date", "hour"])
        rows[name] = d.set_index(["date", "hour"])
    x = rows["es"].join(rows["pt"], how="inner", lsuffix="_es", rsuffix="_pt").dropna().reset_index()
    x["dow"] = x.date.dt.dayofweek
    x["month"] = x.date.dt.month
    x["ym"] = x.date.dt.strftime("%Y-%m")
    x["hol_es"] = x.date.isin(hes).astype(float)
    x["hol_pt"] = x.date.isin(hpt).astype(float)
    x["d"] = np.log(x.load_es) - np.log(x.load_pt)
    x["hdh_d"] = np.maximum(18 - x.temp_es, 0) - np.maximum(18 - x.temp_pt, 0)
    x["cdh_d"] = np.maximum(x.temp_es - 18, 0) - np.maximum(x.temp_pt - 18, 0)
    off_day = (x.dow >= 5) | (x.hol_es == 1)
    x["type"] = np.where(off_day | (x.hour < 8), "off", np.where(x.hour.isin([10, 11, 12, 13, 18, 19, 20, 21]), "peak", "mid"))
    # fake types on weekend / holiday days (same hours, as the paper's weekend check)
    x["ftype"] = np.where(x.hour < 8, "off", np.where(x.hour.isin([10, 11, 12, 13, 18, 19, 20, 21]), "peak", "mid"))
    x["weekend"] = off_day
    x = x[x.date <= END]
    return x.sort_values(["date", "hour"]).reset_index(drop=True)


def dummies(x, cols):
    return pd.concat([pd.get_dummies(x[c].astype(str), prefix=c, drop_first=True, dtype=float) for c in cols], axis=1)


def hac_cluster(X, e, g):
    XtX = np.linalg.pinv(X.T @ X)
    s = pd.DataFrame(X * e[:, None]).groupby(g).sum().to_numpy()
    return XtX @ (s.T @ s) @ XtX


def did(x, brk, y="d", types="type", subset=None, variant="V1"):
    s = x if subset is None else x[subset]
    post = (s.date >= brk).astype(float).to_numpy()
    tp = s[types].to_numpy()
    cols = {f"post_{t}": post * (tp == t) for t in TYPES}
    base = [dummies(s, ["hour", "dow"]), pd.get_dummies(s[types], drop_first=True, dtype=float)]
    if variant != "V4":
        base.append(dummies(s, ["month"]))
    else:
        base.append(dummies(s, ["ym"]))
    if variant in ("V2", "V3"):
        base.append(pd.DataFrame({"trend": (s.date - s.date.min()).dt.days / 365.0, "trend_x_off": (s.date - s.date.min()).dt.days / 365.0 * (tp == "off"),
                                  "trend_x_peak": (s.date - s.date.min()).dt.days / 365.0 * (tp == "peak")}, index=s.index))
    if variant == "V3":
        base.append(s[["hdh_d", "cdh_d", "hol_es", "hol_pt"]])
    X = pd.concat(base + [pd.DataFrame(cols, index=s.index)], axis=1)
    X = X.loc[:, X.std() > 0]
    X.insert(0, "const", 1.0)
    Xv = X.to_numpy()
    yv = s[y].to_numpy()
    b = np.linalg.pinv(Xv) @ yv
    e = yv - Xv @ b
    V = hac_cluster(Xv, e, s.date.dt.to_period("W").astype(str).factorize()[0])
    names = list(X.columns)
    out = {t: (b[names.index(f"post_{t}")], np.sqrt(V[names.index(f"post_{t}"), names.index(f"post_{t}")])) for t in TYPES if f"post_{t}" in names}
    # contrasts between period types (the only thing V4's year-month effects identify)
    for a in ("peak", "mid"):
        i, j = names.index(f"post_{a}"), names.index("post_off")
        out[f"{a}-off"] = (b[i] - b[j], np.sqrt(V[i, i] + V[j, j] - 2 * V[i, j]))
    return out


def features(s):
    f = pd.concat([pd.get_dummies((s.hour.astype(str) + "_" + np.where(s.weekend, "w", s.dow.astype(str))), dtype=float),
                   pd.get_dummies(s.month.astype(str), prefix="m", dtype=float)], axis=1)
    return f


def lasso_errors(x, brk, end):
    """Prediction errors of each country's log load in [brk, end], trained on dates before brk."""
    pre = x[x.date < brk]
    post = x[(x.date >= brk) & (x.date <= end)]
    out = {}
    for c in ("es", "pt"):
        F = features(pd.concat([pre, post]))
        extra = pd.DataFrame({"trend": (pd.concat([pre, post]).date - pre.date.min()).dt.days / 365.0,
                              "hdh": np.maximum(18 - pd.concat([pre, post])[f"temp_{c}"], 0), "cdh": np.maximum(pd.concat([pre, post])[f"temp_{c}"] - 18, 0)}, index=F.index)
        F = pd.concat([F, extra], axis=1)
        Ftr, Fte = F.loc[pre.index], F.loc[post.index]
        mu, sd = Ftr.mean(), Ftr.std().replace(0, 1)
        m = LassoCV(cv=TimeSeriesSplit(4), alphas=20, max_iter=3000, n_jobs=-1).fit(((Ftr - mu) / sd).to_numpy(), np.log(pre[f"load_{c}"]).to_numpy())
        out[c] = np.log(post[f"load_{c}"]).to_numpy() - m.predict(((Fte - mu) / sd).to_numpy())
    p = post.copy()
    p["err_d"] = out["es"] - out["pt"]
    return p


def err_by_type(p, types="type", subset=None):
    s = p if subset is None else p[subset]
    return {t: s.loc[s[types] == t, "err_d"].mean() for t in TYPES}


def main():
    x = build()
    print(f"{len(x)} hours, {x.date.min().date()} -> {x.date.max().date()}")
    res = []
    for v in ["V1", "V2", "V3", "V4"]:
        r = did(x, BREAK, variant=v)
        for t, (b, se) in r.items():
            if v == "V4" and t in TYPES:
                continue  # not separately identified under year-month effects
            res.append(dict(step="DiD", variant=v, type=t, effect_pct=100 * b, se_pct=100 * se, t=b / se))
    p = lasso_errors(x, BREAK, END)
    e = err_by_type(p)
    ref = np.mean([e[t] for t in TYPES])
    for t in TYPES:
        res.append(dict(step="LASSO errors", variant="mean error diff", type=t, effect_pct=100 * e[t], se_pct=np.nan, t=np.nan))
    # LASSO errors, weekend / holiday days with fake types
    ew = err_by_type(p, "ftype", p.weekend.to_numpy())
    for t in TYPES:
        res.append(dict(step="LASSO errors weekend", variant="fake types", type=t, effect_pct=100 * ew[t], se_pct=np.nan, t=np.nan))
    # weekend fake types in DiD
    wk = x.weekend.to_numpy()
    rw = did(x, BREAK, types="ftype", subset=wk, variant="V1")
    for t, (b, se) in rw.items():
        res.append(dict(step="DiD weekend fake types", variant="V1", type=t, effect_pct=100 * b, se_pct=100 * se, t=b / se))
    r = pd.DataFrame(res)
    r.round(3).to_csv(OUT / "tou_did_estimates.csv", index=False)
    pd.set_option("display.width", 200)
    print(r.round(2).to_string(index=False))
    # placebo breaks
    pl = []
    for b in pd.date_range("2019-01-01", "2020-12-01", freq="MS"):
        end = b + pd.DateOffset(months=4) - pd.Timedelta(days=1)
        sub = x[x.date <= end]
        rr = did(sub, b, variant="V1")
        pe = lasso_errors(x, b, end)
        ee = err_by_type(pe)
        pl.append(dict(break_date=b.date(), did_peak=100 * rr["peak"][0], did_mid=100 * rr["mid"][0], did_off=100 * rr["off"][0],
                       lasso_peak=100 * ee["peak"], lasso_mid=100 * ee["mid"], lasso_off=100 * ee["off"]))
        print(pl[-1], flush=True)
    pl = pd.DataFrame(pl)
    pl.round(3).to_csv(OUT / "tou_did_placebo.csv", index=False)
    real_did = r[(r.step == "DiD") & (r.variant == "V1") & (r.type == "peak")].effect_pct.iloc[0]
    real_ls = 100 * e["peak"]
    for nm, real, col in [("DiD V1 peak", real_did, "did_peak"), ("LASSO peak", real_ls, "lasso_peak")]:
        s = pl[col]
        print(f"{nm}: real {real:+.2f}%; {len(s)} placebos sd {s.std():.2f}, 5-95% [{s.quantile(.05):+.2f}, {s.quantile(.95):+.2f}], rank by |.| {int((s.abs() >= abs(real)).sum()) + 1} of {len(s) + 1}")


if __name__ == "__main__":
    main()
