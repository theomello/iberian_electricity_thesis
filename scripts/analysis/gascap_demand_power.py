"""Step 2 of docs/specs/2026-11-12-tax-gascap-demand-design.md: power gate on placebo breaks. The real break (2022-06-15) outcomes are NOT computed.

Outcome d = ln(series) - ln(control) at the same local hour. Per placebo break (the 24 windows of Step 1; 28 days before, 14 after):
OLS of d on post x block (night 0-7, midday 11-14, evening 19-22; other hours' post effect = 'rest'), hour and weekday effects,
temperature and holiday differences (Portugal control), clustered by day. Reports the night-minus-midday contrast and the level (mean post).
MDE = 2.8 x sd of the placebo estimates. Series: 352 (primary), E0 (1201), and, ADDED after the user's question and not in the spec,
351 (free-market retailers), 353 (direct consumers) and industry (E1-E6). Controls: Portugal's consumption, and 351 (for 352).
Data root: env VRE_DATA_ROOT.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = Path(os.environ.get("VRE_DATA_ROOT", ROOT))
OUT = ROOT / "outputs" / "tables"
BLK = {"night": range(0, 7), "midday": range(11, 14), "evening": range(19, 22)}


def es(i):
    d = pd.read_parquet(DATA / f"data/esios/esios_{i}.parquet")
    d = d[d.geo_name == "Península"].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value
    return d.resample("1h").mean()


def local(s, tz):
    d = pd.DataFrame({"v": s}).dropna()
    d = d[(d.index >= "2021-08-01") & (d.index < "2023-02-15")]
    loc = d.index.tz_convert(tz)
    d["date"], d["hour"] = pd.to_datetime(loc.date), loc.hour
    return d.drop_duplicates(["date", "hour"]).set_index(["date", "hour"]).v


def temps():
    t = pd.read_parquet(DATA / "data/weather/temperature_population_hourly.parquet", columns=["country", "utc_timestamp", "temperature_2m"])
    return [t[t.country == c].groupby("utc_timestamp").temperature_2m.mean() for c in ("ES", "PT")]


def main():
    pt = pd.read_parquet(DATA / "data/ren/ren_production_15min.parquet")
    pt = pt[pt.series == "Consumption"].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value_mw.resample("1h").mean()
    tes, tpt = temps()
    hol = pd.read_parquet(DATA / "data/holidays/holidays_es_pt.parquet")
    hes = set(pd.to_datetime(hol[(hol.area == "AN") & (hol.mark == "national")].date))
    hpt = set(pd.to_datetime(hol[hol.area == "PT"].date))
    ind = sum(es(i) for i in range(1202, 1208))
    series = {"352": es(352), "E0": es(1201), "351": es(351), "353": es(353), "industry": ind}
    jobs = [("352", "PT"), ("352", "351"), ("E0", "PT"), ("351", "PT"), ("353", "PT"), ("industry", "PT")]
    base = local(tes, "Europe/Madrid").rename("tes").to_frame().join(local(tpt, "Europe/Lisbon").rename("tpt"), how="inner")
    breaks = [pd.Timestamp(f"{y}-{m:02d}-{d:02d}") for y in (2021, 2022, 2023) for m in range(1, 13) for d in (1, 15)]
    breaks = [b for b in breaks if (pd.Timestamp("2021-10-01") <= b <= pd.Timestamp("2022-04-15")) or (pd.Timestamp("2022-08-01") <= b <= pd.Timestamp("2023-01-15"))]
    rows = []
    for name, ctrl in jobs:
        x = local(series[name], "Europe/Madrid").rename("a").to_frame()
        x = x.join(local(pt, "Europe/Lisbon").rename("c") if ctrl == "PT" else local(series[ctrl], "Europe/Madrid").rename("c"), how="inner").join(base, how="inner").dropna().reset_index()
        x["d"] = np.log(x.a) - np.log(x.c)
        x["dow"] = x.date.dt.dayofweek
        x["hdh"] = np.maximum(18 - x.tes, 0) - np.maximum(18 - x.tpt, 0)
        x["cdh"] = np.maximum(x.tes - 18, 0) - np.maximum(x.tpt - 18, 0)
        x["hol"] = x.date.isin(hes).astype(float) - (x.date.isin(hpt).astype(float) if ctrl == "PT" else 0)
        for b in breaks:
            s = x[(x.date >= b - pd.Timedelta(days=28)) & (x.date < b + pd.Timedelta(days=14))].copy()
            if s.date.nunique() < 40:
                continue
            post = (s.date >= b).astype(float)
            cols = {f"p_{k}": post * s.hour.isin(list(v)) for k, v in BLK.items()}
            cols["p_all"] = post
            Xs = pd.concat([pd.get_dummies(s.hour.astype(str), prefix="h", drop_first=True, dtype=float), pd.get_dummies(s.dow.astype(str), prefix="w", drop_first=True, dtype=float), s[["hdh", "cdh", "hol"]]], axis=1)
            X = pd.concat([Xs, pd.DataFrame(cols, index=s.index).astype(float)], axis=1)
            X = X.loc[:, X.std() > 0]
            X.insert(0, "const", 1.0)
            Xv, yv = X.to_numpy(), s.d.to_numpy()
            beta = np.linalg.pinv(Xv) @ yv
            nm = list(X.columns)
            rows.append({"series": name, "control": ctrl, "break": b, "level": beta[nm.index("p_all")], "night_minus_midday": beta[nm.index("p_night")] - beta[nm.index("p_midday")]})
    r = pd.DataFrame(rows)
    r.to_csv(OUT / "gascap_demand_power_placebo.csv", index=False)
    implied = -0.10 * 0.290
    out = r.groupby(["series", "control"]).agg(n=("level", "size"), sd_contrast=("night_minus_midday", "std"), sd_level=("level", "std")).reset_index()
    out["mde_contrast"] = 2.8 * out.sd_contrast
    out["implied_-0.10"] = implied
    out["P1_mde<=half"] = out.mde_contrast <= abs(implied) / 2
    out["P2_mde<=-0.5_effect"] = out.mde_contrast <= 0.5 * 0.290
    out.to_csv(OUT / "gascap_demand_power.csv", index=False)
    pd.set_option("display.width", 200)
    print(out.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
