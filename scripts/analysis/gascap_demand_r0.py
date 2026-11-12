"""R0 of docs/specs/2026-11-12-demand-redesign-options.md: power gate for a regulated-to-regulated area panel. Real break NOT computed.

Spanish regulated (reference-supplier) purchases by area from OMIE PDBF, all roles summed per unit-period, sign flipped: Endesa XXI EE21C01,
Iberdrola Curenergia IBCUC01, Naturgy GNSUC01, EDP HCURC01 (the 4 areas >= 40 MW; CHCOC01 and EONUC01, under 1.5% of volume, left out).
Portuguese control: SU Eletricidade EDPUC2. Both on OMIE market time (CET), so no clock conversion between them; DST days dropped.
Variants (night - midday contrast, as Step 2; 26 placebo breaks; 28 days pre, 14 post):
 agg_SU   sum of the 4 areas vs SU Eletricidade         agg_352_SU  ESIOS 352 vs SU (does the series matter?)
 panel_SU 4 areas pooled (area x hour, area x weekday effects) vs SU, mean of area contrasts
 synth    sum of the 4 areas vs non-negative weights on SU, Portuguese total load, ESIOS 351 fitted on the window's own pre-period
 ref      sum of the 4 areas vs Portuguese total load (Step 2's control)
Data root: env VRE_DATA_ROOT.
"""
import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import nnls

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = Path(os.environ.get("VRE_DATA_ROOT", ROOT))
OUT = ROOT / "outputs" / "tables"
BLK = {"night": range(0, 7), "midday": range(11, 14)}
ES_UNITS = {"endesa": "EE21C01", "iberdrola": "IBCUC01", "naturgy": "GNSUC01", "edp": "HCURC01"}
DST = pd.to_datetime(["2021-10-31", "2022-03-27", "2022-10-30", "2023-03-26"])


def pdbf():
    fs = [f for f in sorted(glob.glob(str(DATA / "data/omie/pdbf/parquet/pdbf_*.parquet"))) if "202108" <= f[-14:-8] <= "202302"]
    d = pd.concat([pd.read_parquet(f) for f in fs])
    d = d[d.unit.isin(list(ES_UNITS.values()) + ["EDPUC2"])]
    d["date"] = pd.to_datetime(d.date)
    d["hour"] = d.period - 1
    d = d[~d.date.isin(DST)]
    g = (-d.groupby(["unit", "date", "hour"]).schedule_mw.sum()).unstack("unit")
    return g


def esios_h(i):
    s = pd.read_parquet(DATA / f"data/esios/esios_{i}.parquet")
    s = s[s.geo_name == "Península"].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value.resample("1h").mean()
    s.index = s.index.tz_convert("Europe/Madrid")
    return s


def madrid_frame(s):  # series on a Madrid-tz index -> (date, hour) index
    d = pd.DataFrame({"v": s}).dropna()
    d["date"], d["hour"] = pd.to_datetime(d.index.date), d.index.hour
    return d.drop_duplicates(["date", "hour"]).set_index(["date", "hour"]).v


def fit(s, cols_y, cols_x):
    """OLS of y on post x block with hour, weekday effects, temp and holiday differences; returns night-midday and level (cluster-free point estimates)."""
    post = (s.date >= s.brk).astype(float)
    X = pd.concat([pd.get_dummies(s.hour.astype(str), prefix="h", drop_first=True, dtype=float), pd.get_dummies(s.dow.astype(str), prefix="w", drop_first=True, dtype=float), s[["hdh", "cdh", "hol"]]], axis=1)
    X["p_night"], X["p_mid"], X["p_all"] = post * s.hour.isin(BLK["night"]), post * s.hour.isin(BLK["midday"]), post
    X = X.astype(float)
    X = X.loc[:, X.std() > 0]
    X.insert(0, "c", 1.0)
    b = np.linalg.pinv(X.to_numpy()) @ s.y.to_numpy()
    n = list(X.columns)
    return b[n.index("p_night")] - b[n.index("p_mid")], b[n.index("p_all")]


