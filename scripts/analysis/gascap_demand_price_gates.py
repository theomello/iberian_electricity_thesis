"""Step 1 of docs/specs/2026-11-12-tax-gascap-demand-design.md: price gates G0-G4 for the gas-cap demand event (2022-06-15).

Descriptive only: no demand outcome other than the 352/351 share (G4). Windows: 28 days before and 14 days after a break.
Placebo breaks: 1st and 15th of each month 2021-10 -> 2022-04 and 2022-08 -> 2023-01. Blocks (local hours, [start, end)):
night 0-7, midday 11-14, evening 19-22. Data root: env VRE_DATA_ROOT (default: the repo this script sits in).
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = Path(os.environ.get("VRE_DATA_ROOT", ROOT))
OUT = ROOT / "outputs" / "tables"
OUT.mkdir(parents=True, exist_ok=True)
REAL = pd.Timestamp("2022-06-15")
BLOCKS = {"night": range(0, 7), "midday": range(11, 14), "evening": range(19, 22)}


def esios(i):
    d = pd.read_parquet(DATA / f"data/esios/esios_{i}.parquet")
    d = d[d.geo_name == "Península"].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value
    d.index = d.index.tz_convert("Europe/Madrid")
    return d.rename(str(i))


def load():
    p, c = esios(1001), esios(1909)
    o = pd.read_parquet(DATA / "data/omie/prices/omie_day_ahead_prices.parquet").drop_duplicates("utc_timestamp").set_index("utc_timestamp").price_es
    o.index = o.index.tz_convert("Europe/Madrid")
    x = pd.concat([p, c, o.rename("omie")], axis=1).dropna(subset=["1001", "omie"])
    x["1909"] = x["1909"].fillna(0.0)
    x = x[x.index >= "2021-10-01"]
    x["date"] = pd.to_datetime(x.index.date)
    x["hour"] = x.index.hour
    x["lp"] = np.log(x["1001"])
    return x


def window_stats(x, brk):
    pre = x[(x.date >= brk - pd.Timedelta(days=28)) & (x.date < brk)]
    post = x[(x.date >= brk) & (x.date < brk + pd.Timedelta(days=14))]
    if pre.date.nunique() < 26 or post.date.nunique() < 13:
        return None
    r = {"break": brk, "d_level": post.lp.mean() - pre.lp.mean()}
    for b, hs in BLOCKS.items():
        r[b] = post[post.hour.isin(hs)].lp.mean() - pre[pre.hour.isin(hs)].lp.mean()
    r["evening_minus_midday"] = r["evening"] - r["midday"]
    r["night_minus_midday"] = r["night"] - r["midday"]
    return r


def main():
    x = load()
    real = window_stats(x, REAL)
    pb = [pd.Timestamp(f"{y}-{m:02d}-{d:02d}") for y in (2021, 2022, 2023) for m in range(1, 13) for d in (1, 15)]
    pb = [b for b in pb if (pd.Timestamp("2021-10-01") <= b <= pd.Timestamp("2022-04-15")) or (pd.Timestamp("2022-08-01") <= b <= pd.Timestamp("2023-01-15"))]
    pl = pd.DataFrame([r for r in (window_stats(x, b) for b in pb) if r])
    pl.to_csv(OUT / "gascap_demand_gates_placebo.csv", index=False)
    rows = []
    for k in ["d_level", "evening_minus_midday", "night_minus_midday"]:
        p95 = pl[k].abs().quantile(0.95)
        rows.append({"measure": k, "real": real[k], "placebo_p95_abs": p95, "placebo_sd": pl[k].std(), "n_placebo": len(pl),
                     "pass_0.10": abs(real[k]) >= 0.10, "pass_p95": abs(real[k]) > p95})
    for b in BLOCKS:
        rows.append({"measure": b, "real": real[b], "placebo_p95_abs": pl[b].abs().quantile(0.95), "placebo_sd": pl[b].std(), "n_placebo": len(pl)})
    g = pd.DataFrame(rows)
    # G0: does 1001 contain 1909? (hour-of-day effects; window 2022-05-18 -> 06-28)
    w = x[(x.date >= "2022-05-18") & (x.date < "2022-06-29")].copy()
    hd = pd.get_dummies(w.hour, prefix="h", drop_first=True).astype(float)
    g0 = {}
    X = sm.add_constant(pd.concat([w[["1909", "omie"]], hd], axis=1))
    m = sm.OLS(w["1001"], X).fit(cov_type="cluster", cov_kwds={"groups": w.date.factorize()[0]})
    g0["levels_1909"], g0["levels_1909_se"], g0["levels_omie"] = m.params["1909"], m.bse["1909"], m.params["omie"]
    dd = w[["1001", "1909", "omie"]].diff().dropna()
    m2 = sm.OLS(dd["1001"], sm.add_constant(dd[["1909", "omie"]])).fit(cov_type="HC1")
    g0["diff_1909"], g0["diff_1909_se"], g0["diff_omie"] = m2.params["1909"], m2.bse["1909"], m2.params["omie"]
    # G3: first stage, daily mean ln 1001 on Y, 2022-03-01 -> 2023-02-25, weekday effects + linear trend
    mc = pd.read_parquet(DATA / "data/jrc_ppdb/implied_marginal_cost_daily.parquet", columns=["date", "subsidy_eur_mwh"])
    mc["date"] = pd.to_datetime(mc.date)
    Y = mc.groupby("date").subsidy_eur_mwh.max().fillna(0.0).rename("Y")
    dly = x.groupby("date").lp.mean().to_frame().join(Y, how="left")
    dly["Y"] = dly.Y.fillna(0.0)
    dly = dly[(dly.index >= "2022-03-01") & (dly.index <= "2023-02-25")]
    dly.loc[dly.index < REAL, "Y"] = 0.0
    dly["t"] = np.arange(len(dly))
    X = sm.add_constant(pd.concat([dly[["Y", "t"]], pd.get_dummies(dly.index.dayofweek, prefix="dow", drop_first=True).set_index(dly.index).astype(float)], axis=1))
    m3 = sm.OLS(dly.lp, X).fit(cov_type="HAC", cov_kwds={"maxlags": 7})
    g3 = {"Y_coef": m3.params["Y"], "Y_se": m3.bse["Y"], "F": (m3.params["Y"] / m3.bse["Y"]) ** 2, "n_days": len(dly)}
    # G4: share of 352 in (351+352), daily energy, window means
    s = pd.concat([esios(352), esios(351)], axis=1).dropna()
    s["date"] = pd.to_datetime(s.index.date)
    d = s.groupby("date").sum()
    d["share"] = d["352"] / (d["352"] + d["351"])
    pre = d.share[(d.index >= REAL - pd.Timedelta(days=28)) & (d.index < REAL)].mean()
    post = d.share[(d.index >= REAL) & (d.index < REAL + pd.Timedelta(days=14))].mean()
    g4 = {"share_pre": pre, "share_post": post, "rel_change": post / pre - 1}
    g.to_csv(OUT / "gascap_demand_gates.csv", index=False)
    pd.Series({**{f"G0_{k}": v for k, v in g0.items()}, **{f"G3_{k}": v for k, v in g3.items()}, **{f"G4_{k}": v for k, v in g4.items()}}).to_csv(OUT / "gascap_demand_gates_g034.csv")
    pd.set_option("display.width", 200)
    print(g.round(3).to_string(index=False)); print("G0", {k: round(v, 3) for k, v in g0.items()}); print("G3", {k: round(v, 3) for k, v in g3.items()}); print("G4", {k: round(v, 4) for k, v in g4.items()})


if __name__ == "__main__":
    main()
