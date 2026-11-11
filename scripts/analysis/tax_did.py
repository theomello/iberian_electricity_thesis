"""Tax-step difference-in-differences: Spanish measured low-voltage demand (E0) against Portugal's consumption.

Spec and stop rules: docs/specs/2026-11-11-tax-change-design.md. Outcome: ln E0 (ESIOS 1201, peninsular, hourly MWh) minus
ln Portuguese load (REN `Consumption`, 15-minute averaged to the hour) at the same local hour of the same date, each country
on its own clock. Steps (all confirmed in the BOE except where flagged in the spec): 2021-06-26 VAT 21->10%, 2021-09-16
electricity tax 5.11->0.5%, 2022-07-01 VAT 10->5%, 2024-01-01 VAT 5->10% with electricity tax 0.5->2.5%. Post window: 4 months,
cut at the next step (S1 at S2, S4 at 2024-03-01, when a price-triggered step begins). Pre window: A = every day before the
step from 2018-01-01 (the spec), B = the 12 months before; March-June 2020 (COVID) is excluded from every pre window and no
placebo window touches it. Estimators: DiD on a post dummy with hour, weekday and month effects (V1) and with temperature and
holiday differences (V3), clustered by week; LASSO prediction errors (Burlig et al. 2020) trained on the pre window, mean
error difference over the post window. Placebos: fake steps on the 1st of each month 2019-01 -> 2021-02 (4-month post window,
all before 2021-06-26). The Wald ratio divides the effect by the change in ln tax factor. Outputs outputs/tables/tax_did_*.csv.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LassoCV
from sklearn.model_selection import TimeSeriesSplit

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tou_did import dummies, hac_cluster  # noqa: E402

warnings.filterwarnings("ignore")
OUT = ROOT / "outputs" / "tables"
END = pd.Timestamp("2024-12-31")
COVID = (pd.Timestamp("2020-03-01"), pd.Timestamp("2020-06-30"))
# (name, date, post-window end, change in tax factor from the BOE rates)
F = {"pre": 1.0511269632 * 1.21, "s1": 1.0511269632 * 1.10, "s2": 1.005 * 1.10, "s3": 1.005 * 1.05, "s4": 1.025 * 1.10}
STEPS = [
    ("S1 VAT 21->10%", "2021-06-26", "2021-09-15", np.log(F["s1"] / F["pre"])),
    ("S2 electricity tax 5.11->0.5%", "2021-09-16", "2022-01-15", np.log(F["s2"] / F["s1"])),
    ("S3 VAT 10->5%", "2022-07-01", "2022-10-31", np.log(F["s3"] / F["s2"])),
    ("S4 VAT 5->10%, tax 0.5->2.5%", "2024-01-01", "2024-02-29", np.log(F["s4"] / F["s3"])),
]


def build() -> pd.DataFrame:
    es = pd.read_parquet(ROOT / "data/esios/esios_1201.parquet").drop_duplicates("utc_timestamp").set_index("utc_timestamp").value
    pt = pd.read_parquet(ROOT / "data/ren/ren_production_15min.parquet")
    pt = pt[pt.series == "Consumption"].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value_mw.resample("1h").mean()
    t = pd.read_parquet(ROOT / "data/weather/temperature_population_hourly.parquet", columns=["country", "utc_timestamp", "temperature_2m"])
    tes = t[t.country == "ES"].groupby("utc_timestamp").temperature_2m.mean()
    tpt = t[t.country == "PT"].groupby("utc_timestamp").temperature_2m.mean()
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    hpt = set(pd.to_datetime(hol[hol.area == "PT"].date))
    rows = {}
    for name, s, tz, temp in [("es", es, "Europe/Madrid", tes), ("pt", pt, "Europe/Lisbon", tpt)]:
        d = pd.DataFrame({"load": s, "temp": temp}).dropna()
        d = d[(d.index >= "2017-12-31") & (d.index < "2025-01-02")]
        loc = d.index.tz_convert(tz)
        d["date"] = pd.to_datetime(loc.date)
        d["hour"] = loc.hour
        d = d.drop_duplicates(["date", "hour"])
        rows[name] = d.set_index(["date", "hour"])
    x = rows["es"].join(rows["pt"], how="inner", lsuffix="_es", rsuffix="_pt").dropna().reset_index()
    x["dow"] = x.date.dt.dayofweek
    x["month"] = x.date.dt.month
    x["hol_es"] = x.date.isin(hes).astype(float)
    x["hol_pt"] = x.date.isin(hpt).astype(float)
    x["weekend"] = (x.dow >= 5) | (x.hol_es == 1)
    x["d"] = np.log(x.load_es) - np.log(x.load_pt)
    x["hdh_d"] = np.maximum(18 - x.temp_es, 0) - np.maximum(18 - x.temp_pt, 0)
    x["cdh_d"] = np.maximum(x.temp_es - 18, 0) - np.maximum(x.temp_pt - 18, 0)
    x = x[x.date <= END]
    return x.sort_values(["date", "hour"]).reset_index(drop=True)


def window(x, brk, post_end, pre_months):
    brk, post_end = pd.Timestamp(brk), pd.Timestamp(post_end)
    lo = pd.Timestamp("2018-01-01") if pre_months is None else brk - pd.DateOffset(months=pre_months)
    pre = x[(x.date >= lo) & (x.date < brk) & ~x.date.between(*COVID)]
    post = x[(x.date >= brk) & (x.date <= post_end)]
    return pre, post


def did(pre, post, controls):
    s = pd.concat([pre, post])
    isp = np.r_[np.zeros(len(pre)), np.ones(len(post))]
    base = [dummies(s, ["hour", "dow", "month"])]
    if controls:
        base.append(s[["hdh_d", "cdh_d", "hol_es", "hol_pt"]])
    X = pd.concat(base, axis=1)
    X = X.loc[:, X.std() > 0]
    X.insert(0, "post", isp)
    X.insert(0, "const", 1.0)
    Xv, yv = X.to_numpy(), s.d.to_numpy()
    b = np.linalg.pinv(Xv) @ yv
    e = yv - Xv @ b
    V = hac_cluster(Xv, e, s.date.dt.to_period("W").astype(str).factorize()[0])
    i = list(X.columns).index("post")
    return b[i], np.sqrt(V[i, i])


def lasso_err(pre, post):
    full = pd.concat([pre, post])
    out = {}
    for c in ("es", "pt"):
        F_ = pd.concat([pd.get_dummies(full.hour.astype(str) + "_" + np.where(full.weekend, "w", full.dow.astype(str)), dtype=float),
                        pd.get_dummies(full.month.astype(str), prefix="m", dtype=float)], axis=1)
        F_["trend"] = (full.date - pre.date.min()).dt.days / 365.0
        F_["hdh"] = np.maximum(18 - full[f"temp_{c}"], 0)
        F_["cdh"] = np.maximum(full[f"temp_{c}"] - 18, 0)
        tr, te = F_.loc[pre.index], F_.loc[post.index]
        mu, sd = tr.mean(), tr.std().replace(0, 1)
        m = LassoCV(cv=TimeSeriesSplit(4), alphas=20, max_iter=3000, n_jobs=-1).fit(((tr - mu) / sd).to_numpy(), np.log(pre[f"load_{c}"]).to_numpy())
        out[c] = np.log(post[f"load_{c}"]).to_numpy() - m.predict(((te - mu) / sd).to_numpy())
    p = post.copy()
    p["err"] = out["es"] - out["pt"]
    g = p.date.dt.to_period("W").astype(str).factorize()[0]
    X = np.ones((len(p), 1))
    V = hac_cluster(X, p.err.to_numpy() - p.err.mean(), g)
    return p.err.mean(), float(np.sqrt(V[0, 0]))


def run(x, brk, post_end, pre_months):
    pre, post = window(x, brk, post_end, pre_months)
    b1, s1 = did(pre, post, False)
    b3, s3 = did(pre, post, True)
    bl, sl = lasso_err(pre, post)
    return dict(n_pre=len(pre), n_post=len(post), did_v1=100 * b1, se_v1=100 * s1, did_v3=100 * b3, se_v3=100 * s3, lasso=100 * bl, se_lasso=100 * sl)


def main():
    x = build()
    print(f"{len(x)} hours, {x.date.min().date()} -> {x.date.max().date()}", flush=True)
    res = []
    for pm, lab in ((None, "A whole prior"), (12, "B 12 months")):
        for name, brk, end, dlnf in STEPS:
            r = run(x, brk, end, pm)
            r.update(pre=lab, step=name, date=brk, dln_tax_factor_pct=100 * dlnf)
            for k in ("did_v1", "did_v3", "lasso"):
                r[f"wald_{k}"] = r[k] / (100 * dlnf)
            res.append(r)
            print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    pd.DataFrame(res).round(3).to_csv(OUT / "tax_did_estimates.csv", index=False)
    # placebos
    pl = []
    for b in pd.date_range("2019-01-01", "2021-02-01", freq="MS"):
        end = b + pd.DateOffset(months=4) - pd.Timedelta(days=1)
        if end >= COVID[0] and b <= COVID[1]:
            continue
        for pm, lab in ((None, "A"), (12, "B")):
            r = run(x, b, end, pm)
            r.update(pre=lab, date=b.date())
            pl.append(r)
        print(pl[-1]["date"], flush=True)
    pl = pd.DataFrame(pl)
    pl.round(3).to_csv(OUT / "tax_did_placebo.csv", index=False)
    real = pd.DataFrame(res)
    for lab in ("A", "B"):
        pp = pl[pl.pre == lab]
        rr = real[real.pre.str.startswith(lab)]
        for col in ("did_v1", "did_v3", "lasso"):
            s = pp[col]
            print(f"{lab} {col}: {len(s)} placebos sd {s.std():.2f}, 5-95% [{s.quantile(.05):+.2f}, {s.quantile(.95):+.2f}]; real "
                  + "; ".join(f"{n[:2]} {v:+.2f} (rank {int((s.abs() >= abs(v)).sum()) + 1}/{len(s) + 1})" for n, v in zip(rr.step, rr[col])))


if __name__ == "__main__":
    main()
