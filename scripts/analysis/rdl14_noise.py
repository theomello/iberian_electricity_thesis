"""Noise check for the RDL 14/2022 shocks (pre-2021 data only; no 2022 data is read).

    .venv/bin/python scripts/analysis/rdl14_noise.py

Lighting: daily ln(load 22-23h / load 18-21h) (and a second reference, 14-17h) for ESIOS E1+E2 (1202+1203), Spain minus Portugal (REN consumption), leave-year-out LASSO residual
(tou_ces.taste_pred); sd of 58-weekday window means (the length of 11 Aug -> 31 Oct) over 2018-2020 pre-reform days, and the detectable effect 2.8 sd.
Air-conditioning: daily ln(E1+E2 total), Spain minus Portugal residual regressed on the cooling-degree gap (max(tmean-24,0) Spain minus Portugal) within summer windows; sd of that slope across windows.
Writes outputs/tables/rdl14_noise.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_ces as C  # noqa: E402
import tou_cross_tariff as CT  # noqa: E402
import tou_did as T  # noqa: E402

WIN, STEP = 58, 5
HRS = {"late": [22, 23], "eve": [18, 19, 20, 21], "aft": [14, 15, 16, 17]}


def hsum(load, hrs):
    return load[load.hour.isin(hrs)].groupby("date").v.sum()


def main():
    x = C.D.prep(T.build("e0", end="2021-09-14"))
    es = CT.esios_load([1202, 1203])
    pt = x[["date", "hour", "load_pt"]].rename(columns={"load_pt": "v"})
    g = x.groupby("date")
    d = pd.DataFrame(index=sorted(x.date.unique()))
    d.index.name = "date"
    for nm, c in (("es", "temp_es"), ("pt", "temp_pt")):
        d[f"tmean_{nm}"], d[f"tmin_{nm}"], d[f"tmax_{nm}"] = g[c].mean(), g[c].min(), g[c].max()
    first = x.groupby("date").first()
    d["es_work"] = first.kind == "work"
    d["pt_work"] = (first.dow < 5) & (first.hol_pt == 0)
    full = (es.groupby("date").hour.count() == 24) & (pt.groupby("date").hour.count() == 24)
    d = d.reset_index()
    d["month"], d["year"] = d.date.dt.month, d.date.dt.year
    covid = d.date.between(*C.EV.COVID)
    d["pre"] = d.date.between(C.PRE0, C.PRE1) & ~covid & d.date.isin(full[full].index)
    d["both"] = d.es_work & d.pt_work
    d = d.set_index("date", drop=False)
    for nm, ld in (("es", es), ("pt", pt)):
        for k, h in HRS.items():
            d[f"q_{nm}_{k}"] = hsum(ld, h)
        d[f"q_{nm}_day"] = ld.groupby("date").v.sum()
    d = d.reset_index(drop=True)
    d["cdh_gap"] = np.maximum(d.tmean_es - 24, 0) - np.maximum(d.tmean_pt - 24, 0)

    def resid(nm, y):
        r = pd.Series(np.nan, index=d.index)
        for yr in (2018, 2019, 2020):
            s = d.year == yr
            r[s] = (y - C.taste_pred(d, y, nm, (yr,)))[s]
        return r

    rows = []
    for lab, ref in (("22-23 vs 18-21", "eve"), ("22-23 vs 14-17", "aft")):
        res = {}
        for nm in ("es", "pt"):
            y = np.log(d[f"q_{nm}_late"] / d[f"q_{nm}_{ref}"])
            res[nm] = resid(nm, y)
        elig = d.pre & d.both & res["es"].notna() & res["pt"].notna()
        r = (res["es"] - res["pt"])[elig].to_numpy()
        m = np.array([r[i:i + WIN].mean() for i in range(0, len(r) - WIN + 1, STEP)])
        rows.append(dict(test=f"lighting {lab}", days=len(r), daily_sd=r.std(ddof=1), window_mean_sd=m.std(ddof=1), max_abs=np.abs(m).max(), mde=2.8 * m.std(ddof=1)))
        print(rows[-1], flush=True)
    res = {nm: resid(nm, np.log(d[f"q_{nm}_day"])) for nm in ("es", "pt")}
    e = d.pre & d.both & res["es"].notna() & res["pt"].notna() & d.month.between(6, 9)
    dd = d[e].assign(r=(res["es"] - res["pt"])[e])
    sl = []
    for yr, s in dd.groupby("year"):
        for i in range(0, len(s) - WIN + 1, STEP):
            w = s.iloc[i:i + WIN]
            sl.append(np.polyfit(w.cdh_gap, w.r, 1)[0])
    sl = np.array(sl)
    typ = dd.cdh_gap[dd.cdh_gap > 0].mean()
    rows.append(dict(test="air-conditioning slope (log load per degree of cooling gap)", days=len(dd), daily_sd=dd.r.std(ddof=1), window_mean_sd=sl.std(ddof=1) if len(sl) > 1 else np.nan,
                     max_abs=np.abs(sl).max() if len(sl) else np.nan, mde=2.8 * sl.std(ddof=1) if len(sl) > 1 else np.nan, n_windows=len(sl), mean_positive_gap=typ))
    print(rows[-1], flush=True)
    R = pd.DataFrame(rows)
    R.round(5).to_csv(T.OUT / "rdl14_noise.csv", index=False)
    print(R.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