def main():
    g = pdbf()
    es_sum = g[list(ES_UNITS.values())].sum(axis=1, min_count=4)
    pt = pd.read_parquet(DATA / "data/ren/ren_production_15min.parquet")
    pt = pt[pt.series == "Consumption"].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value_mw.resample("1h").mean()
    pt.index = pt.index.tz_convert("Europe/Madrid")  # same instant, labelled on the Madrid clock
    t = pd.read_parquet(DATA / "data/weather/temperature_population_hourly.parquet", columns=["country", "utc_timestamp", "temperature_2m"])
    tes = t[t.country == "ES"].groupby("utc_timestamp").temperature_2m.mean()
    tpt = t[t.country == "PT"].groupby("utc_timestamp").temperature_2m.mean()
    tes.index, tpt.index = tes.index.tz_convert("Europe/Madrid"), tpt.index.tz_convert("Europe/Madrid")
    hol = pd.read_parquet(DATA / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    hpt = set(pd.to_datetime(hol[hol.area == "PT"].date))
    base = pd.DataFrame({"es_sum": es_sum, "su": g["EDPUC2"], "pt": madrid_frame(pt), "s352": madrid_frame(esios_h(352)), "s351": madrid_frame(esios_h(351)),
                         "tes": madrid_frame(tes), "tpt": madrid_frame(tpt)})
    for k, u in ES_UNITS.items():
        base[k] = g[u]
    x = base.dropna().reset_index()
    x = x[(x.date >= "2021-08-15") & (x.date < "2023-02-15")]
    x["dow"] = x.date.dt.dayofweek
    x["hdh"] = np.maximum(18 - x.tes, 0) - np.maximum(18 - x.tpt, 0)
    x["cdh"] = np.maximum(x.tes - 18, 0) - np.maximum(x.tpt - 18, 0)
    x["hol"] = x.date.isin(hes).astype(float) - x.date.isin(hpt).astype(float)
    L = lambda c: np.log(x[c])
    breaks = [pd.Timestamp(f"{y}-{m:02d}-{d:02d}") for y in (2021, 2022, 2023) for m in range(1, 13) for d in (1, 15)]
    breaks = [b for b in breaks if (pd.Timestamp("2021-10-01") <= b <= pd.Timestamp("2022-04-15")) or (pd.Timestamp("2022-08-01") <= b <= pd.Timestamp("2023-01-15"))]
    rows = []
    for b in breaks:
        w = (x.date >= b - pd.Timedelta(days=28)) & (x.date < b + pd.Timedelta(days=14))
        s = x[w].copy()
        if s.date.nunique() < 38:
            continue
        s["brk"] = b
        pre = s.date < b
        res = {"break": b}
        for name, y in [("agg_SU", L("es_sum") - L("su")), ("agg_352_SU", L("s352") - L("su")), ("ref", L("es_sum") - L("pt"))]:
            s["y"] = y[w]
            res[name], res[name + "_lvl"] = fit(s, None, None)
        # panel: area-by-area contrasts averaged (area-specific hour and weekday effects via separate fits)
        cs = []
        for k in ES_UNITS:
            s["y"] = (L(k) - L("su"))[w]
            cs.append(fit(s, None, None)[0])
        res["panel_SU"] = float(np.mean(cs))
        # synthetic weights on the pre-period, residualised on hour effects
        hr = s.hour.astype(str)
        yy = np.log(s.es_sum)
        C = np.column_stack([np.log(s[c]) for c in ("su", "pt", "s351")])
        dm = lambda v: v - pd.Series(v, index=s.index)[pre].groupby(hr[pre]).mean().reindex(hr).to_numpy()
        wts, _ = nnls(np.column_stack([dm(C[:, j]) for j in range(3)])[pre.to_numpy()], dm(yy.to_numpy())[pre.to_numpy()])
        s["y"] = yy.to_numpy() - C @ wts
        res["synth"], res["synth_lvl"] = fit(s, None, None)
        res["w_su"], res["w_pt"], res["w_351"] = wts
        rows.append(res)
    r = pd.DataFrame(rows)
    r.to_csv(OUT / "gascap_demand_r0_placebo.csv", index=False)
    o = pd.DataFrame({"variant": ["agg_SU", "agg_352_SU", "panel_SU", "synth", "ref"], "n": len(r),
                      "sd": [r[c].std() for c in ["agg_SU", "agg_352_SU", "panel_SU", "synth", "ref"]],
                      "sd_level": [r[c + "_lvl"].std() if c + "_lvl" in r else np.nan for c in ["agg_SU", "agg_352_SU", "panel_SU", "synth", "ref"]]})
    o["mde"] = 2.8 * o.sd
    o["P1_mde<=1.45%"] = o.mde <= 0.0145
    o["P2_mde<=14.5%"] = o.mde <= 0.145
    o["stop_sd>=3%"] = o.sd >= 0.03
    o.to_csv(OUT / "gascap_demand_r0.csv", index=False)
    print(o.round(4).to_string(index=False)); print(r[["w_su", "w_pt", "w_351"]].mean().round(3).to_dict())
    print("sum of 4 areas / 352:", (x.es_sum / x.s352).describe()[["mean", "min", "max"]].round(3).to_dict())


if __name__ == "__main__":
    main()
